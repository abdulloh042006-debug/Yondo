from uuid import UUID

import pytest

from yondo_api.companions.integrations import IdentityStatus
from yondo_api.models.user import User

from .conftest import approve


async def setup_bookable_companion(e):
    client = e['client']
    service = await client.post(
        '/api/v1/companions/me/services',
        headers=e['owner'],
        json={
            'service_code': 'coffee',
            'description': 'Coffee companion',
            'price_minor': 50000,
            'currency': 'UZS',
            'unit_minutes': 60,
        },
    )
    assert service.status_code == 201
    availability = await client.post(
        '/api/v1/companions/me/availability',
        headers=e['owner'],
        json={
            'starts_at': '2027-01-10T10:00:00+05:00',
            'ends_at': '2027-01-10T13:00:00+05:00',
            'timezone': 'Asia/Tashkent',
        },
    )
    assert availability.status_code == 201
    async with e['app'].state.db_session_factory() as session:
        user = await session.get(User, UUID(e['owner_id']))
        user.age, user.gender, user.city = 22, 'woman', 'Tashkent'
        await session.commit()
    await approve(e)
    e['identity'].status = IdentityStatus.VERIFIED
    active = await client.post('/api/v1/companions/me/activate', headers=e['owner'])
    assert active.status_code == 200
    return service.json()


def booking_payload(service_id, start='2027-01-10T06:00:00Z', duration=60):
    return {
        'service_id': service_id,
        'starts_at': start,
        'duration_minutes': duration,
        'timezone': 'Asia/Tashkent',
        'meeting_place': 'Central public cafe',
    }


@pytest.mark.asyncio
async def test_booking_contract_and_companion_acceptance(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    created = await client.post(
        '/api/v1/bookings',
        headers=e['customer'],
        json=booking_payload(service['id'], duration=120),
    )
    assert created.status_code == 201, created.text
    contract = created.json()
    assert contract['status'] == 'pending'
    assert contract['duration_minutes'] == 120
    assert contract['price_minor'] == 100000
    assert contract['currency'] == 'UZS'
    assert contract['customer_contract_accepted_at']
    assert contract['companion_contract_accepted_at'] is None

    accepted = await client.post(f'/api/v1/bookings/{contract["id"]}/accept', headers=e['owner'])
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['status'] == 'accepted'
    assert accepted.json()['companion_contract_accepted_at']
    assert (await client.get('/api/v1/bookings', headers=e['customer'])).json()[0][
        'id'
    ] == contract['id']
    outsider = await client.get(f'/api/v1/bookings/{contract["id"]}', headers=e['other'])
    assert outsider.status_code == 404


@pytest.mark.asyncio
async def test_booking_validates_availability_overlap_and_pricing_units(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    url = '/api/v1/bookings'
    headers = e['customer']
    outside = await client.post(
        url, headers=headers, json=booking_payload(service['id'], '2027-01-10T08:00:00Z')
    )
    assert outside.status_code == 409
    fractional = await client.post(
        url, headers=headers, json=booking_payload(service['id'], duration=90)
    )
    assert fractional.status_code == 422
    first = await client.post(url, headers=headers, json=booking_payload(service['id']))
    assert first.status_code == 201, first.text
    adjacent = await client.post(
        url,
        headers=headers,
        json=booking_payload(service['id'], start='2027-01-10T07:00:00Z'),
    )
    assert adjacent.status_code == 201, adjacent.text
    overlap = await client.post(
        url,
        headers=headers,
        json=booking_payload(service['id'], start='2027-01-10T06:30:00Z'),
    )
    assert overlap.status_code == 409


@pytest.mark.asyncio
async def test_booking_decline_cancel_and_role_checks(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    created = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    booking_id = created.json()['id']
    denied = await client.post(f'/api/v1/bookings/{booking_id}/accept', headers=e['customer'])
    assert denied.status_code == 403
    declined = await client.post(
        f'/api/v1/bookings/{booking_id}/decline', headers=e['owner'], json={}
    )
    assert declined.status_code == 200
    assert declined.json()['status'] == 'cancelled'

    second = await client.post(
        '/api/v1/bookings',
        headers=e['customer'],
        json=booking_payload(service['id'], start='2027-01-10T07:00:00Z'),
    )
    cancelled = await client.post(
        f'/api/v1/bookings/{second.json()["id"]}/cancel', headers=e['customer'], json={}
    )
    assert cancelled.status_code == 200
    assert cancelled.json()['status'] == 'cancelled'
    duplicate = await client.post(
        f'/api/v1/bookings/{second.json()["id"]}/cancel', headers=e['customer'], json={}
    )
    assert duplicate.status_code == 409
