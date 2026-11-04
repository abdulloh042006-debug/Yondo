import json
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from support import API

from yondo_api.core.time import utc_now
from yondo_api.payments.models import Payment, Payout, Refund
from yondo_api.payments.service import expire_pending_payments, process_refunds

from .helpers import (
    B,
    P,
    accepted_booking,
    checkout,
    confirmed_booking,
    pay,
    request_booking,
    shift_booking,
)


async def payouts(market):
    async with market.app.state.db_session_factory() as session:
        return list(await session.scalars(select(Payout)))


async def test_checkout_is_idempotent_and_confirms_booking(market):
    companion = await market.companion()
    booking = await accepted_booking(market, companion)
    first = await checkout(market, booking['id'])
    assert first.status_code == 200, first.text
    payment = first.json()
    assert payment['status'] == 'pending'
    assert payment['amount_minor'] == 110_000
    assert payment['breakdown']['platform_fee_minor'] == 10_000
    assert payment['checkout_url'].endswith(payment['id'])
    same = await checkout(market, booking['id'])
    assert same.json()['id'] == payment['id']
    other_key = await checkout(market, booking['id'], key='another-key-2')
    assert other_key.json()['id'] == payment['id']
    stranger, _ = await market.user()
    assert (await checkout(market, booking['id'], headers=stranger)).status_code == 404
    page = await market.client.get(f'{P}/sandbox/{payment["id"]}')
    assert page.status_code == 200 and '110000 UZS' in page.text
    assert await pay(market, payment['id']) == 'captured'
    assert await pay(market, payment['id']) == 'duplicate'
    confirmed = await market.client.get(f'{B}/{booking["id"]}', headers=market.customer)
    assert confirmed.json()['status'] == 'confirmed'
    assert 'pay' not in confirmed.json()['actions']
    paid_again = await checkout(market, booking['id'], key='third-key-3')
    assert paid_again.status_code == 409
    held = await payouts(market)
    assert [(p.status, p.amount_minor) for p in held] == [('held', 100_000)]
    mine = await market.client.get(P, headers=market.customer)
    assert mine.json()['items'][0]['status'] == 'succeeded'
    earnings = await market.client.get(f'{API}/payouts/me', headers=companion.headers)
    assert earnings.json()['summary'][0]['held_minor'] == 100_000


async def test_checkout_requires_accepted_booking(market):
    companion = await market.companion()
    pending = await request_booking(market, companion)
    response = await checkout(market, pending['id'])
    assert response.status_code == 409 and response.json()['code'] == 'booking_not_payable'
    bad_key = await market.client.post(
        f'{P}/bookings/{pending["id"]}/checkout',
        headers=market.customer,
        json={'idempotency_key': 'bad key!'},
    )
    assert bad_key.status_code == 422


async def test_webhook_signature_dedup_and_amount_checks(market):
    companion = await market.companion()
    booking = await accepted_booking(market, companion)
    payment = (await checkout(market, booking['id'])).json()
    provider = market.app.state.payment_providers['sandbox']
    async with market.app.state.db_session_factory() as session:
        provider_id = (await session.get(Payment, UUID(payment['id']))).provider_payment_id

    def signed(**overrides):
        body = json.dumps(
            {
                'event_id': 'evt-1',
                'payment_id': provider_id,
                'status': 'succeeded',
                'amount_minor': 110_000,
                'currency': 'UZS',
                **overrides,
            }
        ).encode()
        return body, {'X-Yondo-Signature': provider.sign(body), 'Content-Type': 'application/json'}

    body, headers = signed()
    forged = await market.client.post(
        f'{P}/webhooks/sandbox', content=body, headers={**headers, 'X-Yondo-Signature': 'bad'}
    )
    assert forged.status_code == 401
    assert (await market.client.post(f'{P}/webhooks/unknown', content=body)).status_code == 404
    wrong_body, wrong_headers = signed(event_id='evt-0', amount_minor=1)
    mismatch = await market.client.post(
        f'{P}/webhooks/sandbox', content=wrong_body, headers=wrong_headers
    )
    assert mismatch.json()['outcome'] == 'amount_mismatch'
    state = await market.client.get(f'{P}/{payment["id"]}', headers=market.customer)
    assert state.json()['status'] == 'failed'
    retry = (await checkout(market, booking['id'], key='retry-key-22')).json()
    assert retry['id'] != payment['id'] and retry['status'] == 'pending'
    async with market.app.state.db_session_factory() as session:
        retry_provider_id = (await session.get(Payment, UUID(retry['id']))).provider_payment_id
    body, headers = signed(payment_id=retry_provider_id)
    first = await market.client.post(f'{P}/webhooks/sandbox', content=body, headers=headers)
    assert first.json()['outcome'] == 'captured'
    again = await market.client.post(f'{P}/webhooks/sandbox', content=body, headers=headers)
    assert again.json()['outcome'] == 'duplicate'


