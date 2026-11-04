from collections.abc import Iterable
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class IdentityStatus(StrEnum):
    UNKNOWN = 'unknown'
    PENDING = 'pending'
    VERIFIED = 'verified'
    REJECTED = 'rejected'


class IdentityEligibility(Protocol):
    """Read-only adapter to Trust & Safety. Never infer identity from phone OTP or role."""

    async def get_status(self, session: AsyncSession, user_id: UUID) -> IdentityStatus: ...


class UnconfiguredIdentityEligibility:
    async def get_status(self, session: AsyncSession, user_id: UUID) -> IdentityStatus:
        return IdentityStatus.UNKNOWN


async def verified_user_ids(
    adapter: IdentityEligibility, session: AsyncSession, user_ids: Iterable[UUID]
) -> set[UUID]:
    """Return the subset of users whose identity is currently verified.

    Adapters may implement an efficient ``verified_user_ids`` batch read; otherwise
    each user is checked through the canonical single-user read.
    """
    ids = list(dict.fromkeys(user_ids))
    batch = getattr(adapter, 'verified_user_ids', None)
    if batch is not None:
        return set(await batch(session, ids))
    return {
        user_id
        for user_id in ids
        if IdentityStatus(await adapter.get_status(session, user_id)) == IdentityStatus.VERIFIED
    }
