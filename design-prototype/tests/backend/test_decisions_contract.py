"""Characterization + contract tests for the product decisions (availability containment, ID types, fees, minor units).
They exercise the REAL backend. They do not change it: a failing assertion here is a finding, not something to patch silently."""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from yondo_api.config import Settings
from yondo_api.payments.service import platform_fee

from tests.companions.test_bookings import booking_payload, setup_bookable_companion
from tests.companions.test_payments import FakePaymentProvider, accepted_booking

DISC = '/api/v1/discovery/companions'
# Fixture window (tests/companions/test_bookings.py): 2027-01-10 10:00–13:00 +05:00  ==  05:00Z–08:00Z
D = '2027-01-10T'


def z(h, m=0):
    return f'{D}{h:02d}:{m:02d}:00Z'


async def found(client, frm, until):
    r = await client.get(DISC, params={'available_from': frm, 'available_until': until})
    assert r.status_code == 200, r.text
    return len(r.json()['items']) == 1


# ---------- Decision 2: availability = FULL CONTAINMENT ----------
@pytest.mark.asyncio
@pytest.mark.parametrize(
    'frm,until,expected,why',
    [
        (z(5), z(8), True, 'exact match of the window'),
        (z(6), z(7), True, 'request fully inside the window'),
        (z(5), z(6), True, 'inside, shares window start'),
        (z(7), z(8), True, 'inside, shares window end'),
        (z(4), z(6), False, 'partial overlap: starts before window'),
        (z(7), z(9), False, 'partial overlap: ends after window'),
        (z(4), z(9), False, 'request CONTAINS the window (intersection would match, containment must not)'),
        (z(9), z(10), False, 'disjoint after window'),
        (z(3), z(4), False, 'disjoint before window'),
        (z(4), z(5), False, 'touches window start only (zero overlap)'),
        (z(8), z(9), False, 'touches window end only (zero overlap)'),
        ('2027-01-10T11:00:00+05:00', '2027-01-10T12:00:00+05:00', True, 'offset notation = same instants (06:00Z–07:00Z)'),
        ('2027-01-10T09:00:00+05:00', '2027-01-10T12:00:00+05:00', False, 'offset notation, starts 04:00Z (before window)'),
    ],
)
async def test_availability_filter_is_full_containment(prepared, frm, until, expected, why):
    client = prepared['client']
    await setup_bookable_companion(prepared)
    assert await found(client, frm, until) is expected, why


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'params,why',
    [
        ({'available_from': z(7), 'available_until': z(6)}, 'until before from'),
        ({'available_from': z(6), 'available_until': z(6)}, 'zero-length interval'),
        ({'available_from': z(6)}, 'only available_from'),
        ({'available_until': z(7)}, 'only available_until'),
        ({'available_from': '2027-01-10T06:00:00', 'available_until': '2027-01-10T07:00:00'}, 'naive timestamps (no timezone)'),
    ],
)
async def test_availability_filter_rejects_invalid_intervals(prepared, params, why):
    r = await prepared['client'].get(DISC, params=params)
    assert r.status_code == 422, why
    assert r.json()['code'] == 'invalid_discovery_filter', r.text


@pytest.mark.asyncio
async def test_booking_conflicts_stay_in_force_inside_the_window(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booked = await client.post('/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'], start=z(6)))
    assert booked.status_code == 201, booked.text  # pending booking 06:00–07:00Z
    assert not await found(client, z(6, 30), z(7, 30)), 'overlaps the pending booking'
    assert not await found(client, z(6), z(7)), 'identical to the booking'
    assert not await found(client, z(5), z(8)), 'window-wide request overlaps the booking'
    assert await found(client, z(7), z(7, 30)), 'adjacent after the booking is free'
    assert await found(client, z(5), z(6)), 'adjacent before the booking is free'


