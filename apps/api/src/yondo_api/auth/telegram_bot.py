"""Login codes through the project's own FREE Telegram bot (Bot API ``sendMessage``).

The owner's separate bot service (aiogram, on his VPS, not in this repo) owns all Telegram
updates: /start <payload>, the contact-sharing keyboard and the ``contact.user_id == from.id``
check. This backend therefore registers NO webhook and never calls ``getUpdates``. It only:

1. issues link challenges (``/auth/telegram/link/start``),
2. receives the bot's verified result (``/auth/telegram/link/complete``),
3. sends codes with ``sendMessage`` to the linked private chat (this module).

Our code is generated, hashed and verified by ``auth.service`` exactly as for every other
channel. ``deliver`` raises before anything is written when sending fails, so a failed send
never looks like "code sent" and never starts the resend cooldown. Never retried, never falls
back to the paid Telegram Gateway.

Secrets: the bot token is part of the Bot API URL (``/bot<token>/sendMessage``), so neither the
URL nor any httpx exception (whose request carries it) is logged or chained into our errors:
``ApplicationError`` is raised outside every ``except`` block, as in ``telegram_gateway``.
Logs carry only the Bot API ``error_code`` (an int), the HTTP status and exception class names.
"""

from collections.abc import Awaitable, Callable

import httpx
import structlog

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.providers import OtpDelivery, otp_delivery_failed

ChatLookup = Callable[[str], Awaitable[int | None]]

# Bot API descriptions that mean "this chat cannot get messages from the bot".
_UNREACHABLE = ('bot was blocked', 'chat not found', 'user is deactivated', 'bot can\'t initiate')

MESSAGE = (
    'Yondo kirish kodi: {code}\n'
    'Kodni hech kimga bermang. U 5 daqiqa amal qiladi.\n\n'
    'Код входа Yondo: {code}\n'
    'Никому не сообщайте код. Он действует 5 минут.'
)


def telegram_link_required() -> ApplicationError:
    return ApplicationError(
        'telegram_link_required', 'Open the Yondo Telegram bot and share your contact first', 422
    )


def telegram_bot_unreachable() -> ApplicationError:
    return ApplicationError(
        'telegram_bot_unreachable',
        'The Yondo Telegram bot cannot message this account; unblock or restart the bot',
        422,
    )


def _logger() -> structlog.typing.FilteringBoundLogger:
    return structlog.get_logger(__name__)


class TelegramBotOtpProvider:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = 'https://api.telegram.org',
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
        chat_lookup: ChatLookup | None = None,
    ) -> None:
        self._token = token
        self._base_url = base_url.rstrip('/')
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self.chat_lookup = chat_lookup  # attached at startup (needs the DB session factory)

    async def deliver(self, phone_number: str, code: str) -> OtpDelivery:
        chat_id = await self.chat_lookup(phone_number) if self.chat_lookup else None
        if chat_id is None:
            raise telegram_link_required()
        await self.send_code(chat_id, code)
        return OtpDelivery(channel='telegram')

    async def send_code(self, chat_id: int, code: str) -> None:
        error = await self._send(chat_id, MESSAGE.format(code=code))
        if error is not None:
            raise error

    async def _send(self, chat_id: int, text: str) -> ApplicationError | None:
        logger = _logger()
        failure: str | None = None
        response: httpx.Response | None = None
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout_seconds), transport=self._transport
            ) as client:
                response = await client.post(
                    f'{self._base_url}/bot{self._token}/sendMessage',
                    json={'chat_id': chat_id, 'text': text, 'protect_content': True},
                )
        except Exception as exc:  # noqa: BLE001 - never chain: the request carries the token
            failure = type(exc).__name__
        if response is None:
            logger.warning('telegram_bot_transport_failed', error_type=failure)
            return otp_delivery_failed()
        try:
            body = response.json()
        except ValueError:
            body = None
        envelope = body if isinstance(body, dict) else {}
        ok = envelope.get('ok')
        if ok is True and 200 <= response.status_code < 300:
            logger.info('telegram_bot_code_sent')
            return None
        error_code = envelope.get('error_code')
        description = envelope.get('description')
        if (
            ok is False
            and error_code in (400, 403)
            and isinstance(description, str)
            and any(marker in description.lower() for marker in _UNREACHABLE)
        ):
            logger.info('telegram_bot_chat_unreachable', telegram_error_code=error_code)
            return telegram_bot_unreachable()
        logger.warning(
            'telegram_bot_rejected',
            http_status=response.status_code,
            telegram_error_code=error_code if isinstance(error_code, int) else None,
        )
        return otp_delivery_failed()
