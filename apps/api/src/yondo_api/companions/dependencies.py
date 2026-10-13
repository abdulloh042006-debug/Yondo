from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.dependencies import AuthenticatedUser, get_authenticated_user, get_db_session
from yondo_api.companions import service
from yondo_api.models.user import User, UserRoleType

Session = Annotated[AsyncSession, Depends(get_db_session)]
Principal = Annotated[AuthenticatedUser, Depends(get_authenticated_user)]


async def companion_owner(principal: Principal, session: Session) -> User:
    user = await service.locked_user(session, principal.user.id)
    await service.require_role(session, user, UserRoleType.COMPANION)
    return user


async def companion_admin(principal: Principal, session: Session) -> User:
    await service.require_role(session, principal.user, UserRoleType.ADMIN)
    return principal.user


def object_storage(request: Request):
    storage = request.app.state.object_storage
    if storage is None:
        raise ApplicationError('storage_unavailable', 'Object storage is not configured', 503)
    return storage


Owner = Annotated[User, Depends(companion_owner)]
Admin = Annotated[User, Depends(companion_admin)]
