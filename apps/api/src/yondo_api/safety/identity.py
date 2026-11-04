"""ID + selfie verification and the database-backed identity eligibility adapter."""

from __future__ import annotations

from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import object_storage
from yondo_api.companions.integrations import IdentityStatus
from yondo_api.core.db import commit, lock_users
from yondo_api.core.deps import CurrentUser, Session
from yondo_api.core.images import (
    IMAGE_REQUEST_BODY,
    discard_image,
    read_image,
    signed_url,
    store_image,
)
from yondo_api.core.schemas import Input, Output, UtcDatetime
from yondo_api.core.time import utc_now
from yondo_api.models.user import User
from yondo_api.notifications.service import notify
from yondo_api.safety.models import IdentityVerification, VerificationStatus

router = APIRouter(prefix='/verification', tags=['verification'])

_STATUS_MAP = {
    VerificationStatus.PENDING: IdentityStatus.PENDING,
    VerificationStatus.VERIFIED: IdentityStatus.VERIFIED,
    VerificationStatus.REJECTED: IdentityStatus.REJECTED,
}


class DatabaseIdentityEligibility:
    """Identity status from the latest submitted verification (drafts are ignored)."""

    async def get_status(self, session: AsyncSession, user_id: UUID) -> IdentityStatus:
        latest = await session.scalar(
            select(IdentityVerification.status)
            .where(
                IdentityVerification.user_id == user_id,
                IdentityVerification.status != VerificationStatus.DRAFT,
            )
            .order_by(IdentityVerification.created_at.desc(), IdentityVerification.id.desc())
            .limit(1)
        )
        return _STATUS_MAP.get(latest, IdentityStatus.UNKNOWN)

    async def verified_user_ids(self, session: AsyncSession, user_ids: list[UUID]) -> set[UUID]:
        if not user_ids:
            return set()
        latest = (
            select(
                IdentityVerification.user_id,
                func.max(IdentityVerification.created_at).label('created_at'),
            )
            .where(
                IdentityVerification.user_id.in_(user_ids),
                IdentityVerification.status != VerificationStatus.DRAFT,
            )
            .group_by(IdentityVerification.user_id)
            .subquery()
        )
        rows = await session.scalars(
            select(IdentityVerification.user_id)
            .join(
                latest,
                (IdentityVerification.user_id == latest.c.user_id)
                & (IdentityVerification.created_at == latest.c.created_at),
            )
            .where(IdentityVerification.status == VerificationStatus.VERIFIED)
        )
        return set(rows)


class VerificationStart(Input):
    document_type: Literal['passport', 'id_card', 'driver_license']


class VerificationResponse(Output):
    id: UUID
    status: str
    document_type: str
    has_document: bool
    has_selfie: bool
    submitted_at: UtcDatetime | None
    reviewed_at: UtcDatetime | None
    review_note: str | None


class AdminVerificationView(VerificationResponse):
    user_id: UUID
    document_url: str | None = None
    selfie_url: str | None = None


class VerificationDecision(Input):
    decision: Literal['approve', 'reject']
    note: str = Field(min_length=1, max_length=2000)


def view(item: IdentityVerification) -> VerificationResponse:
    return VerificationResponse(
        id=item.id,
        status=item.status,
        document_type=item.document_type,
        has_document=item.document_key is not None,
        has_selfie=item.selfie_key is not None,
        submitted_at=item.submitted_at,
        reviewed_at=item.reviewed_at,
        review_note=item.review_note,
    )


async def admin_view(request: Request, item: IdentityVerification) -> AdminVerificationView:
    return AdminVerificationView(
        **view(item).model_dump(),
        user_id=item.user_id,
        document_url=await signed_url(request, item.document_key, 300),
        selfie_url=await signed_url(request, item.selfie_key, 300),
    )


async def latest(session: AsyncSession, user_id: UUID) -> IdentityVerification | None:
    return await session.scalar(
        select(IdentityVerification)
        .where(IdentityVerification.user_id == user_id)
        .order_by(IdentityVerification.created_at.desc(), IdentityVerification.id.desc())
        .limit(1)
    )


