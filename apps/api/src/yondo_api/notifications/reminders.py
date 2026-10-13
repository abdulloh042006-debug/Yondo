"""Idempotent 24-hour and 1-hour in-app meeting reminders.

Run a sweep every five minutes. Nothing is pushed externally.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.companions.models import CompanionApplication, CompanionProfile
from yondo_api.models.user import AccountStatus, User
from yondo_api.notifications.models import UserNotification

REMINDER_WINDOWS = (
    ('meeting_reminder_24h', timedelta(hours=24)),
    ('meeting_reminder_1h', timedelta(hours=1)),
)
DEFAULT_WINDOW = timedelta(minutes=10)
MAX_CANDIDATES = 5000


@dataclass(frozen=True, slots=True)
class ReminderSweepResult:
    candidate_bookings: int
    notices_created: int
    bookings_processed: int


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('Reminder scheduler requires timezone-aware UTC timestamps')
    return value.astimezone(UTC)


def _stored_utc(value: datetime) -> datetime:
    # SQLite loses stored TZ information. Booking timestamps are UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def _active_participants(session: AsyncSession, booking: Booking) -> set[UUID]:
    customer = await session.get(User, booking.customer_id)
    companion = await session.scalar(
        select(User)
        .join(CompanionApplication, CompanionApplication.user_id == User.id)
        .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
        .where(CompanionProfile.id == booking.profile_id)
    )
    if (
        customer is None
        or companion is None
        or customer.account_status != AccountStatus.ACTIVE
        or companion.account_status != AccountStatus.ACTIVE
        or customer.id == companion.id
    ):
        return set()
    return {customer.id, companion.id}


def _notice_insert(
    session: AsyncSession,
    booking: Booking,
    recipient_id: UUID,
    kind: str,
    lead: timedelta,
    now: datetime,
):
    values = {
        'id': uuid4(),
        'recipient_id': recipient_id,
        'actor_id': None,
        'booking_id': booking.id,
        'gift_order_id': None,
        'kind': kind,
        'source_key': f'{kind}:{booking.id}',
        'details': {
            'booking_id': str(booking.id),
            'starts_at': _stored_utc(booking.starts_at).isoformat(),
            'timezone': booking.timezone,
            'minutes_before_start': int(lead.total_seconds() // 60),
        },
        'created_at': now,
        'updated_at': now,
    }
    dialect = session.get_bind().dialect.name
    if dialect == 'postgresql':
        stmt = pg_insert(UserNotification).values(**values)
    elif dialect == 'sqlite':
        stmt = sqlite_insert(UserNotification).values(**values)
    else:
        raise RuntimeError('Reminders require PostgreSQL or SQLite')
    return stmt.on_conflict_do_nothing(index_elements=['recipient_id', 'source_key'])


async def sweep_meeting_reminders(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    now: datetime | None = None,
    window: timedelta = DEFAULT_WINDOW,
) -> ReminderSweepResult:
    """Queue reminders only for currently confirmed bookings and active participants.

    Booking FOR UPDATE SKIP LOCKED serializes against booking cancellation on
    PostgreSQL. ON CONFLICT and a unique index deduplicate overlapping workers.
    Each booking commits independently so failures can safely be retried.
    """
    instant = _utc(now if now is not None else datetime.now(UTC))
    if not timedelta(0) < window <= timedelta(minutes=30):
        raise ValueError('Reminder sweep window must be within 0–30 minutes')
    candidates: list[tuple[UUID, str, timedelta]] = []
    async with session_factory() as session:
        for kind, lead in REMINDER_WINDOWS:
            ids = await session.scalars(
                select(Booking.id)
                .where(
                    Booking.status == BookingStatus.CONFIRMED,
                    Booking.starts_at > instant + lead - window,
                    Booking.starts_at <= instant + lead,
                )
                .order_by(Booking.starts_at, Booking.id)
                .limit(MAX_CANDIDATES)
            )
            candidates.extend((id_, kind, lead) for id_ in ids)

    created = processed = 0
    for booking_id, kind, lead in candidates:
        async with session_factory() as session:
            booking = await session.scalar(
                select(Booking).where(Booking.id == booking_id)
                .with_for_update(skip_locked=True)
                .execution_options(populate_existing=True)
            )
            if (
                booking is None
                or booking.status != BookingStatus.CONFIRMED
                or not instant + lead - window < _stored_utc(booking.starts_at) <= instant + lead
            ):
                continue
            recipients = await _active_participants(session, booking)
            if not recipients:
                continue
            for recipient in recipients:
                result = await session.execute(
                    _notice_insert(session, booking, recipient, kind, lead, instant)
                )
                created += result.rowcount or 0
            await session.commit()
            processed += 1
    return ReminderSweepResult(len(candidates), created, processed)
