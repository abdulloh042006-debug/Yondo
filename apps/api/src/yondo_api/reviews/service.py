from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings import service as bookings
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.config import Settings
from yondo_api.core.db import commit
from yondo_api.core.time import as_utc, utc_now
from yondo_api.models.user import User
from yondo_api.notifications.service import notify
from yondo_api.reviews.models import CRITERIA, Review, ReviewDirection


async def rating_summary(
    session: AsyncSession, user_ids: Iterable[UUID], direction: ReviewDirection
) -> dict[UUID, tuple[float | None, int]]:
    ids = list(set(user_ids))
    if not ids:
        return {}
    rows = await session.execute(
        select(Review.subject_id, func.avg(Review.rating), func.count())
        .where(
            Review.subject_id.in_(ids),
            Review.direction == direction,
            Review.status == 'published',
        )
        .group_by(Review.subject_id)
    )
    return {subject: (round(float(avg), 2), count) for subject, avg, count in rows}


async def customer_ratings(
    session: AsyncSession, user_ids: Iterable[UUID]
) -> dict[UUID, tuple[float | None, int]]:
    return await rating_summary(session, user_ids, ReviewDirection.FOR_CUSTOMER)


async def completed_counts(session: AsyncSession, companion_ids: list[UUID]) -> dict[UUID, int]:
    if not companion_ids:
        return {}
    rows = await session.execute(
        select(Booking.companion_id, func.count())
        .where(
            Booking.companion_id.in_(companion_ids),
            Booking.status == BookingStatus.COMPLETED,
        )
        .group_by(Booking.companion_id)
    )
    return dict(rows.all())


async def submit_review(
    session: AsyncSession,
    settings: Settings,
    author: User,
    booking_id: UUID,
    rating: int,
    criteria: dict[str, int],
    tags: list[str],
    text: str,
) -> Review:
    booking, role = await bookings.participant_booking(session, booking_id, author, lock=True)
    if booking.status != BookingStatus.COMPLETED or booking.ended_at is None:
        raise ApplicationError('review_not_allowed', 'Only completed bookings can be reviewed', 409)
    if utc_now() > as_utc(booking.ended_at) + timedelta(days=settings.review_window_days):
        raise ApplicationError('review_window_closed', 'The review window has closed', 409)
    direction = (
        ReviewDirection.FOR_COMPANION if role == 'customer' else ReviewDirection.FOR_CUSTOMER
    )
    allowed_criteria = set(CRITERIA[direction])
    unknown = set(criteria) - allowed_criteria
    if unknown:
        raise ApplicationError('invalid_criteria', f'Unknown criteria: {sorted(unknown)}', 422)
    allowed_tags = set(
        settings.review_tags_for_companion
        if direction == ReviewDirection.FOR_COMPANION
        else settings.review_tags_for_customer
    )
    if set(tags) - allowed_tags:
        raise ApplicationError('invalid_tags', 'Use the configured quick tags', 422)
    subject = booking.companion_id if role == 'customer' else booking.customer_id
    review = Review(
        booking_id=booking.id,
        author_id=author.id,
        subject_id=subject,
        direction=direction,
        rating=rating,
        criteria=criteria,
        tags=list(dict.fromkeys(tags)),
        text=text,
        status='published',
    )
    session.add(review)
    notify(
        session,
        subject,
        'review_received',
        'Yangi baho',
        f'Sizga {rating} yulduzli baho qoldirildi.',
        {'booking_id': booking.id},
    )
    await commit(session, 'review_exists', 'You already reviewed this booking')
    return review
