from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
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
