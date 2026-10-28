"""Offline demo gift orders, reserved inventory and manual operator fulfillment.

These tables never represent a real captured CLICK transaction.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class GiftTestStatus(StrEnum):
    AWAITING_TEST_PAYMENT = 'awaiting_test_payment'
    TEST_PAID = 'test_paid'
    PREPARING = 'preparing'
    OUT_FOR_DELIVERY = 'out_for_delivery'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'


class GiftTestOrder(TimestampMixin, Base):
    __tablename__ = 'gift_test_orders'
    __table_args__ = (
        CheckConstraint(
            "status IN ('awaiting_test_payment','test_paid','preparing',"
            "'out_for_delivery','delivered','cancelled')",
            name='ck_gift_test_order_status',
        ),
        CheckConstraint(
            "delivery_method IN ('pickup','manual_delivery')",
            name='ck_gift_test_delivery_method',
        ),
        CheckConstraint('subtotal_minor >= 0', name='ck_gift_test_order_amount'),
        UniqueConstraint('click_trans_id', name='uq_gift_test_click_trans'),
        Index('ix_gift_test_order_customer', 'customer_id', 'created_at'),
        Index('ix_gift_test_order_status', 'status', 'created_at'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='RESTRICT'), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default=GiftTestStatus.AWAITING_TEST_PAYMENT, nullable=False
    )
    subtotal_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default='UZS', nullable=False)
    delivery_method: Mapped[str] = mapped_column(String(24), nullable=False)
    delivery_note: Mapped[str | None] = mapped_column(Text)
    click_trans_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    test_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_changed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey('users.id', ondelete='RESTRICT'), nullable=True
    )


class GiftTestOrderItem(TimestampMixin, Base):
    __tablename__ = 'gift_test_order_items'
    __table_args__ = (
        UniqueConstraint('order_id', 'product_id', name='uq_gift_test_order_product'),
        CheckConstraint('quantity BETWEEN 1 AND 100', name='ck_gift_test_order_item_quantity'),
        CheckConstraint(
            'unit_price_minor >= 0 AND line_total_minor >= 0',
            name='ck_gift_test_order_item_amounts',
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey('gift_test_orders.id', ondelete='RESTRICT'), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey('gift_products.id', ondelete='RESTRICT'), nullable=False
    )
    name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
