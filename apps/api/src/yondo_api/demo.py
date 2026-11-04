"""Development-only demo data, created through the real API so every rule is applied.

Run from apps/api: ``python -m yondo_api.cli seed-demo``. Sign in with the printed phone
numbers; development OTP codes are returned by ``/auth/otp/request``.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

import httpx
from PIL import Image, ImageDraw
from sqlalchemy import select

from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType

API = '/api/v1'
ADMIN, CUSTOMER, VENDOR = '+998900000001', '+998900000002', '+998900000009'
COMPANIONS = [
    (
        '+998900000003',
        'Malika',
        'female',
        24,
        41.311,
        69.279,
        'Yunusobod',
        [('coffee', 12_000_000, 60), ('walking', 10_000_000, 60)],
        ['uz', 'ru', 'en'],
        ['Kitob', 'San’at'],
    ),
    (
        '+998900000004',
        'Jasur',
        'male',
        27,
        41.285,
        69.204,
        'Chilonzor',
        [('cinema', 15_000_000, 120), ('city_friend', 9_000_000, 60)],
        ['uz', 'en'],
        ['Kino', 'Futbol'],
    ),
    (
        '+998900000005',
        'Dilnoza',
        'female',
        22,
        41.327,
        69.334,
        'Mirzo Ulug‘bek',
        [('study_coworking', 8_000_000, 60), ('conversation', 7_000_000, 30)],
        ['uz', 'ru'],
        ['IT', 'Ingliz tili'],
    ),
]
PRODUCTS = [
    ('flowers', 'Qizil atirgullar (15 dona)', 25_000_000, 20, '#c0392b'),
    ('flowers', 'Lola guldastasi', 18_000_000, 15, '#e67e22'),
    ('chocolate', 'Shokolad to‘plami', 9_000_000, 30, '#6d4c41'),
    ('gift_box', 'Sovg‘a qutisi', 30_000_000, 10, '#8e44ad'),
]


def picture(color: str, label: str) -> bytes:
    image = Image.new('RGB', (600, 600), color=color)
    ImageDraw.Draw(image).text((40, 280), label, fill='white')
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


async def sign_in(client: httpx.AsyncClient, phone: str) -> dict[str, str]:
    issued = (await client.post(f'{API}/auth/otp/request', json={'phone_number': phone})).json()
    tokens = (
        await client.post(
            f'{API}/auth/otp/verify',
            json={'phone_number': phone, 'code': issued['development_otp']},
        )
    ).json()
    return {'Authorization': f'Bearer {tokens["access_token"]}'}


def check(response: httpx.Response) -> dict:
    if response.status_code >= 400:
        raise RuntimeError(f'{response.request.method} {response.request.url}: {response.text}')
    return response.json() if response.content else {}


async def grant(app, phone: str, *roles: UserRoleType) -> None:
    async with app.state.db_session_factory() as session:
        user = await session.scalar(select(User).where(User.phone_number == phone))
        for role in roles:
            if await session.get(UserRole, (user.id, role)) is None:
                session.add(UserRole(user_id=user.id, role=role))
        if UserRoleType.ADMIN in roles:
            user.account_status = AccountStatus.ACTIVE
        await session.commit()


async def seed(app) -> list[str]:
    settings = app.state.settings
    if not settings.is_local:
        raise RuntimeError('Demo data can only be created in development or test')
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url='http://seed'
    ) as client:
        admin = await sign_in(client, ADMIN)
        check(
            await client.put(
                f'{API}/auth/profile',
                headers=admin,
                json={'display_name': 'Admin', 'age': 30, 'gender': 'male', 'city': 'Tashkent'},
            )
        )
        await grant(app, ADMIN, UserRoleType.ADMIN)
        customer = await sign_in(client, CUSTOMER)
        check(
            await client.put(
                f'{API}/auth/profile',
                headers=customer,
                json={'display_name': 'Sardor', 'age': 28, 'gender': 'male', 'city': 'Tashkent'},
            )
        )
        await grant(app, CUSTOMER, UserRoleType.CUSTOMER)
        zone = ZoneInfo('Asia/Tashkent')
        today = datetime.now(UTC).astimezone(zone).date()
        for phone, name, gender, age, lat, lon, area, services, languages, interests in COMPANIONS:
            headers = await sign_in(client, phone)
            check(
                await client.put(
                    f'{API}/auth/profile',
                    headers=headers,
                    json={'display_name': name, 'age': age, 'gender': gender, 'city': 'Tashkent'},
                )
            )
            await grant(app, phone, UserRoleType.COMPANION)
            root = f'{API}/companions/me'
            check(
                await client.post(
                    f'{root}/application',
                    headers=headers,
                    json={'statement': f'{name}: Toshkentda ijtimoiy companion.'},
                )
            )
            check(
                await client.post(
                    f'{root}/profile',
                    headers=headers,
                    json={
                        'display_name': name,
                        'bio': f'Salom! Men {name}. Suhbat va sayrni yaxshi ko‘raman.',
                        'languages': languages,
                        'interests': interests,
                    },
                )
            )
            for code, price, unit in services:
                check(
                    await client.post(
                        f'{root}/services',
                        headers=headers,
                        json={
                            'service_code': code,
                            'price_minor': price,
                            'currency': 'UZS',
                            'unit_minutes': unit,
                        },
                    )
                )
            for day in range(1, 15):
                # 10:00-18:00 Tashkent time for the next two weeks.
                start = datetime.combine(today + timedelta(days=day), time(10), tzinfo=zone)
                check(
                    await client.post(
                        f'{root}/availability',
                        headers=headers,
                        json={
                            'starts_at': start.isoformat(),
                            'ends_at': (start + timedelta(hours=8)).isoformat(),
                            'timezone': 'Asia/Tashkent',
                        },
                    )
                )
            check(
                await client.post(
                    f'{root}/photos',
                    headers={**headers, 'Content-Type': 'image/png'},
                    content=picture('#5b4bdb', name),
                )
            )
            check(
                await client.put(
                    f'{root}/location',
                    headers=headers,
                    json={'area': area, 'latitude': lat, 'longitude': lon},
                )
            )
            application = check(await client.post(f'{root}/application/submit', headers=headers))
            check(
                await client.post(
                    f'{API}/companions/admin/applications/{application["id"]}/decision',
                    headers=admin,
                    json={
                        'decision': 'approve',
                        'note': 'Demo',
                        'expected_revision': application['revision'],
                    },
                )
            )
            profile = check(await client.post(f'{root}/profile/submit', headers=headers))
            check(
                await client.post(
                    f'{API}/companions/admin/profiles/{profile["id"]}/decision',
                    headers=admin,
                    json={
                        'decision': 'approve',
                        'note': 'Demo',
                        'expected_revision': profile['revision'],
                    },
                )
            )
            check(
                await client.post(
                    f'{API}/verification/me', headers=headers, json={'document_type': 'id_card'}
                )
            )
            for part in ('document', 'selfie'):
                check(
                    await client.post(
                        f'{API}/verification/me/{part}',
                        headers={**headers, 'Content-Type': 'image/png'},
                        content=picture('#555555', part),
                    )
                )
            verification = check(
                await client.post(f'{API}/verification/me/submit', headers=headers)
            )
            check(
                await client.post(
                    f'{API}/admin/verifications/{verification["id"]}/decision',
                    headers=admin,
                    json={'decision': 'approve', 'note': 'Demo'},
                )
            )
            check(await client.post(f'{root}/activate', headers=headers))
        vendor = await sign_in(client, VENDOR)
        check(
            await client.put(
                f'{API}/auth/profile',
                headers=vendor,
                json={
                    'display_name': 'Gul Bozori',
                    'age': 35,
                    'gender': 'female',
                    'city': 'Tashkent',
                },
            )
        )
        await grant(app, VENDOR, UserRoleType.VENDOR)
        shop = check(
            await client.post(
                f'{API}/vendors/me',
                headers=vendor,
                json={
                    'name': 'Gul Bozori',
                    'description': 'Yangi gullar va sovg‘alar',
                    'city': 'Tashkent',
                    'currency': 'UZS',
                    'delivery_fee_minor': 2_000_000,
                    'delivery_time_minutes': 90,
                },
            )
        )
        check(
            await client.post(
                f'{API}/admin/vendors/{shop["id"]}/decision',
                headers=admin,
                json={'decision': 'approve', 'note': 'Demo'},
            )
        )
        for category, name, price, stock, color in PRODUCTS:
            product = check(
                await client.post(
                    f'{API}/vendors/me/products',
                    headers=vendor,
                    json={'category': category, 'name': name, 'price_minor': price, 'stock': stock},
                )
            )
            check(
                await client.post(
                    f'{API}/vendors/me/products/{product["id"]}/images',
                    headers={**vendor, 'Content-Type': 'image/png'},
                    content=picture(color, name),
                )
            )
    return [
        f'Admin:     {ADMIN}',
        f'Customer:  {CUSTOMER}',
        *[f'Companion: {c[0]} ({c[1]})' for c in COMPANIONS],
        f'Vendor:    {VENDOR}',
    ]


async def run_seed() -> int:
    from yondo_api.main import create_application

    app = create_application()
    async with app.router.lifespan_context(app):
        async with app.state.db_session_factory() as session:
            if await session.scalar(select(User.id).where(User.phone_number == ADMIN)):
                print('Demo data already exists.')
                return 0
        for line in await seed(app):
            print(line)
    return 0
