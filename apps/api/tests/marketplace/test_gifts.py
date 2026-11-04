from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from support import API, png

from yondo_api.core.time import utc_now
from yondo_api.gifts.models import Product
from yondo_api.models.user import UserRoleType
from yondo_api.payments.models import Payout

from .helpers import B, P, accepted_booking, checkout, pay

G = f'{API}/gifts'
VME = f'{API}/vendors/me'


async def make_vendor(market, name='Gul Bozori', products=(('flowers', 'Atirgul', 50_000, 5),)):
    headers, user_id = await market.user((UserRoleType.VENDOR,), name=name)
    applied = await market.client.post(
        VME,
        headers=headers,
        json={
            'name': name,
            'city': 'Tashkent',
            'currency': 'UZS',
            'delivery_fee_minor': 20_000,
            'delivery_time_minutes': 60,
        },
    )
    assert applied.status_code == 201, applied.text
    not_yet = await market.client.post(
        f'{VME}/products',
        headers=headers,
        json={'category': 'flowers', 'name': 'x', 'price_minor': 1, 'stock': 1},
    )
    assert not_yet.json()['code'] == 'vendor_not_approved'
    decided = await market.client.post(
        f'{API}/admin/vendors/{applied.json()["id"]}/decision',
        headers=market.admin,
        json={'decision': 'approve', 'note': 'Verified shop'},
    )
    assert decided.json()['status'] == 'approved'
    created = []
    for category, product_name, price, stock in products:
        product = await market.client.post(
            f'{VME}/products',
            headers=headers,
            json={'category': category, 'name': product_name, 'price_minor': price, 'stock': stock},
        )
        assert product.status_code == 201, product.text
        image = await market.client.post(
            f'{VME}/products/{product.json()["id"]}/images',
            headers={**headers, 'Content-Type': 'image/png'},
            content=png(),
        )
        assert image.status_code == 201, image.text
        created.append(product.json())
    return headers, user_id, created


def delivery(hours=3):
    return {
        'recipient_name': 'Dilnoza',
        'recipient_phone': '901112233',
        'address': 'Chilonzor 5',
        'delivery_at': (utc_now() + timedelta(hours=hours)).isoformat(),
    }


async def stock_of(market, product_id):
    async with market.app.state.db_session_factory() as session:
        return (await session.get(Product, UUID(product_id))).stock


async def test_catalog_cart_checkout_and_vendor_fulfilment(market):
    vendor_headers, vendor_id, products = await make_vendor(
        market, products=(('flowers', 'Atirgul', 50_000, 5), ('chocolate', 'Shokolad', 30_000, 2))
    )
    roses, chocolate = products
    categories = await market.client.get(f'{G}/categories', headers=market.customer)
    counts = {c['category']: c['products'] for c in categories.json()}
    assert counts['flowers'] == 1 and counts['toys'] == 0
    listed = await market.client.get(
        f'{G}/products', headers=market.customer, params={'category': 'flowers'}
    )
    card = listed.json()['items'][0]
    assert card['name'] == 'Atirgul' and card['image']['url'].startswith('https://storage.test/')
    page = await market.client.get(f'{G}/products/{roses["id"]}', headers=market.customer)
    assert page.json()['delivery_fee_minor'] == 20_000
    assert page.json()['vendor_name'] == 'Gul Bozori'
    fav = await market.client.put(
        f'{API}/favorites/products/{roses["id"]}', headers=market.customer
    )
    assert fav.status_code == 204
    favs = await market.client.get(f'{API}/favorites/products', headers=market.customer)
    assert favs.json()[0]['is_favorite'] is True
    too_many = await market.client.put(
        f'{G}/cart/items/{chocolate["id"]}', headers=market.customer, json={'quantity': 3}
    )
    assert too_many.json()['code'] == 'insufficient_stock'
    await market.client.put(
        f'{G}/cart/items/{roses["id"]}',
        headers=market.customer,
        json={'quantity': 2, 'note': 'Qizil'},
    )
    cart = await market.client.put(
        f'{G}/cart/items/{chocolate["id"]}', headers=market.customer, json={'quantity': 1}
    )
    assert cart.json()['subtotal_minor'] == 130_000
    soon = await market.client.post(
        f'{P}/gifts/checkout',
        headers=market.customer,
        json={'idempotency_key': 'gift-key-0001', 'delivery': delivery(hours=0.5)},
    )
    assert soon.json()['code'] == 'delivery_too_soon'
    payment = await market.client.post(
        f'{P}/gifts/checkout',
        headers=market.customer,
        json={'idempotency_key': 'gift-key-0001', 'delivery': delivery()},
    )
    assert payment.status_code == 200, payment.text
    body = payment.json()
    assert body['booking_id'] is None
    assert body['amount_minor'] == 150_000  # 130k goods + 20k delivery, 0% gift fee
    assert (await market.client.get(f'{G}/cart', headers=market.customer)).json()['items'] == []
    assert await stock_of(market, roses['id']) == 3
    vendor_orders = await market.client.get(f'{VME}/orders', headers=vendor_headers)
    assert vendor_orders.json()['items'] == []  # unpaid orders are invisible to vendors
    assert await pay(market, body['id']) == 'captured'
    orders = await market.client.get(f'{G}/orders', headers=market.customer)
    order = orders.json()['items'][0]
    assert order['status'] == 'new' and order['recipient_phone'] == '+998901112233'
    assert {i['product_name'] for i in order['items']} == {'Atirgul', 'Shokolad'}
    url = f'{VME}/orders/{order["id"]}/status'
    skip = await market.client.post(url, headers=vendor_headers, json={'status': 'delivered'})
    assert skip.json()['code'] == 'invalid_gift_transition'
    for status in ('accepted', 'preparing', 'courier_assigned', 'delivering', 'delivered'):
        moved = await market.client.post(url, headers=vendor_headers, json={'status': status})
        assert moved.status_code == 200, moved.text
    async with market.app.state.db_session_factory() as session:
        payout = (await session.scalars(select(Payout))).one()
    assert payout.beneficiary_id == vendor_id
    assert (payout.status, payout.amount_minor) == ('scheduled', 150_000)
    review = await market.client.post(
        f'{G}/orders/{order["id"]}/review',
        headers=market.customer,
        json={'rating': 5, 'text': 'Chiroyli'},
    )
    assert review.status_code == 201
    ratings = await market.client.get(f'{VME}/ratings', headers=vendor_headers)
    assert ratings.json()['rating_average'] == 5.0
    rated = await market.client.get(f'{G}/products/{roses["id"]}', headers=market.customer)
    assert rated.json()['rating_count'] == 1