@pytest.mark.asyncio
async def test_general_availability_is_not_a_booked_slot_and_booking_also_needs_containment(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    for start, dur in [(z(7, 30), 60), (z(4, 30), 60), (z(9), 60)]:  # partly after / partly before / fully outside
        r = await client.post('/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'], start=start, duration=dur))
        assert r.status_code == 409, f'{start}: {r.text}'
        assert r.json()['code'] == 'availability_not_found'
    ok = await client.post('/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'], start=z(7), duration=60))
    assert ok.status_code == 201, 'booking ending exactly at window end must be accepted'


# ---------- Decision 5: user ids vs profile ids ----------
def report(reported, booking=None, **kw):
    body = {'reported_user_id': reported, 'category': 'harassment', 'description': 'test report'}
    if booking:
        body['booking_id'] = booking
    body.update(kw)
    return body


@pytest.mark.asyncio
async def test_report_target_must_be_a_user_id_not_a_profile_id(prepared):
    e, client = prepared, prepared['client']
    profile_id = e['profile']['id']
    assert profile_id != e['owner_id'], 'profile id and user id are different identifiers'
    r = await client.post('/api/v1/safety/reports', headers=e['customer'], json=report(profile_id))
    assert (r.status_code, r.json()['code']) == (404, 'reported_user_not_found'), r.text
    r = await client.put(f'/api/v1/safety/blocks/{profile_id}', headers=e['customer'])
    assert (r.status_code, r.json()['code']) == (404, 'user_not_found'), r.text


@pytest.mark.asyncio
async def test_report_reporter_identity_comes_from_the_session_not_the_body(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    b = (await client.post('/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id']))).json()
    forged = await client.post('/api/v1/safety/reports', headers=e['customer'], json=report(e['owner_id'], b['id'], reporter_id=e['other_id']))
    assert forged.status_code == 422, 'a client-supplied reporter identity must be rejected, not trusted'
    assert any(x['type'] == 'extra_forbidden' and x['loc'][-1] == 'reporter_id' for x in forged.json()['errors']), forged.text
    ok = await client.post('/api/v1/safety/reports', headers=e['customer'], json=report(e['owner_id'], b['id']))
    assert ok.status_code == 201, ok.text
    assert len((await client.get('/api/v1/safety/reports', headers=e['customer'])).json()) == 1
    assert (await client.get('/api/v1/safety/reports', headers=e['other'])).json() == [], 'attributed to the authenticated user only'


@pytest.mark.asyncio
async def test_report_and_block_error_matrix(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    b = (await client.post('/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id']))).json()
    cases = [
        ('unauthenticated', None, report(e['owner_id']), 401),
        ('self report', e['customer'], report(e['customer_id']) if 'customer_id' in e else None, 422),
        ('unknown user', e['customer'], report(str(uuid4())), 404),
        ('malformed id', e['customer'], report('not-a-uuid'), 422),
        ('unknown booking', e['customer'], report(e['owner_id'], str(uuid4())), 404),
        ('target is not the booking counterparty', e['customer'], report(e['other_id'], b['id']), 422),
        ('stranger reports on a booking they are not part of', e['other'], report(e['owner_id'], b['id']), None),
    ]
    for name, headers, body, expected in cases:
        if body is None:
            continue
        r = await client.post('/api/v1/safety/reports', headers=headers or {}, json=body)
        if expected is None:
            assert r.status_code in (403, 404), f'{name}: {r.status_code} {r.text}'
        else:
            assert r.status_code == expected, f'{name}: {r.status_code} {r.text}'
    assert (await client.put(f'/api/v1/safety/blocks/{e["owner_id"]}')).status_code == 401
    assert (await client.put(f'/api/v1/safety/blocks/{str(uuid4())}', headers=e['customer'])).status_code == 404


@pytest.mark.asyncio
async def test_public_api_does_not_expose_the_companion_user_id_to_customers(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    card = (await client.get(DISC)).json()['items'][0]
    assert 'user_id' not in card and e['owner_id'] not in str(card)
    b = (await client.post('/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id']))).json()
    assert e['owner_id'] not in str(b), 'BookingResponse carries profile_id and customer_id only: no mapping to the companion user'
    assert b['profile_id'] == card['id']