async def editable_draft(session: AsyncSession, user_id: UUID) -> IdentityVerification:
    await lock_users(session, [user_id])
    item = await latest(session, user_id)
    if item is None or item.status != VerificationStatus.DRAFT:
        raise ApplicationError('verification_not_draft', 'Start a verification first', 409)
    return item


async def decide(
    session: AsyncSession, verification_id: UUID, admin: User, decision: str, note: str
) -> IdentityVerification:
    item = await session.scalar(
        select(IdentityVerification)
        .where(IdentityVerification.id == verification_id)
        .with_for_update()
    )
    if item is None:
        raise ApplicationError('verification_not_found', 'Verification not found', 404)
    if item.user_id == admin.id:
        raise ApplicationError('self_approval_forbidden', 'Self approval is not permitted', 403)
    if item.status != VerificationStatus.PENDING:
        raise ApplicationError('verification_not_pending', 'Verification is not pending', 409)
    item.status = (
        VerificationStatus.VERIFIED if decision == 'approve' else VerificationStatus.REJECTED
    )
    item.reviewed_at = utc_now()
    item.reviewed_by = admin.id
    item.review_note = note
    approved = item.status == VerificationStatus.VERIFIED
    notify(
        session,
        item.user_id,
        'verification_decided',
        'Shaxsingiz tasdiqlandi' if approved else 'Tasdiqlash rad etildi',
        note[:200],
        {'verification_id': item.id},
    )
    await commit(session)
    return item


@router.get('/me', response_model=VerificationResponse | None)
async def my_verification(user: CurrentUser, session: Session):
    item = await latest(session, user.id)
    return view(item) if item else None


@router.post('/me', response_model=VerificationResponse, status_code=201)
async def start_verification(payload: VerificationStart, user: CurrentUser, session: Session):
    await lock_users(session, [user.id])
    current = await latest(session, user.id)
    if current is not None and current.status in {
        VerificationStatus.PENDING,
        VerificationStatus.VERIFIED,
    }:
        raise ApplicationError(
            'verification_in_progress', 'Verification is already pending or complete', 409
        )
    if current is not None and current.status == VerificationStatus.DRAFT:
        current.document_type = payload.document_type
        item = current
    else:
        item = IdentityVerification(
            user_id=user.id, status=VerificationStatus.DRAFT, document_type=payload.document_type
        )
        session.add(item)
    await commit(session)
    return view(item)


async def _upload(request: Request, user: User, session, field: Literal['document', 'selfie']):
    object_storage(request)
    user_id = user.id
    draft_id = (await editable_draft(session, user_id)).id
    await session.rollback()  # release the lock while processing the image
    content, _, _ = await read_image(request)
    key = f'verifications/{user_id}/{draft_id}/{field}-{uuid4()}.jpg'
    await store_image(request, key, content)
    try:
        draft = await editable_draft(session, user_id)
        if draft.id != draft_id:
            raise ApplicationError('verification_not_draft', 'Verification changed', 409)
        previous = getattr(draft, f'{field}_key')
        setattr(draft, f'{field}_key', key)
        await commit(session)
    except BaseException:
        await discard_image(request, key)
        raise
    if previous:
        await discard_image(request, previous)
    return view(draft)


@router.post(
    '/me/document',
    response_model=VerificationResponse,
    openapi_extra=IMAGE_REQUEST_BODY,
)
async def upload_document(request: Request, user: CurrentUser, session: Session):
    return await _upload(request, user, session, 'document')


@router.post(
    '/me/selfie',
    response_model=VerificationResponse,
    openapi_extra=IMAGE_REQUEST_BODY,
)
async def upload_selfie(request: Request, user: CurrentUser, session: Session):
    return await _upload(request, user, session, 'selfie')


@router.post('/me/submit', response_model=VerificationResponse)
async def submit_verification(user: CurrentUser, session: Session):
    draft = await editable_draft(session, user.id)
    if draft.document_key is None or draft.selfie_key is None:
        raise ApplicationError(
            'verification_incomplete', 'Upload both the document and the selfie', 422
        )
    draft.status = VerificationStatus.PENDING
    draft.submitted_at = utc_now()
    await commit(session)
    return view(draft)
