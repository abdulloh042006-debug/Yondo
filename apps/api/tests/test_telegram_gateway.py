import json
from contextlib import asynccontextmanager

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.providers import DevelopmentOtpProvider, UnconfiguredOtpProvider
from yondo_api.auth.telegram_gateway import TelegramGatewayOtpProvider
from yondo_api.config import Settings
from yondo_api.main import create_application, default_otp_provider
from yondo_api.models.user import User

TOKEN = 'gw_token_' + 'x' * 24
PHONE = '+998901234567'


def gateway(handler, **kwargs):
    return TelegramGatewayOtpProvider(token=TOKEN, transport=httpx.MockTransport(handler), **kwargs)


@pytest.mark.asyncio
async def test_deliver_checks_ability_then_sends_our_code_without_returning_it():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, json.loads(request.content), request.headers))
        if request.url.path.endswith('/checkSendAbility'):
            return httpx.Response(200, json={'ok': True, 'result': {'request_id': 'req_1'}})
        return httpx.Response(200, json={'ok': True, 'result': {'request_id': 'req_1'}})

    delivery = await gateway(handler).deliver(PHONE, '123456')
    assert delivery.development_code is None  # the code never goes back to the browser
    assert [path for path, _, _ in calls] == ['/checkSendAbility', '/sendVerificationMessage']
    assert calls[0][1] == {'phone_number': PHONE}
    assert calls[1][1] == {
        'phone_number': PHONE,
        'code': '123456',
        'ttl': 300,
        'request_id': 'req_1',
    }
    assert all(headers['authorization'] == f'Bearer {TOKEN}' for _, _, headers in calls)


@pytest.mark.asyncio
async def test_number_without_telegram_gets_a_clear_422_and_no_code_is_sent():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={'ok': False, 'error': 'PHONE_NUMBER_NOT_OCCUPIED'})

    with pytest.raises(ApplicationError) as caught:
        await gateway(handler).deliver(PHONE, '123456')
    assert (caught.value.code, caught.value.status_code) == ('otp_telegram_unavailable', 422)
    assert seen == ['/checkSendAbility']


@pytest.mark.asyncio
async def test_every_other_failure_is_a_generic_503():
    def refused_send(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith('/checkSendAbility'):
            return httpx.Response(200, json={'ok': True, 'result': {'request_id': 'r'}})
        return httpx.Response(200, json={'ok': False, 'error': 'BALANCE_NOT_ENOUGH'})

    def server_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text='bad gateway')

    def not_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text='<html>')

    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout('timeout', request=request)

    for handler in (refused_send, server_error, not_json, unreachable):
        with pytest.raises(ApplicationError) as caught:
            await gateway(handler).deliver(PHONE, '123456')
        assert (caught.value.code, caught.value.status_code) == ('otp_delivery_unavailable', 503)


@pytest.mark.asyncio
async def test_failures_never_log_the_code_or_the_phone(caplog):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'ok': False, 'error': 'BALANCE_NOT_ENOUGH'})

    with caplog.at_level('WARNING'), pytest.raises(ApplicationError):
        await gateway(handler).deliver(PHONE, '654321')
    assert caplog.records
    for record in caplog.records:
        text = record.getMessage() + str(getattr(record, 'tg_error', ''))
        assert '654321' not in text and PHONE not in text and TOKEN not in text


def test_settings_validate_the_gateway_url_and_wiring_picks_the_provider():
    base = {'auth_otp_pepper': 'p' * 40}
    configured = {'telegram_gateway_token': SecretStr(TOKEN)}
    with pytest.raises(ValidationError):
        Settings(
            environment='production', **base, **configured, telegram_gateway_api_url='http://x'
        )
    production = default_otp_provider(Settings(environment='production', **base, **configured))
    assert isinstance(production, TelegramGatewayOtpProvider)
    unconfigured = default_otp_provider(Settings(environment='production', **base))
    assert isinstance(unconfigured, UnconfiguredOtpProvider)
    assert isinstance(default_otp_provider(Settings(environment='test')), DevelopmentOtpProvider)
    with_token = default_otp_provider(Settings(environment='test', **configured))
    assert isinstance(with_token, TelegramGatewayOtpProvider)


@asynccontextmanager
async def client_with(provider):
    settings = Settings(
        environment='test',
        database_url='sqlite+aiosqlite:///:memory:',
        redis_url='redis://localhost:6379/15',
        auth_otp_pepper='test-only-auth-pepper-0123456789abcdef',
    )
    app = create_application(settings, otp_provider=provider)
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.begin() as connection:
            await connection.run_sync(User.metadata.create_all)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            yield client


@pytest.mark.asyncio
async def test_login_through_the_real_endpoints_with_a_telegram_delivered_code():
    delivered = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if request.url.path.endswith('/sendVerificationMessage'):
            delivered['code'] = body['code']
        return httpx.Response(200, json={'ok': True, 'result': {'request_id': 'r'}})

    async with client_with(gateway(handler)) as client:
        requested = await client.post('/api/v1/auth/otp/request', json={'phone_number': PHONE})
        assert requested.status_code == 202, requested.text
        assert requested.json().get('development_otp') is None  # nothing on screen
        wrong = await client.post(
            '/api/v1/auth/otp/verify', json={'phone_number': PHONE, 'code': '000000'}
        )
        assert wrong.status_code == 401
        verified = await client.post(
            '/api/v1/auth/otp/verify', json={'phone_number': PHONE, 'code': delivered['code']}
        )
        assert verified.status_code == 200, verified.text
        assert verified.json()['access_token']
