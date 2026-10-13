"""Meeting reminder scheduling, recipient isolation, duplicate protection."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select

from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.models.user import AccountStatus, User
from yondo_api.notifications.models import UserNotification
from yondo_api.notifications.reminders import sweep_meeting_reminders

from .test_phases11_15 import confirmed_booking

KINDS = {'meeting_reminder_24h', 'meeting_reminder_1h'}


async def booking_start(e, booking_id):
    async with e['app'].state.db_session_factory() as session:
        row = await session.get(Booking, UUID(booking_id))
        dt = row.starts_at
        return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


async def user_reminders(e, who):
    r = await e['client'].get('/api/v1/notifications', headers=e[who])
    assert r.status_code == 200, r.text
    return [notice for notice in r.json() if notice['kind'] in KINDS]


@pytest.mark.asyncio
async def test_reminders_24h_and_1h_once_per_booking_participant(prepared):
    e = prepared
    bid = await confirmed_booking(e)
    starts = await booking_start(e, bid)
    factory = e['app'].state.db_session_factory
    assert (await sweep_meeting_reminders(
        factory, now=starts - timedelta(hours=48)
    )).notices_created == 0
    first = await sweep_meeting_reminders(
        factory, now=starts - timedelta(hours=24) + timedelta(minutes=2)
    )
    assert first.candidate_bookings == 1
    assert first.notices_created == 2
    assert (await sweep_meeting_reminders(
        factory, now=starts - timedelta(hours=24) + timedelta(minutes=3)
    )).notices_created == 0
    second = await sweep_meeting_reminders(
        factory, now=starts - timedelta(hours=1) + timedelta(minutes=2)
    )
    assert second.notices_created == 2
    assert (await sweep_meeting_reminders(
        factory, now=starts - timedelta(hours=1) + timedelta(minutes=3)
    )).notices_created == 0
    for who in ('customer', 'owner'):
        notices = await user_reminders(e, who)
        assert len(notices) == 2
        assert {row['kind'] for row in notices} == KINDS
        assert all(row['booking_id'] == bid for row in notices)
        assert all(row['gift_order_id'] is None for row in notices)
        assert all(row['details']['minutes_before_start'] in {60, 1440} for row in notices)
        assert all('meeting_place' not in row['details'] for row in notices)
    assert await user_reminders(e, 'other') == []
    assert await user_reminders(e, 'admin') == []


@pytest.mark.asyncio
async def test_missed_window_never_generates_stale_reminder(prepared):
    e = prepared
    bid = await confirmed_booking(e)
    starts = await booking_start(e, bid)
    factory = e['app'].state.db_session_factory
    early = await sweep_meeting_reminders(factory, now=starts - timedelta(hours=24, minutes=1))
    assert early.notices_created == 0
    due = await sweep_meeting_reminders(factory, now=starts - timedelta(hours=24))
    assert due.notices_created == 2
    missed = await sweep_meeting_reminders(factory, now=starts - timedelta(minutes=48))
    assert missed.notices_created == 0
    past = await sweep_meeting_reminders(factory, now=starts + timedelta(minutes=5))
    assert past.notices_created == 0
    assert len(await user_reminders(e, 'customer')) == 1


@pytest.mark.asyncio
async def test_cancelled_booking_has_no_scheduled_reminder(prepared):
    e = prepared
    bid = await confirmed_booking(e)
    starts = await booking_start(e, bid)
    async with e['app'].state.db_session_factory() as session:
        booking = await session.get(Booking, UUID(bid))
        booking.status = BookingStatus.CANCELLED
        await session.commit()
    result = await sweep_meeting_reminders(
        e['app'].state.db_session_factory,
        now=starts - timedelta(hours=1) + timedelta(minutes=1),
    )
    assert result.notices_created == 0
    assert await user_reminders(e, 'customer') == []


@pytest.mark.asyncio
async def test_inactive_companion_blocks_pair_reminders(prepared):
    e = prepared
    bid = await confirmed_booking(e)
    starts = await booking_start(e, bid)
    async with e['app'].state.db_session_factory() as session:
        companion = await session.get(User, UUID(e['owner_id']))
        companion.account_status = AccountStatus.RESTRICTED
        await session.commit()
    result = await sweep_meeting_reminders(
        e['app'].state.db_session_factory,
        now=starts - timedelta(hours=1) + timedelta(minutes=1),
    )
    assert result.notices_created == 0
    assert await user_reminders(e, 'customer') == []


@pytest.mark.asyncio
async def test_invalid_scheduler_clock_or_window_fails_closed(prepared):
    factory = prepared['app'].state.db_session_factory
    with pytest.raises(ValueError, match='timezone-aware'):
        await sweep_meeting_reminders(factory, now=datetime(2027, 1, 1))
    with pytest.raises(ValueError, match='within 0'):
        await sweep_meeting_reminders(
            factory, now=datetime(2027, 1, 1, tzinfo=UTC), window=timedelta(0)
        )


@pytest.mark.asyncio
async def test_repeated_sweeps_are_database_idempotent(prepared):
    e = prepared
    bid = await confirmed_booking(e)
    starts = await booking_start(e, bid)
    factory = e['app'].state.db_session_factory
    for minute in range(1, 6):
        await sweep_meeting_reminders(
            factory, now=starts - timedelta(hours=1) + timedelta(minutes=minute)
        )
    async with factory() as session:
        count = await session.scalar(
            select(func.count()).select_from(UserNotification).where(
                UserNotification.kind == 'meeting_reminder_1h',
                UserNotification.booking_id == UUID(bid),
            )
        )
        assert count == 2


@pytest.mark.asyncio
async def test_postgres_parallel_reminder_workers_do_not_duplicate(prepared):
    e = prepared
    if e['app'].state.db_engine.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL concurrency test only')
    bid = await confirmed_booking(e)
    starts = await booking_start(e, bid)
    factory = e['app'].state.db_session_factory
    results = await asyncio.gather(
        sweep_meeting_reminders(factory, now=starts - timedelta(hours=1)),
        sweep_meeting_reminders(factory, now=starts - timedelta(hours=1)),
    )
    assert sum(r.notices_created for r in results) == 2
    for who in ('customer', 'owner'):
        assert len(await user_reminders(e, who)) == 1
