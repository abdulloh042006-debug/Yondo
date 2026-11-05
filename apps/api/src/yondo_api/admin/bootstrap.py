"""Grant (or revoke) the admin role from the server shell: the only way to get the first admin.

    python -m yondo_api.admin.bootstrap --phone +998XXXXXXXXX           # grant
    python -m yondo_api.admin.bootstrap --phone +998XXXXXXXXX --revoke  # revoke

Run it from apps/api with the API's environment (YONDO_DATABASE_URL). `PUT /auth/roles` never
grants admin, so this command is the bootstrap path. A missing user is created as an active
account with that phone (the same row the OTP login would create); signing in still needs the
normal phone + code login. Idempotent: a repeated run changes nothing and says so. Every change
writes an AdminAuditEvent (admin_id = the user's own id: there is no other admin to name).
Only the masked phone is ever printed.

Exit codes: 0 done or nothing to change, 1 refused (account unavailable, last admin), 2 bad phone.
"""

import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yondo_api.admin.models import AdminAuditEvent
from yondo_api.api.errors import ApplicationError
from yondo_api.auth.phone import normalize_uzbekistan_phone
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType

EXIT_OK, EXIT_REFUSED, EXIT_BAD_PHONE = 0, 1, 2
_UNAVAILABLE = {AccountStatus.SUSPENDED, AccountStatus.BANNED, AccountStatus.DELETED}
_REASON = 'server-side admin bootstrap command'


def mask_phone(phone_number: str) -> str:
    """'+998901110099' -> '+998 90 *** ** 99'."""
    digits = phone_number.lstrip('+')
    return f'+{digits[:3]} {digits[3:5]} *** ** {digits[-2:]}'


async def grant_admin(session: AsyncSession, phone_number: str) -> tuple[int, str]:
    masked = mask_phone(phone_number)
    user = await session.scalar(select(User).where(User.phone_number == phone_number))
    if user is not None and user.account_status in _UNAVAILABLE:
        return EXIT_REFUSED, f'{masked}: account is {user.account_status.value}; nothing changed'
    if user is not None and await session.get(UserRole, (user.id, UserRoleType.ADMIN)):
        return EXIT_OK, f'{masked}: already an admin; nothing changed'
    created = user is None
    if created:
        user = User(phone_number=phone_number, account_status=AccountStatus.ACTIVE)
        session.add(user)
        await session.flush()
    session.add(UserRole(user_id=user.id, role=UserRoleType.ADMIN))
    session.add(
        AdminAuditEvent(
            admin_id=user.id, target_id=user.id, action='admin_bootstrap', reason=_REASON
        )
    )
    await session.commit()
    return EXIT_OK, f'{masked}: admin role granted' + (' (new user created)' if created else '')


async def revoke_admin(session: AsyncSession, phone_number: str) -> tuple[int, str]:
    masked = mask_phone(phone_number)
    user = await session.scalar(select(User).where(User.phone_number == phone_number))
    # Lock every admin row (PostgreSQL) so two concurrent revokes cannot remove the last two.
    admins = (
        await session.scalars(
            select(UserRole).where(UserRole.role == UserRoleType.ADMIN).with_for_update()
        )
    ).all()
    role = next((row for row in admins if user is not None and row.user_id == user.id), None)
    if role is None:
        return EXIT_OK, f'{masked}: not an admin; nothing changed'
    if len(admins) <= 1:
        return EXIT_REFUSED, f'{masked}: refused, this is the last admin; nothing changed'
    await session.delete(role)
    session.add(
        AdminAuditEvent(admin_id=user.id, target_id=user.id, action='admin_revoke', reason=_REASON)
    )
    await session.commit()
    return EXIT_OK, f'{masked}: admin role revoked'


async def run(
    argv: list[str] | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog='python -m yondo_api.admin.bootstrap')
    parser.add_argument(
        '--phone', required=True, help='Uzbekistan phone number, e.g. +998901234567'
    )
    parser.add_argument('--revoke', action='store_true', help='remove the admin role instead')
    args = parser.parse_args(argv)
    try:
        phone_number = normalize_uzbekistan_phone(args.phone)
    except ApplicationError:
        print('invalid phone number (expected an Uzbekistan number such as +998 90 *** ** **)')
        return EXIT_BAD_PHONE
    action = revoke_admin if args.revoke else grant_admin
    if session_factory is not None:
        async with session_factory() as session:
            code, message = await action(session, phone_number)
    else:
        from yondo_api.config import get_settings
        from yondo_api.db.session import create_database_engine, create_session_factory

        engine = create_database_engine(get_settings().database_url_async)
        try:
            async with create_session_factory(engine)() as session:
                code, message = await action(session, phone_number)
        finally:
            await engine.dispose()
    print(message)
    return code


if __name__ == '__main__':
    raise SystemExit(asyncio.run(run()))
