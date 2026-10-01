from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from yondo_api.auth import service
from yondo_api.auth.providers import DevelopmentOtpProvider
from yondo_api.config import Settings
from yondo_api.main import create_application
from yondo_api.models.auth import AuthSession, OtpChallenge
from yondo_api.models.user import User


@asynccontextmanager
async def make_client(environment: str = 'test', otp_provider=None):
    settings = Settings(
        environment=environment,
        database_url='sqlite+aiosqlite:///:memory:',
        redis_url='redis://localhost:6379/15',
        auth_otp_pepper='test-only-auth-pepper-0123456789abcdef',
    )
    app = create_application(settings, otp_provider=otp_provider)
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.begin() as connection:
            await connection.run_sync(User.metadata.create_all)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            yield client, app


@pytest_asyncio.fixture
async def auth_client():
    async with make_client(otp_provider=DevelopmentOtpProvider()) as result:
        yield result


async def request_code(client):
    return await client.post('/api/v1/auth/otp/request', json={'phone_number': '901234567'})


def wrong_code_for(code: str) -> str:
    return '000000' if code != '000000' else '000001'


@pytest.mark.asyncio
async def test_otp_request_and_valid_verification_create_user_and_tokens(auth_client):
    client, _ = auth_client
    response = await request_code(client)
    assert response.status_code == 202
    body = response.json()
    assert body['expires_in_seconds'] == 300
    assert body['resend_after_seconds'] == 60
    assert len(body['development_otp']) == 6

    verified = await client.post(
        '/api/v1/auth/otp/verify',
        json={'phone_number': '+998 (90) 123-45-67', 'code': body['development_otp']},
    )
    assert verified.status_code == 200
    tokens = verified.json()
    assert tokens['token_type'] == 'bearer'
    assert tokens['expires_in'] == 900
    assert len(tokens['access_token']) >= 40
    assert len(tokens['refresh_token']) >= 40

    profile = await client.get(
        '/api/v1/auth/me', headers={'Authorization': f"Bearer {tokens['access_token']}"}
    )
    assert profile.status_code == 200
    assert profile.json()['phone_number'] == '+998901234567'


@pytest.mark.asyncio
async def test_otp_hash_is_stored_instead_of_code(auth_client):
    client, app = auth_client
    response = await request_code(client)
    code = response.json()['development_otp']
    async with app.state.db_session_factory() as session:
        challenge = await session.get(OtpChallenge, '+998901234567')
        assert challenge is not None
        assert isinstance(challenge.code_hash, bytes)
        assert code.encode() not in challenge.code_hash


@pytest.mark.asyncio
async def test_invalid_otp_is_rejected(auth_client):
    client, _ = auth_client
    issued = await request_code(client)
    response = await client.post(
        '/api/v1/auth/otp/verify',
        json={
            'phone_number': '901234567',
            'code': wrong_code_for(issued.json()['development_otp']),
        },
    )
    assert response.status_code == 401
    assert response.json()['code'] == 'invalid_otp'


@pytest.mark.asyncio
async def test_expired_otp_is_rejected(auth_client, monkeypatch):
    client, _ = auth_client
    response = await request_code(client)
    code = response.json()['development_otp']
    issued_at = service._now()
    monkeypatch.setattr(service, '_now', lambda: issued_at + timedelta(minutes=6))
    verified = await client.post(
        '/api/v1/auth/otp/verify',
        json={'phone_number': '901234567', 'code': code},
    )
    assert verified.status_code == 401
    assert verified.json()['code'] == 'otp_expired'


@pytest.mark.asyncio
async def test_three_failed_attempts_lock_for_60_seconds(auth_client, monkeypatch):
    client, _ = auth_client
    issued = await request_code(client)
    correct_code = issued.json()['development_otp']
    wrong_code = wrong_code_for(correct_code)
    for _ in range(3):
        response = await client.post(
            '/api/v1/auth/otp/verify',
            json={'phone_number': '901234567', 'code': wrong_code},
        )
        assert response.status_code == 401

    blocked = await client.post(
        '/api/v1/auth/otp/verify',
        json={'phone_number': '901234567', 'code': correct_code},
    )
    assert blocked.status_code == 429
    assert blocked.json()['code'] == 'otp_temporarily_blocked'

    blocked_at = service._now()
    monkeypatch.setattr(service, '_now', lambda: blocked_at + timedelta(seconds=60))
    unblocked = await client.post(
        '/api/v1/auth/otp/verify',
        json={'phone_number': '901234567', 'code': correct_code},
    )
    assert unblocked.status_code == 200


