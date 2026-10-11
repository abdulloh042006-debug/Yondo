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
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class PaymentStatus(StrEnum):
    CREATING = 'creating'
    PENDING = 'pending'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'


class Payment(TimestampMixin, Base):
    __tablename__ = 'payments'
    __table_args__ = (
        CheckConstraint(
            "status IN ('creating', 'pending', 'succeeded', 'failed')",
            name='ck_payment_status',
        ),
        CheckConstraint(
            'subtotal_minor >= 0 AND platform_fee_minor >= 0 AND amount_minor >= 0',
            name='ck_payment_amounts',
        ),
        UniqueConstraint('customer_id', 'idempotency_key', name='uq_payment_idempotency'),
        Index(
            'uq_successful_payment_per_booking',
            'booking_id',
            unique=True,
            postgresql_where=text("status = 'succeeded'"),
            sqlite_where=text("status = 'succeeded'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        ForeignKey('bookings.id', ondelete='RESTRICT'), index=True
    )
    customer_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    provider_reference: Mapped[str | None] = mapped_column(String(256), unique=True)
    status: Mapped[str] = mapped_column(String(16), default=PaymentStatus.CREATING)
    subtotal_minor: Mapped[int] = mapped_column(BigInteger)
    platform_fee_minor: Mapped[int] = mapped_column(BigInteger)
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    checkout_url: Mapped[str | None] = mapped_column(String(2048))
    refund_required: Mapped[bool] = mapped_column(default=False, server_default='false')


class PaymentEventReceipt(TimestampMixin, Base):
    __tablename__ = 'payment_event_receipts'
    __table_args__ = (UniqueConstraint('provider_event_id', name='uq_payment_provider_event'),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(ForeignKey('payments.id', ondelete='RESTRICT'))
    provider_event_id: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32))


class CompanionPayout(TimestampMixin, Base):
    __tablename__ = 'companion_payouts'
    __table_args__ = (
        CheckConstraint('amount_minor >= 0', name='ck_companion_payout_amount'),
        CheckConstraint("status IN ('held', 'ready', 'paid')", name='ck_companion_payout_status'),
        UniqueConstraint('booking_id', name='uq_companion_payout_booking'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id', ondelete='RESTRICT'))
    companion_user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(16), default='held')
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
