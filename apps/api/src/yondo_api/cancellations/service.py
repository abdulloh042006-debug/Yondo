"""Cancellation tracking: record events, count them, open review cases, enforce restrictions.

Security-sensitive. Rules that hold everywhere in this module:
* no money, refund or fee logic; no automatic restriction (a threshold only opens a review case);
* callers own the transaction: every function adds rows to the caller's session and never
  commits, so an event is stored atomically with the booking transition that caused it;
* `utcnow` is the single clock (tests replace it); inputs are never trusted for timestamps.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking
from yondo_api.cancellations.models import (
    CASE_TRIGGERS,
    BookingRestriction,
    CancellationAuditEntry,
    CancellationCase,
    CancellationEvent,
)
from yondo_api.cancellations.policy import (
    CancellationPolicy,
    CountedEvent,
    Counters,
    as_utc,
    counts_as_cancellation,
    is_last_minute,
    iso_z,
    lead_seconds,
    summarize,
)
from yondo_api.companions.models import CompanionApplication, CompanionProfile
from yondo_api.config import Settings
from yondo_api.notifications.service import enqueue_user_notice


def utcnow() -> datetime:
    return datetime.now(UTC)


async def companion_user_id(session: AsyncSession, booking: Booking) -> UUID | None:
    return await session.scalar(
        select(CompanionApplication.user_id)
        .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
        .where(CompanionProfile.id == booking.profile_id)
    )


def event_state(event: CancellationEvent) -> dict:
    """The mutable review state of an event, as stored in audit previous/new snapshots."""
    return {
        'excuse_state': event.excuse_state,
        'review_state': event.review_state,
        'reviewed_by': str(event.reviewed_by) if event.reviewed_by else None,
    }


def add_audit(
    session: AsyncSession,
    *,
    action: str,
    actor_kind: str,
    actor_user_id: UUID | None,
    subject_user_id: UUID | None,
    booking_id: UUID | None = None,
    event_id: UUID | None = None,
    case_id: UUID | None = None,
    restriction_id: UUID | None = None,
    previous: dict | None = None,
    new: dict | None = None,
    reason: str | None = None,
) -> CancellationAuditEntry:
    entry = CancellationAuditEntry(
        action=action,
        actor_kind=actor_kind,
        actor_user_id=actor_user_id,
        subject_user_id=subject_user_id,
        booking_id=booking_id,
        event_id=event_id,
        case_id=case_id,
        restriction_id=restriction_id,
        previous_state=previous,
        new_state=new,
        reason=reason,
        created_at=utcnow(),  # microsecond order inside one transaction
    )
    session.add(entry)
    return entry


# ---------------------------------------------------------------- counting and review cases


async def counters_for(
    session: AsyncSession, policy: CancellationPolicy, user_id: UUID, role: str, now: datetime
) -> Counters:
    window_start = policy.window_start(now)
    rows = (
        await session.execute(
            select(
                CancellationEvent.kind,
                CancellationEvent.excuse_state,
                CancellationEvent.last_minute,
                CancellationEvent.booking_status_before,
                CancellationEvent.occurred_at,
            ).where(
                CancellationEvent.subject_user_id == user_id,
                CancellationEvent.subject_role == role,
                CancellationEvent.occurred_at >= window_start,
            )
        )
    ).all()
    closed = dict(
        (
            await session.execute(
                select(CancellationCase.trigger, func.max(CancellationCase.closed_at))
                .where(
                    CancellationCase.user_id == user_id,
                    CancellationCase.role == role,
                    CancellationCase.status == 'closed',
                )
                .group_by(CancellationCase.trigger)
            )
        ).all()
    )
    since = {
        trigger: max(window_start, as_utc(closed[trigger])) if closed.get(trigger) else window_start
        for trigger in CASE_TRIGGERS
    }
    events = [
        CountedEvent(
            kind=row.kind,
            excuse_state=row.excuse_state,
            last_minute=row.last_minute,
            booking_status_before=row.booking_status_before,
            occurred_at=as_utc(row.occurred_at),
        )
        for row in rows
    ]
    return summarize(events, policy, since)


async def _open_case(
    session: AsyncSession,
    user_id: UUID,
    role: str,
    trigger: str,
    snapshot: dict,
    now: datetime,
) -> CancellationCase | None:
    existing = await session.scalar(
        select(CancellationCase.id).where(
            CancellationCase.user_id == user_id,
            CancellationCase.role == role,
            CancellationCase.trigger == trigger,
            CancellationCase.status == 'open',
        )
    )
    if existing is not None:
        return None
    case = CancellationCase(
        user_id=user_id, role=role, trigger=trigger, status='open', snapshot=snapshot,
        opened_at=now,
    )
    try:
        # A concurrent event of the same user may open the same case: the partial unique index
        # decides, and losing the race must never fail the booking transition around it.
        async with session.begin_nested():
            session.add(case)
            await session.flush()
    except IntegrityError:
        return None
    add_audit(
        session,
        action='case_opened',
        actor_kind='system',
        actor_user_id=None,
        subject_user_id=user_id,
        case_id=case.id,
        new={'role': role, 'trigger': trigger, **snapshot},
    )
    return case


async def evaluate_subject(
    session: AsyncSession,
    policy: CancellationPolicy,
    user_id: UUID,
    role: str,
    now: datetime,
    *,
    new_counted_event: CancellationEvent | None = None,
) -> None:
    """Warn at the warning threshold and open review cases at the review thresholds."""
    await session.flush()
    counters = await counters_for(session, policy, user_id, role, now)
    if (
        new_counted_event is not None
        and policy.warning_threshold
        and counters.cancellations == policy.warning_threshold
    ):
        await enqueue_user_notice(
            session,
            user_id,
            'cancellation_warning',
            new_counted_event.id,
            booking_id=new_counted_event.booking_id,
            details={
                'role': role,
                'count': counters.cancellations,
                'window_days': policy.window_days,
            },
        )
        add_audit(
            session,
            action='warning_sent',
            actor_kind='system',
            actor_user_id=None,
            subject_user_id=user_id,
            booking_id=new_counted_event.booking_id,
            event_id=new_counted_event.id,
            new={'role': role, 'count': counters.cancellations,
                 'threshold': policy.warning_threshold},
        )
    for trigger, threshold in policy.thresholds().items():
        count = counters.get(trigger)
        if threshold and count >= threshold:
            await _open_case(
                session,
                user_id,
                role,
                trigger,
                {'count': count, 'threshold': threshold, 'window_days': policy.window_days},
                now,
            )


# ---------------------------------------------------------------- recording events


async def record_event(
    session: AsyncSession,
    settings: Settings,
    booking: Booking,
    *,
    kind: str,
    party: str,
    actor_user_id: UUID | None,
    subject_user_id: UUID | None,
    subject_role: str | None,
    previous_status: str,
    reason: str = '',
    emergency: bool = False,
    excused: bool = False,
    now: datetime | None = None,
) -> CancellationEvent | None:
    """Store one event (plus audit entry) and re-evaluate the subject. None = tracking is off."""
    policy = CancellationPolicy.from_settings(settings)
    if not policy.tracking_enabled:
        return None
    now = now or utcnow()
    lead = lead_seconds(booking.starts_at, now)
    claimed = emergency and not excused
    event = CancellationEvent(
        booking_id=booking.id,
        kind=kind,
        party=party,
        actor_user_id=actor_user_id,
        subject_user_id=subject_user_id,
        subject_role=subject_role,
        booking_status_before=previous_status,
        booking_starts_at=as_utc(booking.starts_at),
        occurred_at=now,
        lead_seconds=lead,
        last_minute=kind in ('cancelled', 'declined')
        and is_last_minute(lead, policy.last_minute_hours),
        reason=reason.strip(),
        excuse_state='granted' if excused else 'claimed' if claimed else 'none',
        review_state='open' if claimed else 'none',
    )
    session.add(event)
    await session.flush()
    add_audit(
        session,
        action='event_recorded',
        actor_kind=party,
        actor_user_id=actor_user_id,
        subject_user_id=subject_user_id,
        booking_id=booking.id,
        event_id=event.id,
        new={
            'kind': kind,
            'party': party,
            'booking_status_before': previous_status,
            'lead_seconds': lead,
            'last_minute': event.last_minute,
            **event_state(event),
        },
        reason=event.reason or None,
    )
    countable = kind in ('cancelled', 'no_show')
    if subject_user_id is not None and subject_role is not None and countable:
        counted = kind == 'cancelled' and counts_as_cancellation(
            CountedEvent(kind, event.excuse_state, event.last_minute, previous_status, now),
            policy,
        )
        await evaluate_subject(
            session, policy, subject_user_id, subject_role, now,
            new_counted_event=event if counted else None,
        )
    return event


async def record_cancellation(
    session: AsyncSession,
    settings: Settings,
    booking: Booking,
    *,
    actor_user_id: UUID,
    is_customer: bool,
    previous_status: str,
    reason: str,
    emergency: bool,
    declined: bool = False,
) -> CancellationEvent | None:
    """A participant cancelled (or the companion declined) a booking. Call before commit."""
    role = 'customer' if is_customer else 'companion'
    return await record_event(
        session, settings, booking,
        kind='declined' if declined else 'cancelled',
        party=role,
        actor_user_id=actor_user_id,
        subject_user_id=actor_user_id,
        subject_role=role,
        previous_status=previous_status,
        reason=reason,
        emergency=emergency and not declined,
    )


async def record_expiry(
    session: AsyncSession, settings: Settings, booking: Booking, previous_status: str,
    now: datetime | None = None,
) -> None:
    """The system expired a request nobody confirmed: recorded for the trail, never counted."""
    await record_event(
        session, settings, booking,
        kind='expired', party='system', actor_user_id=None, subject_user_id=None,
        subject_role=None, previous_status=previous_status, now=now,
    )


# ---------------------------------------------------------------- restrictions


async def active_restriction(
    session: AsyncSession, user_id: UUID, role: str, now: datetime | None = None
) -> BookingRestriction | None:
    now = now or utcnow()
    return await session.scalar(
        select(BookingRestriction)
        .where(
            BookingRestriction.user_id == user_id,
            BookingRestriction.role == role,
            BookingRestriction.lifted_at.is_(None),
            BookingRestriction.ends_at > now,
        )
        .order_by(BookingRestriction.ends_at.desc())
        .limit(1)
    )


async def assert_not_restricted(session: AsyncSession, user_id: UUID, role: str) -> None:
    """403 `booking_restricted` with the end time. Never reveals the reason or other users."""
    restriction = await active_restriction(session, user_id, role)
    if restriction is not None:
        raise ApplicationError(
            'booking_restricted',
            'Booking is temporarily restricted for this account',
            403,
            details={'role': role, 'ends_at': iso_z(restriction.ends_at)},
        )
