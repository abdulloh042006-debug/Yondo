"""Username + password sign-in, registration step, change and reset (docs/login-password.md)."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.auth import passwords
from yondo_api.auth.dependencies import AuthenticatedUser, get_authenticated_user, get_db_session
from yondo_api.auth.phone import normalize_uzbekistan_phone
from yondo_api.auth.schemas import OtpValue, TokenResponse, UserResponse
from yondo_api.auth.service import consume_otp, create_session
from yondo_api.config import Settings
from yondo_api.models.auth import AuthSession, PasswordLoginGuard
from yondo_api.models.user import AccountStatus, User, UserRole

router = APIRouter(prefix='/auth', tags=['authentication'])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Principal = Annotated[AuthenticatedUser, Depends(get_authenticated_user)]
PasswordValue = Annotated[SecretStr, Field(min_length=1, max_length=1024)]


class PasswordLogin(BaseModel):
    model_config = ConfigDict(extra='forbid')
    # Username or phone number.
    login: str = Field(min_length=1, max_length=64)
    password: PasswordValue


class Registration(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1, max_length=64)
    password: PasswordValue


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    current_password: PasswordValue
    new_password: PasswordValue


class PasswordReset(BaseModel):
    model_config = ConfigDict(extra='forbid')
    phone_number: str = Field(min_length=9, max_length=32)
    code: OtpValue
    new_password: PasswordValue


class UsernameAvailability(BaseModel):
    username: str
    available: bool
    reason: Literal['invalid', 'reserved', 'taken'] | None = None


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _ip_check(request: Request, bucket: str) -> None:
    ip = request.client.host if request.client else None
    request.app.state.password_ip_limiter.check(bucket, ip)


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _tokens(data) -> TokenResponse:
    return TokenResponse(
        access_token=data.access_token, refresh_token=data.refresh_token, expires_in=data.expires_in
    )


async def user_response(session: AsyncSession, user: User) -> UserResponse:
    roles = await session.scalars(select(UserRole.role).where(UserRole.user_id == user.id))
    return UserResponse(
        id=user.id,
        phone_number=user.phone_number,
        username=user.username,
        has_password=user.password_hash is not None,
        password_setup_required=user.password_hash is None or user.username is None,
        age=user.age,
        gender=user.gender,
        city=user.city,
        ui_locale=user.ui_locale,
        roles=list(roles),
        created_at=user.created_at,
    )


async def _clear_guard(session: AsyncSession, user: User) -> None:
    guard = await session.get(PasswordLoginGuard, passwords.subject_for_user(user.id))
    if guard is not None:
        await session.delete(guard)


@router.get('/username/available', response_model=UsernameAvailability)
async def username_available(
    request: Request, session: Session, username: str = Query(min_length=1, max_length=64)
) -> UsernameAvailability:
    """Deliberate availability check for the registration form (rate-limited per IP)."""
    _ip_check(request, 'username')
    name = passwords.normalize_username(username)
    problem = passwords.username_problem(name)
    if problem is None and await session.scalar(select(User.id).where(User.username == name)):
        problem = 'taken'
    return UsernameAvailability(username=name, available=problem is None, reason=problem)


@router.post('/registration', response_model=UserResponse)
async def complete_registration(
    payload: Registration, request: Request, principal: Principal, session: Session
) -> UserResponse:
    """Set username + password after a code (OTP) sign-in; this completes the account."""
    settings = _settings(request)
    user = await session.get(User, principal.user.id, with_for_update=True, populate_existing=True)
    if user.password_hash is not None and user.username is not None:
        raise ApplicationError('registration_complete', 'The account is already set up', 409)
    window = timedelta(seconds=settings.auth_registration_window_seconds)
    if principal.session.via != 'otp' or _now() - _as_utc(principal.session.created_at) > window:
        raise ApplicationError(
            'reauth_required', 'Sign in with a code again, then set the password', 403
        )
    name = passwords.normalize_username(payload.username)
    if user.username is not None and user.username != name:
        raise ApplicationError('username_already_set', 'The username is already set', 409)
    problem = passwords.username_problem(name)
    if problem == 'invalid':
        raise ApplicationError('invalid_username', 'The username does not meet the rules', 422)
    if problem == 'reserved':
        raise ApplicationError('username_unavailable', 'This username is not available', 409)
    password = payload.password.get_secret_value()
    passwords.check_password_rules(password, user.phone_number)
    user.username = name
    user.password_hash = await passwords.hash_password(password, settings.auth_scrypt_log_n)
    user.password_changed_at = _now()
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            'username_unavailable', 'This username is not available', 409
        ) from exc
    await session.refresh(user)
    return await user_response(session, user)


@router.post('/password/login', response_model=TokenResponse)
async def password_login(
    payload: PasswordLogin, request: Request, session: Session
) -> TokenResponse:
    """Username or phone + password. Unknown login, no password or wrong password: one answer."""
    settings = _settings(request)
    _ip_check(request, 'password')
    raw = payload.login.strip()
    user = None
    normalized = passwords.normalize_username(raw)
    if raw[:1].isalpha():
        user = await session.scalar(select(User).where(User.username == normalized))
    else:
        try:
            normalized = normalize_uzbekistan_phone(raw)
        except ApplicationError:
            pass
        else:
            user = await session.scalar(select(User).where(User.phone_number == normalized))
    subject = (
        passwords.subject_for_user(user.id) if user else passwords.subject_for_unknown(normalized)
    )
    guard = await passwords.locked_guard(session, subject)
    passwords.ensure_not_blocked(guard)
    ok = await passwords.verify_password(
        payload.password.get_secret_value(),
        user.password_hash if user else None,
        settings.auth_scrypt_log_n,
    )
    if not ok:
        passwords.record_failure(guard)
        await session.commit()
        raise passwords.invalid_credentials()
    if user.account_status in {
        AccountStatus.SUSPENDED,
        AccountStatus.BANNED,
        AccountStatus.DELETED,
    }:
        await session.commit()
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    await passwords.discard_guard(session, guard)
    tokens = await create_session(session, user, settings, _now(), via='password')
    await session.commit()
    return _tokens(tokens)


@router.put('/password', status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange, request: Request, principal: Principal, session: Session
) -> Response:
    """Needs the current password; signs out every OTHER session."""
    settings = _settings(request)
    user = await session.get(User, principal.user.id, populate_existing=True)
    if user.password_hash is None:
        raise ApplicationError('password_not_set', 'Set a password in the registration step', 409)
    guard = await passwords.locked_guard(session, passwords.subject_for_user(user.id))
    passwords.ensure_not_blocked(guard)
    if not await passwords.verify_password(
        payload.current_password.get_secret_value(), user.password_hash, settings.auth_scrypt_log_n
    ):
        passwords.record_failure(guard)
        await session.commit()
        raise passwords.invalid_credentials()
    new_password = payload.new_password.get_secret_value()
    passwords.check_password_rules(new_password, user.phone_number)
    now = _now()
    user.password_hash = await passwords.hash_password(new_password, settings.auth_scrypt_log_n)
    user.password_changed_at = now
    await passwords.discard_guard(session, guard)
    await session.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.id != principal.session.id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post('/password/reset', response_model=TokenResponse)
async def reset_password(
    payload: PasswordReset, request: Request, session: Session
) -> TokenResponse:
    """Code from POST /auth/otp/request + a new password; signs out ALL sessions."""
    settings = _settings(request)
    _ip_check(request, 'reset')
    phone_number = normalize_uzbekistan_phone(payload.phone_number)
    new_password = payload.new_password.get_secret_value()
    passwords.check_password_rules(new_password, phone_number)  # before the code is used up
    now = _now()
    user = await consume_otp(session, phone_number, payload.code, settings, now)
    if user is None:  # a code proves the phone: same as a code sign-in, the account is created
        user = User(phone_number=phone_number, account_status=AccountStatus.VERIFICATION_PENDING)
        session.add(user)
        await session.flush()
    user.password_hash = await passwords.hash_password(new_password, settings.auth_scrypt_log_n)
    user.password_changed_at = now
    await _clear_guard(session, user)
    await session.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    tokens = await create_session(session, user, settings, now, via='otp')
    await session.commit()
    return _tokens(tokens)
