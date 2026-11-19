"""Passwords and usernames (docs/login-password.md, docs/product-decisions.md §3 and §6).

- Hash: stdlib ``hashlib.scrypt`` with a per-password 16-byte random salt and the parameters
  stored next to it: ``scrypt$<log2 N>$<r>$<p>$<salt b64>$<key b64>``. Verification always uses
  the stored parameters, so the cost can be raised later (rehash on the next login).
- Rules: 8-128 characters, not the phone number, no composition rules.
- Username: 3-30 of a-z, 0-9, "_" and "."; starts with a letter; no ".."; unique (stored lower
  case); a reserved list is refused. Private: only the owner sees it (``/auth/me``).
- Attempts: 5 wrong passwords lock that account's password login for 15 minutes; unknown logins
  are counted the same way, so the answers never reveal whether a login exists.
- The plain password is never stored, logged or echoed.
"""

import base64
import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from anyio import CapacityLimiter, to_thread
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.models.auth import PasswordLoginGuard

PASSWORD_MIN, PASSWORD_MAX = 8, 128
MAX_FAILED_ATTEMPTS = 5
LOCKOUT = timedelta(minutes=15)
_R, _P, _SALT, _KEY = 8, 1, 16, 32
# At most two hashes at once: each scrypt call with log_n=17 takes about 128 MiB.
_HASH_LIMITER = CapacityLimiter(2)

USERNAME = re.compile(r'[a-z][a-z0-9_.]{2,29}')
RESERVED_USERNAMES = frozenset(
    {
        'admin',
        'administrator',
        'admins',
        'root',
        'superuser',
        'sysadmin',
        'system',
        'sys',
        'moderator',
        'moderators',
        'mod',
        'staff',
        'team',
        'owner',
        'yondo',
        'yondo.uz',
        'yondo_uz',
        'yondoapp',
        'yondo_app',
        'yondo.app',
        'support',
        'help',
        'helpdesk',
        'info',
        'contact',
        'sos',
        'emergency',
        'security',
        'safety',
        'abuse',
        'report',
        'api',
        'www',
        'web',
        'app',
        'mail',
        'email',
        'null',
        'none',
        'nil',
        'undefined',
        'anonymous',
        'unknown',
        'test',
        'demo',
        'bot',
        'official',
        'verify',
        'verified',
        'login',
        'signin',
        'signup',
        'register',
        'settings',
        'account',
        'me',
        'user',
        'users',
        'companion',
        'customer',
        'vendor',
        'billing',
        'payments',
        'payment',
        'legal',
        'privacy',
        'terms',
    }
)


def weak_password() -> ApplicationError:
    return ApplicationError(
        'weak_password', 'The password must be 8-128 characters and not the phone number', 422
    )


def invalid_credentials() -> ApplicationError:
    return ApplicationError('invalid_credentials', 'The login or password is incorrect', 401)


def password_login_blocked() -> ApplicationError:
    return ApplicationError(
        'password_login_blocked', 'Too many attempts; try again later or sign in with a code', 429
    )


def check_password_rules(password: str, phone_number: str) -> None:
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        raise weak_password()
    candidate = password.strip()
    phone = re.sub(r'\D', '', phone_number)
    if re.fullmatch(r'[+\d\s().-]+', candidate) and re.sub(r'\D', '', candidate) in {
        phone,
        phone[3:],
        f'00{phone}',
    }:
        raise weak_password()


def normalize_username(value: str) -> str:
    return value.strip().lower()


def username_problem(username: str) -> str | None:
    """None when the (normalised) username may be registered, else 'invalid' or 'reserved'."""
    if not USERNAME.fullmatch(username) or '..' in username:
        return 'invalid'
    if username in RESERVED_USERNAMES or username.startswith(('yondo', 'admin')):
        return 'reserved'
    return None


