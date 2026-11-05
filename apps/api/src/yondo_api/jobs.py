"""Maintenance jobs: `python -m yondo_api.jobs` (schedule it hourly; see deploy/README.md).

1. Expire bookings whose start time passed while still pending/accepted (releases the slot).
2. Erase accounts whose deletion request is due (personal data gone within the 30-day window).

Idempotent and safe to run more often or from several hosts (each step is a single transaction per
row/batch). Exit code 1 means an account could not be erased because of open bookings.
"""

import asyncio
import logging

from yondo_api.account.deletion import process_due_deletions
from yondo_api.bookings.expiry import expire_stale_bookings
from yondo_api.config import get_settings
from yondo_api.db.session import create_database_engine, create_session_factory


async def main(storage=None) -> int:
    settings = get_settings()
    engine = create_database_engine(settings.database_url_async)
    try:
        factory = create_session_factory(engine)
        async with factory() as session:
            expired = await expire_stale_bookings(session)
        async with factory() as session:
            erased, skipped = await process_due_deletions(session, storage)
    finally:
        await engine.dispose()
    if storage is None and erased:
        logging.getLogger(__name__).warning('No object storage configured: photo objects kept')
    print(
        f'bookings_expired={expired} accounts_erased={len(erased)} '
        f'skipped_open_bookings={len(skipped)}'
    )
    return 1 if skipped else 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
