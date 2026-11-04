from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.safety.models import UserBlock


async def blocked_either_way(session: AsyncSession, user_id: UUID) -> set[UUID]:
    rows = await session.execute(
        select(UserBlock.blocker_id, UserBlock.blocked_id).where(
            or_(UserBlock.blocker_id == user_id, UserBlock.blocked_id == user_id)
        )
    )
    return {blocked if blocker == user_id else blocker for blocker, blocked in rows}


async def is_blocked(session: AsyncSession, first: UUID, second: UUID) -> bool:
    return second in await blocked_either_way(session, first)


async def ensure_not_blocked(session: AsyncSession, first: UUID, second: UUID) -> None:
    if await is_blocked(session, first, second):
        raise ApplicationError('user_blocked', 'This interaction is blocked', 403)
