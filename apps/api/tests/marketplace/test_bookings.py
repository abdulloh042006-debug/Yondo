import asyncio
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import select
from support import API

from yondo_api.bookings.models import Booking
from yondo_api.bookings.service import expire_due
from yondo_api.core.time import utc_now
from yondo_api.notifications.models import Notification

from .conftest import hour_from_now
from .helpers import B, accepted_booking, booking_payload, request_booking, shift_booking


async def test_quote_prices_whole_units_with_platform_fee(market):
    companion = await market.companion()
    payload = booking_payload(companion, duration=120)
    payload.pop('accept_contract')
    quote = await market.client.post(f'{B}/quote', headers=market.customer, json=payload)
    assert quote.status_code == 200, quote.text
    body = quote.json()
    assert body['service_amount_minor'] == 200_000
    assert body['platform_fee_minor'] == 20_000
    assert body['total_minor'] == 220_000
    assert body['timezone'] == 'Asia/Tashkent'
    contract = body['contract']
    assert contract['companion']['display_name'] == 'Malika'
    assert contract['cancellation_policy']['free_cancellation_hours'] == 24
    assert 'prohibited_services' in contract['platform_rules']
    odd = await market.client.post(
        f'{B}/quote', headers=market.customer, json={**payload, 'duration_minutes': 90}
    )
    assert odd.status_code == 422 and odd.json()['code'] == 'invalid_duration'


async def test_request_validation_rules(market):
    companion = await market.companion()
    client, customer = market.client, market.customer
    payload = booking_payload(companion)
    no_contract = await client.post(B, headers=customer, json={**payload, 'accept_contract': False})
    assert no_contract.status_code == 422
    outside = await client.post(
        B, headers=customer, json=booking_payload(companion, start_hours=40)
    )
    assert outside.status_code == 409 and outside.json()['code'] == 'outside_availability'
    soon = await client.post(B, headers=customer, json=booking_payload(companion, start_hours=0))
    assert soon.status_code == 422 and soon.json()['code'] == 'booking_too_soon'
    seconds = {**payload, 'starts_at': (hour_from_now(25) + timedelta(seconds=5)).isoformat()}
    assert (await client.post(B, headers=customer, json=seconds)).status_code == 422
    self_book = await client.post(B, headers=companion.headers, json=payload)
    assert self_book.status_code == 403  # companion account lacks the customer role
    pending_user, _ = await market.user(name=None, age=15)
    assert (await client.post(B, headers=pending_user, json=payload)).status_code == 403
    hidden = await market.companion('Hidden', activate=False)
    hidden_payload = booking_payload(hidden)
    assert (await client.post(B, headers=customer, json=hidden_payload)).status_code == 404


async def test_request_accept_and_notifications(market):
    companion = await market.companion()
    booking = await request_booking(market, companion)
    assert booking['status'] == 'pending'
    assert booking['role'] == 'customer'
    assert booking['actions'] == ['cancel', 'chat']
    assert booking['companion_payout_minor'] is None
    assert booking['customer']['display_name'] == 'Sardor'
    duplicate = await market.client.post(
        B, headers=market.customer, json=booking_payload(companion)
    )
    assert duplicate.json()['code'] == 'duplicate_booking_request'
    seen = await market.client.get(f'{B}/{booking["id"]}', headers=companion.headers)
    assert seen.json()['actions'] == ['accept', 'decline', 'chat']
    assert seen.json()['companion_payout_minor'] == 100_000
    other, _ = await market.user()
    assert (await market.client.get(f'{B}/{booking["id"]}', headers=other)).status_code == 404
    assert (
        await market.client.post(f'{B}/{booking["id"]}/accept', headers=market.customer)
    ).status_code == 404
    accepted = await market.client.post(f'{B}/{booking["id"]}/accept', headers=companion.headers)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['status'] == 'accepted'
    assert accepted.json()['payment_due_at'] is not None
    again = await market.client.post(f'{B}/{booking["id"]}/accept', headers=companion.headers)
    assert again.status_code == 409
    async with market.app.state.db_session_factory() as session:
        kinds = list(
            await session.scalars(select(Notification.kind).order_by(Notification.created_at))
        )
    assert kinds == ['booking_requested', 'booking_accepted']
    events = await market.client.get(f'{B}/{booking["id"]}/events', headers=market.customer)
    assert [item['event'] for item in events.json()] == ['requested', 'accepted']


