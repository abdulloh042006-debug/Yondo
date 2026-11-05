"""ID + selfie verification: user submission and administrator review."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from anyio import CancelScope, to_thread
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from yondo_api.admin.models import AdminAuditEvent
from yondo_api.api.errors import ApplicationError
from yondo_api.companions import service as companion_service
from yondo_api.companions.dependencies import Admin, Principal, Session, object_storage
from yondo_api.companions.photos import IMAGE_TYPES, compensate_upload, process_image
from yondo_api.models.user import AccountStatus
from yondo_api.verification.models import IdentityVerification, VerificationStatus
from yondo_api.verification.service import latest

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/verification', tags=['verification'])
admin_router = APIRouter(prefix='/admin/verifications', tags=['admin verification'])
IMAGE_URL_SECONDS = 300
IMAGE_BODY = {
    'requestBody': {
        'required': True,
        'content': {
            mime: {'schema': {'type': 'string', 'format': 'binary'}}
            for mime in IMAGE_TYPES.values()
        },
    }
}


class VerificationStart(BaseModel):
    model_config = ConfigDict(extra='forbid')
    document_type: Literal['passport', 'id_card', 'driver_license']


class VerificationRead(BaseModel):
    id: UUID
    status: Literal['draft', 'pending', 'verified', 'rejected']
    document_type: str
    has_document: bool
    has_selfie: bool
    submitted_at: datetime | None
    reviewed_at: datetime | None
    review_note: str | None


class AdminVerificationRead(VerificationRead):
    user_id: UUID
    document_url: str | None
    selfie_url: str | None


class VerificationDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: Literal['approve', 'reject']
    note: str = Field(
        min_length=1,
        max_length=2000,
        description='Shown to the user in GET /verification/me; erased with the account.',
    )


def read(item: IdentityVerification) -> VerificationRead:
    return VerificationRead(
        id=item.id,
        status=item.status,
        document_type=item.document_type,
        has_document=item.document_key is not None,
        has_selfie=item.selfie_key is not None,
        submitted_at=item.submitted_at,
        reviewed_at=item.reviewed_at,
        review_note=item.review_note,
    )


async def _url(storage, key: str | None) -> str | None:
    if not key or storage is None:
        return None
    try:
        return await storage.create_download_url(key, IMAGE_URL_SECONDS)
    except Exception:
        return None


async def admin_read(request: Request, item: IdentityVerification) -> AdminVerificationRead:
    storage = request.app.state.object_storage
    return AdminVerificationRead(
        **read(item).model_dump(),
        user_id=item.user_id,
        document_url=await _url(storage, item.document_key),
        selfie_url=await _url(storage, item.selfie_key),
    )


def check_usable(principal) -> None:
    if principal.user.account_status not in {
        AccountStatus.ACTIVE,
        AccountStatus.VERIFICATION_PENDING,
    }:
        raise ApplicationError('verification_forbidden', 'This operation is not permitted', 403)


async def draft_for(session, user_id: UUID) -> IdentityVerification:
    await companion_service.locked_user(session, user_id)
    item = await latest(session, user_id)
    if item is None or item.status != VerificationStatus.DRAFT:
        raise ApplicationError('verification_not_draft', 'Start a verification first', 409)
    return item


@router.get('/me', response_model=VerificationRead | None)
async def my_verification(principal: Principal, session: Session):
    item = await latest(session, principal.user.id)
    return read(item) if item else None


@router.post('/me', response_model=VerificationRead, status_code=201)
async def start(payload: VerificationStart, principal: Principal, session: Session):
    check_usable(principal)
    user_id = principal.user.id
    await companion_service.locked_user(session, user_id)
    current = await latest(session, user_id)
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
            user_id=user_id, status=VerificationStatus.DRAFT, document_type=payload.document_type
        )
        session.add(item)
    await session.commit()
    return read(item)


async def _reconcile_failed_save(request: Request, storage, draft_id, field, key) -> None:
    """Delete the new object only when a fresh transaction shows the row does not use it."""
    try:
        with CancelScope(shield=True):
            async with request.app.state.db_session_factory() as fresh:
                row = await fresh.get(IdentityVerification, draft_id)
                saved = row is not None and getattr(row, f'{field}_key') == key
    except Exception:
        # Commit outcome unknown: keep the object; the private key in the log allows cleanup.
        logger.exception('Verification upload outcome unknown: storage_key=%s', key)
        return
    if not saved:
        await compensate_upload(storage, key)


async def _upload(request: Request, principal, session, field: str) -> VerificationRead:
    check_usable(principal)
    storage = object_storage(request)
    user_id = principal.user.id
    draft_id = (await draft_for(session, user_id)).id
    await session.rollback()  # do not hold the user lock while decoding the image
    settings = request.app.state.settings
    content_type = request.headers.get('content-type', '').split(';')[0].strip()
    if content_type not in IMAGE_TYPES.values():
        raise ApplicationError('invalid_photo_type', 'A JPEG, PNG or WebP image is required', 415)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > settings.companion_photo_max_bytes:
            raise ApplicationError('photo_too_large', 'Image exceeds the byte limit', 413)
        data.extend(chunk)
    # Re-encoded without EXIF/location data, like profile photos.
    content, _, _ = await to_thread.run_sync(
        process_image,
        data,
        content_type,
        settings,
        limiter=request.app.state.companion_image_limiter,
    )
    key = f'verifications/{user_id}/{draft_id}/{field}-{uuid4()}.jpg'

    async def chunks():
        yield content

    try:
        await storage.upload(key, chunks(), 'image/jpeg')
    except asyncio.CancelledError:
        await compensate_upload(storage, key)
        raise
    except Exception as exc:
        await compensate_upload(storage, key)
        raise ApplicationError('storage_unavailable', 'Image upload failed', 503) from exc
    try:
        draft = await draft_for(session, user_id)
        if draft.id != draft_id:
            raise ApplicationError('verification_not_draft', 'Verification changed', 409)
        previous = getattr(draft, f'{field}_key')
        setattr(draft, f'{field}_key', key)
        await session.commit()
    except BaseException:
        await _reconcile_failed_save(request, storage, draft_id, field, key)
        raise
    if previous:
        await compensate_upload(storage, previous)
    return read(draft)


@router.post('/me/document', response_model=VerificationRead, openapi_extra=IMAGE_BODY)
async def upload_document(request: Request, principal: Principal, session: Session):
    """Raw JPEG/PNG/WebP photo of the identity document."""
    return await _upload(request, principal, session, 'document')


@router.post('/me/selfie', response_model=VerificationRead, openapi_extra=IMAGE_BODY)
async def upload_selfie(request: Request, principal: Principal, session: Session):
    """Raw JPEG/PNG/WebP selfie for comparison with the document photo."""
    return await _upload(request, principal, session, 'selfie')


@router.post('/me/submit', response_model=VerificationRead)
async def submit(principal: Principal, session: Session):
    check_usable(principal)
    draft = await draft_for(session, principal.user.id)
    if draft.document_key is None or draft.selfie_key is None:
        raise ApplicationError(
            'verification_incomplete', 'Upload both the document and the selfie', 422
        )
    draft.status = VerificationStatus.PENDING
    draft.submitted_at = datetime.now(UTC)
    await session.commit()
    return read(draft)


@admin_router.get('', response_model=list[AdminVerificationRead])
async def queue(
    request: Request,
    admin: Admin,
    session: Session,
    status: Literal['pending', 'verified', 'rejected'] = 'pending',
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    items = await session.scalars(
        select(IdentityVerification)
        .where(IdentityVerification.status == status)
        .order_by(IdentityVerification.submitted_at, IdentityVerification.id)
        .limit(limit)
    )
    return [await admin_read(request, item) for item in items]


@admin_router.post('/{verification_id}/decision', response_model=AdminVerificationRead)
async def decide(
    verification_id: UUID,
    payload: VerificationDecision,
    request: Request,
    admin: Admin,
    session: Session,
):
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
    approved = payload.decision == 'approve'
    item.status = VerificationStatus.VERIFIED if approved else VerificationStatus.REJECTED
    item.reviewed_at = datetime.now(UTC)
    item.reviewed_by = admin.id
    item.review_note = payload.note
    session.add(
        AdminAuditEvent(
            admin_id=admin.id,
            target_id=item.user_id,
            action='identity_verified' if approved else 'identity_rejected',
            # Not the free-text note: audit rows outlive account erasure.
            reason=f'identity_verification:{item.id}',
        )
    )
    await session.commit()
    return await admin_read(request, item)
