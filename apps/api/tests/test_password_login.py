"""Username + password login (docs/login-password.md; product decisions §3, §6; 2026-11-15)."""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import select, text, update

from yondo_api.auth.passwords import IpRateLimiter
from yondo_api.auth.providers import DevelopmentOtpProvider
from yondo_api.config import Settings
from yondo_api.main import create_application
from yondo_api.models.auth import AuthSession, PasswordLoginGuard
from yondo_api.models.user import AccountStatus, User

A = '/api/v1/auth'
PHONE = '+998901234567'
PASSWORD = 'tog-yonida-choy-7'


@asynccontextmanager
async def client_for(**extra):
    settings = Settings(
        **{
            'environment': 'test',
            'database_url': os.environ.get(
                'YONDO_TEST_DATABASE_URL', 'sqlite+aiosqlite:///:memory:'
            ),
            'auth_otp_pepper': 'test-only-auth-pepper-0123456789abcdef',
            'telegram_gateway_token': None,
            'auth_scrypt_log_n': 14,  # fast tests; production default is 17
            **extra,
        }
    )
    app = create_application(settings, otp_provider=DevelopmentOtpProvider())
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.begin() as connection:
            if connection.dialect.name == 'sqlite':
                await connection.run_sync(User.metadata.create_all)
            else:
                await connection.execute(
                    text('TRUNCATE users, otp_challenges, password_login_guards CASCADE')
                )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            yield client, app


async def otp_login(client, phone=PHONE):
    issued = await client.post(f'{A}/otp/request', json={'phone_number': phone})
    code = issued.json()['development_otp']
    tokens = (
        await client.post(f'{A}/otp/verify', json={'phone_number': phone, 'code': code})
    ).json()
    return {'Authorization': f'Bearer {tokens["access_token"]}'}


async def register(client, username='ali.valiyev', password=PASSWORD, phone=PHONE):
    headers = await otp_login(client, phone)
    response = await client.post(
        f'{A}/registration', headers=headers, json={'username': username, 'password': password}
    )
    return headers, response


async def login(client, who, password=PASSWORD):
    return await client.post(f'{A}/password/login', json={'login': who, 'password': password})


def bearer(response):
    return {'Authorization': f'Bearer {response.json()["access_token"]}'}


async def test_register_then_sign_in_with_username_or_phone():
    async with client_for() as (client, app):
        headers = await otp_login(client)
        me = (await client.get(f'{A}/me', headers=headers)).json()
        assert (me['username'], me['has_password'], me['password_setup_required']) == (
            None,
            False,
            True,
        )
        done = await client.post(
            f'{A}/registration',
            headers=headers,
            json={'username': '  Ali.Valiyev ', 'password': PASSWORD},
        )
        assert done.status_code == 200, done.text
        assert done.json()['username'] == 'ali.valiyev'
        assert (
            done.json()['has_password'] is True and done.json()['password_setup_required'] is False
        )
        assert PASSWORD not in done.text
        for who in ('ali.valiyev', 'ALI.Valiyev', '+998 90 123 45 67', '901234567', '998901234567'):
            ok = await login(client, who)
            assert ok.status_code == 200, (who, ok.text)
        me = await client.get(f'{A}/me', headers=bearer(ok))
        assert me.json()['username'] == 'ali.valiyev'
        async with app.state.db_session_factory() as session:
            user = await session.scalar(select(User))
            assert (
                user.password_hash.startswith('scrypt$14$8$1$')
                and PASSWORD not in user.password_hash
            )
            vias = set(await session.scalars(select(AuthSession.via)))
            assert vias == {'otp', 'password'}
        again = await client.post(
            f'{A}/registration',
            headers=headers,
            json={'username': 'ali.valiyev', 'password': PASSWORD},
        )
        assert again.status_code == 409 and again.json()['code'] == 'registration_complete'


async def test_username_rules_reserved_names_and_availability():
    async with client_for() as (client, app):
        headers = await otp_login(client)
        for bad in ('ab', '1ali', 'ali..vali', 'ali-vali', 'a' * 31, 'ali vali', 'alí'):
            response = await client.post(
                f'{A}/registration', headers=headers, json={'username': bad, 'password': PASSWORD}
            )
            assert response.status_code == 422 and response.json()['code'] == 'invalid_username', (
                bad
            )
        for reserved in ('admin', 'Yondo', 'support', 'sos', 'yondo_team', 'administrator', 'null'):
            response = await client.post(
                f'{A}/registration',
                headers=headers,
                json={'username': reserved, 'password': PASSWORD},
            )
            assert response.status_code == 409, reserved
            assert response.json()['code'] == 'username_unavailable'

        async def check(name):
            return (await client.get(f'{A}/username/available', params={'username': name})).json()

        assert await check('Ali_1') == {'username': 'ali_1', 'available': True, 'reason': None}
        assert (await check('admin'))['reason'] == 'reserved'
        assert (await check('1x'))['reason'] == 'invalid'
        assert (await register(client, 'ali_1'))[1].status_code == 200
        assert (await check('ALI_1'))['reason'] == 'taken'
        _, taken = await register(client, 'Ali_1', phone='+998935550011')
        assert taken.status_code == 409 and taken.json()['code'] == 'username_unavailable'


