"""End-to-end in-app inbox integration for gift demo and completed meetings."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import SecretStr

from yondo_api.meetings import router as meeting_module
from yondo_api.models.user import AccountStatus, User

from .test_manual_gifts_click_test import (
    SECRET,
    SERVICE,
    click_callback,
    new_test_order,
    product_and_cart,
    signed,
)
from .test_phases11_15 import confirmed_booking


def enable_demo(e):
    e['app'].state.settings = e['app'].state.settings.model_copy(
        update={
            'click_test_enabled': True,
            'click_test_service_id': SERVICE,
            'click_test_secret': SecretStr(SECRET),
        }
    )


async def notices(e, role='customer', **params):
    r = await e['client'].get(
        '/api/v1/notifications', headers=e[role], params=params
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.asyncio
async def test_gift_order_notifies_admin_without_leaking_customer_details(prepared):
    e = prepared
    enable_demo(e)
    await product_and_cart(e)
    order = await new_test_order(e)
    admin = await notices(e, 'admin')
    assert len(admin) == 1
    assert admin[0]['kind'] == 'gift_order_created'
    assert admin[0]['gift_order_id'] == order['id']
    assert admin[0]['booking_id'] is None
    assert admin[0]['details']['is_test_order'] is True
    assert admin[0]['details']['real_money_moved'] is False
    assert 'delivery_note' not in str(admin[0]['details'])
    assert await notices(e, 'customer') == []
    assert await notices(e, 'owner') == []
    assert (
        await e['client'].post(
            f'/api/v1/notifications/{admin[0]["id"]}/read',
            headers=e['customer'],
        )
    ).status_code == 404
    assert (
        await e['client'].get('/api/v1/notifications/unread-count', headers=e['admin'])
    ).json()['unread_count'] == 1


@pytest.mark.asyncio
async def test_simulated_gift_fulfillment_inbox_read_all_and_pagination(prepared):
    e = prepared
    enable_demo(e)
    await product_and_cart(e)
    order = await new_test_order(e)
    simulation = await e['client'].post(
        f'/api/v1/gifts/click-test/admin/orders/{order["id"]}/simulate',
        headers=e['admin'], json={'result': 'success'},
    )
    assert simulation.status_code == 200, simulation.text
    api = f'/api/v1/admin/gifts/test-orders/{order["id"]}/status'
    for status in ('preparing', 'out_for_delivery', 'delivered'):
        r = await e['client'].post(
            api, headers=e['admin'], json={'status': status}
        )
        assert r.status_code == 200, r.text
    customer_notices = await notices(e)
    assert [n['kind'] for n in customer_notices] == [
        'gift_delivered',
        'gift_out_for_delivery',
        'gift_preparing',
        'gift_test_paid',
    ]
    assert all(n['booking_id'] is None for n in customer_notices)
    assert all(n['gift_order_id'] == order['id'] for n in customer_notices)
    assert (await notices(e, limit=2, offset=1)) == customer_notices[1:3]
    assert len(await notices(e, unread_only=True)) == 4
    assert (await e['client'].get(
        '/api/v1/notifications/unread-count', headers=e['customer']
    )).json()['unread_count'] == 4
    result = await e['client'].post(
        '/api/v1/notifications/read-all', headers=e['customer']
    )
    assert result.status_code == 200, result.text
    assert result.json()['marked_count'] == 4
    assert (await e['client'].post(
        '/api/v1/notifications/read-all', headers=e['customer']
    )).json()['marked_count'] == 0
    assert await notices(e, unread_only=True) == []
    assert (await e['client'].get(
        '/api/v1/notifications/unread-count', headers=e['admin']
    )).json()['unread_count'] == 1  # No cross-user mark-as-read side effects.
    assert (
        await e['client'].post(
            f'/api/v1/admin/gifts/test-orders/{order["id"]}/status',
            headers=e['admin'], json={'status': 'delivered'},
        )
    ).status_code == 409
    assert len(await notices(e)) == 4


@pytest.mark.asyncio
async def test_offline_click_complete_and_replay_enqueue_once(prepared):
    e = prepared
    enable_demo(e)
    await product_and_cart(e)
    order = await new_test_order(e)
    assert (await click_callback(e, 'prepare', signed(order, action=0))).json()['error'] == 0
    complete = signed(order, action=1)
    assert (await click_callback(e, 'complete', complete)).json()['error'] == 0
    assert (await click_callback(e, 'complete', complete)).json()['error'] == 0
    assert [n['kind'] for n in await notices(e)] == ['gift_test_paid']


@pytest.mark.asyncio
async def test_gift_cancelled_notifications_and_stock_restock(prepared):
    e = prepared
    enable_demo(e)
    await product_and_cart(e)
    order = await new_test_order(e)
    cancel = await e['client'].post(
        f'/api/v1/gifts/click-test/admin/orders/{order["id"]}/simulate',
        headers=e['admin'], json={'result': 'cancel'},
    )
    assert cancel.status_code == 200
    assert cancel.json()['status'] == 'cancelled'
    assert [n['kind'] for n in await notices(e)] == ['gift_cancelled']
    assert (
        await e['client'].post(
            f'/api/v1/gifts/click-test/admin/orders/{order["id"]}/simulate',
            headers=e['admin'], json={'result': 'cancel'},
        )
    ).status_code == 409
    assert [n['kind'] for n in await notices(e)] == ['gift_cancelled']


@pytest.mark.asyncio
async def test_completed_meeting_prompts_both_to_review_and_keeps_bookings_private(
    prepared, monkeypatch
):
    e = prepared
    bid = await confirmed_booking(e)
    root = f'/api/v1/meetings/bookings/{bid}'
    assert (await e['client'].post(root + '/check-in', headers=e['customer'])).status_code == 200
    assert (await e['client'].post(root + '/check-in', headers=e['owner'])).status_code == 200

    class FutureClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2027, 1, 10, 7, 0, tzinfo=UTC)

    monkeypatch.setattr(meeting_module, 'datetime', FutureClock)
    assert (await e['client'].post(root + '/start', headers=e['owner'])).status_code == 200
    assert (await e['client'].post(root + '/end', headers=e['customer'])).status_code == 200
    assert (await e['client'].post(root + '/end', headers=e['owner'])).status_code == 200
    for role in ('customer', 'owner'):
        review_notices = [n for n in await notices(e, role) if n['kind'] == 'review_reminder']
        assert len(review_notices) == 1
        assert review_notices[0]['booking_id'] == bid
        assert review_notices[0]['gift_order_id'] is None
    assert await notices(e, 'other') == []
    assert (
        await e['client'].post(root + '/end', headers=e['owner'])
    ).status_code == 409
    assert len([n for n in await notices(e) if n['kind'] == 'review_reminder']) == 1


@pytest.mark.asyncio
async def test_inactive_user_cannot_access_notification_inbox(prepared):
    e = prepared
    enable_demo(e)
    await product_and_cart(e)
    await new_test_order(e)
    async with e['app'].state.db_session_factory() as session:
        uid = UUID(e['other_id'])
        other = await session.get(User, uid)
        other.account_status = AccountStatus.RESTRICTED
        await session.commit()
    assert (
        await e['client'].get('/api/v1/notifications', headers=e['other'])
    ).status_code == 403
    assert (
        await e['client'].post('/api/v1/notifications/read-all', headers=e['other'])
    ).status_code == 403
