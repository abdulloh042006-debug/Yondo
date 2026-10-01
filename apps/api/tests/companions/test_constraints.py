from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from yondo_api.companions.models import (
    CompanionApplication,
    CompanionAvailability,
    CompanionProfile,
    CompanionService,
)
from yondo_api.models.user import UserRole, UserRoleType

from .conftest import approve


@pytest.mark.parametrize(
    'model,changes',
    [
        (CompanionApplication, {'status': 'active'}),
        (CompanionProfile, {'content_status': 'verified'}),
        (CompanionProfile, {'activation_requested': True}),
    ],
)
async def test_database_rejects_invalid_states(prepared, model, changes):
    async with prepared['app'].state.db_session_factory() as session:
        record = await session.scalar(select(model))
        for key, value in changes.items():
            setattr(record, key, value)
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.parametrize('changes', [{'price_minor': -1}, {'unit_minutes': 0}, {'currency': 'US'}])
async def test_database_rejects_invalid_prices(prepared, changes):
    values = {
        'profile_id': UUID(prepared['profile']['id']),
        'service_code': 'coffee',
        'price_minor': 100,
        'currency': 'UZS',
        'unit_minutes': 60,
    }
    async with prepared['app'].state.db_session_factory() as session:
        session.add(CompanionService(**(values | changes)))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_database_rejects_invalid_availability_and_orphan(prepared):
    now = datetime.now(UTC)
    async with prepared['app'].state.db_session_factory() as session:
        session.add(
            CompanionAvailability(
                profile_id=UUID(prepared['profile']['id']),
                starts_at=now,
                ends_at=now,
                timezone='UTC',
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
        session.add(
            CompanionService(
                profile_id=uuid4(),
                service_code='coffee',
                price_minor=100,
                currency='UZS',
                unit_minutes=60,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_database_unique_service_and_profile(prepared):
    async with prepared['app'].state.db_session_factory() as session:
        session.add_all(
            [
                CompanionService(
                    profile_id=UUID(prepared['profile']['id']),
                    service_code='coffee',
                    price_minor=100,
                    currency='UZS',
                    unit_minutes=60,
                )
                for _ in range(2)
            ]
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
        session.add(
            CompanionProfile(
                application_id=UUID(prepared['application']['id']),
                display_name='Duplicate',
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_postgres_exclusion_constraint_enforces_direct_inserts(prepared):
    if prepared['app'].state.db_engine.dialect.name != 'postgresql':
        pytest.skip(
            'Requires YONDO_TEST_DATABASE_URL pointing to a migrated PostgreSQL test database'
        )
    now = datetime.now(UTC)
    async with prepared['app'].state.db_session_factory() as session:
        ddl = await session.scalar(
            text(
                'SELECT pg_get_constraintdef(oid) FROM pg_constraint '
                "WHERE conname = 'ex_companion_availability_overlap'"
            )
        )
        assert 'EXCLUDE USING gist' in ddl
        assert 'tstzrange' in ddl
        session.add(
            CompanionAvailability(
                profile_id=UUID(prepared['profile']['id']),
                starts_at=now,
                ends_at=now + timedelta(hours=1),
                timezone='UTC',
            )
        )
        await session.commit()
        session.add(
            CompanionAvailability(
                profile_id=UUID(prepared['profile']['id']),
                starts_at=now + timedelta(minutes=30),
                ends_at=now + timedelta(hours=2),
                timezone='UTC',
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_self_approval_denied_and_pending_edits_invalidate(prepared):
    e = prepared
    async with e['app'].state.db_session_factory() as session:
        session.add(UserRole(user_id=UUID(e['owner_id']), role=UserRoleType.ADMIN))
        await session.commit()
    await e['client'].post('/api/v1/companions/me/application/submit', headers=e['owner'])
    response = await e['client'].post(
        f'/api/v1/companions/admin/applications/{e["application"]["id"]}/decision',
        headers=e['owner'],
        json={'expected_revision': 2, 'decision': 'approve', 'note': 'Self approval'},
    )
    assert response.status_code == 403


async def test_profile_stale_approval_and_invalid_admin_payload(prepared):
    e = prepared
    await e['client'].post('/api/v1/companions/me/profile/submit', headers=e['owner'])
    url = f'/api/v1/companions/admin/profiles/{e["profile"]["id"]}/decision'
    assert (
        await e['client'].post(
            url,
            headers=e['admin'],
            json={'expected_revision': 2, 'decision': 'activate', 'note': 'x'},
        )
    ).status_code == 422
    await e['client'].put(
        '/api/v1/companions/me/profile',
        headers=e['owner'],
        json={'display_name': 'Changed after submission'},
    )
    assert (
        await e['client'].post(
            url,
            headers=e['admin'],
            json={'expected_revision': 2, 'decision': 'approve', 'note': 'x'},
        )
    ).status_code == 409


async def test_repeated_approval_is_invalid(prepared):
    await approve(prepared)
    for resource, ident in [
        ('applications', prepared['application']['id']),
        ('profiles', prepared['profile']['id']),
    ]:
        response = await prepared['client'].post(
            f'/api/v1/companions/admin/{resource}/{ident}/decision',
            headers=prepared['admin'],
            json={'expected_revision': 2, 'decision': 'approve', 'note': 'Again'},
        )
        assert response.status_code == 409


async def test_postgres_concurrent_inserts_cannot_overlap(prepared):
    import asyncio

    from sqlalchemy import func

    if prepared['app'].state.db_engine.dialect.name != 'postgresql':
        pytest.skip('Requires a migrated PostgreSQL test database with concurrent connections')
    now = datetime.now(UTC)
    factory = prepared['app'].state.db_session_factory

    async def reserve_window():
        async with factory() as session:
            session.add(
                CompanionAvailability(
                    profile_id=UUID(prepared['profile']['id']),
                    starts_at=now,
                    ends_at=now + timedelta(hours=1),
                    timezone='UTC',
                )
            )
            try:
                await session.commit()
                return 'created'
            except IntegrityError:
                await session.rollback()
                return 'conflict'

    results = await asyncio.wait_for(asyncio.gather(reserve_window(), reserve_window()), timeout=10)
    assert sorted(results) == ['conflict', 'created']
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(CompanionAvailability)) == 1
