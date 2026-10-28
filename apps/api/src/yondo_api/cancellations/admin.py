"""Admin endpoints: review events/cases, record no-shows, add and lift restrictions (all audited).

Every mutation writes a `cancellation_audit_entries` row (previous -> new state) and an
`admin_audit_events` row (the console-wide trail) in the same transaction as the change.
"""

from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from yondo_api.admin.models import AdminAuditEvent
from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.cancellations.models import (
    BookingRestriction,
    CancellationAuditEntry,
    CancellationCase,
    CancellationEvent,
)
from yondo_api.cancellations.policy import CancellationPolicy, as_utc, iso_z
from yondo_api.cancellations.schemas import (
    AdminCaseRead,
    AdminEventRead,
    AdminRestrictionRead,
    CancellationAuditRead,
    CaseClose,
    CaseTrigger,
    CountersRead,
    EventKind,
    EventReview,
    ExcuseState,
    NoShowWrite,
    Party,
    RestrictionCreate,
    RestrictionLift,
    ReviewState,
    Role,
    RoleSummary,
    UserCancellationSummary,
)
from yondo_api.cancellations.service import (
    active_restriction,
    add_audit,
    companion_user_id,
    counters_for,
    evaluate_subject,
    event_state,
    record_event,
    utcnow,
)
from yondo_api.companions.dependencies import Admin, Session
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType
from yondo_api.notifications.service import enqueue_booking_notice, enqueue_user_notice

router = APIRouter(prefix='/admin/cancellations', tags=['admin cancellations'])


def _policy(request: Request) -> CancellationPolicy:
    return CancellationPolicy.from_settings(request.app.state.settings)


def _restriction_read(row: BookingRestriction, now: datetime) -> AdminRestrictionRead:
    return AdminRestrictionRead(
        id=row.id,
        user_id=row.user_id,
        role=row.role,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        reason=row.reason,
        case_id=row.case_id,
        created_by=row.created_by,
        lifted_at=row.lifted_at,
        lifted_by=row.lifted_by,
        lift_reason=row.lift_reason,
        active=row.lifted_at is None and as_utc(row.ends_at) > now,
    )


def _admin_trail(session: Session, admin: User, target: UUID, action: str, reason: str) -> None:
    session.add(
        AdminAuditEvent(admin_id=admin.id, target_id=target, action=action, reason=reason)
    )


