from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.dependencies import (
    AuthenticatedUser,
    get_authenticated_user,
    get_db_session,
)
from yondo_api.auth.providers import OtpDeliveryProvider, OtpRateLimitHook
from yondo_api.auth.schemas import (
    OtpRequest,
    OtpRequestResponse,
    OtpVerification,
    RefreshRequest,
    RoleSelection,
    TokenResponse,
    UserProfileUpdate,
    UserResponse,
)
from yondo_api.auth.service import (
    TokenResponseData,
    issue_otp,
    revoke_session,
    rotate_refresh_token,
    verify_otp,
)
from yondo_api.config import Settings
from yondo_api.models.user import UserRole, UserRoleType

router = APIRouter(prefix='/auth', tags=['authentication'])
SessionDependency = Annotated[AsyncSession, Depends(get_db_session)]
PrincipalDependency = Annotated[AuthenticatedUser, Depends(get_authenticated_user)]


def _token_response(data: TokenResponseData) -> TokenResponse:
    return TokenResponse(
        access_token=data.access_token,
        refresh_token=data.refresh_token,
        expires_in=data.expires_in,
    )


@router.post(
    '/otp/request',
    response_model=OtpRequestResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_otp(
    payload: OtpRequest,
    request: Request,
    session: SessionDependency,
) -> OtpRequestResponse:
    limiter: OtpRateLimitHook = request.app.state.otp_rate_limit_hook
    provider: OtpDeliveryProvider = request.app.state.otp_provider
    settings: Settings = request.app.state.settings
    await limiter.check()
    issued = await issue_otp(session, payload.phone_number, settings, provider)
    development_otp = (
        issued.development_code
        if settings.environment in {'development', 'test'}
        else None
    )
    return OtpRequestResponse(
        message='If the number can receive a code, one has been sent.',
        expires_in_seconds=300,
        resend_after_seconds=60,
        development_otp=development_otp,
    )


@router.post('/otp/verify', response_model=TokenResponse)
async def verify(
    payload: OtpVerification,
    request: Request,
    session: SessionDependency,
) -> TokenResponse:
    user, tokens = await verify_otp(
        session, payload.phone_number, payload.code, request.app.state.settings
    )
    return _token_response(tokens)


@router.post('/refresh', response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    session: SessionDependency,
) -> TokenResponse:
    tokens = await rotate_refresh_token(session, payload.refresh_token, request.app.state.settings)
    return _token_response(tokens)


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    principal: PrincipalDependency,
    session: SessionDependency,
) -> Response:
    await revoke_session(session, principal.session.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/me', response_model=UserResponse)
async def get_profile(
    principal: PrincipalDependency,
    session: SessionDependency,
) -> UserResponse:
    roles = await session.scalars(
        select(UserRole.role).where(UserRole.user_id == principal.user.id)
    )
    user = principal.user
    return UserResponse(
        id=user.id,
        phone_number=user.phone_number,
        age=user.age,
        gender=user.gender,
        city=user.city,
        roles=list(roles),
        created_at=user.created_at,
    )


@router.put('/profile', response_model=UserResponse)
async def update_profile(
    payload: UserProfileUpdate,
    principal: PrincipalDependency,
    session: SessionDependency,
) -> UserResponse:
    for field in payload.model_fields_set:
        setattr(principal.user, field, getattr(payload, field))
    await session.commit()
    await session.refresh(principal.user)
    roles = await session.scalars(
        select(UserRole.role).where(UserRole.user_id == principal.user.id)
    )
    user = principal.user
    return UserResponse(
        id=user.id,
        phone_number=user.phone_number,
        age=user.age,
        gender=user.gender,
        city=user.city,
        roles=list(roles),
        created_at=user.created_at,
    )


@router.put('/roles', response_model=list[UserRoleType])
async def select_roles(
    payload: RoleSelection,
    principal: PrincipalDependency,
    session: SessionDependency,
) -> list[UserRoleType]:
    if UserRoleType.ADMIN in payload.roles:
        raise ApplicationError('invalid_role', 'The admin role cannot be self-assigned', 403)
    if len(set(payload.roles)) != len(payload.roles):
        raise ApplicationError('duplicate_role', 'Roles must be unique', 422)
    await session.execute(
        delete(UserRole).where(
            UserRole.user_id == principal.user.id,
            UserRole.role != UserRoleType.ADMIN,
        )
    )
    session.add_all(
        UserRole(user_id=principal.user.id, role=role) for role in payload.roles
    )
    await session.commit()
    return payload.roles
