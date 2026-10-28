from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from yondo_api.admin.models import AdminAuditEvent
from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking
from yondo_api.companions.dependencies import Admin, Session
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType
from yondo_api.payments.models import Payment
from yondo_api.safety.models import SafetyReport

router = APIRouter(prefix='/admin', tags=['admin'])


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    account_status: AccountStatus
    city: str | None


class AdminUserListItem(AdminUserRead):
    """List row; the phone number is masked so the queue leaks the minimum."""

    phone_masked: str
    roles: list[UserRoleType]
    created_at: datetime


class AdminSummary(BaseModel):
    users: int
    bookings: int
    payments: int
    open_reports: int


class AdminBookingRead(BaseModel):
    id: UUID
    status: str
    created_at: datetime


class AdminAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    admin_id: UUID
    target_id: UUID
    action: str
    reason: str
    created_at: datetime


def mask_phone(phone: str) -> str:
    return f'{phone[:4]}{"•" * max(len(phone) - 7, 0)}{phone[-3:]}' if len(phone) > 7 else '•••'


class AdminAccountDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: AccountStatus
    reason: str = Field(min_length=8, max_length=2000)


@router.get('/summary', response_model=AdminSummary)
async def summary(admin: Admin, session: Session):
    return {
        'users': await session.scalar(select(func.count()).select_from(User)),
        'bookings': await session.scalar(select(func.count()).select_from(Booking)),
        'payments': await session.scalar(select(func.count()).select_from(Payment)),
        'open_reports': await session.scalar(
            select(func.count()).select_from(SafetyReport).where(SafetyReport.status == 'open')
        ),
    }


@router.get('/users', response_model=list[AdminUserListItem])
async def users(
    admin: Admin,
    session: Session,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    account_status: AccountStatus | None = None,
    phone: str | None = Query(default=None, min_length=4, max_length=32, pattern=r'^\+?[0-9]+$'),
):
    query = select(User)
    if account_status is not None:
        query = query.where(User.account_status == account_status)
    if phone is not None:
        query = query.where(User.phone_number.like(f'%{phone}%'))
    records = list(
        await session.scalars(
            query.order_by(User.created_at.desc(), User.id.desc()).offset(offset).limit(limit)
        )
    )
    return [
        AdminUserListItem(
            id=u.id,
            account_status=u.account_status,
            city=u.city,
            phone_masked=mask_phone(u.phone_number),
            roles=sorted({r.role for r in u.roles}),
            created_at=u.created_at,
        )
        for u in records
    ]


@router.get('/bookings', response_model=list[AdminBookingRead])
async def bookings(
    admin: Admin,
    session: Session,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    records = list(
        await session.scalars(
            select(Booking)
            .order_by(Booking.created_at.desc(), Booking.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return [AdminBookingRead(id=b.id, status=b.status, created_at=b.created_at) for b in records]


@router.get('/audit-events', response_model=list[AdminAuditRead])
async def audit_events(
    admin: Admin,
    session: Session,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    target_id: UUID | None = None,
    action_prefix: str | None = Query(default=None, max_length=32, pattern=r'^[a-z_]+:?[a-z_]*$'),
):
    query = select(AdminAuditEvent)
    if target_id is not None:
        query = query.where(AdminAuditEvent.target_id == target_id)
    if action_prefix:
        query = query.where(AdminAuditEvent.action.like(f'{action_prefix}%'))
    return list(
        await session.scalars(
            query.order_by(AdminAuditEvent.created_at.desc(), AdminAuditEvent.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )


@router.get('/reports')
async def reports(admin: Admin, session: Session, limit: int = Query(default=50, ge=1, le=100)):
    records = list(
        await session.scalars(
            select(SafetyReport).order_by(SafetyReport.created_at.desc()).limit(limit)
        )
    )
    return [
        {
            'id': str(r.id),
            'category': r.category,
            'status': r.status,
            'reporter_id': str(r.reporter_id),
            'reported_user_id': str(r.reported_user_id),
        }
        for r in records
    ]


@router.post('/users/{user_id}/status', response_model=AdminUserRead)
async def set_account_status(
    user_id: UUID, payload: AdminAccountDecision, admin: Admin, session: Session
):
    if user_id == admin.id:
        raise ApplicationError('admin_self_change_forbidden', 'Cannot change own status', 403)
    user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise ApplicationError('user_not_found', 'User not found', 404)
    if await session.get(UserRole, (user_id, UserRoleType.ADMIN)) is not None:
        raise ApplicationError(
            'admin_target_forbidden', 'Admin accounts require separate review', 403
        )
    # "deleted" is reached only through the user's own deletion request and is irreversible.
    if AccountStatus.DELETED in (payload.status, user.account_status):
        raise ApplicationError(
            'account_deleted_status_locked', 'Deleted status is set only by account deletion', 409
        )
    user.account_status = payload.status
    session.add(
        AdminAuditEvent(
            admin_id=admin.id,
            target_id=user.id,
            action=f'account_status:{payload.status.value}',
            reason=payload.reason.strip(),
        )
    )
    await session.commit()
    await session.refresh(user)
    return user
