from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_http_client, create_pool
from app.routers import auth, cart, dashboard, orders


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool()
    app.state.http = create_http_client()
    yield
    await app.state.pool.close()
    await app.state.http.aclose()


tags_metadata = [
    {
        "name": "Корзина",
        "description": (
            "Управление корзиной покупателя.\n\n"
            "Корзина идентифицируется по заголовку **`X-Session-Id`** (UUID). "
            "Если заголовок не передан — сервер создаёт новую сессию автоматически "
            "и возвращает её идентификатор в заголовке ответа `X-Session-Id`. "
            "Сохраняйте этот идентификатор для последующих запросов.\n\n"
            "Данные корзины хранятся в таблице `cart_items`. "
            "После оформления заказа корзина очищается автоматически."
        ),
    },
    {
        "name": "Заказы",
        "description": (
            "Оформление заказов и просмотр истории.\n\n"
            "**Формат номера заказа:** `LX-YYYYMMDD-NNNN`\n\n"
            "**Жизненный цикл статусов:**\n"
            "`created` → `confirmed` → `in_assembly` → `shipped` → `delivered` / `cancelled`\n\n"
            "**Стоимость доставки:**\n"
            "| Тип | Стоимость |\n"
            "|---|---|\n"
            "| `courier` — курьерская | 300 ₽ |\n"
            "| `cdek` — доставка СДЭК | 250 ₽ |\n"
            "| `pickup` — самовывоз | бесплатно |"
        ),
    },
    {
        "name": "Служебные",
        "description": "Проверка работоспособности сервиса.",
    },
]

app = FastAPI(
    title="SmartLight — Сервис управления заказами",
    description=(
        "## Микросервис обработки заказов\n\n"
        "Управляет корзиной покупателя и оформлением заказов. "
        "Для проверки актуальных цен и остатков обращается в **catalog-service**.\n\n"
        "### Базовый URL\n"
        "- Docker: `http://orders-service:3002`\n"
        "- Локально: `http://localhost:3002`\n\n"
    ),
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact={"name": "SmartLight Dev Team"},
    license_info={"name": "Proprietary"},
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content={"error": "server_error", "message": str(detail)})



app.include_router(auth.router,      prefix="/api/v1/auth",      tags=["Авторизация"])
app.include_router(dashboard.router, prefix="/api/v1",         tags=["Dashboard"])
app.include_router(cart.router,      prefix="/api/v1/cart",     tags=["Корзина"])
app.include_router(orders.router,    prefix="/api/v1/orders",   tags=["Заказы"])


@app.get("/health", tags=["Служебные"], summary="Проверка работоспособности сервиса")
async def health():
    """Возвращает статус `ok` если сервис запущен. Используется Docker healthcheck."""
    return {"status": "ok", "service": "orders-service"}
