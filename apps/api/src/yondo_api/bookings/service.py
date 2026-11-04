from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Request
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings import policy
from yondo_api.bookings.models import (
    HELD_STATUSES,
    Booking,
    BookingEvent,
    BookingStatus,
    CancellationReason,
)
from yondo_api.bookings.schemas import (
    BookingCreate,
    BookingRequest,
    BookingResponse,
    CancellationPreview,
    MeetingPlace,
    Party,
)
from yondo_api.companions.models import CompanionAvailability
from yondo_api.config import Settings
from yondo_api.core.db import lock_users
from yondo_api.core.deps import has_role, require_active
from yondo_api.core.money import BPS_DENOMINATOR, apply_bps
from yondo_api.core.time import as_utc, utc_now
from yondo_api.models.user import User, UserRoleType
from yondo_api.notifications.service import notify
from yondo_api.realtime.broker import queue_event
from yondo_api.safety.service import ensure_not_blocked


def fmt_local(value: datetime, timezone: str) -> str:
    return as_utc(value).astimezone(ZoneInfo(timezone)).strftime('%d.%m.%Y %H:%M')


def not_found() -> ApplicationError:
    return ApplicationError('booking_not_found', 'Booking not found', 404)


def invalid_transition(message: str) -> ApplicationError:
    return ApplicationError('invalid_booking_transition', message, 409)


async def lock_booking(session: AsyncSession, booking_id: UUID) -> Booking:
    booking = await session.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if booking is None:
        raise not_found()
    return booking


def role_of(booking: Booking, user: User) -> str | None:
    if booking.customer_id == user.id:
        return 'customer'
    if booking.companion_id == user.id:
        return 'companion'
    return None


async def participant_booking(
    session: AsyncSession, booking_id: UUID, user: User, *, lock: bool = False
) -> tuple[Booking, str]:
    booking = (
        await lock_booking(session, booking_id) if lock else await session.get(Booking, booking_id)
    )
    role = role_of(booking, user) if booking is not None else None
    if booking is None or role is None:
        raise not_found()
    return booking, role


def record_event(
    session: AsyncSession,
    booking: Booking,
    event: str,
    *,
    actor_id: UUID | None,
    from_status: str | None,
    data: dict[str, Any] | None = None,
) -> None:
    session.add(
        BookingEvent(
            booking_id=booking.id,
            actor_id=actor_id,
            event=event,
            from_status=from_status,
            to_status=booking.status,
            data=data or {},
            created_at=utc_now(),
        )
    )
    for party in (booking.customer_id, booking.companion_id):
        queue_event(
            session,
            party,
            {
                'type': 'booking_updated',
                'booking_id': str(booking.id),
                'status': booking.status,
                'event': event,
            },
        )
    from yondo_api.chat.service import post_system_message

    post_system_message(session, booking, event, data or {})


def transition(
    session: AsyncSession,
    booking: Booking,
    to_status: BookingStatus,
    event: str,
    *,
    actor_id: UUID | None,
    data: dict[str, Any] | None = None,
) -> None:
    previous = booking.status
    booking.status = to_status
    record_event(session, booking, event, actor_id=actor_id, from_status=previous, data=data)


def booking_notice(
    session: AsyncSession, booking: Booking, user_id: UUID, kind: str, title: str, body: str
) -> None:
    notify(session, user_id, kind, title, body, {'booking_id': booking.id})


async def held_intervals(
    session: AsyncSession,
    user_id: UUID,
    start: datetime,
    end: datetime,
    *,
    party: str = 'companion',
) -> list[tuple[datetime, datetime]]:
    column = Booking.companion_id if party == 'companion' else Booking.customer_id
    rows = await session.execute(
        select(Booking.starts_at, Booking.ends_at).where(
            column == user_id,
            Booking.status.in_(HELD_STATUSES),
            Booking.starts_at < end,
            Booking.ends_at > start,
        )
    )
    return [(as_utc(s), as_utc(e)) for s, e in rows]


