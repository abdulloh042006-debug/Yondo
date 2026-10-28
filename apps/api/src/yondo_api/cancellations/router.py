"""User-facing cancellation endpoints: own events, own restrictions, dispute an event."""

from uuid import UUID

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from yondo_api.api.errors import ApplicationError
from yondo_api.cancellations.models import BookingRestriction, CancellationEvent
from yondo_api.cancellations.policy import CancellationPolicy, as_utc
from yondo_api.cancellations.schemas import DisputeWrite, MyEventRead, MyRestrictionRead
from yondo_api.cancellations.service import (
    add_audit,
    evaluate_subject,
    event_state,
    utcnow,
)
from yondo_api.companions.dependencies import Principal, Session

router = APIRouter(prefix='/cancellations', tags=['cancellations'])
REVIEWABLE_KINDS = ('cancelled', 'no_show')


@router.get('/me/events', response_model=list[MyEventRead])
async def my_events(
    principal: Principal,
    session: Session,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
):
    """Events counted against the caller only; other people's events are never readable."""
    return list(
        await session.scalars(
            select(CancellationEvent)
            .where(CancellationEvent.subject_user_id == principal.user.id)
            .order_by(CancellationEvent.occurred_at.desc(), CancellationEvent.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )


@router.get('/me/restrictions', response_model=list[MyRestrictionRead])
async def my_restrictions(
    principal: Principal,
    session: Session,
    active_only: bool = True,
    limit: int = Query(default=30, ge=1, le=100),
):
    now = utcnow()
    query = select(BookingRestriction).where(BookingRestriction.user_id == principal.user.id)
    if active_only:
        query = query.where(
            BookingRestriction.lifted_at.is_(None), BookingRestriction.ends_at > now
        )
    rows = await session.scalars(query.order_by(BookingRestriction.ends_at.desc()).limit(limit))
    return [
        MyRestrictionRead(
            id=r.id,
            role=r.role,
            starts_at=r.starts_at,
            ends_at=r.ends_at,
            active=r.lifted_at is None and as_utc(r.ends_at) > now,
            lifted_at=r.lifted_at,
        )
        for r in rows
    ]


@router.post('/me/events/{event_id}/dispute', response_model=MyEventRead)
async def dispute_event(
    event_id: UUID, payload: DisputeWrite, request: Request, principal: Principal, session: Session
):
    """Contest an event and/or claim an emergency. An admin decides; a claim does not count."""
    event = await session.scalar(
        select(CancellationEvent)
        .where(
            CancellationEvent.id == event_id,
            CancellationEvent.subject_user_id == principal.user.id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if event is None:
        raise ApplicationError('cancellation_event_not_found', 'Event not found', 404)
    if event.kind not in REVIEWABLE_KINDS:
        raise ApplicationError('event_not_disputable', 'This event cannot be disputed', 409)
    if event.review_state == 'open':
        raise ApplicationError('dispute_already_open', 'A review is already pending', 409)
    if event.review_state == 'reviewed':
        raise ApplicationError('event_already_reviewed', 'An admin already decided', 409)
    previous = event_state(event)
    event.dispute_note = payload.note.strip()
    event.disputed_at = utcnow()
    event.review_state = 'open'
    if payload.emergency and event.excuse_state == 'none':
        event.excuse_state = 'claimed'
    add_audit(
        session,
        action='dispute_filed',
        actor_kind=event.subject_role or 'customer',
        actor_user_id=principal.user.id,
        subject_user_id=principal.user.id,
        booking_id=event.booking_id,
        event_id=event.id,
        previous=previous,
        new=event_state(event),
        reason=event.dispute_note,
    )
    policy = CancellationPolicy.from_settings(request.app.state.settings)
    if policy.tracking_enabled and event.subject_role:
        await evaluate_subject(session, policy, principal.user.id, event.subject_role, utcnow())
    await session.commit()
    await session.refresh(event)
    return event
