"""Booking spam guards: per-customer request rate and open-request caps (no Redis needed).

Counts are read from the bookings table, so they survive restarts and hold across instances.
They are soft limits (two simultaneous requests may overshoot by one); the hard guard against a
double-booked slot stays the overlap check plus the PostgreSQL exclusion constraint.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.cancellations.service import utcnow
from yondo_api.config import Settings

OPEN_STATUSES = (BookingStatus.PENDING, BookingStatus.ACCEPTED)


class BookingRateLimiter(Protocol):
    """Injected like the OTP limiter (`app.state.booking_rate_limiter`); tests may replace it."""

    async def check(self, session: AsyncSession, user_id: UUID, *, limit_per_hour: int) -> None: ...


class DatabaseBookingRateLimiter:
    async def check(self, session: AsyncSession, user_id: UUID, *, limit_per_hour: int) -> None:
        if limit_per_hour <= 0:
            return
        created = await session.scalar(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.customer_id == user_id,
                Booking.created_at >= utcnow() - timedelta(hours=1),
            )
        )
        if (created or 0) >= limit_per_hour:
            raise ApplicationError(
                'booking_rate_limited', 'Too many booking requests; try again later', 429
            )


async def enforce_open_request_limits(
    session: AsyncSession, settings: Settings, customer_id: UUID, profile_id: UUID
) -> None:
    """Requests still waiting (pending/accepted, start in the future): overall and per companion."""
    overall = settings.booking_open_requests_limit
    per_companion = settings.booking_open_requests_per_companion_limit
    if not overall and not per_companion:
        return
    rows = (
        await session.execute(
            select(Booking.profile_id).where(
                Booking.customer_id == customer_id,
                Booking.status.in_(OPEN_STATUSES),
                Booking.starts_at > utcnow(),
            )
        )
    ).scalars().all()
    if overall and len(rows) >= overall:
        raise ApplicationError(
            'booking_open_limit_reached', 'Too many unanswered booking requests', 409
        )
    if per_companion and sum(1 for pid in rows if pid == profile_id) >= per_companion:
        raise ApplicationError(
            'booking_open_limit_per_companion_reached',
            'Too many unanswered requests to this companion',
            409,
        )
