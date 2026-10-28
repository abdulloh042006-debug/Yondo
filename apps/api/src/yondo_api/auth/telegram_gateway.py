"""Telegram Gateway login-code delivery: the code arrives as a Telegram message, not an SMS.

Reference: https://core.telegram.org/gateway and /gateway/verification-tutorial (read 2026-10-28).

* `checkSendAbility` first: it says whether the number can receive Telegram messages. If it cannot,
  the user gets a clear "no Telegram on this number" error instead of a code that never arrives.
  A success returns a `request_id`, passed on to `sendVerificationMessage` so the fee is not
  charged twice.
* `sendVerificationMessage` sends OUR code (we generate, hash and verify it ourselves, exactly as
  with SMS). The code is never logged and never returned to the browser (`OtpDelivery` carries no
  development code).
* Any other failure (network, timeout, 5xx, unreadable answer, rejected request) is a generic 503;
  the gateway's error string is logged without the phone number or the code, for operators.

Not read from the docs: the error strings and exact response shapes, the allowed `ttl` range, and
the delivery-report signature (the callback is not used). Only mocked-transport tests exist so far;
the first real call with the owner's own number is the live test.
"""

import logging

import httpx

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.providers import OtpDelivery
from yondo_api.config import Settings

logger = logging.getLogger(__name__)


class TelegramGatewayOtpProvider:
    def __init__(
        self,
        *,
        token: str,
        api_url: str = 'https://gatewayapi.telegram.org',
        ttl_seconds: int = 300,  # the same lifetime as our own challenge (OTP_LIFETIME, 5 minutes)
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token = token
        self._api_url = api_url.rstrip('/')
        self._ttl = ttl_seconds
        self._timeout = timeout
        self._transport = transport

    @classmethod
    def from_settings(cls, settings: Settings) -> 'TelegramGatewayOtpProvider':
        return cls(
            token=settings.telegram_gateway_token.get_secret_value(),
            api_url=settings.telegram_gateway_api_url,
        )

    async def deliver(self, phone_number: str, code: str) -> OtpDelivery:
        headers = {'Authorization': f'Bearer {self._token}'}
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            ability = await self._call(
                client, 'checkSendAbility', {'phone_number': phone_number}, headers
            )
            if not ability.get('ok'):
                logger.warning(
                    'telegram gateway: number cannot be reached',
                    extra={'tg_error': ability.get('error')},
                )
                raise ApplicationError(
                    'otp_telegram_unavailable',
                    'This number cannot receive Telegram codes',
                    422,
                )
            body: dict[str, object] = {
                'phone_number': phone_number,
                'code': code,
                'ttl': self._ttl,
            }
            request_id = (ability.get('result') or {}).get('request_id')
            if request_id:
                body['request_id'] = request_id
            sent = await self._call(client, 'sendVerificationMessage', body, headers)
        if not sent.get('ok'):
            logger.warning('telegram gateway: code not sent', extra={'tg_error': sent.get('error')})
            raise self._unavailable()
        return OtpDelivery()

    async def _call(
        self,
        client: httpx.AsyncClient,
        method: str,
        body: dict[str, object],
        headers: dict[str, str],
    ) -> dict:
        try:
            response = await client.post(f'{self._api_url}/{method}', json=body, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning('telegram gateway: %s failed (%s)', method, type(exc).__name__)
            raise self._unavailable() from exc
        if response.status_code >= 500:
            logger.warning('telegram gateway: %s answered %s', method, response.status_code)
            raise self._unavailable()
        try:
            data = response.json()
        except ValueError as exc:
            logger.warning('telegram gateway: %s returned a non-JSON answer', method)
            raise self._unavailable() from exc
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _unavailable() -> ApplicationError:
        return ApplicationError('otp_delivery_unavailable', 'OTP delivery is unavailable', 503)
