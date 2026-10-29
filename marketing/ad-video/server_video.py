"""End-to-end test backend: the REAL Yondo FastAPI app on a throw-away SQLite file.

TEST DOUBLES (never used outside this script, and only because no external service exists here):
  * object storage  -> in-memory (photos cannot be uploaded to MinIO in this environment)
  * identity check  -> always "verified" (the real provider is not integrated yet)
  * OTP delivery    -> the development provider, which returns the code in the response

Everything else (authz, state machines, audit trail, discovery rules) is the production code.
Seed data is labelled "DEMO". This verifies behaviour on SQLite, NOT on PostgreSQL.

Usage: python server.py <port> <sqlite-file>
"""

import asyncio
import os
import sys
from uuid import UUID

import httpx
import uvicorn
from sqlalchemy import select

from yondo_api.auth.providers import DevelopmentOtpProvider
from yondo_api.companions.integrations import IdentityStatus
from yondo_api.config import Settings
from yondo_api.db.base import Base
from yondo_api.main import create_application
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DB = sys.argv[2] if len(sys.argv) > 2 else 'e2e.db'

ADMIN = '+998901110001'
CUSTOMER = '+998901110003'
PENDING_USER = '+998901110004'
OTHER_ADMIN_TARGET = '+998901110005'


class MemoryStorage:
    def __init__(self):
        self.objects = {}

    async def upload(self, key, content, content_type):
        self.objects[key] = (b''.join([chunk async for chunk in content]), content_type)

    async def create_download_url(self, key, expires_in_seconds=300):
        return f'http://127.0.0.1:{PORT}/__test_storage/{key}'

    async def delete(self, key):
        self.objects.pop(key, None)


class AlwaysVerified:
    async def get_status(self, session, user_id):
        return IdentityStatus.VERIFIED


async def login(client, phone):
    issued = await client.post('/api/v1/auth/otp/request', json={'phone_number': phone})
    verified = await client.post(
        '/api/v1/auth/otp/verify',
        json={'phone_number': phone, 'code': issued.json()['development_otp']},
    )
    headers = {'Authorization': f'Bearer {verified.json()["access_token"]}'}
    me = (await client.get('/api/v1/auth/me', headers=headers)).json()
    return headers, me['id']


async def set_user(app, user_id, roles, status=AccountStatus.ACTIVE, city='Toshkent', age=27):
    async with app.state.db_session_factory() as session:
        user = await session.get(User, UUID(user_id))
        user.account_status = status
        user.city = city
        user.age = age
        existing = set(await session.scalars(select(UserRole.role).where(UserRole.user_id == user.id)))
        for role in roles:
            if role not in existing:
                session.add(UserRole(user_id=user.id, role=role))
        await session.commit()