async def covering_timezone(
    session: AsyncSession,
    profile_id: UUID,
    start: datetime,
    end: datetime,
    *,
    exclude_id: UUID | None = None,
    extra: tuple[datetime, datetime] | None = None,
) -> str | None:
    """Return the window timezone when contiguous availability fully covers [start, end)."""
    query = select(CompanionAvailability).where(
        CompanionAvailability.profile_id == profile_id,
        CompanionAvailability.starts_at <= end,
        CompanionAvailability.ends_at >= start,
    )
    if exclude_id is not None:
        query = query.where(CompanionAvailability.id != exclude_id)
    windows = [
        (as_utc(item.starts_at), as_utc(item.ends_at), item.timezone)
        for item in await session.scalars(query)
    ]
    if extra is not None:
        windows.append((as_utc(extra[0]), as_utc(extra[1]), ''))
    cursor, zone = start, None
    for window_start, window_end, timezone in sorted(windows):
        if window_start > cursor:
            break
        if window_end > cursor:
            zone = zone or timezone or None
            cursor = window_end
        if cursor >= end:
            return zone or ''
    return None


async def ensure_no_conflicts(
    session: AsyncSession,
    companion_id: UUID,
    customer_id: UUID,
    start: datetime,
    end: datetime,
    *,
    exclude_id: UUID | None = None,
) -> None:
    query = select(Booking.id).where(
        Booking.status.in_(HELD_STATUSES),
        Booking.starts_at < end,
        Booking.ends_at > start,
        or_(Booking.companion_id == companion_id, Booking.customer_id == customer_id),
    )
    if exclude_id is not None:
        query = query.where(Booking.id != exclude_id)
    if await session.scalar(query.limit(1)) is not None:
        raise ApplicationError('slot_unavailable', 'This time is no longer available', 409)


async def prepare(
    session: AsyncSession, request: Request, customer: User, payload: BookingRequest
) -> dict[str, Any]:
    """Validate a booking request and compute its price and contract (Booking Summary)."""
    from yondo_api.discovery.service import public_candidate

    settings: Settings = request.app.state.settings
    require_active(customer)
    if not await has_role(session, customer, UserRoleType.CUSTOMER):
        raise ApplicationError('customer_role_required', 'Select the customer role to book', 403)
    candidate = await public_candidate(session, request, customer, payload.profile_id)
    await ensure_not_blocked(session, customer.id, candidate.user.id)
    service = next((item for item in candidate.services if item.id == payload.service_id), None)
    if service is None:
        raise ApplicationError('service_not_found', 'Service not offered by this companion', 404)
    if payload.duration_minutes > settings.booking_max_duration_minutes:
        raise ApplicationError('invalid_duration', 'Duration exceeds the configured maximum', 422)
    amounts = policy.price(
        service.price_minor, service.unit_minutes, payload.duration_minutes, settings
    )
    now = utc_now()
    starts_at = as_utc(payload.starts_at)
    ends_at = starts_at + timedelta(minutes=payload.duration_minutes)
    if starts_at < now + timedelta(minutes=settings.booking_min_lead_minutes):
        raise ApplicationError('booking_too_soon', 'Choose a later start time', 422)
    if starts_at > now + timedelta(days=settings.booking_max_horizon_days):
        raise ApplicationError('booking_too_far', 'Choose an earlier start time', 422)
    zone = await covering_timezone(session, candidate.profile.id, starts_at, ends_at)
    if zone is None:
        raise ApplicationError(
            'outside_availability', 'The companion is not available at this time', 409
        )
    timezone = zone or settings.booking_default_timezone
    place = payload.meeting_place.model_dump()
    contract = policy.contract_snapshot(
        settings=settings,
        customer={'id': str(customer.id), 'display_name': customer.display_name},
        companion={
            'id': str(candidate.user.id),
            'display_name': candidate.profile.display_name,
        },
        service={
            'id': str(service.id),
            'code': service.service_code,
            'unit_price_minor': service.price_minor,
            'unit_minutes': service.unit_minutes,
        },
        starts_at=starts_at,
        ends_at=ends_at,
        timezone=timezone,
        duration_minutes=payload.duration_minutes,
        meeting_place=place,
        amounts=amounts,
        currency=service.currency,
    )
    return {
        'candidate': candidate,
        'service': service,
        'amounts': amounts,
        'starts_at': starts_at,
        'ends_at': ends_at,
        'timezone': timezone,
        'contract': contract,
    }


