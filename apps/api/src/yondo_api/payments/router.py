from __future__ import annotations

import html
import json
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from yondo_api.api.errors import ApplicationError
from yondo_api.core.deps import CurrentUser, Session
from yondo_api.core.schemas import Page, PageParams, page_of
from yondo_api.core.time import utc_now
from yondo_api.payments import service
from yondo_api.payments.models import Payment, Payout, PayoutStatus
from yondo_api.payments.providers import SandboxPaymentProvider
from yondo_api.payments.schemas import (
    BookingCheckout,
    Earnings,
    EarningsSummary,
    PaymentResponse,
    PayoutResponse,
    SandboxResult,
    WebhookAck,
)

router = APIRouter(prefix='/payments', tags=['payments'])
payouts_router = APIRouter(prefix='/payouts', tags=['payouts'])


@router.post('/bookings/{booking_id}/checkout', response_model=PaymentResponse)
async def checkout_booking(
    booking_id: UUID,
    payload: BookingCheckout,
    request: Request,
    user: CurrentUser,
    session: Session,
):
    return await service.checkout_booking(
        session, request.app.state, user, booking_id, payload.idempotency_key
    )


@router.get('', response_model=Page[PaymentResponse])
async def my_payments(
    user: CurrentUser, session: Session, params: Annotated[PageParams, Depends()]
):
    rows = list(
        await session.scalars(
            select(Payment)
            .where(Payment.payer_id == user.id)
            .order_by(Payment.created_at.desc(), Payment.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    return page_of([PaymentResponse.model_validate(row) for row in rows], params)


@router.get('/{payment_id}', response_model=PaymentResponse)
async def get_payment(payment_id: UUID, user: CurrentUser, session: Session):
    payment = await session.get(Payment, payment_id)
    if payment is None or payment.payer_id != user.id:
        raise ApplicationError('payment_not_found', 'Payment not found', 404)
    return payment


@router.post('/webhooks/{provider_name}', response_model=WebhookAck)
async def provider_webhook(provider_name: str, request: Request, session: Session):
    """Provider callback. Authenticated by the provider signature, not a user session."""
    provider = request.app.state.payment_providers.get(provider_name)
    if provider is None:
        raise ApplicationError('not_found', 'Not found', 404)
    body = await request.body()
    event = provider.parse_webhook({k.lower(): v for k, v in request.headers.items()}, body)
    try:
        payload = json.loads(body)
    except ValueError:
        payload = {}
    outcome = await service.handle_webhook(session, provider, event, payload)
    return WebhookAck(outcome=outcome)


def _sandbox(request: Request) -> SandboxPaymentProvider:
    provider = request.app.state.payment_providers.get('sandbox')
    if not request.app.state.settings.is_local or not isinstance(provider, SandboxPaymentProvider):
        raise ApplicationError('not_found', 'Not found', 404)
    return provider


@router.get('/sandbox/{payment_id}', response_class=HTMLResponse, include_in_schema=False)
async def sandbox_checkout_page(payment_id: UUID, request: Request, session: Session):
    _sandbox(request)
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise ApplicationError('payment_not_found', 'Payment not found', 404)
    amount = html.escape(f'{payment.amount_minor} {payment.currency}')
    status = html.escape(payment.status)
    return HTMLResponse(
        f"""<!doctype html><html><head><meta name="viewport" content="width=device-width">
<title>Yondo sandbox payment</title></head>
<body style="font-family:sans-serif;max-width:420px;margin:40px auto;padding:0 16px">
<h2>Yondo sandbox payment</h2><p>Amount: <b>{amount}</b></p><p>Status: {status}</p>
<p>This simulated page exists only in local development.</p>
<button onclick="go('succeeded')">Pay</button> <button onclick="go('failed')">Fail</button>
<p id="out"></p>
<script>
async function go(result) {{
  const r = await fetch(location.pathname + '/simulate', {{method: 'POST',
    headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{result}})}});
  document.getElementById('out').textContent = JSON.stringify(await r.json());
}}
</script></body></html>"""
    )


@router.post('/sandbox/{payment_id}/simulate', response_model=WebhookAck, include_in_schema=False)
async def sandbox_simulate(
    payment_id: UUID, payload: SandboxResult, request: Request, session: Session
):
    """Local only: emulate the provider calling the signed webhook."""
    provider = _sandbox(request)
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise ApplicationError('payment_not_found', 'Payment not found', 404)
    body = json.dumps(
        {
            'event_id': str(uuid4()),
            'payment_id': payment.provider_payment_id,
            'status': payload.result,
            'amount_minor': payment.amount_minor,
            'currency': payment.currency,
        }
    ).encode()
    event = provider.parse_webhook({provider.signature_header: provider.sign(body)}, body)
    outcome = await service.handle_webhook(session, provider, event, json.loads(body))
    await service.process_refunds(session, request.app.state)
    return WebhookAck(outcome=outcome)


@payouts_router.get('/me', response_model=Earnings)
async def my_earnings(user: CurrentUser, session: Session):
    """Companion/vendor earnings (TZ §4, §30)."""
    payouts = list(
        await session.scalars(
            select(Payout)
            .where(Payout.beneficiary_id == user.id)
            .order_by(Payout.created_at.desc())
            .limit(200)
        )
    )
    now = utc_now()
    totals: dict[str, dict[str, int]] = {}
    for payout in payouts:
        bucket = totals.setdefault(
            payout.currency, {'held': 0, 'scheduled': 0, 'available': 0, 'paid': 0}
        )
        if payout.status == PayoutStatus.HELD:
            bucket['held'] += payout.amount_minor
        elif payout.status == PayoutStatus.PAID:
            bucket['paid'] += payout.amount_minor
        elif service.is_due(payout, now):
            bucket['available'] += payout.amount_minor
        elif payout.status == PayoutStatus.SCHEDULED:
            bucket['scheduled'] += payout.amount_minor
    return Earnings(
        summary=[
            EarningsSummary(
                currency=currency,
                held_minor=values['held'],
                scheduled_minor=values['scheduled'],
                available_minor=values['available'],
                paid_minor=values['paid'],
            )
            for currency, values in sorted(totals.items())
        ],
        payouts=[PayoutResponse.model_validate(item) for item in payouts],
    )
