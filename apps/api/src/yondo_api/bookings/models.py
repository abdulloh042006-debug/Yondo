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
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    column,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class BookingStatus(StrEnum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    CONFIRMED = 'confirmed'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    NO_SHOW = 'no_show'
    DISPUTED = 'disputed'


# Statuses that reserve the companion's (and customer's) time.
HELD_STATUSES = (BookingStatus.ACCEPTED, BookingStatus.CONFIRMED, BookingStatus.ACTIVE)
_HELD_SQL = "status IN ('accepted', 'confirmed', 'active')"
_STATUS_SQL = (
    "status IN ('pending', 'accepted', 'confirmed', 'active', 'completed', 'cancelled', "
    "'no_show', 'disputed')"
)


class CancellationReason(StrEnum):
    CUSTOMER = 'customer_cancelled'
    COMPANION = 'companion_cancelled'
    DECLINED = 'declined'
    REQUEST_EXPIRED = 'request_expired'
    PAYMENT_EXPIRED = 'payment_expired'
    ADMIN = 'admin_cancelled'


def _no_overlap(name: str, party: str) -> ExcludeConstraint:
    return ExcludeConstraint(
        (party, '='),
        (func.tstzrange(column('starts_at'), column('ends_at'), '[)'), '&&'),
        name=name,
        using='gist',
        where=text(_HELD_SQL),
    ).ddl_if(dialect='postgresql')


class Booking(TimestampMixin, Base):
    __tablename__ = 'bookings'
    __table_args__ = (
        CheckConstraint(_STATUS_SQL, name='ck_bookings_status'),
        CheckConstraint('ends_at > starts_at', name='ck_bookings_interval'),
        CheckConstraint('duration_minutes > 0', name='ck_bookings_duration'),
        CheckConstraint('customer_id <> companion_id', name='ck_bookings_distinct_parties'),
        CheckConstraint(
            'service_amount_minor >= 0 AND platform_fee_minor >= 0 AND total_minor >= 0 '
            'AND companion_payout_minor >= 0 AND refund_minor >= 0',
            name='ck_bookings_amounts',
        ),
        Index('ix_bookings_customer_start', 'customer_id', 'starts_at'),
        Index('ix_bookings_companion_start', 'companion_id', 'starts_at'),
        Index('ix_bookings_status', 'status'),
        # Database-level double-booking protection for held reservations.
        _no_overlap('ex_bookings_companion_overlap', 'companion_id'),
        _no_overlap('ex_bookings_customer_overlap', 'customer_id'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    companion_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    profile_id: Mapped[UUID] = mapped_column(ForeignKey('companion_profiles.id'))
    service_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('companion_services.id', ondelete='SET NULL')
    )
    rebooked_from_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('bookings.id', ondelete='SET NULL')
    )
    status: Mapped[str] = mapped_column(String(16), default=BookingStatus.PENDING)

    service_code: Mapped[str] = mapped_column(String(64))
    unit_price_minor: Mapped[int] = mapped_column(BigInteger)
    unit_minutes: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    timezone: Mapped[str] = mapped_column(String(64))

    meeting_place_name: Mapped[str] = mapped_column(String(200))
    meeting_address: Mapped[str] = mapped_column(String(500), default='')
    meeting_latitude: Mapped[float | None] = mapped_column(Float)
    meeting_longitude: Mapped[float | None] = mapped_column(Float)
    customer_note: Mapped[str] = mapped_column(Text, default='')

    service_amount_minor: Mapped[int] = mapped_column(BigInteger)
    platform_fee_minor: Mapped[int] = mapped_column(BigInteger)
    total_minor: Mapped[int] = mapped_column(BigInteger)
    companion_payout_minor: Mapped[int] = mapped_column(BigInteger)
    refund_minor: Mapped[int] = mapped_column(BigInteger, default=0)

    contract: Mapped[dict[str, Any]] = mapped_column(JSON)
    contract_version: Mapped[str] = mapped_column(String(64))
    customer_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    companion_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payment_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    cancellation_reason: Mapped[str | None] = mapped_column(String(32))
    cancellation_note: Mapped[str | None] = mapped_column(Text)

    # Meeting flow (Phase 11).
    customer_checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    companion_checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    no_show_reported_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    no_show_party: Mapped[str | None] = mapped_column(String(16))


class BookingEvent(Base):
    """Append-only audit trail of booking state changes."""

    __tablename__ = 'booking_events'
    __table_args__ = (Index('ix_booking_events_booking_created', 'booking_id', 'created_at'),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id', ondelete='CASCADE'))
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    event: Mapped[str] = mapped_column(String(64))
    from_status: Mapped[str | None] = mapped_column(String(16))
    to_status: Mapped[str] = mapped_column(String(16))
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
