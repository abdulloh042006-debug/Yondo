"""Persistent demo mode: keep the demo data between restarts (a free PostgreSQL such as Neon).

Turned on by `YONDO_DEMO_DATABASE_URL`; without it `demo_app.py` keeps the throw-away SQLite file. In this mode:
  * the schema comes from the real Alembic migrations (SQLite, for local tests only, uses create_all);
  * the DEMO seed runs only into an empty database and is bracketed by a state marker, so accounts/bookings survive
    restarts while a start that died halfway through seeding is wiped and seeded again (nobody can have used a
    database that was never served);
  * once the server is up (and then daily) the DEMO companions get availability for the next days, because the seed
    window is a single evening and the demo would otherwise stop accepting bookings after two days;
  * a small loop does what `python -m yondo_api.jobs` does hourly in production (booking expiry, due erasures),
    because a free web service has no cron.
The connection string is a secret: it is only ever read from the environment and never printed.
"""

import asyncio
import logging
import os
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from sqlalchemy import delete, select, text

from yondo_api.account.deletion import process_due_deletions
from yondo_api.bookings.expiry import expire_stale_bookings
from yondo_api.config import Settings
from yondo_api.db.base import Base
from yondo_api.db.session import create_database_engine
from yondo_api.models.user import User, UserRole, UserRoleType

log = logging.getLogger('demo_persist')

STATE_TABLE = 'demo_seed_state'  # demo-harness bookkeeping, not part of the product schema
AVAILABILITY_DAYS = 14
MAINTENANCE_SECONDS = 900


def normalize_database_url(raw: str) -> str:
    """Accept what a provider shows (`postgresql://…`, `postgres://…`, even `psql '…'`) and return the SQLAlchemy URL."""
    found = re.search(r'(postgres(?:ql)?(?:\+psycopg)?|sqlite\+aiosqlite)://[^\s\'"]+', raw or '')
    if not found:
        raise ValueError('YONDO_DEMO_DATABASE_URL must be a postgresql:// connection string')
    url = found.group(0)
    return re.sub(r'^postgres(?:ql)?(?:\+psycopg)?://', 'postgresql+psycopg://', url)


def api_dir() -> Path:
    here = Path(__file__).resolve().parent
    # image: /app/api; repo: infra/deploy/demo -> apps/api
    for candidate in (os.environ.get('YONDO_API_DIR'), here / 'api', here.parents[2] / 'apps' / 'api'):
        if candidate and (Path(candidate) / 'alembic.ini').exists():
            return Path(candidate)
    raise FileNotFoundError('apps/api (alembic.ini) not found; set YONDO_API_DIR')


def run_migrations(database_url: str) -> None:
    """`alembic upgrade head` against the persistent database (idempotent when it is already current)."""
    subprocess.run(
        [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
        cwd=api_dir(), env={**os.environ, 'YONDO_DATABASE_URL': database_url}, check=True,
    )


async def prepare_database(database_url: str) -> bool:
    """Run before the app exists. A start that died while seeding left a 'running' marker: wipe that half-seeded schema.

    Returns True when a wipe happened. Only a database whose seed we started ourselves is ever wiped: the marker is
    written by `mark_seed`, and the server only begins serving after the seed completed.
    """
    settings = Settings(environment='test', database_url=database_url)
    engine = create_database_engine(settings.database_url_async)
    create_state = text(f'CREATE TABLE IF NOT EXISTS {STATE_TABLE} (state TEXT PRIMARY KEY)')
    wiped = False
    try:
        async with engine.begin() as connection:
            await connection.execute(create_state)
            wiped = await connection.scalar(text(f"SELECT 1 FROM {STATE_TABLE} WHERE state = 'running'")) is not None
            if wiped:
                if database_url.startswith('postgresql'):
                    await connection.execute(text('DROP SCHEMA public CASCADE'))
                    await connection.execute(text('CREATE SCHEMA public'))
                else:
                    await connection.run_sync(Base.metadata.drop_all)
                    await connection.execute(text(f'DROP TABLE {STATE_TABLE}'))
                await connection.execute(create_state)
    finally:
        await engine.dispose()
    return wiped


async def seed_status(app) -> str:
    """'complete' (marker present), 'legacy' (users but no marker: left alone) or 'empty' (seed needed)."""
    async with app.state.db_session_factory() as session:
        if await session.scalar(text(f"SELECT 1 FROM {STATE_TABLE} WHERE state = 'complete'")) is not None:
            return 'complete'
        return 'legacy' if await session.scalar(select(User.id).limit(1)) is not None else 'empty'


async def mark_seed(app, state: str) -> None:
    async with app.state.db_session_factory() as session:
        await session.execute(text(f'DELETE FROM {STATE_TABLE}'))
        await session.execute(text(f'INSERT INTO {STATE_TABLE} (state) VALUES (:state)'), {'state': state})
        await session.commit()


async def restrict_admins(app, keep_phone: str | None) -> None:
    """Leave the admin role only on `keep_phone` (on nobody when it is None). `keep_phone` must be normalized."""
    async with app.state.db_session_factory() as session:
        statement = delete(UserRole).where(UserRole.role == UserRoleType.ADMIN)
        if keep_phone:
            keep_id = await session.scalar(select(User.id).where(User.phone_number == keep_phone))
            if keep_id is not None:
                statement = statement.where(UserRole.user_id != keep_id)
        await session.execute(statement)
        await session.commit()


async def top_up_availability(app, login, phones, offsets=range(1, AVAILABILITY_DAYS + 1)) -> int:
    """Give each existing DEMO companion 10:00–22:00 (Tashkent) on `offsets` days from today; existing windows are refused and skipped."""
    created = 0
    now = datetime.now(UTC)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://demo') as client:
        for phone in phones:
            async with app.state.db_session_factory() as session:
                if await session.scalar(select(User.id).where(User.phone_number == phone)) is None:
                    continue  # login() would register a stray account for an unknown number
            headers, _ = await login(client, phone)
            for offset in offsets:
                day = (now + timedelta(days=offset)).date()
                start = datetime(day.year, day.month, day.day, 5, 0, tzinfo=UTC)  # 10:00 Asia/Tashkent
                body = {'starts_at': start.isoformat().replace('+00:00', 'Z'),
                        'ends_at': (start + timedelta(hours=12)).isoformat().replace('+00:00', 'Z'),
                        'timezone': 'Asia/Tashkent'}
                sent = await client.post(f'{app.state.settings.api_v1_prefix}/companions/me/availability',
                                         headers=headers, json=body)
                created += sent.status_code == 201
    return created


async def maintenance_loop(app, login, phones) -> None:
    """Runs after the server is serving: top up at once (all days), then every round; daily only the newest day."""
    offsets = range(1, AVAILABILITY_DAYS + 1)
    topped_on = None
    while True:
        try:
            today = datetime.now(UTC).date()
            if topped_on != today:
                await top_up_availability(app, login, phones, offsets)
                topped_on, offsets = today, range(AVAILABILITY_DAYS, AVAILABILITY_DAYS + 1)
            async with app.state.db_session_factory() as session:
                await expire_stale_bookings(session)
            async with app.state.db_session_factory() as session:
                await process_due_deletions(session, None)
        except Exception:  # keep the demo alive; the next round retries
            log.exception('demo maintenance failed')
        await asyncio.sleep(MAINTENANCE_SECONDS)
