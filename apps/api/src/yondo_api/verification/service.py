from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.companions.integrations import IdentityStatus
from yondo_api.verification.models import IdentityVerification, VerificationStatus

logger = logging.getLogger(__name__)

_STATUS = {
    VerificationStatus.PENDING: IdentityStatus.PENDING,
    VerificationStatus.VERIFIED: IdentityStatus.VERIFIED,
    VerificationStatus.REJECTED: IdentityStatus.REJECTED,
}


async def latest(session: AsyncSession, user_id: UUID, *, submitted_only: bool = False):
    query = select(IdentityVerification).where(IdentityVerification.user_id == user_id)
    if submitted_only:
        query = query.where(IdentityVerification.status != VerificationStatus.DRAFT)
    return await session.scalar(
        query.order_by(
            IdentityVerification.created_at.desc(), IdentityVerification.id.desc()
        ).limit(1)
    )


class DatabaseIdentityEligibility:
    """Identity status from the latest submitted verification; drafts never count.

    This is the read-only adapter the companion activation gate and discovery use. A
    decision is final for that submission: there is no revocation endpoint yet, so a
    verified companion stays verified until a newer submission is decided.
    """

    async def get_status(self, session: AsyncSession, user_id: UUID) -> IdentityStatus:
        item = await latest(session, user_id, submitted_only=True)
        return _STATUS.get(item.status, IdentityStatus.UNKNOWN) if item else IdentityStatus.UNKNOWN


async def erase_verification_images(
    session: AsyncSession, user_id: UUID, storage, now: datetime | None = None
) -> None:
    """Account erasure: delete document/selfie objects; keep only the de-identified decision.

    A key is cleared only after its object was deleted. Without storage, or when a delete
    fails, the private key stays on the row so the object can still be found and removed.
    """
    now = now or datetime.now(UTC)
    for item in await session.scalars(
        select(IdentityVerification).where(IdentityVerification.user_id == user_id)
    ):
        for field in ('document_key', 'selfie_key'):
            key = getattr(item, field)
            if not key:
                continue
            if storage is None:
                logger.warning('No object storage: verification image kept, id=%s', item.id)
                continue
            try:
                await storage.delete(key)
            except Exception:  # the key is kept so a later run can retry
                logger.exception('Verification image not deleted: id=%s', item.id)
                continue
            setattr(item, field, None)
        item.review_note = None
        item.updated_at = now


DRAFT_MAX_AGE = timedelta(hours=24)


async def delete_images(item: IdentityVerification, storage) -> bool:
    """Delete the item's objects; clear each key only after its delete. True if none remain."""
    for field in ('document_key', 'selfie_key'):
        key = getattr(item, field)
        if not key:
            continue
        if storage is None:
            logger.warning('No object storage: verification image kept, id=%s', item.id)
            continue
        try:
            await storage.delete(key)
        except Exception:  # the key is kept so a later run can retry
            logger.exception('Verification image not deleted: id=%s', item.id)
            continue
        setattr(item, field, None)
    return item.document_key is None and item.selfie_key is None


async def purge_decided_images(
    session: AsyncSession, storage, retention_days: int, now: datetime | None = None
) -> int:
    """Jobs: delete images of verified/rejected submissions decided more than retention ago."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days)
    items = await session.scalars(
        select(IdentityVerification).where(
            IdentityVerification.status.in_(
                [VerificationStatus.VERIFIED, VerificationStatus.REJECTED]
            ),
            IdentityVerification.reviewed_at <= cutoff,
            (IdentityVerification.document_key.is_not(None))
            | (IdentityVerification.selfie_key.is_not(None)),
        )
    )
    cleared = 0
    for item in items:
        cleared += await delete_images(item, storage)
    await session.commit()
    return cleared


async def purge_abandoned_drafts(
    session: AsyncSession, storage, now: datetime | None = None
) -> int:
    """Jobs: remove drafts untouched for 24 h (never submitted) with their objects."""
    cutoff = (now or datetime.now(UTC)) - DRAFT_MAX_AGE
    items = await session.scalars(
        select(IdentityVerification).where(
            IdentityVerification.status == VerificationStatus.DRAFT,
            IdentityVerification.updated_at <= cutoff,
        )
    )
    removed = 0
    for item in items:
        if await delete_images(item, storage):
            await session.execute(
                delete(IdentityVerification).where(IdentityVerification.id == item.id)
            )
            removed += 1
    await session.commit()
    return removed
