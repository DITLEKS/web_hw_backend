from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.enums import ProductStatus


class CategoryOut(BaseModel):
    id:         int    = Field(..., description="Идентификатор категории", example=1)
    slug:       str    = Field(..., description="URL-slug категории",      example="led")
    name:       str    = Field(..., description="Название категории",      example="LED")
    color_hex:  str    = Field(..., description="HEX-цвет категории для отображения в UI", example="#3B82F6")
    sort_order: int    = Field(..., description="Порядок сортировки (меньше — выше)", example=0)


class CategoryListResponse(BaseModel):
    data: list[CategoryOut]


class ProductListItem(BaseModel):
    id:            int            = Field(..., description="Внутренний идентификатор товара", example=1)
    sku:           str            = Field(..., description="Артикул товара. Формат: LX-ТИП-ЦОКОЛЬ-МОЩНОСТЬ", example="LX-LED-E27-9W")
    category:      CategoryOut    = Field(..., description="Категория товара")
    name:          str            = Field(..., description="Название товара", example="Лампа светодиодная груша 9 Вт E27")
    price:         str            = Field(..., description="Текущая цена в рублях", example="89.00")
    old_price:     Optional[str]  = Field(None, description="Старая цена (отображается как зачёркнутая). null если скидки нет", example="120.00")
    stock_quantity: int           = Field(..., description="Остаток на складе в штуках", example=150)
    status:        ProductStatus  = Field(..., description="Статус товара: active / archived / out_of_stock", example=ProductStatus.active)
    primary_image: Optional[str]  = Field(None, description="URL главного изображения товара. null если изображений нет")


class ProductListMeta(BaseModel):
    page:        int = Field(..., description="Текущая страница", example=1)
    limit:       int = Field(..., description="Количество товаров на странице", example=10)
    total:       int = Field(..., description="Общее количество товаров по фильтру", example=42)
    total_pages: int = Field(..., description="Общее количество страниц", example=4)


class ProductListResponse(BaseModel):
    data: list[ProductListItem]
    meta: ProductListMeta


class ProductAttributeOut(BaseModel):
    attr_key:   str           = Field(..., description="Ключ характеристики", example="Мощность")
    attr_value: str           = Field(..., description="Значение характеристики", example="9")
    unit:       Optional[str] = Field(None, description="Единица измерения", example="Вт")


class ProductImageOut(BaseModel):
    id:         int           = Field(..., description="Идентификатор изображения", example=1)
    url:        str           = Field(..., description="URL изображения", example="https://cdn.smartlight.ru/images/lx-led-e27-9w-1.jpg")
    alt_text:   Optional[str] = Field(None, description="Альтернативный текст для SEO и доступности", example="Лампа LED E27 9Вт вид спереди")
    is_primary: bool          = Field(..., description="Главное изображение (отображается первым)", example=True)
    sort_order: int           = Field(..., description="Порядок сортировки изображений", example=0)


class ProductDetail(BaseModel):
    id:             int                      = Field(..., example=1)
    sku:            str                      = Field(..., example="LX-LED-E27-9W")
    category:       CategoryOut
    name:           str                      = Field(..., example="Лампа светодиодная груша 9 Вт E27")
    description:    Optional[str]            = Field(None, description="Подробное описание товара")
    price:          str                      = Field(..., example="89.00")
    old_price:      Optional[str]            = Field(None, example="120.00")
    stock_quantity: int                      = Field(..., example=150)
    status:         ProductStatus            = Field(..., example=ProductStatus.active)
    attributes:     list[ProductAttributeOut] = Field(..., description="Характеристики товара (мощность, цоколь, цветовая температура и т.д.)")
    images:         list[ProductImageOut]    = Field(..., description="Изображения товара (отсортированы по sort_order)")
    created_at:     str                      = Field(..., example="2026-01-15T10:00:00+00:00")
    updated_at:     str                      = Field(..., example="2026-04-12T15:30:00+00:00")


class ProductDetailResponse(BaseModel):
    data: ProductDetail


