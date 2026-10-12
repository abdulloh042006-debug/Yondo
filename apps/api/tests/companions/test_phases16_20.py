"""Phase 16–20 API, permissions, transactional notices, and beta gating."""
from uuid import UUID

import pytest

from yondo_api.models.user import UserRole, UserRoleType

from .test_bookings import booking_payload, setup_bookable_companion
from .test_payments import accepted_booking


async def offer_product(e, *, currency='UZS', stock=5):
    async with e['app'].state.db_session_factory() as session:
        session.add(UserRole(user_id=UUID(e['other_id']), role=UserRoleType.VENDOR))
        await session.commit()
    product = await e['client'].post(
        '/api/v1/gifts/vendor/products',
        headers=e['other'],
        json={
            'category': 'flowers',
            'name': 'Tulip bouquet',
            'description': 'A gift from the catalog',
            'price_minor': 100_000,
            'currency': currency,
            'stock': stock,
        },
    )
    assert product.status_code == 201, product.text
    pid = product.json()['id']
    published = await e['client'].post(
        f'/api/v1/gifts/admin/products/{pid}/publish', headers=e['admin']
    )
    assert published.status_code == 200, published.text
    return pid


@pytest.mark.asyncio
async def test_booking_gift_preview_is_scoped_and_checkout_never_charges(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    bid = await accepted_booking(e, service)
    pid = await offer_product(e)
    assert (
        await client.put(
            f'/api/v1/gifts/cart/{pid}',
            json={'quantity': 2},
            headers=e['customer'],
        )
    ).status_code == 200
    preview = await client.get(
        f'/api/v1/integration/bookings/{bid}/preview', headers=e['customer']
    )
    assert preview.status_code == 200, preview.text
    result = preview.json()
    assert result['booking_id'] == bid
    assert result['gift_subtotal_minor'] == 200_000
    assert result['subtotal_minor'] == result['booking_service_minor'] + 200_000
    assert result['delivery_fee_minor'] is None
    assert result['total_minor'] is None
    assert result['checkout_available'] is False
    assert (
        await client.post(
            f'/api/v1/integration/bookings/{bid}/checkout', headers=e['customer']
        )
    ).status_code == 503
    assert (
        await client.get(f'/api/v1/integration/bookings/{bid}/preview', headers=e['other'])
    ).status_code == 403


@pytest.mark.asyncio
async def test_booking_gift_quote_checks_booking_status_and_currency(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert booking.status_code == 201, booking.text
    bid = booking.json()['id']
    assert (
        await client.get(f'/api/v1/integration/bookings/{bid}/preview',
                         headers=e['customer'])
    ).status_code == 409
    await client.post(f'/api/v1/bookings/{bid}/accept', headers=e['owner'])
    pid = await offer_product(e, currency='USD')
    await client.put(f'/api/v1/gifts/cart/{pid}', headers=e['customer'],
                     json={'quantity': 1})
    wrong_currency = await client.get(f'/api/v1/integration/bookings/{bid}/preview',
                                      headers=e['customer'])
    assert wrong_currency.status_code == 409, wrong_currency.text
    assert wrong_currency.json()['code'] == 'gift_currency_mismatch'


@pytest.mark.asyncio
async def test_vendor_ownership_price_reapproval_and_stock(prepared):
    e, client = prepared, prepared['client']
    pid = await offer_product(e)
    url = f'/api/v1/vendor/products/{pid}'
    assert (await client.patch(url, headers=e['customer'],
                               json={'price_minor': 99_000})).status_code == 403
    assert (await client.patch(url, headers=e['other'], json={})).status_code == 422
    stock = await client.patch(url, headers=e['other'], json={'stock': 3})
    assert stock.status_code == 200, stock.text
    assert stock.json()['published'] is True
    changed = await client.patch(url, headers=e['other'], json={'price_minor': 70_000})
    assert changed.status_code == 200, changed.text
    assert changed.json()['published'] is False
    assert (await client.get('/api/v1/gifts/products')).json() == []
    summary = await client.get('/api/v1/vendor/summary', headers=e['other'])
    assert summary.status_code == 200
    assert summary.json()['products'] == 1
    assert summary.json()['earnings_available'] is False
    assert (await client.get('/api/v1/vendor/orders', headers=e['other'])).status_code == 503
    assert (await client.get('/api/v1/vendor/earnings', headers=e['other'])).status_code == 503
    assert (await client.patch(url, headers=e['other'], json={'stock': None})).status_code == 422
    assert (
        await client.patch(url, headers=e['other'], json={'description': 'Updated description'})
    ).status_code == 200


@pytest.mark.asyncio
async def test_notification_delivery_and_owner_read_isolation(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert booking.status_code == 201, booking.text
    bid = booking.json()['id']
    owner_notices = await client.get('/api/v1/notifications', headers=e['owner'])
    assert owner_notices.status_code == 200
    assert [n['kind'] for n in owner_notices.json()] == ['booking_requested']
    assert (await client.get('/api/v1/notifications', headers=e['customer'])).json() == []
    await client.post(f'/api/v1/bookings/{bid}/accept', headers=e['owner'])
    customer_notices = await client.get('/api/v1/notifications', headers=e['customer'])
    assert [n['kind'] for n in customer_notices.json()] == ['booking_accepted']
    other_read = await client.post(
        f'/api/v1/notifications/{customer_notices.json()[0]["id"]}/read',
        headers=e['owner'],
    )
    assert other_read.status_code == 404
    read = await client.post(
        f'/api/v1/notifications/{customer_notices.json()[0]["id"]}/read',
        headers=e['customer'],
    )
    assert read.status_code == 200 and read.json()['read_at']
    again = await client.post(
        f'/api/v1/notifications/{customer_notices.json()[0]["id"]}/read',
        headers=e['customer'],
    )
    assert again.json()['read_at'] == read.json()['read_at']
    assert (
        await client.get('/api/v1/notifications/unread-count', headers=e['customer'])
    ).json()['unread_count'] == 0
    sent = await client.post(
        f'/api/v1/chat/bookings/{bid}/messages', headers=e['customer'],
        json={'kind': 'text', 'body': 'Hello companion'},
    )
    assert sent.status_code == 201, sent.text
    owner_notices = await client.get('/api/v1/notifications', headers=e['owner'])
    assert {n['kind'] for n in owner_notices.json()} == {'booking_requested', 'chat_message'}
    assert (
        await client.get('/api/v1/notifications', headers=e['customer'],
                         params={'unread_only': True})
    ).json() == []


@pytest.mark.asyncio
async def test_beta_invitation_feedback_admin_isolation_and_revocation(prepared):
    e, client = prepared, prepared['client']
    me = await client.get('/api/v1/auth/me', headers=e['customer'])
    uid = me.json()['id']
    url = f'/api/v1/beta/admin/enrollments/{uid}'
    assert (await client.get('/api/v1/beta/me', headers=e['customer'])).status_code == 403
    assert (
        await client.put(url, headers=e['customer'], json={'enabled': True})
    ).status_code == 403
    enrolled = await client.put(url, headers=e['admin'], json={'enabled': True})
    assert enrolled.status_code == 200, enrolled.text
    assert enrolled.json()['enabled'] is True
    assert (await client.get('/api/v1/beta/me', headers=e['customer'])).status_code == 200
    feedback = await client.post('/api/v1/beta/feedback', headers=e['customer'],
                                 json={'category': 'usability', 'rating': 4,
                                       'description': 'Search options need a clearer label'})
    assert feedback.status_code == 201, feedback.text
    assert (
        await client.get('/api/v1/beta/admin/feedback', headers=e['other'])
    ).status_code == 403
    admin_feedback = await client.get('/api/v1/beta/admin/feedback', headers=e['admin'])
    assert admin_feedback.status_code == 200 and len(admin_feedback.json()) == 1
    readiness = await client.get('/api/v1/beta/admin/readiness', headers=e['admin'])
    assert readiness.json()['beta_live'] is False
    assert readiness.json()['ready'] is False
    assert (
        await client.put(url, headers=e['admin'], json={'enabled': False})
    ).status_code == 200
    assert (
        await client.post('/api/v1/beta/feedback', headers=e['customer'],
                          json={'category': 'bug', 'rating': 1,
                                'description': 'This should not be accepted'})
    ).status_code == 403


@pytest.mark.asyncio
async def test_gift_preview_rechecks_stock_after_vendor_edit(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    bid = await accepted_booking(e, service)
    pid = await offer_product(e, stock=4)
    assert (await client.put(f'/api/v1/gifts/cart/{pid}', headers=e['customer'],
                             json={'quantity': 3})).status_code == 200
    assert (await client.get(f'/api/v1/integration/bookings/{bid}/preview',
                             headers=e['customer'])).status_code == 200
    changed = await client.patch(f'/api/v1/vendor/products/{pid}', headers=e['other'],
                                 json={'stock': 2})
    assert changed.status_code == 200 and changed.json()['published'] is True
    stale = await client.get(f'/api/v1/integration/bookings/{bid}/preview',
                             headers=e['customer'])
    assert stale.status_code == 409
    assert stale.json()['code'] == 'gift_unavailable'


@pytest.mark.asyncio
async def test_vendor_cannot_edit_another_vendors_listing(prepared):
    e, client = prepared, prepared['client']
    pid = await offer_product(e)
    async with e['app'].state.db_session_factory() as session:
        session.add(UserRole(user_id=UUID(e['owner_id']), role=UserRoleType.VENDOR))
        await session.commit()
    url = f'/api/v1/vendor/products/{pid}'
    wrong = await client.patch(url, headers=e['owner'], json={'price_minor': 1})
    assert wrong.status_code == 404
    detail = await client.get(f'/api/v1/gifts/products/{pid}')
    assert detail.status_code == 200
    assert detail.json()['price_minor'] == 100_000


@pytest.mark.asyncio
async def test_replayed_signed_payment_event_notifies_once(prepared):
    from .test_payments import FakePaymentProvider
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    bid = await accepted_booking(e, service)
    provider = FakePaymentProvider()
    e['app'].state.payment_provider = provider
    e['app'].state.settings = e['app'].state.settings.model_copy(
        update={'platform_fee_bps': 0}
    )
    checkout = await client.post(
        f'/api/v1/payments/bookings/{bid}',
        headers={**e['customer'], 'Idempotency-Key': 'notice-test-payment'},
    )
    assert checkout.status_code == 201, checkout.text
    assert (await client.post('/api/v1/payments/webhook',
                              content=b'signed')).status_code == 204
    assert (await client.post('/api/v1/payments/webhook',
                              content=b'signed')).status_code == 204
    notices = (await client.get('/api/v1/notifications',
                                headers=e['customer'])).json()
    assert [n['kind'] for n in notices].count('payment_confirmed') == 1
    owner = (await client.get('/api/v1/notifications', headers=e['owner'])).json()
    assert [n['kind'] for n in owner].count('payment_confirmed') == 1