async def create(
    session: AsyncSession, request: Request, customer: User, payload: BookingCreate
) -> Booking:
    settings: Settings = request.app.state.settings
    prepared = await prepare(session, request, customer, payload)
    candidate, service, amounts = prepared['candidate'], prepared['service'], prepared['amounts']
    starts_at, ends_at = prepared['starts_at'], prepared['ends_at']
    await lock_users(session, [customer.id, candidate.user.id])
    await ensure_no_conflicts(session, candidate.user.id, customer.id, starts_at, ends_at)
    duplicate = await session.scalar(
        select(Booking.id).where(
            Booking.customer_id == customer.id,
            Booking.companion_id == candidate.user.id,
            Booking.status == BookingStatus.PENDING,
            Booking.starts_at < ends_at,
            Booking.ends_at > starts_at,
        )
    )
    if duplicate is not None:
        raise ApplicationError('duplicate_booking_request', 'You already requested this time', 409)
    if payload.rebooked_from_id is not None:
        previous = await session.get(Booking, payload.rebooked_from_id)
        if (
            previous is None
            or previous.customer_id != customer.id
            or previous.companion_id != candidate.user.id
        ):
            raise ApplicationError('booking_not_found', 'Booking not found', 404)
    now = utc_now()
    booking = Booking(
        customer_id=customer.id,
        companion_id=candidate.user.id,
        profile_id=candidate.profile.id,
        service_id=service.id,
        rebooked_from_id=payload.rebooked_from_id,
        status=BookingStatus.PENDING,
        service_code=service.service_code,
        unit_price_minor=service.price_minor,
        unit_minutes=service.unit_minutes,
        currency=service.currency,
        starts_at=starts_at,
        ends_at=ends_at,
        duration_minutes=payload.duration_minutes,
        timezone=prepared['timezone'],
        meeting_place_name=payload.meeting_place.name,
        meeting_address=payload.meeting_place.address,
        meeting_latitude=payload.meeting_place.latitude,
        meeting_longitude=payload.meeting_place.longitude,
        customer_note=payload.note,
        service_amount_minor=amounts.service_amount_minor,
        platform_fee_minor=amounts.platform_fee_minor,
        total_minor=amounts.total_minor,
        companion_payout_minor=amounts.companion_payout_minor,
        refund_minor=0,
        contract=prepared['contract'],
        contract_version=settings.booking_contract_version,
        customer_accepted_at=now,
        request_expires_at=min(
            now + timedelta(minutes=settings.booking_request_ttl_minutes), starts_at
        ),
    )
    session.add(booking)
    await session.flush()
    record_event(session, booking, 'requested', actor_id=customer.id, from_status=None)
    booking_notice(
        session,
        booking,
        booking.companion_id,
        'booking_requested',
        "Yangi bron so'rovi",
        f'{customer.display_name or "Mijoz"} {fmt_local(starts_at, booking.timezone)} '
        f"uchun bron so'radi.",
    )
    await save(session)
    return booking