async def test_failed_payment_allows_retry(market):
    companion = await market.companion()
    booking = await accepted_booking(market, companion)
    payment = (await checkout(market, booking['id'])).json()
    assert await pay(market, payment['id'], 'failed') == 'failed'
    retry = await checkout(market, booking['id'], key='retry-key-1')
    assert retry.json()['status'] == 'pending'
    assert await pay(market, retry.json()['id']) == 'captured'


async def test_paid_customer_cancellations_refund_by_policy(market):
    companion = await market.companion(windows=((24, 34), (60, 70)))
    early, early_payment = await confirmed_booking(market, companion, start_hours=61)
    cancelled = await market.client.post(
        f'{B}/{early["id"]}/cancel', headers=market.customer, json={}
    )
    assert cancelled.json()['refund_minor'] == 110_000
    state = await market.client.get(f'{P}/{early_payment["id"]}', headers=market.customer)
    assert state.json()['status'] == 'refunded'
    assert state.json()['refunded_minor'] == 110_000
    async with market.app.state.db_session_factory() as session:
        refunds = list(await session.scalars(select(Refund)))
    assert [(r.status, r.amount_minor) for r in refunds] == [('succeeded', 110_000)]
    late, late_payment = await confirmed_booking(market, companion, start_hours=25)
    soon = utc_now() + timedelta(hours=2)
    await shift_booking(market, late['id'], starts_at=soon, ends_at=soon + timedelta(hours=1))
    cancelled = await market.client.post(
        f'{B}/{late["id"]}/cancel', headers=market.customer, json={}
    )
    assert cancelled.json()['refund_minor'] == 55_000
    state = await market.client.get(f'{P}/{late_payment["id"]}', headers=market.customer)
    assert state.json()['status'] == 'partially_refunded'
    by_booking = {str(p.booking_id): p for p in await payouts(market)}
    assert by_booking[early['id']].status == 'cancelled'
    assert by_booking[late['id']].status == 'scheduled'
    assert by_booking[late['id']].amount_minor == 50_000


async def test_companion_cancellation_refunds_in_full(market):
    companion = await market.companion()
    booking, payment = await confirmed_booking(market, companion)
    response = await market.client.post(
        f'{B}/{booking["id"]}/cancel', headers=companion.headers, json={'note': 'Ill'}
    )
    assert response.json()['refund_minor'] == 110_000
    assert response.json()['cancellation_reason'] == 'companion_cancelled'
    assert (await payouts(market))[0].status == 'cancelled'


async def test_money_for_expired_booking_is_refunded_automatically(market):
    companion = await market.companion()
    booking = await accepted_booking(market, companion)
    payment = (await checkout(market, booking['id'])).json()
    await shift_booking(market, booking['id'], payment_due_at=utc_now() - timedelta(seconds=1))
    async with market.app.state.db_session_factory() as session:
        from yondo_api.bookings.service import expire_due

        assert await expire_due(session) == 1
        assert await expire_pending_payments(session) == 1
    assert await pay(market, payment['id']) == 'refunded_unpayable'
    state = await market.client.get(f'{P}/{payment["id"]}', headers=market.customer)
    assert state.json()['status'] == 'refunded'
    async with market.app.state.db_session_factory() as session:
        assert await process_refunds(session, market.app.state) == 0
    assert await payouts(market) == []


async def test_concurrent_checkouts_create_a_single_live_payment(market):
    import asyncio

    import pytest

    if market.app.state.db_engine.dialect.name != 'postgresql':
        pytest.skip('Concurrency semantics require PostgreSQL row locks')
    companion = await market.companion()
    booking = await accepted_booking(market, companion)
    results = await asyncio.gather(
        *[checkout(market, booking['id'], key=f'parallel-key-{index}') for index in range(5)]
    )
    assert {result.status_code for result in results} == {200}
    assert len({result.json()['id'] for result in results}) == 1
    async with market.app.state.db_session_factory() as session:
        assert len(list(await session.scalars(select(Payment)))) == 1
