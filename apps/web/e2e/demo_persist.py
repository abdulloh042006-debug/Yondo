"""Persistent demo mode: keep the demo data between restarts (a free PostgreSQL such as Neon).

Turned on by `YONDO_DEMO_DATABASE_URL`; without it `server.py` keeps the throw-away SQLite file. In this mode:
  * the schema comes from the real Alembic migrations (SQLite, for local tests only, uses create_all);
  * the DEMO seed runs only while the database has no users, so accounts/bookings survive restarts;
  * every start (and then daily) the two DEMO companions get availability for the next days, because the seed
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
from sqlalchemy import delete, select

from yondo_api.account.deletion import process_due_deletions
from yondo_api.bookings.expiry import expire_stale_bookings
from yondo_api.models.user import User, UserRole, UserRoleType

log = logging.getLogger('demo_persist')

DEMO_COMPANIONS = ('+998901110011', '+998901110012')  # DEMO Madina, DEMO Jasur (seeded by server.py)
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
    for candidate in (os.environ.get('YONDO_API_DIR'), here / 'api', here.parents[1] / 'api'):  # image: /app/api; repo: apps/web/e2e -> apps/api
        if candidate and (Path(candidate) / 'alembic.ini').exists():
            return Path(candidate)
    raise FileNotFoundError('apps/api (alembic.ini) not found; set YONDO_API_DIR')


def run_migrations(database_url: str) -> None:
    """`alembic upgrade head` against the persistent database (idempotent when it is already current)."""
    subprocess.run(
        [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
        cwd=api_dir(), env={**os.environ, 'YONDO_DATABASE_URL': database_url}, check=True,
    )


async def has_users(app) -> bool:
    async with app.state.db_session_factory() as session:
        return await session.scalar(select(User.id).limit(1)) is not None


async def restrict_admins(app, keep_phone: str | None) -> None:
    """Leave the admin role only on `keep_phone` (on nobody when it is None)."""
    async with app.state.db_session_factory() as session:
        statement = delete(UserRole).where(UserRole.role == UserRoleType.ADMIN)
        if keep_phone:
            keep_id = await session.scalar(select(User.id).where(User.phone_number == keep_phone))
            if keep_id is not None:
                statement = statement.where(UserRole.user_id != keep_id)
        await session.execute(statement)
        await session.commit()


async def top_up_availability(app, login, days: int = AVAILABILITY_DAYS) -> int:
    """Give each DEMO companion 10:00–22:00 (Tashkent) on the next days; windows that already exist are refused and skipped."""
    created = 0
    now = datetime.now(UTC)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url='http://demo') as client:
        for phone in DEMO_COMPANIONS:
            headers, _ = await login(client, phone)
            for offset in range(1, days + 1):
                day = (now + timedelta(days=offset)).date()
                start = datetime(day.year, day.month, day.day, 5, 0, tzinfo=UTC)  # 10:00 Asia/Tashkent
                body = {'starts_at': start.isoformat().replace('+00:00', 'Z'),
                        'ends_at': (start + timedelta(hours=12)).isoformat().replace('+00:00', 'Z'),
                        'timezone': 'Asia/Tashkent'}
                sent = await client.post(f'{app.state.settings.api_v1_prefix}/companions/me/availability',
                                         headers=headers, json=body)
                created += sent.status_code == 201
    return created


async def maintenance_loop(app, login) -> None:
    last_top_up = datetime.now(UTC).date()
    while True:
        await asyncio.sleep(MAINTENANCE_SECONDS)
        try:
            async with app.state.db_session_factory() as session:
                await expire_stale_bookings(session)
            async with app.state.db_session_factory() as session:
                await process_due_deletions(session, None)
            if datetime.now(UTC).date() != last_top_up:
                await top_up_availability(app, login)
                last_top_up = datetime.now(UTC).date()
        except Exception:  # keep the demo alive; the next round retries
            log.exception('demo maintenance failed')
