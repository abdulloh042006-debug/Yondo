"""Drives the DEMO payment flow against a running harness (server.py with YONDO_DEMO_PUBLIC_URL=https://...).

Usage: python demo_payment_check.py <port>
Checks (exit code 1 on any failure): checkout link -> DEMO page -> succeed => booking confirmed (twice = idempotent);
second booking: fail => payment failed, booking stays accepted. No money moves; the provider is a stand-in.
"""

import re
import sys
from datetime import datetime, timedelta

import httpx

PORT = sys.argv[1] if len(sys.argv) > 1 else '8000'
ORIGIN = f'http://127.0.0.1:{PORT}'
API = f'{ORIGIN}/api/v1'
failures = []


def check(name, ok, detail=''):
    print(('PASS  ' if ok else 'FAIL  ') + name + (f'  [{detail}]' if detail and not ok else ''))
    if not ok:
        failures.append(name)


def login(c, phone):
    issued = c.post(f'{API}/auth/otp/request', json={'phone_number': phone}).json()
    tok = c.post(f'{API}/auth/otp/verify', json={'phone_number': phone, 'code': issued['development_otp'], 'accept_legal': True}).json()
    return {'Authorization': f'Bearer {tok["access_token"]}'}


def items(payload):
    return payload['items'] if isinstance(payload, dict) and 'items' in payload else payload


def local(url):
    return re.sub(r'^https://[^/]+', ORIGIN, url)


with httpx.Client(timeout=60) as c:
    customer, companion = login(c, '+998901110003'), login(c, '+998901110011')
    mine = items(c.get(f'{API}/bookings?limit=50', headers=customer).json())
    seeded = next(b for b in mine if b['meeting_place'].startswith('DEMO: Magic City'))
    madina = next(i for i in items(c.get(f'{API}/discovery/companions').json()) if i['display_name'] == 'DEMO Madina')
    service = next(s for s in c.get(f'{API}/discovery/companions/{madina["id"]}').json()['services'] if s['service_code'] == 'coffee')
    base = datetime.fromisoformat(seeded['starts_at'].replace('Z', '+00:00'))

    def new_paid_booking(hours, key):
        start = (base + timedelta(hours=hours)).isoformat().replace('+00:00', 'Z')
        made = c.post(f'{API}/bookings', headers=customer, json={
            'service_id': service['id'], 'starts_at': start, 'duration_minutes': 60,
            'meeting_place': 'DEMO: test to‘lov', 'timezone': 'Asia/Tashkent'})
        booking = made.json()
        c.post(f'{API}/bookings/{booking["id"]}/accept', headers=companion)
        pay = c.post(f'{API}/payments/bookings/{booking["id"]}', headers={**customer, 'Idempotency-Key': key})
        return booking['id'], pay

    booking_id, pay = new_paid_booking(2, 'demo-key-success-0001')
    check('checkout created (201) with an https DEMO link', pay.status_code == 201 and pay.json()['checkout_url'].startswith('https://'), pay.text[:160])
    link = local(pay.json()['checkout_url'])
    page = c.get(link)
    check('DEMO page says no money moves', page.status_code == 200 and 'Hech qanday pul yechilmaydi' in page.text)
    state = c.get(f'{API}/bookings/{booking_id}', headers=customer).json()['status']
    check('before paying the booking is still accepted', state == 'accepted', state)
    done = c.post(f'{link}/succeed', follow_redirects=False)
    check('succeed redirects back to the booking', done.status_code == 303 and done.headers['location'] == f'/bookings/{booking_id}', f'{done.status_code} {done.headers.get("location")}')
    state = c.get(f'{API}/bookings/{booking_id}', headers=customer).json()['status']
    check('booking is confirmed by the real webhook path', state == 'confirmed', state)
    again = c.post(f'{link}/succeed', follow_redirects=False)
    state = c.get(f'{API}/bookings/{booking_id}', headers=customer).json()['status']
    check('pressing succeed twice is idempotent', again.status_code == 303 and state == 'confirmed', f'{again.status_code} {state}')
    statuses = [p['status'] for p in c.get(f'{API}/payments/bookings/{booking_id}', headers=customer).json()]
    check('one payment, succeeded', statuses == ['succeeded'], str(statuses))
    forged = c.post(f'{API}/payments/webhook', content=b'{"event_id":"x","provider_reference":"demo-x","status":"succeeded"}',
                    headers={'x-demo-signature': 'bad', 'content-type': 'application/json'})
    check('an unsigned webhook is refused (401)', forged.status_code == 401, str(forged.status_code))

    booking2, pay2 = new_paid_booking(4, 'demo-key-failure-0001')
    link2 = local(pay2.json()['checkout_url'])
    failed = c.post(f'{link2}/fail', follow_redirects=False)
    state = c.get(f'{API}/bookings/{booking2}', headers=customer).json()['status']
    statuses = [p['status'] for p in c.get(f'{API}/payments/bookings/{booking2}', headers=customer).json()]
    check('fail: payment failed, booking stays accepted', failed.status_code == 303 and state == 'accepted' and statuses == ['failed'], f'{state} {statuses}')
    check('unknown reference is 404', c.get(f'{ORIGIN}/demo-pay/demo-nope').status_code == 404)

print('\nDEMO PAYMENT: ' + ('FAILED ' + str(failures) if failures else 'all checks passed'))
sys.exit(1 if failures else 0)
