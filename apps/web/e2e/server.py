"""End-to-end test backend: the REAL Yondo FastAPI app on a throw-away SQLite file.

TEST DOUBLES (never used outside this script, and only because no external service exists here):
  * object storage  -> in-memory (photos cannot be uploaded to MinIO in this environment)
  * identity check  -> always "verified" (the real provider is not integrated yet)
  * OTP delivery    -> the development provider, which returns the code in the response

Everything else (authz, state machines, audit trail, discovery rules) is the production code.
Seed data is labelled "DEMO". This verifies behaviour on SQLite, NOT on PostgreSQL.

Usage: python server.py <port> <sqlite-file>

Optional environment (used by the public demo image, see infra/deploy/README.md):
  YONDO_DEMO_HOST         bind address (default 127.0.0.1)
  YONDO_DEMO_ADMIN_PHONE  phone of the seeded admin. Default: the well-known test number on loopback only; when
                          the server is bound to a public address and this is unset, a random unknown number
                          is used (nobody can sign in as admin; the OTP is shown on screen to every visitor)
  YONDO_WEB_DIST          folder of the built web app; when set, it is served at "/" next to the API
  YONDO_DEMO_PUBLIC_URL   https URL of this server (Render's RENDER_EXTERNAL_URL is used if unset); turns on the
                          DEMO payment provider (demo_payment.py): no money moves, fee = DEMO 0. Unset = payment 503
"""

import asyncio
import os
import secrets
import sys
from uuid import UUID

import httpx
import uvicorn
from sqlalchemy import select
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

from demo_payment import DemoPaymentProvider, install_demo_payment_routes
from yondo_api.companions.integrations import IdentityStatus
from yondo_api.config import Settings
from yondo_api.db.base import Base
from yondo_api.main import create_application
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DB = sys.argv[2] if len(sys.argv) > 2 else 'e2e.db'

HOST = os.environ.get('YONDO_DEMO_HOST', '127.0.0.1')
WEB_DIST = os.environ.get('YONDO_WEB_DIST')
PUBLIC_URL = os.environ.get('YONDO_DEMO_PUBLIC_URL') or os.environ.get('RENDER_EXTERNAL_URL')

