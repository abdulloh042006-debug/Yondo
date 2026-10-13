from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.bookings.router import _participant
from yondo_api.chat.service import append_system_message, publish
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.companions.models import CompanionApplication, CompanionProfile
from yondo_api.meetings.models import MeetingAttendance
from yondo_api.notifications.service import enqueue_booking_notice

router = APIRouter(prefix='/meetings', tags=['meetings'])


class MeetingState(BaseModel):
    booking_id: UUID
    booking_status: BookingStatus
    arrived_count: int
    ended_count: int
    customer_arrived: bool
    companion_arrived: bool


async def locked_booking(session: Session, booking_id: UUID) -> Booking:
    booking = await session.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    return booking


async def participants(session: Session, booking: Booking, caller_id: UUID) -> set[UUID]:
    await _participant(session, booking, caller_id)
    companion_id = await session.scalar(
        select(CompanionApplication.user_id)
        .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
        .where(CompanionProfile.id == booking.profile_id)
    )
    if companion_id is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    return {booking.customer_id, companion_id}


async def state(session: Session, booking: Booking, ids: set[UUID]) -> MeetingState:
    rows = list(
        await session.scalars(
            select(MeetingAttendance).where(
                MeetingAttendance.booking_id == booking.id,
                MeetingAttendance.user_id.in_(ids),
            )
        )
    )
    arrivals = {row.user_id for row in rows}
    return MeetingState(
        booking_id=booking.id,
        booking_status=BookingStatus(booking.status),
        arrived_count=len(arrivals),
        ended_count=sum(row.ended_at is not None for row in rows),
        customer_arrived=booking.customer_id in arrivals,
        companion_arrived=bool(arrivals - {booking.customer_id}),
    )


@router.get('/bookings/{booking_id}', response_model=MeetingState)
async def get_meeting(booking_id: UUID, principal: Principal, session: Session):
    booking = await locked_booking(session, booking_id)
    ids = await participants(session, booking, principal.user.id)
    return await state(session, booking, ids)


@router.post('/bookings/{booking_id}/check-in', response_model=MeetingState)
async def check_in(booking_id: UUID, request: Request, principal: Principal, session: Session):
    booking = await locked_booking(session, booking_id)
    ids = await participants(session, booking, principal.user.id)
    if booking.status != BookingStatus.CONFIRMED:
        raise ApplicationError('meeting_not_ready', 'A confirmed booking is required', 409)
    row = await session.scalar(
        select(MeetingAttendance).where(
            MeetingAttendance.booking_id == booking.id,
            MeetingAttendance.user_id == principal.user.id,
        )
    )
    if row is None:
        session.add(
            MeetingAttendance(
                booking_id=booking.id, user_id=principal.user.id, arrived_at=datetime.now(UTC)
            )
        )
        msg = append_system_message(session, booking.id, 'participant_arrived')
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise ApplicationError('meeting_state_conflict', 'Meeting state changed', 409) from exc
        await session.refresh(msg)
        await publish(request, msg)
    return await state(session, booking, ids)


@router.post('/bookings/{booking_id}/start', response_model=MeetingState)
async def start_meeting(booking_id: UUID, request: Request, principal: Principal, session: Session):
    booking = await locked_booking(session, booking_id)
    ids = await participants(session, booking, principal.user.id)
    if booking.status != BookingStatus.CONFIRMED:
        raise ApplicationError('meeting_not_ready', 'A confirmed booking is required', 409)
    current = await state(session, booking, ids)
    if current.arrived_count != len(ids):
        raise ApplicationError('meeting_check_in_required', 'Both participants must check in', 409)
    starts_at = booking.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=UTC)
    if datetime.now(UTC) < starts_at:
        raise ApplicationError(
            'meeting_too_early', 'Meeting cannot start before scheduled time', 409
        )
    booking.status = BookingStatus.ACTIVE
    msg = append_system_message(session, booking.id, 'meeting_started', {'status': 'active'})
    await session.commit()
    await session.refresh(msg)
    await publish(request, msg)
    return await state(session, booking, ids)


@router.post('/bookings/{booking_id}/end', response_model=MeetingState)
async def end_meeting(booking_id: UUID, request: Request, principal: Principal, session: Session):
    booking = await locked_booking(session, booking_id)
    ids = await participants(session, booking, principal.user.id)
    if booking.status != BookingStatus.ACTIVE:
        raise ApplicationError('meeting_not_active', 'The meeting is not active', 409)
    row = await session.scalar(
        select(MeetingAttendance).where(
            MeetingAttendance.booking_id == booking.id,
            MeetingAttendance.user_id == principal.user.id,
        )
    )
    if row is None:
        raise ApplicationError('meeting_check_in_required', 'Check-in required', 409)
    if row.ended_at is not None:
        raise ApplicationError('meeting_already_ended', 'End already acknowledged', 409)
    row.ended_at = datetime.now(UTC)
    await session.flush()
    current = await state(session, booking, ids)
    complete = current.ended_count == len(ids)
    if complete:
        booking.status = BookingStatus.COMPLETED
    msg = append_system_message(
        session,
        booking.id,
        'meeting_completed' if complete else 'meeting_end_acknowledged',
        {'status': booking.status},
    )
    if complete:
        await session.flush()
        await enqueue_booking_notice(
            session, booking, 'review_reminder', msg.id, recipients='both'
        )
    await session.commit()
    await session.refresh(msg)
    await publish(request, msg)
    return await state(session, booking, ids)