async def _locked_event(session: Session, event_id: UUID) -> CancellationEvent:
    event = await session.scalar(
        select(CancellationEvent)
        .where(CancellationEvent.id == event_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if event is None:
        raise ApplicationError('cancellation_event_not_found', 'Event not found', 404)
    return event


# ------------------------------------------------------------------------------ events


@router.get('/events', response_model=list[AdminEventRead])
async def list_events(
    admin: Admin,
    session: Session,
    subject_user_id: UUID | None = None,
    booking_id: UUID | None = None,
    kind: EventKind | None = None,
    party: Party | None = None,
    last_minute: bool | None = None,
    excuse_state: ExcuseState | None = None,
    review_state: ReviewState | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
):
    query = select(CancellationEvent)
    for column, value in (
        (CancellationEvent.subject_user_id, subject_user_id),
        (CancellationEvent.booking_id, booking_id),
        (CancellationEvent.kind, kind),
        (CancellationEvent.party, party),
        (CancellationEvent.last_minute, last_minute),
        (CancellationEvent.excuse_state, excuse_state),
        (CancellationEvent.review_state, review_state),
    ):
        if value is not None:
            query = query.where(column == value)
    if since is not None:
        query = query.where(CancellationEvent.occurred_at >= as_utc(since))
    if until is not None:
        query = query.where(CancellationEvent.occurred_at < as_utc(until))
    return list(
        await session.scalars(
            query.order_by(CancellationEvent.occurred_at.desc(), CancellationEvent.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )


@router.post('/events/{event_id}/review', response_model=AdminEventRead)
async def review_event(
    event_id: UUID, payload: EventReview, request: Request, admin: Admin, session: Session
):
    """Excuse an event (emergency accepted: it stops counting) or uphold it (it counts)."""
    event = await _locked_event(session, event_id)
    if event.kind not in ('cancelled', 'no_show'):
        raise ApplicationError('event_not_reviewable', 'This event is not counted', 409)
    previous = event_state(event)
    now = utcnow()
    if payload.decision == 'excuse':
        event.excuse_state = 'granted'
    elif event.excuse_state in ('claimed', 'granted'):
        event.excuse_state = 'rejected'
    event.review_state = 'reviewed'
    event.reviewed_by, event.reviewed_at = admin.id, now
    event.review_note = payload.note.strip()
    add_audit(
        session,
        action='event_reviewed',
        actor_kind='admin',
        actor_user_id=admin.id,
        subject_user_id=event.subject_user_id,
        booking_id=event.booking_id,
        event_id=event.id,
        previous=previous,
        new={**event_state(event), 'decision': payload.decision},
        reason=event.review_note,
    )
    _admin_trail(
        session, admin, event.subject_user_id, f'cancellation_event:{payload.decision}',
        event.review_note,
    )
    policy = _policy(request)
    if policy.tracking_enabled and event.subject_user_id and event.subject_role:
        await evaluate_subject(session, policy, event.subject_user_id, event.subject_role, now)
    await session.commit()
    await session.refresh(event)
    return event


@router.post('/bookings/{booking_id}/no-show', response_model=AdminEventRead, status_code=201)
async def record_no_show(
    booking_id: UUID, payload: NoShowWrite, request: Request, admin: Admin, session: Session
):
    """Record that one participant did not show up (nothing sets 'no-show' elsewhere)."""
    settings = request.app.state.settings
    if not settings.cancellation_tracking_enabled:
        raise ApplicationError(
            'cancellation_tracking_disabled', 'Cancellation tracking is switched off', 409
        )
    booking = await session.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    # Only a paid, confirmed meeting can be missed; a second record covers "both missing".
    if booking.status not in (BookingStatus.CONFIRMED, BookingStatus.NO_SHOW):
        raise ApplicationError(
            'invalid_booking_transition', 'Only a confirmed booking can be a no-show', 409
        )
    now = utcnow()
    if as_utc(booking.starts_at) > now:
        raise ApplicationError('no_show_too_early', 'The booking has not started yet', 409)
    subject = booking.customer_id
    if payload.party == 'companion':
        subject = await companion_user_id(session, booking)
    if subject is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    if await session.scalar(
        select(CancellationEvent.id).where(
            CancellationEvent.booking_id == booking.id,
            CancellationEvent.kind == 'no_show',
            CancellationEvent.subject_user_id == subject,
        )
    ):
        raise ApplicationError('no_show_already_recorded', 'Already recorded', 409)
    previous_status = booking.status
    booking.status = BookingStatus.NO_SHOW
    event = await record_event(
        session, settings, booking,
        kind='no_show', party='admin', actor_user_id=admin.id, subject_user_id=subject,
        subject_role=payload.party, previous_status=previous_status, reason=payload.note,
        excused=payload.excused, now=now,
    )
    await enqueue_booking_notice(
        session, booking, 'booking_no_show', event.id, actor_id=admin.id, recipients='both'
    )
    _admin_trail(session, admin, subject, 'booking_no_show:record', payload.note.strip())
    await session.commit()
    await session.refresh(event)
    return event


# ------------------------------------------------------------------------------ cases


@router.get('/cases', response_model=list[AdminCaseRead])
async def list_cases(
    admin: Admin,
    session: Session,
    status: Literal['open', 'closed'] | None = 'open',
    trigger: CaseTrigger | None = None,
    user_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
):
    query = select(CancellationCase)
    for column, value in (
        (CancellationCase.status, status),
        (CancellationCase.trigger, trigger),
        (CancellationCase.user_id, user_id),
    ):
        if value is not None:
            query = query.where(column == value)
    return list(
        await session.scalars(
            query.order_by(CancellationCase.opened_at.desc(), CancellationCase.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )


async def _locked_case(session: Session, case_id: UUID) -> CancellationCase:
    case = await session.scalar(
        select(CancellationCase)
        .where(CancellationCase.id == case_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if case is None:
        raise ApplicationError('cancellation_case_not_found', 'Case not found', 404)
    return case


def _close_case(
    session: Session, case: CancellationCase, admin: User, resolution: str, note: str, now: datetime
) -> None:
    previous = {'status': case.status, 'resolution': case.resolution}
    case.status, case.resolution = 'closed', resolution
    case.closed_at, case.closed_by, case.note = now, admin.id, note
    add_audit(
        session,
        action='case_closed',
        actor_kind='admin',
        actor_user_id=admin.id,
        subject_user_id=case.user_id,
        case_id=case.id,
        previous=previous,
        new={'status': 'closed', 'resolution': resolution},
        reason=note,
    )


@router.post('/cases/{case_id}/close', response_model=AdminCaseRead)
async def close_case(case_id: UUID, payload: CaseClose, admin: Admin, session: Session):
    """Review finished without a restriction. A closed case moves the counting baseline."""
    case = await _locked_case(session, case_id)
    if case.status != 'open':
        raise ApplicationError('case_not_open', 'The case is already closed', 409)
    note = payload.note.strip()
    _close_case(session, case, admin, 'no_action', note, utcnow())
    _admin_trail(session, admin, case.user_id, 'cancellation_case:close', note)
    await session.commit()
    await session.refresh(case)
    return case


# ------------------------------------------------------------------------------ restrictions


@router.get('/restrictions', response_model=list[AdminRestrictionRead])
async def list_restrictions(
    admin: Admin,
    session: Session,
    user_id: UUID | None = None,
    role: Role | None = None,
    active: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
):
    now = utcnow()
    query = select(BookingRestriction)
    if user_id is not None:
        query = query.where(BookingRestriction.user_id == user_id)
    if role is not None:
        query = query.where(BookingRestriction.role == role)
    if active is True:
        query = query.where(
            BookingRestriction.lifted_at.is_(None), BookingRestriction.ends_at > now
        )
    elif active is False:
        query = query.where(
            (BookingRestriction.lifted_at.is_not(None)) | (BookingRestriction.ends_at <= now)
        )
    rows = await session.scalars(
        query.order_by(BookingRestriction.created_at.desc(), BookingRestriction.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return [_restriction_read(row, now) for row in rows]


@router.post('/restrictions', response_model=AdminRestrictionRead, status_code=201)
async def create_restriction(
    payload: RestrictionCreate, request: Request, admin: Admin, session: Session
):
    """The only way a restriction starts: a temporary, reasoned, audited admin decision."""
    policy = _policy(request)
    if payload.user_id == admin.id:
        raise ApplicationError('admin_self_change_forbidden', 'Cannot restrict yourself', 403)
    days = payload.duration_days or policy.restriction_default_days
    if days > policy.restriction_max_days:
        raise ApplicationError(
            'restriction_too_long',
            f'A restriction lasts at most {policy.restriction_max_days} days',
            422,
        )
    user = await session.scalar(
        select(User).where(User.id == payload.user_id).with_for_update()
    )
    if user is None or user.account_status == AccountStatus.DELETED:
        raise ApplicationError('user_not_found', 'User not found', 404)
    if await session.get(UserRole, (user.id, UserRoleType.ADMIN)) is not None:
        raise ApplicationError(
            'admin_target_forbidden', 'Admin accounts require separate review', 403
        )
    if await session.get(UserRole, (user.id, UserRoleType(payload.role))) is None:
        raise ApplicationError('restriction_role_mismatch', 'The user lacks that role', 422)
    now = utcnow()
    if await active_restriction(session, user.id, payload.role, now) is not None:
        raise ApplicationError('restriction_already_active', 'A restriction is already active', 409)
    case = None
    if payload.case_id is not None:
        case = await _locked_case(session, payload.case_id)
        if case.user_id != user.id or case.role != payload.role:
            raise ApplicationError('case_user_mismatch', 'The case belongs to another user', 422)
        if case.status != 'open':
            raise ApplicationError('case_not_open', 'The case is already closed', 409)
    reason = payload.reason.strip()
    row = BookingRestriction(
        user_id=user.id, role=payload.role, starts_at=now, ends_at=now + timedelta(days=days),
        reason=reason, case_id=payload.case_id, created_by=admin.id,
    )
    session.add(row)
    await session.flush()
    add_audit(
        session,
        action='restriction_created',
        actor_kind='admin',
        actor_user_id=admin.id,
        subject_user_id=user.id,
        restriction_id=row.id,
        case_id=payload.case_id,
        previous={'active': False},
        new={'active': True, 'role': payload.role, 'ends_at': iso_z(row.ends_at),
             'duration_days': days},
        reason=reason,
    )
    if case is not None:
        _close_case(session, case, admin, 'restricted', reason, now)
    _admin_trail(session, admin, user.id, 'booking_restriction:create', reason)
    await enqueue_user_notice(
        session, user.id, 'booking_restricted', row.id, actor_id=admin.id,
        details={'role': payload.role, 'ends_at': iso_z(row.ends_at)},
    )
    await session.commit()
    await session.refresh(row)
    return _restriction_read(row, now)


@router.post('/restrictions/{restriction_id}/lift', response_model=AdminRestrictionRead)
async def lift_restriction(
    restriction_id: UUID, payload: RestrictionLift, admin: Admin, session: Session
):
    row = await session.scalar(
        select(BookingRestriction)
        .where(BookingRestriction.id == restriction_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise ApplicationError('restriction_not_found', 'Restriction not found', 404)
    now = utcnow()
    if row.lifted_at is not None or as_utc(row.ends_at) <= now:
        raise ApplicationError('restriction_not_active', 'The restriction is not active', 409)
    reason = payload.reason.strip()
    row.lifted_at, row.lifted_by, row.lift_reason = now, admin.id, reason
    add_audit(
        session,
        action='restriction_lifted',
        actor_kind='admin',
        actor_user_id=admin.id,
        subject_user_id=row.user_id,
        restriction_id=row.id,
        previous={'active': True, 'ends_at': iso_z(row.ends_at)},
        new={'active': False, 'lifted_at': iso_z(now)},
        reason=reason,
    )
    _admin_trail(session, admin, row.user_id, 'booking_restriction:lift', reason)
    await enqueue_user_notice(
        session, row.user_id, 'booking_restriction_lifted', row.id, actor_id=admin.id,
        details={'role': row.role},
    )
    await session.commit()
    await session.refresh(row)
    return _restriction_read(row, now)


# ------------------------------------------------------------------------------ audit, summary


@router.get('/audit', response_model=list[CancellationAuditRead])
async def list_audit(
    admin: Admin,
    session: Session,
    subject_user_id: UUID | None = None,
    booking_id: UUID | None = None,
    event_id: UUID | None = None,
    restriction_id: UUID | None = None,
    case_id: UUID | None = None,
    action: str | None = Query(default=None, max_length=40, pattern=r'^[a-z_]+$'),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
):
    query = select(CancellationAuditEntry)
    for column, value in (
        (CancellationAuditEntry.subject_user_id, subject_user_id),
        (CancellationAuditEntry.booking_id, booking_id),
        (CancellationAuditEntry.event_id, event_id),
        (CancellationAuditEntry.restriction_id, restriction_id),
        (CancellationAuditEntry.case_id, case_id),
        (CancellationAuditEntry.action, action),
    ):
        if value is not None:
            query = query.where(column == value)
    return list(
        await session.scalars(
            query.order_by(
                CancellationAuditEntry.created_at.desc(), CancellationAuditEntry.id.desc()
            )
            .offset(offset)
            .limit(limit)
        )
    )


@router.get('/users/{user_id}/summary', response_model=UserCancellationSummary)
async def user_summary(user_id: UUID, request: Request, admin: Admin, session: Session):
    user = await session.get(User, user_id)
    if user is None:
        raise ApplicationError('user_not_found', 'User not found', 404)
    policy, now = _policy(request), utcnow()
    roles: list[RoleSummary] = []
    held = {r.role.value for r in user.roles}
    for role in ('customer', 'companion'):
        if role not in held:
            continue
        counters = await counters_for(session, policy, user.id, role, now)
        open_cases = list(
            await session.scalars(
                select(CancellationCase.id).where(
                    CancellationCase.user_id == user.id,
                    CancellationCase.role == role,
                    CancellationCase.status == 'open',
                )
            )
        )
        restriction = await active_restriction(session, user.id, role, now)
        roles.append(
            RoleSummary(
                role=role,
                window_days=policy.window_days,
                counters=CountersRead(
                    cancellations=counters.cancellations,
                    last_minute=counters.last_minute,
                    no_shows=counters.no_shows,
                    emergency_claims=counters.emergency_claims,
                    excused=counters.excused,
                ),
                thresholds=policy.thresholds(),
                needs_review=bool(open_cases),
                open_case_ids=open_cases,
                active_restriction=_restriction_read(restriction, now) if restriction else None,
            )
        )
    return UserCancellationSummary(user_id=user.id, roles=roles)
