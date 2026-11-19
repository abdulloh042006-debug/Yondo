"""Sign in / register with Telegram Login (OIDC) and Google (docs/login-telegram-google.md).

Rules (product decisions §3, CEO 2026-11-18):
- Accounts stay phone-anchored. A Telegram ID token with ``phone_number_verified: true`` counts
  as phone proof: it signs in to the account with that phone (linking the Telegram ``sub``) or
  creates it. Without a verified phone, and always for a new Google identity, the user proves a
  phone with a code (POST /auth/social/complete) before any account is created or linked.
- Never link by e-mail, and never link to an existing account without that account's phone proof.
- State, flow token, nonce and PKCE verifier are single-use with a short TTL; only hashes of the
  browser-held values are stored. Tokens, codes and ID tokens are never logged.
- Not configured: 503 ``provider_not_configured`` (the web hides the button).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from urllib.parse import quote, urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.dependencies import AuthenticatedUser, get_authenticated_user, get_db_session
from yondo_api.auth.oidc import JwksCache, provider_unreachable, verify_id_token
from yondo_api.auth.phone import normalize_uzbekistan_phone
from yondo_api.auth.schemas import OtpValue, TokenResponse
from yondo_api.auth.service import consume_otp, create_session
from yondo_api.auth.social_models import ExternalIdentity, SocialLoginChallenge
from yondo_api.auth.telegram_models import TelegramLink
from yondo_api.config import Settings
from yondo_api.models.user import AccountStatus, User

router = APIRouter(prefix='/auth/social', tags=['authentication'])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Principal = Annotated[AuthenticatedUser, Depends(get_authenticated_user)]

TELEGRAM_ISSUER = 'https://oauth.telegram.org'
TELEGRAM_AUTHORIZE_URL = f'{TELEGRAM_ISSUER}/auth'
TELEGRAM_TOKEN_URL = f'{TELEGRAM_ISSUER}/token'
TELEGRAM_JWKS_URL = f'{TELEGRAM_ISSUER}/.well-known/jwks.json'
TELEGRAM_SCOPES = ('openid', 'profile', 'phone', 'telegram:bot_access')
GOOGLE_ISSUERS = ('accounts.google.com', 'https://accounts.google.com')
GOOGLE_JWKS_URL = 'https://www.googleapis.com/oauth2/v3/certs'
Provider = Literal['telegram', 'google']
_UNAVAILABLE = {AccountStatus.SUSPENDED, AccountStatus.BANNED, AccountStatus.DELETED}


class SocialLogin:
    """Per-app state: JWKS caches and the HTTP transport (tests inject a mock transport)."""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport
        self.telegram_jwks = JwksCache(TELEGRAM_JWKS_URL)
        self.google_jwks = JwksCache(GOOGLE_JWKS_URL)

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.settings.social_login_timeout_seconds,
            transport=self.transport,
            follow_redirects=False,
        )


# ---- schemas -------------------------------------------------------------------------------


class SocialConfig(BaseModel):
    telegram: bool
    # Bot ID for the official Telegram JS library (public), or null = off.
    telegram_client_id: str | None
    # The authorization-code flow (mobile / system browser) is configured too.
    telegram_code_flow: bool
    # The web client ID for Google Identity Services (the first configured ID), or null = off.
    google_client_id: str | None


class LinkedIdentity(BaseModel):
    provider: Provider
    linked_at: datetime


class TelegramStart(BaseModel):
    model_config = ConfigDict(extra='forbid')
    redirect_uri: str | None = Field(default=None, max_length=512)


class TelegramStarted(BaseModel):
    authorization_url: str
    # Returned once; keep it in the browser (sessionStorage) and send it with the code.
    flow_token: str
    expires_in_seconds: int


class TelegramNonce(BaseModel):
    # Pass it to Telegram.Login.auth({nonce}); single-use, short-lived.
    nonce: str
    expires_in_seconds: int


class TelegramIdToken(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id_token: str = Field(min_length=1, max_length=8192)


class TelegramExchange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    code: str = Field(min_length=1, max_length=2048)
    state: str = Field(min_length=16, max_length=128)
    flow_token: str = Field(min_length=16, max_length=128)


class GoogleCredential(BaseModel):
    model_config = ConfigDict(extra='forbid')
    credential: str = Field(min_length=1, max_length=8192)


class SocialComplete(BaseModel):
    model_config = ConfigDict(extra='forbid')
    signup_token: str = Field(min_length=16, max_length=128)
    phone_number: str = Field(min_length=9, max_length=32)
    code: OtpValue


class SocialResult(BaseModel):
    # signed_in: tokens are set. phone_required: prove a phone with a code, then POST
    # /auth/social/complete with signup_token. linked: the provider was added to this account.
    status: Literal['signed_in', 'phone_required', 'linked']
    provider: Provider
    tokens: TokenResponse | None = None
    password_setup_required: bool | None = None
    signup_token: str | None = None
    expires_in_seconds: int | None = None


# ---- helpers -------------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _hash(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()


def _service(request: Request) -> SocialLogin:
    return request.app.state.social_login


def _ip_check(request: Request) -> None:
    ip = request.client.host if request.client else None
    request.app.state.password_ip_limiter.check('social', ip)


def not_configured() -> ApplicationError:
    return ApplicationError(
        'provider_not_configured', 'This sign-in method is not configured', 503
    )


def _state_invalid() -> ApplicationError:
    return ApplicationError(
        'social_state_invalid', 'The sign-in attempt expired or was already used', 400
    )


def _telegram_settings(request: Request, *, code_flow: bool = False) -> Settings:
    settings: Settings = request.app.state.settings
    enabled = settings.telegram_code_flow_enabled if code_flow else settings.telegram_login_enabled
    if not enabled:
        raise not_configured()
    return settings


async def _sign_in(
    session: AsyncSession, user: User, settings: Settings, provider: Provider
) -> SocialResult:
    tokens = await create_session(session, user, settings, _now(), via=provider)
    await session.commit()
    return SocialResult(
        status='signed_in',
        provider=provider,
        tokens=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
        ),
        password_setup_required=user.password_hash is None or user.username is None,
    )


def _ensure_available(user: User | None) -> User:
    if user is None or user.account_status in _UNAVAILABLE:
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    return user


async def _identity(session: AsyncSession, provider: str, subject: str) -> ExternalIdentity | None:
    return await session.scalar(
        select(ExternalIdentity).where(
            ExternalIdentity.provider == provider, ExternalIdentity.provider_subject == subject
        )
    )


async def _user_identity(
    session: AsyncSession, user_id: UUID, provider: str
) -> ExternalIdentity | None:
    return await session.scalar(
        select(ExternalIdentity).where(
            ExternalIdentity.user_id == user_id, ExternalIdentity.provider == provider
        )
    )


async def _add_identity(session: AsyncSession, user: User, provider: str, subject: str) -> None:
    if await _user_identity(session, user.id, provider) is not None:
        raise ApplicationError(
            'provider_already_linked', 'Another account of this provider is linked', 409
        )
    session.add(ExternalIdentity(provider=provider, provider_subject=subject, user_id=user.id))
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            'identity_in_use', 'This account is linked to another Yondo account', 409
        ) from exc


async def _record_bot_chat(session: AsyncSession, phone: str, telegram_user_id: int) -> None:
    """telegram:bot_access granted: the bot may DM this user, so later codes need no /start."""
    now = _now()
    await session.execute(
        delete(TelegramLink).where(
            (TelegramLink.telegram_user_id == telegram_user_id)
            | (TelegramLink.phone_number == phone)
        )
    )
    session.add(
        TelegramLink(
            phone_number=phone,
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_user_id,  # private chat id == user id
            linked_at=now,
        )
    )


async def _signup_ticket(
    session: AsyncSession,
    settings: Settings,
    provider: Provider,
    subject: str,
    telegram_user_id: int | None = None,
) -> SocialResult:
    token = secrets.token_urlsafe(32)
    lifetime = settings.social_login_lifetime_seconds
    session.add(
        SocialLoginChallenge(
            provider=provider,
            kind='signup',
            token_hash=_hash(token),
            provider_subject=subject,
            telegram_user_id=telegram_user_id,
            expires_at=_now() + timedelta(seconds=lifetime),
        )
    )
    await session.commit()
    return SocialResult(
        status='phone_required',
        provider=provider,
        signup_token=token,
        expires_in_seconds=lifetime,
    )


async def _link_to(
    session: AsyncSession, user: User, provider: Provider, subject: str
) -> SocialResult:
    existing = await _identity(session, provider, subject)
    if existing is not None and existing.user_id != user.id:
        raise ApplicationError(
            'identity_in_use', 'This account is linked to another Yondo account', 409
        )
    if existing is None:
        await _add_identity(session, user, provider, subject)
    await session.commit()
    return SocialResult(status='linked', provider=provider)


async def _cleanup(session: AsyncSession) -> None:
    await session.execute(
        delete(SocialLoginChallenge).where(
            SocialLoginChallenge.expires_at < _now() - timedelta(days=1)
        )
    )


# ---- endpoints -----------------------------------------------------------------------------


@router.get('/config', response_model=SocialConfig)
async def social_config(request: Request) -> SocialConfig:
    settings: Settings = request.app.state.settings
    google = settings.google_client_id_list
    client_id = settings.telegram_login_client_id.strip()
    return SocialConfig(
        telegram=settings.telegram_login_enabled,
        telegram_client_id=client_id or None,
        telegram_code_flow=settings.telegram_code_flow_enabled,
        google_client_id=google[0] if google else None,
    )


@router.get('/identities', response_model=list[LinkedIdentity])
async def list_identities(principal: Principal, session: Session) -> list[LinkedIdentity]:
    rows = await session.scalars(
        select(ExternalIdentity)
        .where(ExternalIdentity.user_id == principal.user.id)
        .order_by(ExternalIdentity.provider)
    )
    return [
        LinkedIdentity(provider=row.provider, linked_at=_as_utc(row.created_at)) for row in rows
    ]


@router.delete('/identities/{provider}', status_code=status.HTTP_204_NO_CONTENT)
async def unlink_identity(provider: Provider, principal: Principal, session: Session) -> Response:
    """Only with a password set, so the account always keeps a way in besides the phone code."""
    user = await session.get(User, principal.user.id, populate_existing=True)
    if user.password_hash is None:
        raise ApplicationError('password_not_set', 'Set a password before unlinking', 409)
    identity = await _user_identity(session, user.id, provider)
    if identity is None:
        raise ApplicationError('identity_not_linked', 'This provider is not linked', 404)
    await session.delete(identity)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _telegram_start(
    request: Request, session: AsyncSession, payload: TelegramStart, user_id: UUID | None
) -> TelegramStarted:
    settings = _telegram_settings(request, code_flow=True)
    _ip_check(request)
    allowed = settings.telegram_login_redirect_uri_list
    redirect_uri = payload.redirect_uri or allowed[0]
    if redirect_uri not in allowed:
        raise ApplicationError('invalid_redirect_uri', 'This redirect URI is not allowed', 422)
    state, flow_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    nonce, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')
    lifetime = settings.social_login_lifetime_seconds
    await _cleanup(session)
    session.add(
        SocialLoginChallenge(
            provider='telegram',
            kind='authorize',
            token_hash=_hash(state),
            binding_hash=_hash(flow_token),
            nonce=nonce,
            code_verifier=verifier,
            redirect_uri=redirect_uri,
            user_id=user_id,
            expires_at=_now() + timedelta(seconds=lifetime),
        )
    )
    await session.commit()
    query = urlencode(
        {
            'client_id': settings.telegram_login_client_id.strip(),
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(TELEGRAM_SCOPES),
            'state': state,
            'nonce': nonce,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        },
        quote_via=quote,
    )
    return TelegramStarted(
        authorization_url=f'{TELEGRAM_AUTHORIZE_URL}?{query}',
        flow_token=flow_token,
        expires_in_seconds=lifetime,
    )


@router.post('/telegram/start', response_model=TelegramStarted, status_code=201)
async def telegram_start(
    payload: TelegramStart, request: Request, session: Session
) -> TelegramStarted:
    """Sign in or register: returns the oauth.telegram.org URL to open (code flow + PKCE)."""
    return await _telegram_start(request, session, payload, None)


@router.post('/telegram/link/start', response_model=TelegramStarted, status_code=201)
async def telegram_link_start(
    payload: TelegramStart, request: Request, principal: Principal, session: Session
) -> TelegramStarted:
    """A signed-in user adds Telegram to the account (Settings)."""
    return await _telegram_start(request, session, payload, principal.user.id)


async def _telegram_tokens(
    service: SocialLogin, settings: Settings, challenge: SocialLoginChallenge, code: str
) -> tuple[dict, set[str]]:
    client_id = settings.telegram_login_client_id.strip()
    secret = settings.telegram_login_client_secret.get_secret_value()
    async with service.client() as client:
        try:
            response = await client.post(
                TELEGRAM_TOKEN_URL,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': challenge.redirect_uri,
                    'client_id': client_id,
                    'code_verifier': challenge.code_verifier,
                },
                auth=(client_id, secret),
            )
        except httpx.HTTPError as exc:
            raise provider_unreachable() from exc
        if response.status_code >= 500:
            raise provider_unreachable()
        try:
            body = response.json() if response.status_code == 200 else None
        except ValueError:
            body = None
        id_token = body.get('id_token') if isinstance(body, dict) else None
        if not isinstance(id_token, str):
            raise ApplicationError(
                'social_code_invalid', 'The sign-in code is invalid or expired', 401
            )
        claims = await verify_id_token(
            id_token,
            jwks=service.telegram_jwks,
            client=client,
            issuers=(TELEGRAM_ISSUER,),
            audiences=[client_id],
        )
    nonce = claims.get('nonce')
    # Telegram's docs do not promise to echo the nonce; when present it must match.
    if nonce is not None and not hmac.compare_digest(str(nonce), challenge.nonce or ''):
        raise ApplicationError('social_token_invalid', 'The sign-in token is invalid', 401)
    scope = body.get('scope')
    # RFC 6749 §5.1: no "scope" in the token response = the requested scopes were granted.
    granted = set(scope.split()) if isinstance(scope, str) else set(TELEGRAM_SCOPES)
    return claims, granted


def _verified_phone(claims: dict) -> str | None:
    phone = claims.get('phone_number')
    if claims.get('phone_number_verified') is not True or not isinstance(phone, str):
        return None
    try:
        return normalize_uzbekistan_phone(phone)
    except ApplicationError:
        return None  # not an Uzbekistan number: prove one with a code instead


@router.post('/telegram/exchange', response_model=SocialResult)
async def telegram_exchange(
    payload: TelegramExchange, request: Request, session: Session
) -> SocialResult:
    """The callback page sends code + state + flow token; the code is exchanged server-side."""
    settings = _telegram_settings(request, code_flow=True)
    _ip_check(request)
    now = _now()
    challenge = await session.scalar(
        select(SocialLoginChallenge).where(
            SocialLoginChallenge.token_hash == _hash(payload.state),
            SocialLoginChallenge.kind == 'authorize',
            SocialLoginChallenge.provider == 'telegram',
        )
    )
    if (
        challenge is None
        or challenge.consumed_at is not None
        or now >= _as_utc(challenge.expires_at)
        or not hmac.compare_digest(challenge.binding_hash or b'', _hash(payload.flow_token))
    ):
        raise _state_invalid()
    # Single use, even if the exchange below fails.
    used = await session.execute(
        update(SocialLoginChallenge)
        .where(SocialLoginChallenge.id == challenge.id, SocialLoginChallenge.consumed_at.is_(None))
        .values(consumed_at=now)
    )
    if used.rowcount != 1:
        raise _state_invalid()
    await session.commit()

    claims, granted = await _telegram_tokens(_service(request), settings, challenge, payload.code)
    return await _telegram_finish(session, settings, claims, granted, challenge.user_id)


async def _telegram_finish(
    session: AsyncSession,
    settings: Settings,
    claims: dict,
    granted: set[str],
    link_user_id: UUID | None,
) -> SocialResult:
    """Shared by both Telegram flows once the ID token is verified."""
    subject = claims['sub']
    phone = _verified_phone(claims) if 'phone' in granted else None
    tg_id = claims.get('id')
    tg_id = tg_id if isinstance(tg_id, int) and not isinstance(tg_id, bool) and tg_id > 0 else None
    bot_access = 'telegram:bot_access' in granted and tg_id is not None

    if link_user_id is not None:  # linking from Settings
        user = _ensure_available(await session.get(User, link_user_id))
        if bot_access and phone == user.phone_number:
            await _record_bot_chat(session, phone, tg_id)
        return await _link_to(session, user, 'telegram', subject)

    identity = await _identity(session, 'telegram', subject)
    if identity is not None:
        user = _ensure_available(await session.get(User, identity.user_id))
    elif phone is not None:
        user = await session.scalar(select(User).where(User.phone_number == phone))
        if user is None:
            user = User(phone_number=phone, account_status=AccountStatus.VERIFICATION_PENDING)
            session.add(user)
            await session.flush()
        _ensure_available(user)
        await _add_identity(session, user, 'telegram', subject)
    else:
        return await _signup_ticket(
            session, settings, 'telegram', subject, tg_id if bot_access else None
        )
    if bot_access and phone is not None and phone == user.phone_number:
        await _record_bot_chat(session, phone, tg_id)
    return await _sign_in(session, user, settings, 'telegram')


# ---- Telegram: official JS library (web) -----------------------------------------------------


async def _issue_nonce(
    request: Request, session: AsyncSession, user_id: UUID | None
) -> TelegramNonce:
    settings = _telegram_settings(request)
    _ip_check(request)
    nonce = secrets.token_urlsafe(32)
    lifetime = settings.social_login_lifetime_seconds
    await _cleanup(session)
    session.add(
        SocialLoginChallenge(
            provider='telegram',
            kind='nonce',
            token_hash=_hash(nonce),
            user_id=user_id,
            expires_at=_now() + timedelta(seconds=lifetime),
        )
    )
    await session.commit()
    return TelegramNonce(nonce=nonce, expires_in_seconds=lifetime)


@router.post('/telegram/nonce', response_model=TelegramNonce, status_code=201)
async def telegram_nonce(request: Request, session: Session) -> TelegramNonce:
    """A single-use nonce for Telegram.Login.auth; the ID token must carry it back."""
    return await _issue_nonce(request, session, None)


@router.post('/telegram/link/nonce', response_model=TelegramNonce, status_code=201)
async def telegram_link_nonce(
    request: Request, principal: Principal, session: Session
) -> TelegramNonce:
    return await _issue_nonce(request, session, principal.user.id)


async def _telegram_id_token(
    request: Request, session: AsyncSession, id_token: str, user_id: UUID | None
) -> SocialResult:
    settings = _telegram_settings(request)
    _ip_check(request)
    service = _service(request)
    async with service.client() as client:
        claims = await verify_id_token(
            id_token,
            jwks=service.telegram_jwks,
            client=client,
            issuers=(TELEGRAM_ISSUER,),
            audiences=[settings.telegram_login_client_id.strip()],
        )
    # The token reached the browser directly, so the nonce is what makes it single-use.
    nonce = claims.get('nonce')
    if not isinstance(nonce, str) or not 16 <= len(nonce) <= 128:
        raise ApplicationError('social_token_invalid', 'The sign-in token is invalid', 401)
    now = _now()
    used = await session.execute(
        update(SocialLoginChallenge)
        .where(
            SocialLoginChallenge.token_hash == _hash(nonce),
            SocialLoginChallenge.kind == 'nonce',
            SocialLoginChallenge.provider == 'telegram',
            SocialLoginChallenge.consumed_at.is_(None),
            SocialLoginChallenge.expires_at > now,
            SocialLoginChallenge.user_id.is_(None)
            if user_id is None
            else SocialLoginChallenge.user_id == user_id,
        )
        .values(consumed_at=now)
    )
    if used.rowcount != 1:
        raise _state_invalid()
    await session.commit()
    # The library asks for profile, phone and bot access ("write"); what was granted shows in the
    # claims (phone) or not at all (bot access): an unusable chat answers telegram_bot_unreachable
    # later and the bot link flow (/start) repairs it.
    return await _telegram_finish(session, settings, claims, set(TELEGRAM_SCOPES), user_id)


@router.post('/telegram', response_model=SocialResult)
async def telegram_sign_in(
    payload: TelegramIdToken, request: Request, session: Session
) -> SocialResult:
    """ID token from Telegram.Login.auth (official JS library) with a nonce from /telegram/nonce."""
    return await _telegram_id_token(request, session, payload.id_token, None)


@router.post('/telegram/link', response_model=SocialResult)
async def telegram_link(
    payload: TelegramIdToken, request: Request, principal: Principal, session: Session
) -> SocialResult:
    return await _telegram_id_token(request, session, payload.id_token, principal.user.id)


async def _google_subject(request: Request, credential: str) -> str:
    settings: Settings = request.app.state.settings
    audiences = settings.google_client_id_list
    if not audiences:
        raise not_configured()
    _ip_check(request)
    service = _service(request)
    async with service.client() as client:
        claims = await verify_id_token(
            credential,
            jwks=service.google_jwks,
            client=client,
            issuers=GOOGLE_ISSUERS,
            audiences=audiences,
        )
    return claims['sub']  # never the e-mail


@router.post('/google', response_model=SocialResult)
async def google_sign_in(
    payload: GoogleCredential, request: Request, session: Session
) -> SocialResult:
    """Google ID token (GIS credential). A new Google identity always needs a phone code."""
    subject = await _google_subject(request, payload.credential)
    settings: Settings = request.app.state.settings
    identity = await _identity(session, 'google', subject)
    if identity is None:
        await _cleanup(session)
        return await _signup_ticket(session, settings, 'google', subject)
    user = _ensure_available(await session.get(User, identity.user_id))
    return await _sign_in(session, user, settings, 'google')


@router.post('/google/link', response_model=SocialResult)
async def google_link(
    payload: GoogleCredential, request: Request, principal: Principal, session: Session
) -> SocialResult:
    subject = await _google_subject(request, payload.credential)
    user = _ensure_available(await session.get(User, principal.user.id))
    return await _link_to(session, user, 'google', subject)


@router.post('/complete', response_model=SocialResult)
async def complete_signup(
    payload: SocialComplete, request: Request, session: Session
) -> SocialResult:
    """Phone proof for a social identity: a code from POST /auth/otp/request (or the bot).

    The phone's account (existing or new) gets the identity linked and is signed in.
    """
    settings: Settings = request.app.state.settings
    _ip_check(request)
    now = _now()
    challenge = await session.scalar(
        select(SocialLoginChallenge).where(
            SocialLoginChallenge.token_hash == _hash(payload.signup_token),
            SocialLoginChallenge.kind == 'signup',
        )
    )
    if challenge is None or challenge.consumed_at is not None or now >= _as_utc(
        challenge.expires_at
    ):
        raise ApplicationError(
            'signup_token_invalid', 'The sign-up step expired; start again', 400
        )
    provider, subject = challenge.provider, challenge.provider_subject
    if await _identity(session, provider, subject) is not None:
        raise ApplicationError(
            'identity_in_use', 'This account is linked to another Yondo account', 409
        )
    phone = normalize_uzbekistan_phone(payload.phone_number)
    user = await consume_otp(session, phone, payload.code, settings, now)
    if user is None:
        user = User(phone_number=phone, account_status=AccountStatus.VERIFICATION_PENDING)
        session.add(user)
        await session.flush()
    await _add_identity(session, user, provider, subject)
    if challenge.telegram_user_id is not None:  # bot access was granted at Telegram
        await _record_bot_chat(session, phone, challenge.telegram_user_id)
    used = await session.execute(
        update(SocialLoginChallenge)
        .where(SocialLoginChallenge.id == challenge.id, SocialLoginChallenge.consumed_at.is_(None))
        .values(consumed_at=now)
    )
    if used.rowcount != 1:
        await session.rollback()
        raise ApplicationError(
            'signup_token_invalid', 'The sign-up step expired; start again', 400
        )
    # The phone code is the proof here, so the session counts as a code sign-in.
    tokens = await create_session(session, user, settings, now, via='otp')
    await session.commit()
    return SocialResult(
        status='signed_in',
        provider=provider,
        tokens=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
        ),
        password_setup_required=user.password_hash is None or user.username is None,
    )

