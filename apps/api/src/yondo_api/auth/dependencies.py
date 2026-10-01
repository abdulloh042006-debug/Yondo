from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.service import _as_utc, _now, _token_hash
from yondo_api.models.auth import AuthSession
from yondo_api.models.user import AccountStatus, User

_bearer = HTTPBearer(auto_error=False)


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory = request.app.state.db_session_factory
    async with factory() as session:
        yield session


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user: User
    session: AuthSession


async def get_authenticated_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthenticatedUser:
    if credentials is None:
        raise ApplicationError('authentication_required', 'Authentication is required', 401)
    auth_session = await session.scalar(
        select(AuthSession).where(
            AuthSession.access_token_hash == _token_hash(credentials.credentials)
        )
    )
    now = _now()
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or now >= _as_utc(auth_session.access_expires_at)
    ):
        raise ApplicationError(
            'invalid_access_token', 'The access token is invalid or expired', 401
        )
    user = await session.get(User, auth_session.user_id)
    if user is None or user.account_status in {AccountStatus.SUSPENDED, AccountStatus.BANNED}:
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    return AuthenticatedUser(user=user, session=auth_session)
