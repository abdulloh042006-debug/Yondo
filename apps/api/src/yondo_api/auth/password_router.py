"""Username + password sign-in, registration step, change and reset (docs/login-password.md)."""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.account.deletion import erase_account
from yondo_api.api.errors import ApplicationError
from yondo_api.auth import age, passwords
from yondo_api.auth.age import current_age, ensure_phone_not_blocked
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
    # Required while the account has none (18+, owner 2026-11-19).
    date_of_birth: date | None = None


class DateOfBirth(BaseModel):
    model_config = ConfigDict(extra='forbid')
    date_of_birth: date


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


# Sessions that may set the password: a code sign-in, or a social sign-in (Telegram's verified
# phone, or an identity linked earlier with phone proof).
_SETUP_VIA = frozenset({'otp', 'telegram', 'google'})


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
        date_of_birth=user.date_of_birth,
        date_of_birth_required=user.date_of_birth is None,
        age_restricted=user.age_restricted_at is not None,
        age=current_age(user.date_of_birth, user.age),
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
    age = _now() - _as_utc(principal.session.created_at)
    if principal.session.via not in _SETUP_VIA or age > window:
        raise ApplicationError(
            'reauth_required', 'Sign in with a code again, then set the password', 403
        )
    if user.age_restricted_at is not None:
        raise age.age_restricted()
    if user.date_of_birth is None and (
        payload.date_of_birth is not None or settings.auth_require_date_of_birth
    ):
        # A brand-new sign-up (made in this registration window) under 18 is erased; an older
        # account that never set a password keeps its data and simply stays behind the gate.
        new_account = _now() - _as_utc(user.created_at) <= window
        await _set_date_of_birth(
            request, session, user, payload.date_of_birth, new_account=new_account
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


async def _set_date_of_birth(
    request: Request, session: AsyncSession, user: User, dob: date | None, *, new_account: bool
) -> None:
    """Store a declared date of birth (18+, owner/CEO 2026-11-19).

    Under 18, nothing is stored:
    - a new sign-up is erased at once (no account remains); only a salted hash of the phone is
      kept with a 30-day cooldown, so an instant retry with another date is refused;
    - an existing account is flagged ``age_restricted_at`` and stays locked until an admin clears
      it after an ID check (it can still delete itself or write to support).
    """
    if dob is None:
        raise ApplicationError('date_of_birth_required', 'Enter your date of birth', 422)
    try:
        years = age.checked_age(dob)
    except ApplicationError as exc:
        if exc.code == 'age_restricted':
            if new_account:
                await age.block_phone(session, _settings(request), user.phone_number)
                await erase_account(session, user, request.app.state.object_storage, _now())
            else:
                user.age_restricted_at = _now()
            await session.commit()
        raise
    user.date_of_birth = dob
    user.age = years


@router.put('/date-of-birth', response_model=UserResponse)
async def set_date_of_birth(
    payload: DateOfBirth, request: Request, principal: Principal, session: Session
) -> UserResponse:
    """One-time step for accounts made before 2026-11-19 (18+). It cannot be changed later."""
    user = await session.get(User, principal.user.id, with_for_update=True, populate_existing=True)
    if user.age_restricted_at is not None:  # no retry with another date; an admin checks the ID
        raise age.age_restricted()
    if user.date_of_birth is not None:
        raise ApplicationError('date_of_birth_already_set', 'The date of birth is already set', 409)
    await _set_date_of_birth(request, session, user, payload.date_of_birth, new_account=False)
    await session.commit()
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
        await ensure_phone_not_blocked(session, settings, phone_number)  # 18+ cooldown
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
