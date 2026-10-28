from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from yondo_api.account import deletion
from yondo_api.account.models import AccountDeletionRequest, SupportRequest
from yondo_api.account.router import SupportCategory, UtcDatetime
from yondo_api.admin.models import AdminAuditEvent
from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Admin, Session

router = APIRouter(prefix='/admin', tags=['admin'])


class AdminSupportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    category: SupportCategory
    message: str
    status: Literal['open', 'answered', 'closed']
    reply: str | None
    created_at: UtcDatetime
    replied_at: UtcDatetime | None


class SupportReply(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reply: str = Field(min_length=2, max_length=4000)
    close: bool = False


class AdminDeletionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    status: Literal['pending', 'cancelled', 'completed']
    requested_at: UtcDatetime
    due_at: UtcDatetime
    completed_at: UtcDatetime | None


class DeletionRun(BaseModel):
    erased: list[UUID]
    skipped_open_bookings: list[UUID]


@router.get('/support/requests', response_model=list[AdminSupportRead])
async def list_support_requests(
    admin: Admin,
    session: Session,
    status: Literal['open', 'answered', 'closed'] | None = Query(default=None),
):
    query = select(SupportRequest).order_by(SupportRequest.created_at.desc()).limit(200)
    if status is not None:
        query = query.where(SupportRequest.status == status)
    return list(await session.scalars(query))


@router.post('/support/requests/{request_id}/reply', response_model=AdminSupportRead)
async def reply_support_request(
    request_id: UUID, payload: SupportReply, admin: Admin, session: Session
):
    item = await session.scalar(
        select(SupportRequest).where(SupportRequest.id == request_id).with_for_update()
    )
    if item is None:
        raise ApplicationError('support_request_not_found', 'Support request not found', 404)
    reply = payload.reply.strip()
    if len(reply) < 2:
        raise ApplicationError('support_reply_too_short', 'Reply is too short', 422)
    item.reply = reply
    item.replied_at = datetime.now(UTC)
    item.replied_by = admin.id
    item.status = 'closed' if payload.close else 'answered'
    session.add(
        AdminAuditEvent(
            admin_id=admin.id,
            target_id=item.user_id,
            action='support_reply',
            reason=f'support request {item.id}',
        )
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.get('/account-deletions', response_model=list[AdminDeletionRead])
async def list_deletions(admin: Admin, session: Session):
    return list(
        await session.scalars(
            select(AccountDeletionRequest)
            .order_by(AccountDeletionRequest.requested_at.desc())
            .limit(200)
        )
    )


@router.post('/account-deletions/process-due', response_model=DeletionRun)
async def process_due(request: Request, admin: Admin, session: Session):
    """Run the erasure now (normally hourly via `python -m yondo_api.jobs`, infra/jobs)."""
    erased, skipped = await deletion.process_due_deletions(
        session, request.app.state.object_storage
    )
    for user_id in erased:
        session.add(
            AdminAuditEvent(
                admin_id=admin.id,
                target_id=user_id,
                action='account_erased',
                reason='User deletion request reached its due date',
            )
        )
    await session.commit()
    return DeletionRun(erased=erased, skipped_open_bookings=skipped)
