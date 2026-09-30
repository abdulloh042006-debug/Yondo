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
