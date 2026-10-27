"""DEMO payment provider: a stand-in for CLICK/Payme until the owner supplies real merchant keys.

It never moves money. `create_checkout` returns a link to a DEMO page served by this process; pressing a button
there sends a signed event to the REAL `/payments/webhook` route (idempotency, locking, booking confirmation and
notifications are the production code). Only the demo harness (`server.py`) wires this in; the API itself keeps
`UnconfiguredPaymentProvider` unless a provider is injected.

Enabled by `YONDO_DEMO_PUBLIC_URL` (or Render's `RENDER_EXTERNAL_URL`): must be https because the API refuses any
other checkout URL. The platform fee used with it is the labelled DEMO value 0 (the real policy is the owner's).
"""

import hashlib
import hmac
import json
import secrets
from html import escape
from uuid import uuid4

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy import select

from yondo_api.payments.models import Payment
from yondo_api.payments.provider import CheckoutSession, PaymentEvent

OUTCOMES = {'succeed': 'succeeded', 'fail': 'failed'}


class DemoPaymentProvider:
    def __init__(self, public_url: str) -> None:
        if not public_url.startswith('https://'):
            raise ValueError('The demo payment page URL must be https (the API refuses other checkout URLs)')
        self.public_url = public_url.rstrip('/')
        self._key = secrets.token_bytes(32)  # only this process can sign an event

    def sign(self, body: bytes) -> str:
        return hmac.new(self._key, body, hashlib.sha256).hexdigest()

    async def create_checkout(self, *, idempotency_key: str, amount_minor: int, currency: str, description: str) -> CheckoutSession:
        reference = f'demo-{uuid4().hex}'
        return CheckoutSession(provider_reference=reference, checkout_url=f'{self.public_url}/demo-pay/{reference}')

    async def verify_event(self, body: bytes, headers: dict[str, str]) -> PaymentEvent:
        if not hmac.compare_digest(self.sign(body), headers.get('x-demo-signature', '')):
            raise ValueError('bad demo signature')
        data = json.loads(body)
        return PaymentEvent(event_id=data['event_id'], provider_reference=data['provider_reference'], status=data['status'])


def _som(amount_minor: int) -> str:
    whole, minor = divmod(amount_minor, 100)
    text = f'{whole:,}'.replace(',', ' ')
    return f'{text}.{minor:02d}' if minor else text


PAGE = """<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>DEMO to‘lov</title><style>body{{font-family:system-ui,sans-serif;background:#f5f2ec;color:#111;margin:0;display:grid;place-items:center;min-height:100vh}}
main{{background:#fff;border:2px solid #111;border-radius:16px;padding:28px;max-width:420px;margin:16px}}h1{{margin:0 0 8px;font-size:22px}}
.demo{{background:#e8501a;color:#fff;border-radius:8px;padding:4px 10px;font-weight:700;font-size:13px}}
button{{font:inherit;font-weight:700;padding:12px 18px;border-radius:12px;border:2px solid #111;cursor:pointer;margin:6px 6px 0 0}}
.ok{{background:#111;color:#fff}}.no{{background:#fff;color:#111}}</style></head><body><main>
<p><span class="demo">DEMO</span></p><h1>Sinov to‘lov sahifasi</h1>
<p>Bu haqiqiy to‘lov emas. <b>Hech qanday pul yechilmaydi.</b> Haqiqiy to‘lov provayderi (Click yoki boshqasi) keyinroq ulanadi.</p>
<p>Summa: <b>{amount} {currency}</b><br>Holat: <b>{status}</b></p>
<form method="post" action="/demo-pay/{reference}/succeed"><button class="ok">To‘lovni tasdiqlash (DEMO)</button></form>
<form method="post" action="/demo-pay/{reference}/fail"><button class="no">Rad etish (DEMO)</button></form>
</main></body></html>"""


def install_demo_payment_routes(app: FastAPI, provider: DemoPaymentProvider) -> None:
    async def load(reference: str) -> Payment | None:
        async with app.state.db_session_factory() as session:
            return await session.scalar(select(Payment).where(Payment.provider_reference == reference))

    @app.get('/demo-pay/{reference}', response_class=HTMLResponse, include_in_schema=False)
    async def demo_pay_page(reference: str):
        payment = await load(reference)
        if payment is None:
            return PlainTextResponse('Topilmadi', status_code=404)
        return HTMLResponse(PAGE.format(
            amount=escape(_som(payment.amount_minor)), currency=escape(payment.currency),
            status=escape(str(getattr(payment.status, 'value', payment.status))), reference=escape(reference)))

    @app.post('/demo-pay/{reference}/{outcome}', include_in_schema=False)
    async def demo_pay_decide(reference: str, outcome: str):
        payment = await load(reference)
        if payment is None or outcome not in OUTCOMES:
            return PlainTextResponse('Topilmadi', status_code=404)
        body = json.dumps({'event_id': f'demo-evt-{uuid4().hex}', 'provider_reference': reference,
                           'status': OUTCOMES[outcome]}).encode()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://demo') as client:
            sent = await client.post(f'{app.state.settings.api_v1_prefix}/payments/webhook', content=body,
                                     headers={'x-demo-signature': provider.sign(body), 'content-type': 'application/json'})
        if sent.status_code != 204:
            return PlainTextResponse(f'To‘lov hodisasi qabul qilinmadi ({sent.status_code})', status_code=502)
        return RedirectResponse(f'/bookings/{payment.booking_id}', status_code=303)
