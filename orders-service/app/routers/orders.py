from asyncio import gather as asyncio_gather
from decimal import Decimal
from typing import Optional

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.constants import DELIVERY_COSTS, ErrorCode, ALLOWED_STATUS_TRANSITIONS
from app.core.config import settings
from app.database import get_pool
from app.enums import DeliveryType, OrderStatus
from app.schemas import (
    CreateOrderRequest,
    ErrorResponse,
    OrderCreatedResponse,
    OrderDetailResponse,
    OrderListResponse,
    OrderStatusUpdateRequest,
    OrderStatusUpdatedResponse,
)
from shared.auth import create_admin_dependency
from shared.utils import record_to_dict

router = APIRouter()
get_current_admin = create_admin_dependency(settings.jwt_secret_key, settings.jwt_algorithm)


async def generate_order_number(conn: asyncpg.Connection) -> str:
    """Генерирует номер заказа в формате LX-YYYYMMDD-NNNN."""
    date_str = await conn.fetchval("SELECT TO_CHAR(NOW(), 'YYYYMMDD')")
    seq = await conn.fetchval(
        """SELECT COALESCE(MAX(CAST(SPLIT_PART(order_number, '-', 3) AS INT)), 0) + 1
           FROM orders WHERE order_number LIKE $1""",
        f"LX-{date_str}-%",
    )
    return f"LX-{date_str}-{seq:04d}"


async def apply_promo(conn, code: Optional[str], subtotal: Decimal) -> tuple[Optional[int], Decimal]:
    if not code:
        return None, Decimal("0")

    promo = await conn.fetchrow(
        """SELECT id, discount_type, discount_value, min_order_amount,
                  max_uses, used_count, is_active
           FROM promo_codes WHERE code = $1""",
        code.upper(),
    )

    if not promo:
        raise HTTPException(status_code=400, detail={"error": ErrorCode.PROMO_INVALID, "message": "Промокод не найден"})
    if not promo["is_active"]:
        raise HTTPException(status_code=400, detail={"error": ErrorCode.PROMO_INVALID, "message": "Промокод неактивен"})
    if promo["min_order_amount"] and subtotal < Decimal(str(promo["min_order_amount"])):
        raise HTTPException(status_code=400, detail={"error": ErrorCode.PROMO_INVALID, "message": f"Минимальная сумма заказа для промокода: {promo['min_order_amount']} ₽"})
    if promo["max_uses"] and promo["used_count"] >= promo["max_uses"]:
        raise HTTPException(status_code=400, detail={"error": ErrorCode.PROMO_INVALID, "message": "Промокод исчерпан"})

    if promo["discount_type"] == "percent":
        discount = (subtotal * Decimal(str(promo["discount_value"])) / 100).quantize(Decimal("0.01"))
    else:
        discount = min(Decimal(str(promo["discount_value"])), subtotal)

    return promo["id"], discount


