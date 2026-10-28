from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from yondo_api.api.errors import ApplicationError
from yondo_api.auth import service
from yondo_api.auth.providers import (
    DevelopmentOtpProvider,
    OtpDelivery,
    UnconfiguredOtpProvider,
    otp_channel_unavailable,
    otp_delivery_failed,
)
from yondo_api.auth.telegram_gateway import TelegramGatewayOtpProvider
from yondo_api.config import Settings
from yondo_api.main import create_application, select_otp_provider
from yondo_api.models.auth import OtpChallenge
from yondo_api.models.user import User

PEPPER = 'test-only-auth-pepper-0123456789abcdef'
PHONE = '+998901234567'


def make_settings(environment: str = 'test', **overrides) -> Settings:
    return Settings(
        _env_file=None,
        environment=environment,
        database_url='sqlite+aiosqlite:///:memory:',
        redis_url='redis://localhost:6379/15',
        auth_otp_pepper=PEPPER,
        **{'telegram_gateway_token': None, **overrides},
    )


@asynccontextmanager
async def make_client(settings: Settings | None = None, otp_provider=None):
    app = create_application(settings or make_settings(), otp_provider=otp_provider)
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.begin() as connection:
            await connection.run_sync(User.metadata.create_all)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            yield client, app


class FakeProvider:
    """Records every call; raises `error` when set, otherwise reports a Telegram delivery."""

    def __init__(self, error: ApplicationError | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    async def deliver(self, phone_number: str, code: str) -> OtpDelivery:
        self.calls.append((phone_number, code))
        if self.error is not None:
            raise self.error
        return OtpDelivery(channel='telegram')


async def request_code(client):
    return await client.post('/api/v1/auth/otp/request', json={'phone_number': '901234567'})


async def challenge_count(app) -> int:
    async with app.state.db_session_factory() as session:
        return await session.scalar(select(func.count()).select_from(OtpChallenge))


@pytest.mark.asyncio
async def test_default_development_response_is_unchanged_and_has_no_delivery_channel():
    async with make_client(otp_provider=DevelopmentOtpProvider()) as (client, _):
        response = await request_code(client)
    assert response.status_code == 202
    body = response.json()
    assert set(body) == {'message', 'expires_in_seconds', 'resend_after_seconds', 'development_otp'}
    assert len(body['development_otp']) == 6
    assert 'delivery_channel' not in body


@pytest.mark.asyncio
async def test_default_provider_for_test_environment_is_development_provider():
    async with make_client() as (client, app):
        assert isinstance(app.state.otp_provider, DevelopmentOtpProvider)
        response = await request_code(client)
    assert 'delivery_channel' not in response.json()


@pytest.mark.asyncio
async def test_telegram_delivery_reports_channel_without_leaking_the_code():
    provider = FakeProvider()
    async with make_client(otp_provider=provider) as (client, app):
        response = await request_code(client)
        assert response.status_code == 202
        body = response.json()
        assert body['delivery_channel'] == 'telegram'
        assert 'development_otp' not in body
        assert body['expires_in_seconds'] == 300
        assert body['resend_after_seconds'] == 60

        assert [phone for phone, _ in provider.calls] == [PHONE]
        code = provider.calls[0][1]
        assert code not in response.text
        async with app.state.db_session_factory() as session:
            challenge = await session.get(OtpChallenge, PHONE)
            assert challenge is not None
            assert challenge.code_hash == service._otp_hash(app.state.settings, PHONE, code)

        verified = await client.post(
            '/api/v1/auth/otp/verify', json={'phone_number': PHONE, 'code': code}
        )
        assert verified.status_code == 200
        assert verified.json()['token_type'] == 'bearer'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('error', 'status_code', 'code'),
    [
        (otp_channel_unavailable(), 422, 'otp_channel_unavailable'),
        (otp_delivery_failed(), 502, 'otp_delivery_failed'),
    ],
)
async def test_failed_delivery_writes_no_challenge_and_starts_no_cooldown(
    error, status_code, code
):
    assert (error.status_code, error.code) == (status_code, code)
    provider = FakeProvider(error=error)
    async with make_client(otp_provider=provider) as (client, app):
        first = await request_code(client)
        assert first.status_code == status_code
        assert first.json()['code'] == code
        assert await challenge_count(app) == 0

        # No resend cooldown: the very next request reaches the provider again.
        second = await request_code(client)
        assert second.status_code == status_code
        assert second.json()['code'] == code
        assert len(provider.calls) == 2
        assert await challenge_count(app) == 0

        # Once the provider recovers, the same phone can get a code straight away.
        provider.error = None
        third = await request_code(client)
        assert third.status_code == 202
        assert third.json()['delivery_channel'] == 'telegram'
        assert await challenge_count(app) == 1


