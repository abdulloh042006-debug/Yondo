"""Cancellation tracking through the real API: who/when/why, thresholds, excuses, no-shows."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from yondo_api.account.deletion import erase_account
from yondo_api.bookings.expiry import expire_stale_bookings
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.cancellations import service as cancellation_service
from yondo_api.cancellations.models import (
    CancellationAuditEntry,
    CancellationCase,
    CancellationEvent,
)
from yondo_api.models.user import User

from .cancellation_helpers import (
    ADMIN,
    API,
    STARTS,
    admin_events,
    book,
    cancel,
    configure,
    freeze,
    notices,
    summary,
    user_id,
)
from .test_bookings import booking_payload, setup_bookable_companion
from .test_phases11_15 import confirmed_booking


@pytest.mark.asyncio
async def test_customer_cancellation_is_tracked_audited_and_notified(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await book(e, service)
    response = await cancel(e, 'customer', booking_id, reason='Plans changed')
    assert response.status_code == 200 and response.json()['status'] == 'cancelled'

    (event,) = await admin_events(e, booking_id=booking_id)
    customer_id = await user_id(e, e['customer'])
    assert (event['kind'], event['party'], event['subject_role']) == (
        'cancelled', 'customer', 'customer')
    assert event['subject_user_id'] == customer_id == event['actor_user_id']
    assert event['booking_status_before'] == 'accepted'
    assert event['reason'] == 'Plans changed' and event['last_minute'] is False
    assert event['excuse_state'] == 'none' and event['review_state'] == 'none'
    assert event['lead_seconds'] > 24 * 3600

    trail = await client.get(
        f'{ADMIN}/audit', headers=e['admin'], params={'event_id': event['id']})
    assert [a['action'] for a in trail.json()] == ['event_recorded']
    assert trail.json()[0]['new_state']['kind'] == 'cancelled'
    # The other party is notified by the existing booking notice; the actor is not.
    assert [n['kind'] for n in await notices(e, 'owner')][0] == 'booking_cancelled'
    assert 'booking_cancelled' not in [n['kind'] for n in await notices(e, 'customer')]
    mine = await client.get(f'{API}/cancellations/me/events', headers=e['customer'])
    assert [x['id'] for x in mine.json()] == [event['id']]


@pytest.mark.asyncio
async def test_companion_cancellation_and_decline_are_tracked_separately(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    accepted = await book(e, service, '2027-01-10T06:00:00Z')
    pending = await book(e, service, '2027-01-10T07:00:00Z', accept=False)
    assert (await cancel(e, 'owner', accepted, reason='Ill')).status_code == 200
    declined = await client.post(
        f'{API}/bookings/{pending}/decline', headers=e['owner'], json={'reason': 'Busy'})
    assert declined.status_code == 200
    kinds = {x['kind']: x for x in await admin_events(e)}
    owner_id = e['owner_id']
    assert kinds['cancelled']['party'] == 'companion'
    assert kinds['cancelled']['subject_user_id'] == owner_id
    assert kinds['declined']['subject_role'] == 'companion'
    # The cancellation of an accepted booking counts; a decline is a normal answer: not counted.
    result = await summary(e, owner_id, 'companion')
    assert result['counters']['cancellations'] == 1
    # Customers never get a companion's user id from their own endpoint.
    mine = await client.get(f'{API}/cancellations/me/events', headers=e['customer'])
    assert mine.json() == [] and owner_id not in mine.text
    theirs = await client.get(f'{API}/cancellations/me/events', headers=e['owner'])
    assert len(theirs.json()) == 2 and 'user_id' not in theirs.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('before', 'last_minute'),
    [
        (timedelta(hours=24, seconds=1), False),
        (timedelta(hours=24), False),
        (timedelta(hours=24) - timedelta(seconds=1), True),
        (timedelta(0), True),
        (-timedelta(minutes=30), True),
    ],
)
async def test_last_minute_flag_follows_the_configured_deadline(prepared, monkeypatch, before,
                                                               last_minute):
    e = prepared
    service = await setup_bookable_companion(e)
    booking_id = await book(e, service)
    freeze(monkeypatch, STARTS - before)
    assert (await cancel(e, 'customer', booking_id)).status_code == 200
    (event,) = await admin_events(e, booking_id=booking_id)
    assert event['last_minute'] is last_minute
    assert event['lead_seconds'] == int(before.total_seconds())


@pytest.mark.asyncio
async def test_last_minute_deadline_is_configurable_without_code_changes(prepared, monkeypatch):
    e = prepared
    configure(e, cancellation_last_minute_hours=2)
    service = await setup_bookable_companion(e)
    booking_id = await book(e, service)
    freeze(monkeypatch, STARTS - timedelta(hours=3))
    await cancel(e, 'customer', booking_id)
    assert (await admin_events(e))[0]['last_minute'] is False  # 3 h ahead is fine with a 2 h rule


@pytest.mark.asyncio
async def test_pending_withdrawal_is_recorded_but_counted_only_when_configured(prepared):
    e = prepared
    service = await setup_bookable_companion(e)
    customer_id = await user_id(e, e['customer'])
    await cancel(e, 'customer', await book(e, service, accept=False))
    assert (await summary(e, customer_id))['counters']['cancellations'] == 0
    configure(e, cancellation_count_pending_requests=True)
    assert (await summary(e, customer_id))['counters']['cancellations'] == 1


@pytest.mark.asyncio
async def test_emergency_claim_is_not_counted_until_an_admin_decides(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    customer_id = await user_id(e, e['customer'])
    first = await book(e, service)
    await cancel(e, 'customer', first, reason='Hospital', emergency=True)
    (event,) = await admin_events(e, booking_id=first)
    assert (event['excuse_state'], event['review_state']) == ('claimed', 'open')
    counters = (await summary(e, customer_id))['counters']
    assert (counters['cancellations'], counters['emergency_claims']) == (0, 1)
    assert [x['id'] for x in await admin_events(e, review_state='open')] == [event['id']]

    # Upheld: the claim is rejected and the cancellation counts.
    review = await client.post(
        f'{ADMIN}/events/{event["id"]}/review', headers=e['admin'],
        json={'decision': 'uphold', 'note': 'No evidence of an emergency'})
    assert review.status_code == 200, review.text
    assert (review.json()['excuse_state'], review.json()['review_state']) == (
        'rejected', 'reviewed')
    counters = (await summary(e, customer_id))['counters']
    assert (counters['cancellations'], counters['emergency_claims']) == (1, 0)

    # Excused later: it stops counting and is only tracked.
    again = await client.post(
        f'{ADMIN}/events/{event["id"]}/review', headers=e['admin'],
        json={'decision': 'excuse', 'note': 'Hospital letter received'})
    assert again.json()['excuse_state'] == 'granted'
    counters = (await summary(e, customer_id))['counters']
    assert (counters['cancellations'], counters['excused']) == (0, 1)
    # previous -> new state is in the trail, with the admin id and a timestamp.
    trail = (await client.get(
        f'{ADMIN}/audit', headers=e['admin'],
        params={'event_id': event['id'], 'action': 'event_reviewed'})).json()
    assert [(t['previous_state']['excuse_state'], t['new_state']['excuse_state'])
            for t in trail] == [('rejected', 'granted'), ('claimed', 'rejected')]
    assert all(t['actor_user_id'] and t['created_at'] and t['reason'] for t in trail)
    console = await client.get(
        f'{API}/admin/audit-events', headers=e['admin'],
        params={'action_prefix': 'cancellation_event'})
    assert {a['action'] for a in console.json()} == {
        'cancellation_event:uphold', 'cancellation_event:excuse'}


@pytest.mark.asyncio
async def test_thresholds_warn_then_open_a_review_case_but_never_restrict(prepared, monkeypatch):
    e, client = prepared, prepared['client']
    configure(e, cancellation_warning_threshold=2, cancellation_review_threshold=3,
              cancellation_last_minute_review_threshold=0)
    service = await setup_bookable_companion(e)
    customer_id = await user_id(e, e['customer'])
    for _ in range(2):
        await cancel(e, 'customer', await book(e, service))
    kinds = [n['kind'] for n in await notices(e, 'customer')]
    assert kinds.count('cancellation_warning') == 1  # at the 2nd, not before, not again
    assert (await summary(e, customer_id))['needs_review'] is False
    await cancel(e, 'customer', await book(e, service))
    result = await summary(e, customer_id)
    assert result['needs_review'] is True and result['counters']['cancellations'] == 3
    assert [n['kind'] for n in await notices(e, 'customer')].count('cancellation_warning') == 1
    cases = (await client.get(f'{ADMIN}/cases', headers=e['admin'])).json()
    assert [(c['trigger'], c['status'], c['user_id']) for c in cases] == [
        ('cancellations', 'open', customer_id)]
    assert cases[0]['snapshot'] == {'count': 3, 'threshold': 3, 'window_days': 30}
    # NOT a restriction: the customer can still book.
    assert (await client.get(f'{ADMIN}/restrictions', headers=e['admin'])).json() == []
    await book(e, service)
    # Closing the case moves the baseline: only newer events count toward a new one.
    case_id = cases[0]['id']
    closed = await client.post(
        f'{ADMIN}/cases/{case_id}/close', headers=e['admin'],
        json={'note': 'Reviewed history, no action'})
    assert closed.status_code == 200 and closed.json()['resolution'] == 'no_action'
    assert (await client.post(
        f'{ADMIN}/cases/{case_id}/close', headers=e['admin'],
        json={'note': 'Reviewed history, no action'})).status_code == 409
    freeze(monkeypatch, datetime.now(UTC) + timedelta(hours=1))
    assert (await summary(e, customer_id))['counters']['cancellations'] == 0
    assert (await summary(e, customer_id))['needs_review'] is False


@pytest.mark.asyncio
async def test_repeated_last_minute_cancellations_open_their_own_case(prepared, monkeypatch):
    e, client = prepared, prepared['client']
    configure(e, cancellation_last_minute_review_threshold=2, cancellation_review_threshold=0,
              cancellation_warning_threshold=0)
    service = await setup_bookable_companion(e)
    freeze(monkeypatch, STARTS - timedelta(hours=1))
    for _ in range(2):
        await cancel(e, 'customer', await book(e, service))
    cases = (await client.get(f'{ADMIN}/cases', headers=e['admin'])).json()
    assert [c['trigger'] for c in cases] == ['last_minute']
    only = await client.get(f'{ADMIN}/events', headers=e['admin'], params={'last_minute': True})
    assert len(only.json()) == 2


@pytest.mark.asyncio
async def test_admin_records_a_no_show_on_a_confirmed_booking(prepared, monkeypatch):
    e, client = prepared, prepared['client']
    booking_id = await confirmed_booking(e)
    url = f'{ADMIN}/bookings/{booking_id}/no-show'
    body = {'party': 'customer', 'note': 'Did not arrive within 30 minutes'}
    early = await client.post(url, headers=e['admin'], json=body)
    assert early.status_code == 409 and early.json()['code'] == 'no_show_too_early'
    freeze(monkeypatch, STARTS + timedelta(minutes=45))
    for who in ('customer', 'owner'):
        assert (await client.post(url, headers=e[who], json=body)).status_code == 403
    done = await client.post(url, headers=e['admin'], json=body)
    assert done.status_code == 201, done.text
    event = done.json()
    customer_id = await user_id(e, e['customer'])
    assert (event['kind'], event['party'], event['subject_user_id']) == (
        'no_show', 'admin', customer_id)
    async with e['app'].state.db_session_factory() as session:
        assert (await session.get(Booking, UUID(booking_id))).status == BookingStatus.NO_SHOW
    assert (await summary(e, customer_id))['counters']['no_shows'] == 1
    again = await client.post(url, headers=e['admin'], json=body)
    assert again.status_code == 409 and again.json()['code'] == 'no_show_already_recorded'
    # Both parties are told; the second record covers "both missing".
    for who in ('customer', 'owner'):
        assert 'booking_no_show' in [n['kind'] for n in await notices(e, who)]
    both = await client.post(url, headers=e['admin'], json={**body, 'party': 'companion'})
    assert both.status_code == 201
    assert (await summary(e, e['owner_id'], 'companion'))['counters']['no_shows'] == 1
    repeated = await client.post(url, headers=e['admin'], json={**body, 'party': 'companion'})
    assert repeated.status_code == 409


@pytest.mark.asyncio
async def test_no_show_needs_a_confirmed_booking(prepared, monkeypatch):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    pending = await book(e, service, accept=False)
    freeze(monkeypatch, STARTS + timedelta(hours=1))
    response = await client.post(
        f'{ADMIN}/bookings/{pending}/no-show', headers=e['admin'],
        json={'party': 'customer', 'note': 'Pending is not a meeting'})
    assert response.status_code == 409
    assert response.json()['code'] == 'invalid_booking_transition'
    assert (await client.post(
        f'{ADMIN}/bookings/{uuid4()}/no-show', headers=e['admin'],
        json={'party': 'customer', 'note': 'Unknown booking id'})).status_code == 404


@pytest.mark.asyncio
async def test_excused_no_show_is_not_counted(prepared, monkeypatch):
    e, client = prepared, prepared['client']
    booking_id = await confirmed_booking(e)
    freeze(monkeypatch, STARTS + timedelta(hours=1))
    done = await client.post(
        f'{ADMIN}/bookings/{booking_id}/no-show', headers=e['admin'],
        json={'party': 'customer', 'note': 'Documented emergency', 'excused': True})
    assert done.status_code == 201 and done.json()['excuse_state'] == 'granted'
    counters = (await summary(e, await user_id(e, e['customer'])))['counters']
    assert (counters['no_shows'], counters['excused']) == (0, 1)


@pytest.mark.asyncio
async def test_system_expiry_is_recorded_for_the_trail_but_never_counted(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    swept = await book(e, service, '2027-01-10T05:00:00Z', accept=False)
    refused = await book(e, service, '2027-01-10T07:00:00Z', accept=False)
    async with e['app'].state.db_session_factory() as session:
        for hours, booking_id in ((5, swept), (2, refused)):  # disjoint: PostgreSQL guards overlaps
            item = await session.get(Booking, UUID(booking_id))
            now = datetime.now(UTC)
            item.starts_at = now - timedelta(hours=hours)
            item.ends_at = now - timedelta(hours=hours) + timedelta(hours=1)
        await session.commit()
    assert (await client.post(f'{API}/bookings/{refused}/accept', headers=e['owner'])
            ).status_code == 409
    async with e['app'].state.db_session_factory() as session:
        assert await expire_stale_bookings(session) == 1
    events = await admin_events(e, kind='expired')
    assert {x['booking_id'] for x in events} == {swept, refused}
    assert all(x['party'] == 'system' and x['subject_user_id'] is None for x in events)
    assert (await summary(e, await user_id(e, e['customer'])))['counters']['cancellations'] == 0


@pytest.mark.asyncio
async def test_user_can_dispute_their_event_once_and_an_admin_decides(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await book(e, service)
    await cancel(e, 'customer', booking_id)
    (event,) = await admin_events(e, booking_id=booking_id)
    url = f'{API}/cancellations/me/events/{event["id"]}/dispute'
    note = {'note': 'My relative was taken to hospital', 'emergency': True}
    assert (await client.post(url, headers=e['other'], json=note)).status_code == 404
    assert (await client.post(url, headers=e['owner'], json=note)).status_code == 404
    short = await client.post(url, headers=e['customer'], json={'note': 'short'})
    assert short.status_code == 422
    disputed = await client.post(url, headers=e['customer'], json=note)
    assert disputed.status_code == 200, disputed.text
    assert (disputed.json()['excuse_state'], disputed.json()['review_state']) == ('claimed', 'open')
    assert (await client.post(url, headers=e['customer'], json=note)).json()['code'] == (
        'dispute_already_open')
    queue = await admin_events(e, review_state='open')
    assert queue[0]['dispute_note'] == note['note'] and queue[0]['disputed_at']
    await client.post(f'{ADMIN}/events/{event["id"]}/review', headers=e['admin'],
                      json={'decision': 'excuse', 'note': 'Documents checked'})
    final = await client.post(url, headers=e['customer'], json=note)
    assert final.status_code == 409 and final.json()['code'] == 'event_already_reviewed'
    # Admin notes are internal: the user's own view has no review note and no ids.
    mine = await client.get(f'{API}/cancellations/me/events', headers=e['customer'])
    assert 'Documents checked' not in mine.text and 'user_id' not in mine.text


@pytest.mark.asyncio
async def test_admin_endpoints_require_an_admin_and_data_is_private(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    await cancel(e, 'customer', await book(e, service))
    uid = await user_id(e, e['customer'])
    reads = [f'{ADMIN}/events', f'{ADMIN}/cases', f'{ADMIN}/restrictions', f'{ADMIN}/audit',
             f'{ADMIN}/users/{uid}/summary']
    for url in reads:
        assert (await client.get(url)).status_code == 401
        for who in ('customer', 'owner', 'other'):
            assert (await client.get(url, headers=e[who])).status_code == 403, (url, who)
        assert (await client.get(url, headers=e['admin'])).status_code == 200
    # Admin lists expose ids only, never phone numbers.
    text = (await client.get(f'{ADMIN}/events', headers=e['admin'])).text
    assert '90100' not in text and 'phone' not in text
    assert (await client.get(f'{API}/cancellations/me/events')).status_code == 401


@pytest.mark.asyncio
async def test_tracking_can_be_switched_off_without_blocking_cancellations(prepared):
    e, client = prepared, prepared['client']
    configure(e, cancellation_tracking_enabled=False)
    service = await setup_bookable_companion(e)
    assert (await cancel(e, 'customer', await book(e, service))).status_code == 200
    assert await admin_events(e) == []
    off = await client.post(
        f'{ADMIN}/bookings/{await book(e, service)}/no-show', headers=e['admin'],
        json={'party': 'customer', 'note': 'Tracking is off here'})
    assert off.status_code == 409 and off.json()['code'] == 'cancellation_tracking_disabled'


@pytest.mark.asyncio
async def test_account_erasure_removes_the_users_free_text_but_keeps_the_record(prepared):
    e = prepared
    service = await setup_bookable_companion(e)
    booking_id = await book(e, service)
    await cancel(e, 'customer', booking_id, reason='My phone is 998901234567')
    customer_id = UUID(await user_id(e, e['customer']))
    async with e['app'].state.db_session_factory() as session:
        user = await session.get(User, customer_id)
        await erase_account(session, user, None, datetime.now(UTC))
        await session.commit()
    async with e['app'].state.db_session_factory() as session:
        stored = (await session.scalars(select(CancellationEvent))).one()
        assert stored.reason == '' and stored.kind == 'cancelled'
        audit = list(await session.scalars(select(CancellationAuditEntry)))
        assert audit  # the trail itself stays


@pytest.mark.asyncio
async def test_booking_create_still_takes_only_the_five_fields(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    extra = await client.post(
        f'{API}/bookings', headers=e['customer'],
        json={**booking_payload(service['id']), 'emergency': True})
    assert extra.status_code == 422


@pytest.mark.asyncio
async def test_losing_the_race_to_open_a_case_never_breaks_the_surrounding_transaction(
    prepared, monkeypatch
):
    e = prepared
    uid = UUID(await user_id(e, e['customer']))
    snapshot = {'count': 5, 'threshold': 5, 'window_days': 30}
    async with e['app'].state.db_session_factory() as session:
        now = datetime.now(UTC)
        first = await cancellation_service._open_case(
            session, uid, 'customer', 'cancellations', snapshot, now)
        assert first is not None

        async def blind(*args, **kwargs):  # a concurrent transaction we cannot see yet
            return None

        monkeypatch.setattr(session, 'scalar', blind)
        second = await cancellation_service._open_case(
            session, uid, 'customer', 'cancellations', snapshot, now)
        monkeypatch.undo()
        assert second is None  # the partial unique index refused it; the savepoint absorbed it
        await session.commit()  # the outer transaction (and the first case) survived
    async with e['app'].state.db_session_factory() as session:
        rows = list(await session.scalars(select(CancellationCase)))
        assert len(rows) == 1 and rows[0].status == 'open'
