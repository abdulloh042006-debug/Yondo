"""TezCheck (tezcheck.uz) payment adapter: one merchant API in front of Click, Payme, Uzum, cards.

API reference: https://tezcheck.uz/api-docs (summary and open questions: docs/payments-tezcheck.md).

* `create_checkout` creates a one-time **bill** (`POST /bills`) and returns its `payment_url`.
  The bill id is the provider reference, because every webhook carries it as `data.bill_id`.
  `Idempotency-Key` is our payment id, so a retry after a timeout returns the same link
  instead of a second bill.
* `verify_event` checks the webhook signature (HMAC-SHA256 over `{timestamp}.{delivery id}.{raw
  body}`, +-300 s, several `v1=` values while a secret is being rotated) and maps
  `payment.succeeded` / `payment.failed`. The router deduplicates on the event id (the body
  `id`, not a header). Configure the webhook in the TezCheck cabinet to send only these two
  event types; any other type is refused here.
* Only a verified webhook changes a payment; the browser return is never proof of payment.
* Test-environment payments (`data.environment != "live"`) are refused unless
  `accept_test_payments` is set, which settings only allow outside production.
"""

import hashlib
import hmac
import json
import logging
import time
from collections.abc import Callable

import httpx

from yondo_api.config import Settings
from yondo_api.payments.provider import CheckoutSession, PaymentEvent

logger = logging.getLogger(__name__)

SIGNATURE_WINDOW_SECONDS = 300
BILL_TITLE = 'Yondo bron'
EVENT_STATUS = {'payment.succeeded': 'succeeded', 'payment.failed': 'failed'}


class TezCheckError(Exception):
    """Raised for any refused request or webhook; the router turns it into a generic 503 / 401."""


class TezCheckPaymentProvider:
    def __init__(
        self,
        *,
        api_url: str,
        token: str,
        webhook_secret: str,
        cash_desk_code: str = '',
        return_url: str = '',
        accept_test_payments: bool = False,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._api_url = api_url.rstrip('/')
        self._token = token
        self._secret = webhook_secret.encode()
        self._cash_desk_code = cash_desk_code
        self._return_url = return_url
        self._accept_test_payments = accept_test_payments
        self._timeout = timeout
        self._transport = transport
        self._clock = clock

    @classmethod
    def from_settings(cls, settings: Settings) -> 'TezCheckPaymentProvider':
        return cls(
            api_url=settings.tezcheck_api_url,
            token=settings.tezcheck_token.get_secret_value(),
            webhook_secret=settings.tezcheck_webhook_secret.get_secret_value(),
            cash_desk_code=settings.tezcheck_cash_desk_code,
            return_url=settings.tezcheck_return_url,
            accept_test_payments=settings.tezcheck_accept_test_payments,
        )

    async def create_checkout(
        self, *, idempotency_key: str, amount_minor: int, currency: str, description: str
    ) -> CheckoutSession:
        if currency != 'UZS':
            raise TezCheckError('TezCheck accepts UZS only')
        body: dict[str, object] = {
            'amount_minor': amount_minor,
            'title': BILL_TITLE,
            'description': description[:2000],
            'external_reference': idempotency_key[:128],
        }
        if self._return_url:
            body['return_url'] = self._return_url
        headers = {'Authorization': f'Bearer {self._token}', 'Idempotency-Key': idempotency_key}
        if self._cash_desk_code:
            headers['X-Cash-Desk-Code'] = self._cash_desk_code
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.post(f'{self._api_url}/bills', json=body, headers=headers)
        if response.status_code not in (200, 201):
            logger.warning(
                'tezcheck bill creation refused', extra={'tezcheck': self._error_summary(response)}
            )
            raise TezCheckError(f'bill creation refused ({response.status_code})')
        try:
            data = response.json()['data']
            return CheckoutSession(
                provider_reference=str(data['bill']['id']), checkout_url=str(data['payment_url'])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TezCheckError('unexpected bill response') from exc

    async def verify_event(self, body: bytes, headers: dict[str, str]) -> PaymentEvent:
        headers = {name.lower(): value for name, value in headers.items()}
        try:
            timestamp = int(headers['x-checkout-timestamp'])
            delivery = headers['x-checkout-delivery']
            candidates = headers['x-checkout-signature'].split(',')
        except (KeyError, ValueError) as exc:
            raise TezCheckError('missing or malformed webhook headers') from exc
        if abs(self._clock() - timestamp) > SIGNATURE_WINDOW_SECONDS:
            raise TezCheckError('webhook timestamp outside the allowed window')
        signed = f'{timestamp}.{delivery}.'.encode() + body
        expected = 'v1=' + hmac.new(self._secret, signed, hashlib.sha256).hexdigest()
        if not any(hmac.compare_digest(candidate.strip(), expected) for candidate in candidates):
            raise TezCheckError('webhook signature mismatch')
        try:
            payload = json.loads(body)
            status = EVENT_STATUS[payload['type']]
            data = payload['data']
            environment = data['environment']
            return_event = PaymentEvent(
                event_id=str(payload['id']), provider_reference=str(data['bill_id']), status=status
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TezCheckError('unsupported or malformed webhook event') from exc
        if environment != 'live' and not self._accept_test_payments:
            raise TezCheckError('test-environment payment refused')
        return return_event

    @staticmethod
    def _error_summary(response: httpx.Response) -> dict[str, object]:
        try:
            error = response.json().get('error', {})
            return {
                'status': response.status_code,
                'code': error.get('code'),
                'request_id': error.get('request_id'),
            }
        except (ValueError, AttributeError):
            return {'status': response.status_code}
