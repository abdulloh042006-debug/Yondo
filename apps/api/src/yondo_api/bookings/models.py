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
    NO_SHOW = 'no-show'
    DISPUTED = 'disputed'


class Booking(TimestampMixin, Base):
    __tablename__ = 'bookings'
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'confirmed', 'active', 'completed', "
            "'cancelled', 'no-show', 'disputed')",
            name='ck_booking_status',
        ),
        CheckConstraint('ends_at > starts_at', name='ck_booking_interval'),
        CheckConstraint('duration_minutes > 0', name='ck_booking_duration'),
        CheckConstraint('price_minor >= 0', name='ck_booking_price'),
        Index('ix_bookings_customer_created', 'customer_id', 'created_at'),
        Index('ix_bookings_profile_start', 'profile_id', 'starts_at'),
        ExcludeConstraint(
            ('profile_id', '='),
            (func.tstzrange(column('starts_at'), column('ends_at'), '[)'), '&&'),
            where=text("status IN ('pending', 'accepted', 'confirmed', 'active')"),
            name='ex_booking_active_overlap',
            using='gist',
        ).ddl_if(dialect='postgresql'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey('companion_profiles.id', ondelete='RESTRICT')
    )
    service_id: Mapped[UUID] = mapped_column(
        ForeignKey('companion_services.id', ondelete='RESTRICT')
    )
    status: Mapped[str] = mapped_column(String(16), default=BookingStatus.PENDING)
    service_code: Mapped[str] = mapped_column(String(64))
    service_description: Mapped[str] = mapped_column(Text)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64))
    duration_minutes: Mapped[int] = mapped_column()
    meeting_place: Mapped[str] = mapped_column(String(512))
    price_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    customer_contract_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    companion_contract_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
