"""Automated checks for the demo harness: DEMO payment, persistent-mode helpers, admin policy.

Run from apps/api (CI does the same):  python -m pytest ../../infra/deploy/demo -c pyproject.toml --rootdir .
In-process on SQLite; no server, no network. The seed makes the first test take a few seconds.
"""

import pytest
import pytest_asyncio
from sqlalchemy import func, inspect, select

import demo_app
import demo_payment_check
from demo_payment import DemoPaymentProvider
from demo_persist import (
    mark_seed, normalize_database_url, prepare_database, restrict_admins, seed_status, top_up_availability,
)
from httpx import ASGITransport, AsyncClient
from yondo_api.auth.providers import DevelopmentOtpProvider
from yondo_api.db.base import Base
from yondo_api.models.user import User, UserRole, UserRoleType

loop = pytest.mark.asyncio(loop_scope='module')


async def _tables(app):
    async with app.state.db_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(scope='module', loop_scope='module')
async def demo(tmp_path_factory):
    """The full demo (seeded, DEMO payments on) on a throw-away SQLite file."""
    url = f'sqlite+aiosqlite:///{tmp_path_factory.mktemp("demo") / "demo.db"}'
    app = demo_app.build_app(url, 0, DemoPaymentProvider('https://demo.test'))
    async with app.router.lifespan_context(app):
        await _tables(app)
        await demo_app.seed(app)
        yield app


@pytest_asyncio.fixture(scope='module', loop_scope='module')
async def bare(tmp_path_factory):
    """Schema only, no seed."""
    url = f'sqlite+aiosqlite:///{tmp_path_factory.mktemp("bare") / "bare.db"}'
    app = demo_app.build_app(url, 0, None)
    async with app.router.lifespan_context(app):
        await _tables(app)
        yield app


async def _admins(app):
    async with app.state.db_session_factory() as session:
        rows = await session.execute(
            select(User.phone_number).join(UserRole, UserRole.user_id == User.id).where(UserRole.role == UserRoleType.ADMIN))
        return sorted(r[0] for r in rows)


def test_normalize_database_url():
    expected = 'postgresql+psycopg://u:p%40ss@ep-1.neon.tech/db?sslmode=require&channel_binding=require'
    for raw in (
        'postgresql://u:p%40ss@ep-1.neon.tech/db?sslmode=require&channel_binding=require',
        'postgres://u:p%40ss@ep-1.neon.tech/db?sslmode=require&channel_binding=require',
        "psql 'postgresql://u:p%40ss@ep-1.neon.tech/db?sslmode=require&channel_binding=require'",
        '"postgresql+psycopg://u:p%40ss@ep-1.neon.tech/db?sslmode=require&channel_binding=require"',
    ):
        assert normalize_database_url(raw) == expected
    with pytest.raises(ValueError):
        normalize_database_url('mysql://u:p@h/db')
    with pytest.raises(ValueError):
        normalize_database_url('')


def test_admin_phone_accepts_every_spelling_the_api_accepts():
    for raw in ('+998909990001', '+998 90 999 00 01', '909990001', '998909990001', ' (90) 999-00-01 '):
        assert demo_app.admin_phone(raw) == '+998909990001'
    assert demo_app.admin_phone('') == '' and demo_app.admin_phone('   ') == ''
    with pytest.raises(SystemExit):
        demo_app.admin_phone('not a phone')


@loop
async def test_demo_payment_flow(demo):
    async with AsyncClient(transport=ASGITransport(app=demo), base_url='http://demo', timeout=60) as client:
        failures, passed = await demo_payment_check.run_checks(client)
    assert not failures
    assert len(passed) >= 13  # 14 with the web app mounted (spa check)
    # A second run on the same database must work too (fresh keys, next free slots).
    async with AsyncClient(transport=ASGITransport(app=demo), base_url='http://demo', timeout=60) as client:
        failures, _ = await demo_payment_check.run_checks(client)
    assert not failures


@loop
async def test_top_up_availability_is_idempotent_and_never_registers_strangers(demo):
    phones = (demo_app.MADINA, demo_app.JASUR)
    first = await top_up_availability(demo, demo_app.login, phones)
    assert first >= 14  # at least one new window per day for one of them
    assert await top_up_availability(demo, demo_app.login, phones) == 0  # every window already exists
    before = await _user_count(demo)
    assert await top_up_availability(demo, demo_app.login, ('+998909990008',)) == 0
    assert await _user_count(demo) == before  # an unknown number must not become an account


async def _user_count(app):
    async with app.state.db_session_factory() as session:
        return await session.scalar(select(func.count()).select_from(User))


@loop
async def test_restrict_admins_keeps_exactly_one(bare):
    async with AsyncClient(transport=ASGITransport(app=bare), base_url='http://bare') as client:
        for phone in ('+998909990001', '+998909990002', '+998901110001'):
            _, user_id = await demo_app.login(client, phone)
            await demo_app.set_user(bare, user_id, [UserRoleType.ADMIN])
    assert len(await _admins(bare)) == 3
    await restrict_admins(bare, '+998909990002')
    assert await _admins(bare) == ['+998909990002']
    await restrict_admins(bare, '+998909990077')  # a number that does not exist: fail closed, nobody keeps admin
    assert await _admins(bare) == []
    await restrict_admins(bare, None)
    assert await _admins(bare) == []


@loop
async def test_interrupted_seed_is_wiped_but_a_complete_one_never(tmp_path):
    url = f'sqlite+aiosqlite:///{tmp_path / "seed-state.db"}'
    assert await prepare_database(url) is False  # fresh database: nothing to wipe
    app = demo_app.build_app(url, 0, None)
    async with app.router.lifespan_context(app):
        await _tables(app)
        assert await seed_status(app) == 'empty'
        await mark_seed(app, 'running')
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://s') as client:
            await demo_app.login(client, '+998909990003')  # a half-seeded database already has users
    assert await prepare_database(url) is True  # the 'running' marker means we died while seeding: wipe
    app = demo_app.build_app(url, 0, None)
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.connect() as connection:
            assert 'users' not in await connection.run_sync(lambda c: inspect(c).get_table_names())
        await _tables(app)
        assert await seed_status(app) == 'empty'
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://s') as client:
            await demo_app.login(client, '+998909990004')
        assert await seed_status(app) == 'legacy'  # users without a marker are left alone
        await mark_seed(app, 'complete')
        assert await seed_status(app) == 'complete'
    assert await prepare_database(url) is False  # a complete seed is never wiped


@loop
async def test_demo_shows_the_code_on_screen_even_if_a_telegram_token_is_set(tmp_path, monkeypatch):
    monkeypatch.setenv('YONDO_TELEGRAM_GATEWAY_TOKEN', '123:not-a-real-token')
    app = demo_app.build_app(f'sqlite+aiosqlite:///{tmp_path / "otp.db"}', 0, None)
    async with app.router.lifespan_context(app):
        assert isinstance(app.state.otp_provider, DevelopmentOtpProvider)
        await _tables(app)
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://s') as client:
            await demo_app.login(client, '+998909990005')  # logs in through `development_otp`
