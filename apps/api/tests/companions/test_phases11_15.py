from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import select

from yondo_api.chat.models import ChatMessage
from yondo_api.meetings import router as meeting_module
from yondo_api.models.user import UserRole, UserRoleType
from yondo_api.payments.models import Payment, PaymentStatus
from yondo_api.payments.provider import PaymentEvent

from .test_bookings import booking_payload, setup_bookable_companion
from .test_payments import FakePaymentProvider, accepted_booking


async def confirmed_booking(e):
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    provider = FakePaymentProvider()
    e['app'].state.payment_provider = provider
    e['app'].state.settings = e['app'].state.settings.model_copy(update={'platform_fee_bps': 0})
    checkout = await e['client'].post(
        f'/api/v1/payments/bookings/{booking_id}',
        headers={**e['customer'], 'Idempotency-Key': 'meeting-confirm-001'},
    )
    assert checkout.status_code == 201, checkout.text
    webhook = await e['client'].post('/api/v1/payments/webhook', content=b'verified')
    assert webhook.status_code == 204
    return booking_id


@pytest.mark.asyncio
async def test_meeting_two_person_checkin_start_end_and_review(prepared, monkeypatch):
    e, client = prepared, prepared['client']
    booking_id = await confirmed_booking(e)
    root = f'/api/v1/meetings/bookings/{booking_id}'
    assert (await client.post(root + '/start', headers=e['owner'])).status_code == 409
    assert (await client.post(root + '/check-in', headers=e['other'])).status_code == 404
    checkin = await client.post(root + '/check-in', headers=e['customer'])
    assert checkin.status_code == 200, checkin.text
    assert checkin.json()['arrived_count'] == 1
    repeated = await client.post(root + '/check-in', headers=e['customer'])
    assert repeated.status_code == 200
    assert repeated.json()['arrived_count'] == 1
    assert (await client.post(root + '/start', headers=e['customer'])).status_code == 409
    assert (await client.post(root + '/check-in', headers=e['owner'])).status_code == 200
    too_early = await client.post(root + '/start', headers=e['owner'])
    assert too_early.status_code == 409
    assert too_early.json()['code'] == 'meeting_too_early'

    class TestMeetingClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2027, 1, 10, 7, 0, tzinfo=UTC)

    monkeypatch.setattr(meeting_module, 'datetime', TestMeetingClock)
    started = await client.post(root + '/start', headers=e['owner'])
    assert started.status_code == 200, started.text
    assert started.json()['booking_status'] == 'active'
    assert (await client.post(root + '/start', headers=e['owner'])).status_code == 409
    alert = await client.post(
        f'/api/v1/safety/bookings/{booking_id}/sos',
        headers=e['customer'],
        params={'confirmed': True},
    )
    assert alert.status_code == 201, alert.text
    assert alert.json()['emergency_service_contacted'] is False
    ended = await client.post(root + '/end', headers=e['customer'])
    assert ended.status_code == 200, ended.text
    assert ended.json()['booking_status'] == 'active'
    assert ended.json()['ended_count'] == 1
    assert (await client.post(root + '/end', headers=e['customer'])).status_code == 409
    finished = await client.post(root + '/end', headers=e['owner'])
    assert finished.status_code == 200, finished.text
    assert finished.json()['booking_status'] == 'completed'

    url = f'/api/v1/reviews/bookings/{booking_id}'
    reviewed = await client.post(
        url,
        headers=e['customer'],
        json={'stars': 5, 'tags': ['punctuality'], 'comment': 'Good meeting'},
    )
    assert reviewed.status_code == 201, reviewed.text
    assert reviewed.json()['reviewee_id'] == e['owner_id']
    assert (await client.post(url, headers=e['customer'], json={'stars': 4})).status_code == 409
    other_review = await client.post(
        url, headers=e['owner'], json={'stars': 4, 'comment': 'Respectful'}
    )
    assert other_review.status_code == 201, other_review.text
    assert (await client.get(url, headers=e['other'])).status_code == 404
    assert len((await client.get(url, headers=e['owner'])).json()) == 2
    profile = await client.get(f'/api/v1/discovery/companions/{e["profile"]["id"]}')
    assert profile.status_code == 200
    assert profile.json()['rating'] == 5.0
    assert profile.json()['review_count'] == 1
    assert (
        len(
            (await client.get('/api/v1/discovery/companions', params={'rating_min': 5})).json()[
                'items'
            ]
        )
        == 1
    )


