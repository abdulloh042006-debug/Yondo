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
    from yondo_api.reviews.models import ReviewDirection
    from yondo_api.reviews.service import completed_counts, rating_summary

    ids = list(set(companion_user_ids))
    ratings = await rating_summary(session, ids, ReviewDirection.FOR_COMPANION)
    completed = await completed_counts(session, ids)
    return {
        user_id: CompanionStats(
            rating_average=ratings.get(user_id, (None, 0))[0],
            rating_count=ratings.get(user_id, (None, 0))[1],
            completed_bookings=completed.get(user_id, 0),
        )
        for user_id in ids
    }


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
