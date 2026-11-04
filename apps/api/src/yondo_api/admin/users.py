from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field
from sqlalchemy import func, or_, select, update

from yondo_api.admin.audit import audit
from yondo_api.api.errors import ApplicationError
from yondo_api.auth.service import profile_complete
from yondo_api.bookings import service as bookings
from yondo_api.bookings.models import Booking, BookingStatus, CancellationReason
from yondo_api.core.db import commit, lock_users
from yondo_api.core.deps import AdminUser, Session
from yondo_api.core.schemas import Input, Output, Page, PageParams, UtcDatetime, page_of
from yondo_api.core.time import utc_now
from yondo_api.models.auth import AuthSession
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType
from yondo_api.notifications.service import notify
from yondo_api.safety.models import AdminAuditLog, Report

router = APIRouter(prefix='/admin/users', tags=['admin: users'])


class AdminUserView(Output):
    id: UUID
    phone_number: str
    display_name: str | None
    age: int | None
    gender: str | None
    city: str | None
    account_status: str
    roles: list[str]
    identity_status: str
    created_at: UtcDatetime


class AuditEntry(Output):
    id: UUID
    admin_id: UUID | None
    action: str
    reason: str
    data: dict[str, str]
    created_at: UtcDatetime


class AdminUserDetail(AdminUserView):
    bookings_as_customer: int
    bookings_as_companion: int
    reports_received: int
    reports_filed: int
    history: list[AuditEntry]


class ModerationAction(Input):
    action: Literal['warn', 'restrict', 'suspend', 'ban', 'reinstate']
    reason: str = Field(min_length=1, max_length=2000)


class RoleChange(Input):
    role: UserRoleType
    action: Literal['grant', 'revoke']


async def user_views(session, request: Request, users: list[User]) -> list[AdminUserView]:
    identity = request.app.state.identity_eligibility
    roles: dict[UUID, list[str]] = {}
    if users:
        for user_id, role in await session.execute(
            select(UserRole.user_id, UserRole.role).where(
                UserRole.user_id.in_([u.id for u in users])
            )
        ):
            roles.setdefault(user_id, []).append(str(role))
    views = []
    for user in users:
        try:
            status = str(await identity.get_status(session, user.id))
        except Exception:
            status = 'unavailable'
        views.append(
            AdminUserView(
                id=user.id,
                phone_number=user.phone_number,
                display_name=user.display_name,
                age=user.age,
                gender=user.gender,
                city=user.city,
                account_status=user.account_status,
                roles=sorted(roles.get(user.id, [])),
                identity_status=status,
                created_at=user.created_at,
            )
        )
    return views


@router.get('', response_model=Page[AdminUserView])
async def list_users(
    request: Request,
    admin: AdminUser,
    session: Session,
    params: Annotated[PageParams, Depends()],
    q: Annotated[str | None, Query(max_length=64)] = None,
    status: AccountStatus | None = None,
    role: UserRoleType | None = None,
):
    query = select(User)
    if q:
        pattern = f'%{q}%'
        query = query.where(or_(User.phone_number.ilike(pattern), User.display_name.ilike(pattern)))
    if status:
        query = query.where(User.account_status == status)
    if role:
        query = query.where(User.id.in_(select(UserRole.user_id).where(UserRole.role == role)))
    rows = list(
        await session.scalars(
            query.order_by(User.created_at.desc(), User.id)
            .offset(params.offset)
            .limit(params.limit + 1)
        )
    )
    page = page_of(rows, params)
    return Page[AdminUserView](
        items=await user_views(session, request, page.items), next_offset=page.next_offset
    )


async def _count(session, query) -> int:
    return await session.scalar(select(func.count()).select_from(query.subquery())) or 0


