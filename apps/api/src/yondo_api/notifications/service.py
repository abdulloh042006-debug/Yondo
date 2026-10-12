"""Durable in-app notifications committed with the triggering transaction."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.bookings.models import Booking
from yondo_api.companions.models import CompanionApplication, CompanionProfile
from yondo_api.notifications.models import UserNotification


async def enqueue_booking_notice(
    session: AsyncSession,
    booking: Booking,
    kind: str,
    source_id: UUID,
    *,
    actor_id: UUID | None = None,
    recipients: str = 'other',
) -> None:
    companion_id = await session.scalar(
        select(CompanionApplication.user_id)
        .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
        .where(CompanionProfile.id == booking.profile_id)
    )
    for recipient_id in {booking.customer_id, companion_id} - {None}:
        if recipients == 'other' and recipient_id == actor_id:
            continue
        session.add(UserNotification(
            recipient_id=recipient_id,
            actor_id=actor_id,
            booking_id=booking.id,
            kind=kind,
            source_key=f'{kind}:{source_id}',
            details={'booking_id': str(booking.id)},
        ))
