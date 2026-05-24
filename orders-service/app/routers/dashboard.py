from fastapi import APIRouter, Depends
from app.database import get_pool, get_http
from app.core.config import settings
from app.schemas import DashboardResponse
from shared.auth import create_admin_dependency
from shared.utils import record_to_dict

router = APIRouter()
get_current_admin = create_admin_dependency(settings.jwt_secret_key, settings.jwt_algorithm)


@router.get("", response_model=DashboardResponse, summary="Dashboard", description="Статистика и предупреждения по магазинам.",)
async def dashboard(
    pool=Depends(get_pool),
    http=Depends(get_http),
    _: dict = Depends(get_current_admin),
):
    today_orders_count = await pool.fetchval(
        "SELECT COUNT(*) FROM orders WHERE created_at >= CURRENT_DATE"
    )
    revenue = await pool.fetchval(
        "SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE created_at >= CURRENT_DATE"
    )
    new_customers = await pool.fetchval(
        "SELECT COUNT(*) FROM customers WHERE created_at >= CURRENT_DATE"
    )

    recent_orders_rows = await pool.fetch(
        """
        SELECT o.order_number, o.total_amount, o.status, c.email AS customer_email
        FROM orders o
        LEFT JOIN customers c ON c.id = o.customer_id
        ORDER BY o.created_at DESC
        LIMIT 5
        """
    )

    low_stock = []
    try:
        response = await http.get("/api/v1/products", params={"status": "active", "limit": 100})
        response.raise_for_status()
        products = response.json().get("data", [])
        low_stock = [
            {
                "sku": item["sku"],
                "name": item["name"],
                "stock_quantity": item["stock_quantity"],
            }
            for item in products
            if item.get("stock_quantity") is not None and item["stock_quantity"] <= 5
        ][:10]
    except Exception:
        low_stock = []

    return {
        "data": {
            "today": {
                "orders_count": today_orders_count,
                "revenue": str(revenue or 0),
                "new_customers": new_customers,
            },
            "recent_orders": [record_to_dict(r) for r in recent_orders_rows],
            "low_stock": low_stock,
        }
    }
