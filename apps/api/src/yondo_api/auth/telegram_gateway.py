"""Telegram Gateway OTP delivery (https://core.telegram.org/gateway).

Telegram only *delivers* OUR code: ``auth.service`` generates, hashes and verifies it, this
adapter sends it with ``POST {base_url}/sendVerificationMessage``::

    Authorization: Bearer <token>
    {"phone_number": "+998...", "code": "<our 6 digits>", "ttl": 300, "payload": "<random id>"}

``payload`` is an opaque random id (never the phone, the code or any PII). No ``callback_url``:
delivery reports are optional and not used. Exactly ONE request is made per call and it is
never retried (a blind retry of a send can be billed twice); the caller decides whether the
user may ask again. Nothing is written to the database when this raises (see ``issue_otp``).

Outcome mapping. Everything Telegram-specific is the table ``ERROR_RULES`` plus
``DEFAULT_RULE`` below; the strings come from third-party documentation and are unverified
(docs/otp-telegram-gateway.md), so change them there::

    Telegram answer                                    outcome                           log
    ok:true on HTTP 2xx                                OtpDelivery(channel='telegram')   info
    ok:false, PHONE_NUMBER_*                           422 otp_channel_unavailable       info
    ok:false, BALANCE_NOT_ENOUGH or ACCESS_TOKEN_*     502 otp_delivery_failed           error
    ok:false, FLOOD_WAIT_*                             502 otp_delivery_failed           warning
    ok:false, REQUEST_* or any other / unknown error   502 otp_delivery_failed           warning
    ok:false without an error string; ok missing or    502 otp_delivery_failed           warning
      not a boolean; body not a JSON object;
      ok:true on a non-2xx status
    HTTP 5xx, whatever the body says                   502 otp_delivery_failed           warning
    timeout, connection error, any other exception     502 otp_delivery_failed           warning
      raised by the HTTP layer

The body is read before the HTTP status of a 4xx (the real status for an unknown number is not
documented), so a 4xx carrying ``ok:false`` + ``PHONE_NUMBER_*`` still maps to 422.

``BALANCE_NOT_ENOUGH`` and ``ACCESS_TOKEN_*`` are logged at error level because they need the
owner's action (top up / replace the token); the user only ever sees the neutral 502. The 422
does reveal that a number has no Telegram account (the account-enumeration trade-off noted in
docs/otp-telegram-gateway.md, section 7): the user needs it to choose another way in.

Secrets: the token, the phone number and the code never appear in an exception message, in a
log line or in the exception chain (``ApplicationError`` messages are fixed strings and are
raised outside any ``except`` block, so no httpx exception, whose request carries the
Authorization header, becomes ``__context__``). Logs carry only the Telegram error string
(validated against a strict character set), Telegram's own request id as ``telegram_request_id``
(not ``request_id``, which is our HTTP correlation id) and, for transport failures, the
exception class name.
"""

import re
import secrets
from collections.abc import Callable

import httpx
import structlog

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.providers import OtpDelivery, otp_channel_unavailable, otp_delivery_failed

SEND_METHOD = 'sendVerificationMessage'

# (prefix of the Telegram `error` string, upper-cased) -> (error to raise, log level).
# First match wins; anything not listed falls through to DEFAULT_RULE.
ErrorRule = tuple[str, Callable[[], ApplicationError], str]
ERROR_RULES: tuple[ErrorRule, ...] = (
    ('PHONE_NUMBER_', otp_channel_unavailable, 'info'),
    ('BALANCE_NOT_ENOUGH', otp_delivery_failed, 'error'),
    ('ACCESS_TOKEN_', otp_delivery_failed, 'error'),
    ('FLOOD_WAIT_', otp_delivery_failed, 'warning'),
)
DEFAULT_RULE: tuple[Callable[[], ApplicationError], str] = (otp_delivery_failed, 'warning')

_ERROR_NAME = re.compile(r'[A-Z0-9_]{1,64}')
_REQUEST_ID = re.compile(r'[A-Za-z0-9_.:-]{1,128}')


def _logger() -> structlog.typing.FilteringBoundLogger:
    # Resolved per call, not at import: structlog is configured by create_application() and its
    # cache_logger_on_first_use would otherwise pin whatever configuration was active at the
    # first log line (e.g. a stale processor list when the app is created more than once).
    return structlog.get_logger(__name__)


def _loggable(pattern: re.Pattern[str], value: object) -> str | None:
    """Return `value` only if it is a short, boring identifier; never echo anything else."""
    return value if isinstance(value, str) and pattern.fullmatch(value) else None


def _envelope(response: httpx.Response) -> dict[str, object] | None:
    try:
        body = response.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def _request_id(envelope: dict[str, object] | None) -> str | None:
    if envelope is None:
        return None
    result = envelope.get('result')
    source = result if isinstance(result, dict) else envelope
    return _loggable(_REQUEST_ID, source.get('request_id'))


def _classify(response: httpx.Response) -> ApplicationError | None:
    """Log the outcome and return the error to raise, or None when Telegram accepted the send."""
    logger = _logger()
    status = response.status_code
    envelope = _envelope(response)
    telegram_request_id = _request_id(envelope)
    ok = envelope.get('ok') if envelope is not None else None
    error = envelope.get('error') if envelope is not None else None

    if ok is True and 200 <= status < 300:
        logger.info('telegram_gateway_sent', telegram_request_id=telegram_request_id)
        return None

    if status < 500 and ok is False and isinstance(error, str) and error.strip():
        name = error.strip().upper()
        factory, level = DEFAULT_RULE
        for prefix, rule_factory, rule_level in ERROR_RULES:
            if name.startswith(prefix):
                factory, level = rule_factory, rule_level
                break
        getattr(logger, level)(
            'telegram_gateway_rejected',
            telegram_error=_loggable(_ERROR_NAME, name) or 'UNPARSEABLE',
            http_status=status,
            telegram_request_id=telegram_request_id,
        )
        return factory()

    logger.warning(
        'telegram_gateway_bad_response', http_status=status, telegram_request_id=telegram_request_id
    )
    return otp_delivery_failed()


class TelegramGatewayOtpProvider:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = 'https://gatewayapi.telegram.org',
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
        ttl_seconds: int = 300,
    ) -> None:
        # The token is a secret: keep it private and never include it in logs or messages.
        self._token = token
        self._base_url = base_url.rstrip('/')
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._ttl_seconds = ttl_seconds

    async def deliver(self, phone_number: str, code: str) -> OtpDelivery:
        body = {
            'phone_number': phone_number,
            'code': code,
            'ttl': self._ttl_seconds,
            'payload': secrets.token_urlsafe(16),
        }
        headers = {'Authorization': f'Bearer {self._token}'}
        response: httpx.Response | None = None
        error_type = ''
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, transport=self._transport
            ) as client:
                response = await client.post(
                    f'{self._base_url}/{SEND_METHOD}', json=body, headers=headers
                )
        except Exception as exc:  # fail closed on anything the HTTP layer can raise
            error_type = type(exc).__name__
        # Raised outside the `except` block on purpose: no httpx exception (its request holds
        # the Authorization header) may end up as __context__/__cause__ of what we raise.
        if response is None:
            _logger().warning('telegram_gateway_unreachable', error_type=error_type)
            raise otp_delivery_failed()
        error = _classify(response)
        if error is not None:
            raise error
        return OtpDelivery(channel='telegram')
