from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, func, select, update

from yondo_api.api.errors import ApplicationError
from yondo_api.core.db import commit
from yondo_api.core.deps import CurrentUser, Session
from yondo_api.core.schemas import Page, PageParams, page_of
from yondo_api.core.time import utc_now
from yondo_api.notifications.models import DeviceToken, Notification
from yondo_api.notifications.schemas import (
    DeviceRegistration,
    DeviceRemoval,
    NotificationResponse,
    UnreadCount,
)

router = APIRouter(prefix='/notifications', tags=['notifications'])


@router.get('', response_model=Page[NotificationResponse])
async def list_notifications(
    user: CurrentUser,
    session: Session,
    params: Annotated[PageParams, Depends()],
    unread_only: bool = False,
):
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    rows = list(
        await session.scalars(
            query.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    return page_of([NotificationResponse.model_validate(row) for row in rows], params)


@router.get('/unread-count', response_model=UnreadCount)
async def unread_count(user: CurrentUser, session: Session):
    count = await session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return UnreadCount(unread=count or 0)


@router.post('/{notification_id}/read', response_model=NotificationResponse)
async def mark_read(notification_id: UUID, user: CurrentUser, session: Session):
    item = await session.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    )
    if item is None:
        raise ApplicationError('notification_not_found', 'Notification not found', 404)
    if item.read_at is None:
        item.read_at = utc_now()
        await commit(session)
    return item


@router.post('/read-all', status_code=204)
async def mark_all_read(user: CurrentUser, session: Session):
    await session.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=utc_now())
    )
    await commit(session)
    return Response(status_code=204)


@router.put('/devices', status_code=204)
async def register_device(payload: DeviceRegistration, user: CurrentUser, session: Session):
    existing = await session.scalar(select(DeviceToken).where(DeviceToken.token == payload.token))
    if existing is None:
        session.add(DeviceToken(user_id=user.id, token=payload.token, platform=payload.platform))
    else:
        # A device token belongs to whichever account last signed in on that device.
        existing.user_id = user.id
        existing.platform = payload.platform
        existing.updated_at = utc_now()
    await commit(session, 'device_conflict', 'Device token is already registered')
    return Response(status_code=204)


@router.post('/devices/remove', status_code=204)
async def remove_device(payload: DeviceRemoval, user: CurrentUser, session: Session):
    await session.execute(
        delete(DeviceToken).where(
            DeviceToken.token == payload.token, DeviceToken.user_id == user.id
        )
    )
    await commit(session)
    return Response(status_code=204)
