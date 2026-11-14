import io
import json

import pytest

from yondo_api import doctor

PEPPER = 'pepper-' + 'p' * 40
TOKEN = 'tg-gateway-token-fake-0123456789'
DB_URL = 'postgresql+psycopg://yondo:db-password-fake-123@db.internal:5432/yondo'
REDIS_URL = 'redis://:redis-password-fake@redis.internal:6379/0'
S3_ACCESS = 'access-key-fake-AKIA0000'
S3_SECRET = 'secret-key-fake-zzzzzzzzzzzzzzzz'
CARD = '4111 1111 1111 1234'
HOLDER = 'Test Holder'
TEZ_TOKEN = 'tezcheck-token-fake-9999'
TEZ_WEBHOOK = 'tezcheck-webhook-secret-fake-0000'

SECRETS = (PEPPER, TOKEN, 'db-password-fake-123', 'redis-password-fake', S3_ACCESS, S3_SECRET)

PRODUCTION = {
    'YONDO_ENVIRONMENT': 'production',
    'YONDO_DATABASE_URL': DB_URL,
    'YONDO_REDIS_URL': REDIS_URL,
    'YONDO_AUTH_OTP_PEPPER': PEPPER,
    'YONDO_TELEGRAM_GATEWAY_TOKEN': TOKEN,
    'YONDO_STORAGE_BACKEND': 's3',
    'YONDO_STORAGE_ENDPOINT': 'https://user:pw-in-url@s3.example.test/x?sig=abc',
    'YONDO_STORAGE_BUCKET': 'bucket',
    'YONDO_STORAGE_ACCESS_KEY': S3_ACCESS,
    'YONDO_STORAGE_SECRET_KEY': S3_SECRET,
    'YONDO_PAYMENT_PROVIDER': 'manual',
    'YONDO_MANUAL_PAYMENT_CARDS': json.dumps([{'label': 'Visa', 'number': CARD, 'holder': HOLDER}]),
    'YONDO_PUBLIC_WEB_URL': 'https://app.example.test',
}


@pytest.fixture
def env(monkeypatch):
    for key in list(__import__('os').environ):
        if key.upper().startswith('YONDO_'):
            monkeypatch.delenv(key)

    def apply(values: dict[str, str]) -> None:
        for key, value in values.items():
            monkeypatch.setenv(key, value)

    return apply


def run(strict: bool = False, env_file=None) -> tuple[int, str, dict[str, doctor.Check]]:
    out = io.StringIO()
    code = doctor.run(env_file, strict=strict, out=out)
    checks = {c.name: c for c in doctor.Doctor(doctor.read_env(env_file)).checks()}
    return code, out.getvalue(), checks


def test_development_defaults_pass_and_strict_fails_on_missing_optionals(env):
    env({})
    code, out, checks = run()
    assert code == 0 and 'Result: OK' in out
    assert checks['Telegram Gateway (login codes)'].status == doctor.MISSING
    assert 'shown on screen' in checks['Telegram Gateway (login codes)'].detail
    assert checks['TezCheck payments'].detail.startswith('disabled (beta)')
    assert run(strict=True)[0] == 1


def test_production_without_required_settings_fails(env):
    env({'YONDO_ENVIRONMENT': 'production'})
    code, out, checks = run()
    assert code == 1 and 'Result: FAIL' in out
    for name in ('Database', 'Redis', 'Login code pepper', 'Telegram Gateway (login codes)'):
        assert checks[name].status == doctor.MISSING and checks[name].required, name
    assert '503' in checks['Telegram Gateway (login codes)'].detail  # the safe fallback
    assert 'API settings' in out  # the API itself refuses the default pepper


def test_complete_production_passes_and_prints_no_secret(env):
    env(PRODUCTION)
    code, out, checks = run()
    assert code == 0, out
    assert all(
        c.status in {doctor.OK, doctor.DISABLED, doctor.INFO, doctor.MISSING}
        for c in checks.values()
    )
    for value in SECRETS + (CARD, CARD.replace(' ', ''), HOLDER, 'pw-in-url', 'sig=abc'):
        assert value not in out, value
    assert f'set ({len(TOKEN)} chars)' in out
    assert '••••1234' in out
    assert 'https://s3.example.test' in out
    assert checks['TezCheck payments'].status == doctor.DISABLED


