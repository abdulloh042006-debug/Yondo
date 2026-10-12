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


class AdminAccountDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: AccountStatus
    reason: str = Field(min_length=8, max_length=2000)


@router.get('/summary')
async def summary(admin: Admin, session: Session):
    return {
        'users': await session.scalar(select(func.count()).select_from(User)),
        'bookings': await session.scalar(select(func.count()).select_from(Booking)),
        'payments': await session.scalar(select(func.count()).select_from(Payment)),
        'open_reports': await session.scalar(
            select(func.count()).select_from(SafetyReport).where(SafetyReport.status == 'open')
        ),
    }


@router.get('/users', response_model=list[AdminUserRead])
async def users(admin: Admin, session: Session, limit: int = Query(default=50, ge=1, le=100)):
    return list(await session.scalars(select(User).order_by(User.created_at.desc()).limit(limit)))


@router.get('/bookings')
async def bookings(admin: Admin, session: Session, limit: int = Query(default=50, ge=1, le=100)):
    records = list(
        await session.scalars(select(Booking).order_by(Booking.created_at.desc()).limit(limit))
    )
    return [{'id': str(b.id), 'status': b.status, 'created_at': b.created_at} for b in records]


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
