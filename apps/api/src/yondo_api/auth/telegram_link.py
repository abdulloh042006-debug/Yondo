"""Link a phone number to the user's private chat with the Yondo Telegram bot.

Flow (docs/login-telegram-bot.md):
1. Browser: POST /auth/telegram/link/start {phone_number} -> deep link t.me/<bot>?start=<token>
   and a poll token returned ONCE (only SHA-256 hashes of both are stored).
2. The user opens the bot; the bot service (owner's VPS) asks for the contact and checks
   ``contact.user_id == from.id``, then calls POST /auth/telegram/link/complete with the shared
   secret header. We verify, store the phone <-> Telegram link and send the code via the bot.
3. Browser polls GET /auth/telegram/link/status (header X-Yondo-Link-Poll), then the user types the
   code into the existing POST /auth/otp/verify. Later logins use POST /auth/otp/request directly.

Only private chats are supported: Telegram's private chat id equals the user id, so a completion
whose chat id differs from the user id (a group, a channel) is rejected.
"""

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.dependencies import get_db_session
from yondo_api.auth.phone import normalize_uzbekistan_phone
from yondo_api.auth.providers import OtpDelivery
from yondo_api.auth.service import issue_otp
from yondo_api.auth.telegram_bot import TelegramBotOtpProvider
from yondo_api.auth.telegram_models import (
    LinkChallengeStatus,
    TelegramLink,
    TelegramLinkChallenge,
)
from yondo_api.config import Settings

router = APIRouter(prefix='/auth/telegram/link', tags=['authentication'])
Session = Annotated[AsyncSession, Depends(get_db_session)]
MAX_STARTS_PER_PHONE = 5
START_WINDOW = timedelta(minutes=10)
_CHALLENGE = re.compile(r'[A-Za-z0-9_-]{16,64}')


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _hash(value: str) -> bytes:
    return hashlib.sha256(value.encode()).digest()


def attach_chat_lookup(provider: object, factory: async_sessionmaker) -> None:
    """Give the bot provider read access to verified links (used by /auth/otp/request)."""
    if not isinstance(provider, TelegramBotOtpProvider):
        return

    async def lookup(phone_number: str) -> int | None:
        async with factory() as session:
            link = await session.get(TelegramLink, phone_number)
            return link.telegram_chat_id if link else None

    provider.chat_lookup = lookup


def _bot(request: Request) -> tuple[Settings, TelegramBotOtpProvider]:
    settings: Settings = request.app.state.settings
    provider = request.app.state.otp_provider
    if settings.otp_provider != 'telegram_bot' or not isinstance(provider, TelegramBotOtpProvider):
        raise ApplicationError(
            'telegram_bot_unavailable', 'Telegram bot login is not enabled', 503
        )
    return settings, provider


class LinkConfig(BaseModel):
    enabled: bool
    bot_username: str | None


class LinkStart(BaseModel):
    model_config = ConfigDict(extra='forbid')
    phone_number: str = Field(min_length=1, max_length=32)


class LinkStarted(BaseModel):
    status: Literal['initiated']
    deep_link: str
    # Returned once; send it back in the X-Yondo-Link-Poll header to read the status.
    poll_token: str
    expires_in_seconds: int
    # True when this phone already has a verified chat: the client may go straight to
    # POST /auth/otp/request instead of opening the bot again.
    already_linked: bool


class LinkStatus(BaseModel):
    status: Literal['awaiting_contact', 'linked', 'otp_sent', 'expired', 'failed']
    failure_code: str | None = None
    expires_in_seconds: int


class LinkComplete(BaseModel):
    model_config = ConfigDict(extra='forbid')
    challenge: str = Field(min_length=1, max_length=64)
    phone_number: str = Field(min_length=1, max_length=32)
    telegram_user_id: int = Field(strict=True, gt=0, lt=2**63)
    telegram_chat_id: int = Field(strict=True, gt=0, lt=2**63)


class LinkCompleted(BaseModel):
    status: Literal['linked']


