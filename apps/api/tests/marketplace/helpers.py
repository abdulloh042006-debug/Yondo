from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import update
from support import API

from yondo_api.bookings.models import Booking

from .conftest import hour_from_now

B = f'{API}/bookings'


def booking_payload(companion, *, start_hours=25, duration=60, service='coffee', **extra):
    return {
        'profile_id': companion.profile_id,
        'service_id': companion.services[service]['id'],
        'starts_at': hour_from_now(start_hours).isoformat(),
        'duration_minutes': duration,
        'meeting_place': {
            'name': 'Cafe Central',
            'address': 'Amir Temur 1',
            'latitude': 41.31,
            'longitude': 69.28,
        },
        'accept_contract': True,
        **extra,
    }


async def request_booking(market, companion, headers=None, **kwargs):
    response = await market.client.post(
        B, headers=headers or market.customer, json=booking_payload(companion, **kwargs)
    )
    assert response.status_code == 201, response.text
    return response.json()


async def accepted_booking(market, companion, headers=None, **kwargs):
    booking = await request_booking(market, companion, headers, **kwargs)
    accepted = await market.client.post(f'{B}/{booking["id"]}/accept', headers=companion.headers)
    assert accepted.status_code == 200, accepted.text
    return accepted.json()


async def shift_booking(market, booking_id, **values):
    async with market.app.state.db_session_factory() as session:
        await session.execute(
            update(Booking).where(Booking.id == UUID(booking_id)).values(**values)
        )
        await session.commit()


async def move_to_past(market, booking_id, hours_ago: float):
    """Move a booking so that it started ``hours_ago`` hours before now."""
    from yondo_api.core.time import utc_now

    start = utc_now() - timedelta(hours=hours_ago)
    async with market.app.state.db_session_factory() as session:
        booking = await session.get(Booking, UUID(booking_id))
        duration = booking.ends_at - booking.starts_at
        booking.starts_at = start
        booking.ends_at = start + duration
        await session.commit()


P = f'{API}/payments'


async def checkout(market, booking_id, key='checkout-key-1', headers=None):
    response = await market.client.post(
        f'{P}/bookings/{booking_id}/checkout',
        headers=headers or market.customer,
        json={'idempotency_key': key},
    )
    return response


async def pay(market, payment_id, result='succeeded'):
    response = await market.client.post(
        f'{P}/sandbox/{payment_id}/simulate', json={'result': result}
    )
    assert response.status_code == 200, response.text
    return response.json()['outcome']


async def confirmed_booking(market, companion, **kwargs):
    booking = await accepted_booking(market, companion, **kwargs)
    payment = await checkout(market, booking['id'], key=f'key-{booking["id"]}')
    assert payment.status_code == 200, payment.text
    assert await pay(market, payment.json()['id']) == 'captured'
    return booking, payment.json()
