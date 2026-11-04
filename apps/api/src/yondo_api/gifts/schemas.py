from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from yondo_api.core.schemas import Input, MinorAmount, Output, UtcDatetime

Category = Literal['flowers', 'chocolate', 'gift_box', 'toys', 'birthday', 'romantic', 'custom']


# --- Vendor panel --------------------------------------------------------------------------


class VendorWrite(Input):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default='', max_length=4000)
    city: str = Field(min_length=1, max_length=128)
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    delivery_fee_minor: MinorAmount = 0
    delivery_time_minutes: int = Field(default=120, gt=0, le=7 * 24 * 60)


class VendorResponse(Output):
    id: UUID
    user_id: UUID
    name: str
    description: str
    city: str
    status: str
    currency: str
    delivery_fee_minor: int
    delivery_time_minutes: int
    review_note: str | None
    created_at: UtcDatetime


class ProductWrite(Input):
    category: Category
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=4000)
    price_minor: int = Field(strict=True, gt=0, le=9_223_372_036_854_775_807)
    stock: int = Field(strict=True, ge=0, le=1_000_000)
    is_active: bool = True
    delivery_time_minutes: int | None = Field(default=None, gt=0, le=7 * 24 * 60)


class StockUpdate(Input):
    stock: int = Field(strict=True, ge=0, le=1_000_000)


class ImageView(Output):
    id: UUID
    url: str | None
    width: int
    height: int


class VendorProduct(Output):
    id: UUID
    category: str
    name: str
    description: str
    price_minor: int
    currency: str
    stock: int
    is_active: bool
    hidden_by_admin: bool
    hidden_reason: str | None
    delivery_time_minutes: int | None
    images: list[ImageView] = []


class OrderStatusUpdate(Input):
    status: Literal[
        'accepted', 'preparing', 'courier_assigned', 'delivering', 'delivered', 'cancelled'
    ]
    note: str = Field(default='', max_length=500)


# --- Catalog -------------------------------------------------------------------------------


class ProductCard(Output):
    id: UUID
    category: str
    name: str
    price_minor: int
    currency: str
    vendor_id: UUID
    vendor_name: str
    image: ImageView | None
    rating_average: float | None
    rating_count: int
    delivery_time_minutes: int
    in_stock: bool
    is_favorite: bool


class ProductPage(ProductCard):
    description: str
    images: list[ImageView]
    stock: int
    vendor_city: str
    delivery_fee_minor: int


class CatalogPage(Output):
    items: list[ProductCard]
    total: int
    next_offset: int | None


class CategoryCount(Output):
    category: str
    products: int


class CartLine(Input):
    quantity: int = Field(strict=True, gt=0, le=100)
    note: str = Field(default='', max_length=500)


class CartItemView(Output):
    product: ProductCard
    quantity: int
    note: str
    line_total_minor: int


class CartView(Output):
    items: list[CartItemView]
    currency: str | None
    subtotal_minor: int


# --- Checkout & orders ---------------------------------------------------------------------


class GiftLine(Input):
    product_id: UUID
    quantity: int = Field(strict=True, gt=0, le=100)
    note: str = Field(default='', max_length=500)


class Delivery(Input):
    recipient_name: str = Field(min_length=1, max_length=128)
    recipient_phone: str = Field(min_length=9, max_length=32)
    address: str = Field(min_length=1, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    delivery_at: AwareDatetime
    note: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def paired(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('latitude and longitude must be provided together')
        return self


class GiftCheckout(Input):
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r'^[A-Za-z0-9_.:-]+$')
    # Omit to check out the whole cart.
    items: list[GiftLine] | None = Field(default=None, min_length=1, max_length=50)
    delivery: Delivery


class BookingGifts(Input):
    """Gifts delivered to the meeting place at the start time (Booking + Gift, Phase 16)."""

    items: list[GiftLine] = Field(min_length=1, max_length=20)
    recipient_name: str | None = Field(default=None, max_length=128)
    note: str = Field(default='', max_length=1000)


class OrderItemView(Output):
    product_id: UUID | None
    product_name: str
    unit_price_minor: int
    quantity: int
    note: str


class GiftOrderView(Output):
    id: UUID
    customer_id: UUID
    vendor_id: UUID
    vendor_name: str | None = None
    booking_id: UUID | None
    payment_id: UUID | None
    status: str
    recipient_name: str
    recipient_phone: str
    delivery_address: str
    delivery_latitude: float | None
    delivery_longitude: float | None
    delivery_at: UtcDatetime
    note: str
    currency: str
    subtotal_minor: int
    delivery_fee_minor: int
    platform_fee_minor: int
    total_minor: int
    cancelled_reason: str | None
    delivered_at: UtcDatetime | None
    created_at: UtcDatetime
    items: list[OrderItemView] = []


class GiftReviewCreate(Input):
    rating: int = Field(strict=True, ge=1, le=5)
    text: str = Field(default='', max_length=2000)


class GiftReviewView(Output):
    id: UUID
    order_id: UUID
    rating: int
    text: str
    created_at: UtcDatetime


class VendorRatings(Output):
    rating_average: float | None
    rating_count: int
    reviews: list[GiftReviewView]
