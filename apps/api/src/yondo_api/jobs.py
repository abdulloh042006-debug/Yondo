"""Maintenance jobs: `python -m yondo_api.jobs` (schedule it hourly; see deploy/README.md).

1. Expire bookings whose start time passed while still pending/accepted (releases the slot).
2. Erase accounts whose deletion request is due (personal data gone within the 30-day window).

3. Delete ID/selfie images of decided verifications older than the retention (proposal, default 0).
4. Delete ID verification drafts abandoned for 24 h, with their objects.

Idempotent and safe to run more often or from several hosts (each step is a single transaction per
row/batch). Exit code 1 means an account could not be erased because of open bookings.
"""

import asyncio
import logging

from yondo_api.account.deletion import process_due_deletions
from yondo_api.bookings.expiry import expire_stale_bookings
from yondo_api.config import get_settings
from yondo_api.db.session import create_database_engine, create_session_factory
from yondo_api.integrations.s3 import build_object_storage
from yondo_api.verification.service import purge_abandoned_drafts, purge_decided_images


async def main(storage=None) -> int:
    settings = get_settings()
    engine = create_database_engine(settings.database_url_async)
    try:
        factory = create_session_factory(engine)
        async with factory() as session:
            expired = await expire_stale_bookings(session)
        async with factory() as session:
            erased, skipped = await process_due_deletions(session, storage)
        async with factory() as session:
            id_purged = await purge_decided_images(
                session, storage, settings.identity_image_retention_days
            )
        async with factory() as session:
            drafts_purged = await purge_abandoned_drafts(session, storage)
    finally:
        await engine.dispose()
        if hasattr(storage, 'aclose'):
            await storage.aclose()
    if storage is None and erased:
        logging.getLogger(__name__).warning(
            'No object storage configured: photo and ID image objects kept'
        )
    print(
        f'bookings_expired={expired} accounts_erased={len(erased)} '
        f'skipped_open_bookings={len(skipped)} id_images_purged={id_purged} '
        f'id_drafts_purged={drafts_purged}'
    )
    return 1 if skipped else 0


def run() -> int:
    # Same storage as the API (YONDO_STORAGE_BACKEND); without it erasure keeps photo objects.
    return asyncio.run(main(build_object_storage(get_settings())))


if __name__ == '__main__':
    raise SystemExit(run())