def test_invalid_values_are_reported_without_echoing_them(env):
    bad_card = '4111 1111 11'
    env(
        {
            **PRODUCTION,
            'YONDO_MANUAL_PAYMENT_CARDS': json.dumps(
                [{'label': 'Visa', 'number': bad_card, 'holder': HOLDER}]
            ),
            'YONDO_AUTH_OTP_PEPPER': 'short-pepper-value',
            'YONDO_PLATFORM_FEE_BPS': 'abc',
            'YONDO_STORAGE_ENDPOINT': 'http://s3.example.test',
        }
    )
    code, out, checks = run()
    assert code == 1
    assert checks['Manual payment cards'].status == doctor.INVALID
    assert checks['Login code pepper'].status == doctor.INVALID
    assert checks['Platform fee'].status == doctor.INVALID
    assert checks['S3 photo/ID storage'].status == doctor.INVALID
    for value in (bad_card, HOLDER, 'short-pepper-value') + SECRETS[1:]:
        assert value not in out, value


def test_tezcheck_is_reported_active_when_auto_uses_its_token(env):
    env(
        {
            **PRODUCTION,
            'YONDO_PAYMENT_PROVIDER': 'auto',
            'YONDO_TEZCHECK_TOKEN': TEZ_TOKEN,
            'YONDO_TEZCHECK_WEBHOOK_SECRET': TEZ_WEBHOOK,
        }
    )
    code, out, checks = run()
    assert code == 0, out
    assert checks['TezCheck payments'].status == doctor.OK
    assert 'ACTIVE' in checks['TezCheck payments'].detail
    assert TEZ_TOKEN not in out and TEZ_WEBHOOK not in out


def test_platform_fee_is_described_as_deducted_from_the_companion(env):
    env({'YONDO_PLATFORM_FEE_BPS': '500'})
    check = run()[2]['Platform fee']
    assert check.status == doctor.OK and 'deducted from the companion' in check.detail


def test_env_file_is_read_and_the_environment_wins(env, tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text(f'YONDO_TELEGRAM_GATEWAY_TOKEN={TOKEN}\nYONDO_PLATFORM_FEE_BPS=500\n')
    env({'YONDO_PLATFORM_FEE_BPS': '700'})
    code, out, checks = run(env_file=env_file)
    assert checks['Telegram Gateway (login codes)'].status == doctor.OK
    assert 'YONDO_PLATFORM_FEE_BPS=700' in checks['Platform fee'].detail
    assert TOKEN not in out


def test_cli_exit_codes(env, capsys):
    env({})
    assert doctor.main(['--env-file', '/nonexistent/.env']) == 0
    assert doctor.main(['--strict', '--env-file', '/nonexistent/.env']) == 1
    assert 'Result:' in capsys.readouterr().out


def test_malformed_json_is_reported_not_crashed(env):
    raw = '[{"label": "Visa", "number": "4111 1111 1111 9876", "holder": "Test Holder"'  # no ]
    env({**PRODUCTION, 'YONDO_MANUAL_PAYMENT_CARDS': raw})
    code, out, checks = run()
    assert code == 1
    assert checks['Manual payment cards'].status == doctor.INVALID
    assert 'YONDO_MANUAL_PAYMENT_CARDS could not be parsed' in out
    for value in ('4111 1111 1111 9876', '9876', HOLDER):
        assert value not in out, value


def test_s3_in_development_does_not_require_bucket_or_keys(env):
    env({'YONDO_STORAGE_BACKEND': 's3'})
    assert run()[2]['S3 photo/ID storage'].status == doctor.OK


def test_telegram_bot_check_needs_all_values_and_prints_no_secret(env):
    bot_token, shared = '123:bot-token-fake-ABCDEFGHIJ', 'bot-shared-secret-fake-' + 's' * 20
    env({**PRODUCTION, 'YONDO_OTP_PROVIDER': 'telegram_bot'})
    _, out, checks = run()
    assert checks['Telegram bot (login codes, free)'].status == doctor.INVALID
    env({
        **PRODUCTION,
        'YONDO_OTP_PROVIDER': 'telegram_bot',
        'YONDO_TELEGRAM_BOT_TOKEN': bot_token,
        'YONDO_TELEGRAM_BOT_USERNAME': '@YondoTestBot',
        'YONDO_BOT_SHARED_SECRET': shared,
    })
    _, out, checks = run()
    assert checks['Telegram bot (login codes, free)'].status == doctor.OK
    assert bot_token not in out and shared not in out and '@YondoTestBot' in out
    env({**PRODUCTION, 'YONDO_OTP_PROVIDER': 'auto'})
    _, _, checks = run()
    assert checks['Telegram bot (login codes, free)'].required is False
