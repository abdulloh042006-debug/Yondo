"""18+ for everyone (owner, 2026-11-19; CEO decisions; docs/age-limit.md)."""

import os
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from sqlalchemy import delete, func, select, text, update

from yondo_api.admin.models import AdminAuditEvent
from yondo_api.auth.age import age_on, checked_age
from yondo_api.auth.providers import DevelopmentOtpProvider
from yondo_api.config import Settings
from yondo_api.main import create_application
from yondo_api.models.auth import AgeBlock, OtpChallenge
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType

A = '/api/v1/auth'
PASSWORD = 'tog-yonida-choy-7'
TODAY = datetime.now(UTC).date()


def years_ago(n: int, days: int = 0) -> str:
    try:
        d = TODAY.replace(year=TODAY.year - n)
    except ValueError:  # 29 February
        d = TODAY.replace(year=TODAY.year - n, day=28)
    return (d + timedelta(days=days)).isoformat()


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
            'auth_scrypt_log_n': 14,
            'auth_require_password_setup': True,
            'auth_require_date_of_birth': True,
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
                    text('TRUNCATE users, otp_challenges, otp_issues, age_blocks CASCADE')
                )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            yield client, app


async def code_login(client, phone):
    issued = await client.post(f'{A}/otp/request', json={'phone_number': phone})
    assert issued.status_code == 202, issued.text
    verified = await client.post(
        f'{A}/otp/verify', json={'phone_number': phone, 'code': issued.json()['development_otp']}
    )
    return verified


def bearer(response) -> dict:
    return {'Authorization': f'Bearer {response.json()["access_token"]}'}


async def register(client, headers, dob=None, username='vali.k'):
    body = {'username': username, 'password': PASSWORD}
    if dob is not None:
        body['date_of_birth'] = dob
    return await client.post(f'{A}/registration', headers=headers, json=body)


def test_age_arithmetic_and_bounds():
    assert age_on(date(2008, 11, 19), date(2026, 11, 19)) == 18
    assert age_on(date(2008, 11, 20), date(2026, 11, 19)) == 17
    assert checked_age(date(2008, 11, 19), date(2026, 11, 19)) == 18
    for bad, code in ((date(2008, 11, 20), 'age_restricted'),
                      (date(2027, 1, 1), 'invalid_date_of_birth'),
                      (date(1900, 1, 1), 'invalid_date_of_birth')):
        with pytest.raises(Exception) as caught:
            checked_age(bad, date(2026, 11, 19))
        assert caught.value.code == code


@pytest.mark.asyncio
async def test_adult_registration_stores_a_private_date_and_shows_the_age():
    async with client_for() as (client, _app):
        headers = bearer(await code_login(client, '+998901230001'))
        missing = await register(client, headers)
        assert missing.status_code == 422 and missing.json()['code'] == 'date_of_birth_required'
        done = await register(client, headers, years_ago(30))
        assert done.status_code == 200, done.text
        me = done.json()
        assert me['date_of_birth'] == years_ago(30) and me['age'] == 30
        assert me['date_of_birth_required'] is False and me['age_restricted'] is False
        # The age follows the date of birth: a profile edit cannot change it.
        await client.put(f'{A}/profile', headers=headers, json={'age': 19, 'city': 'Samarqand'})
        me = (await client.get(f'{A}/me', headers=headers)).json()
        assert me['age'] == 30 and me['city'] == 'Samarqand'
        again = await client.put(
            f'{A}/date-of-birth', headers=headers, json={'date_of_birth': years_ago(40)}
        )
        assert again.status_code == 409 and again.json()['code'] == 'date_of_birth_already_set'


@pytest.mark.asyncio
async def test_new_sign_up_under_18_leaves_no_account_and_a_30_day_cooldown():
    async with client_for() as (client, app):
        phone = '+998901230002'
        headers = bearer(await code_login(client, phone))
        refused = await register(client, headers, years_ago(18, days=1))  # 18 tomorrow
        assert refused.status_code == 403 and refused.json()['code'] == 'age_restricted'
        async with app.state.db_session_factory() as session:
            assert await session.scalar(select(User).where(User.phone_number == phone)) is None
            erased = await session.scalar(select(User))
            assert erased.account_status == AccountStatus.DELETED
            assert erased.date_of_birth is None and erased.username is None
            block = await session.scalar(select(AgeBlock))
            assert block is not None and phone.encode() not in block.phone_hash  # only a hash
        # The erased session no longer works, and a new sign-up with another date is refused.
        assert (await client.get(f'{A}/me', headers=headers)).status_code in (401, 403)
        retry = await code_login(client, phone)
        assert retry.status_code == 403 and retry.json()['code'] == 'age_restricted'
        async with app.state.db_session_factory() as session:
            assert await session.scalar(select(func.count()).select_from(User)) == 1  # tombstone
            await session.execute(
                update(AgeBlock).values(blocked_until=datetime.now(UTC) - timedelta(seconds=1))
            )
            await session.execute(delete(OtpChallenge))  # past the resend cooldown
            await session.commit()
        later = await code_login(client, phone)
        assert later.status_code == 200
        assert (await register(client, bearer(later), years_ago(25))).status_code == 200