async def test_password_rules():
    async with client_for() as (client, app):
        headers = await otp_login(client)
        for weak in (
            '1234567',
            'x' * 129,
            '901234567',
            '+998 90 123 45 67',
            '998901234567',
            '+998901234567',
        ):
            response = await client.post(
                f'{A}/registration', headers=headers, json={'username': 'vali', 'password': weak}
            )
            assert response.status_code == 422 and response.json()['code'] == 'weak_password'
            assert weak not in response.text
        ok = await client.post(
            f'{A}/registration', headers=headers, json={'username': 'vali', 'password': 'abcdefgh'}
        )
        assert ok.status_code == 200  # 8 characters, no composition rules


async def test_registration_needs_a_fresh_code_session():
    async with client_for() as (client, app):
        headers = await otp_login(client)
        async with app.state.db_session_factory() as session:
            await session.execute(
                update(AuthSession).values(created_at=datetime.now(UTC) - timedelta(hours=1))
            )
            await session.commit()
        stale = await client.post(
            f'{A}/registration', headers=headers, json={'username': 'vali', 'password': PASSWORD}
        )
        assert stale.status_code == 403 and stale.json()['code'] == 'reauth_required'
        assert (
            await client.post(f'{A}/registration', json={'username': 'vali', 'password': PASSWORD})
        ).status_code == 401


async def test_failures_are_generic_and_lock_after_five():
    async with client_for() as (client, app):
        await register(client)
        await otp_login(client, '+998935550011')  # an account with no password
        bodies = []
        for who, password in (
            ('ali.valiyev', 'wrong-password'),
            ('nobody.here', PASSWORD),
            ('+998935550011', PASSWORD),
            ('+998977777777', PASSWORD),
            ('not a login!', PASSWORD),
        ):
            response = await login(client, who, password)
            assert response.status_code == 401, who
            body = response.json()
            body.pop('request_id', None)
            bodies.append(body)
        assert (
            all(body == bodies[0] for body in bodies) and bodies[0]['code'] == 'invalid_credentials'
        )
        # Same account through both identifiers: 1 + 2 + 2 failures = locked.
        for who in ('901234567', 'ali.valiyev', '+998901234567', 'ALI.VALIYEV'):
            await login(client, who, 'still-wrong')
        blocked = await login(client, 'ali.valiyev')  # even the right password
        assert blocked.status_code == 429 and blocked.json()['code'] == 'password_login_blocked'
        # Unknown logins lock the same way (no enumeration through the 429).
        for _ in range(5):
            await login(client, 'ghost.user', 'whatever-1')
        assert (await login(client, 'ghost.user', 'whatever-1')).status_code == 429
        async with app.state.db_session_factory() as session:
            await session.execute(
                update(PasswordLoginGuard).values(
                    blocked_until=datetime.now(UTC) - timedelta(seconds=1)
                )
            )
            await session.commit()
        assert (await login(client, 'ali.valiyev')).status_code == 200  # after 15 minutes
        async with app.state.db_session_factory() as session:
            user = await session.scalar(select(User).where(User.username == 'ali.valiyev'))
            assert await session.get(PasswordLoginGuard, f'user:{user.id}') is None


async def test_per_ip_limit_and_suspended_account():
    async with client_for() as (client, app):
        await register(client)
        app.state.password_ip_limiter = IpRateLimiter(3)
        for _ in range(3):
            assert (await login(client, 'nobody.x')).status_code == 401
        limited = await login(client, 'ali.valiyev')
        assert limited.status_code == 429 and limited.json()['code'] == 'rate_limited'
        app.state.password_ip_limiter = IpRateLimiter(20)
        async with app.state.db_session_factory() as session:
            await session.execute(update(User).values(account_status=AccountStatus.SUSPENDED))
            await session.commit()
        assert (await login(client, 'ali.valiyev')).status_code == 403
        assert (await login(client, 'ali.valiyev', 'wrong-one')).status_code == 401


async def test_change_password_signs_out_other_sessions():
    async with client_for() as (client, app):
        first, _ = await register(client)
        second = bearer(await login(client, 'ali.valiyev'))
        wrong = await client.put(
            f'{A}/password',
            headers=second,
            json={'current_password': 'nope-nope', 'new_password': 'new-password-1'},
        )
        assert wrong.status_code == 401 and wrong.json()['code'] == 'invalid_credentials'
        weak = await client.put(
            f'{A}/password',
            headers=second,
            json={'current_password': PASSWORD, 'new_password': 'short'},
        )
        assert weak.status_code == 422
        changed = await client.put(
            f'{A}/password',
            headers=second,
            json={'current_password': PASSWORD, 'new_password': 'new-password-1'},
        )
        assert changed.status_code == 204
        assert (await client.get(f'{A}/me', headers=second)).status_code == 200
        assert (await client.get(f'{A}/me', headers=first)).status_code == 401
        assert (await login(client, 'ali.valiyev')).status_code == 401
        assert (await login(client, 'ali.valiyev', 'new-password-1')).status_code == 200
        otp_only = await otp_login(client, '+998935550011')
        none = await client.put(
            f'{A}/password',
            headers=otp_only,
            json={'current_password': 'x' * 8, 'new_password': 'new-password-1'},
        )
        assert none.status_code == 409 and none.json()['code'] == 'password_not_set'