# ---------- Decision 1: fees are backend-owned; missing policy fails safely ----------
@pytest.mark.asyncio
async def test_payment_without_fee_policy_fails_safe_with_503(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    e['app'].state.payment_provider = FakePaymentProvider()
    assert e['app'].state.settings.platform_fee_bps is None, 'default must be unconfigured'
    r = await client.post(f'/api/v1/payments/bookings/{booking_id}', headers={**e['customer'], 'Idempotency-Key': 'no-fee-policy-1'})
    assert r.status_code == 503, r.text
    assert r.json()['code'].startswith('payment_'), r.text


@pytest.mark.asyncio
async def test_combined_checkout_needs_a_cart_and_never_charges_without_fee_policy(prepared):
    # Full preview/checkout with items (checkout_available false, nulls, 503 combined_checkout_unavailable) is covered by the backend's own
    # test_gifts_vendor_catalog_moderation_cart_and_disabled_checkout; here we pin the contract the UI relies on for the empty-cart path.
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    p = await client.get(f'/api/v1/integration/bookings/{booking_id}/preview', headers=e['customer'])
    assert (p.status_code, p.json()['code']) == (409, 'cart_empty'), p.text
    c = await client.post(f'/api/v1/integration/bookings/{booking_id}/checkout', headers=e['customer'])
    assert c.status_code in (409, 503) and c.json()['code'] in ('cart_empty', 'combined_checkout_unavailable'), c.text


@pytest.mark.asyncio
async def test_fee_is_computed_by_backend_in_integer_tiyin(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    e['app'].state.payment_provider = FakePaymentProvider()
    e['app'].state.settings = e['app'].state.settings.model_copy(update={'platform_fee_bps': 500})  # TEST FIXTURE value, not a business rule
    r = await client.post(f'/api/v1/payments/bookings/{booking_id}', headers={**e['customer'], 'Idempotency-Key': 'fee-integer-001'})
    assert r.status_code == 201, r.text
    p = r.json()
    assert (p['subtotal_minor'], p['platform_fee_minor'], p['amount_minor']) == (50000, 2500, 52500)
    assert all(isinstance(p[k], int) for k in ('subtotal_minor', 'platform_fee_minor', 'amount_minor'))


# ---------- Decision 4: integer tiyin, rounding, zero, invalid, large ----------
@pytest.mark.parametrize(
    'subtotal,bps,expected',
    [(0, 500, 0), (50000, 0, 0), (1, 500, 0), (9, 500, 0), (10, 500, 1), (11, 500, 1), (50000, 500, 2500), (50000, 10000, 50000),
     (999_999_999_999, 10000, 999_999_999_999), (2**62, 10000, 2**62), (2**62, 1, (2**62 + 5000) // 10000), (123_456_789, 333, (123_456_789 * 333 + 5000) // 10000)],
)
def test_platform_fee_integer_round_half_up(subtotal, bps, expected):
    out = platform_fee(subtotal, bps)
    assert out == expected and isinstance(out, int)


@pytest.mark.parametrize('bps,ok', [(None, True), (0, True), (10000, True), (-1, False), (10001, False)])
def test_fee_bps_setting_validation(bps, ok):
    if ok:
        assert Settings(platform_fee_bps=bps).platform_fee_bps == bps
    else:
        with pytest.raises(ValidationError):
            Settings(platform_fee_bps=bps)


@pytest.mark.asyncio
@pytest.mark.parametrize('price,allowed', [(0, {201}), (1, {201}), (-1, {422}), (100.5, {422}), (2**63, {422}), (2**63 - 1, {201, 422})])
async def test_service_price_minor_validation(prepared, price, allowed):
    e, client = prepared, prepared['client']
    r = await client.post('/api/v1/companions/me/services', headers=e['owner'], json={'service_code': 'coffee', 'description': 'x', 'price_minor': price, 'currency': 'UZS', 'unit_minutes': 60})
    assert r.status_code in allowed and r.status_code < 500, f'price_minor={price!r} → {r.status_code} {r.text[:160]}'
