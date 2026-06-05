from decimal import Decimal
from app.enums import DeliveryType


class ErrorCode:
    VALIDATION_ERROR    = "validation_error"
    CART_EMPTY          = "cart_empty"
    PROMO_INVALID       = "promo_invalid"
    ORDER_NOT_FOUND     = "order_not_found"
    ITEM_NOT_FOUND      = "item_not_found"
    PRODUCT_NOT_FOUND   = "product_not_found"
    INSUFFICIENT_STOCK  = "insufficient_stock"
    SESSION_REQUIRED    = "session_required"
    CATALOG_UNAVAILABLE = "catalog_unavailable"


DELIVERY_COSTS: dict[DeliveryType, Decimal] = {
    DeliveryType.courier: Decimal("300.00"),
    DeliveryType.cdek:    Decimal("250.00"),
    DeliveryType.pickup:  Decimal("0.00"),
}


ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "created":     {"confirmed", "cancelled"},
    "confirmed":   {"in_assembly", "cancelled"},
    "in_assembly": {"shipped", "cancelled"},
    "shipped":     {"delivered", "cancelled"},
    "delivered":   set(),
    "cancelled":   set(),
}