@pytest.mark.asyncio
async def test_existing_account_flag_retry_support_and_admin_clear():
    async with client_for() as (client, app):
        phone = '+998901230004'
        headers = bearer(await code_login(client, phone))
        assert (await register(client, headers, years_ago(30))).status_code == 200
        async with app.state.db_session_factory() as session:
            user = await session.scalar(select(User).where(User.phone_number == phone))
            user.date_of_birth = None  # an account from before the age limit
            await session.commit()
        gated = await client.get('/api/v1/account/consents', headers=headers)
        assert gated.json()['code'] == 'date_of_birth_required'
        refused = await client.put(
            f'{A}/date-of-birth', headers=headers, json={'date_of_birth': years_ago(16)}
        )
        assert refused.status_code == 403 and refused.json()['code'] == 'age_restricted'
        me = (await client.get(f'{A}/me', headers=headers)).json()
        assert me['age_restricted'] is True and me['date_of_birth'] is None
        # No quick retry with another date, and the app stays locked...
        retry = await client.put(
            f'{A}/date-of-birth', headers=headers, json={'date_of_birth': years_ago(30)}
        )
        assert retry.json()['code'] == 'age_restricted'
        assert (await client.get('/api/v1/account/consents', headers=headers)).json()[
            'code'
        ] == 'age_restricted'
        # ...but support and self-deletion stay reachable.
        support = await client.post(
            '/api/v1/support/requests', headers=headers,
            json={'topic': 'account', 'message': 'I typed the wrong year of birth.'},
        )
        assert support.json().get('code') != 'age_restricted', support.text
        assert (await client.get('/api/v1/account/deletion', headers=headers)).json().get(
            'code'
        ) != 'age_restricted'
        # An admin checks the ID and clears the flag; the action is audited.
        admin_headers = bearer(await code_login(client, '+998901230099'))
        async with app.state.db_session_factory() as session:
            admin = await session.scalar(select(User).where(User.phone_number == '+998901230099'))
            session.add(UserRole(user_id=admin.id, role=UserRoleType.ADMIN))
            admin.username, admin.date_of_birth = 'boss', date(1980, 1, 1)
            admin.password_hash = 'scrypt$14$8$1$x$y'
            admin.account_status = AccountStatus.ACTIVE
            target = await session.scalar(select(User).where(User.phone_number == phone))
            target_id = target.id
            await session.commit()
        url = f'/api/v1/admin/users/{target_id}/age-restriction/clear'
        cleared = await client.post(
            url, headers=admin_headers, json={'reason': 'ID card: born 1996'}
        )
        assert cleared.status_code == 200, cleared.text
        async with app.state.db_session_factory() as session:
            event = await session.scalar(
                select(AdminAuditEvent).where(AdminAuditEvent.action == 'age_restriction_cleared')
            )
            assert event is not None and event.target_id == target_id
        twice = await client.post(url, headers=admin_headers, json={'reason': 'again'})
        assert twice.json()['code'] == 'age_restriction_not_set'
        ok = await client.put(
            f'{A}/date-of-birth', headers=headers, json={'date_of_birth': years_ago(30)}
        )
        assert ok.status_code == 200 and ok.json()['age'] == 30
        final = await client.get('/api/v1/account/consents', headers=headers)
        assert final.status_code == 200, final.text


@pytest.mark.asyncio
async def test_without_the_gate_registration_still_checks_a_given_date():
    async with client_for(auth_require_date_of_birth=False) as (client, _app):
        headers = bearer(await code_login(client, '+998901230005'))
        assert (await register(client, headers)).status_code == 200  # no date: allowed
        headers = bearer(await code_login(client, '+998901230006'))
        refused = await register(client, headers, years_ago(15), username='yosh.bola')
        assert refused.json()['code'] == 'age_restricted'
