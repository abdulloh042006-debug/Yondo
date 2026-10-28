"""Duplicate / spam booking protection: slot clashes, request rate, open-request caps."""

import pytest

from yondo_api.api.errors import ApplicationError

from .cancellation_helpers import API, book, cancel, configure, user_id
from .test_bookings import booking_payload, setup_bookable_companion


@pytest.mark.asyncio
async def test_identical_and_overlapping_slots_are_rejected_for_any_customer(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    await book(e, service, '2027-01-10T06:00:00Z', accept=False)
    for start in ('2027-01-10T06:00:00Z', '2027-01-10T06:30:00Z', '2027-01-10T05:30:00Z'):
        again = await client.post(
            f'{API}/bookings', headers=e['customer'], json=booking_payload(service['id'], start))
        assert again.status_code == 409 and again.json()['code'] == 'booking_time_unavailable'
    # After the first request is cancelled the slot is free again (no stale duplicate lock-out).
    first = (await client.get(f'{API}/bookings', headers=e['customer'])).json()[0]['id']
    await cancel(e, 'customer', first)
    await book(e, service, '2027-01-10T06:00:00Z', accept=False)


@pytest.mark.asyncio
async def test_booking_request_rate_limit_is_configurable(prepared):
    e = prepared
    configure(e, booking_requests_per_hour_limit=2)
    service = await setup_bookable_companion(e)
    for start in ('2027-01-10T05:00:00Z', '2027-01-10T06:00:00Z'):
        booking_id = await book(e, service, start, accept=False)
        await cancel(e, 'customer', booking_id)  # cancelling does not reset the counter
    limited = await book(e, service, '2027-01-10T07:00:00Z', expect=429)
    assert limited.json()['code'] == 'booking_rate_limited'
    configure(e, booking_requests_per_hour_limit=0)  # 0 = off
    await book(e, service, '2027-01-10T07:00:00Z', accept=False)


@pytest.mark.asyncio
async def test_rate_limiter_is_injected_like_the_otp_limiter(prepared):
    e = prepared
    seen = []

    class Deny:
        async def check(self, session, user_id, *, limit_per_hour):
            seen.append((str(user_id), limit_per_hour))
            raise ApplicationError('booking_rate_limited', 'Denied by the test limiter', 429)

    service = await setup_bookable_companion(e)
    e['app'].state.booking_rate_limiter = Deny()
    response = await book(e, service, expect=429)
    assert response.json()['code'] == 'booking_rate_limited'
    assert seen == [(await user_id(e, e['customer']), 20)]  # the placeholder default


@pytest.mark.asyncio
async def test_open_request_caps_stop_spamming_one_companion_or_many(prepared):
    e = prepared
    service = await setup_bookable_companion(e)
    configure(e, booking_open_requests_per_companion_limit=2)
    first = await book(e, service, '2027-01-10T05:00:00Z', accept=False)
    await book(e, service, '2027-01-10T06:00:00Z', accept=False)
    capped = await book(e, service, '2027-01-10T07:00:00Z', expect=409)
    assert capped.json()['code'] == 'booking_open_limit_per_companion_reached'
    await cancel(e, 'customer', first)  # answering/cancelling frees a place
    await book(e, service, '2027-01-10T07:00:00Z', accept=False)
    configure(e, booking_open_requests_limit=2)
    overall = await book(e, service, '2027-01-10T05:00:00Z', expect=409)
    assert overall.json()['code'] == 'booking_open_limit_reached'
    configure(e, booking_open_requests_limit=0, booking_open_requests_per_companion_limit=0)
    await book(e, service, '2027-01-10T05:00:00Z', accept=False)


@pytest.mark.asyncio
async def test_confirmation_steps_are_unchanged(prepared):
    """Nothing new bypasses the existing flow: a request is pending until the companion accepts."""
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await book(e, service, accept=False)
    paid_too_early = await client.post(
        f'{API}/payments/bookings/{booking_id}',
        headers={**e['customer'], 'Idempotency-Key': 'abuse-guard-1'})
    assert paid_too_early.status_code == 409
    own = await client.post(f'{API}/bookings/{booking_id}/accept', headers=e['customer'])
    assert own.status_code == 403 and own.json()['code'] == 'companion_role_required'
