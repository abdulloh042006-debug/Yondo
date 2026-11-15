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


# Paths an account without username + password may still use when the setup gate is on.
_SETUP_ALLOWED = ('/auth/', '/legal/')


async def get_authenticated_user(
    request: Request,
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
    if user is None or user.account_status in {
        AccountStatus.SUSPENDED,
        AccountStatus.BANNED,
        AccountStatus.DELETED,
    }:
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    settings = request.app.state.settings
    if settings.auth_require_password_setup and (
        user.password_hash is None or user.username is None
    ):
        path = request.url.path.removeprefix(settings.api_v1_prefix)
        if not path.startswith(_SETUP_ALLOWED):
            raise ApplicationError(
                'password_setup_required', 'Set a username and password first', 403
            )
    return AuthenticatedUser(user=user, session=auth_session)
