"""Telegram bot login (owner decision 2026-11-14). Mocked Bot API only: nothing reaches Telegram."""

import asyncio
import json
import os
import re
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import select, text

from yondo_api.auth import telegram_link
from yondo_api.auth.telegram_bot import TelegramBotOtpProvider
from yondo_api.auth.telegram_models import TelegramLink, TelegramLinkChallenge
from yondo_api.config import Settings
from yondo_api.main import create_application
from yondo_api.models.auth import OtpChallenge
from yondo_api.models.user import User

TOKEN = '123456:TEST-ONLY-bot-token-never-real'
SECRET = 'test-only-shared-bot-secret-0123456789'
LINK = '/api/v1/auth/telegram/link'
PHONE = '+998901112233'


class FakeBotApi:
    def __init__(self):
        self.sent: list[dict] = []
        self.mode = 'ok'

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.url.path == f'/bot{TOKEN}/sendMessage'
        if self.mode == 'timeout':
            raise httpx.ReadTimeout('timed out', request=request)
        if self.mode == 'blocked':
            return httpx.Response(
                403,
                json={'ok': False, 'error_code': 403,
                      'description': 'Forbidden: bot was blocked by the user'},
            )
        if self.mode == 'malformed':
            return httpx.Response(200, text='<html>not json</html>')
        if self.mode == 'server':
            return httpx.Response(500, json={'ok': False, 'error_code': 500})
        self.sent.append(json.loads(request.content))
        return httpx.Response(200, json={'ok': True, 'result': {'message_id': len(self.sent)}})

    def last_code(self) -> str:
        return re.search(r'\b(\d{6})\b', self.sent[-1]['text']).group(1)


def bot_settings(**extra):
    values = {
        'environment': 'test',
        'database_url': os.environ.get(
            'YONDO_TEST_DATABASE_URL', 'sqlite+aiosqlite:///:memory:'
        ),
        'auth_otp_pepper': 'test-only-auth-pepper-0123456789abcdef',
        'telegram_gateway_token': None,
        'otp_provider': 'telegram_bot',
        'telegram_bot_token': TOKEN,
        'telegram_bot_username': 'YondoTestBot',
        'bot_shared_secret': SECRET,
    }
    return Settings(**{**values, **extra})


@asynccontextmanager
async def bot_client(settings=None):
    api = FakeBotApi()
    provider = TelegramBotOtpProvider(TOKEN, transport=httpx.MockTransport(api))
    app = create_application(settings or bot_settings(), otp_provider=provider)
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.begin() as connection:
            if connection.dialect.name == 'sqlite':
                await connection.run_sync(User.metadata.create_all)
            else:  # opt-in PostgreSQL test database, already migrated
                await connection.execute(
                    text(
                        'TRUNCATE users, otp_challenges, telegram_links, '
                        'telegram_link_challenges CASCADE'
                    )
                )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            yield client, app, api


async def start(client, phone=PHONE):
    response = await client.post(f'{LINK}/start', json={'phone_number': phone})
    assert response.status_code == 201, response.text
    body = response.json()
    token = body['deep_link'].split('?start=')[1]
    return token, body


async def complete(client, token, *, phone=PHONE, user_id=777001, chat_id=None, secret=SECRET):
    headers = {'X-Yondo-Bot-Secret': secret} if secret is not None else {}
    return await client.post(
        f'{LINK}/complete',
        headers=headers,
        json={
            'challenge': token,
            'phone_number': phone,
            'telegram_user_id': user_id,
            'telegram_chat_id': chat_id if chat_id is not None else user_id,
        },
    )


async def status(client, poll):
    return (await client.get(f'{LINK}/status', headers={'X-Yondo-Link-Poll': poll})).json()


