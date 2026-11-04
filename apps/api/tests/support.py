"""Shared test helpers for marketplace domains."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from io import BytesIO
from uuid import UUID

import httpx
from PIL import Image
from sqlalchemy import event, text

from yondo_api.companions.integrations import IdentityStatus
from yondo_api.config import Settings
from yondo_api.db.base import Base
from yondo_api.main import create_application
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType

API = '/api/v1'


class MemoryStorage:
    def __init__(self):
        self.objects = {}

    async def upload(self, key, content, content_type):
        self.objects[key] = (b''.join([chunk async for chunk in content]), content_type)

    async def create_download_url(self, key, expires_in_seconds=300):
        assert key in self.objects
        return f'https://storage.test/private/{key}?expires={expires_in_seconds}'

    async def delete(self, key):
        self.objects.pop(key, None)


class PerUserIdentity:
    """Identity adapter whose verified users are controlled by the test."""

    def __init__(self):
        self.statuses: dict[UUID, IdentityStatus] = {}

    async def get_status(self, session, user_id):
        return self.statuses.get(UUID(str(user_id)), IdentityStatus.UNKNOWN)

    async def verified_user_ids(self, session, user_ids):
        return {
            user_id for user_id in user_ids if self.statuses.get(user_id) == IdentityStatus.VERIFIED
        }


def png(width=24, height=16, color='red'):
    buffer = BytesIO()
    Image.new('RGB', (width, height), color=color).save(buffer, format='PNG')
    return buffer.getvalue()


def database_url_for_tests() -> str:
    return os.environ.get('YONDO_TEST_DATABASE_URL', 'sqlite+aiosqlite:///:memory:')


async def reset_database(engine) -> None:
    if engine.dialect.name == 'sqlite':

        @event.listens_for(engine.sync_engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    else:
        async with engine.begin() as connection:
            await connection.execute(text('TRUNCATE users CASCADE'))
            await connection.execute(text('TRUNCATE otp_challenges'))


@asynccontextmanager
async def running_app(identity=None, storage=None, **settings_overrides):
    settings = Settings(
        environment='test',
        database_url=database_url_for_tests(),
        **settings_overrides,
    )
    app = create_application(
        settings,
        object_storage=storage if storage is not None else MemoryStorage(),
        identity_eligibility=identity,
    )
    async with app.router.lifespan_context(app):
        await reset_database(app.state.db_engine)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            yield app, client


async def sign_in(client, phone: str) -> tuple[dict[str, str], str]:
    issued = await client.post(f'{API}/auth/otp/request', json={'phone_number': phone})
    assert issued.status_code == 202, issued.text
    verified = await client.post(
        f'{API}/auth/otp/verify',
        json={'phone_number': phone, 'code': issued.json()['development_otp']},
    )
    assert verified.status_code == 200, verified.text
    headers = {'Authorization': f'Bearer {verified.json()["access_token"]}'}
    me = await client.get(f'{API}/auth/me', headers=headers)
    return headers, me.json()['id']


async def create_user(
    app,
    client,
    phone: str,
    roles=(UserRoleType.CUSTOMER,),
    *,
    name: str | None = None,
    age: int = 25,
    gender: str = 'female',
    city: str = 'Tashkent',
) -> tuple[dict[str, str], UUID]:
    headers, user_id = await sign_in(client, phone)
    profile = await client.put(
        f'{API}/auth/profile',
        headers=headers,
        json={
            'display_name': name or f'User {phone[-4:]}',
            'age': age,
            'gender': gender,
            'city': city,
        },
    )
    assert profile.status_code == 200, profile.text
    async with app.state.db_session_factory() as session:
        for role in roles:
            session.add(UserRole(user_id=UUID(user_id), role=role))
        user = await session.get(User, UUID(user_id))
        if UserRoleType.ADMIN in roles:
            user.account_status = AccountStatus.ACTIVE
        await session.commit()
    return headers, UUID(user_id)
