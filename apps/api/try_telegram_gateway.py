"""Live check of Telegram Gateway delivery with YOUR OWN Telegram number (test messages are free).

Usage:  python try_telegram_gateway.py +998XXXXXXXXX

Use the number you logged in to gateway.telegram.org with. The token is read from
YONDO_TELEGRAM_GATEWAY_TOKEN (the same variable the API uses) or asked for with hidden input; it is
never printed or stored. A random code is generated here and sent through the real provider adapter
(the same two-step flow as the API: checkSendAbility, then sendVerificationMessage); you type the
code back to confirm it arrived. On a failure only the Telegram method and its error string are
printed, never the token, the phone number or the code.
Exit code 0 = sent (and confirmed when you typed it), 1 = failed or the typed code did not match.
"""

import asyncio
import getpass
import os
import secrets
import sys
from pathlib import Path

import structlog

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

from yondo_api.api.errors import ApplicationError  # noqa: E402
from yondo_api.auth.phone import normalize_uzbekistan_phone  # noqa: E402
from yondo_api.auth.telegram_gateway import TelegramGatewayOtpProvider  # noqa: E402

SAFE_FIELDS = ('telegram_method', 'telegram_error', 'http_status', 'error_type')


def show_gateway_event(logger, method_name, event_dict):
    """structlog processor: print what the adapter logged, but only a whitelist of fields.

    That is the Telegram method, the gateway's own error string and the HTTP status; never a token,
    a phone number or a code. The event is dropped afterwards, so nothing else is printed.
    """
    event = str(event_dict.get('event', ''))
    if event.startswith('telegram_gateway_'):
        details = ' '.join(
            f'{field}={event_dict[field]}' for field in SAFE_FIELDS if event_dict.get(field)
        )
        print(f'  gateway: {event} {details}'.rstrip())
    raise structlog.DropEvent


async def main(raw_phone: str) -> int:
    phone = normalize_uzbekistan_phone(raw_phone)
    token = os.environ.get('YONDO_TELEGRAM_GATEWAY_TOKEN', '').strip()
    if not token:
        token = getpass.getpass('Telegram Gateway token (hidden, not stored): ').strip()
    structlog.configure(processors=[show_gateway_event])
    code = f'{secrets.randbelow(1_000_000):06d}'
    try:
        await TelegramGatewayOtpProvider(token=token).deliver(phone, code)
    except ApplicationError as exc:
        print(f'FAIL: {exc.code} (HTTP {exc.status_code})')
        return 1
    print(
        f'Sent to {phone[:7]}***{phone[-2:]}. Open Telegram: the code should arrive within seconds.'
    )
    typed = input('Type the code you received (or press Enter to skip): ').strip()
    if not typed:
        return 0
    print(
        'MATCH: the code you typed is the one we sent.'
        if typed == code
        else 'MISMATCH: wrong code.'
    )
    return 0 if typed == code else 1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python try_telegram_gateway.py +998XXXXXXXXX')
    raise SystemExit(asyncio.run(main(sys.argv[1])))
