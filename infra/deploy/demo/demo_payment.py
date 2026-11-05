"""DEMO payment provider: a stand-in for CLICK/Payme until the owner supplies real merchant keys.

It never moves money. `create_checkout` returns a link to the web app's own DEMO page (`/demo-pay/<reference>`, a
React route with i18n); its two buttons call the endpoints below, which accept only the PAYING customer's session and
then send a signed event to the REAL `/payments/webhook` route (idempotency, locking, booking confirmation and
notifications are the production code). Only the demo harness (`demo_app.py`) wires this in; the API itself keeps
`UnconfiguredPaymentProvider` unless a provider is injected.

Enabled by `YONDO_DEMO_PUBLIC_URL` (or Render's `RENDER_EXTERNAL_URL`): must be https because the API refuses any
other checkout URL. The platform fee used with it is the labelled DEMO value 0 (the real policy is the owner's).
"""

import hashlib
import hmac
import json
import secrets
from uuid import uuid4

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Principal
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


def install_demo_payment_routes(app: FastAPI, provider: DemoPaymentProvider) -> None:
    prefix = app.state.settings.api_v1_prefix

    async def own_payment(reference: str, principal: Principal) -> Payment:
        """The payment behind `reference`, only for the customer who has to pay it (anyone else sees a 404)."""
        async with app.state.db_session_factory() as session:
            payment = await session.scalar(select(Payment).where(Payment.provider_reference == reference))
        if payment is None or payment.customer_id != principal.user.id:
            raise ApplicationError('payment_not_found', 'Payment not found', 404)
        return payment

    def view(payment: Payment, status: str | None = None) -> dict:
        return {'booking_id': str(payment.booking_id), 'amount_minor': payment.amount_minor,
                'currency': payment.currency, 'status': status or str(getattr(payment.status, 'value', payment.status))}

    @app.get(f'{prefix}/demo-pay/{{reference}}', include_in_schema=False)
    async def demo_pay_status(reference: str, principal: Principal):
        return view(await own_payment(reference, principal))

    @app.post(f'{prefix}/demo-pay/{{reference}}/{{outcome}}', include_in_schema=False)
    async def demo_pay_decide(reference: str, outcome: str, principal: Principal):
        payment = await own_payment(reference, principal)
        if outcome not in OUTCOMES:
            raise ApplicationError('invalid_payment_event', 'Payment event status is invalid', 422)
        body = json.dumps({'event_id': f'demo-evt-{uuid4().hex}', 'provider_reference': reference,
                           'status': OUTCOMES[outcome]}).encode()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://demo') as client:
            sent = await client.post(f'{prefix}/payments/webhook', content=body,
                                     headers={'x-demo-signature': provider.sign(body), 'content-type': 'application/json'})
        if sent.status_code != 204:
            raise ApplicationError('payment_provider_unavailable', 'The payment event was not accepted', 503)
        async with app.state.db_session_factory() as session:
            current = await session.get(Payment, payment.id)
        return view(current)