# Fail closed: the well-known admin number is only ever used on loopback. On a public bind (the demo image) a missing
# or empty YONDO_DEMO_ADMIN_PHONE must not hand the admin console to every visitor.
LOOPBACK = HOST in ('127.0.0.1', 'localhost', '::1')
ADMIN = os.environ.get('YONDO_DEMO_ADMIN_PHONE', '').strip() or (
    '+998901110001' if LOOPBACK else f'+998{secrets.randbelow(10**9):09d}'
)
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
            await client.post(f'{base}/me/application/submit', headers=headers)
            if approve_all:
                rev = (await client.get(f'{base}/me/application', headers=headers)).json()['revision']
                await client.post(f'{base}/admin/applications/{app_row["id"]}/decision', headers=admin, json={'decision': 'approve', 'expected_revision': rev, 'note': 'DEMO: ariza tekshirildi'})
                await client.post(f'{base}/me/profile/submit', headers=headers)
                review = (await client.get(f'{base}/admin/users/{uid}/content-review', headers=admin)).json()
                await client.post(f'{base}/admin/profiles/{profile["id"]}/decision', headers=admin, json={'decision': 'approve', 'expected_revision': review['profile']['revision'], 'note': 'DEMO: kontent tekshirildi'})
                await client.post(f'{base}/me/activate', headers=headers)
            else:
                await client.post(f'{base}/me/profile/submit', headers=headers)
            return headers, uid, profile['id']

        _, _, madina_profile = await companion('+998901110011', 'DEMO Madina', 'DEMO profil: shahar bo‘ylab sayr va kofe suhbati.', 15000000, True)
        await companion('+998901110012', 'DEMO Jasur', 'DEMO profil: til mashqi va kitoblar.', 9000000, True, city='Samarqand')
        await companion('+998901110013', 'DEMO Sevara', 'DEMO profil: tasdiq kutilmoqda.', 12000000, False)

        # A booking + a safety report so the admin safety queue has a real record to review.
        services = (await client.get(f'/api/v1/discovery/companions/{madina_profile}')).json()['services']
        from datetime import UTC, datetime, timedelta

        # Make Madina bookable: availability must cover the booking.
        mh, _ = await login(client, '+998901110011')
        start = datetime.now(UTC).replace(microsecond=0) + timedelta(days=2, hours=1)
        await client.post('/api/v1/companions/me/availability', headers=mh, json={
            'starts_at': (start - timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
            'ends_at': (start + timedelta(hours=6)).isoformat().replace('+00:00', 'Z'),
            'timezone': 'Asia/Tashkent'})
        booked = await client.post('/api/v1/bookings', headers=customer, json={
            'service_id': services[0]['id'],
            'starts_at': start.isoformat().replace('+00:00', 'Z'),
            'duration_minutes': 60, 'meeting_place': 'DEMO: Magic City kafesi', 'timezone': 'Asia/Tashkent'})
        madina_user = (await client.get(f'/api/v1/discovery/companions/{madina_profile}')).json()
        await client.post('/api/v1/safety/reports', headers=customer, json={
            'reported_user_id': await _user_of_profile(app, madina_profile),
            'booking_id': booked.json().get('id'),
            'category': 'unsafe_behavior',
            'description': 'DEMO shikoyat: ko‘rib chiqish uchun namunaviy yozuv.'})
        _ = madina_user

        # DEMO: a confirmed (paid) booking that started 2 minutes ago, so the meeting flow (check-in, start,
        # SOS signal, end, review) can be exercised without a payment provider. Written straight to the DB:
        # the API never confirms without a provider-verified payment.
        from yondo_api.bookings.models import Booking, BookingStatus

        now = datetime.now(UTC).replace(microsecond=0)
        async with app.state.db_session_factory() as session:
            session.add(Booking(
                customer_id=UUID(customer_id), profile_id=UUID(madina_profile), service_id=UUID(services[1]['id']),
                status=BookingStatus.CONFIRMED, service_code=services[1]['service_code'], service_description='',
                starts_at=now - timedelta(minutes=2), ends_at=now + timedelta(minutes=58), timezone='Asia/Tashkent',
                duration_minutes=60, meeting_place='DEMO: Yunusobod bog‘i (tasdiqlangan)', price_minor=services[1]['price_minor'] * 2,
                currency='UZS', customer_contract_accepted_at=now, companion_contract_accepted_at=now))
            await session.commit()


async def _user_of_profile(app, profile_id):
    from yondo_api.companions.models import CompanionApplication, CompanionProfile

    async with app.state.db_session_factory() as session:
        profile = await session.get(CompanionProfile, UUID(profile_id))
        application = await session.get(CompanionApplication, profile.application_id)
        return str(application.user_id)


class SpaFiles(StaticFiles):
    """The built web app: unknown paths fall back to index.html (client-side routes).

    Not for /api paths or for names with a file extension (a missing asset must stay a 404).
    """

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            rel = path.replace('\\', '/')  # StaticFiles hands over OS-specific separators
            if exc.status_code != 404 or rel.startswith('api/') or '.' in rel.rsplit('/', 1)[-1]:
                raise
            return await super().get_response('index.html', scope)


async def main():
    # DEMO payments (no money moves) only when a public https URL is known; otherwise the honest 503 stays.
    demo_pay = DemoPaymentProvider(PUBLIC_URL) if PUBLIC_URL else None
    settings = Settings(environment='test', database_url=f'sqlite+aiosqlite:///{DB}',
                        **({'platform_fee_bps': 0} if demo_pay else {}))  # labelled DEMO fee, the real policy is the owner's
    app = create_application(settings, object_storage=MemoryStorage(), identity_eligibility=AlwaysVerified(),
                             payment_provider=demo_pay)
    if demo_pay:
        install_demo_payment_routes(app, demo_pay)
    if WEB_DIST:
        app.mount('/', SpaFiles(directory=WEB_DIST, html=True), name='web')
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await seed(app)
        print('SEED_DONE', flush=True)
        server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=PORT, lifespan='off', log_level='warning'))
        await server.serve()


asyncio.run(main())
