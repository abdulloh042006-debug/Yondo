from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.models.user import User


async def commit(
    session: AsyncSession,
    code: str = 'record_conflict',
    message: str = 'Duplicate or conflicting record',
) -> None:
    """Commit and translate integrity violations into a structured 409."""
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(code, message, 409) from exc


async def lock_users(session: AsyncSession, user_ids: Iterable[UUID]) -> dict[UUID, User]:
    """Lock user rows in a deterministic order so concurrent aggregates cannot deadlock."""
    ordered = sorted(set(user_ids), key=str)
    users: dict[UUID, User] = {}
    for user_id in ordered:
        user = await session.scalar(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None:
            raise ApplicationError('user_not_found', 'User not found', 404)
        users[user_id] = user
    return users