async def test_link_send_code_verify_and_later_login():
    async with bot_client() as (client, app, api):
        config = (await client.get(f'{LINK}/config')).json()
        assert config == {'enabled': True, 'bot_username': 'YondoTestBot'}
        token, body = await start(client, '90 111 22 33')
        assert body['deep_link'].startswith('https://t.me/YondoTestBot?start=')
        assert re.fullmatch(r'[A-Za-z0-9_-]{16,64}', token)
        assert body['status'] == 'initiated' and body['already_linked'] is False
        assert (await status(client, body['poll_token']))['status'] == 'awaiting_contact'
        done = await complete(client, token, phone='998901112233')
        assert done.status_code == 200 and done.json() == {'status': 'linked'}
        assert (await status(client, body['poll_token']))['status'] == 'otp_sent'
        assert api.sent[-1]['chat_id'] == 777001 and 'development_otp' not in done.text
        async with app.state.db_session_factory() as session:
            row = await session.scalar(select(TelegramLinkChallenge))
            assert row.token_hash != token.encode() and len(row.token_hash) == 32
            link = await session.get(TelegramLink, PHONE)
            assert (link.telegram_user_id, link.telegram_chat_id) == (777001, 777001)
        verified = await client.post(
            '/api/v1/auth/otp/verify', json={'phone_number': PHONE, 'code': api.last_code()}
        )
        assert verified.status_code == 200 and verified.json()['access_token']
        # A second start for a linked phone says so; later logins skip the bot dance.
        assert (await start(client))[1]['already_linked'] is True
        again = await client.post('/api/v1/auth/otp/request', json={'phone_number': PHONE})
        assert again.status_code == 202, again.text
        assert again.json()['delivery_channel'] == 'telegram'
        assert 'development_otp' not in again.json() and len(api.sent) == 2
        cooldown = await client.post('/api/v1/auth/otp/request', json={'phone_number': PHONE})
        assert cooldown.status_code == 429 and cooldown.json()['code'] == 'otp_resend_cooldown'
        wrong = await client.post(
            '/api/v1/auth/otp/verify', json={'phone_number': PHONE, 'code': '000000'
                                             if api.last_code() != '000000' else '111111'}
        )
        assert wrong.status_code == 401


async def test_unlinked_phone_cannot_get_a_code_and_nothing_is_stored():
    async with bot_client() as (client, app, api):
        response = await client.post('/api/v1/auth/otp/request', json={'phone_number': PHONE})
        assert response.status_code == 422 and response.json()['code'] == 'telegram_link_required'
        async with app.state.db_session_factory() as session:
            assert await session.get(OtpChallenge, PHONE) is None
        assert api.sent == []


async def test_secret_and_challenge_validation():
    async with bot_client() as (client, app, api):
        token, body = await start(client)
        for secret in (None, '', 'wrong-secret', SECRET[:-1]):
            denied = await complete(client, token, secret=secret)
            assert denied.status_code == 401 and denied.json()['code'] == 'invalid_bot_secret'
        assert (await status(client, body['poll_token']))['status'] == 'awaiting_contact'
        assert (await complete(client, 'x' * 43)).status_code == 404
        assert (await complete(client, 'bad token!')).status_code == 404
        group = await complete(client, token, user_id=5, chat_id=6)
        assert group.status_code == 422 and group.json()['code'] == 'telegram_chat_not_private'
        bad_ids = await client.post(
            f'{LINK}/complete',
            headers={'X-Yondo-Bot-Secret': SECRET},
            json={'challenge': token, 'phone_number': PHONE,
                  'telegram_user_id': '777', 'telegram_chat_id': -1},
        )
        assert bad_ids.status_code == 422
        assert (await client.get(f'{LINK}/status')).status_code == 404
        assert (
            await client.get(f'{LINK}/status', headers={'X-Yondo-Link-Poll': token})
        ).status_code == 404  # the deep-link token is not the poll token
        assert api.sent == []