def _scrypt(password: str, salt: bytes, log_n: int, r: int, p: int) -> bytes:
    n = 1 << log_n
    return hashlib.scrypt(
        password.encode(), salt=salt, n=n, r=r, p=p, dklen=_KEY, maxmem=128 * r * n * 2 + 2**20
    )


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode()


async def hash_password(password: str, log_n: int) -> str:
    salt = secrets.token_bytes(_SALT)
    key = await to_thread.run_sync(_scrypt, password, salt, log_n, _R, _P, limiter=_HASH_LIMITER)
    return f'scrypt${log_n}${_R}${_P}${_b64(salt)}${_b64(key)}'


def _parse(stored: str) -> tuple[int, int, int, bytes, bytes] | None:
    try:
        scheme, log_n, r, p, salt, key = stored.split('$')
        if scheme != 'scrypt':
            return None
        return int(log_n), int(r), int(p), base64.b64decode(salt), base64.b64decode(key)
    except (ValueError, TypeError):
        return None


async def verify_password(password: str, stored: str | None, log_n: int) -> bool:
    """Constant-work check: without a stored hash a dummy hash is computed and False returned."""
    parsed = _parse(stored) if stored else None
    if parsed is None:
        await to_thread.run_sync(
            _scrypt, password, b'\0' * _SALT, log_n, _R, _P, limiter=_HASH_LIMITER
        )
        return False
    stored_log_n, r, p, salt, key = parsed
    candidate = await to_thread.run_sync(
        _scrypt, password, salt, stored_log_n, r, p, limiter=_HASH_LIMITER
    )
    return hmac.compare_digest(candidate, key)


class IpRateLimiter:
    """Fixed one-minute windows per (bucket, IP), in process memory.

    Correct for the single-process demo and a single API instance; several instances would need
    a shared store (Redis), to be added with the server work.
    """

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self.clock = time.time  # tests replace it
        self._counts: dict[tuple[str, str, int], int] = defaultdict(int)

    def check(self, bucket: str, ip: str | None) -> None:
        if self.per_minute <= 0:
            return
        minute = int(self.clock() // 60)
        if len(self._counts) > 50_000:  # drop old windows
            for key in [k for k in self._counts if k[2] < minute]:
                del self._counts[key]
        key = (bucket, ip or 'unknown', minute)
        self._counts[key] += 1
        if self._counts[key] > self.per_minute:
            raise ApplicationError('rate_limited', 'Too many attempts; try again later', 429)


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


async def locked_guard(session: AsyncSession, subject: str) -> PasswordLoginGuard:
    if session.get_bind().dialect.name == 'postgresql':
        # Serialise attempts per subject (also when no guard row exists yet).
        await session.execute(
            text('SELECT pg_advisory_xact_lock(hashtextextended(:subject, 1))'),
            {'subject': subject},
        )
    guard = await session.get(
        PasswordLoginGuard, subject, with_for_update=True, populate_existing=True
    )
    if guard is None:
        guard = PasswordLoginGuard(subject=subject, failed_attempts=0)
        session.add(guard)
    return guard


async def discard_guard(session: AsyncSession, guard: PasswordLoginGuard) -> None:
    """Reset the counter (a success): remove the row, or forget it if it was never stored."""
    if guard in session.new:
        session.expunge(guard)
    else:
        await session.delete(guard)


def ensure_not_blocked(guard: PasswordLoginGuard) -> None:
    if guard.blocked_until is not None:
        if _now() < _as_utc(guard.blocked_until):
            raise password_login_blocked()
        guard.failed_attempts, guard.blocked_until = 0, None


def record_failure(guard: PasswordLoginGuard) -> None:
    guard.failed_attempts += 1
    if guard.failed_attempts >= MAX_FAILED_ATTEMPTS:
        guard.blocked_until = _now() + LOCKOUT


def subject_for_user(user_id) -> str:
    return f'user:{user_id}'


def subject_for_unknown(login: str) -> str:
    return f'login:{hashlib.sha256(login.encode()).hexdigest()[:48]}'
