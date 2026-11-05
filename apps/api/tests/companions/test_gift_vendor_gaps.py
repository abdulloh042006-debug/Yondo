from uuid import UUID

import pytest
from sqlalchemy import select

from yondo_api.admin.models import AdminAuditEvent
from yondo_api.gifts.models import GiftCartItem, GiftProduct
from yondo_api.gifts.orders_models import GiftTestOrder, GiftTestOrderItem
from yondo_api.models.user import UserRole, UserRoleType

PRODUCT = {
    'category': 'flowers',
    'name': 'Tulip bouquet',
    'description': 'Fresh seasonal flowers',
    'price_minor': 120000,
    'currency': 'UZS',
    'stock': 3,
}


async def vendor_product(e, **overrides):
    async with e['app'].state.db_session_factory() as session:
        if await session.get(UserRole, (UUID(e['other_id']), UserRoleType.VENDOR)) is None:
            session.add(UserRole(user_id=UUID(e['other_id']), role=UserRoleType.VENDOR))
            await session.commit()
    created = await e['client'].post(
        '/api/v1/gifts/vendor/products', headers=e['other'], json=PRODUCT | overrides
    )
    assert created.status_code == 201, created.text
    return created.json()['id']


@pytest.mark.asyncio
async def test_admin_product_list_includes_unpublished_and_audits_decisions(prepared):
    e, client = prepared, prepared['client']
    draft = await vendor_product(e, name='Draft box', stock=0)
    ready = await vendor_product(e, name='Ready box')
    url = '/api/v1/gifts/admin/products'
    for headers in (e['other'], e['customer']):
        denied = await client.get(url, headers=headers)
        assert denied.status_code == 403
        assert denied.json()['code'] == 'role_required'
    everything = await client.get(url, headers=e['admin'])
    assert everything.status_code == 200, everything.text
    assert {row['id'] for row in everything.json()} == {draft, ready}
    assert (await client.get('/api/v1/gifts/products')).json() == []

    published = await client.post(
        f'/api/v1/gifts/admin/products/{ready}/publish', headers=e['admin']
    )
    assert published.status_code == 200, published.text
    pending = await client.get(url, headers=e['admin'], params={'published': 'false'})
    assert [row['id'] for row in pending.json()] == [draft]
    live = await client.get(url, headers=e['admin'], params={'published': 'true'})
    assert [row['id'] for row in live.json()] == [ready]
    own = await client.get(url, headers=e['admin'], params={'vendor_id': e['other_id']})
    assert len(own.json()) == 2
    nobody = await client.get(url, headers=e['admin'], params={'vendor_id': e['owner_id']})
    assert nobody.json() == []

    withdrawn = await client.post(
        f'/api/v1/gifts/admin/products/{ready}/unpublish', headers=e['admin']
    )
    assert withdrawn.status_code == 200, withdrawn.text
    async with e['app'].state.db_session_factory() as session:
        events = list(
            await session.scalars(
                select(AdminAuditEvent)
                .where(AdminAuditEvent.action.like('gift_product_%'))
                .order_by(AdminAuditEvent.created_at)
            )
        )
    assert [event.action for event in events] == [
        'gift_product_published',
        'gift_product_unpublished',
    ]
    assert {str(event.target_id) for event in events} == {e['other_id']}
    assert {event.reason for event in events} == {f'gift_product:{ready}'}


@pytest.mark.asyncio
async def test_vendor_deletes_only_own_never_ordered_products(prepared):
    e, client = prepared, prepared['client']
    product_id = await vendor_product(e)
    assert (
        await client.post(f'/api/v1/gifts/admin/products/{product_id}/publish', headers=e['admin'])
    ).status_code == 200
    carted = await client.put(
        f'/api/v1/gifts/cart/{product_id}', headers=e['customer'], json={'quantity': 1}
    )
    assert carted.status_code == 200, carted.text

    # Without the vendor role (admins included) the call is refused; another vendor gets 404.
    for headers in (e['admin'], e['customer']):
        denied = await client.delete(f'/api/v1/vendor/products/{product_id}', headers=headers)
        assert denied.status_code == 403
        assert denied.json()['code'] == 'role_required'
    async with e['app'].state.db_session_factory() as session:
        session.add(UserRole(user_id=UUID(e['owner_id']), role=UserRoleType.VENDOR))
        await session.commit()
    foreign = await client.delete(f'/api/v1/vendor/products/{product_id}', headers=e['owner'])
    assert foreign.status_code == 404
    assert foreign.json()['code'] == 'gift_not_found'
    removed = await client.delete(f'/api/v1/vendor/products/{product_id}', headers=e['other'])
    assert removed.status_code == 204, removed.text
    assert (await client.get('/api/v1/gifts/cart', headers=e['customer'])).json() == []
    assert (await client.get('/api/v1/gifts/products')).json() == []
    again = await client.delete(f'/api/v1/vendor/products/{product_id}', headers=e['other'])
    assert again.status_code == 404
    assert again.json()['code'] == 'gift_not_found'

    ordered = await vendor_product(e, name='Ordered box')
    async with e['app'].state.db_session_factory() as session:
        customer_id = (await client.get('/api/v1/auth/me', headers=e['customer'])).json()['id']
        order = GiftTestOrder(
            customer_id=UUID(customer_id), subtotal_minor=120000, delivery_method='pickup'
        )
        session.add(order)
        await session.flush()
        session.add(
            GiftTestOrderItem(
                order_id=order.id,
                product_id=UUID(ordered),
                name_snapshot='Ordered box',
                quantity=1,
                unit_price_minor=120000,
                line_total_minor=120000,
            )
        )
        await session.commit()
    blocked = await client.delete(f'/api/v1/vendor/products/{ordered}', headers=e['other'])
    assert blocked.status_code == 409
    assert blocked.json()['code'] == 'gift_product_in_use'
    async with e['app'].state.db_session_factory() as session:
        assert await session.get(GiftProduct, UUID(ordered)) is not None
        assert list(await session.scalars(select(GiftCartItem))) == []
