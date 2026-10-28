"""Telegram Gateway OTP delivery (https://core.telegram.org/gateway).

Telegram only *delivers* OUR code: ``auth.service`` generates, hashes and verifies it. Delivery is
a two-step flow, at most TWO requests per call (JSON bodies, ``Authorization: Bearer <token>``)::

    1. POST {base_url}/checkSendAbility
       {"phone_number": "+998..."}
    2. POST {base_url}/sendVerificationMessage
       {"phone_number": "+998...", "code": "<our 6 digits>", "ttl": 300,
        "payload": "<random id>", "request_id": "<from step 1, when present>"}

Step 2 happens only when step 1 answered ``ok:true``; if the check fails nothing is sent. The
``request_id`` from the check is passed on so Telegram does not bill the check and the send
separately. ``payload`` is an opaque random id (never the phone, the code or any PII). No
``callback_url``: delivery reports are optional and not used. Neither call is ever retried (a blind
retry of a send can be billed twice); the caller decides whether the user may ask again. Nothing is
written to the database when this raises (see ``issue_otp``).

Verified live on 2026-10-28 with the owner's own Uzbek (+998) number, an account registered as an
individual: both steps work against the real API, JSON request bodies are accepted, ``ttl`` 300 is
accepted, and our own code was delivered and matched. Still UNVERIFIED: the exact ``error`` strings
for a number without Telegram and for an empty balance (the table below is a guess from third-party
documentation), the allowed ``ttl`` range, the real HTTP status of a rejected request, delivery to
other users' numbers, and the sender name the user sees. See docs/otp-telegram-gateway.md and
docs/login-telegram-gateway.md.

Outcome mapping. Everything Telegram-specific is the table ``ERROR_RULES`` plus ``DEFAULT_RULE``
below, applied to the answer of EACH call; change the strings there::

    Telegram answer (check or send)                    outcome                           log
    ok:true on HTTP 2xx                                next step / OtpDelivery('telegram')  info
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
Authorization header, becomes ``__context__``). Logs carry only the Telegram method name, the
Telegram error string (validated against a strict character set), Telegram's own request id as
``telegram_request_id`` (not ``request_id``, which is our HTTP correlation id) and, for transport
failures, the exception class name.
"""

import re
import secrets
from collections.abc import Callable

import httpx
import structlog

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.providers import OtpDelivery, otp_channel_unavailable, otp_delivery_failed

CHECK_METHOD = 'checkSendAbility'
SEND_METHOD = 'sendVerificationMessage'
_OK_EVENT = {CHECK_METHOD: 'telegram_gateway_checked', SEND_METHOD: 'telegram_gateway_sent'}

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


def _classify(method: str, response: httpx.Response) -> tuple[ApplicationError | None, str | None]:
    """Log the outcome of one call.

    Returns (error to raise, or None when Telegram accepted the call; Telegram's request id when
    it sent one in a form safe to log and to pass back).
    """
    logger = _logger()
    status = response.status_code
    envelope = _envelope(response)
    telegram_request_id = _request_id(envelope)
    ok = envelope.get('ok') if envelope is not None else None
    error = envelope.get('error') if envelope is not None else None

    if ok is True and 200 <= status < 300:
        logger.info(_OK_EVENT[method], telegram_request_id=telegram_request_id)
        return None, telegram_request_id

    if status < 500 and ok is False and isinstance(error, str) and error.strip():
        name = error.strip().upper()
        factory, level = DEFAULT_RULE
        for prefix, rule_factory, rule_level in ERROR_RULES:
            if name.startswith(prefix):
                factory, level = rule_factory, rule_level
                break
        getattr(logger, level)(
            'telegram_gateway_rejected',
            telegram_method=method,
            telegram_error=_loggable(_ERROR_NAME, name) or 'UNPARSEABLE',
            http_status=status,
            telegram_request_id=telegram_request_id,
        )
        return factory(), telegram_request_id

    logger.warning(
        'telegram_gateway_bad_response',
        telegram_method=method,
        http_status=status,
        telegram_request_id=telegram_request_id,
    )
    return otp_delivery_failed(), telegram_request_id


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
        headers = {'Authorization': f'Bearer {self._token}'}
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds, transport=self._transport
        ) as client:
            # 1. Can this number receive a Telegram message at all? If not, nothing is sent.
            check_body: dict[str, object] = {'phone_number': phone_number}
            checked = await self._post(client, CHECK_METHOD, check_body, headers)
            error, request_id = _classify(CHECK_METHOD, checked)
            if error is not None:
                raise error
            # 2. Send OUR code; the check's request_id keeps Telegram from billing twice.
            body: dict[str, object] = {
                'phone_number': phone_number,
                'code': code,
                'ttl': self._ttl_seconds,
                'payload': secrets.token_urlsafe(16),
            }
            if request_id is not None:
                body['request_id'] = request_id
            sent = await self._post(client, SEND_METHOD, body, headers)
            error, _ = _classify(SEND_METHOD, sent)
            if error is not None:
                raise error
        return OtpDelivery(channel='telegram')

    async def _post(
        self,
        client: httpx.AsyncClient,
        method: str,
        body: dict[str, object],
        headers: dict[str, str],
    ) -> httpx.Response:
        response: httpx.Response | None = None
        error_type = ''
        try:
            response = await client.post(f'{self._base_url}/{method}', json=body, headers=headers)
        except Exception as exc:  # fail closed on anything the HTTP layer can raise
            error_type = type(exc).__name__
        # Raised outside the `except` block on purpose: no httpx exception (its request holds
        # the Authorization header) may end up as __context__/__cause__ of what we raise.
        if response is None:
            _logger().warning(
                'telegram_gateway_unreachable', telegram_method=method, error_type=error_type
            )
            raise otp_delivery_failed()
        return response
