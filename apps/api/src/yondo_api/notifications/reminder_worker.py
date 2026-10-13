"""Standalone scheduled meeting-reminder worker: in-app only, no external push.

Usage:
  python -m yondo_api.notifications.reminder_worker --once
  python -m yondo_api.notifications.reminder_worker --loop --interval-seconds 300
"""

import argparse
import asyncio
import logging

from yondo_api.config import get_settings
from yondo_api.db.session import create_database_engine, create_session_factory
from yondo_api.notifications.reminders import sweep_meeting_reminders

logger = logging.getLogger(__name__)


async def _run(loop: bool, interval_seconds: int) -> None:
    engine = create_database_engine(get_settings().database_url_async)
    factory = create_session_factory(engine)
    try:
        while True:
            try:
                result = await sweep_meeting_reminders(factory)
                logger.info(
                    'Meeting reminders: candidate_bookings=%d processed=%d notices_created=%d',
                    result.candidate_bookings,
                    result.bookings_processed,
                    result.notices_created,
                )
            except Exception:
                logger.exception('Meeting reminder sweep failed')
                if not loop:
                    raise
            if not loop:
                return
            await asyncio.sleep(interval_seconds)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate in-app meeting reminders')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--once', action='store_true', help='One sweep for cron/QA')
    mode.add_argument('--loop', action='store_true', help='Repeated background worker')
    parser.add_argument('--interval-seconds', type=int, default=300)
    args = parser.parse_args()
    if not 60 <= args.interval_seconds <= 600:
        parser.error('--interval-seconds must be between 60 and 600')
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(_run(args.loop, args.interval_seconds))
    except KeyboardInterrupt:
        logger.info('Meeting reminder worker stopped')


if __name__ == '__main__':
    main()
