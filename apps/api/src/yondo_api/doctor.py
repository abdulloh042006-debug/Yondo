"""Configuration doctor: which external integrations are configured, missing or invalid.

    python -m yondo_api.doctor [--strict] [--env-file PATH]

It reads the same sources as the API (``YONDO_*`` environment variables over the ``.env`` file)
and checks **format only**. It makes no network call and never contacts a real service.
It never prints a secret: secrets appear as "set (N chars)" or "missing", card numbers as the
last 4 digits at most, and URLs as scheme + host only (no credentials, no path).

Exit code: 0 when everything required for this environment is OK, 1 when something required is
missing or invalid, or when the API itself would refuse these settings. ``--strict`` also fails
on optional integrations that are missing. Setup guide: docs/configuration.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from pydantic import ValidationError

from yondo_api.config import ManualPaymentCard, Settings

OK, MISSING, INVALID, DISABLED, INFO = 'ok', 'missing', 'invalid', 'disabled', 'info'
ENVIRONMENTS = ('development', 'test', 'staging', 'production')
DEFAULT_PEPPER = 'development-only-change-me'


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    status: str
    required: bool
    detail: str


def read_env(env_file: Path | None) -> dict[str, str]:
    """YONDO_* values as the API sees them: the process environment wins over the env file."""
    values: dict[str, str] = {}
    if env_file is not None and env_file.is_file():
        for key, value in dotenv_values(env_file).items():
            if value is not None and key.upper().startswith('YONDO_'):
                values[key.upper()] = value
    for key, value in os.environ.items():
        if key.upper().startswith('YONDO_'):
            values[key.upper()] = value
    return values


def secret(value: str | None) -> str:
    return f'set ({len(value)} chars)' if value else 'missing'


def origin(url: str) -> str:
    """scheme://host[:port] only: never userinfo (credentials), path or query."""
    parts = urlsplit(url)
    if not parts.scheme or not parts.hostname:
        return 'not a URL'
    port = f':{parts.port}' if parts.port else ''
    return f'{parts.scheme}://{parts.hostname}{port}'


