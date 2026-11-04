from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.core.time import utc_now
from yondo_api.notifications.models import Notification, PushStatus
from yondo_api.realtime.broker import queue_event


def notify(
    session: AsyncSession,
    user_id: UUID,
    kind: str,
    title: str,
    body: str = '',
    data: dict[str, Any] | None = None,
    *,
    push: bool = True,
) -> Notification:
    """Record an in-app notification; push delivery happens later through the outbox worker."""
    payload = {key: str(value) for key, value in (data or {}).items()}
    notification = Notification(
        id=uuid4(),
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        data=payload,
        push_status=PushStatus.PENDING if push else PushStatus.SKIPPED,
        push_attempts=0,
    )
    session.add(notification)
    queue_event(
        session,
        user_id,
        {
            'type': 'notification',
            'notification': {
                'id': str(notification.id),
                'kind': kind,
                'title': title,
                'body': body,
                'data': payload,
                'created_at': utc_now().isoformat(),
            },
        },
    )
    return notification
