from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from yondo_api.bookings.expiry import expire_stale_bookings
from yondo_api.bookings.models import Booking, BookingStatus

from .test_bookings import booking_payload, setup_bookable_companion


async def _move_to_past(e, booking_id):
    async with e['app'].state.db_session_factory() as session:
        item = await session.get(Booking, UUID(booking_id))
        now = datetime.now(UTC)
        item.starts_at, item.ends_at = now - timedelta(hours=2), now - timedelta(hours=1)
        await session.commit()


async def _status(e, booking_id):
    async with e['app'].state.db_session_factory() as session:
        return (await session.get(Booking, UUID(booking_id))).status


@pytest.mark.asyncio
async def test_overdue_bookings_expire_release_the_slot_and_cannot_be_accepted_or_paid(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    first = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert first.status_code == 201, first.text
    # Same slot is reserved while the first booking is pending.
    clash = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert clash.json()['code'] == 'booking_time_unavailable'

    # Pending past its start: accept is refused and the booking becomes expired.
    await _move_to_past(e, first.json()['id'])
    accept_url = f'/api/v1/bookings/{first.json()["id"]}/accept'
    accept = await client.post(accept_url, headers=e['owner'])
    assert accept.status_code == 409
    assert accept.json()['code'] == 'booking_expired'
    assert await _status(e, first.json()['id']) == BookingStatus.EXPIRED

    # Accepted but unpaid past its start: payment is refused (never implies a payment).
    second = await client.post(
        '/api/v1/bookings',
        headers=e['customer'],
        json=booking_payload(service['id'], start='2027-01-10T07:00:00Z'),
    )
    assert second.status_code == 201, second.text
    accepted = await client.post(
        f'/api/v1/bookings/{second.json()["id"]}/accept', headers=e['owner']
    )
    assert accepted.status_code == 200, accepted.text
    await _move_to_past(e, second.json()['id'])
    pay = await client.post(
        f'/api/v1/payments/bookings/{second.json()["id"]}',
        headers={**e['customer'], 'Idempotency-Key': 'expired-booking-1'},
    )
    assert pay.status_code == 409, pay.text
    assert pay.json()['code'] == 'booking_expired'

    # The periodic sweep expires the rest; a future booking is untouched.
    third = await client.post(
        '/api/v1/bookings',
        headers=e['customer'],
        json=booking_payload(service['id'], start='2027-01-10T06:00:00Z'),
    )
    assert third.status_code == 201, third.text
    stale = await client.post(
        '/api/v1/bookings',
        headers=e['customer'],
        json=booking_payload(service['id'], start='2027-01-10T05:00:00Z'),
    )
    await _move_to_past(e, stale.json()['id'])
    async with e['app'].state.db_session_factory() as session:
        assert await expire_stale_bookings(session) == 1
    assert await _status(e, stale.json()['id']) == BookingStatus.EXPIRED
    assert await _status(e, third.json()['id']) == BookingStatus.PENDING

    # An expired booking no longer reserves its slot (also enforced by the PostgreSQL exclusion).
    async with e['app'].state.db_session_factory() as session:
        item = await session.get(Booking, UUID(third.json()['id']))
        item.status = BookingStatus.EXPIRED
        await session.commit()
    rebook = await client.post(
        '/api/v1/bookings',
        headers=e['customer'],
        json=booking_payload(service['id'], start='2027-01-10T06:00:00Z'),
    )
    assert rebook.status_code == 201, rebook.text


@pytest.mark.asyncio
async def test_block_the_other_participant_via_booking(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    booking_id = booking.json()['id']
    block_url = f'/api/v1/safety/bookings/{booking_id}/block'
    outsider = await client.put(block_url, headers=e['other'])
    assert outsider.status_code in {403, 404}
    blocked = await client.put(block_url, headers=e['customer'])
    assert blocked.status_code == 204, blocked.text
    mine = await client.get('/api/v1/safety/blocked-bookings', headers=e['customer'])
    assert mine.json() == [booking_id]
    theirs = await client.get('/api/v1/safety/blocked-bookings', headers=e['owner'])
    assert theirs.json() == []
    assert (await client.get('/api/v1/safety/blocks', headers=e['customer'])).json() == [
        e['owner_id']
    ]
    again = await client.post(
        '/api/v1/bookings',
        headers=e['customer'],
        json=booking_payload(service['id'], start='2027-01-10T07:00:00Z'),
    )
    assert again.json()['code'] == 'booking_blocked'
    unblocked = await client.delete(
        f'/api/v1/safety/bookings/{booking_id}/block', headers=e['customer']
    )
    assert unblocked.status_code == 204
    assert (await client.get('/api/v1/safety/blocked-bookings', headers=e['customer'])).json() == []
