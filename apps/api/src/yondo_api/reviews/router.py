from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.bookings.router import _participant
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.companions.models import CompanionApplication, CompanionProfile
from yondo_api.reviews.models import BookingReview

router = APIRouter(prefix='/reviews', tags=['reviews'])


class ReviewWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    stars: int = Field(strict=True, ge=1, le=5)
    tags: list[str] = Field(default_factory=list, max_length=10)
    comment: str = Field(default='', max_length=2000)


class ReviewRead(ReviewWrite):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    booking_id: UUID
    reviewer_id: UUID
    reviewee_id: UUID


@router.post('/bookings/{booking_id}', response_model=ReviewRead, status_code=201)
async def create_review(
    booking_id: UUID, payload: ReviewWrite, principal: Principal, session: Session
):
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    is_customer, _ = await _participant(session, booking, principal.user.id)
    if booking.status != BookingStatus.COMPLETED:
        raise ApplicationError('review_not_ready', 'The booking is not completed', 409)
    other_id = (
        await session.scalar(
            select(CompanionApplication.user_id)
            .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
            .where(CompanionProfile.id == booking.profile_id)
        )
        if is_customer
        else booking.customer_id
    )
    if other_id is None or other_id == principal.user.id:
        raise ApplicationError('review_not_allowed', 'Review is not allowed', 409)
    if any(not isinstance(tag, str) or not 1 <= len(tag.strip()) <= 64 for tag in payload.tags):
        raise ApplicationError('invalid_review_tag', 'Review tags must be 1–64 characters', 422)
    review = BookingReview(
        booking_id=booking.id,
        reviewer_id=principal.user.id,
        reviewee_id=other_id,
        stars=payload.stars,
        tags=list(dict.fromkeys(tag.strip() for tag in payload.tags)),
        comment=payload.comment.strip(),
    )
    session.add(review)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError('review_already_exists', 'Review already submitted', 409) from exc
    await session.refresh(review)
    return review


@router.get('/bookings/{booking_id}', response_model=list[ReviewRead])
async def list_booking_reviews(booking_id: UUID, principal: Principal, session: Session):
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    await _participant(session, booking, principal.user.id)
    return list(
        await session.scalars(select(BookingReview).where(BookingReview.booking_id == booking_id))
    )
