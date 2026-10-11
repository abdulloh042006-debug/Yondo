from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.bookings.schemas import BookingCancel, BookingCreate, BookingResponse
from yondo_api.chat.service import append_system_message, publish
from yondo_api.companions import service as companion_service
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.companions.models import (
    CompanionApplication,
    CompanionAvailability,
    CompanionProfile,
    CompanionService,
)
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType

router = APIRouter(prefix='/bookings', tags=['bookings'])
RESERVING_STATUSES = (
    BookingStatus.PENDING,
    BookingStatus.ACCEPTED,
    BookingStatus.CONFIRMED,
    BookingStatus.ACTIVE,
)


async def _active_customer(principal: Principal, session: Session) -> User:
    user = await session.get(User, principal.user.id)
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    if await session.get(UserRole, (user.id, UserRoleType.CUSTOMER)) is None:
        raise ApplicationError('customer_role_required', 'Customer role is required', 403)
    return user


async def _booking(session: Session, booking_id: UUID) -> Booking:
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    return booking


async def _participant(session: Session, booking: Booking, user_id: UUID) -> tuple[bool, bool]:
    profile_owner_id = await session.scalar(
        select(CompanionApplication.user_id)
        .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
        .where(CompanionProfile.id == booking.profile_id)
    )
    is_customer = booking.customer_id == user_id
    is_companion = profile_owner_id == user_id
    if not (is_customer or is_companion):
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    user = await session.get(User, user_id)
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    required_role = UserRoleType.CUSTOMER if is_customer else UserRoleType.COMPANION
    if await session.get(UserRole, (user_id, required_role)) is None:
        raise ApplicationError('account_role_required', 'The required account role is missing', 403)
    return is_customer, is_companion


async def _public_profile(session: Session, profile_id: UUID, request):
    row = (
        await session.execute(
            select(CompanionProfile, User)
            .join(CompanionApplication, CompanionApplication.id == CompanionProfile.application_id)
            .join(User, User.id == CompanionApplication.user_id)
            .where(CompanionProfile.id == profile_id)
        )
    ).first()
    if row is None:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    profile, user = row
    status = await companion_service.companion_status(
        session, user, profile, request.app.state.identity_eligibility
    )
    if not status.publicly_active:
        raise ApplicationError('companion_not_found', 'Companion not found', 404)
    return profile


@router.post('', response_model=BookingResponse, status_code=201)
async def create_booking(
    payload: BookingCreate, request: Request, principal: Principal, session: Session
):
    customer = await _active_customer(principal, session)
    service_item = await session.get(CompanionService, payload.service_id)
    if service_item is None:
        raise ApplicationError('companion_service_not_found', 'Service not found', 404)
    profile = await _public_profile(session, service_item.profile_id, request)

    # Serialize requests for the same companion; PostgreSQL also has a GiST exclusion
    # constraint as the final concurrency guard.
    profile = await companion_service.profile_for(
        session,
        await session.scalar(
            select(CompanionApplication.user_id).where(
                CompanionApplication.id == profile.application_id
            )
        ),
    )
    if payload.duration_minutes % service_item.unit_minutes:
        raise ApplicationError(
            'invalid_booking_duration',
            'Duration must be a whole number of the service pricing unit',
            422,
        )
    try:
        ends_at = payload.starts_at + timedelta(minutes=payload.duration_minutes)
    except OverflowError as exc:
        raise ApplicationError(
            'invalid_booking_interval', 'Booking interval is invalid', 422
        ) from exc
    if payload.starts_at <= datetime.now(UTC):
        raise ApplicationError('booking_start_in_past', 'Booking must start in the future', 422)
    availability = select(CompanionAvailability.id).where(
        CompanionAvailability.profile_id == profile.id,
        CompanionAvailability.starts_at <= payload.starts_at,
        CompanionAvailability.ends_at >= ends_at,
    )
    if await session.scalar(availability) is None:
        raise ApplicationError('availability_not_found', 'The companion is not available then', 409)
    overlap = select(Booking.id).where(
        Booking.profile_id == profile.id,
        Booking.status.in_(RESERVING_STATUSES),
        Booking.starts_at < ends_at,
        Booking.ends_at > payload.starts_at,
    )
    if await session.scalar(overlap) is not None:
        raise ApplicationError('booking_time_unavailable', 'That time is already reserved', 409)
    units = payload.duration_minutes // service_item.unit_minutes
    booking = Booking(
        customer_id=customer.id,
        profile_id=profile.id,
        service_id=service_item.id,
        status=BookingStatus.PENDING,
        service_code=service_item.service_code,
        service_description=service_item.description,
        starts_at=payload.starts_at,
        ends_at=ends_at,
        timezone=payload.timezone,
        duration_minutes=payload.duration_minutes,
        meeting_place=payload.meeting_place,
        price_minor=service_item.price_minor * units,
        currency=service_item.currency,
        customer_contract_accepted_at=datetime.now(UTC),
    )
    session.add(booking)
    await session.flush()
    system_message = append_system_message(
        session, booking.id, 'booking_requested', {'status': booking.status}
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            'booking_time_unavailable', 'That time is already reserved', 409
        ) from exc
    await session.refresh(booking)
    await session.refresh(system_message)
    await publish(request, system_message)
    return booking