@router.post(
    "",
    status_code=201,
    response_model=OrderCreatedResponse,
    summary="Оформить заказ",
    description=(
        "Создаёт заказ из текущей корзины. "
        "После успешного создания корзина автоматически очищается. "
        "Заголовок **`X-Session-Id`** обязателен.\n\n"
        "**Номер заказа** генерируется в формате `LX-YYYYMMDD-NNNN`.\n\n"
        "**Стоимость доставки:**\n"
        "- `courier` — 300 ₽\n"
        "- `cdek` — 250 ₽\n"
        "- `pickup` — бесплатно"
    ),
    responses={
        201: {"description": "Заказ успешно создан"},
        400: {
            "description": "Ошибка при оформлении заказа",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "пустая_корзина": {
                            "summary": "Корзина пуста",
                            "value": {"error": "cart_empty", "message": "Невозможно оформить заказ: корзина пуста"},
                        },
                        "нет_сессии": {
                            "summary": "Не передан заголовок X-Session-Id",
                            "value": {"error": "session_required", "message": "Передайте заголовок X-Session-Id"},
                        },
                        "неверный_промокод": {
                            "summary": "Промокод недействителен",
                            "value": {"error": "promo_invalid", "message": "Промокод не найден"},
                        },
                    }
                }
            },
        },
    },
)
async def create_order(
    body: CreateOrderRequest,
    x_session_id: Optional[str] = Header(
        None,
        alias="X-Session-Id",
        description="Идентификатор сессии корзины. **Обязателен** для оформления заказа",
        example="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    ),
    pool: asyncpg.Pool = Depends(get_pool),
):
    if not x_session_id:
        raise HTTPException(
            status_code=400,
            detail={"error": ErrorCode.SESSION_REQUIRED, "message": "Передайте заголовок X-Session-Id"},
        )

    async with pool.acquire() as conn:
        async with conn.transaction():
            cart_items = await conn.fetch("SELECT * FROM cart_items WHERE session_id = $1", x_session_id)
            if not cart_items:
                raise HTTPException(
                    status_code=400,
                    detail={"error": ErrorCode.CART_EMPTY, "message": "Невозможно оформить заказ: корзина пуста"},
                )

            subtotal          = sum(Decimal(str(i["total_price"])) for i in cart_items)
            promo_id, discount = await apply_promo(conn, body.promo_code, subtotal)
            delivery_cost     = DELIVERY_COSTS[DeliveryType(body.delivery_type)]
            total_amount      = (subtotal - discount + delivery_cost).quantize(Decimal("0.01"))
            order_number      = await generate_order_number(conn)

            customer_row = await conn.fetchrow(
                """
                INSERT INTO customers (email, first_name, last_name, phone)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (email) DO UPDATE
                    SET first_name = EXCLUDED.first_name,
                        last_name  = EXCLUDED.last_name,
                        phone      = COALESCE(EXCLUDED.phone, customers.phone),
                        updated_at = NOW()
                RETURNING id
                """,
                body.email,
                body.first_name,
                body.last_name,
                body.phone,
            )
            customer_id = customer_row["id"]

            order = await conn.fetchrow(
                """
                INSERT INTO orders
                    (order_number, customer_id, status, delivery_type, delivery_city, delivery_street,
                     delivery_zip, promo_code_id, discount_amount, subtotal,
                     delivery_cost, total_amount, payment_method, payment_status)
                VALUES
                    ($1, $2, 'created', $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 'pending')
                RETURNING id, order_number, status, subtotal, discount_amount,
                          delivery_cost, total_amount, payment_method, payment_status
                """,
                order_number,
                customer_id,
                body.delivery_type.value, body.delivery_city, body.delivery_street,
                body.delivery_zip, promo_id, discount, subtotal,
                delivery_cost, total_amount, body.payment_method.value,
            )

            order_id = order["id"]

            await conn.executemany(
                "INSERT INTO order_items (order_id, sku, name, quantity, unit_price, total_price) VALUES ($1,$2,$3,$4,$5,$6)",
                [(order_id, i["sku"], i["name"], i["quantity"], i["unit_price"], i["total_price"]) for i in cart_items],
            )
            await conn.execute(
                "INSERT INTO order_status_history (order_id, new_status, comment) VALUES ($1, 'created', 'Заказ создан')",
                order_id,
            )
            if promo_id:
                await conn.execute("UPDATE promo_codes SET used_count = used_count + 1 WHERE id = $1", promo_id)

            await conn.execute("DELETE FROM cart_items WHERE session_id = $1", x_session_id)

    return {"data": record_to_dict(order), "message": "Заказ создан"}


@router.get(
    "",
    response_model=OrderListResponse,
    summary="История заказов",
    description=(
        "Возвращает список заказов с постраничной навигацией, "
        "отсортированных по дате создания (новые первые). "
        "До добавления авторизации (модуль 5) возвращает все заказы без фильтрации по пользователю."
    ),
    responses={200: {"description": "Список заказов успешно получен"}},
)
async def list_orders(
    status: Optional[OrderStatus] = Query(None, description="Статус заказа для фильтрации", example=OrderStatus.created),
    search: Optional[str] = Query(None, description="Поиск по номеру заказа или email клиента", example="LX-20260412"),
    page:  int = Query(1,  ge=1,         description="Номер страницы (начиная с 1)", example=1),
    limit: int = Query(20, ge=1, le=100, description="Количество заказов на странице (максимум 100)", example=20),
    pool: asyncpg.Pool = Depends(get_pool),
    _: dict = Depends(get_current_admin),
):
    conditions: list[str] = []
    params: list = []

    if status:
        params.append(status.value)
        conditions.append(f"o.status = ${len(params)}")

    if search:
        params.append(f"%{search}%")
        conditions.append(
            f"(o.order_number ILIKE ${len(params)} OR c.email ILIKE ${len(params)} OR c.first_name ILIKE ${len(params)} OR c.last_name ILIKE ${len(params)})"
        )

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    total = await pool.fetchval(
        f"SELECT COUNT(*) FROM orders o LEFT JOIN customers c ON c.id = o.customer_id {where}",
        *params,
    )
    offset = (page - 1) * limit
    params += [limit, offset]

    rows = await pool.fetch(
        f"""
        SELECT o.order_number, o.status, o.total_amount, o.created_at,
               json_build_object(
                   'email', c.email,
                   'first_name', c.first_name,
                   'last_name', c.last_name,
                   'phone', c.phone
               ) AS customer
        FROM orders o
        LEFT JOIN customers c ON c.id = o.customer_id
        {where}
        ORDER BY o.created_at DESC
        LIMIT ${len(params) - 1} OFFSET ${len(params)}
        """,
        *params,
    )

    return {
        "data": [record_to_dict(r) for r in rows],
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": -(-total // limit) if total else 0,
        },
    }