async def test_overlapping_requests_only_one_can_be_accepted(market):
    companion = await market.companion()
    other, _ = await market.user(name='Jasur')
    first = await request_booking(market, companion)
    second = await request_booking(market, companion, other, duration=120)
    assert (
        await market.client.post(f'{B}/{first["id"]}/accept', headers=companion.headers)
    ).status_code == 200
    conflict = await market.client.post(f'{B}/{second["id"]}/accept', headers=companion.headers)
    assert conflict.status_code == 409 and conflict.json()['code'] == 'slot_unavailable'
    taken = await market.client.post(B, headers=other, json=booking_payload(companion))
    assert taken.json()['code'] == 'slot_unavailable'
    profile = await market.client.get(
        f'{API}/discovery/companions/{companion.profile_id}', headers=other
    )
    slots = profile.json()['availability']
    assert len(slots) == 2 and slots[0]['ends_at'] == first['starts_at']


async def test_decline_and_cancel_rules(market):
    companion = await market.companion()
    first = await request_booking(market, companion)
    cannot = await market.client.post(
        f'{B}/{first["id"]}/cancel', headers=companion.headers, json={}
    )
    assert cannot.status_code == 409
    declined = await market.client.post(
        f'{B}/{first["id"]}/decline', headers=companion.headers, json={'note': 'Busy'}
    )
    assert declined.json()['status'] == 'cancelled'
    assert declined.json()['cancellation_reason'] == 'declined'
    second = await request_booking(market, companion, start_hours=27)
    preview = await market.client.get(f'{B}/{second["id"]}/cancellation', headers=market.customer)
    assert preview.json() == {'refund_minor': 0, 'refund_percent': 0.0, 'policy': 'no_payment'}
    cancelled = await market.client.post(
        f'{B}/{second["id"]}/cancel', headers=market.customer, json={'note': 'Changed plans'}
    )
    assert cancelled.json()['cancellation_reason'] == 'customer_cancelled'
    assert cancelled.json()['actions'] == []
    assert (
        await market.client.post(f'{B}/{second["id"]}/cancel', headers=market.customer, json={})
    ).status_code == 409


async def test_cancellation_policy_preview_for_paid_booking(market):
    companion = await market.companion(windows=((24, 34), (60, 70)))
    booking = await accepted_booking(market, companion, start_hours=61)
    await shift_booking(market, booking['id'], status='confirmed', confirmed_at=utc_now())
    url = f'{B}/{booking["id"]}/cancellation'
    free = await market.client.get(url, headers=market.customer)
    assert free.json() == {'refund_minor': 110_000, 'refund_percent': 100.0, 'policy': 'free'}
    late_start = utc_now() + timedelta(hours=2)
    await shift_booking(
        market, booking['id'], starts_at=late_start, ends_at=late_start + timedelta(hours=1)
    )
    late = await market.client.get(url, headers=market.customer)
    assert late.json() == {'refund_minor': 55_000, 'refund_percent': 50.0, 'policy': 'partial'}
    by_companion = await market.client.get(url, headers=companion.headers)
    assert by_companion.json()['policy'] == 'full_companion_cancel'
    assert by_companion.json()['refund_minor'] == 110_000


async def test_request_and_payment_expiry(market):
    companion = await market.companion()
    booking = await request_booking(market, companion)
    await shift_booking(market, booking['id'], request_expires_at=utc_now() - timedelta(minutes=1))
    expired = await market.client.post(f'{B}/{booking["id"]}/accept', headers=companion.headers)
    assert expired.status_code == 409 and expired.json()['code'] == 'booking_expired'
    state = await market.client.get(f'{B}/{booking["id"]}', headers=market.customer)
    assert state.json()['cancellation_reason'] == 'request_expired'
    accepted = await accepted_booking(market, companion, start_hours=28)
    await shift_booking(market, accepted['id'], payment_due_at=utc_now() - timedelta(seconds=1))
    async with market.app.state.db_session_factory() as session:
        assert await expire_due(session) == 1
    state = await market.client.get(f'{B}/{accepted["id"]}', headers=market.customer)
    assert state.json()['cancellation_reason'] == 'payment_expired'


