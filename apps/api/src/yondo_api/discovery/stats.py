"""Public trust statistics and badges for companion cards (TZ §14)."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.discovery.schemas import CompanionStats

# PLACEHOLDER thresholds pending product approval of the trust model.
NEW_COMPANION_COMPLETED_BOOKINGS = 3
TRUSTED_MIN_COMPLETED_BOOKINGS = 10
TRUSTED_MIN_RATING = 4.5


async def companion_stats(
    session: AsyncSession, companion_user_ids: Iterable[UUID]
) -> dict[UUID, CompanionStats]:
    return {user_id: CompanionStats() for user_id in companion_user_ids}


def badges_for(stats: CompanionStats) -> list[str]:
    # Every publicly listed companion passed the identity gate.
    badges = ['verified']
    if stats.completed_bookings < NEW_COMPANION_COMPLETED_BOOKINGS:
        badges.append('new')
    if (
        stats.completed_bookings >= TRUSTED_MIN_COMPLETED_BOOKINGS
        and stats.rating_average is not None
        and stats.rating_average >= TRUSTED_MIN_RATING
    ):
        badges.append('trusted')
    return badges
