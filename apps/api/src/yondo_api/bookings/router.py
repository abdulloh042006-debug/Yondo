from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_, select

from yondo_api.bookings import service
from yondo_api.bookings.models import Booking, BookingEvent, BookingStatus
from yondo_api.bookings.schemas import (
    BookingCreate,
    BookingEventResponse,
    BookingRequest,
    BookingResponse,
    CancellationPreview,
    DecisionNote,
    MeetingPlace,
    Quote,
    RebookTemplate,
)
from yondo_api.core.deps import CurrentUser, Session
from yondo_api.core.schemas import Page, PageParams, page_of
from yondo_api.core.time import utc_now
from yondo_api.payments.service import process_refunds

router = APIRouter(prefix='/bookings', tags=['bookings'])

FINISHED = (
    BookingStatus.COMPLETED,
    BookingStatus.CANCELLED,
    BookingStatus.NO_SHOW,
    BookingStatus.DISPUTED,
)


async def one(session, request, booking: Booking, viewer) -> BookingResponse:
    return (await service.build_responses(session, request, [booking], viewer))[0]


@router.post('/quote', response_model=Quote)
async def quote(payload: BookingRequest, request: Request, user: CurrentUser, session: Session):
    """Booking Summary: price breakdown and the contract the customer will accept."""
    prepared = await service.prepare(session, request, user, payload)
    service_item, amounts = prepared['service'], prepared['amounts']
    return Quote(
        service_code=service_item.service_code,
        unit_price_minor=service_item.price_minor,
        unit_minutes=service_item.unit_minutes,
        duration_minutes=payload.duration_minutes,
        currency=service_item.currency,
        service_amount_minor=amounts.service_amount_minor,
        platform_fee_minor=amounts.platform_fee_minor,
        total_minor=amounts.total_minor,
        starts_at=prepared['starts_at'],
        ends_at=prepared['ends_at'],
        timezone=prepared['timezone'],
        contract=prepared['contract'],
    )


@router.post('', response_model=BookingResponse, status_code=201)
async def create_booking(
    payload: BookingCreate, request: Request, user: CurrentUser, session: Session
):
    booking = await service.create(session, request, user, payload)
    return await one(session, request, booking, user)


@router.get('', response_model=Page[BookingResponse])
async def list_bookings(
    request: Request,
    user: CurrentUser,
    session: Session,
    params: Annotated[PageParams, Depends()],
    role: Literal['customer', 'companion', 'any'] = 'any',
    status: Annotated[list[BookingStatus] | None, Query()] = None,
    scope: Literal['upcoming', 'past', 'all'] = 'all',
):
    query = select(Booking)
    if role == 'customer':
        query = query.where(Booking.customer_id == user.id)
    elif role == 'companion':
        query = query.where(Booking.companion_id == user.id)
    else:
        query = query.where(or_(Booking.customer_id == user.id, Booking.companion_id == user.id))
    if status:
        query = query.where(Booking.status.in_(status))
    now = utc_now()
    if scope == 'upcoming':
        query = query.where(Booking.ends_at > now, Booking.status.not_in(FINISHED)).order_by(
            Booking.starts_at
        )
    elif scope == 'past':
        query = query.where(or_(Booking.ends_at <= now, Booking.status.in_(FINISHED))).order_by(
            Booking.starts_at.desc()
        )
    else:
        query = query.order_by(Booking.starts_at.desc())
    rows = list(await session.scalars(query.offset(params.offset).limit(params.limit + 1)))
    page = page_of(rows, params)
    return Page[BookingResponse](
        items=await service.build_responses(session, request, page.items, user),
        next_offset=page.next_offset,
    )


@router.get('/{booking_id}', response_model=BookingResponse)
async def get_booking(booking_id: UUID, request: Request, user: CurrentUser, session: Session):
    booking, _ = await service.participant_booking(session, booking_id, user)
    return await one(session, request, booking, user)


@router.get('/{booking_id}/events', response_model=list[BookingEventResponse])
async def booking_events(booking_id: UUID, user: CurrentUser, session: Session):
    await service.participant_booking(session, booking_id, user)
    return list(
        await session.scalars(
            select(BookingEvent)
            .where(BookingEvent.booking_id == booking_id)
            .order_by(BookingEvent.created_at, BookingEvent.id)
        )
    )


@router.post('/{booking_id}/accept', response_model=BookingResponse)
async def accept_booking(booking_id: UUID, request: Request, user: CurrentUser, session: Session):
    booking = await service.accept(session, request, user, booking_id)
    return await one(session, request, booking, user)


@router.post('/{booking_id}/decline', response_model=BookingResponse)
async def decline_booking(
    booking_id: UUID, payload: DecisionNote, request: Request, user: CurrentUser, session: Session
):
    booking = await service.decline(session, user, booking_id, payload.note)
    return await one(session, request, booking, user)


@router.get('/{booking_id}/cancellation', response_model=CancellationPreview)
async def cancellation_preview(booking_id: UUID, user: CurrentUser, session: Session):
    booking, role = await service.participant_booking(session, booking_id, user)
    return service.preview_cancellation(booking, role, utc_now())


@router.post('/{booking_id}/cancel', response_model=BookingResponse)
async def cancel_booking(
    booking_id: UUID, payload: DecisionNote, request: Request, user: CurrentUser, session: Session
):
    booking = await service.cancel(session, user, booking_id, payload.note)
    # Best effort: send queued refunds now; the worker retries anything left pending.
    await process_refunds(session, request.app.state)
    return await one(session, request, booking, user)


@router.get('/{booking_id}/rebook', response_model=RebookTemplate)
async def rebook_template(booking_id: UUID, user: CurrentUser, session: Session):
    """Book Again (TZ §35): a prefilled request; the client picks a new time."""
    booking, role = await service.participant_booking(session, booking_id, user)
    if role != 'customer' or booking.status != BookingStatus.COMPLETED:
        raise service.invalid_transition('Only a completed booking can be booked again')
    return RebookTemplate(
        profile_id=booking.profile_id,
        service_id=booking.service_id,
        service_code=booking.service_code,
        duration_minutes=booking.duration_minutes,
        meeting_place=MeetingPlace.model_construct(
            name=booking.meeting_place_name,
            address=booking.meeting_address,
            latitude=booking.meeting_latitude,
            longitude=booking.meeting_longitude,
        ),
    )
