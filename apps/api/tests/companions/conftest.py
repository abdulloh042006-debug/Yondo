import asyncio
import os
import sys
from io import BytesIO
from uuid import UUID

import httpx
import pytest
import pytest_asyncio
from PIL import Image
from sqlalchemy import event, text

from yondo_api.companions.integrations import IdentityStatus
from yondo_api.config import Settings
from yondo_api.db.base import Base
from yondo_api.main import create_application
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType


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


class TestIdentity:
    def __init__(self):
        self.status = IdentityStatus.UNKNOWN

    async def get_status(self, session, user_id):
        return self.status


def png():
    buffer = BytesIO()
    Image.new('RGB', (24, 16), color='red').save(buffer, format='PNG')
    return buffer.getvalue()


async def login(client, app, phone, role=UserRoleType.COMPANION):
    issued = await client.post('/api/v1/auth/otp/request', json={'phone_number': phone})
    response = await client.post(
        '/api/v1/auth/otp/verify',
        json={
            'phone_number': phone,
            'code': issued.json()['development_otp'],
        },
    )
    headers = {'Authorization': f'Bearer {response.json()["access_token"]}'}
    me = (await client.get('/api/v1/auth/me', headers=headers)).json()
    async with app.state.db_session_factory() as session:
        user = await session.get(User, UUID(me['id']))
        user.account_status = AccountStatus.ACTIVE
        session.add(UserRole(user_id=user.id, role=role))
        await session.commit()
    return headers, me['id']


@pytest.fixture(scope='session')
def event_loop_policy():
    # Psycopg async requires the selector loop on the primary Windows dev platform.
    if sys.platform == 'win32':
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture
async def env():
    settings = Settings(
        environment='test',
        database_url=os.environ.get('YONDO_TEST_DATABASE_URL', 'sqlite+aiosqlite:///:memory:'),
    )
    storage, identity = MemoryStorage(), TestIdentity()
    app = create_application(settings, object_storage=storage, identity_eligibility=identity)
    async with app.router.lifespan_context(app):
        engine = app.state.db_engine
        if engine.dialect.name == 'sqlite':

            @event.listens_for(engine.sync_engine, 'connect')
            def foreign_keys(connection, _):
                connection.execute('PRAGMA foreign_keys=ON')

            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        else:
            # Explicit opt-in test database only; migrated schema must already exist.
            async with engine.begin() as connection:
                await connection.execute(text('TRUNCATE users CASCADE'))
                await connection.execute(text('TRUNCATE otp_challenges'))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            owner, owner_id = await login(client, app, '901000001')
            other, other_id = await login(client, app, '901000002')
            customer, _ = await login(client, app, '901000003', UserRoleType.CUSTOMER)
            admin, _ = await login(client, app, '901000004', UserRoleType.ADMIN)
            yield {
                'client': client,
                'app': app,
                'owner': owner,
                'owner_id': owner_id,
                'other': other,
                'other_id': other_id,
                'customer': customer,
                'admin': admin,
                'storage': storage,
                'identity': identity,
            }


async def create_profile(env, headers=None):
    headers = headers or env['owner']
    client = env['client']
    application = await client.post('/api/v1/companions/me/application', json={}, headers=headers)
    assert application.status_code == 201, application.text
    profile = await client.post(
        '/api/v1/companions/me/profile',
        headers=headers,
        json={
            'display_name': 'Test companion',
            'bio': 'Coffee and walks',
            'languages': ['uz', 'en'],
            'interests': ['Reading'],
        },
    )
    assert profile.status_code == 201, profile.text
    return application.json(), profile.json()


@pytest_asyncio.fixture
async def prepared(env):
    application, profile = await create_profile(env)
    env.update(application=application, profile=profile)
    return env


async def approve(env):
    client, owner, admin = env['client'], env['owner'], env['admin']
    root = '/api/v1/companions'
    assert (await client.post(f'{root}/me/application/submit', headers=owner)).status_code == 200
    assert (
        await client.post(
            f'{root}/admin/applications/{env["application"]["id"]}/decision',
            headers=admin,
            json={
                'expected_revision': (
                    await client.get(f'{root}/me/application', headers=owner)
                ).json()['revision'],
                'decision': 'approve',
                'note': 'Application checked',
            },
        )
    ).status_code == 200
    assert (await client.post(f'{root}/me/profile/submit', headers=owner)).status_code == 200
    assert (
        await client.post(
            f'{root}/admin/profiles/{env["profile"]["id"]}/decision',
            headers=admin,
            json={
                'expected_revision': (
                    await client.get(
                        f'{root}/admin/users/{env["owner_id"]}/content-review', headers=admin
                    )
                ).json()['profile']['revision'],
                'decision': 'approve',
                'note': 'Content checked',
            },
        )
    ).status_code == 200