async def seed(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://seed') as client:
        admin, admin_id = await login(client, ADMIN)
        await set_user(app, admin_id, [UserRoleType.ADMIN], age=40)
        customer, customer_id = await login(client, CUSTOMER)
        await set_user(app, customer_id, [UserRoleType.CUSTOMER])
        _, pending_id = await login(client, PENDING_USER)
        await set_user(app, pending_id, [UserRoleType.CUSTOMER], status=AccountStatus.VERIFICATION_PENDING)
        _, target_id = await login(client, OTHER_ADMIN_TARGET)
        await set_user(app, target_id, [UserRoleType.CUSTOMER])

        async def companion(phone, name, bio, price, approve_all, city='Toshkent'):
            headers, uid = await login(client, phone)
            await set_user(app, uid, [UserRoleType.COMPANION], city=city, age=26)
            base = '/api/v1/companions'
            app_row = (await client.post(f'{base}/me/application', json={'statement': f'{name}: ariza matni'}, headers=headers)).json()
            profile = (await client.post(
                f'{base}/me/profile',
                headers=headers,
                json={'display_name': name, 'bio': bio, 'languages': ['uz', 'ru'], 'interests': ['Kitob', 'Sayr']},
            )).json()
            await client.post(f'{base}/me/services', headers=headers, json={'service_code': 'coffee', 'price_minor': price, 'currency': 'UZS', 'unit_minutes': 60, 'description': 'Kafe yoki parkda suhbat'})
            await client.post(f'{base}/me/services', headers=headers, json={'service_code': 'walking', 'price_minor': price // 2, 'currency': 'UZS', 'unit_minutes': 30, 'description': ''})
            # illustrated profile pictures (PHOTOS_DIR/<name>-N.jpg), uploaded through the real photo endpoint
            pdir = os.environ.get('PHOTOS_DIR')
            if pdir:
                for f in sorted(os.listdir(pdir)):
                    if f.startswith(name.lower() + '-') and f.endswith('.jpg'):
                        with open(os.path.join(pdir, f), 'rb') as fh:
                            up = await client.post(f'{base}/me/photos', headers={**headers, 'content-type': 'image/jpeg'}, content=fh.read())
                        print('PHOTO', name, f, up.status_code, flush=True)
            await client.post(f'{base}/me/application/submit', headers=headers)
            if approve_all:
                rev = (await client.get(f'{base}/me/application', headers=headers)).json()['revision']
                await client.post(f'{base}/admin/applications/{app_row["id"]}/decision', headers=admin, json={'decision': 'approve', 'expected_revision': rev, 'note': 'ariza tekshirildi'})
                await client.post(f'{base}/me/profile/submit', headers=headers)
                review = (await client.get(f'{base}/admin/users/{uid}/content-review', headers=admin)).json()
                await client.post(f'{base}/admin/profiles/{profile["id"]}/decision', headers=admin, json={'decision': 'approve', 'expected_revision': review['profile']['revision'], 'note': 'kontent tekshirildi'})
                await client.post(f'{base}/me/activate', headers=headers)
            else:
                await client.post(f'{base}/me/profile/submit', headers=headers)
            return headers, uid, profile['id']

        _, _, madina_profile = await companion('+998901110011', 'Madina', 'shahar bo‘ylab sayr va kofe suhbati.', 15000000, True)
        await companion('+998901110012', 'Jasur', 'kitoblar va kino haqida suhbat.', 9000000, True, city='Samarqand')
        await companion('+998901110013', 'Sevara', 'tasdiq kutilmoqda.', 12000000, False)

        # A booking + a safety report so the admin safety queue has a real record to review.
        services = (await client.get(f'/api/v1/discovery/companions/{madina_profile}')).json()['services']
        from datetime import UTC, datetime, timedelta

        # Make Madina bookable: availability must cover the booking.
        mh, _ = await login(client, '+998901110011')
        # daytime slot for the video: day+2 (UTC date) 10:00 Tashkent = 05:00 UTC; availability 09:00-16:00 Tashkent
        start = (datetime.now(UTC) + timedelta(days=2)).replace(hour=5, minute=0, second=0, microsecond=0)
        await client.post('/api/v1/companions/me/availability', headers=mh, json={
            'starts_at': (start - timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
            'ends_at': (start + timedelta(hours=6)).isoformat().replace('+00:00', 'Z'),
            'timezone': 'Asia/Tashkent'})
        booked = await client.post('/api/v1/bookings', headers=customer, json={
            'service_id': services[0]['id'],
            'starts_at': start.isoformat().replace('+00:00', 'Z'),
            'duration_minutes': 60, 'meeting_place': 'Magic City kafesi', 'timezone': 'Asia/Tashkent'})
        madina_user = (await client.get(f'/api/v1/discovery/companions/{madina_profile}')).json()
        await client.post('/api/v1/safety/reports', headers=customer, json={
            'reported_user_id': await _user_of_profile(app, madina_profile),
            'booking_id': booked.json().get('id'),
            'category': 'unsafe_behavior',
            'description': 'ko‘rib chiqish uchun namunaviy yozuv.'})
        _ = madina_user


async def _user_of_profile(app, profile_id):
    from yondo_api.companions.models import CompanionApplication, CompanionProfile

    async with app.state.db_session_factory() as session:
        profile = await session.get(CompanionProfile, UUID(profile_id))
        application = await session.get(CompanionApplication, profile.application_id)
        return str(application.user_id)


async def main():
    settings = Settings(environment='test', database_url=f'sqlite+aiosqlite:///{DB}')
    store = MemoryStorage()
    # Pinned: the seeding below logs in with `development_otp`; a stray Telegram token must not change that.
    app = create_application(
        settings,
        object_storage=store,
        identity_eligibility=AlwaysVerified(),
        otp_provider=DevelopmentOtpProvider(),
    )

    # serve the in-memory objects at the URLs create_download_url() hands out (test double only)
    from fastapi import Response as _Resp

    @app.get('/__test_storage/{key:path}', include_in_schema=False)
    async def _test_storage(key: str):
        if key not in store.objects:
            return _Resp(status_code=404)
        body, ctype = store.objects[key]
        return _Resp(content=body, media_type=ctype or 'image/jpeg', headers={'Cache-Control': 'max-age=3600'})
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await seed(app)
        print('SEED_DONE', flush=True)
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=PORT, lifespan='off', log_level='warning'))
        await server.serve()


asyncio.run(main())