async def test_availability_edits_cannot_orphan_reservations(market):
    companion = await market.companion()
    window = companion.availability[0]
    await accepted_booking(market, companion)
    path = f'{API}/companions/me/availability/{window["id"]}'
    blocked = await market.client.delete(path, headers=companion.headers)
    assert blocked.status_code == 409 and blocked.json()['code'] == 'availability_has_bookings'
    shrink = {
        'starts_at': hour_from_now(30).isoformat(),
        'ends_at': hour_from_now(34).isoformat(),
        'timezone': 'Asia/Tashkent',
    }
    assert (
        await market.client.put(path, headers=companion.headers, json=shrink)
    ).status_code == 409
    keep = {
        **shrink,
        'starts_at': hour_from_now(24).isoformat(),
        'ends_at': hour_from_now(27).isoformat(),
    }
    assert (await market.client.put(path, headers=companion.headers, json=keep)).status_code == 200


async def test_free_service_is_confirmed_on_accept(market):
    companion = await market.companion(services=(('conversation', 0, 30),))
    booking = await accepted_booking(market, companion, service='conversation', duration=30)
    assert booking['status'] == 'confirmed'
    assert booking['total_minor'] == 0


async def test_listing_scopes_and_rebook(market):
    companion = await market.companion()
    booking = await request_booking(market, companion)
    mine = await market.client.get(B, headers=market.customer, params={'role': 'customer'})
    assert [item['id'] for item in mine.json()['items']] == [booking['id']]
    assert (
        await market.client.get(B, headers=market.customer, params={'role': 'companion'})
    ).json()['items'] == []
    upcoming = await market.client.get(B, headers=companion.headers, params={'scope': 'upcoming'})
    assert len(upcoming.json()['items']) == 1
    past = await market.client.get(B, headers=companion.headers, params={'scope': 'past'})
    assert past.json()['items'] == []
    pending = await market.client.get(B, headers=companion.headers, params={'status': 'pending'})
    assert len(pending.json()['items']) == 1
    early = await market.client.get(f'{B}/{booking["id"]}/rebook', headers=market.customer)
    assert early.status_code == 409
    await shift_booking(market, booking['id'], status='completed')
    template = await market.client.get(f'{B}/{booking["id"]}/rebook', headers=market.customer)
    assert template.status_code == 200
    assert template.json()['meeting_place']['name'] == 'Cafe Central'
    rebooked = await request_booking(
        market, companion, start_hours=27, rebooked_from_id=booking['id']
    )
    assert rebooked['rebooked_from_id'] == booking['id']


async def test_concurrent_accepts_produce_a_single_reservation(market):
    if market.app.state.db_engine.dialect.name != 'postgresql':
        pytest.skip('Concurrency semantics require PostgreSQL row locks')
    companion = await market.companion()
    customers = [market.customer, (await market.user())[0], (await market.user())[0]]
    requests = [await request_booking(market, companion, headers) for headers in customers]
    results = await asyncio.gather(
        *[
            market.client.post(f'{B}/{item["id"]}/accept', headers=companion.headers)
            for item in requests
        ]
    )
    assert sorted(result.status_code for result in results) == [200, 409, 409]
    async with market.app.state.db_session_factory() as session:
        held = await session.scalars(
            select(Booking).where(
                Booking.companion_id == companion.user_id, Booking.status == 'accepted'
            )
        )
        assert len(list(held)) == 1


async def test_database_rejects_overlapping_held_bookings(market):
    if market.app.state.db_engine.dialect.name != 'postgresql':
        pytest.skip('Exclusion constraints are PostgreSQL-only')
    from sqlalchemy.exc import IntegrityError

    companion = await market.companion()
    first = await accepted_booking(market, companion)
    other, _ = await market.user()
    second = await request_booking(market, companion, other, start_hours=27)
    # Bypass application checks: the database itself must refuse the overlap.
    with pytest.raises(IntegrityError):
        await shift_booking(
            market,
            second['id'],
            status='accepted',
            starts_at=hour_from_now(25),
            ends_at=hour_from_now(26),
        )
    assert UUID(first['id'])
