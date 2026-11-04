"""Operational commands. Usage (from apps/api):

python -m yondo_api.cli grant-admin +998901234567
python -m yondo_api.cli worker [--once]
python -m yondo_api.cli seed-demo    # development only
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select

from yondo_api.auth.phone import normalize_uzbekistan_phone
from yondo_api.config import get_settings
from yondo_api.db.session import create_database_engine, create_session_factory
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType


async def grant_admin(phone: str) -> int:
    """Bootstrap the first administrator. The person must have signed in with OTP once."""
    settings = get_settings()
    engine = create_database_engine(settings.database_url_async)
    try:
        async with create_session_factory(engine)() as session:
            number = normalize_uzbekistan_phone(phone)
            user = await session.scalar(select(User).where(User.phone_number == number))
            if user is None:
                print(f'No account for {number}; sign in with OTP first.', file=sys.stderr)
                return 1
            if await session.get(UserRole, (user.id, UserRoleType.ADMIN)) is None:
                session.add(UserRole(user_id=user.id, role=UserRoleType.ADMIN))
            if user.account_status == AccountStatus.VERIFICATION_PENDING:
                user.account_status = AccountStatus.ACTIVE
            await session.commit()
            print(f'Granted admin role to {number} ({user.id}).')
            return 0
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='yondo_api.cli')
    commands = parser.add_subparsers(dest='command', required=True)
    admin = commands.add_parser('grant-admin', help='grant the admin role to an existing account')
    admin.add_argument('phone')
    worker = commands.add_parser('worker', help='run background jobs')
    worker.add_argument('--once', action='store_true', help='run every job once and exit')
    commands.add_parser('seed-demo', help='create demo accounts and content (development only)')
    args = parser.parse_args(argv)
    if args.command == 'grant-admin':
        return asyncio.run(grant_admin(args.phone))
    if args.command == 'seed-demo':
        from yondo_api.demo import run_seed

        return asyncio.run(run_seed())
    from yondo_api.worker import run_worker

    return asyncio.run(run_worker(once=args.once))


if __name__ == '__main__':
    raise SystemExit(main())