class _ChatProvider:
    """Delivers one code to an already verified chat (no lookup)."""

    def __init__(self, bot: TelegramBotOtpProvider, chat_id: int) -> None:
        self._bot, self._chat_id = bot, chat_id

    async def deliver(self, phone_number: str, code: str) -> OtpDelivery:
        await self._bot.send_code(self._chat_id, code)
        return OtpDelivery(channel='telegram')


@router.get('/config', response_model=LinkConfig)
async def link_config(request: Request) -> LinkConfig:
    settings: Settings = request.app.state.settings
    enabled = settings.otp_provider == 'telegram_bot'
    username = settings.telegram_bot_username if enabled else None
    return LinkConfig(enabled=enabled, bot_username=username)


@router.post('/start', response_model=LinkStarted, status_code=201)
async def start_link(payload: LinkStart, request: Request, session: Session) -> LinkStarted:
    settings, _ = _bot(request)
    await request.app.state.otp_rate_limit_hook.check()
    phone_number = normalize_uzbekistan_phone(payload.phone_number)
    now = _now()
    recent = await session.scalar(
        select(func.count())
        .select_from(TelegramLinkChallenge)
        .where(
            TelegramLinkChallenge.phone_number == phone_number,
            TelegramLinkChallenge.created_at >= now - START_WINDOW,
        )
    )
    if recent >= MAX_STARTS_PER_PHONE:
        raise ApplicationError('telegram_link_rate_limited', 'Too many attempts; try later', 429)
    token, poll_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    lifetime = settings.telegram_link_lifetime_seconds
    session.add(
        TelegramLinkChallenge(
            token_hash=_hash(token),
            poll_hash=_hash(poll_token),
            phone_number=phone_number,
            status=LinkChallengeStatus.PENDING,
            expires_at=now + timedelta(seconds=lifetime),
            created_at=now,
        )
    )
    already_linked = await session.get(TelegramLink, phone_number) is not None
    await session.commit()
    return LinkStarted(
        status='initiated',
        deep_link=f'https://t.me/{settings.telegram_bot_username}?start={token}',
        poll_token=poll_token,
        expires_in_seconds=lifetime,
        already_linked=already_linked,
    )


@router.get('/status', response_model=LinkStatus)
async def link_status(
    request: Request,
    session: Session,
    x_yondo_link_poll: Annotated[str | None, Header(max_length=128)] = None,
) -> LinkStatus:
    _bot(request)
    challenge = None
    if x_yondo_link_poll:
        challenge = await session.scalar(
            select(TelegramLinkChallenge).where(
                TelegramLinkChallenge.poll_hash == _hash(x_yondo_link_poll)
            )
        )
    if challenge is None:
        raise ApplicationError('telegram_link_invalid', 'Unknown or expired link', 404)
    now = _now()
    remaining = max(0, int((_as_utc(challenge.expires_at) - now).total_seconds()))
    status = challenge.status
    if status == LinkChallengeStatus.PENDING:
        status = 'expired' if remaining == 0 else 'awaiting_contact'
    return LinkStatus(
        status=status, failure_code=challenge.failure_code, expires_in_seconds=remaining
    )


async def _same_completion(session, challenge_id, telegram_user_id: int, phone: str) -> bool:
    row = await session.get(TelegramLinkChallenge, challenge_id, populate_existing=True)
    return row.telegram_user_id == telegram_user_id and row.phone_number == phone


def _raise_used():
    raise ApplicationError('telegram_link_used', 'This link was already used', 409)


def _fail(challenge: TelegramLinkChallenge, code: str, now: datetime) -> None:
    challenge.status = LinkChallengeStatus.FAILED
    challenge.failure_code = code
    challenge.consumed_at = now