@router.get(
    "/{order_number}",
    response_model=OrderDetailResponse,
    summary="Детали заказа",
    description=(
        "Возвращает полную информацию о заказе: "
        "позиции, адрес доставки, данные об оплате и историю изменений статуса. "
        "Номер заказа имеет формат `LX-YYYYMMDD-NNNN`."
    ),
    responses={
        200: {"description": "Детали заказа получены"},
        404: {
            "description": "Заказ с таким номером не найден",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"error": "order_not_found", "message": "Заказ с указанным номером не найден"}
                }
            },
        },
    },
)
async def get_order(order_number: str, pool: asyncpg.Pool = Depends(get_pool), _: dict = Depends(get_current_admin)):
    row = await pool.fetchrow(
        """
        SELECT o.order_number, o.status, o.delivery_type,
               o.delivery_city, o.delivery_street, o.delivery_zip,
               o.subtotal, o.discount_amount, o.delivery_cost, o.total_amount,
               o.payment_method, o.payment_status, o.tracking_number,
               pc.code AS promo_code, o.customer_id
        FROM orders o
        LEFT JOIN promo_codes pc ON pc.id = o.promo_code_id
        WHERE o.order_number = $1
        """,
        order_number,
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.ORDER_NOT_FOUND, "message": "Заказ с указанным номером не найден"},
        )

    order = record_to_dict(row)
    customer = await pool.fetchrow(
        "SELECT email, first_name, last_name, phone FROM customers WHERE id = $1",
        row["customer_id"],
    )
    order["customer"] = record_to_dict(customer) if customer else {"email": None, "first_name": None, "last_name": None, "phone": None}

    items, history = await asyncio_gather(
        pool.fetch("SELECT sku, name, quantity, unit_price, total_price FROM order_items WHERE order_id = (SELECT id FROM orders WHERE order_number = $1)", order_number),
        pool.fetch("SELECT old_status, new_status AS status, changed_at, comment, changed_by FROM order_status_history WHERE order_id = (SELECT id FROM orders WHERE order_number = $1) ORDER BY changed_at", order_number),
    )

    order["items"] = [record_to_dict(i) for i in items]
    order["status_history"] = [record_to_dict(h) for h in history]
    return {"data": order}


@router.patch(
    "/{order_number}/status",
    response_model=OrderStatusUpdatedResponse,
    summary="Изменить статус заказа",
    description="Обновление статуса заказа администратором с комментарием и трек-номером при необходимости.",
    responses={
        200: {"description": "Статус заказа обновлён"},
        400: {
            "description": "Неверный переход статуса",
            "content": {
                "application/json": {
                    "example": {"error": "invalid_status_transition", "message": "Нельзя перейти из 'created' в 'delivered'"}
                }
            },
        },
        401: {
            "description": "Требуется JWT",
            "content": {
                "application/json": {
                    "example": {"error": "unauthorized", "message": "Требуется JWT"}
                }
            },
        },
        404: {
            "description": "Заказ не найден",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"error": "order_not_found", "message": "Заказ не найден"}
                }
            },
        },
    },
)
async def update_order_status(
    order_number: str,
    body: OrderStatusUpdateRequest,
    pool: asyncpg.Pool = Depends(get_pool),
    admin: dict = Depends(get_current_admin),
):
    row = await pool.fetchrow("SELECT id, status FROM orders WHERE order_number = $1", order_number)
    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": ErrorCode.ORDER_NOT_FOUND, "message": "Заказ не найден"},
        )

    current_status = row["status"]
    if body.status == current_status or body.status not in ALLOWED_STATUS_TRANSITIONS.get(current_status, set()):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_status_transition", "message": f"Нельзя перейти из '{current_status}' в '{body.status}'"},
        )

    await pool.execute(
        "UPDATE orders SET status = $1, tracking_number = $2, operator_comment = $3, updated_at = NOW() WHERE id = $4",
        body.status,
        body.tracking_number,
        body.comment,
        row["id"],
    )

    await pool.execute(
        "INSERT INTO order_status_history (order_id, old_status, new_status, changed_by, comment) VALUES ($1, $2, $3, $4, $5)",
        row["id"],
        current_status,
        body.status,
        admin["email"],
        body.comment,
    )

    changed_at = await pool.fetchval(
        "SELECT changed_at FROM order_status_history WHERE order_id = $1 ORDER BY changed_at DESC LIMIT 1",
        row["id"],
    )

    return {
        "data": {
            "order_number": order_number,
            "status": body.status,
            "tracking_number": body.tracking_number,
            "previous_status": current_status,
            "changed_by": admin["email"],
            "changed_at": changed_at.isoformat() if changed_at else None,
        },
        "message": "Статус обновлён",
    }
