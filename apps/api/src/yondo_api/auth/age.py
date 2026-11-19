"""18+ for everyone (owner, 2026-11-19; docs/age-limit.md).

The date of birth is a self-declaration at registration; the ID review is the strong check for
companions. It is private: other users only ever see the age, where the age was already shown.
"""

import hmac
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.config import Settings
from yondo_api.models.auth import AgeBlock

ADULT_AGE = 18
OLDEST = 120
AGE_BLOCK = timedelta(days=30)


def today_utc() -> date:
    return datetime.now(UTC).date()


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def age_restricted() -> ApplicationError:
    return ApplicationError('age_restricted', 'Yondo is only for people aged 18 and over', 403)


def checked_age(dob: date, today: date | None = None) -> int:
    """The age for a declared date of birth; refuses implausible dates and anyone under 18."""
    current = today or today_utc()
    if dob > current or age_on(dob, current) > OLDEST:
        raise ApplicationError('invalid_date_of_birth', 'Enter a real date of birth', 422)
    years = age_on(dob, current)
    if years < ADULT_AGE:
        raise age_restricted()
    return years


def current_age(dob: date | None, stored: int | None) -> int | None:
    """Shown age: from the date of birth when known (never stale), else the old stored value."""
    return age_on(dob, today_utc()) if dob is not None else stored


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def phone_hash(settings: Settings, phone_number: str) -> bytes:
    """Salted (peppered) hash: the number itself is never kept for a refused sign-up."""
    key = settings.auth_otp_pepper.get_secret_value().encode()
    return hmac.digest(key, f'age-block:{phone_number}'.encode(), 'sha256')


async def ensure_phone_not_blocked(
    session: AsyncSession, settings: Settings, phone_number: str
) -> None:
    """Called before a NEW account is created for this phone."""
    row = await session.get(AgeBlock, phone_hash(settings, phone_number))
    if row is not None and datetime.now(UTC) < _as_utc(row.blocked_until):
        raise age_restricted()


async def block_phone(session: AsyncSession, settings: Settings, phone_number: str) -> None:
    key = phone_hash(settings, phone_number)
    until = datetime.now(UTC) + AGE_BLOCK
    row = await session.get(AgeBlock, key)
    if row is None:
        session.add(AgeBlock(phone_hash=key, blocked_until=until))
    else:
        row.blocked_until = until


async def prune_age_blocks(session: AsyncSession) -> int:
    result = await session.execute(
        delete(AgeBlock).where(AgeBlock.blocked_until < datetime.now(UTC))
    )
    await session.commit()
    return result.rowcount or 0