async def test_expired_reused_and_mismatched_challenges(monkeypatch):
    async with bot_client() as (client, app, api):
        token, body = await start(client)
        real_now = telegram_link._now
        monkeypatch.setattr(telegram_link, '_now', lambda: real_now() + timedelta(hours=1))
        assert (await status(client, body['poll_token']))['status'] == 'expired'
        expired = await complete(client, token)
        assert expired.status_code == 410 and expired.json()['code'] == 'telegram_link_expired'
        assert (await complete(client, token)).status_code == 410
        monkeypatch.setattr(telegram_link, '_now', real_now)

        token, body = await start(client)
        mismatch = await complete(client, token, phone='+998909998877')
        assert mismatch.status_code == 409 and mismatch.json()['code'] == 'telegram_phone_mismatch'
        assert (await status(client, body['poll_token']))['status'] == 'failed'
        assert (await complete(client, token)).status_code == 409  # single use

        token, body = await start(client)
        assert (await complete(client, token)).status_code == 200
        retried = await complete(client, token)
        assert retried.status_code == 200 and retried.json() == {'status': 'already_linked'}
        assert len(api.sent) == 1  # a retried completion never sends a second code
        stolen = await complete(client, token, user_id=999)
        assert stolen.status_code == 409 and stolen.json()['code'] == 'telegram_link_used'


async def test_conflicting_telegram_ids_and_relink_of_same_phone():
    async with bot_client() as (client, app, api):
        token, _ = await start(client)
        assert (await complete(client, token, user_id=111)).status_code == 200
        other_phone = '+998935554433'
        token, body = await start(client, other_phone)
        conflict = await complete(client, token, phone=other_phone, user_id=111)
        assert conflict.status_code == 409
        assert conflict.json()['code'] == 'telegram_account_linked_elsewhere'
        assert (await status(client, body['poll_token']))['failure_code'] == (
            'telegram_account_linked_elsewhere'
        )
        # Same phone, verified again from a new Telegram account: the link is replaced.
        async with app.state.db_session_factory() as session:
            challenge = await session.get(OtpChallenge, PHONE)
            challenge.issued_at -= timedelta(minutes=2)  # past the resend cooldown
            await session.commit()
        token, _ = await start(client)
        assert (await complete(client, token, user_id=222)).status_code == 200
        async with app.state.db_session_factory() as session:
            assert (await session.get(TelegramLink, PHONE)).telegram_user_id == 222
        assert api.sent[-1]['chat_id'] == 222


async def test_concurrent_duplicate_completions_send_one_code():
    async with bot_client() as (client, app, api):
        if app.state.db_engine.dialect.name != 'postgresql':
            pytest.skip('native concurrency needs PostgreSQL (SQLite tests share one connection)')
        token, _ = await start(client)
        results = await asyncio.gather(*(complete(client, token) for _ in range(4)))
        assert {r.status_code for r in results} == {200}
        assert len(api.sent) == 1


@pytest.mark.parametrize(
    ('mode', 'code'),
    [
        ('blocked', 'telegram_bot_unreachable'),
        ('timeout', 'otp_delivery_failed'),
        ('malformed', 'otp_delivery_failed'),
        ('server', 'otp_delivery_failed'),
    ],
)
async def test_failed_send_is_not_sent_and_starts_no_cooldown(mode, code, capsys):
    async with bot_client() as (client, app, api):
        api.mode = mode
        token, body = await start(client)
        done = await complete(client, token)
        assert done.status_code == 200 and done.json() == {'status': 'linked'}
        state = await status(client, body['poll_token'])
        assert (state['status'], state['failure_code']) == ('failed', code)
        async with app.state.db_session_factory() as session:
            assert await session.get(OtpChallenge, PHONE) is None  # no code, no cooldown
        retry = await client.post('/api/v1/auth/otp/request', json={'phone_number': PHONE})
        assert retry.json()['code'] == code and TOKEN not in retry.text
        api.mode = 'ok'  # e.g. the user unblocked the bot: works at once (no cooldown)
        ok = await client.post('/api/v1/auth/otp/request', json={'phone_number': PHONE})
        assert ok.status_code == 202 and len(api.sent) == 1
        captured = capsys.readouterr()
        assert TOKEN not in captured.out + captured.err
        assert SECRET not in captured.out + captured.err


