"""OTP limits and the client-IP key (owner, 2026-11-19; docs/client-ip.md)."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from yondo_api.auth import service
from yondo_api.auth.providers import DevelopmentOtpProvider
from yondo_api.config import Settings
from yondo_api.main import create_application
from yondo_api.models.user import User

OTP = '/api/v1/auth/otp/request'


@asynccontextmanager
async def make_client(peer=('127.0.0.1', 1234), **extra):
    settings = Settings(
        environment='test',
        database_url='sqlite+aiosqlite:///:memory:',
        redis_url='redis://localhost:6379/15',
        auth_otp_pepper='test-only-auth-pepper-0123456789abcdef',
        telegram_gateway_token=None,
        **extra,
    )
    app = create_application(settings, otp_provider=DevelopmentOtpProvider())
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.begin() as connection:
            await connection.run_sync(User.metadata.create_all)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=peer), base_url='http://test'
        ) as client:
            yield client, app


class Clock:
    def __init__(self, monkeypatch):
        self.now = datetime(2026, 11, 19, 8, 0, tzinfo=UTC)
        monkeypatch.setattr(service, '_now', lambda: self.now)

    def advance(self, **kw):
        self.now += timedelta(**kw)


@pytest.mark.asyncio
async def test_five_codes_per_hour_per_phone(monkeypatch):
    clock = Clock(monkeypatch)
    async with make_client() as (client, _app):
        for _ in range(5):
            assert (await client.post(OTP, json={'phone_number': '901110001'})).status_code == 202
            clock.advance(seconds=61)  # past the resend cooldown
        sixth = await client.post(OTP, json={'phone_number': '901110001'})
        assert sixth.status_code == 429 and sixth.json()['code'] == 'otp_hourly_limit'
        # Another number is not affected.
        assert (await client.post(OTP, json={'phone_number': '901110002'})).status_code == 202
        clock.advance(minutes=60)
        assert (await client.post(OTP, json={'phone_number': '901110001'})).status_code == 202


@pytest.mark.asyncio
async def test_ten_codes_per_day_per_phone(monkeypatch):
    clock = Clock(monkeypatch)
    # The per-IP limit runs on real time; switch it off here to count the per-phone limit only.
    async with make_client(auth_otp_ip_rate_limit_per_minute=0) as (client, _app):
        statuses = []
        for _ in range(11):
            response = await client.post(OTP, json={'phone_number': '901110003'})
            statuses.append(response.json().get('code', response.status_code))
            clock.advance(minutes=13)  # 4-5 per hour: under the hourly limit
        assert statuses[:10] == [202] * 10
        assert statuses[10] == 'otp_daily_limit'
        clock.advance(hours=24)
        assert (await client.post(OTP, json={'phone_number': '901110003'})).status_code == 202


@pytest.mark.asyncio
async def test_code_requests_are_limited_per_ip(monkeypatch):
    Clock(monkeypatch)
    async with make_client(auth_otp_ip_rate_limit_per_minute=2) as (client, app):
        app.state.otp_ip_limiter.clock = lambda: 1_800_000_000.0  # one fixed minute
        codes = []
        for n in range(3):
            response = await client.post(OTP, json={'phone_number': f'90111001{n}'})
            codes.append(response.json().get('code', response.status_code))
        assert codes == [202, 202, 'rate_limited']


def limiter_ips(app) -> set[str]:
    return {key[1] for key in app.state.otp_ip_limiter._counts}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('mode', 'peer', 'headers', 'expected'),
    [
        # Default: no header is ever trusted.
        ('peer', ('10.0.0.5', 1), {'x-forwarded-for': '6.6.6.6'}, '10.0.0.5'),
        # X-Forwarded-For from a trusted proxy: only the entry the proxy appended counts; a value
        # the client wrote on the left (forged) is ignored.
        ('xff', ('10.0.0.5', 1), {'x-forwarded-for': '6.6.6.6, 203.0.113.9'}, '203.0.113.9'),
        # The same forged header straight from the internet (untrusted peer): ignored.
        ('xff', ('198.51.100.7', 1), {'x-forwarded-for': '6.6.6.6'}, '198.51.100.7'),
        # Garbage in the header: fall back to the peer.
        ('xff', ('10.0.0.5', 1), {'x-forwarded-for': 'not-an-ip'}, '10.0.0.5'),
    ],
)
async def test_forged_forwarded_for_does_not_change_the_limiter_key(
    monkeypatch, mode, peer, headers, expected
):
    Clock(monkeypatch)
    async with make_client(peer=peer, client_ip_mode=mode) as (client, app):
        await client.post(OTP, json={'phone_number': '901110020'}, headers=headers)
        assert limiter_ips(app) == {expected}


@pytest.mark.asyncio
async def test_header_mode_only_from_a_trusted_proxy(monkeypatch):
    Clock(monkeypatch)
    extra = {'client_ip_mode': 'header', 'client_ip_header': 'true-client-ip'}
    async with make_client(peer=('10.1.2.3', 1), **extra) as (client, app):
        await client.post(
            OTP, json={'phone_number': '901110030'}, headers={'true-client-ip': '203.0.113.5'}
        )
        assert limiter_ips(app) == {'203.0.113.5'}
    async with make_client(peer=('198.51.100.8', 1), **extra) as (client, app):
        await client.post(
            OTP, json={'phone_number': '901110031'}, headers={'true-client-ip': '6.6.6.6'}
        )
        assert limiter_ips(app) == {'198.51.100.8'}


def test_header_mode_needs_a_header_name():
    with pytest.raises(ValueError):
        Settings(environment='test', client_ip_mode='header', client_ip_header='')
