from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import Field, field_validator
from sqlalchemy import select

from yondo_api.bookings import service as bookings
from yondo_api.core.deps import CurrentUser, Session
from yondo_api.core.schemas import Input, Output, Page, PageParams, UtcDatetime, page_of
from yondo_api.models.user import User
from yondo_api.reviews import service
from yondo_api.reviews.models import Review, ReviewDirection

router = APIRouter(tags=['reviews'])

Score = Annotated[int, Field(strict=True, ge=1, le=5)]


class ReviewCreate(Input):
    rating: Score
    criteria: dict[str, Score] = Field(default_factory=dict, max_length=10)
    tags: list[str] = Field(default_factory=list, max_length=10)
    text: str = Field(default='', max_length=2000)

    @field_validator('tags')
    @classmethod
    def short_tags(cls, values: list[str]) -> list[str]:
        if any(len(value) > 64 for value in values):
            raise ValueError('Tags are limited to 64 characters')
        return values


class ReviewResponse(Output):
    id: UUID
    booking_id: UUID
    author_id: UUID
    subject_id: UUID
    direction: str
    rating: int
    criteria: dict[str, int]
    tags: list[str]
    text: str
    status: str
    created_at: UtcDatetime


class PublicReview(Output):
    id: UUID
    author_name: str | None
    rating: int
    criteria: dict[str, int]
    tags: list[str]
    text: str
    created_at: UtcDatetime


class ReviewSummary(Output):
    rating_average: float | None
    rating_count: int
    criteria_average: dict[str, float]
    tag_counts: dict[str, int]
    items: list[PublicReview]
    next_offset: int | None


@router.post('/bookings/{booking_id}/review', response_model=ReviewResponse, status_code=201)
async def create_review(
    booking_id: UUID, payload: ReviewCreate, request: Request, user: CurrentUser, session: Session
):
    return await service.submit_review(
        session,
        request.app.state.settings,
        user,
        booking_id,
        payload.rating,
        payload.criteria,
        payload.tags,
        payload.text,
    )


@router.get('/bookings/{booking_id}/reviews', response_model=list[ReviewResponse])
async def booking_reviews(booking_id: UUID, user: CurrentUser, session: Session):
    await bookings.participant_booking(session, booking_id, user)
    return list(
        await session.scalars(
            select(Review).where(Review.booking_id == booking_id, Review.status == 'published')
        )
    )


@router.get('/discovery/companions/{profile_id}/reviews', response_model=ReviewSummary)
async def companion_reviews(
    profile_id: UUID,
    request: Request,
    viewer: CurrentUser,
    session: Session,
    params: Annotated[PageParams, Depends()],
):
    from yondo_api.discovery.service import public_candidate

    candidate = await public_candidate(session, request, viewer, profile_id)
    published = (
        Review.subject_id == candidate.user.id,
        Review.direction == ReviewDirection.FOR_COMPANION,
        Review.status == 'published',
    )
    all_reviews = list(await session.scalars(select(Review).where(*published)))
    criteria: dict[str, list[int]] = {}
    tags: dict[str, int] = {}
    for review in all_reviews:
        for key, value in review.criteria.items():
            criteria.setdefault(key, []).append(value)
        for tag in review.tags:
            tags[tag] = tags.get(tag, 0) + 1
    rows = list(
        await session.execute(
            select(Review, User.display_name)
            .join(User, User.id == Review.author_id)
            .where(*published)
            .order_by(Review.created_at.desc(), Review.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    page = page_of(
        [
            PublicReview(
                id=review.id,
                # First name only; never expose the reviewer's phone or full identity.
                author_name=(name or '').split(' ')[0] or None,
                rating=review.rating,
                criteria=review.criteria,
                tags=review.tags,
                text=review.text,
                created_at=review.created_at,
            )
            for review, name in rows
        ],
        params,
    )
    count = len(all_reviews)
    return ReviewSummary(
        rating_average=round(sum(r.rating for r in all_reviews) / count, 2) if count else None,
        rating_count=count,
        criteria_average={k: round(sum(v) / len(v), 2) for k, v in sorted(criteria.items())},
        tag_counts=dict(sorted(tags.items(), key=lambda item: -item[1])),
        items=page.items,
        next_offset=page.next_offset,
    )


@router.get('/reviews/me', response_model=Page[ReviewResponse])
async def my_reviews(
    user: CurrentUser,
    session: Session,
    params: Annotated[PageParams, Depends()],
    received: bool = True,
):
    column = Review.subject_id if received else Review.author_id
    rows = list(
        await session.scalars(
            select(Review)
            .where(column == user.id, Review.status == 'published')
            .order_by(Review.created_at.desc(), Review.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    return page_of([ReviewResponse.model_validate(row) for row in rows], params)
