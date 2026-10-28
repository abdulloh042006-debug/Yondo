"""Release time slots of bookings that can no longer happen.

Owner rule (2026-10-23): a reserved slot is released automatically when the booking is
cancelled or its time has run out, and a booking never implies that a payment was made.
A request still `pending` (not accepted) or `accepted` (not paid, so not `confirmed`) when its
start time arrives can no longer take place: it becomes `expired`, which does not reserve the
slot (see the exclusion constraint) and cannot be accepted or paid any more.
Confirmed/active bookings are left to the meeting flow.
"""

from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus

EXPIRABLE_STATUSES = (BookingStatus.PENDING, BookingStatus.ACCEPTED)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def is_stale(booking: Booking, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    return booking.status in EXPIRABLE_STATUSES and _utc(booking.starts_at) <= now


async def refuse_if_expired(session: AsyncSession, booking: Booking) -> None:
    """Before accepting or paying: an overdue booking is expired instead (call refused)."""
    if is_stale(booking):
        booking.status = BookingStatus.EXPIRED
        await session.commit()
        raise ApplicationError('booking_expired', 'The booking start time has passed', 409)


async def expire_stale_bookings(session: AsyncSession, now: datetime | None = None) -> int:
    """Periodic sweep (see yondo_api.jobs). Returns how many bookings were expired."""
    now = now or datetime.now(UTC)
    result = await session.execute(
        update(Booking)
        .where(Booking.status.in_(EXPIRABLE_STATUSES), Booking.starts_at <= now)
        .values(status=BookingStatus.EXPIRED)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return result.rowcount or 0