async def test_reset_by_code_signs_out_all_sessions_and_unlocks():
    async with client_for() as (client, app):
        old, _ = await register(client)
        for _ in range(5):
            await login(client, 'ali.valiyev', 'wrong-pass')
        assert (await login(client, 'ali.valiyev')).status_code == 429
        code = (await client.post(f'{A}/otp/request', json={'phone_number': PHONE})).json()[
            'development_otp'
        ]
        weak = await client.post(
            f'{A}/password/reset',
            json={'phone_number': PHONE, 'code': code, 'new_password': '901234567'},
        )
        assert weak.status_code == 422  # the code is not used up by a rejected password
        reset = await client.post(
            f'{A}/password/reset',
            json={'phone_number': PHONE, 'code': code, 'new_password': 'brand-new-pass'},
        )
        assert reset.status_code == 200, reset.text
        assert (await client.get(f'{A}/me', headers=old)).status_code == 401
        assert (await client.get(f'{A}/me', headers=bearer(reset))).status_code == 200
        assert (await login(client, 'ali.valiyev', 'brand-new-pass')).status_code == 200
        reused = await client.post(
            f'{A}/password/reset',
            json={'phone_number': PHONE, 'code': code, 'new_password': 'another-pass'},
        )
        assert reused.status_code == 401


async def test_secrets_never_echoed_or_logged(capsys):
    async with client_for() as (client, app):
        headers = await otp_login(client)
        bad = await client.post(
            f'{A}/registration',
            headers=headers,
            json={'username': 'vali', 'password': PASSWORD, 'extra': 1},
        )
        assert bad.status_code == 422 and PASSWORD not in bad.text
        await register(client, 'vali')
        await login(client, 'vali', 'Wrong-Secret-99')
        out = capsys.readouterr()
        assert PASSWORD not in out.out + out.err and 'Wrong-Secret-99' not in out.out + out.err


async def test_setup_gate_is_off_by_default_and_blocks_when_on():
    async with client_for() as (client, app):
        headers = await otp_login(client)
        open_ = await client.get('/api/v1/bookings', headers=headers)
        assert open_.json().get('code') != 'password_setup_required'
    async with client_for(auth_require_password_setup=True) as (client, app):
        headers = await otp_login(client)
        gated = await client.get('/api/v1/bookings', headers=headers)
        assert gated.status_code == 403 and gated.json()['code'] == 'password_setup_required'
        assert (await client.get(f'{A}/me', headers=headers)).status_code == 200
        done = await client.post(
            f'{A}/registration', headers=headers, json={'username': 'vali', 'password': PASSWORD}
        )
        assert done.status_code == 200
        after = await client.get('/api/v1/bookings', headers=headers)
        assert after.json().get('code') != 'password_setup_required'


async def test_account_erasure_frees_the_username():
    from yondo_api.account.deletion import erase_account

    async with client_for() as (client, app):
        await register(client)
        async with app.state.db_session_factory() as session:
            user = await session.scalar(select(User))
            await erase_account(session, user, None, datetime.now(UTC))
            await session.commit()
            user = await session.get(User, user.id)
            assert (user.username, user.password_hash) == (None, None)
        assert (await login(client, 'ali.valiyev')).status_code == 401
        free = await client.get(f'{A}/username/available', params={'username': 'ali.valiyev'})
        assert free.json()['available'] is True


async def test_two_registrations_racing_for_one_username():
    async with client_for() as (client, app):
        if app.state.db_engine.dialect.name != 'postgresql':
            pytest.skip('native concurrency needs PostgreSQL (SQLite tests share one connection)')
        first = await otp_login(client, '+998935550011')
        second = await otp_login(client, '+998935550022')
        results = await asyncio.gather(
            *(
                client.post(
                    f'{A}/registration',
                    headers=h,
                    json={'username': 'same.name', 'password': PASSWORD},
                )
                for h in (first, second)
            )
        )
        assert sorted(r.status_code for r in results) == [200, 409]
        assert {r.json().get('code') for r in results if r.status_code == 409} == {
            'username_unavailable'
        }
        async with app.state.db_session_factory() as session:
            owners = list(
                await session.scalars(select(User.id).where(User.username == 'same.name'))
            )
            assert len(owners) == 1 and isinstance(owners[0], UUID)
