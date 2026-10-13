from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, update

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.models.user import AccountStatus
from yondo_api.notifications.models import UserNotification

router = APIRouter(prefix='/notifications', tags=['notifications'])

class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    booking_id: UUID | None
    gift_order_id: UUID | None
    kind: str
    details: dict
    created_at: datetime
    read_at: datetime | None

def check_active(principal: Principal) -> None:
    if principal.user.account_status != AccountStatus.ACTIVE:
        raise ApplicationError('account_unavailable', 'Account unavailable', 403)

@router.get('', response_model=list[NotificationRead])
async def list_notifications(
    principal: Principal, session: Session, unread_only: bool = False,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000)
):
    check_active(principal)
    query = select(UserNotification).where(UserNotification.recipient_id == principal.user.id)
    if unread_only:
        query = query.where(UserNotification.read_at.is_(None))
    query = (
        query.order_by(UserNotification.created_at.desc(), UserNotification.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(await session.scalars(query))

@router.get('/unread-count')
async def unread_count(principal: Principal, session: Session):
    check_active(principal)
    count = await session.scalar(
        select(func.count()).select_from(UserNotification).where(
            UserNotification.recipient_id == principal.user.id,
            UserNotification.read_at.is_(None),
        )
    )
    return {'unread_count': count or 0}

@router.post('/read-all')
async def mark_all_read(principal: Principal, session: Session):
    check_active(principal)
    result = await session.execute(
        update(UserNotification)
        .where(
            UserNotification.recipient_id == principal.user.id,
            UserNotification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    await session.commit()
    return {'marked_count': result.rowcount}


@router.post('/{notification_id}/read', response_model=NotificationRead)
async def mark_read(notification_id: UUID, principal: Principal, session: Session):
    check_active(principal)
    row = await session.scalar(
        select(UserNotification).where(
            UserNotification.id == notification_id,
            UserNotification.recipient_id == principal.user.id,
        ).with_for_update()
    )
    if row is None:
        raise ApplicationError('notification_not_found', 'Notification not found', 404)
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(row)
    return row
