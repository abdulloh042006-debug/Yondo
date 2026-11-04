from datetime import timedelta

from sqlalchemy import select
from support import API

from yondo_api.bookings.meeting import auto_complete_overdue
from yondo_api.core.time import utc_now
from yondo_api.payments.models import Payout
from yondo_api.safety.models import Dispute

from .helpers import B, completed_booking, confirmed_booking, shift_booking, started_booking


async def payout_for(market):
    async with market.app.state.db_session_factory() as session:
        return (await session.scalars(select(Payout))).one()


async def test_check_in_start_and_end(market):
    companion = await market.companion()
    booking, _ = await confirmed_booking(market, companion)
    early = await market.client.post(f'{B}/{booking["id"]}/check-in', headers=market.customer)
    assert early.status_code == 409 and early.json()['code'] == 'check_in_not_open'
    soon = utc_now() + timedelta(minutes=10)
    await shift_booking(market, booking['id'], starts_at=soon, ends_at=soon + timedelta(hours=1))
    customer_view = await market.client.get(f'{B}/{booking["id"]}', headers=market.customer)
    assert 'check_in' in customer_view.json()['actions']
    checked = await market.client.post(f'{B}/{booking["id"]}/check-in', headers=market.customer)
    assert checked.json()['customer_checked_in_at'] is not None
    twice = await market.client.post(f'{B}/{booking["id"]}/check-in', headers=market.customer)
    assert twice.status_code == 409
    not_yet = await market.client.post(f'{B}/{booking["id"]}/start', headers=companion.headers)
    assert not_yet.json()['code'] == 'check_in_required'
    await market.client.post(f'{B}/{booking["id"]}/check-in', headers=companion.headers)
    by_customer = await market.client.post(f'{B}/{booking["id"]}/start', headers=market.customer)
    assert by_customer.status_code == 403
    started = await market.client.post(f'{B}/{booking["id"]}/start', headers=companion.headers)
    assert started.json()['status'] == 'active'
    assert 'sos' in started.json()['actions']
    ended = await market.client.post(f'{B}/{booking["id"]}/end', headers=market.customer)
    assert ended.json()['status'] == 'completed'
    assert 'review' in ended.json()['actions'] and 'rebook' in ended.json()['actions']
    payout = await payout_for(market)
    assert payout.status == 'scheduled' and payout.available_at is not None


async def test_no_show_opens_dispute_and_holds_payout(market):
    companion = await market.companion()
    booking, _ = await confirmed_booking(market, companion)
    started = utc_now() - timedelta(minutes=20)
    await shift_booking(
        market, booking['id'], starts_at=started, ends_at=started + timedelta(hours=1)
    )
    url = f'{B}/{booking["id"]}/no-show'
    not_checked = await market.client.post(url, headers=market.customer, json={})
    assert not_checked.json()['code'] == 'check_in_required'
    await market.client.post(f'{B}/{booking["id"]}/check-in', headers=market.customer)
    reported = await market.client.post(url, headers=market.customer, json={'note': 'Waited'})
    assert reported.status_code == 200, reported.text
    assert reported.json()['status'] == 'disputed'
    assert reported.json()['no_show_party'] == 'companion'
    async with market.app.state.db_session_factory() as session:
        dispute = (await session.scalars(select(Dispute))).one()
    assert dispute.category == 'no_show' and dispute.previous_booking_status == 'no_show'
    assert (await payout_for(market)).status == 'held'
    events = await market.client.get(f'{B}/{booking["id"]}/events', headers=companion.headers)
    assert [e['event'] for e in events.json()][-2:] == ['no_show_reported', 'dispute_opened']


async def test_overdue_active_meetings_are_auto_completed(market):
    companion = await market.companion()
    booking, _ = await started_booking(market, companion)
    past = utc_now() - timedelta(hours=5)
    await shift_booking(market, booking['id'], starts_at=past, ends_at=past + timedelta(hours=1))
    async with market.app.state.db_session_factory() as session:
        assert await auto_complete_overdue(session, market.app.state.settings) == 1
    state = await market.client.get(f'{B}/{booking["id"]}', headers=market.customer)
    assert state.json()['status'] == 'completed'


async def test_completed_flow_helper(market):
    companion = await market.companion()
    booking, _ = await completed_booking(market, companion)
    assert booking['status'] == 'completed'
    assert API