async def test_customer_cancel_restores_stock_and_refunds(market):
    _, _, (roses,) = await make_vendor(market)
    payment = await market.client.post(
        f'{P}/gifts/checkout',
        headers=market.customer,
        json={
            'idempotency_key': 'gift-key-0002',
            'delivery': delivery(),
            'items': [{'product_id': roses['id'], 'quantity': 2}],
        },
    )
    await pay(market, payment.json()['id'])
    order = (await market.client.get(f'{G}/orders', headers=market.customer)).json()['items'][0]
    cancelled = await market.client.post(
        f'{G}/orders/{order["id"]}/cancel', headers=market.customer
    )
    assert cancelled.json()['status'] == 'cancelled'
    assert await stock_of(market, roses['id']) == 5
    state = await market.client.get(f'{P}/{payment.json()["id"]}', headers=market.customer)
    assert state.json()['status'] == 'refunded'


async def test_unpaid_orders_release_stock_on_failure(market):
    _, _, (roses,) = await make_vendor(market)
    payment = await market.client.post(
        f'{P}/gifts/checkout',
        headers=market.customer,
        json={
            'idempotency_key': 'gift-key-0003',
            'delivery': delivery(),
            'items': [{'product_id': roses['id'], 'quantity': 5}],
        },
    )
    assert await stock_of(market, roses['id']) == 0
    sold_out = await market.client.post(
        f'{P}/gifts/checkout',
        headers=market.customer,
        json={
            'idempotency_key': 'gift-key-0004',
            'delivery': delivery(),
            'items': [{'product_id': roses['id'], 'quantity': 1}],
        },
    )
    assert sold_out.json()['code'] == 'insufficient_stock'
    assert await pay(market, payment.json()['id'], 'failed') == 'failed'
    assert await stock_of(market, roses['id']) == 5
    late = await pay(market, payment.json()['id'])
    assert late == 'refunded_unpayable'


async def test_booking_and_gift_one_checkout(market):
    vendor_headers, _, (roses,) = await make_vendor(market)
    companion = await market.companion()
    booking = await accepted_booking(market, companion)
    payment = await market.client.post(
        f'{P}/bookings/{booking["id"]}/checkout',
        headers=market.customer,
        json={
            'idempotency_key': 'combo-key-001',
            'gifts': {'items': [{'product_id': roses['id'], 'quantity': 1}], 'note': 'Surprise'},
        },
    )
    assert payment.status_code == 200, payment.text
    body = payment.json()
    assert body['amount_minor'] == 110_000 + 50_000 + 20_000
    assert body['breakdown']['gifts_subtotal_minor'] == 50_000
    await pay(market, body['id'])
    orders = await market.client.get(f'{VME}/orders', headers=vendor_headers)
    order = orders.json()['items'][0]
    assert order['booking_id'] == booking['id']
    assert order['delivery_address'].startswith('Cafe Central')
    assert order['delivery_at'] == booking['starts_at']
    cancelled = await market.client.post(
        f'{B}/{booking["id"]}/cancel', headers=companion.headers, json={}
    )
    assert cancelled.json()['status'] == 'cancelled'
    state = await market.client.get(f'{P}/{body["id"]}', headers=market.customer)
    assert state.json()['status'] == 'refunded' and state.json()['refunded_minor'] == 180_000
    gift = await market.client.get(f'{G}/orders/{order["id"]}', headers=market.customer)
    assert gift.json()['status'] == 'cancelled'
    assert await stock_of(market, roses['id']) == 5
    metrics = await market.client.get(f'{API}/admin/analytics', headers=market.admin)
    assert metrics.json()['gift_attach_rate'] == 1.0
    assert checkout


async def test_home_gift_sections_and_admin_moderation(market):
    vendor_headers, _, (roses,) = await make_vendor(market)
    home = await market.client.get(f'{API}/discovery/home', headers=market.customer)
    flowers = next(s for s in home.json()['gift_sections'] if s['key'] == 'flowers')
    assert flowers['items'][0]['id'] == roses['id']
    hidden = await market.client.post(
        f'{API}/admin/products/{roses["id"]}/moderation',
        headers=market.admin,
        json={'action': 'hide', 'reason': 'Misleading photo'},
    )
    assert hidden.json()['hidden_by_admin'] is True
    assert (
        await market.client.get(f'{G}/products/{roses["id"]}', headers=market.customer)
    ).status_code == 404
    mine = await market.client.get(f'{VME}/products', headers=vendor_headers)
    assert mine.json()[0]['hidden_reason'] == 'Misleading photo'
    customer_as_vendor = await market.client.get(VME, headers=market.customer)
    assert customer_as_vendor.json()['code'] == 'vendor_role_required'