@pytest.mark.asyncio
async def test_resend_cooldown(auth_client):
    client, _ = auth_client
    await request_code(client)
    response = await client.post(
        '/api/v1/auth/otp/request', json={'phone_number': '+998901234567'}
    )
    assert response.status_code == 429
    assert response.json()['code'] == 'otp_resend_cooldown'


@pytest.mark.asyncio
async def test_new_otp_invalidates_previous_code(auth_client, monkeypatch):
    client, _ = auth_client
    first = await request_code(client)
    first_code = first.json()['development_otp']
    issued_at = service._now()
    monkeypatch.setattr(service, '_now', lambda: issued_at + timedelta(seconds=61))
    second = await client.post(
        '/api/v1/auth/otp/request', json={'phone_number': '+998 90 123 45 67'}
    )
    second_code = second.json()['development_otp']
    assert second_code != first_code

    invalidated = await client.post(
        '/api/v1/auth/otp/verify',
        json={'phone_number': '901234567', 'code': first_code},
    )
    assert invalidated.status_code == 401
    verified = await client.post(
        '/api/v1/auth/otp/verify',
        json={'phone_number': '998901234567', 'code': second_code},
    )
    assert verified.status_code == 200


@pytest.mark.asyncio
async def test_normalized_phone_is_unique_and_success_consumes_otp(auth_client):
    client, app = auth_client
    issued = await client.post(
        '/api/v1/auth/otp/request', json={'phone_number': '90-123-45-67'}
    )
    response = await client.post(
        '/api/v1/auth/otp/verify',
        json={
            'phone_number': '00998 90 123 45 67',
            'code': issued.json()['development_otp'],
        },
    )
    assert response.status_code == 200
    async with app.state.db_session_factory() as session:
        users = await session.scalars(select(User))
        assert len(list(users)) == 1
        assert await session.get(OtpChallenge, '+998901234567') is None
        sessions = await session.scalars(select(AuthSession))
        assert len(list(sessions)) == 1


@pytest.mark.asyncio
async def test_production_never_exposes_development_otp():
    async with make_client(
        environment='production', otp_provider=DevelopmentOtpProvider()
    ) as (client, _):
        response = await request_code(client)
    assert response.status_code == 202
    assert 'development_otp' not in response.json()


@pytest.mark.asyncio
async def test_production_without_provider_returns_unavailable():
    async with make_client(environment='production') as (client, _):
        response = await request_code(client)
    assert response.status_code == 503
    assert response.json()['code'] == 'otp_delivery_unavailable'


@pytest.mark.asyncio
async def test_refresh_rotates_tokens_and_logout_revokes_session(auth_client):
    client, _ = auth_client
    issued = await request_code(client)
    tokens = await client.post(
        '/api/v1/auth/otp/verify',
        json={'phone_number': '901234567', 'code': issued.json()['development_otp']},
    )
    token_data = tokens.json()
    refreshed = await client.post(
        '/api/v1/auth/refresh', json={'refresh_token': token_data['refresh_token']}
    )
    assert refreshed.status_code == 200
    rotated = refreshed.json()
    assert rotated['access_token'] != token_data['access_token']
    assert rotated['refresh_token'] != token_data['refresh_token']

    old_refresh = await client.post(
        '/api/v1/auth/refresh', json={'refresh_token': token_data['refresh_token']}
    )
    assert old_refresh.status_code == 401
    logout = await client.post(
        '/api/v1/auth/logout',
        headers={'Authorization': f"Bearer {rotated['access_token']}"},
    )
    assert logout.status_code == 204
    me = await client.get(
        '/api/v1/auth/me',
        headers={'Authorization': f"Bearer {rotated['access_token']}"},
    )
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_profile_and_role_selection_require_authentication(auth_client):
    client, _ = auth_client
    issued = await request_code(client)
    tokens = await client.post(
        '/api/v1/auth/otp/verify',
        json={'phone_number': '901234567', 'code': issued.json()['development_otp']},
    )
    headers = {'Authorization': f"Bearer {tokens.json()['access_token']}"}

    profile = await client.put(
        '/api/v1/auth/profile',
        json={'age': 30, 'gender': 'unspecified', 'city': 'Tashkent'},
        headers=headers,
    )
    assert profile.status_code == 200
    assert profile.json()['age'] == 30
    assert profile.json()['city'] == 'Tashkent'

    roles = await client.put(
        '/api/v1/auth/roles',
        json={'roles': ['customer', 'companion']},
        headers=headers,
    )
    assert roles.status_code == 200
    assert set(roles.json()) == {'customer', 'companion'}

    admin = await client.put(
        '/api/v1/auth/roles', json={'roles': ['admin']}, headers=headers
    )
    assert admin.status_code == 403
