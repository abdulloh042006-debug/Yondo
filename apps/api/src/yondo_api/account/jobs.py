"""Daily erasure job: `python -m yondo_api.account.jobs` (schedule it once a day, e.g. cron).

Erases accounts whose deletion request is due, so personal data is gone within the 30-day window.
Photo objects are deleted only when an object-storage adapter is configured for this process;
otherwise the photo rows are tombstoned and the keys are logged for storage clean-up.
"""

import asyncio
import logging

from yondo_api.account.deletion import process_due_deletions
from yondo_api.config import get_settings
from yondo_api.db.session import create_database_engine, create_session_factory


async def main(storage=None) -> int:
    settings = get_settings()
    engine = create_database_engine(settings.database_url_async)
    try:
        async with create_session_factory(engine)() as session:
            erased, skipped = await process_due_deletions(session, storage)
    finally:
        await engine.dispose()
    if storage is None and erased:
        logging.getLogger(__name__).warning('No object storage configured: photo objects kept')
    print(f'erased={len(erased)} skipped_open_bookings={len(skipped)}')
    return 1 if skipped else 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