def is_https(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme == 'https' and bool(parts.hostname)


class Doctor:
    def __init__(self, env: dict[str, str]) -> None:
        self.env = env
        self.environment = env.get('YONDO_ENVIRONMENT', 'development').strip().lower()
        self.prod = self.environment in {'staging', 'production'}

    def get(self, name: str) -> str:
        return self.env.get(name, '').strip()

    def checks(self) -> list[Check]:
        steps: list[Callable[[], Check]] = [
            self.environment_check,
            self.database,
            self.redis,
            self.otp_pepper,
            self.telegram_gateway,
            self.object_storage,
            self.public_web_url,
            self.payment_provider,
            self.manual_cards,
            self.platform_fee,
            self.tezcheck,
            self.click_test,
            self.cors,
            self.push_notifications,
            self.demo_flags,
        ]
        return [step() for step in steps]

    def environment_check(self) -> Check:
        if self.environment not in ENVIRONMENTS:
            return Check(
                'Environment', INVALID, True, f'YONDO_ENVIRONMENT must be one of {ENVIRONMENTS}'
            )
        return Check('Environment', OK, True, f'YONDO_ENVIRONMENT={self.environment}')

    def database(self) -> Check:
        url = self.get('YONDO_DATABASE_URL')
        if not url:
            if self.prod:
                return Check(
                    'Database',
                    MISSING,
                    True,
                    'YONDO_DATABASE_URL missing (no fallback: the API cannot start)',
                )
            return Check(
                'Database',
                OK,
                False,
                'YONDO_DATABASE_URL missing: local default postgres on localhost',
            )
        scheme = urlsplit(url).scheme
        if not scheme.startswith('postgresql'):
            return Check(
                'Database',
                INVALID,
                True,
                f'YONDO_DATABASE_URL {secret(url)}: must start with postgresql+psycopg://',
            )
        return Check(
            'Database',
            OK,
            True,
            f'YONDO_DATABASE_URL {secret(url)}, scheme {scheme} (credentials hidden)',
        )

    def redis(self) -> Check:
        url = self.get('YONDO_REDIS_URL')
        if not url:
            status = MISSING if self.prod else OK
            return Check(
                'Redis',
                status,
                self.prod,
                'YONDO_REDIS_URL missing: local default redis://localhost:6379/0',
            )
        if urlsplit(url).scheme not in {'redis', 'rediss'}:
            return Check(
                'Redis',
                INVALID,
                True,
                f'YONDO_REDIS_URL {secret(url)}: must start with redis:// or rediss://',
            )
        return Check(
            'Redis',
            OK,
            self.prod,
            f'YONDO_REDIS_URL {secret(url)}, scheme {urlsplit(url).scheme} (credentials hidden)',
        )

    def otp_pepper(self) -> Check:
        value = self.get('YONDO_AUTH_OTP_PEPPER')
        if not value or value == DEFAULT_PEPPER:
            status = MISSING if self.prod else OK
            return Check(
                'Login code pepper',
                status,
                self.prod,
                'YONDO_AUTH_OTP_PEPPER missing: development default '
                '(refused in staging/production)',
            )
        if len(value) < 32:
            status = INVALID if self.prod else OK
            return Check(
                'Login code pepper',
                status,
                self.prod,
                f'YONDO_AUTH_OTP_PEPPER {secret(value)}: '
                'needs 32+ characters in staging/production',
            )
        return Check('Login code pepper', OK, self.prod, f'YONDO_AUTH_OTP_PEPPER {secret(value)}')

    def telegram_gateway(self) -> Check:
        token = self.get('YONDO_TELEGRAM_GATEWAY_TOKEN')
        base = self.get('YONDO_TELEGRAM_GATEWAY_BASE_URL') or 'https://gatewayapi.telegram.org'
        if not token:
            fallback = (
                'login answers 503 "not configured"'
                if self.prod
                else 'the code is shown on screen (development/test only)'
            )
            return Check(
                'Telegram Gateway (login codes)',
                MISSING,
                self.prod,
                f'YONDO_TELEGRAM_GATEWAY_TOKEN missing: {fallback}',
            )
        if not is_https(base):
            return Check(
                'Telegram Gateway (login codes)',
                INVALID,
                True,
                'YONDO_TELEGRAM_GATEWAY_BASE_URL must be an https URL',
            )
        return Check(
            'Telegram Gateway (login codes)',
            OK,
            self.prod,
            f'YONDO_TELEGRAM_GATEWAY_TOKEN {secret(token)}, {origin(base)}; '
            'balance is not checked (no network calls)',
        )

    def object_storage(self) -> Check:
        name = 'S3 photo/ID storage'
        backend = self.get('YONDO_STORAGE_BACKEND').lower() or 'disabled'
        if backend == 'disabled':
            return Check(
                name,
                MISSING,
                False,
                'YONDO_STORAGE_BACKEND=disabled: photo and ID uploads answer 503',
            )
        if backend != 's3':
            return Check(name, INVALID, True, 'YONDO_STORAGE_BACKEND must be "disabled" or "s3"')
        problems = []
        endpoint = self.get('YONDO_STORAGE_ENDPOINT') or 'http://localhost:9000'
        public = self.get('YONDO_STORAGE_PUBLIC_ENDPOINT') or endpoint
        for var in ('YONDO_STORAGE_BUCKET', 'YONDO_STORAGE_ACCESS_KEY', 'YONDO_STORAGE_SECRET_KEY'):
            if not self.get(var):
                problems.append(f'{var} missing')
        if self.prod:
            for var, url in (
                ('YONDO_STORAGE_ENDPOINT', endpoint),
                ('YONDO_STORAGE_PUBLIC_ENDPOINT', public),
            ):
                if not is_https(url):
                    problems.append(f'{var} must be https')
        detail = (
            f'endpoint {origin(endpoint)}, public {origin(public)}, '
            f'access key {secret(self.get("YONDO_STORAGE_ACCESS_KEY"))}, '
            f'secret key {secret(self.get("YONDO_STORAGE_SECRET_KEY"))}'
        )
        if problems:
            return Check(name, INVALID, True, f'{"; ".join(problems)} ({detail})')
        return Check(name, OK, True, detail)

    def public_web_url(self) -> Check:
        url = self.get('YONDO_PUBLIC_WEB_URL')
        manual = self.get('YONDO_PAYMENT_PROVIDER').lower() == 'manual'
        if not url:
            return Check(
                'Public web URL',
                MISSING,
                manual,
                'YONDO_PUBLIC_WEB_URL missing (needed for manual payments: <url>/pay/<reference>)',
            )
        if not is_https(url):
            return Check(
                'Public web URL', INVALID, manual, 'YONDO_PUBLIC_WEB_URL must be an https URL'
            )
        return Check('Public web URL', OK, manual, f'YONDO_PUBLIC_WEB_URL {origin(url)}')

    def payment_provider(self) -> Check:
        provider = self.get('YONDO_PAYMENT_PROVIDER').lower() or 'auto'
        if provider not in {'auto', 'manual', 'tezcheck'}:
            return Check(
                'Payment provider',
                INVALID,
                True,
                'YONDO_PAYMENT_PROVIDER must be auto, manual or tezcheck',
            )
        if provider == 'auto' and not self.get('YONDO_TEZCHECK_TOKEN'):
            return Check(
                'Payment provider',
                MISSING,
                False,
                'YONDO_PAYMENT_PROVIDER=auto with no TezCheck token: '
                'payments answer 503 (no real money moves)',
            )
        return Check('Payment provider', OK, False, f'YONDO_PAYMENT_PROVIDER={provider}')

    def manual_cards(self) -> Check:
        name = 'Manual payment cards'
        raw = self.get('YONDO_MANUAL_PAYMENT_CARDS')
        manual = self.get('YONDO_PAYMENT_PROVIDER').lower() == 'manual'
        if not raw:
            return Check(
                name,
                MISSING,
                manual,
                'YONDO_MANUAL_PAYMENT_CARDS missing '
                '(needed only for YONDO_PAYMENT_PROVIDER=manual)',
            )
        try:
            items = json.loads(raw)
            if not isinstance(items, list) or not items:
                raise ValueError
            cards = [ManualPaymentCard.model_validate(item) for item in items]
        except (ValueError, ValidationError):
            # Never echo the value or the validation error input: it may hold a card number.
            return Check(
                name,
                INVALID,
                manual,
                'YONDO_MANUAL_PAYMENT_CARDS must be a JSON list of '
                '{"label","number","holder"} (16-19 digit numbers)',
            )
        shown = ', '.join(f'{card.label} ••••{card.number.replace(" ", "")[-4:]}' for card in cards)
        return Check(name, OK, manual, f'{len(cards)} card(s): {shown} (holder names hidden)')

    def platform_fee(self) -> Check:
        raw = self.get('YONDO_PLATFORM_FEE_BPS')
        if not raw:
            return Check(
                'Platform fee',
                MISSING,
                False,
                'YONDO_PLATFORM_FEE_BPS missing: payment creation answers 503 "not configured". '
                'Owner decision: 5% from the companion side; the code still adds the fee '
                'to the customer total, so do not set it until that is built',
            )
        if not raw.isdigit() or not 0 <= int(raw) <= 10_000:
            return Check(
                'Platform fee',
                INVALID,
                True,
                'YONDO_PLATFORM_FEE_BPS must be an integer 0..10000 (basis points)',
            )
        return Check(
            'Platform fee',
            OK,
            False,
            f'YONDO_PLATFORM_FEE_BPS={int(raw)} basis points. WARNING: the code adds the fee '
            'to the customer total; the owner decision is to deduct it from the companion side',
        )

    def tezcheck(self) -> Check:
        name = 'TezCheck payments'
        token = self.get('YONDO_TEZCHECK_TOKEN')
        provider = self.get('YONDO_PAYMENT_PROVIDER').lower() or 'auto'
        if provider == 'manual' or (provider == 'auto' and not token):
            return Check(name, DISABLED, False, 'disabled (beta): not used in the beta')
        problems = []
        if not token:
            problems.append('YONDO_TEZCHECK_TOKEN missing')
        if len(self.get('YONDO_TEZCHECK_WEBHOOK_SECRET')) < 16:
            problems.append('YONDO_TEZCHECK_WEBHOOK_SECRET needs 16+ characters')
        api = self.get('YONDO_TEZCHECK_API_URL') or 'https://api.tezcheck.uz/api/merchant/v1'
        if not is_https(api):
            problems.append('YONDO_TEZCHECK_API_URL must be https')
        if self.environment == 'production' and self.get(
            'YONDO_TEZCHECK_ACCEPT_TEST_PAYMENTS'
        ).lower() in {'1', 'true', 'yes', 'on'}:
            problems.append('YONDO_TEZCHECK_ACCEPT_TEST_PAYMENTS is not allowed in production')
        webhook = secret(self.get('YONDO_TEZCHECK_WEBHOOK_SECRET'))
        detail = (
            f'token {secret(token)}, webhook secret {webhook}; '
            'ACTIVE (the beta decision is not to use TezCheck)'
        )
        if problems:
            return Check(name, INVALID, True, f'{"; ".join(problems)} ({detail})')
        return Check(name, OK, False, detail)

    def click_test(self) -> Check:
        enabled = self.get('YONDO_CLICK_TEST_ENABLED').lower() in {'1', 'true', 'yes', 'on'}
        if not enabled:
            return Check(
                'CLICK test emulator',
                DISABLED,
                False,
                'off (offline emulator, local environments only)',
            )
        if self.prod:
            return Check(
                'CLICK test emulator',
                INVALID,
                True,
                'YONDO_CLICK_TEST_ENABLED is refused outside development/test',
            )
        return Check(
            'CLICK test emulator',
            OK,
            False,
            f'on; secret {secret(self.get("YONDO_CLICK_TEST_SECRET"))}',
        )

    def cors(self) -> Check:
        return Check(
            'CORS',
            INFO,
            False,
            'no setting: the API adds no CORS headers; the web app reaches it same-origin '
            'via /api (Caddy / Vite proxy)',
        )

    def push_notifications(self) -> Check:
        value = self.get('YONDO_FCM_PROJECT_ID')
        return Check(
            'Push notifications (FCM)',
            INFO,
            False,
            f'YONDO_FCM_PROJECT_ID {"set" if value else "missing"}: not used by the code yet',
        )

    def demo_flags(self) -> Check:
        names = (
            'YONDO_DEMO_HOST',
            'YONDO_DEMO_PUBLIC_URL',
            'YONDO_DEMO_DATABASE_URL',
            'YONDO_DEMO_ADMIN_PHONE',
            'YONDO_WEB_DIST',
        )
        shown = ', '.join(f'{n} {"set" if self.get(n) else "unset"}' for n in names)
        return Check('Demo harness (infra/deploy/demo only)', INFO, False, shown)


def settings_errors(env_file: Path | None) -> list[str]:
    """Problems the API itself would refuse at start-up (messages never contain input values)."""
    try:
        Settings(_env_file=env_file)  # type: ignore[call-arg]
    except ValidationError as exc:
        return [
            f'{".".join(str(p) for p in err["loc"]) or "settings"}: {err["msg"]}'
            for err in exc.errors(include_input=False, include_url=False)
        ]
    return []


def run(env_file: Path | None, strict: bool = False, out=None) -> int:
    out = out or sys.stdout
    doctor = Doctor(read_env(env_file))
    checks = doctor.checks()
    errors = settings_errors(env_file)
    print(
        f'Yondo configuration doctor — environment: {doctor.environment} '
        '(format checks only, no network calls)',
        file=out,
    )
    for check in checks:
        need = 'required' if check.required else 'optional'
        print(f'  {check.status:<8} {need:<8} {check.name}: {check.detail}', file=out)
    for error in errors:
        print(f'  invalid  required API settings: {error}', file=out)
    failed = [c for c in checks if c.required and c.status in {MISSING, INVALID}] or errors
    if strict:
        failed = failed or [c for c in checks if c.status in {MISSING, INVALID}]
    print(f'Result: {"FAIL" if failed else "OK"}. Setup guide: docs/configuration.md', file=out)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Check Yondo integration settings (no network calls).'
    )
    parser.add_argument(
        '--strict', action='store_true', help='also fail on missing optional integrations'
    )
    parser.add_argument(
        '--env-file', type=Path, default=Path('.env'), help='env file to read (default .env)'
    )
    args = parser.parse_args(argv)
    return run(args.env_file, args.strict)


if __name__ == '__main__':
    sys.exit(main())
