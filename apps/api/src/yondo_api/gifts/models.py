from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin

# TZ §28 categories.
CATEGORIES = ('flowers', 'chocolate', 'gift_box', 'toys', 'birthday', 'romantic', 'custom')


class VendorStatus(StrEnum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    SUSPENDED = 'suspended'


class GiftOrderStatus(StrEnum):
    # Internal pre-payment state; vendors only see orders from ``new`` onwards.
    PENDING_PAYMENT = 'pending_payment'
    NEW = 'new'
    ACCEPTED = 'accepted'
    PREPARING = 'preparing'
    COURIER_ASSIGNED = 'courier_assigned'
    DELIVERING = 'delivering'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'


# TZ §31 vendor-driven status progression.
NEXT_STATUS = {
    GiftOrderStatus.NEW: GiftOrderStatus.ACCEPTED,
    GiftOrderStatus.ACCEPTED: GiftOrderStatus.PREPARING,
    GiftOrderStatus.PREPARING: GiftOrderStatus.COURIER_ASSIGNED,
    GiftOrderStatus.COURIER_ASSIGNED: GiftOrderStatus.DELIVERING,
    GiftOrderStatus.DELIVERING: GiftOrderStatus.DELIVERED,
}
REFUNDABLE_ON_CANCEL = (GiftOrderStatus.NEW, GiftOrderStatus.ACCEPTED)


class Vendor(TimestampMixin, Base):
    __tablename__ = 'vendors'
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'suspended')", name='ck_vendors_status'
        ),
        CheckConstraint('delivery_fee_minor >= 0', name='ck_vendors_delivery_fee'),
        CheckConstraint('length(currency) = 3', name='ck_vendors_currency'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default='')
    city: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default=VendorStatus.PENDING)
    currency: Mapped[str] = mapped_column(String(3))
    delivery_fee_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    delivery_time_minutes: Mapped[int] = mapped_column(Integer, default=120)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Product(TimestampMixin, Base):
    __tablename__ = 'products'
    __table_args__ = (
        CheckConstraint(
            "category IN ('flowers', 'chocolate', 'gift_box', 'toys', 'birthday', 'romantic', "
            "'custom')",
            name='ck_products_category',
        ),
        CheckConstraint('price_minor > 0', name='ck_products_price'),
        CheckConstraint('stock >= 0', name='ck_products_stock'),
        Index('ix_products_vendor', 'vendor_id'),
        Index('ix_products_category_active', 'category', 'is_active'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    vendor_id: Mapped[UUID] = mapped_column(ForeignKey('vendors.id', ondelete='CASCADE'))
    category: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default='')
    price_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    hidden_by_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden_reason: Mapped[str | None] = mapped_column(Text)
    delivery_time_minutes: Mapped[int | None] = mapped_column(Integer)


class ProductImage(Base):
    __tablename__ = 'product_images'
    __table_args__ = (UniqueConstraint('product_id', 'position', name='uq_product_image_position'),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey('products.id', ondelete='CASCADE'), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    position: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CartItem(TimestampMixin, Base):
    __tablename__ = 'cart_items'
    __table_args__ = (CheckConstraint('quantity > 0', name='ck_cart_items_quantity'),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), primary_key=True
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey('products.id', ondelete='CASCADE'), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(String(500), default='')


class FavoriteProduct(Base):
    __tablename__ = 'favorite_products'

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), primary_key=True
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey('products.id', ondelete='CASCADE'), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GiftOrder(TimestampMixin, Base):
    __tablename__ = 'gift_orders'
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_payment', 'new', 'accepted', 'preparing', 'courier_assigned', "
            "'delivering', 'delivered', 'cancelled')",
            name='ck_gift_orders_status',
        ),
        CheckConstraint(
            'subtotal_minor > 0 AND delivery_fee_minor >= 0 AND platform_fee_minor >= 0 '
            'AND total_minor = subtotal_minor + delivery_fee_minor + platform_fee_minor',
            name='ck_gift_orders_amounts',
        ),
        Index('ix_gift_orders_vendor_status', 'vendor_id', 'status'),
        Index('ix_gift_orders_customer_created', 'customer_id', 'created_at'),
        Index('ix_gift_orders_payment', 'payment_id'),
        Index('ix_gift_orders_booking', 'booking_id'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    vendor_id: Mapped[UUID] = mapped_column(ForeignKey('vendors.id'))
    booking_id: Mapped[UUID | None] = mapped_column(ForeignKey('bookings.id'))
    payment_id: Mapped[UUID | None] = mapped_column(ForeignKey('payments.id'))
    status: Mapped[str] = mapped_column(String(24), default=GiftOrderStatus.PENDING_PAYMENT)
    recipient_name: Mapped[str] = mapped_column(String(128))
    recipient_phone: Mapped[str] = mapped_column(String(32))
    delivery_address: Mapped[str] = mapped_column(String(500))
    delivery_latitude: Mapped[float | None] = mapped_column(Float)
    delivery_longitude: Mapped[float | None] = mapped_column(Float)
    delivery_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(Text, default='')
    currency: Mapped[str] = mapped_column(String(3))
    subtotal_minor: Mapped[int] = mapped_column(BigInteger)
    delivery_fee_minor: Mapped[int] = mapped_column(BigInteger)
    platform_fee_minor: Mapped[int] = mapped_column(BigInteger)
    total_minor: Mapped[int] = mapped_column(BigInteger)
    cancelled_reason: Mapped[str | None] = mapped_column(String(64))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GiftOrderItem(Base):
    __tablename__ = 'gift_order_items'
    __table_args__ = (CheckConstraint('quantity > 0', name='ck_gift_order_items_quantity'),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey('gift_orders.id', ondelete='CASCADE'), index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey('products.id', ondelete='SET NULL'))
    product_name: Mapped[str] = mapped_column(String(200))
    unit_price_minor: Mapped[int] = mapped_column(BigInteger)
    quantity: Mapped[int] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(String(500), default='')


class GiftReview(TimestampMixin, Base):
    __tablename__ = 'gift_reviews'
    __table_args__ = (
        CheckConstraint('rating BETWEEN 1 AND 5', name='ck_gift_reviews_rating'),
        Index('ix_gift_reviews_vendor', 'vendor_id'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey('gift_orders.id', ondelete='CASCADE'), unique=True
    )
    customer_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    vendor_id: Mapped[UUID] = mapped_column(ForeignKey('vendors.id'))
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, default='')
