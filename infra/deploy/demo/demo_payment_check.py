"""DEMO payment flow checks, shared by the pytest suite (in-process) and the command line (a running server).

Usage against a running server: python demo_payment_check.py <port | https://origin>
It can be run again and again: every run books the first free slots and uses fresh Idempotency-Keys.
No money moves; the provider is a stand-in. Needs a server started with the DEMO payment provider.
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

PREFIX = '/api/v1'


def _items(payload):
    return payload['items'] if isinstance(payload, dict) and 'items' in payload else payload


async def _login(client, phone):
    issued = (await client.post(f'{PREFIX}/auth/otp/request', json={'phone_number': phone})).json()
    token = (await client.post(f'{PREFIX}/auth/otp/verify', json={
        'phone_number': phone, 'code': issued['development_otp'], 'accept_legal': True})).json()
    return {'Authorization': f'Bearer {token["access_token"]}'}


def _candidate_starts(seeded_start):
    """Hours inside the seed window and inside the topped-up 10:00-22:00 (Tashkent) windows of the next days."""
    out = [seeded_start + timedelta(hours=h) for h in (2, 3, 4, 5)] if seeded_start else []
    midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    for day in range(1, 15):
        out += [midnight + timedelta(days=day, hours=h) for h in range(6, 16)]
    return iter(out)


async def run_checks(client, companion_phone='+998901110011', customer_phone='+998901110003', spa=False):
    """Run the checks with an httpx client (ASGI or real); returns (failures, passed_names)."""
    failures, passed = [], []

    def check(name, ok, detail=''):
        print(('PASS  ' if ok else 'FAIL  ') + name + (f'  [{detail}]' if detail and not ok else ''))
        (passed if ok else failures).append(name)

    customer, companion = await _login(client, customer_phone), await _login(client, companion_phone)
    mine = _items((await client.get(f'{PREFIX}/bookings?limit=50', headers=customer)).json())
    seeded = next((b for b in mine if b['meeting_place'].startswith('DEMO: Magic City')), None)
    madina = next(i for i in _items((await client.get(f'{PREFIX}/discovery/companions')).json()) if i['display_name'] == 'DEMO Madina')
    service = next(s for s in (await client.get(f'{PREFIX}/discovery/companions/{madina["id"]}')).json()['services'] if s['service_code'] == 'coffee')
    slots = _candidate_starts(datetime.fromisoformat(seeded['starts_at'].replace('Z', '+00:00')) if seeded else None)

    async def book_and_accept():
        for start in slots:
            made = await client.post(f'{PREFIX}/bookings', headers=customer, json={
                'service_id': service['id'], 'starts_at': start.isoformat().replace('+00:00', 'Z'), 'duration_minutes': 60,
                'meeting_place': 'DEMO: test to‘lov', 'timezone': 'Asia/Tashkent'})
            if made.status_code == 201:
                booking_id = made.json()['id']
                await client.post(f'{PREFIX}/bookings/{booking_id}/accept', headers=companion)
                return booking_id
        raise RuntimeError('no free slot left for the check (the DEMO companion is fully booked)')

    async def booking_status(booking_id):
        return (await client.get(f'{PREFIX}/bookings/{booking_id}', headers=customer)).json()['status']

    async def payments(booking_id):
        return [p['status'] for p in (await client.get(f'{PREFIX}/payments/bookings/{booking_id}', headers=customer)).json()]

    booking_id = await book_and_accept()
    pay = await client.post(f'{PREFIX}/payments/bookings/{booking_id}', headers={**customer, 'Idempotency-Key': f'demo-{uuid4().hex}'})
    link = pay.json().get('checkout_url', '')
    ref = link.rsplit('/', 1)[-1]
    check('checkout created (201) with an https link to the web app DEMO page', pay.status_code == 201 and link.startswith('https://') and '/demo-pay/demo-' in link, pay.text[:160])
    if spa:
        page = await client.get(f'/demo-pay/{ref}')
        check('the DEMO page route is served by the web app', page.status_code == 200 and 'text/html' in page.headers['content-type'])
    shown = await client.get(f'{PREFIX}/demo-pay/{ref}', headers=customer)
    check('the paying customer sees amount and status pending', shown.status_code == 200 and shown.json()['status'] == 'pending' and shown.json()['booking_id'] == booking_id, shown.text[:160])
    check('anonymous visitors are refused (401)', (await client.get(f'{PREFIX}/demo-pay/{ref}')).status_code == 401)
    check('the companion cannot see the payment page (404)', (await client.get(f'{PREFIX}/demo-pay/{ref}', headers=companion)).status_code == 404)
    stolen = await client.post(f'{PREFIX}/demo-pay/{ref}/succeed', headers=companion)
    check('the companion cannot confirm the payment (404, booking stays accepted)', stolen.status_code == 404 and await booking_status(booking_id) == 'accepted')
    check('an unknown outcome is refused (422)', (await client.post(f'{PREFIX}/demo-pay/{ref}/refund', headers=customer)).status_code == 422)
    done = await client.post(f'{PREFIX}/demo-pay/{ref}/succeed', headers=customer)
    check('the customer confirms: payment succeeded', done.status_code == 200 and done.json()['status'] == 'succeeded', done.text[:160])
    check('booking is confirmed by the real webhook path', await booking_status(booking_id) == 'confirmed')
    again = await client.post(f'{PREFIX}/demo-pay/{ref}/succeed', headers=customer)
    check('pressing confirm twice is idempotent', again.status_code == 200 and await booking_status(booking_id) == 'confirmed')
    check('one payment, succeeded', await payments(booking_id) == ['succeeded'], str(await payments(booking_id)))
    forged = await client.post(f'{PREFIX}/payments/webhook', content=b'{"event_id":"x","provider_reference":"demo-x","status":"succeeded"}',
                               headers={'x-demo-signature': 'bad', 'content-type': 'application/json'})
    check('an unsigned webhook is refused (401)', forged.status_code == 401, str(forged.status_code))

    booking2 = await book_and_accept()
    pay2 = await client.post(f'{PREFIX}/payments/bookings/{booking2}', headers={**customer, 'Idempotency-Key': f'demo-{uuid4().hex}'})
    ref2 = pay2.json()['checkout_url'].rsplit('/', 1)[-1]
    failed = await client.post(f'{PREFIX}/demo-pay/{ref2}/fail', headers=customer)
    check('reject: payment failed, booking stays accepted',
          failed.status_code == 200 and await booking_status(booking2) == 'accepted' and await payments(booking2) == ['failed'])
    check('unknown reference is 404', (await client.get(f'{PREFIX}/demo-pay/demo-nope', headers=customer)).status_code == 404)
    return failures, passed


async def _main(target):
    origin = target.rstrip('/') if target.startswith('http') else f'http://127.0.0.1:{target}'
    async with httpx.AsyncClient(base_url=origin, timeout=90, follow_redirects=False) as client:
        failures, _ = await run_checks(client, spa=True)
    print('\nDEMO PAYMENT: ' + ('FAILED ' + str(failures) if failures else 'all checks passed'))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(_main(sys.argv[1] if len(sys.argv) > 1 else '8000')))
