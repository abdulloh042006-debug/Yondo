"""Payment provider abstraction. The real local provider is selected later (TZ §26)."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Literal, Protocol

from yondo_api.api.errors import ApplicationError


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    provider_payment_id: str
    checkout_url: str


@dataclass(frozen=True, slots=True)
class RefundResult:
    provider_refund_id: str
    succeeded: bool


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    event_id: str
    provider_payment_id: str
    status: Literal['succeeded', 'failed']
    amount_minor: int
    currency: str
    failure_reason: str | None = None


class PaymentProvider(Protocol):
    name: str

    async def create_checkout(
        self, payment_id: str, amount_minor: int, currency: str, description: str
    ) -> CheckoutSession: ...

    async def refund(
        self, provider_payment_id: str, refund_id: str, amount_minor: int
    ) -> RefundResult: ...

    def parse_webhook(self, headers: dict[str, str], body: bytes) -> WebhookEvent: ...


class SandboxPaymentProvider:
    """Local-only simulated provider. Never enabled in staging or production."""

    name = 'sandbox'
    signature_header = 'x-yondo-signature'

    def __init__(self, secret: bytes, checkout_base_url: str) -> None:
        self.secret = secret
        self.checkout_base_url = checkout_base_url.rstrip('/')

    def sign(self, body: bytes) -> str:
        return hmac.new(self.secret, body, hashlib.sha256).hexdigest()

    async def create_checkout(
        self, payment_id: str, amount_minor: int, currency: str, description: str
    ) -> CheckoutSession:
        return CheckoutSession(
            provider_payment_id=f'sbx_{payment_id}',
            checkout_url=f'{self.checkout_base_url}/{payment_id}',
        )

    async def refund(
        self, provider_payment_id: str, refund_id: str, amount_minor: int
    ) -> RefundResult:
        return RefundResult(provider_refund_id=f'sbx_refund_{refund_id}', succeeded=True)

    def parse_webhook(self, headers: dict[str, str], body: bytes) -> WebhookEvent:
        signature = headers.get(self.signature_header, '')
        if not hmac.compare_digest(self.sign(body), signature):
            raise ApplicationError('invalid_signature', 'Webhook signature is invalid', 401)
        try:
            data = json.loads(body)
            return WebhookEvent(
                event_id=str(data['event_id']),
                provider_payment_id=str(data['payment_id']),
                status=data['status'],
                amount_minor=int(data['amount_minor']),
                currency=str(data['currency']),
                failure_reason=data.get('failure_reason'),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ApplicationError('invalid_webhook', 'Webhook payload is invalid', 400) from exc
