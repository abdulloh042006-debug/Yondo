from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest_asyncio
from support import API, PerUserIdentity, create_user, png, running_app

from yondo_api.companions.integrations import IdentityStatus
from yondo_api.models.user import UserRoleType


@dataclass
class Companion:
    headers: dict[str, str]
    user_id: UUID
    profile_id: str
    services: dict[str, dict] = field(default_factory=dict)
    availability: list[dict] = field(default_factory=list)


def hour_from_now(hours: float) -> datetime:
    base = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    return base + timedelta(hours=hours)


class Market:
    def __init__(self, app, client, identity, storage):
        self.app = app
        self.client = client
        self.identity = identity
        self.storage = storage
        self.counter = 0

    def phone(self) -> str:
        self.counter += 1
        return f'90{self.counter:07d}'

    async def user(self, roles=(UserRoleType.CUSTOMER,), **kwargs):
        return await create_user(self.app, self.client, self.phone(), roles, **kwargs)

    async def companion(
        self,
        name='Malika',
        *,
        services=(('coffee', 100_000, 60),),
        windows=((24, 34),),
        gender='female',
        age=24,
        city='Tashkent',
        languages=('uz', 'en'),
        interests=('Books',),
        location=None,
        photo=True,
        verified=True,
        activate=True,
    ) -> Companion:
        client, admin = self.client, self.admin
        headers, user_id = await self.user(
            (UserRoleType.COMPANION,), name=name, gender=gender, age=age, city=city
        )
        root = f'{API}/companions'
        app_resp = await client.post(f'{root}/me/application', headers=headers, json={})
        assert app_resp.status_code == 201, app_resp.text
        profile = await client.post(
            f'{root}/me/profile',
            headers=headers,
            json={
                'display_name': name,
                'bio': f'{name} bio',
                'languages': list(languages),
                'interests': list(interests),
            },
        )
        assert profile.status_code == 201, profile.text
        result = Companion(headers=headers, user_id=user_id, profile_id=profile.json()['id'])
        for code, price, unit in services:
            created = await client.post(
                f'{root}/me/services',
                headers=headers,
                json={
                    'service_code': code,
                    'price_minor': price,
                    'currency': 'UZS',
                    'unit_minutes': unit,
                },
            )
            assert created.status_code == 201, created.text
            result.services[code] = created.json()
        for start, end in windows:
            window = await client.post(
                f'{root}/me/availability',
                headers=headers,
                json={
                    'starts_at': hour_from_now(start).isoformat(),
                    'ends_at': hour_from_now(end).isoformat(),
                    'timezone': 'Asia/Tashkent',
                },
            )
            assert window.status_code == 201, window.text
            result.availability.append(window.json())
        if photo:
            uploaded = await client.post(
                f'{root}/me/photos',
                headers={**headers, 'Content-Type': 'image/png'},
                content=png(),
            )
            assert uploaded.status_code == 201, uploaded.text
        if location:
            located = await client.put(
                f'{root}/me/location',
                headers=headers,
                json={'area': location[2], 'latitude': location[0], 'longitude': location[1]},
            )
            assert located.status_code == 200, located.text
        await client.post(f'{root}/me/application/submit', headers=headers)
        application = (await client.get(f'{root}/me/application', headers=headers)).json()
        decided = await client.post(
            f'{root}/admin/applications/{application["id"]}/decision',
            headers=admin,
            json={
                'expected_revision': application['revision'],
                'decision': 'approve',
                'note': 'ok',
            },
        )
        assert decided.status_code == 200, decided.text
        await client.post(f'{root}/me/profile/submit', headers=headers)
        review = (
            await client.get(f'{root}/admin/users/{user_id}/content-review', headers=admin)
        ).json()
        decided = await client.post(
            f'{root}/admin/profiles/{result.profile_id}/decision',
            headers=admin,
            json={
                'expected_revision': review['profile']['revision'],
                'decision': 'approve',
                'note': 'ok',
            },
        )
        assert decided.status_code == 200, decided.text
        if verified:
            await self.verify_identity(user_id)
        if activate:
            activated = await client.post(f'{root}/me/activate', headers=headers)
            assert activated.status_code == 200, activated.text
        return result

    async def verify_identity(self, user_id: UUID) -> None:
        self.identity.statuses[user_id] = IdentityStatus.VERIFIED


@pytest_asyncio.fixture
async def market():
    from support import MemoryStorage

    identity, storage = PerUserIdentity(), MemoryStorage()
    async with running_app(identity=identity, storage=storage) as (app, client):
        m = Market(app, client, identity, storage)
        m.admin, m.admin_id = await m.user((UserRoleType.ADMIN,), name='Admin')
        m.customer, m.customer_id = await m.user(name='Sardor', gender='male', age=27)
        yield m
