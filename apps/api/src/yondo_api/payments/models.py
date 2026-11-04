from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class PaymentStatus(StrEnum):
    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'
    PARTIALLY_REFUNDED = 'partially_refunded'


PAID_STATUSES = (
    PaymentStatus.SUCCEEDED,
    PaymentStatus.PARTIALLY_REFUNDED,
    PaymentStatus.REFUNDED,
)


class RefundStatus(StrEnum):
    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'


class PayoutStatus(StrEnum):
    HELD = 'held'
    SCHEDULED = 'scheduled'
    PAID = 'paid'
    CANCELLED = 'cancelled'


_LIVE_BOOKING_PAYMENT = "booking_id IS NOT NULL AND status IN ('pending', 'succeeded')"


class Payment(TimestampMixin, Base):
    __tablename__ = 'payments'
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'cancelled', 'refunded', "
            "'partially_refunded')",
            name='ck_payments_status',
        ),
        CheckConstraint('amount_minor > 0', name='ck_payments_amount'),
        CheckConstraint(
            'refunded_minor >= 0 AND refunded_minor <= amount_minor', name='ck_payments_refunded'
        ),
        UniqueConstraint('payer_id', 'idempotency_key', name='uq_payments_idempotency'),
        UniqueConstraint('provider', 'provider_payment_id', name='uq_payments_provider_id'),
        # At most one live (pending or captured) payment per booking: no duplicate charges.
        Index(
            'uq_payments_live_booking',
            'booking_id',
            unique=True,
            postgresql_where=text(_LIVE_BOOKING_PAYMENT),
            sqlite_where=text(_LIVE_BOOKING_PAYMENT),
        ),
        Index('ix_payments_payer_created', 'payer_id', 'created_at'),
        Index('ix_payments_status', 'status'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payer_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    booking_id: Mapped[UUID | None] = mapped_column(ForeignKey('bookings.id'))
    provider: Mapped[str] = mapped_column(String(32))
    provider_payment_id: Mapped[str | None] = mapped_column(String(128))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default=PaymentStatus.PENDING)
    currency: Mapped[str] = mapped_column(String(3))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    refunded_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    checkout_url: Mapped[str | None] = mapped_column(String(1024))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(String(200))


class Refund(TimestampMixin, Base):
    __tablename__ = 'refunds'
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'succeeded', 'failed')", name='ck_refunds_status'),
        CheckConstraint('amount_minor > 0', name='ck_refunds_amount'),
        Index('ix_refunds_status', 'status'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(ForeignKey('payments.id'), index=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(16), default=RefundStatus.PENDING)
    reason: Mapped[str] = mapped_column(String(64))
    provider_refund_id: Mapped[str | None] = mapped_column(String(128))
    attempts: Mapped[int] = mapped_column(default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Payout(TimestampMixin, Base):
    __tablename__ = 'payouts'
    __table_args__ = (
        CheckConstraint(
            "status IN ('held', 'scheduled', 'paid', 'cancelled')", name='ck_payouts_status'
        ),
        CheckConstraint('amount_minor >= 0', name='ck_payouts_amount'),
        CheckConstraint(
            '(booking_id IS NOT NULL) <> (gift_order_id IS NOT NULL)', name='ck_payouts_source'
        ),
        Index('ix_payouts_beneficiary_status', 'beneficiary_id', 'status'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    beneficiary_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    booking_id: Mapped[UUID | None] = mapped_column(ForeignKey('bookings.id'), unique=True)
    gift_order_id: Mapped[UUID | None] = mapped_column(ForeignKey('gift_orders.id'), unique=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(16), default=PayoutStatus.HELD)
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    reference: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)


class PaymentEvent(Base):
    """Provider callbacks, deduplicated by provider event id (webhook idempotency)."""

    __tablename__ = 'payment_events'
    __table_args__ = (
        UniqueConstraint('provider', 'event_id', name='uq_payment_events_provider_event'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(32))
    event_id: Mapped[str] = mapped_column(String(128))
    payment_id: Mapped[UUID | None] = mapped_column(ForeignKey('payments.id'))
    outcome: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
