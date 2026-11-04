from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.dependencies import AuthenticatedUser, get_authenticated_user, get_db_session
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType

Session = Annotated[AsyncSession, Depends(get_db_session)]
Principal = Annotated[AuthenticatedUser, Depends(get_authenticated_user)]


async def has_role(session: AsyncSession, user: User, role: UserRoleType) -> bool:
    return await session.get(UserRole, (user.id, role)) is not None


def require_active(user: User) -> None:
    """New marketplace actions require an active account (not pending/restricted)."""
    if user.account_status != AccountStatus.ACTIVE:
        raise ApplicationError(
            'account_not_active',
            'Complete your profile; restricted accounts cannot perform this action',
            403,
        )


async def current_user(principal: Principal) -> User:
    return principal.user


async def admin_user(principal: Principal, session: Session) -> User:
    user = principal.user
    if user.account_status != AccountStatus.ACTIVE or not await has_role(
        session, user, UserRoleType.ADMIN
    ):
        raise ApplicationError('admin_required', 'Administrator access is required', 403)
    return user


CurrentUser = Annotated[User, Depends(current_user)]
AdminUser = Annotated[User, Depends(admin_user)]
