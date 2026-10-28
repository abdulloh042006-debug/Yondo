"""Release time slots of bookings that can no longer happen.

Owner rule (2026-10-23): a reserved slot is released automatically when the booking is
cancelled or its time has run out, and a booking never implies that a payment was made.
A request still `pending` (not accepted) or `accepted` (not paid, so not `confirmed`) when its
start time arrives can no longer take place: it becomes `expired`, which does not reserve the
slot (see the exclusion constraint) and cannot be accepted or paid any more.
Confirmed/active bookings are left to the meeting flow.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.cancellations.service import record_expiry
from yondo_api.config import get_settings

EXPIRABLE_STATUSES = (BookingStatus.PENDING, BookingStatus.ACCEPTED)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def is_stale(booking: Booking, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    return booking.status in EXPIRABLE_STATUSES and _utc(booking.starts_at) <= now


async def refuse_if_expired(session: AsyncSession, booking: Booking) -> None:
    """Before accepting or paying: an overdue booking is expired instead (call refused)."""
    if is_stale(booking):
        previous = booking.status
        booking.status = BookingStatus.EXPIRED
        await record_expiry(session, get_settings(), booking, previous)
        await session.commit()
        raise ApplicationError('booking_expired', 'The booking start time has passed', 409)


async def expire_stale_bookings(session: AsyncSession, now: datetime | None = None) -> int:
    """Periodic sweep (see yondo_api.jobs). Returns how many bookings were expired."""
    now = now or datetime.now(UTC)
    # Row locks (skip_locked) keep the sweep away from a booking a user is changing right now.
    stale = list(
        await session.scalars(
            select(Booking)
            .where(Booking.status.in_(EXPIRABLE_STATUSES), Booking.starts_at <= now)
            .with_for_update(skip_locked=True)
        )
    )
    settings = get_settings()
    for booking in stale:
        previous = booking.status
        booking.status = BookingStatus.EXPIRED
        await record_expiry(session, settings, booking, previous, now=now)
    await session.commit()
    return len(stale)