@pytest.mark.asyncio
async def test_block_prevents_new_booking_and_own_contact_is_private(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    blocked = await client.put(f'/api/v1/safety/blocks/{e["owner_id"]}', headers=e['customer'])
    assert blocked.status_code == 204, blocked.text
    booking = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert booking.status_code == 403, booking.text
    assert booking.json()['code'] == 'booking_blocked'
    contact = await client.post(
        '/api/v1/safety/trusted-contacts',
        headers=e['customer'],
        json={'name': 'Emergency person', 'phone_number': '+998901234567'},
    )
    assert contact.status_code == 201, contact.text
    assert (await client.get('/api/v1/safety/trusted-contacts', headers=e['owner'])).json() == []
    listed = await client.get('/api/v1/safety/trusted-contacts', headers=e['customer'])
    assert len(listed.json()) == 1
    assert listed.json()[0]['phone_number'] == '+998901234567'


@pytest.mark.asyncio
async def test_booking_report_target_must_be_the_counterparty(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert booking.status_code == 201
    invalid = await client.post(
        '/api/v1/safety/reports',
        headers=e['customer'],
        json={
            'reported_user_id': e['other_id'],
            'booking_id': booking.json()['id'],
            'category': 'harassment',
            'description': 'A real safety report',
        },
    )
    assert invalid.status_code == 422
    valid = await client.post(
        '/api/v1/safety/reports',
        headers=e['customer'],
        json={
            'reported_user_id': e['owner_id'],
            'booking_id': booking.json()['id'],
            'category': 'harassment',
            'description': 'A real safety report',
        },
    )
    assert valid.status_code == 201, valid.text


@pytest.mark.asyncio
async def test_booking_report_derives_the_counterparty_when_no_user_id_is_given(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert booking.status_code == 201
    body = {'category': 'no_show', 'description': 'Companion did not come'}
    missing = await client.post('/api/v1/safety/reports', headers=e['customer'], json=body)
    assert missing.status_code == 422
    assert missing.json()['code'] == 'report_target_required'
    # Customer side: the companion's user id is never needed (booking_id only).
    by_customer = await client.post(
        '/api/v1/safety/reports',
        headers=e['customer'],
        json={**body, 'booking_id': booking.json()['id']},
    )
    assert by_customer.status_code == 201, by_customer.text
    assert by_customer.json()['reported_user_id'] == e['owner_id']
    # Companion side: derives the customer.
    by_companion = await client.post(
        '/api/v1/safety/reports',
        headers=e['owner'],
        json={**body, 'booking_id': booking.json()['id']},
    )
    assert by_companion.status_code == 201, by_companion.text
    assert by_companion.json()['reported_user_id'] == booking.json()['customer_id']
    # A non-participant cannot use someone else's booking.
    outsider = await client.post(
        '/api/v1/safety/reports',
        headers=e['other'],
        json={**body, 'booking_id': booking.json()['id']},
    )
    assert outsider.status_code in {403, 404}
    own = await client.get('/api/v1/safety/reports', headers=e['customer'])
    assert [r['category'] for r in own.json()] == ['no_show']


@pytest.mark.asyncio
async def test_admin_reporting_and_audited_moderation(prepared):
    e, client = prepared, prepared['client']
    assert (await client.get('/api/v1/admin/summary', headers=e['other'])).status_code == 403
    summary = await client.get('/api/v1/admin/summary', headers=e['admin'])
    assert summary.status_code == 200, summary.text
    assert summary.json()['users'] >= 4
    decision = await client.post(
        f'/api/v1/admin/users/{e["other_id"]}/status',
        headers=e['admin'],
        json={'status': 'suspended', 'reason': 'Policy-based moderation review'},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()['account_status'] == 'suspended'
    assert (await client.get('/api/v1/auth/me', headers=e['other'])).status_code == 403


@pytest.mark.asyncio
async def test_gifts_vendor_catalog_moderation_cart_and_disabled_checkout(prepared):
    e, client = prepared, prepared['client']
    async with e['app'].state.db_session_factory() as session:
        session.add(UserRole(user_id=UUID(e['other_id']), role=UserRoleType.VENDOR))
        await session.commit()
    create = await client.post(
        '/api/v1/gifts/vendor/products',
        headers=e['other'],
        json={
            'category': 'flowers',
            'name': 'Tulip bouquet',
            'description': 'Fresh seasonal flowers',
            'price_minor': 120000,
            'currency': 'UZS',
            'stock': 3,
        },
    )
    assert create.status_code == 201, create.text
    product_id = create.json()['id']
    assert (await client.get('/api/v1/gifts/products')).json() == []
    assert (
        await client.post(
            f'/api/v1/gifts/admin/products/{product_id}/publish',
            headers=e['customer'],
        )
    ).status_code == 403
    approved = await client.post(
        f'/api/v1/gifts/admin/products/{product_id}/publish', headers=e['admin']
    )
    assert approved.status_code == 200, approved.text
    catalog = await client.get('/api/v1/gifts/products')
    assert len(catalog.json()) == 1
    cart = await client.put(
        f'/api/v1/gifts/cart/{product_id}', headers=e['customer'], json={'quantity': 2}
    )
    assert cart.status_code == 200, cart.text
    assert (await client.get('/api/v1/gifts/cart', headers=e['customer'])).json()[0][
        'quantity'
    ] == 2
    preview = await client.get('/api/v1/gifts/checkout/preview', headers=e['customer'])
    assert preview.status_code == 200, preview.text
    assert preview.json()['subtotal_minor'] == 240000
    assert preview.json()['delivery_fee_minor'] is None
    assert preview.json()['checkout_available'] is False
    closed = await client.post('/api/v1/gifts/checkout', headers=e['customer'])
    assert closed.status_code == 503
    assert closed.json()['code'] == 'gift_checkout_unavailable'
    async with e['app'].state.db_session_factory() as session:
        role = await session.get(UserRole, (UUID(e['other_id']), UserRoleType.VENDOR))
        await session.delete(role)
        await session.commit()
    assert (await client.get('/api/v1/gifts/products')).json() == []
    assert (
        await client.get('/api/v1/gifts/checkout/preview', headers=e['customer'])
    ).status_code == 409


@pytest.mark.asyncio
async def test_restricted_customer_cannot_list_private_bookings(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert booking.status_code == 201, booking.text
    me = await client.get('/api/v1/auth/me', headers=e['customer'])
    assert me.status_code == 200
    customer_id = me.json()['id']
    assert (
        await client.post(
            f'/api/v1/admin/users/{customer_id}/status',
            headers=e['admin'],
            json={'status': 'restricted', 'reason': 'Moderation access review'},
        )
    ).status_code == 200
    assert (await client.get('/api/v1/bookings', headers=e['customer'])).status_code == 403
    assert (
        await client.get(f'/api/v1/bookings/{booking.json()["id"]}', headers=e['customer'])
    ).status_code == 403


@pytest.mark.asyncio
async def test_multiple_checkout_keys_do_not_create_second_provider_charge(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    provider = FakePaymentProvider()
    e['app'].state.payment_provider = provider
    e['app'].state.settings = e['app'].state.settings.model_copy(update={'platform_fee_bps': 0})
    url = f'/api/v1/payments/bookings/{booking_id}'
    first = await client.post(
        url, headers={**e['customer'], 'Idempotency-Key': 'payment-attempt-aaa'}
    )
    assert first.status_code == 201, first.text
    second = await client.post(
        url, headers={**e['customer'], 'Idempotency-Key': 'payment-attempt-bbb'}
    )
    assert second.status_code == 409
    assert len(provider.checkouts) == 1


@pytest.mark.asyncio
async def test_discovery_excludes_reserved_time_and_preserves_adjacent_slot(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booked = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert booked.status_code == 201, booked.text
    occupied = await client.get(
        '/api/v1/discovery/companions',
        params={
            'available_from': '2027-01-10T06:00:00Z',
            'available_until': '2027-01-10T06:30:00Z',
        },
    )
    assert occupied.status_code == 200, occupied.text
    assert occupied.json()['items'] == []
    adjacent = await client.get(
        '/api/v1/discovery/companions',
        params={
            'available_from': '2027-01-10T07:00:00Z',
            'available_until': '2027-01-10T07:30:00Z',
        },
    )
    assert adjacent.status_code == 200, adjacent.text
    assert len(adjacent.json()['items']) == 1


@pytest.mark.asyncio
async def test_distinct_verified_success_webhooks_do_not_duplicate_charge_events(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    provider = FakePaymentProvider()
    e['app'].state.payment_provider = provider
    e['app'].state.settings = e['app'].state.settings.model_copy(update={'platform_fee_bps': 0})
    first = await client.post(
        f'/api/v1/payments/bookings/{booking_id}',
        headers={**e['customer'], 'Idempotency-Key': 'payment-webhook-once'},
    )
    assert first.status_code == 201, first.text
    assert (
        await client.post('/api/v1/payments/webhook', content=b'signed-event')
    ).status_code == 204
    provider.event = PaymentEvent('another-event', 'provider-1', 'succeeded')
    assert (
        await client.post('/api/v1/payments/webhook', content=b'other-signed-event')
    ).status_code == 204
    async with e['app'].state.db_session_factory() as session:
        payment = await session.get(Payment, UUID(first.json()['id']))
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.refund_required is False
        messages = list(
            await session.scalars(
                select(ChatMessage).where(
                    ChatMessage.booking_id == UUID(booking_id),
                    ChatMessage.system_code == 'payment_confirmed',
                )
            )
        )
        assert len(messages) == 1
