"""Offline CLICK test wire protocol + personally fulfilled gift demo orders."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import SecretStr

from yondo_api.config import Settings
from yondo_api.gifts.models import GiftProduct
from yondo_api.models.user import UserRole, UserRoleType

SECRET = 'local-click-test-only-secret-that-is-never-production'
SERVICE = 726314


def enable_demo(e):
    e['app'].state.settings = e['app'].state.settings.model_copy(
        update={
            'click_test_enabled': True,
            'click_test_service_id': SERVICE,
            'click_test_secret': SecretStr(SECRET),
        }
    )


async def product_and_cart(e, *, currency='UZS', stock=7, price=120_000, quantity=2):
    async with e['app'].state.db_session_factory() as session:
        session.add(UserRole(user_id=UUID(e['other_id']), role=UserRoleType.VENDOR))
        await session.commit()
    response = await e['client'].post(
        '/api/v1/gifts/vendor/products',
        headers=e['other'],
        json={
            'category': 'flowers',
            'name': 'Handmade gift box',
            'description': 'Packed for personal delivery',
            'price_minor': price,
            'currency': currency,
            'stock': stock,
        },
    )
    assert response.status_code == 201, response.text
    pid = response.json()['id']
    approved = await e['client'].post(
        f'/api/v1/gifts/admin/products/{pid}/publish', headers=e['admin']
    )
    assert approved.status_code == 200, approved.text
    cart = await e['client'].put(
        f'/api/v1/gifts/cart/{pid}', headers=e['customer'],
        json={'quantity': quantity},
    )
    assert cart.status_code == 200, cart.text
    return pid


async def new_test_order(e, *, method='manual_delivery'):
    note = 'Arrange delivery through operator after confirming the order'
    response = await e['client'].post(
        '/api/v1/gifts/test-orders',
        headers=e['customer'],
        json={'delivery_method': method, 'delivery_note': note},
    )
    assert response.status_code == 201, response.text
    return response.json()


def signed(
    order: dict,
    *,
    action: int,
    trans_id: int = 1001100,
    amount: str | None = None,
    error: int = 0,
    prepare_id: int | None = None,
    secret: str = SECRET,
):
    amount = amount or str(Decimal(order['subtotal_minor']) / Decimal(100))
    fields = {
        'click_trans_id': str(trans_id),
        'service_id': str(SERVICE),
        'click_paydoc_id': '902',
        'merchant_trans_id': order['id'],
        'amount': amount,
        'action': str(action),
        'error': str(error),
        'error_note': 'test',
        'sign_time': datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S'),
    }
    parts = [
        fields['click_trans_id'],
        fields['service_id'],
        secret,
        fields['merchant_trans_id'],
    ]
    if action == 1:
        fields['merchant_prepare_id'] = str(prepare_id if prepare_id is not None else trans_id)
        parts.append(fields['merchant_prepare_id'])
    parts += [fields['amount'], fields['action'], fields['sign_time']]
    fields['sign_string'] = hashlib.md5(''.join(parts).encode('utf-8')).hexdigest()
    return fields


async def click_callback(e, action, fields):
    return await e['client'].post(
        f'/api/v1/gifts/click-test/{action}',
        data=fields,
    )


@pytest.mark.asyncio
async def test_test_only_gate_default_off_and_production_forbidden(prepared):
    e, client = prepared, prepared['client']
    assert (
        await client.post('/api/v1/gifts/test-orders', headers=e['customer'],
                          json={'delivery_method': 'pickup'})
    ).status_code == 404
    assert (await client.post('/api/v1/gifts/click-test/prepare', data={})).status_code == 404
    assert (await client.post('/api/v1/gifts/checkout', headers=e['customer'])).status_code == 503
    with pytest.raises(ValueError, match='CLICK test mode requires'):
        Settings(
            environment='production',
            auth_otp_pepper='production-test-only-otp-pepper-long-secret',
            click_test_enabled=True,
            click_test_service_id=SERVICE,
            click_test_secret=SecretStr(SECRET),
        )
    with pytest.raises(ValueError, match='CLICK test mode requires'):
        Settings(environment='test', click_test_enabled=True, click_test_service_id=SERVICE)


@pytest.mark.asyncio
async def test_manual_gift_test_order_reserves_stock_snapshots_and_protects_privacy(prepared):
    e, client = prepared, prepared['client']
    enable_demo(e)
    pid = await product_and_cart(e)
    assert (
        await client.post('/api/v1/gifts/test-orders', headers=e['customer'],
                          json={'delivery_method': 'manual_delivery'})
    ).status_code == 422
    order = await new_test_order(e)
    assert order['subtotal_minor'] == 240_000
    assert order['currency'] == 'UZS'
    assert order['status'] == 'awaiting_test_payment'
    assert order['is_test_order'] is True and order['real_money_moved'] is False
    assert order['payable_total_minor'] is None
    assert order['delivery_fee_minor'] is None
    assert order['items'][0]['name_snapshot'] == 'Handmade gift box'
    assert order['items'][0]['quantity'] == 2
    assert (
        await client.get('/api/v1/gifts/cart', headers=e['customer'])
    ).json() == []
    async with e['app'].state.db_session_factory() as session:
        gift = await session.get(GiftProduct, UUID(pid))
        assert gift.stock == 5
    assert (
        await client.get(f'/api/v1/gifts/test-orders/{order["id"]}', headers=e['owner'])
    ).status_code == 403
    assert (
        await client.get('/api/v1/admin/gifts/test-orders', headers=e['customer'])
    ).status_code == 403
    queue = await client.get('/api/v1/admin/gifts/test-orders', headers=e['admin'])
    assert queue.status_code == 200 and len(queue.json()) == 1
    assert queue.json()[0]['delivery_note'] == order['delivery_note']
    assert (
        await client.get('/api/v1/gifts/test-orders', headers=e['customer'])
    ).json()[0]['id'] == order['id']


@pytest.mark.asyncio
async def test_offline_click_prepare_complete_and_duplicate_are_idempotent(prepared):
    e, client = prepared, prepared['client']
    enable_demo(e)
    await product_and_cart(e)
    order = await new_test_order(e)
    prepare = signed(order, action=0)
    received = await click_callback(e, 'prepare', prepare)
    assert received.status_code == 200, received.text
    assert received.json()['error'] == 0
    assert received.json()['merchant_prepare_id'] == 1001100
    again = await click_callback(e, 'prepare', prepare)
    assert again.json()['error'] == 0
    assert again.json()['merchant_prepare_id'] == 1001100
    complete = signed(order, action=1, prepare_id=1001100)
    finished = await click_callback(e, 'complete', complete)
    assert finished.status_code == 200
    assert finished.json()['error'] == 0
    replayed = await click_callback(e, 'complete', complete)
    assert replayed.json()['error'] == 0
    detail = await client.get(
        f'/api/v1/gifts/test-orders/{order["id"]}', headers=e['customer']
    )
    assert detail.json()['status'] == 'test_paid'
    assert detail.json()['real_money_moved'] is False
    assert (
        await click_callback(e, 'prepare', signed(order, action=0, trans_id=1001101))
    ).json()['error'] == -4


@pytest.mark.asyncio
async def test_bad_click_test_signature_wrong_amount_and_conflicting_prepare_fail(prepared):
    e, client = prepared, prepared['client']
    enable_demo(e)
    await product_and_cart(e)
    order = await new_test_order(e)
    bad = signed(order, action=0)
    bad['sign_string'] = '0' * 32
    assert (await click_callback(e, 'prepare', bad)).json()['error'] == -1
    bad_amount = signed(order, action=0, amount='999.99')
    assert (await click_callback(e, 'prepare', bad_amount)).json()['error'] == -2
    prepared = signed(order, action=0)
    assert (await click_callback(e, 'prepare', prepared)).json()['error'] == 0
    other_transaction = signed(order, action=0, trans_id=1001200)
    assert (
        await click_callback(e, 'prepare', other_transaction)
    ).json()['error'] == -8
    invalid_confirm = signed(order, action=1, prepare_id=1234)
    assert (await click_callback(e, 'complete', invalid_confirm)).json()['error'] == -6
    malformed = await client.post(
        '/api/v1/gifts/click-test/complete',
        content=b'service_id=1&service_id=2',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    assert malformed.json()['error'] == -8
    assert (
        await client.get(f'/api/v1/gifts/test-orders/{order["id"]}',
                         headers=e['customer'])
    ).json()['status'] == 'awaiting_test_payment'


@pytest.mark.asyncio
async def test_operator_can_deliver_self_fulfilled_test_order_after_fake_payment(prepared):
    e, client = prepared, prepared['client']
    enable_demo(e)
    await product_and_cart(e)
    order = await new_test_order(e)
    url = f'/api/v1/gifts/click-test/admin/orders/{order["id"]}/simulate'
    assert (
        await client.post(url, headers=e['customer'], json={'result': 'success'})
    ).status_code == 403
    simulated = await client.post(url, headers=e['admin'], json={'result': 'success'})
    assert simulated.status_code == 200, simulated.text
    assert simulated.json()['status'] == 'test_paid'
    assert simulated.json()['real_money_moved'] is False
    status_url = f'/api/v1/admin/gifts/test-orders/{order["id"]}/status'
    assert (
        await client.post(status_url, headers=e['owner'], json={'status': 'delivered'})
    ).status_code == 403
    for next_status in ('preparing', 'out_for_delivery', 'delivered'):
        response = await client.post(
            status_url, headers=e['admin'], json={'status': next_status}
        )
        assert response.status_code == 200, response.text
        assert response.json()['status'] == next_status
    duplicate = await client.post(
        status_url, headers=e['admin'], json={'status': 'delivered'}
    )
    assert duplicate.status_code == 409
    assert (
        await client.post(status_url, headers=e['admin'], json={'status': 'cancelled'})
    ).status_code == 409


@pytest.mark.asyncio
async def test_test_order_cancellation_restocks_and_complete_does_not_reopen(prepared):
    e, client = prepared, prepared['client']
    enable_demo(e)
    pid = await product_and_cart(e, stock=3)
    order = await new_test_order(e)
    prepare = signed(order, action=0)
    assert (await click_callback(e, 'prepare', prepare)).json()['error'] == 0
    status_url = f'/api/v1/admin/gifts/test-orders/{order["id"]}/status'
    cancelled = await client.post(
        status_url, headers=e['admin'], json={'status': 'cancelled'}
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()['status'] == 'cancelled'
    async with e['app'].state.db_session_factory() as session:
        product = await session.get(GiftProduct, UUID(pid))
        assert product.stock == 3
    complete = signed(order, action=1)
    assert (await click_callback(e, 'complete', complete)).json()['error'] == -9
    duplicate = await client.post(
        status_url, headers=e['admin'], json={'status': 'cancelled'}
    )
    assert duplicate.status_code == 409
    async with e['app'].state.db_session_factory() as session:
        product = await session.get(GiftProduct, UUID(pid))
        assert product.stock == 3


@pytest.mark.asyncio
async def test_click_cancel_callback_restores_stock_only_once(prepared):
    e, client = prepared, prepared['client']
    enable_demo(e)
    pid = await product_and_cart(e, stock=4)
    order = await new_test_order(e)
    assert (
        await click_callback(e, 'prepare', signed(order, action=0))
    ).json()['error'] == 0
    failed = signed(order, action=1, error=-1)
    assert (await click_callback(e, 'complete', failed)).json()['error'] == -9
    assert (await click_callback(e, 'complete', failed)).json()['error'] == -9
    async with e['app'].state.db_session_factory() as session:
        product = await session.get(GiftProduct, UUID(pid))
        assert product.stock == 4
    detail = await client.get(
        f'/api/v1/gifts/test-orders/{order["id"]}', headers=e['customer']
    )
    assert detail.json()['status'] == 'cancelled'


@pytest.mark.asyncio
async def test_click_test_rejects_foreign_currency(prepared):
    e, client = prepared, prepared['client']
    enable_demo(e)
    await product_and_cart(e, currency='USD')
    result = await client.post(
        '/api/v1/gifts/test-orders', headers=e['customer'],
        json={'delivery_method': 'pickup'},
    )
    assert result.status_code == 409
    assert result.json()['code'] == 'click_test_currency_unsupported'


@pytest.mark.asyncio
async def test_postgres_two_buyers_cannot_reserve_the_same_last_stock(prepared):
    import asyncio

    e, client = prepared, prepared['client']
    if e['app'].state.db_engine.dialect.name != 'postgresql':
        pytest.skip('Requires a migrated PostgreSQL test database and concurrent connections')
    enable_demo(e)
    pid = await product_and_cart(e, stock=2, quantity=2)
    async with e['app'].state.db_session_factory() as session:
        session.add(UserRole(user_id=UUID(e['owner_id']), role=UserRoleType.CUSTOMER))
        await session.commit()
    added = await client.put(
        f'/api/v1/gifts/cart/{pid}', headers=e['owner'], json={'quantity': 2}
    )
    assert added.status_code == 200, added.text
    req = {'delivery_method': 'pickup'}
    responses = await asyncio.gather(
        client.post('/api/v1/gifts/test-orders', headers=e['customer'], json=req),
        client.post('/api/v1/gifts/test-orders', headers=e['owner'], json=req),
    )
    assert sorted(x.status_code for x in responses) == [201, 409], [
        (x.status_code, x.text) for x in responses
    ]
    async with e['app'].state.db_session_factory() as session:
        product = await session.get(GiftProduct, UUID(pid))
        assert product.stock == 0


@pytest.mark.asyncio
async def test_test_click_signature_age_and_unauthorized_admin_cancel(prepared):
    e, client = prepared, prepared['client']
    enable_demo(e)
    await product_and_cart(e)
    order = await new_test_order(e)
    expired = signed(order, action=0)
    expired['sign_time'] = '2020-01-01 00:00:00'
    parts = [
        expired['click_trans_id'], expired['service_id'], SECRET, expired['merchant_trans_id'],
        expired['amount'], expired['action'], expired['sign_time'],
    ]
    expired['sign_string'] = hashlib.md5(''.join(parts).encode('utf-8')).hexdigest()
    stale = await click_callback(e, 'prepare', expired)
    assert stale.json()['error'] == -1
    url = f'/api/v1/admin/gifts/test-orders/{order["id"]}/status'
    not_admin = await client.post(
        url, headers=e['customer'], json={'status': 'cancelled'}
    )
    assert not_admin.status_code == 403
    allowed = await client.post(
        url, headers=e['admin'], json={'status': 'cancelled'}
    )
    assert allowed.status_code == 200
    assert allowed.json()['status'] == 'cancelled'


@pytest.mark.asyncio
async def test_postgres_repeated_same_customer_checkout_creates_only_one_order(prepared):
    import asyncio

    e, client = prepared, prepared['client']
    if e['app'].state.db_engine.dialect.name != 'postgresql':
        pytest.skip('Requires PostgreSQL row locks to serialize concurrent cart checkout')
    enable_demo(e)
    pid = await product_and_cart(e, stock=8, quantity=2)
    request = {'delivery_method': 'pickup'}
    results = await asyncio.gather(
        client.post('/api/v1/gifts/test-orders', headers=e['customer'], json=request),
        client.post('/api/v1/gifts/test-orders', headers=e['customer'], json=request),
    )
    assert sorted(r.status_code for r in results) == [201, 409], [
        (r.status_code, r.text) for r in results
    ]
    async with e['app'].state.db_session_factory() as session:
        product = await session.get(GiftProduct, UUID(pid))
        assert product.stock == 6
    own = await client.get('/api/v1/gifts/test-orders', headers=e['customer'])
    assert own.status_code == 200
    assert len(own.json()) == 1