async def save(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError('slot_unavailable', 'This time is no longer available', 409) from exc


def expire_if_due(session: AsyncSession, booking: Booking, now: datetime) -> bool:
    if booking.status == BookingStatus.PENDING and now >= as_utc(booking.request_expires_at):
        cancel_record(session, booking, CancellationReason.REQUEST_EXPIRED, None, now)
        return True
    if (
        booking.status == BookingStatus.ACCEPTED
        and booking.payment_due_at is not None
        and now >= as_utc(booking.payment_due_at)
    ):
        cancel_record(session, booking, CancellationReason.PAYMENT_EXPIRED, None, now)
        return True
    return False


def cancel_record(
    session: AsyncSession,
    booking: Booking,
    reason: CancellationReason,
    actor_id: UUID | None,
    now: datetime,
    note: str = '',
    refund_bps: int = 0,
) -> None:
    booking.cancelled_at = now
    booking.cancelled_by = actor_id
    booking.cancellation_reason = reason
    booking.cancellation_note = note or None
    paid = booking.confirmed_at is not None and booking.total_minor > 0
    booking.refund_minor = apply_bps(booking.total_minor, refund_bps) if paid else 0
    transition(
        session,
        booking,
        BookingStatus.CANCELLED,
        reason,
        actor_id=actor_id,
        data={'refund_minor': booking.refund_minor, 'refund_bps': refund_bps},
    )
    titles = {
        CancellationReason.DECLINED: ('Bron rad etildi', "Companion so'rovni rad etdi."),
        CancellationReason.REQUEST_EXPIRED: (
            "Bron so'rovi muddati tugadi",
            "So'rov belgilangan vaqtda qabul qilinmadi.",
        ),
        CancellationReason.PAYMENT_EXPIRED: (
            "To'lov muddati tugadi",
            "Bron to'lov qilinmagani uchun bekor qilindi.",
        ),
    }
    title, body = titles.get(reason, ('Bron bekor qilindi', 'Bron bekor qilindi.'))
    for party in (booking.customer_id, booking.companion_id):
        if party != actor_id:
            booking_notice(session, booking, party, 'booking_cancelled', title, body)


async def accept(session: AsyncSession, request: Request, companion: User, booking_id: UUID):
    settings: Settings = request.app.state.settings
    booking, role = await participant_booking(session, booking_id, companion)
    if role != 'companion':
        raise not_found()
    require_active(companion)
    await lock_users(session, [booking.customer_id, booking.companion_id])
    booking = await lock_booking(session, booking_id)
    now = utc_now()
    if expire_if_due(session, booking, now):
        await save(session)
        raise ApplicationError('booking_expired', 'The booking request has expired', 409)
    if booking.status != BookingStatus.PENDING:
        raise invalid_transition('Only a pending booking can be accepted')
    await ensure_not_blocked(session, booking.customer_id, booking.companion_id)
    if (
        await covering_timezone(
            session, booking.profile_id, as_utc(booking.starts_at), as_utc(booking.ends_at)
        )
        is None
    ):
        raise ApplicationError(
            'outside_availability', 'The request is outside your current availability', 409
        )
    await ensure_no_conflicts(
        session,
        booking.companion_id,
        booking.customer_id,
        as_utc(booking.starts_at),
        as_utc(booking.ends_at),
        exclude_id=booking.id,
    )
    booking.companion_accepted_at = now
    if booking.total_minor == 0:
        # Nothing to pay: the booking is confirmed immediately.
        booking.confirmed_at = now
        transition(session, booking, BookingStatus.CONFIRMED, 'accepted', actor_id=companion.id)
        booking_notice(
            session,
            booking,
            booking.customer_id,
            'booking_accepted',
            'Bron tasdiqlandi',
            f'Uchrashuv {fmt_local(booking.starts_at, booking.timezone)} da.',
        )
    else:
        booking.payment_due_at = min(
            now + timedelta(minutes=settings.booking_payment_window_minutes),
            as_utc(booking.starts_at),
        )
        transition(session, booking, BookingStatus.ACCEPTED, 'accepted', actor_id=companion.id)
        booking_notice(
            session,
            booking,
            booking.customer_id,
            'booking_accepted',
            'Bron qabul qilindi',
            f"To'lovni {fmt_local(booking.payment_due_at, booking.timezone)} gacha amalga "
            f'oshiring.',
        )
    await save(session)
    return booking


async def decline(session: AsyncSession, companion: User, booking_id: UUID, note: str):
    booking, role = await participant_booking(session, booking_id, companion, lock=True)
    if role != 'companion':
        raise not_found()
    if booking.status != BookingStatus.PENDING:
        raise invalid_transition('Only a pending booking can be declined')
    cancel_record(session, booking, CancellationReason.DECLINED, companion.id, utc_now(), note)
    await save(session)
    return booking


def preview_cancellation(booking: Booking, role: str, now: datetime) -> CancellationPreview:
    if booking.status not in {
        BookingStatus.PENDING,
        BookingStatus.ACCEPTED,
        BookingStatus.CONFIRMED,
    }:
        raise invalid_transition('This booking can no longer be cancelled')
    outcome = policy.cancellation_outcome(
        paid=booking.confirmed_at is not None and booking.total_minor > 0,
        by_companion=role == 'companion',
        now=now,
        starts_at=as_utc(booking.starts_at),
        policy=booking.contract['cancellation_policy'],
    )
    paid = booking.confirmed_at is not None and booking.total_minor > 0
    refund = apply_bps(booking.total_minor, outcome.refund_bps) if paid else 0
    return CancellationPreview(
        refund_minor=refund,
        refund_bps=outcome.refund_bps if paid else 0,
        refund_percent=(outcome.refund_bps if paid else 0) * 100 / BPS_DENOMINATOR,
        policy=outcome.policy,
    )


async def cancel_and_settle(
    session: AsyncSession,
    booking: Booking,
    reason: CancellationReason,
    actor_id: UUID | None,
    note: str,
    refund_bps: int,
) -> None:
    """Cancel and, for paid bookings, queue refunds and adjust the payout."""
    from yondo_api.payments.service import settle_cancellation

    paid = booking.confirmed_at is not None and booking.total_minor > 0
    cancel_record(session, booking, reason, actor_id, utc_now(), note, refund_bps)
    if paid:
        await settle_cancellation(session, booking, refund_bps)


async def cancel(session: AsyncSession, user: User, booking_id: UUID, note: str):
    booking, role = await participant_booking(session, booking_id, user, lock=True)
    now = utc_now()
    if expire_if_due(session, booking, now):
        await save(session)
        raise ApplicationError('booking_expired', 'The booking has already expired', 409)
    preview = preview_cancellation(booking, role, now)
    if role == 'companion' and booking.status == BookingStatus.PENDING:
        raise invalid_transition('Decline a pending request instead of cancelling it')
    reason = CancellationReason.CUSTOMER if role == 'customer' else CancellationReason.COMPANION
    await cancel_and_settle(session, booking, reason, user.id, note, preview.refund_bps)
    await save(session)
    return booking


async def expire_due(session: AsyncSession, now: datetime | None = None) -> int:
    """Expire unanswered requests and unpaid accepted bookings (background worker)."""
    now = now or utc_now()
    ids = list(
        await session.scalars(
            select(Booking.id).where(
                or_(
                    and_(
                        Booking.status == BookingStatus.PENDING,
                        Booking.request_expires_at <= now,
                    ),
                    and_(
                        Booking.status == BookingStatus.ACCEPTED,
                        Booking.payment_due_at <= now,
                    ),
                )
            )
        )
    )
    expired = 0
    for booking_id in ids:
        booking = await lock_booking(session, booking_id)
        if expire_if_due(session, booking, now):
            expired += 1
        await save(session)
    return expired


async def guard_availability_change(
    session: AsyncSession,
    profile_id: UUID,
    companion_id: UUID,
    removed: CompanionAvailability,
    added: tuple[datetime, datetime] | None,
) -> None:
    """Availability edits must keep every held reservation covered (Phase 6 contract)."""
    affected = await session.scalars(
        select(Booking).where(
            Booking.companion_id == companion_id,
            Booking.status.in_(HELD_STATUSES),
            Booking.starts_at < removed.ends_at,
            Booking.ends_at > removed.starts_at,
        )
    )
    for booking in affected:
        covered = await covering_timezone(
            session,
            profile_id,
            as_utc(booking.starts_at),
            as_utc(booking.ends_at),
            exclude_id=removed.id,
            extra=added,
        )
        if covered is None:
            raise ApplicationError(
                'availability_has_bookings',
                'This change would remove time already reserved by a booking',
                409,
            )


def actions_for(booking: Booking, role: str, now: datetime, settings: Settings) -> list[str]:
    status = booking.status
    starts = as_utc(booking.starts_at)
    actions: list[str] = []
    if role == 'customer':
        if status in {BookingStatus.PENDING, BookingStatus.ACCEPTED, BookingStatus.CONFIRMED}:
            actions.append('cancel')
        if status == BookingStatus.ACCEPTED:
            actions.append('pay')
    elif role == 'companion':
        if status == BookingStatus.PENDING:
            actions += ['accept', 'decline']
        if status in {BookingStatus.ACCEPTED, BookingStatus.CONFIRMED}:
            actions.append('cancel')
    if role in {'customer', 'companion'}:
        checked_in = (
            booking.customer_checked_in_at
            if role == 'customer'
            else booking.companion_checked_in_at
        )
        window = timedelta(minutes=settings.meeting_checkin_window_minutes)
        if status == BookingStatus.CONFIRMED:
            if checked_in is None and now >= starts - window and now < as_utc(booking.ends_at):
                actions.append('check_in')
            if (
                role == 'companion'
                and booking.customer_checked_in_at is not None
                and booking.companion_checked_in_at is not None
            ):
                actions.append('start')
            if checked_in is not None and now >= starts + timedelta(
                minutes=settings.meeting_no_show_grace_minutes
            ):
                actions.append('report_no_show')
        if status == BookingStatus.ACTIVE:
            actions += ['end', 'sos']
        if status in {BookingStatus.CONFIRMED, BookingStatus.ACTIVE}:
            actions.append('share')
        if status in {BookingStatus.COMPLETED, BookingStatus.NO_SHOW}:
            actions.append('dispute')
        if status == BookingStatus.COMPLETED:
            actions.append('review')
            if role == 'customer':
                actions.append('rebook')
        if status in {
            BookingStatus.PENDING,
            BookingStatus.ACCEPTED,
            BookingStatus.CONFIRMED,
            BookingStatus.ACTIVE,
        }:
            actions.append('chat')
    return actions


async def build_responses(
    session: AsyncSession, request: Request, bookings: list[Booking], viewer: User
) -> list[BookingResponse]:
    from yondo_api.discovery.stats import companion_stats
    from yondo_api.reviews.service import customer_ratings

    settings: Settings = request.app.state.settings
    user_ids = {b.customer_id for b in bookings} | {b.companion_id for b in bookings}
    users = (
        {user.id: user for user in await session.scalars(select(User).where(User.id.in_(user_ids)))}
        if user_ids
        else {}
    )
    companion_rating = await companion_stats(session, {b.companion_id for b in bookings})
    customer_rating = await customer_ratings(session, {b.customer_id for b in bookings})
    profile_names = await _profile_names(session, {b.profile_id for b in bookings})
    now = utc_now()
    responses = []
    for booking in bookings:
        role = role_of(booking, viewer) or 'admin'
        customer, companion = users[booking.customer_id], users[booking.companion_id]
        c_stats = companion_rating.get(companion.id)
        cu_stats = customer_rating.get(customer.id, (None, 0))
        responses.append(
            BookingResponse(
                id=booking.id,
                status=booking.status,
                role=role,
                customer=Party(
                    id=customer.id,
                    display_name=customer.display_name,
                    age=customer.age,
                    gender=customer.gender,
                    rating_average=cu_stats[0],
                    rating_count=cu_stats[1],
                ),
                companion=Party(
                    id=companion.id,
                    display_name=profile_names.get(booking.profile_id, companion.display_name),
                    age=companion.age,
                    gender=companion.gender,
                    rating_average=c_stats.rating_average if c_stats else None,
                    rating_count=c_stats.rating_count if c_stats else 0,
                ),
                profile_id=booking.profile_id,
                service_id=booking.service_id,
                service_code=booking.service_code,
                unit_price_minor=booking.unit_price_minor,
                unit_minutes=booking.unit_minutes,
                currency=booking.currency,
                starts_at=booking.starts_at,
                ends_at=booking.ends_at,
                duration_minutes=booking.duration_minutes,
                timezone=booking.timezone,
                meeting_place=MeetingPlace.model_construct(
                    name=booking.meeting_place_name,
                    address=booking.meeting_address,
                    latitude=booking.meeting_latitude,
                    longitude=booking.meeting_longitude,
                ),
                note=booking.customer_note,
                service_amount_minor=booking.service_amount_minor,
                platform_fee_minor=booking.platform_fee_minor,
                total_minor=booking.total_minor,
                companion_payout_minor=(
                    booking.companion_payout_minor if role in {'companion', 'admin'} else None
                ),
                refund_minor=booking.refund_minor,
                contract=booking.contract,
                contract_version=booking.contract_version,
                customer_accepted_at=booking.customer_accepted_at,
                companion_accepted_at=booking.companion_accepted_at,
                request_expires_at=booking.request_expires_at,
                payment_due_at=booking.payment_due_at,
                confirmed_at=booking.confirmed_at,
                cancelled_at=booking.cancelled_at,
                cancellation_reason=booking.cancellation_reason,
                cancellation_note=booking.cancellation_note,
                customer_checked_in_at=booking.customer_checked_in_at,
                companion_checked_in_at=booking.companion_checked_in_at,
                started_at=booking.started_at,
                ended_at=booking.ended_at,
                no_show_party=booking.no_show_party,
                rebooked_from_id=booking.rebooked_from_id,
                created_at=booking.created_at,
                actions=actions_for(booking, role, now, settings),
            )
        )
    return responses


async def _profile_names(session: AsyncSession, profile_ids: set[UUID]) -> dict[UUID, str]:
    from yondo_api.companions.models import CompanionProfile

    if not profile_ids:
        return {}
    rows = await session.execute(
        select(CompanionProfile.id, CompanionProfile.display_name).where(
            CompanionProfile.id.in_(profile_ids)
        )
    )
    return dict(rows.all())
