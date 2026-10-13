from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.phone import normalize_uzbekistan_phone
from yondo_api.auth.providers import OtpDeliveryProvider
from yondo_api.config import Settings
from yondo_api.models.auth import AuthSession, OtpChallenge
from yondo_api.models.user import AccountStatus, User

OTP_LIFETIME = timedelta(minutes=5)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
OTP_MAX_ATTEMPTS = 3
OTP_LOCKOUT = timedelta(seconds=60)


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _otp_hash(settings: Settings, phone_number: str, code: str) -> bytes:
    key = settings.auth_otp_pepper.get_secret_value().encode()
    return hmac.digest(key, f'{phone_number}:{code}'.encode(), 'sha256')


def _token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def _new_token() -> str:
    return secrets.token_urlsafe(32)


@dataclass(frozen=True, slots=True)
class IssuedOtp:
    development_code: str | None


async def issue_otp(
    session: AsyncSession,
    phone: str,
    settings: Settings,
    provider: OtpDeliveryProvider,
) -> IssuedOtp:
    phone_number = normalize_uzbekistan_phone(phone)
    now = _now()
    challenge = await session.get(OtpChallenge, phone_number, with_for_update=True)
    if challenge is not None and now < _as_utc(challenge.issued_at) + OTP_RESEND_COOLDOWN:
        raise ApplicationError('otp_resend_cooldown', 'Wait before requesting another code', 429)

    code = f'{secrets.randbelow(1_000_000):06d}'
    delivery = await provider.deliver(phone_number, code)
    if challenge is None:
        challenge = OtpChallenge(
            phone_number=phone_number,
            code_hash=_otp_hash(settings, phone_number, code),
            issued_at=now,
            expires_at=now + OTP_LIFETIME,
            failed_attempts=0,
            blocked_until=None,
        )
        session.add(challenge)
    else:
        challenge.code_hash = _otp_hash(settings, phone_number, code)
        challenge.issued_at = now
        challenge.expires_at = now + OTP_LIFETIME
        challenge.failed_attempts = 0
        challenge.blocked_until = None
    await session.commit()
    return IssuedOtp(delivery.development_code)


async def verify_otp(
    session: AsyncSession, phone: str, code: str, settings: Settings
) -> tuple[User, TokenResponseData]:
    phone_number = normalize_uzbekistan_phone(phone)
    now = _now()
    challenge = await session.get(OtpChallenge, phone_number, with_for_update=True)
    if challenge is None:
        raise ApplicationError('invalid_otp', 'The verification code is invalid or expired', 401)

    blocked_until = _as_utc(challenge.blocked_until) if challenge.blocked_until else None
    if blocked_until is not None and now < blocked_until:
        raise ApplicationError('otp_temporarily_blocked', 'Too many attempts; try again later', 429)
    if blocked_until is not None:
        challenge.failed_attempts = 0
        challenge.blocked_until = None

    if now >= _as_utc(challenge.expires_at):
        await session.delete(challenge)
        await session.commit()
        raise ApplicationError('otp_expired', 'The verification code has expired', 401)

    if not hmac.compare_digest(challenge.code_hash, _otp_hash(settings, phone_number, code)):
        challenge.failed_attempts += 1
        if challenge.failed_attempts >= OTP_MAX_ATTEMPTS:
            challenge.blocked_until = now + OTP_LOCKOUT
        await session.commit()
        raise ApplicationError('invalid_otp', 'The verification code is invalid', 401)

    user = await session.scalar(select(User).where(User.phone_number == phone_number))
    if user is not None and user.account_status in {
        AccountStatus.SUSPENDED,
        AccountStatus.BANNED,
    }:
        await session.delete(challenge)
        await session.commit()
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)

    await session.delete(challenge)
    if user is None:
        user = User(phone_number=phone_number, account_status=AccountStatus.VERIFICATION_PENDING)
        session.add(user)
        await session.flush()
    token_data = await create_session(session, user, settings, now)
    await session.commit()
    return user, token_data


@dataclass(frozen=True, slots=True)
class TokenResponseData:
    access_token: str
    refresh_token: str
    expires_in: int


async def create_session(
    session: AsyncSession, user: User, settings: Settings, now: datetime
) -> TokenResponseData:
    access_token = _new_token()
    refresh_token = _new_token()
    access_lifetime = settings.auth_access_token_lifetime_seconds
    refresh_lifetime = settings.auth_refresh_token_lifetime_seconds
    session.add(
        AuthSession(
            user_id=user.id,
            access_token_hash=_token_hash(access_token),
            refresh_token_hash=_token_hash(refresh_token),
            access_expires_at=now + timedelta(seconds=access_lifetime),
            refresh_expires_at=now + timedelta(seconds=refresh_lifetime),
        )
    )
    await session.flush()
    return TokenResponseData(access_token, refresh_token, access_lifetime)


async def rotate_refresh_token(
    session: AsyncSession, refresh_token: str, settings: Settings
) -> TokenResponseData:
    now = _now()
    auth_session = await session.scalar(
        select(AuthSession)
        .where(AuthSession.refresh_token_hash == _token_hash(refresh_token))
        .with_for_update()
    )
    if (
        auth_session is None
        or auth_session.revoked_at is not None
        or now >= _as_utc(auth_session.refresh_expires_at)
    ):
        raise ApplicationError(
            'invalid_refresh_token', 'The refresh token is invalid or expired', 401
        )

    user = await session.get(User, auth_session.user_id)
    if user is None or user.account_status in {AccountStatus.SUSPENDED, AccountStatus.BANNED}:
        raise ApplicationError(
            'invalid_refresh_token', 'The refresh token is invalid or expired', 401
        )
    access_token = _new_token()
    next_refresh_token = _new_token()
    lifetime = settings.auth_access_token_lifetime_seconds
    auth_session.access_token_hash = _token_hash(access_token)
    auth_session.refresh_token_hash = _token_hash(next_refresh_token)
    auth_session.access_expires_at = now + timedelta(seconds=lifetime)
    await session.commit()
    return TokenResponseData(access_token, next_refresh_token, lifetime)


async def revoke_session(session: AsyncSession, session_id: UUID) -> None:
    auth_session = await session.get(AuthSession, session_id, with_for_update=True)
    if auth_session is not None and auth_session.revoked_at is None:
        auth_session.revoked_at = _now()
        await session.commit()
