"""Shared block gate used by booking and private chat."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.safety.models import UserBlock


async def blocked_between(session: AsyncSession, user_a: UUID, user_b: UUID | None) -> bool:
    if user_b is None:
        return True
    return bool(
        await session.scalar(
            select(UserBlock.id).where(
                or_(
                    (UserBlock.blocker_id == user_a) & (UserBlock.blocked_id == user_b),
                    (UserBlock.blocker_id == user_b) & (UserBlock.blocked_id == user_a),
                )
            )
        )
    )
