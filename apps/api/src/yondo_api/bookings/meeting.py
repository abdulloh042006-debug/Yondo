"""Phase 11 meeting flow: I'm here, Start Meeting, End Meeting and no-show (TZ §12, §22)."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings import service
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.bookings.schemas import BookingResponse, DecisionNote
from yondo_api.config import Settings
from yondo_api.core.deps import CurrentUser, Session
from yondo_api.core.time import as_utc, utc_now

router = APIRouter(prefix='/bookings', tags=['meeting'])


async def check_in(session: AsyncSession, settings: Settings, user, booking_id: UUID) -> Booking:
    booking, role = await service.participant_booking(session, booking_id, user, lock=True)
    if booking.status != BookingStatus.CONFIRMED:
        raise service.invalid_transition('Check-in is available for confirmed bookings')
    now = utc_now()
    opens = as_utc(booking.starts_at) - timedelta(minutes=settings.meeting_checkin_window_minutes)
    if now < opens or now >= as_utc(booking.ends_at):
        raise ApplicationError('check_in_not_open', 'Check-in is not open yet', 409)
    field = 'customer_checked_in_at' if role == 'customer' else 'companion_checked_in_at'
    if getattr(booking, field) is not None:
        raise service.invalid_transition('Already checked in')
    setattr(booking, field, now)
    service.record_event(
        session,
        booking,
        'checked_in',
        actor_id=user.id,
        from_status=booking.status,
        data={'party': role},
    )
    other = booking.companion_id if role == 'customer' else booking.customer_id
    who = 'Mijoz' if role == 'customer' else 'Companion'
    service.booking_notice(
        session, booking, other, 'meeting_check_in', f'{who} yetib keldi', "I'm here"
    )
    await service.save(session)
    return booking


async def start(session: AsyncSession, user, booking_id: UUID) -> Booking:
    booking, role = await service.participant_booking(session, booking_id, user, lock=True)
    if role != 'companion':
        raise ApplicationError('companion_only', 'Only the companion starts the meeting', 403)
    if booking.status != BookingStatus.CONFIRMED:
        raise service.invalid_transition('Only a confirmed booking can start')
    if booking.customer_checked_in_at is None or booking.companion_checked_in_at is None:
        raise ApplicationError('check_in_required', 'Both parties must check in first', 409)
    booking.started_at = utc_now()
    service.transition(session, booking, BookingStatus.ACTIVE, 'started', actor_id=user.id)
    service.booking_notice(
        session,
        booking,
        booking.customer_id,
        'meeting_started',
        'Uchrashuv boshlandi',
        'Xavfsizlik markazi va SOS tugmasi faol. Bronni ishonchli kontakt bilan ulashing.',
    )
    await service.save(session)
    return booking


async def complete(
    session: AsyncSession,
    settings: Settings,
    booking: Booking,
    actor_id: UUID | None,
    now: datetime,
) -> None:
    from yondo_api.payments.service import schedule_payout

    booking.ended_at = now
    booking.ended_by = actor_id
    service.transition(
        session,
        booking,
        BookingStatus.COMPLETED,
        'ended',
        actor_id=actor_id,
        data={'automatic': actor_id is None},
    )
    await schedule_payout(session, booking, settings)
    for party in (booking.customer_id, booking.companion_id):
        service.booking_notice(
            session,
            booking,
            party,
            'meeting_completed',
            'Uchrashuv yakunlandi',
            'Iltimos, baho va fikr qoldiring.',
        )


async def end(session: AsyncSession, settings: Settings, user, booking_id: UUID) -> Booking:
    """Either party may end an active meeting (the customer may need to leave for safety)."""
    booking, _ = await service.participant_booking(session, booking_id, user, lock=True)
    if booking.status != BookingStatus.ACTIVE:
        raise service.invalid_transition('Only an active meeting can be ended')
    await complete(session, settings, booking, user.id, utc_now())
    await service.save(session)
    return booking


async def report_no_show(
    session: AsyncSession, settings: Settings, user, booking_id: UUID, note: str
) -> Booking:
    from yondo_api.payments.service import hold_payout
    from yondo_api.safety.disputes import open_dispute

    booking, role = await service.participant_booking(session, booking_id, user, lock=True)
    if booking.status != BookingStatus.CONFIRMED:
        raise service.invalid_transition('No-show can be reported for confirmed bookings')
    now = utc_now()
    if now < as_utc(booking.starts_at) + timedelta(minutes=settings.meeting_no_show_grace_minutes):
        raise ApplicationError('no_show_too_early', 'Wait for the grace period to pass', 409)
    reporter_in = (
        booking.customer_checked_in_at if role == 'customer' else booking.companion_checked_in_at
    )
    other_in = (
        booking.companion_checked_in_at if role == 'customer' else booking.customer_checked_in_at
    )
    if reporter_in is None:
        raise ApplicationError('check_in_required', 'Check in before reporting a no-show', 409)
    if other_in is not None:
        raise ApplicationError('party_checked_in', 'The other party has checked in', 409)
    booking.no_show_reported_by = user.id
    booking.no_show_party = 'companion' if role == 'customer' else 'customer'
    service.transition(
        session,
        booking,
        BookingStatus.NO_SHOW,
        'no_show_reported',
        actor_id=user.id,
        data={'no_show_party': booking.no_show_party},
    )
    await hold_payout(session, booking.id, 'no_show')
    # TZ §22: the admin (or an automatic rule) reviews and applies refund/payout rules.
    await open_dispute(
        session, booking, user.id, 'no_show', note or 'No-show reported', from_no_show=True
    )
    other = booking.companion_id if role == 'customer' else booking.customer_id
    service.booking_notice(
        session,
        booking,
        other,
        'no_show_reported',
        'No-show haqida xabar',
        'Siz uchrashuvga kelmagan deb belgilandingiz. Administrator ko‘rib chiqadi.',
    )
    await service.save(session)
    return booking


async def auto_complete_overdue(session: AsyncSession, settings: Settings) -> int:
    now = utc_now()
    cutoff = now - timedelta(hours=settings.meeting_auto_complete_hours)
    ids = list(
        await session.scalars(
            select(Booking.id).where(
                Booking.status == BookingStatus.ACTIVE, Booking.ends_at <= cutoff
            )
        )
    )
    for booking_id in ids:
        booking = await service.lock_booking(session, booking_id)
        if booking.status == BookingStatus.ACTIVE:
            await complete(session, settings, booking, None, now)
        await service.save(session)
    return len(ids)


async def _respond(session, request, booking, user) -> BookingResponse:
    return (await service.build_responses(session, request, [booking], user))[0]


@router.post('/{booking_id}/check-in', response_model=BookingResponse)
async def check_in_route(booking_id: UUID, request: Request, user: CurrentUser, session: Session):
    booking = await check_in(session, request.app.state.settings, user, booking_id)
    return await _respond(session, request, booking, user)


@router.post('/{booking_id}/start', response_model=BookingResponse)
async def start_route(booking_id: UUID, request: Request, user: CurrentUser, session: Session):
    booking = await start(session, user, booking_id)
    return await _respond(session, request, booking, user)


@router.post('/{booking_id}/end', response_model=BookingResponse)
async def end_route(booking_id: UUID, request: Request, user: CurrentUser, session: Session):
    booking = await end(session, request.app.state.settings, user, booking_id)
    return await _respond(session, request, booking, user)


@router.post('/{booking_id}/no-show', response_model=BookingResponse)
async def no_show_route(
    booking_id: UUID,
    payload: DecisionNote,
    request: Request,
    user: CurrentUser,
    session: Session,
):
    booking = await report_no_show(
        session, request.app.state.settings, user, booking_id, payload.note
    )
    return await _respond(session, request, booking, user)