@router.post('/complete', response_model=LinkCompleted)
async def complete_link(
    payload: LinkComplete,
    request: Request,
    session: Session,
    x_yondo_bot_secret: Annotated[str | None, Header(max_length=256)] = None,
) -> LinkCompleted:
    """Called only by the Yondo bot service after it verified the shared contact."""
    settings, bot = _bot(request)
    expected = settings.telegram_bot_secret.get_secret_value().encode()
    if not hmac.compare_digest((x_yondo_bot_secret or '').encode(), expected):
        raise ApplicationError('invalid_bot_secret', 'Not allowed', 401)
    if not _CHALLENGE.fullmatch(payload.challenge):
        raise ApplicationError('telegram_link_invalid', 'Unknown or expired link', 404)
    if payload.telegram_chat_id != payload.telegram_user_id:
        raise ApplicationError('telegram_chat_not_private', 'Only private chats are supported', 422)
    phone_number = normalize_uzbekistan_phone(payload.phone_number)
    now = _now()
    challenge = await session.scalar(
        select(TelegramLinkChallenge)
        .where(TelegramLinkChallenge.token_hash == _hash(payload.challenge))
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if challenge is None:
        raise ApplicationError('telegram_link_invalid', 'Unknown or expired link', 404)
    if challenge.status == LinkChallengeStatus.EXPIRED:
        raise ApplicationError('telegram_link_expired', 'The link has expired', 410)
    if challenge.status != LinkChallengeStatus.PENDING:
        # telegram_user_id is set only once the link itself was stored (even if the send failed).
        same = (
            challenge.telegram_user_id == payload.telegram_user_id
            and challenge.phone_number == phone_number
        )
        if same:
            return LinkCompleted(status='linked')  # retried call: no second code
        raise ApplicationError('telegram_link_used', 'This link was already used', 409)
    if now >= _as_utc(challenge.expires_at):
        challenge.status = LinkChallengeStatus.EXPIRED
        await session.commit()
        raise ApplicationError('telegram_link_expired', 'The link has expired', 410)
    if phone_number != challenge.phone_number:
        _fail(challenge, 'telegram_phone_mismatch', now)
        await session.commit()
        raise ApplicationError(
            'telegram_phone_mismatch', 'The shared contact does not match the phone number', 409
        )
    other = await session.scalar(
        select(TelegramLink).where(
            TelegramLink.telegram_user_id == payload.telegram_user_id,
            TelegramLink.phone_number != phone_number,
        )
    )
    if other is not None:
        _fail(challenge, 'telegram_account_linked_elsewhere', now)
        await session.commit()
        raise ApplicationError(
            'telegram_account_linked_elsewhere',
            'This Telegram account is linked to another phone number',
            409,
        )
    link = await session.get(TelegramLink, phone_number, with_for_update=True)
    if link is None:
        session.add(
            TelegramLink(
                phone_number=phone_number,
                telegram_user_id=payload.telegram_user_id,
                telegram_chat_id=payload.telegram_chat_id,
                linked_at=now,
            )
        )
    else:  # same phone, verified again (possibly a new Telegram account): replace
        link.telegram_user_id = payload.telegram_user_id
        link.telegram_chat_id = payload.telegram_chat_id
        link.linked_at = now
    challenge_id = challenge.id
    # Conditional transition: only one concurrent completion can move the row out of 'pending'
    # (FOR UPDATE above serialises on PostgreSQL; this also holds where row locks do not exist).
    claimed = await session.execute(
        update(TelegramLinkChallenge)
        .where(
            TelegramLinkChallenge.id == challenge_id,
            TelegramLinkChallenge.status == LinkChallengeStatus.PENDING,
        )
        .values(
            status=LinkChallengeStatus.LINKED,
            telegram_user_id=payload.telegram_user_id,
            consumed_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        await session.rollback()
        return LinkCompleted(status='linked') if await _same_completion(
            session, challenge_id, payload.telegram_user_id, phone_number
        ) else _raise_used()
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            'telegram_account_linked_elsewhere',
            'This Telegram account is linked to another phone number',
            409,
        ) from exc
    failure: str | None = None
    try:
        await issue_otp(
            session, phone_number, settings, _ChatProvider(bot, payload.telegram_chat_id)
        )
    except ApplicationError as exc:
        await session.rollback()
        failure = exc.code
    challenge = await session.get(TelegramLinkChallenge, challenge_id, populate_existing=True)
    if failure is None:
        challenge.status = LinkChallengeStatus.OTP_SENT
    else:
        challenge.status = LinkChallengeStatus.FAILED
        challenge.failure_code = failure
    await session.commit()
    return LinkCompleted(status='linked')
