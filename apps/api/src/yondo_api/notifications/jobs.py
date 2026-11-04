"""Phase 18 scheduled notifications and the push outbox dispatcher."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import and_, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.bookings.service import fmt_local
from yondo_api.config import Settings
from yondo_api.core.time import utc_now
from yondo_api.integrations.notifications import PushMessage
from yondo_api.integrations.push import InvalidPushToken
from yondo_api.notifications.models import DeviceToken, Notification, NotificationKey, PushStatus
from yondo_api.notifications.service import notify
from yondo_api.reviews.models import Review

logger = structlog.get_logger(__name__)
MAX_PUSH_ATTEMPTS = 3


async def notify_once(
    session: AsyncSession,
    key: str,
    user_id: UUID,
    kind: str,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> bool:
    """Send a scheduled notice exactly once per key, even across concurrent workers."""
    try:
        async with session.begin_nested():
            session.add(NotificationKey(key=key, created_at=utc_now()))
    except IntegrityError:
        return False
    notify(session, user_id, kind, title, body, data)
    return True


async def meeting_reminders(session: AsyncSession, settings: Settings) -> int:
    now = utc_now()
    horizon = now + timedelta(minutes=settings.meeting_reminder_minutes)
    sent = 0
    for booking in await session.scalars(
        select(Booking).where(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.starts_at > now,
            Booking.starts_at <= horizon,
        )
    ):
        when = fmt_local(booking.starts_at, booking.timezone)
        for party in (booking.customer_id, booking.companion_id):
            sent += await notify_once(
                session,
                f'meeting_reminder:{booking.id}:{party}',
                party,
                'meeting_reminder',
                'Uchrashuv yaqinlashmoqda',
                f'{when} da {booking.meeting_place_name}. '
                'Yetib kelganingizda "I\'m here" ni bosing.',
                {'booking_id': booking.id},
            )
    await session.commit()
    return sent


async def payment_reminders(session: AsyncSession, settings: Settings) -> int:
    now = utc_now()
    sent = 0
    for booking in await session.scalars(
        select(Booking).where(
            Booking.status == BookingStatus.ACCEPTED,
            Booking.payment_due_at > now,
            Booking.payment_due_at <= now + timedelta(minutes=15),
        )
    ):
        sent += await notify_once(
            session,
            f'payment_reminder:{booking.id}',
            booking.customer_id,
            'payment_reminder',
            "To'lov muddati tugayapti",
            "Bron bekor bo'lmasligi uchun to'lovni yakunlang.",
            {'booking_id': booking.id},
        )
    await session.commit()
    return sent


async def review_reminders(session: AsyncSession, settings: Settings) -> int:
    now = utc_now()
    ready = now - timedelta(minutes=settings.review_reminder_minutes)
    oldest = now - timedelta(days=settings.review_window_days)
    sent = 0
    for booking in await session.scalars(
        select(Booking).where(
            Booking.status == BookingStatus.COMPLETED,
            and_(Booking.ended_at <= ready, Booking.ended_at >= oldest),
        )
    ):
        reviewed = set(
            await session.scalars(select(Review.author_id).where(Review.booking_id == booking.id))
        )
        for party in (booking.customer_id, booking.companion_id):
            if party in reviewed:
                continue
            sent += await notify_once(
                session,
                f'review_reminder:{booking.id}:{party}',
                party,
                'review_reminder',
                'Uchrashuvni baholang',
                'Fikringiz boshqalarga ishonchli tanlov qilishga yordam beradi.',
                {'booking_id': booking.id},
            )
    await session.commit()
    return sent


async def dispatch_push(session: AsyncSession, provider: Any, limit: int = 200) -> int:
    """Outbox: deliver pending notifications to every registered device of the user."""
    pending = list(
        await session.scalars(
            select(Notification)
            .where(Notification.push_status == PushStatus.PENDING)
            .order_by(Notification.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    delivered = 0
    for item in pending:
        if provider is None:
            item.push_status = PushStatus.SKIPPED
            continue
        tokens = list(
            await session.scalars(select(DeviceToken).where(DeviceToken.user_id == item.user_id))
        )
        if not tokens:
            item.push_status = PushStatus.SKIPPED
            continue
        item.push_attempts += 1
        success = False
        for device in tokens:
            data = {**item.data, 'notification_id': str(item.id), 'kind': item.kind}
            try:
                await provider.send(PushMessage(device.token, item.title, item.body, data))
                success = True
            except InvalidPushToken:
                await session.execute(delete(DeviceToken).where(DeviceToken.id == device.id))
            except Exception:
                logger.warning('push_send_failed', notification_id=str(item.id))
        if success:
            item.push_status = PushStatus.SENT
            delivered += 1
        elif item.push_attempts >= MAX_PUSH_ATTEMPTS:
            item.push_status = PushStatus.FAILED
    await session.commit()
    return delivered
