"""Invite-only beta feedback; does not activate public services."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from yondo_api.api.errors import ApplicationError
from yondo_api.beta.models import BetaEnrollment, BetaFeedback
from yondo_api.companions.dependencies import Admin, Principal, Session
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType

router = APIRouter(prefix='/beta', tags=['closed beta'])

class EnrollmentWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool

class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
    enabled: bool

class FeedbackWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: Literal['bug', 'usability', 'safety', 'pricing', 'other']
    rating: int = Field(strict=True, ge=1, le=5)
    description: str = Field(min_length=10, max_length=2000)

class FeedbackRead(FeedbackWrite):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID

async def require_enrolled(principal: Principal, session: Session) -> BetaEnrollment:
    if principal.user.account_status != AccountStatus.ACTIVE:
        raise ApplicationError('beta_access_denied', 'Account unavailable', 403)
    row = await session.scalar(
        select(BetaEnrollment).where(BetaEnrollment.user_id == principal.user.id)
    )
    if row is None or not row.enabled:
        raise ApplicationError('beta_access_denied', 'Invitation required', 403)
    return row

@router.get('/me', response_model=EnrollmentRead)
async def my_beta(principal: Principal, session: Session):
    return await require_enrolled(principal, session)

@router.post('/feedback', response_model=FeedbackRead, status_code=201)
async def submit_feedback(payload: FeedbackWrite, principal: Principal, session: Session):
    await require_enrolled(principal, session)
    row = BetaFeedback(user_id=principal.user.id, **payload.model_dump())
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row

@router.get('/admin/enrollments', response_model=list[EnrollmentRead])
async def beta_enrollments(
    admin: Admin, session: Session, limit: int = Query(default=50, ge=1, le=100)
):
    return list(await session.scalars(
        select(BetaEnrollment).order_by(BetaEnrollment.created_at.desc()).limit(limit)
    ))

@router.put('/admin/enrollments/{user_id}', response_model=EnrollmentRead)
async def manage_enrollment(
    user_id: UUID, payload: EnrollmentWrite, admin: Admin, session: Session
):
    user = await session.get(User, user_id)
    if user is None or user.account_status != AccountStatus.ACTIVE:
        raise ApplicationError('beta_user_unavailable', 'User unavailable', 409)
    if not any([
        await session.get(UserRole, (user_id, UserRoleType.CUSTOMER)),
        await session.get(UserRole, (user_id, UserRoleType.COMPANION)),
        await session.get(UserRole, (user_id, UserRoleType.VENDOR)),
    ]):
        raise ApplicationError('beta_role_required', 'Participant role required', 403)
    row = await session.scalar(
        select(BetaEnrollment).where(BetaEnrollment.user_id == user_id).with_for_update()
    )
    if row is None:
        row = BetaEnrollment(user_id=user_id, invited_by_id=admin.id, enabled=payload.enabled)
        session.add(row)
    else:
        row.enabled = payload.enabled
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError('beta_enrollment_conflict', 'Enrollment changed', 409) from exc
    await session.refresh(row)
    return row

@router.get('/admin/feedback', response_model=list[FeedbackRead])
async def read_feedback(
    admin: Admin, session: Session, limit: int = Query(default=50, ge=1, le=100)
):
    return list(await session.scalars(
        select(BetaFeedback).order_by(BetaFeedback.created_at.desc()).limit(limit)
    ))

@router.get('/admin/readiness')
async def beta_readiness(admin: Admin):
    return {
        'ready': False,
        'beta_live': False,
        'outstanding_gates': [
            'production_identity_provider',
            'payment_and_refund_policy',
            'gift_delivery_and_combined_checkout',
            'postgresql_concurrency_validation',
            'redis_and_push_delivery',
            'live_trust_and_safety_operations',
            'real_device_accessibility_and_ux_qa',
            'privacy_terms_and_consent',
        ],
    }
