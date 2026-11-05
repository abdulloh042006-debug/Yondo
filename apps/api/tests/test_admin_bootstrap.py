import os

import pytest
import pytest_asyncio
from sqlalchemy import event, select, text

from yondo_api.admin.bootstrap import mask_phone, run
from yondo_api.admin.models import AdminAuditEvent
from yondo_api.db.base import Base
from yondo_api.db.session import create_database_engine, create_session_factory
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType

PHONE = '+998901110099'
OTHER = '+998901110098'


@pytest_asyncio.fixture
async def factory():
    engine = create_database_engine(
        os.environ.get('YONDO_TEST_DATABASE_URL', 'sqlite+aiosqlite:///:memory:')
    )
    if engine.dialect.name == 'sqlite':

        @event.listens_for(engine.sync_engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    else:
        async with engine.begin() as connection:
            await connection.execute(text('TRUNCATE users CASCADE'))
    yield create_session_factory(engine)
    await engine.dispose()


async def state(factory, phone=PHONE):
    async with factory() as session:
        user = await session.scalar(select(User).where(User.phone_number == phone))
        admins = (
            await session.scalars(select(UserRole).where(UserRole.role == UserRoleType.ADMIN))
        ).all()
        events = (await session.scalars(select(AdminAuditEvent))).all()
    return user, admins, events


def test_mask_phone_hides_the_middle_digits():
    assert mask_phone(PHONE) == '+998 90 *** ** 99'


@pytest.mark.asyncio
async def test_bad_phone_exits_2_and_never_echoes_it(factory, capsys):
    assert await run(['--phone', '12345'], factory) == 2
    assert '12345' not in capsys.readouterr().out


@pytest.mark.asyncio
async def test_grant_creates_active_admin_once_and_is_idempotent(factory, capsys):
    assert await run(['--phone', '90 111 00 99'], factory) == 0
    user, admins, events = await state(factory)
    assert user.account_status == AccountStatus.ACTIVE
    assert [a.user_id for a in admins] == [user.id]
    assert [(e.admin_id, e.target_id, e.action) for e in events] == [
        (user.id, user.id, 'admin_bootstrap')
    ]
    assert await run(['--phone', PHONE], factory) == 0
    out = capsys.readouterr().out
    assert 'already an admin' in out and '+998 90 *** ** 99' in out
    assert '901110099' not in out
    _, admins, events = await state(factory)
    assert len(admins) == 1 and len(events) == 1


@pytest.mark.asyncio
async def test_grant_keeps_an_existing_user_and_roles(factory):
    async with factory() as session:
        user = User(phone_number=PHONE, account_status=AccountStatus.VERIFICATION_PENDING)
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role=UserRoleType.CUSTOMER))
        await session.commit()
    assert await run(['--phone', PHONE], factory) == 0
    found, admins, _ = await state(factory)
    assert found.id == user.id and found.account_status == AccountStatus.VERIFICATION_PENDING
    assert {r.role for r in found.roles} == {UserRoleType.CUSTOMER, UserRoleType.ADMIN}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'status', [AccountStatus.SUSPENDED, AccountStatus.BANNED, AccountStatus.DELETED]
)
async def test_grant_refuses_unavailable_accounts(factory, status):
    async with factory() as session:
        session.add(User(phone_number=PHONE, account_status=status))
        await session.commit()
    assert await run(['--phone', PHONE], factory) == 1
    _, admins, events = await state(factory)
    assert admins == [] and events == []


@pytest.mark.asyncio
async def test_revoke_refuses_the_last_admin_then_works_with_two(factory, capsys):
    assert await run(['--phone', PHONE, '--revoke'], factory) == 0  # not an admin: no-op
    assert await run(['--phone', PHONE], factory) == 0
    assert await run(['--phone', PHONE, '--revoke'], factory) == 1
    assert 'last admin' in capsys.readouterr().out
    assert await run(['--phone', OTHER], factory) == 0
    assert await run(['--phone', PHONE, '--revoke'], factory) == 0
    user, admins, events = await state(factory)
    assert len(admins) == 1 and user.id not in [a.user_id for a in admins]
    assert sorted(e.action for e in events) == [
        'admin_bootstrap',
        'admin_bootstrap',
        'admin_revoke',
    ]
    assert await run(['--phone', PHONE, '--revoke'], factory) == 0  # idempotent
    _, _, again = await state(factory)
    assert len(again) == len(events)