@router.get('', response_model=list[BookingResponse])
async def list_bookings(
    principal: Principal,
    session: Session,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    companion_user_id = (
        select(CompanionApplication.user_id)
        .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
        .where(CompanionProfile.id == Booking.profile_id)
        .scalar_subquery()
    )
    query = (
        select(Booking)
        .where(
            or_(Booking.customer_id == principal.user.id, companion_user_id == principal.user.id)
        )
        .order_by(Booking.starts_at.desc(), Booking.id)
        .offset(offset)
        .limit(limit)
    )
    return list(await session.scalars(query))


@router.get('/{booking_id}', response_model=BookingResponse)
async def get_booking(booking_id: UUID, principal: Principal, session: Session):
    booking = await _booking(session, booking_id)
    await _participant(session, booking, principal.user.id)
    return booking


@router.post('/{booking_id}/accept', response_model=BookingResponse)
async def accept_booking(
    booking_id: UUID, request: Request, principal: Principal, session: Session
):
    booking = await _booking(session, booking_id)
    _, is_companion = await _participant(session, booking, principal.user.id)
    if not is_companion:
        raise ApplicationError('companion_role_required', 'Only the companion can accept', 403)
    if booking.status != BookingStatus.PENDING:
        raise ApplicationError(
            'invalid_booking_transition', 'Only pending bookings can be accepted', 409
        )
    booking.status = BookingStatus.ACCEPTED
    booking.companion_contract_accepted_at = datetime.now(UTC)
    system_message = append_system_message(
        session, booking.id, 'booking_accepted', {'status': booking.status}
    )
    await session.commit()
    await session.refresh(booking)
    await session.refresh(system_message)
    await publish(request, system_message)
    return booking


@router.post('/{booking_id}/decline', response_model=BookingResponse)
async def decline_booking(
    booking_id: UUID,
    payload: BookingCancel,
    request: Request,
    principal: Principal,
    session: Session,
):
    booking = await _booking(session, booking_id)
    _, is_companion = await _participant(session, booking, principal.user.id)
    if not is_companion:
        raise ApplicationError('companion_role_required', 'Only the companion can decline', 403)
    if booking.status != BookingStatus.PENDING:
        raise ApplicationError(
            'invalid_booking_transition', 'Only pending bookings can be declined', 409
        )
    booking.status = BookingStatus.CANCELLED
    system_message = append_system_message(
        session, booking.id, 'booking_declined', {'status': booking.status}
    )
    await session.commit()
    await session.refresh(booking)
    await session.refresh(system_message)
    await publish(request, system_message)
    return booking


@router.post('/{booking_id}/cancel', response_model=BookingResponse)
async def cancel_booking(
    booking_id: UUID,
    payload: BookingCancel,
    request: Request,
    principal: Principal,
    session: Session,
):
    booking = await _booking(session, booking_id)
    await _participant(session, booking, principal.user.id)
    if booking.status not in {
        BookingStatus.PENDING,
        BookingStatus.ACCEPTED,
        BookingStatus.CONFIRMED,
    }:
        raise ApplicationError(
            'invalid_booking_transition', 'This booking can no longer be cancelled', 409
        )
    booking.status = BookingStatus.CANCELLED
    system_message = append_system_message(
        session, booking.id, 'booking_cancelled', {'status': booking.status}
    )
    await session.commit()
    await session.refresh(booking)
    await session.refresh(system_message)
    await publish(request, system_message)
    return booking