class ProductCreate(BaseModel):
    sku:            str            = Field(..., description="Уникальный артикул. Формат: LX-ТИП-ЦОКОЛЬ-МОЩНОСТЬ", example="LX-LED-E27-9W", max_length=50)
    category_id:    int            = Field(..., description="ID категории из /api/v1/categories", example=1)
    name:           str            = Field(..., description="Название товара", example="Лампа светодиодная груша 9 Вт E27", max_length=255)
    description:    Optional[str]  = Field(None, description="Подробное описание товара")
    price:          Decimal        = Field(..., description="Цена в рублях (копейки через точку)", example=89.00, gt=0)
    old_price:      Optional[Decimal] = Field(None, description="Старая цена до скидки. Если передана — должна быть больше price", example=120.00, gt=0)
    stock_quantity: int            = Field(0, description="Начальный остаток на складе", example=100, ge=0)

    @field_validator("sku")
    @classmethod
    def validate_sku_format(cls, v: str) -> str:
        parts = v.split("-")
        if len(parts) < 3 or not v.startswith("LX-"):
            raise ValueError("SKU должен иметь формат LX-ТИП-ЦОКОЛЬ[-МОЩНОСТЬ], например: LX-LED-E27-9W")
        return v.upper()

    model_config = {
        "json_schema_extra": {
            "example": {
                "sku": "LX-LED-E27-9W",
                "category_id": 1,
                "name": "Лампа светодиодная груша 9 Вт E27",
                "description": "Энергоэффективная LED-лампа с цоколем E27, мощностью 9 Вт.",
                "price": 89.00,
                "old_price": 120.00,
                "stock_quantity": 100,
            }
        }
    }


class ProductCreatedData(BaseModel):
    id:         int           = Field(..., example=42)
    sku:        str           = Field(..., example="LX-LED-E27-9W")
    status:     ProductStatus = Field(..., example=ProductStatus.active)
    created_at: str           = Field(..., example="2026-04-12T15:00:00+00:00")


class ProductCreatedResponse(BaseModel):
    data:    ProductCreatedData
    message: str = Field(..., example="Товар успешно создан")


class ProductUpdate(BaseModel):
    name:           Optional[str]           = Field(None, description="Новое название товара", example="Лампа LED E27 9Вт обновлённая")
    description:    Optional[str]           = Field(None, description="Новое описание")
    price:          Optional[Decimal]       = Field(None, description="Новая цена в рублях", example=79.00, gt=0)
    old_price:      Optional[Decimal]       = Field(None, description="Новая старая цена (зачёркнутая). Передайте null чтобы убрать", example=89.00)
    stock_quantity: Optional[int]           = Field(None, description="Новый остаток на складе", example=200, ge=0)
    status:         Optional[ProductStatus] = Field(None, description="Новый статус: active / archived / out_of_stock", example=ProductStatus.active)
    category_id:    Optional[int]           = Field(None, description="Новая категория (ID из /api/v1/categories)", example=2)

    model_config = {
        "json_schema_extra": {
            "example": {
                "price": 79.00,
                "stock_quantity": 200,
                "status": "active",
            }
        }
    }


class ProductUpdatedData(BaseModel):
    sku:            str           = Field(..., example="LX-LED-E27-9W")
    price:          str           = Field(..., example="79.00")
    stock_quantity: int           = Field(..., example=200)
    status:         ProductStatus = Field(..., example=ProductStatus.active)
    updated_at:     str           = Field(..., example="2026-04-13T10:00:00+00:00")


class ProductUpdatedResponse(BaseModel):
    data:    ProductUpdatedData
    message: str = Field(..., example="Товар успешно обновлён")


class ValidationDetail(BaseModel):
    field:   str = Field(..., example="price")
    message: str = Field(..., example="Цена должна быть больше 0")


class ValidationErrorResponse(BaseModel):
    error:   str                  = Field(..., example="validation_error")
    details: list[ValidationDetail]


class ErrorResponse(BaseModel):
    error:   str = Field(..., description="Машиночитаемый код ошибки", example="product_not_found")
    message: str = Field(..., description="Человекочитаемое описание ошибки", example="Товар с указанным SKU не найден")