async def test_start_rate_limit_and_disabled_bot():
    async with bot_client() as (client, app, api):
        for _ in range(telegram_link.MAX_STARTS_PER_PHONE):
            await start(client)
        limited = await client.post(f'{LINK}/start', json={'phone_number': PHONE})
        assert limited.status_code == 429
        bad = await client.post(f'{LINK}/start', json={'phone_number': '12345'})
        assert bad.status_code == 422 and bad.json()['code'] == 'invalid_phone_number'
    plain = Settings(
        environment='test',
        database_url='sqlite+aiosqlite:///:memory:',
        telegram_gateway_token=None,
    )
    app = create_application(plain)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            assert (await client.get(f'{LINK}/config')).json() == {
                'enabled': False, 'bot_username': None
            }
            for method, path in (('post', '/start'), ('get', '/status'), ('post', '/complete')):
                kwargs = {'json': {}} if method == 'post' else {}
                response = await getattr(client, method)(f'{LINK}{path}', **kwargs)
                assert response.status_code in (422, 503)
            started = await client.post(f'{LINK}/start', json={'phone_number': PHONE})
            assert started.status_code == 503
            assert started.json()['code'] == 'telegram_bot_unavailable'


def test_settings_require_complete_bot_configuration():
    with pytest.raises(ValidationError):
        Settings(otp_provider='telegram_bot', telegram_bot_token=TOKEN, bot_shared_secret=SECRET)
    with pytest.raises(ValidationError):
        Settings(otp_provider='telegram_gateway', telegram_gateway_token=None)
    assert bot_settings(telegram_bot_username='@YondoTestBot').telegram_bot_username == (
        'YondoTestBot'
    )
    assert TOKEN not in repr(bot_settings()) and SECRET not in repr(bot_settings())


@pytest.mark.parametrize('shared', [None, 'x' * 31])
async def test_complete_is_503_without_a_long_enough_shared_secret(shared):
    async with bot_client(bot_settings(bot_shared_secret=shared)) as (client, app, api):
        token, _ = await start(client)
        for secret in (None, shared or ''):
            response = await complete(client, token, secret=secret)
            assert response.status_code == 503
            assert response.json()['code'] == 'telegram_bot_secret_unset'
        assert api.sent == []


async def test_contract_replay_of_the_vps_bot_request():
    """The owner's aiogram bot: exact headers, normalised +998 phone, no redirects followed."""
    async with bot_client() as (client, app, api):
        token, body = await start(client)
        request = dict(
            headers={
                'X-Yondo-Bot-Secret': SECRET,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            content=json.dumps({
                'challenge': token,
                'phone_number': PHONE,
                'telegram_user_id': 424242,
                'telegram_chat_id': 424242,
            }),
            follow_redirects=False,
        )
        first = await client.post('/api/v1/auth/telegram/link/complete', **request)
        assert first.status_code == 200 and first.json() == {'status': 'linked'}
        repeat = await client.post('/api/v1/auth/telegram/link/complete', **request)
        assert repeat.status_code == 200 and repeat.json() == {'status': 'already_linked'}
        assert len(api.sent) == 1
        assert (await status(client, body['poll_token']))['status'] == 'otp_sent'
        # Rejections are 4xx with only a stable code (nothing for the bot to log but the code).
        bad = await client.post(
            '/api/v1/auth/telegram/link/complete',
            **{**request, 'headers': {**request['headers'], 'X-Yondo-Bot-Secret': 'nope'}},
        )
        assert bad.status_code == 401 and set(bad.json()) <= {'code', 'message', 'request_id'}
        assert TOKEN not in bad.text and SECRET not in bad.text