@pytest.mark.asyncio
async def test_failed_redelivery_keeps_the_previous_challenge_untouched(monkeypatch):
    provider = FakeProvider()
    async with make_client(otp_provider=provider) as (client, app):
        assert (await request_code(client)).status_code == 202
        first_code = provider.calls[0][1]
        async with app.state.db_session_factory() as session:
            before = await session.get(OtpChallenge, PHONE)
            issued_at, code_hash = before.issued_at, before.code_hash

        issued_now = service._now()
        monkeypatch.setattr(service, '_now', lambda: issued_now + timedelta(seconds=61))
        provider.error = otp_delivery_failed()
        failed = await request_code(client)
        assert failed.status_code == 502

        async with app.state.db_session_factory() as session:
            after = await session.get(OtpChallenge, PHONE)
            assert (after.issued_at, after.code_hash) == (issued_at, code_hash)
        verified = await client.post(
            '/api/v1/auth/otp/verify', json={'phone_number': PHONE, 'code': first_code}
        )
        assert verified.status_code == 200


@pytest.mark.asyncio
async def test_unconfigured_production_like_settings_return_503_without_a_challenge():
    settings = make_settings(environment='production')
    async with make_client(settings) as (client, app):
        assert isinstance(app.state.otp_provider, UnconfiguredOtpProvider)
        response = await request_code(client)
        assert response.status_code == 503
        assert response.json()['code'] == 'otp_delivery_unavailable'
        assert await challenge_count(app) == 0


@pytest.mark.parametrize('environment', ['development', 'test', 'staging', 'production'])
def test_configured_token_selects_telegram_gateway_in_every_environment(environment):
    settings = make_settings(environment, telegram_gateway_token='123:test-token')
    assert isinstance(select_otp_provider(settings), TelegramGatewayOtpProvider)


@pytest.mark.parametrize(
    ('environment', 'expected'),
    [
        ('development', DevelopmentOtpProvider),
        ('test', DevelopmentOtpProvider),
        ('staging', UnconfiguredOtpProvider),
        ('production', UnconfiguredOtpProvider),
    ],
)
def test_without_token_selection_falls_back_by_environment(environment, expected):
    assert type(select_otp_provider(make_settings(environment))) is expected


def test_empty_token_means_not_configured():
    settings = make_settings(telegram_gateway_token='')
    assert settings.telegram_gateway_token is None
    assert isinstance(select_otp_provider(settings), DevelopmentOtpProvider)


@pytest.mark.asyncio
async def test_application_uses_telegram_provider_when_token_is_set():
    settings = make_settings(telegram_gateway_token='123:test-token')
    async with make_client(settings) as (_, app):
        assert isinstance(app.state.otp_provider, TelegramGatewayOtpProvider)


@pytest.mark.asyncio
async def test_explicit_provider_argument_beats_configured_token():
    provider = FakeProvider()
    settings = make_settings(telegram_gateway_token='123:test-token')
    async with make_client(settings, otp_provider=provider) as (_, app):
        assert app.state.otp_provider is provider


def test_telegram_gateway_settings_defaults_and_secrecy():
    settings = make_settings(telegram_gateway_token='123:very-secret')
    assert settings.telegram_gateway_base_url == 'https://gatewayapi.telegram.org'
    assert settings.telegram_gateway_timeout_seconds == 10.0
    assert 'very-secret' not in repr(settings)
    assert 'very-secret' not in str(settings.telegram_gateway_token)
    assert make_settings().telegram_gateway_token is None


def test_telegram_gateway_settings_are_validated():
    with pytest.raises(ValidationError):
        make_settings(telegram_gateway_token='123:t', telegram_gateway_timeout_seconds=0)
    with pytest.raises(ValidationError, match='https'):
        make_settings(
            telegram_gateway_token='123:t', telegram_gateway_base_url='http://gateway.example'
        )
