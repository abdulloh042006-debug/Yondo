"""Background worker: expiries, refunds, meeting completion, reminders and push delivery.

Run one process alongside the API (``python -m yondo_api.cli worker``) or call
``python -m yondo_api.cli worker --once`` from an external scheduler. Every job is
idempotent and safe to run concurrently thanks to row locks and idempotency keys.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def jobs() -> list[tuple[str, Callable[[Any, Any], Awaitable[int]]]]:
    from yondo_api.bookings.meeting import auto_complete_overdue
    from yondo_api.bookings.service import expire_due
    from yondo_api.notifications import jobs as notices
    from yondo_api.payments.service import expire_pending_payments, process_refunds

    def with_settings(job):
        return lambda session, state: job(session, state.settings)

    return [
        ('expire_bookings', lambda session, state: expire_due(session)),
        ('expire_payments', lambda session, state: expire_pending_payments(session)),
        ('process_refunds', process_refunds),
        ('auto_complete_meetings', with_settings(auto_complete_overdue)),
        ('meeting_reminders', with_settings(notices.meeting_reminders)),
        ('payment_reminders', with_settings(notices.payment_reminders)),
        ('review_reminders', with_settings(notices.review_reminders)),
        (
            'dispatch_push',
            lambda session, state: notices.dispatch_push(session, state.push_provider),
        ),
    ]


async def run_jobs(state: Any) -> dict[str, int]:
    """Run every job once in its own session; a failing job never blocks the others."""
    results: dict[str, int] = {}
    for name, job in jobs():
        try:
            async with state.db_session_factory() as session:
                session.info['realtime_broker'] = getattr(state, 'realtime_broker', None)
                results[name] = await job(session, state)
        except Exception:
            logger.exception('worker_job_failed', job=name)
            results[name] = -1
    return results


async def run_worker(*, once: bool = False) -> int:
    from yondo_api.main import create_application

    app = create_application()
    async with app.router.lifespan_context(app):
        interval = app.state.settings.worker_interval_seconds
        while True:
            results = await run_jobs(app.state)
            logger.info('worker_cycle', **results)
            if once:
                return 0
            await asyncio.sleep(interval)
