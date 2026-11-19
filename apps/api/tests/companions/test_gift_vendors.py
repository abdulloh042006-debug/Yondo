"""Gift vendors (product decisions §4; CEO answers 2026-11-19; docs/gifts.md)."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import func, select, update

from yondo_api.account.deletion import erase_account
from yondo_api.admin.models import AdminAuditEvent
from yondo_api.gifts.models import GiftProduct
from yondo_api.gifts.orders_models import GiftTestOrder
from yondo_api.gifts.shop_models import VendorShop
from yondo_api.models.user import User, UserRole, UserRoleType
from yondo_api.notifications.models import UserNotification
from yondo_api.verification.models import IdentityVerification

from .test_manual_gifts_click_test import enable_demo

SHOP = {
    'name': 'Gul uyi',
    'description': 'Fresh flowers and small gifts, wrapped by hand.',
    'city': 'Toshkent',
    'delivery_area': 'Toshkent shahri ichida',
}
PRODUCT = {
    'category': 'flowers',
    'name': 'Bahor guldastasi',
    'description': 'Seven tulips',
    'price_minor': 150_000,
    'currency': 'UZS',
    'stock': 5,
}


async def verified_id(e, user_id: str):
    async with e['app'].state.db_session_factory() as session:
        session.add(
            IdentityVerification(
                user_id=UUID(user_id),
                status='verified',
                document_type='id_card',
                submitted_at=datetime.now(UTC),
                reviewed_at=datetime.now(UTC),
            )
        )
        await session.commit()


async def approved_vendor(e, who='other'):
    client = e['client']
    assert (
        await client.put('/api/v1/gifts/vendor/shop', headers=e[who], json=SHOP)
    ).status_code == 200
    await verified_id(e, e[f'{who}_id'])
    shop = (await client.get('/api/v1/gifts/vendor/shop', headers=e[who])).json()
    decided = await client.post(
        f'/api/v1/admin/vendors/{shop["id"]}/decision',
        headers=e['admin'],
        json={'decision': 'approve', 'note': 'ID and shop checked'},
    )
    assert decided.status_code == 200, decided.text
    return shop['id']


async def published_product(e, who='other', **extra):
    client = e['client']
    created = await client.post(
        '/api/v1/gifts/vendor/products', headers=e[who], json={**PRODUCT, **extra}
    )
    assert created.status_code == 201, created.text
    pid = created.json()['id']
    published = await client.post(f'/api/v1/gifts/admin/products/{pid}/publish', headers=e['admin'])
    assert published.status_code == 200, published.text
    return pid


async def count(e, model, *where):
    async with e['app'].state.db_session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model).where(*where))


@pytest.mark.asyncio
async def test_vendor_role_is_never_self_assigned(env):
    refused = await env['client'].put(
        '/api/v1/auth/roles', headers=env['other'], json={'roles': ['customer', 'vendor']}
    )
    assert refused.status_code == 403 and refused.json()['code'] == 'vendor_requires_approval'


@pytest.mark.asyncio
async def test_shop_application_needs_verified_id_then_approval_activates_the_vendor(env):
    e, client = env, env['client']
    bad = await client.put(
        '/api/v1/gifts/vendor/shop', headers=e['other'], json={**SHOP, 'name': 'x'}
    )
    assert bad.status_code == 422
    applied = await client.put('/api/v1/gifts/vendor/shop', headers=e['other'], json=SHOP)
    assert applied.json()['status'] == 'pending' and applied.json()['identity_verified'] is False
    # No Vendor role yet: no products.
    assert (
        await client.post('/api/v1/gifts/vendor/products', headers=e['other'], json=PRODUCT)
    ).status_code == 403
    shop_id = applied.json()['id']
    queue = (await client.get('/api/v1/admin/vendors?status=pending', headers=e['admin'])).json()
    assert [row['id'] for row in queue] == [shop_id]
    url = f'/api/v1/admin/vendors/{shop_id}/decision'
    no_id = await client.post(
        url, headers=e['admin'], json={'decision': 'approve', 'note': 'no ID'}
    )
    assert no_id.status_code == 409 and no_id.json()['code'] == 'identity_not_verified'
    await verified_id(e, e['other_id'])
    approved = await client.post(
        url, headers=e['admin'], json={'decision': 'approve', 'note': 'ok!'}
    )
    assert approved.status_code == 200 and approved.json()['status'] == 'approved'
    assert (
        await count(
            e,
            UserRole,
            UserRole.user_id == UUID(e['other_id']),
            UserRole.role == UserRoleType.VENDOR,
        )
        == 1
    )
    assert await count(e, AdminAuditEvent, AdminAuditEvent.action == 'vendor_shop_approved') == 1
    assert await count(e, UserNotification, UserNotification.kind == 'vendor_approved') == 1
    # Keeping the role through PUT /auth/roles is allowed once approved.
    kept = await client.put(
        '/api/v1/auth/roles', headers=e['other'], json={'roles': ['customer', 'vendor']}
    )
    assert kept.status_code == 200, kept.text


@pytest.mark.asyncio
async def test_rejected_application_returns_to_review_when_edited(env):
    e, client = env, env['client']
    shop = (await client.put('/api/v1/gifts/vendor/shop', headers=e['owner'], json=SHOP)).json()
    rejected = await client.post(
        f'/api/v1/admin/vendors/{shop["id"]}/decision',
        headers=e['admin'],
        json={'decision': 'reject', 'note': 'Describe what you sell'},
    )
    assert rejected.json()['status'] == 'rejected'
    mine = (await client.get('/api/v1/gifts/vendor/shop', headers=e['owner'])).json()
    assert mine['review_note'] == 'Describe what you sell'
    again = await client.put(
        '/api/v1/gifts/vendor/shop',
        headers=e['owner'],
        json={**SHOP, 'description': 'Tulips, roses and tea sets, wrapped by hand.'},
    )
    assert again.json()['status'] == 'pending' and again.json()['review_note'] is None
    assert await count(e, UserNotification, UserNotification.kind == 'vendor_rejected') == 1


@pytest.mark.asyncio
async def test_catalogue_follows_the_shop_status_and_product_rejection(env):
    e, client = env, env['client']
    shop_id = await approved_vendor(e)
    pid = await published_product(e)
    assert [p['id'] for p in (await client.get('/api/v1/gifts/products')).json()] == [pid]
    suspended = await client.post(
        f'/api/v1/admin/vendors/{shop_id}/suspend',
        headers=e['admin'],
        json={'reason': 'Customer complaints are being checked'},
    )
    assert suspended.json()['status'] == 'suspended'
    assert (await client.get('/api/v1/gifts/products')).json() == []
    assert (await client.get(f'/api/v1/gifts/products/{pid}')).status_code == 404
    assert await count(e, UserNotification, UserNotification.kind == 'vendor_suspended') == 1
    assert await count(e, AdminAuditEvent, AdminAuditEvent.action == 'vendor_shop_suspended') == 1
    # A suspended shop cannot add products, but keeps the role.
    assert (
        await client.post('/api/v1/gifts/vendor/products', headers=e['other'], json=PRODUCT)
    ).json()['code'] == 'vendor_shop_not_approved'
    reinstated = await client.post(
        f'/api/v1/admin/vendors/{shop_id}/decision',
        headers=e['admin'],
        json={'decision': 'approve', 'note': 'Checked, fine'},
    )
    assert reinstated.json()['status'] == 'approved'
    assert len((await client.get('/api/v1/gifts/products')).json()) == 1
    rejected = await client.post(
        f'/api/v1/gifts/admin/products/{pid}/reject',
        headers=e['admin'],
        json={'note': 'Photo and description do not match'},
    )
    assert rejected.json()['published'] is False
    assert rejected.json()['rejection_note'] == 'Photo and description do not match'
    assert await count(e, UserNotification, UserNotification.kind == 'gift_product_rejected') == 1
    republished = await client.post(
        f'/api/v1/gifts/admin/products/{pid}/publish', headers=e['admin']
    )
    assert republished.json()['rejection_note'] is None


@pytest.mark.asyncio
async def test_checkout_splits_per_vendor_and_each_shop_moves_its_own_order(env):
    e, client = env, env['client']
    enable_demo(e)
    await approved_vendor(e, 'other')
    await approved_vendor(e, 'owner')
    first = await published_product(e, 'other')
    second = await published_product(e, 'owner', name='Choy toʻplami', category='gift_box')
    for pid in (first, second):
        added = await client.put(
            f'/api/v1/gifts/cart/{pid}', headers=e['customer'], json={'quantity': 1}
        )
        assert added.status_code == 200, added.text
    created = await client.post(
        '/api/v1/gifts/test-orders',
        headers=e['customer'],
        json={'delivery_method': 'manual_delivery', 'delivery_note': 'Chilonzor 5, 3-podezd'},
    )
    assert created.status_code == 201, created.text
    orders = created.json()
    assert len(orders) == 2 and {o['subtotal_minor'] for o in orders} == {150_000}
    vendor_view = (await client.get('/api/v1/vendor/orders', headers=e['other'])).json()
    assert len(vendor_view) == 1
    order = vendor_view[0]
    # Privacy (CEO, 2026-11-19): items, method and the customer's own note; never who they are.
    assert order['customer_label'] == 'Mijoz' and 'customer_id' not in order
    assert order['delivery_note'] == 'Chilonzor 5, 3-podezd' and len(order['short_code']) == 6
    status_url = f'/api/v1/vendor/orders/{order["id"]}/status'
    early = await client.post(status_url, headers=e['other'], json={'status': 'preparing'})
    assert early.status_code == 409  # not paid yet (test payment)
    foreign = await client.post(
        f'/api/v1/vendor/orders/{order["id"]}/status',
        headers=e['owner'],
        json={'status': 'preparing'},
    )
    assert foreign.status_code == 404
    async with e['app'].state.db_session_factory() as session:
        await session.execute(
            update(GiftTestOrder)
            .where(GiftTestOrder.id == UUID(order['id']))
            .values(status='test_paid')
        )
        await session.commit()
    for status in ('preparing', 'out_for_delivery', 'delivered'):
        moved = await client.post(status_url, headers=e['other'], json={'status': status})
        assert moved.status_code == 200 and moved.json()['status'] == status, moved.text
    late = await client.post(
        status_url, headers=e['other'], json={'status': 'cancelled', 'reason': 'x'}
    )
    assert late.status_code == 409
    for kind in ('gift_preparing', 'gift_out_for_delivery', 'gift_delivered'):
        assert await count(e, UserNotification, UserNotification.kind == kind) == 1
    # The shop is told about new orders.
    assert (
        await count(
            e,
            UserNotification,
            UserNotification.kind == 'gift_order_created',
            UserNotification.recipient_id == UUID(e['other_id']),
        )
        == 1
    )
    assert (await client.get('/api/v1/vendor/earnings', headers=e['other'])).status_code == 503


@pytest.mark.asyncio
async def test_cancellations_by_shop_and_customer(env):
    e, client = env, env['client']
    enable_demo(e)
    await approved_vendor(e)
    pid = await published_product(e)

    async def order_one():
        await client.put(f'/api/v1/gifts/cart/{pid}', headers=e['customer'], json={'quantity': 2})
        created = await client.post(
            '/api/v1/gifts/test-orders', headers=e['customer'], json={'delivery_method': 'pickup'}
        )
        return created.json()[0]

    async def stock():
        async with e['app'].state.db_session_factory() as session:
            return (await session.get(GiftProduct, UUID(pid))).stock

    order = await order_one()
    assert await stock() == 3
    mine = await client.post(
        f'/api/v1/gifts/test-orders/{order["id"]}/cancel', headers=e['customer'], json={}
    )
    assert mine.json()['status'] == 'cancelled' and await stock() == 5
    order = await order_one()
    url = f'/api/v1/vendor/orders/{order["id"]}/status'
    no_reason = await client.post(url, headers=e['other'], json={'status': 'cancelled'})
    assert (
        no_reason.status_code == 422 and no_reason.json()['code'] == 'gift_cancel_reason_required'
    )
    cancelled = await client.post(
        url, headers=e['other'], json={'status': 'cancelled', 'reason': 'Out of tulips today'}
    )
    assert cancelled.json()['cancel_reason'] == 'Out of tulips today' and await stock() == 5
    # The customer cannot cancel once the shop is preparing.
    order = await order_one()
    async with e['app'].state.db_session_factory() as session:
        await session.execute(
            update(GiftTestOrder)
            .where(GiftTestOrder.id == UUID(order['id']))
            .values(status='preparing')
        )
        await session.commit()
    too_late = await client.post(
        f'/api/v1/gifts/test-orders/{order["id"]}/cancel', headers=e['customer'], json={}
    )
    assert too_late.status_code == 409 and too_late.json()['code'] == 'gift_order_cancel_too_late'


@pytest.mark.asyncio
async def test_account_deletion_closes_and_de_identifies_the_shop(env):
    e = env
    await approved_vendor(e)
    pid = await published_product(e)
    async with e['app'].state.db_session_factory() as session:
        user = await session.get(User, UUID(e['other_id']))
        await erase_account(session, user, e['storage'], datetime.now(UTC))
        await session.commit()
        shop = await session.scalar(select(VendorShop))
        assert shop.status == 'suspended' and shop.name == 'deleted' and shop.city == ''
        assert (await session.get(GiftProduct, UUID(pid))).published is False