@router.get('/{user_id}', response_model=AdminUserDetail)
async def user_detail(user_id: UUID, request: Request, admin: AdminUser, session: Session):
    user = await session.get(User, user_id)
    if user is None:
        raise ApplicationError('user_not_found', 'User not found', 404)
    base = (await user_views(session, request, [user]))[0]
    history = list(
        await session.scalars(
            select(AdminAuditLog)
            .where(AdminAuditLog.target_type == 'user', AdminAuditLog.target_id == user_id)
            .order_by(AdminAuditLog.created_at.desc())
            .limit(50)
        )
    )
    return AdminUserDetail(
        **base.model_dump(),
        bookings_as_customer=await _count(
            session, select(Booking.id).where(Booking.customer_id == user_id)
        ),
        bookings_as_companion=await _count(
            session, select(Booking.id).where(Booking.companion_id == user_id)
        ),
        reports_received=await _count(
            session, select(Report.id).where(Report.reported_user_id == user_id)
        ),
        reports_filed=await _count(session, select(Report.id).where(Report.reporter_id == user_id)),
        history=[AuditEntry.model_validate(entry) for entry in history],
    )


async def cancel_upcoming_bookings(session, user: User, admin: User) -> int:
    ids = list(
        await session.scalars(
            select(Booking.id).where(
                or_(Booking.customer_id == user.id, Booking.companion_id == user.id),
                Booking.status.in_(
                    (BookingStatus.PENDING, BookingStatus.ACCEPTED, BookingStatus.CONFIRMED)
                ),
            )
        )
    )
    for booking_id in ids:
        booking = await bookings.lock_booking(session, booking_id)
        # The other party is not at fault: paid bookings are refunded in full.
        await bookings.cancel_and_settle(
            session, booking, CancellationReason.ADMIN, admin.id, 'Account moderation', 10_000
        )
    return len(ids)


@router.post('/{user_id}/moderation', response_model=AdminUserView)
async def moderate(
    user_id: UUID, payload: ModerationAction, request: Request, admin: AdminUser, session: Session
):
    """TZ §39 moderation: warn, restrict, suspend, ban, reinstate."""
    if user_id == admin.id:
        raise ApplicationError('self_moderation_forbidden', 'You cannot moderate yourself', 403)
    user = (await lock_users(session, [user_id]))[user_id]
    if await session.get(UserRole, (user_id, UserRoleType.ADMIN)) is not None:
        raise ApplicationError('admin_target_forbidden', 'Revoke the admin role first', 403)
    cancelled = 0
    if payload.action == 'restrict':
        user.account_status = AccountStatus.RESTRICTED
    elif payload.action in {'suspend', 'ban'}:
        user.account_status = (
            AccountStatus.SUSPENDED if payload.action == 'suspend' else AccountStatus.BANNED
        )
        await session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        cancelled = await cancel_upcoming_bookings(session, user, admin)
    elif payload.action == 'reinstate':
        user.account_status = (
            AccountStatus.ACTIVE if profile_complete(user) else AccountStatus.VERIFICATION_PENDING
        )
    titles = {
        'warn': 'Ogohlantirish',
        'restrict': 'Akkaunt cheklandi',
        'suspend': "Akkaunt to'xtatildi",
        'ban': 'Akkaunt bloklandi',
        'reinstate': 'Akkaunt tiklandi',
    }
    notify(session, user.id, 'moderation', titles[payload.action], payload.reason[:200], push=True)
    audit(
        session,
        admin,
        f'user.{payload.action}',
        'user',
        user.id,
        payload.reason,
        {'cancelled_bookings': cancelled, 'account_status': user.account_status},
    )
    await commit(session)
    return (await user_views(session, request, [user]))[0]


@router.post('/{user_id}/roles', response_model=AdminUserView)
async def change_role(
    user_id: UUID, payload: RoleChange, request: Request, admin: AdminUser, session: Session
):
    user = (await lock_users(session, [user_id]))[user_id]
    existing = await session.get(UserRole, (user_id, payload.role))
    if payload.action == 'grant' and existing is None:
        session.add(UserRole(user_id=user_id, role=payload.role))
    elif payload.action == 'revoke' and existing is not None:
        if user_id == admin.id and payload.role == UserRoleType.ADMIN:
            raise ApplicationError(
                'self_demotion_forbidden', 'You cannot revoke your own admin role', 403
            )
        await session.delete(existing)
    audit(session, admin, f'role.{payload.action}', 'user', user_id, '', {'role': payload.role})
    await commit(session)
    return (await user_views(session, request, [user]))[0]
