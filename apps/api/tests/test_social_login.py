"""Telegram Login (OIDC) + Google sign-in (docs/login-telegram-google.md), mocked providers."""

import base64
import json
import os
import time
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from sqlalchemy import func, select, text

from yondo_api.auth.providers import DevelopmentOtpProvider
from yondo_api.auth.social_models import ExternalIdentity
from yondo_api.auth.telegram_models import TelegramLink
from yondo_api.config import Settings
from yondo_api.main import create_application
from yondo_api.models.user import AccountStatus, User

A = '/api/v1/auth'
S = f'{A}/social'
PHONE = '+998901112233'
OTHER = '+998907778899'
CLIENT_ID = '1234567890'
GOOGLE_ID = 'web-client.apps.googleusercontent.com'
REDIRECT = 'https://yondo.test/auth/callback/telegram'
TG = 'https://oauth.telegram.org'


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


def _int(n: int) -> str:
    return _b64(n.to_bytes((n.bit_length() + 7) // 8, 'big'))


RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
EVIL_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
EC_KEY = ec.generate_private_key(ec.SECP256R1())


def _jwks() -> dict:
    pub = RSA_KEY.public_key().public_numbers()
    ecn = EC_KEY.public_key().public_numbers()
    return {
        'keys': [
            {'kty': 'RSA', 'alg': 'RS256', 'kid': 'k1', 'n': _int(pub.n), 'e': _int(pub.e)},
            {
                'kty': 'EC', 'alg': 'ES256', 'crv': 'P-256', 'kid': 'e1',
                'x': _b64(ecn.x.to_bytes(32, 'big')), 'y': _b64(ecn.y.to_bytes(32, 'big')),
            },
        ]
    }


def make_token(claims: dict, *, key=RSA_KEY, kid='k1', alg='RS256') -> str:
    head = _b64(json.dumps({'alg': alg, 'kid': kid, 'typ': 'JWT'}).encode())
    body = _b64(json.dumps(claims).encode())
    signed = f'{head}.{body}'.encode()
    if alg == 'ES256':
        r, s = decode_dss_signature(EC_KEY.sign(signed, ec.ECDSA(hashes.SHA256())))
        sig = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
    else:
        sig = key.sign(signed, padding.PKCS1v15(), hashes.SHA256())
    return f'{head}.{body}.{_b64(sig)}'


def tg_claims(**extra) -> dict:
    now = int(time.time())
    claims = {
        'iss': TG, 'aud': CLIENT_ID, 'sub': 'tg-sub-1', 'iat': now, 'exp': now + 300,
        'id': 555001, 'name': 'Demo', 'phone_number': PHONE.lstrip('+'),
        'phone_number_verified': True,
    }
    claims.update(extra)
    return {k: v for k, v in claims.items() if v is not None}


def google_claims(**extra) -> dict:
    now = int(time.time())
    claims = {
        'iss': 'https://accounts.google.com', 'aud': GOOGLE_ID, 'sub': 'g-sub-1',
        'email': 'someone@example.com', 'email_verified': True, 'iat': now, 'exp': now + 300,
    }
    claims.update(extra)
    return claims


class FakeProviders:
    """Mock transport: JWKS for both providers and Telegram's token endpoint."""

    def __init__(self) -> None:
        self.id_token: str | None = None
        self.token_status = 200
        self.scope: str | None = None
        self.requests: list[httpx.Request] = []
        self.jwks_hits = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)
        if url.endswith('/jwks.json') or url.endswith('/oauth2/v3/certs'):
            self.jwks_hits += 1
            return httpx.Response(200, json=_jwks())
        if url == f'{TG}/token':
            if self.token_status != 200:
                return httpx.Response(self.token_status, json={'error': 'invalid_grant'})
            body = {'access_token': 'x', 'token_type': 'Bearer', 'expires_in': 3600,
                    'id_token': self.id_token}
            if self.scope is not None:
                body['scope'] = self.scope
            return httpx.Response(200, json=body)
        return httpx.Response(404)


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
            'telegram_login_client_id': CLIENT_ID,
            'telegram_login_client_secret': 'test-client-secret',
            'telegram_login_redirect_uris': REDIRECT,
            'google_client_ids': f'{GOOGLE_ID},android-client.apps.googleusercontent.com',
            **extra,
        }
    )
    app = create_application(settings, otp_provider=DevelopmentOtpProvider())
    fake = FakeProviders()
    app.state.social_login.transport = httpx.MockTransport(fake.handler)
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.begin() as connection:
            if connection.dialect.name == 'sqlite':
                await connection.run_sync(User.metadata.create_all)
            else:
                await connection.execute(
                    text(
                        'TRUNCATE users, otp_challenges, otp_issues, password_login_guards, '
                        'telegram_links, '
                        'external_identities, social_login_challenges CASCADE'
                    )
                )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            yield client, app, fake


async def code_for(client, phone):
    issued = await client.post(f'{A}/otp/request', json={'phone_number': phone})
    return issued.json()['development_otp']


async def tg_start(client, headers=None, path='telegram/start'):
    started = await client.post(f'{S}/{path}', json={}, headers=headers or {})
    assert started.status_code == 201, started.text
    data = started.json()
    query = parse_qs(urlsplit(data['authorization_url']).query)
    return data['flow_token'], query


async def tg_login(client, fake, claims=None, headers=None, path='telegram/start'):
    flow, query = await tg_start(client, headers, path)
    fake.id_token = make_token(claims or tg_claims(nonce=query['nonce'][0]))
    return await client.post(
        f'{S}/telegram/exchange',
        json={'code': 'auth-code-1', 'state': query['state'][0], 'flow_token': flow},
    )


async def count(app, model) -> int:
    async with app.state.db_session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model))


def bearer(result) -> dict:
    return {'Authorization': f"Bearer {result['tokens']['access_token']}"}


# ---- configuration -------------------------------------------------------------------------


async def test_config_and_not_configured():
    async with client_for() as (client, _app, _fake):
        config = (await client.get(f'{S}/config')).json()
        assert config == {
            'telegram': True, 'telegram_client_id': CLIENT_ID, 'telegram_code_flow': True,
            'google_client_id': GOOGLE_ID,
        }
    async with client_for(
        telegram_login_client_id='', google_client_ids='', public_web_url=''
    ) as (client, _app, _fake):
        assert (await client.get(f'{S}/config')).json() == {
            'telegram': False, 'telegram_client_id': None, 'telegram_code_flow': False,
            'google_client_id': None,
        }
        for path, body in (
            ('telegram/start', {}),
            ('telegram/nonce', None),
            ('telegram', {'id_token': 'x'}),
            ('google', {'credential': 'x'}),
            ('telegram/exchange', {'code': 'c', 'state': 's' * 20, 'flow_token': 'f' * 20}),
        ):
            response = await client.post(f'{S}/{path}', json=body)
            assert response.status_code == 503
            assert response.json()['code'] == 'provider_not_configured'


async def test_telegram_authorization_url_uses_pkce_and_scopes():
    async with client_for() as (client, _app, _fake):
        _flow, query = await tg_start(client)
        assert query['client_id'] == [CLIENT_ID]
        assert query['redirect_uri'] == [REDIRECT]
        assert query['response_type'] == ['code']
        assert query['code_challenge_method'] == ['S256']
        assert set(query['scope'][0].split()) == {
            'openid', 'profile', 'phone', 'telegram:bot_access',
        }
        bad = await client.post(f'{S}/telegram/start', json={'redirect_uri': 'https://evil.test/'})
        assert bad.json()['code'] == 'invalid_redirect_uri'


# ---- Telegram ------------------------------------------------------------------------------


async def test_telegram_verified_phone_registers_and_records_bot_chat():
    async with client_for() as (client, app, fake):
        result = await tg_login(client, fake)
        assert result.status_code == 200, result.text
        body = result.json()
        assert body['status'] == 'signed_in' and body['password_setup_required'] is True
        token_call = next(r for r in fake.requests if str(r.url) == f'{TG}/token')
        form = parse_qs(token_call.content.decode())
        assert form['grant_type'] == ['authorization_code'] and 'code_verifier' in form
        assert token_call.headers['authorization'].startswith('Basic ')
        me = (await client.get(f'{A}/me', headers=bearer(body))).json()
        assert me['phone_number'] == PHONE
        async with app.state.db_session_factory() as session:
            link = await session.get(TelegramLink, PHONE)
            assert link is not None and link.telegram_chat_id == 555001
        # The new account can set its username + password from this session.
        setup = await client.post(
            f'{A}/registration', headers=bearer(body),
            json={'username': 'demo_user', 'password': 'choy-va-sayr-9'},
        )
        assert setup.status_code == 200, setup.text
        # Second login: same sub -> same account; password login works too.
        again = (await tg_login(client, fake)).json()
        assert again['status'] == 'signed_in' and again['password_setup_required'] is False
        assert await count(app, User) == 1
        pw = await client.post(
            f'{A}/password/login', json={'login': 'demo_user', 'password': 'choy-va-sayr-9'}
        )
        assert pw.status_code == 200


async def test_telegram_existing_phone_signs_in_and_links():
    async with client_for() as (client, app, fake):
        code = await code_for(client, PHONE)
        await client.post(f'{A}/otp/verify', json={'phone_number': PHONE, 'code': code})
        result = (await tg_login(client, fake)).json()
        assert result['status'] == 'signed_in'
        assert await count(app, User) == 1
        assert await count(app, ExternalIdentity) == 1


async def test_telegram_without_bot_access_records_no_chat():
    async with client_for() as (client, app, fake):
        fake.scope = 'openid profile phone'
        assert (await tg_login(client, fake)).json()['status'] == 'signed_in'
        assert await count(app, TelegramLink) == 0


@pytest.mark.parametrize(
    'claims',
    [
        {'phone_number_verified': False},
        {'phone_number': None, 'phone_number_verified': None},
        {'phone_number': '+79161234567'},  # not an Uzbekistan number
    ],
)
async def test_telegram_unverified_or_withheld_phone_needs_a_code(claims):
    async with client_for() as (client, app, fake):
        flow, query = await tg_start(client)
        fake.id_token = make_token(tg_claims(nonce=query['nonce'][0], **claims))
        result = (
            await client.post(
                f'{S}/telegram/exchange',
                json={'code': 'c1', 'state': query['state'][0], 'flow_token': flow},
            )
        ).json()
        assert result['status'] == 'phone_required' and result['signup_token']
        assert await count(app, User) == 0  # never a phone-less account
        code = await code_for(client, OTHER)
        done = await client.post(
            f'{S}/complete',
            json={'signup_token': result['signup_token'], 'phone_number': OTHER, 'code': code},
        )
        assert done.status_code == 200, done.text
        assert done.json()['status'] == 'signed_in'
        me = (await client.get(f'{A}/me', headers=bearer(done.json()))).json()
        assert me['phone_number'] == OTHER
        # The ticket is single-use.
        code = await code_for(client, PHONE)
        replay = await client.post(
            f'{S}/complete',
            json={'signup_token': result['signup_token'], 'phone_number': PHONE, 'code': code},
        )
        assert replay.json()['code'] == 'signup_token_invalid'


async def test_telegram_state_is_single_use_and_bound_to_the_browser():
    async with client_for() as (client, _app, fake):
        flow, query = await tg_start(client)
        fake.id_token = make_token(tg_claims(nonce=query['nonce'][0]))
        body = {'code': 'c1', 'state': query['state'][0], 'flow_token': 'x' * 43}
        wrong = await client.post(f'{S}/telegram/exchange', json=body)
        assert wrong.json()['code'] == 'social_state_invalid'
        body['flow_token'] = flow
        assert (await client.post(f'{S}/telegram/exchange', json=body)).status_code == 200
        replay = await client.post(f'{S}/telegram/exchange', json=body)
        assert replay.json()['code'] == 'social_state_invalid'


async def test_telegram_expired_state():
    async with client_for(social_login_lifetime_seconds=60) as (client, app, fake):
        flow, query = await tg_start(client)
        async with app.state.db_session_factory() as session:
            await session.execute(
                text("UPDATE social_login_challenges SET expires_at = '2000-01-01 00:00:00+00'")
            )
            await session.commit()
        response = await client.post(
            f'{S}/telegram/exchange',
            json={'code': 'c1', 'state': query['state'][0], 'flow_token': flow},
        )
        assert response.json()['code'] == 'social_state_invalid'


@pytest.mark.parametrize(
    ('token_kwargs', 'claims'),
    [
        ({'key': EVIL_KEY}, {}),  # bad signature
        ({}, {'aud': 'someone-else'}),
        ({}, {'iss': 'https://evil.example'}),
        ({}, {'exp': int(time.time()) - 600}),  # expired
        ({}, {'nonce': 'not-the-nonce'}),
        ({'kid': 'unknown'}, {}),
        ({'alg': 'HS256'}, {}),
    ],
)
async def test_telegram_bad_id_tokens_are_rejected(token_kwargs, claims):
    async with client_for() as (client, app, fake):
        flow, query = await tg_start(client)
        fake.id_token = make_token(tg_claims(**claims), **token_kwargs)
        response = await client.post(
            f'{S}/telegram/exchange',
            json={'code': 'c1', 'state': query['state'][0], 'flow_token': flow},
        )
        assert response.status_code == 401
        assert response.json()['code'] == 'social_token_invalid'
        assert await count(app, User) == 0


async def test_telegram_es256_and_missing_nonce_are_accepted():
    async with client_for() as (client, _app, fake):
        result = await tg_login(client, fake, claims=tg_claims(), path='telegram/start')
        assert result.json()['status'] == 'signed_in'
        flow, query = await tg_start(client)
        fake.id_token = make_token(tg_claims(nonce=query['nonce'][0]), kid='e1', alg='ES256')
        es = await client.post(
            f'{S}/telegram/exchange',
            json={'code': 'c2', 'state': query['state'][0], 'flow_token': flow},
        )
        assert es.json()['status'] == 'signed_in'


async def test_telegram_code_rejected_and_provider_down():
    async with client_for() as (client, _app, fake):
        fake.token_status = 400
        assert (await tg_login(client, fake)).json()['code'] == 'social_code_invalid'
        fake.token_status = 502
        response = await tg_login(client, fake)
        assert response.status_code == 503
        assert response.json()['code'] == 'social_provider_unreachable'


async def test_telegram_link_from_settings_and_conflicts():
    async with client_for() as (client, app, fake):
        code = await code_for(client, OTHER)
        tokens = (
            await client.post(f'{A}/otp/verify', json={'phone_number': OTHER, 'code': code})
        ).json()
        headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
        linked = await tg_login(client, fake, headers=headers, path='telegram/link/start')
        assert linked.json()['status'] == 'linked'
        # The verified Telegram phone differs from the account phone: no bot chat recorded.
        assert await count(app, TelegramLink) == 0
        listed = (await client.get(f'{S}/identities', headers=headers)).json()
        assert [row['provider'] for row in listed] == ['telegram']
        # A sign-in with that Telegram account now opens the linked account (not PHONE's).
        signed = (await tg_login(client, fake)).json()
        me = (await client.get(f'{A}/me', headers=bearer(signed))).json()
        assert me['phone_number'] == OTHER
        # Another user cannot link the same Telegram account.
        code = await code_for(client, PHONE)
        other = (
            await client.post(f'{A}/otp/verify', json={'phone_number': PHONE, 'code': code})
        ).json()
        clash = await tg_login(
            client, fake, headers={'Authorization': f'Bearer {other["access_token"]}'},
            path='telegram/link/start',
        )
        assert clash.status_code == 409 and clash.json()['code'] == 'identity_in_use'


# ---- Google --------------------------------------------------------------------------------


async def test_google_new_user_needs_phone_and_never_links_by_email():
    async with client_for() as (client, app, _fake):
        # An account with this phone exists; Google must not attach to it by itself.
        code = await code_for(client, PHONE)
        await client.post(f'{A}/otp/verify', json={'phone_number': PHONE, 'code': code})
        first = await client.post(f'{S}/google', json={'credential': make_token(google_claims())})
        assert first.status_code == 200, first.text
        body = first.json()
        assert body['status'] == 'phone_required' and body['tokens'] is None
        assert await count(app, ExternalIdentity) == 0
        # Wrong code: nothing linked.
        bad = await client.post(
            f'{S}/complete',
            json={'signup_token': body['signup_token'], 'phone_number': PHONE, 'code': '000000'},
        )
        assert bad.status_code == 401
        assert await count(app, ExternalIdentity) == 0
        # The phone code proves the account: now it is linked and signed in.
        code = await code_for(client, OTHER)
        done = await client.post(
            f'{S}/complete',
            json={'signup_token': body['signup_token'], 'phone_number': OTHER, 'code': code},
        )
        assert done.json()['status'] == 'signed_in'
        assert await count(app, User) == 2
        again = (
            await client.post(f'{S}/google', json={'credential': make_token(google_claims())})
        ).json()
        me = (await client.get(f'{A}/me', headers=bearer(again))).json()
        assert me['phone_number'] == OTHER


@pytest.mark.parametrize(
    'claims',
    [
        {'aud': 'other.apps.googleusercontent.com'},
        {'iss': 'https://evil.example'},
        {'exp': int(time.time()) - 600},
    ],
)
async def test_google_bad_tokens(claims):
    async with client_for() as (client, _app, _fake):
        response = await client.post(
            f'{S}/google', json={'credential': make_token(google_claims(**claims))}
        )
        assert response.status_code == 401 and response.json()['code'] == 'social_token_invalid'
    async with client_for() as (client, _app, _fake):
        response = await client.post(
            f'{S}/google', json={'credential': make_token(google_claims(), key=EVIL_KEY)}
        )
        assert response.json()['code'] == 'social_token_invalid'


async def test_google_android_audience_and_plain_issuer_are_accepted():
    async with client_for() as (client, _app, _fake):
        token = make_token(
            google_claims(
                aud='android-client.apps.googleusercontent.com', iss='accounts.google.com'
            )
        )
        response = await client.post(f'{S}/google', json={'credential': token})
        assert response.json()['status'] == 'phone_required'


async def test_link_and_unlink_google_rules():
    async with client_for() as (client, app, _fake):
        code = await code_for(client, PHONE)
        tokens = (
            await client.post(f'{A}/otp/verify', json={'phone_number': PHONE, 'code': code})
        ).json()
        headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
        linked = await client.post(
            f'{S}/google/link', headers=headers, json={'credential': make_token(google_claims())}
        )
        assert linked.json()['status'] == 'linked'
        second = await client.post(
            f'{S}/google/link', headers=headers,
            json={'credential': make_token(google_claims(sub='g-sub-2'))},
        )
        assert second.json()['code'] == 'provider_already_linked'
        # No password yet: unlinking is refused.
        refused = await client.delete(f'{S}/identities/google', headers=headers)
        assert refused.status_code == 409 and refused.json()['code'] == 'password_not_set'
        await client.post(
            f'{A}/registration', headers=headers,
            json={'username': 'demo_two', 'password': 'choy-va-sayr-9'},
        )
        assert (await client.delete(f'{S}/identities/google', headers=headers)).status_code == 204
        missing = await client.delete(f'{S}/identities/google', headers=headers)
        assert missing.json()['code'] == 'identity_not_linked'
        assert await count(app, ExternalIdentity) == 0


async def test_suspended_account_cannot_sign_in_socially():
    async with client_for() as (client, app, fake):
        assert (await tg_login(client, fake)).json()['status'] == 'signed_in'
        async with app.state.db_session_factory() as session:
            user = await session.scalar(select(User))
            user.account_status = AccountStatus.SUSPENDED
            await session.commit()
        response = await tg_login(client, fake)
        assert response.status_code == 403 and response.json()['code'] == 'account_unavailable'


async def test_rate_limit_per_ip():
    async with client_for(auth_password_ip_rate_limit_per_minute=3) as (client, _app, _fake):
        codes = []
        for _ in range(4):
            response = await client.post(f'{S}/google', json={'credential': 'not-a-token'})
            codes.append(response.json()['code'])
        assert codes == ['social_token_invalid'] * 3 + ['rate_limited']


async def test_jwks_is_cached():
    async with client_for() as (client, _app, fake):
        for _ in range(3):
            await client.post(f'{S}/google', json={'credential': make_token(google_claims())})
        assert fake.jwks_hits == 1


async def test_password_gate_allows_social_endpoints():
    async with client_for(auth_require_password_setup=True) as (client, _app, fake):
        body = (await tg_login(client, fake)).json()
        assert body['password_setup_required'] is True
        headers = bearer(body)
        assert (await client.get(f'{S}/identities', headers=headers)).status_code == 200
        blocked = await client.get('/api/v1/notifications', headers=headers)
        assert blocked.json()['code'] == 'password_setup_required'


# ---- Telegram: official JS library (ID token in the browser, nonce from us) -----------------


async def lib_login(client, fake_claims=None, headers=None, link=False):
    path = 'telegram/link/nonce' if link else 'telegram/nonce'
    issued = await client.post(f'{S}/{path}', headers=headers or {})
    assert issued.status_code == 201, issued.text
    nonce = issued.json()['nonce']
    token = make_token(tg_claims(nonce=nonce, **(fake_claims or {})))
    response = await client.post(
        f'{S}/telegram/link' if link else f'{S}/telegram',
        json={'id_token': token}, headers=headers or {},
    )
    return response, token


async def test_library_flow_needs_only_the_client_id():
    async with client_for(telegram_login_client_secret=None) as (client, app, fake):
        config = (await client.get(f'{S}/config')).json()
        assert config['telegram'] is True and config['telegram_code_flow'] is False
        assert (await client.post(f'{S}/telegram/start', json={})).status_code == 503
        response, _token = await lib_login(client)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body['status'] == 'signed_in' and body['password_setup_required'] is True
        assert not any(str(r.url).endswith('/token') for r in fake.requests)
        me = (await client.get(f'{A}/me', headers=bearer(body))).json()
        assert me['phone_number'] == PHONE
        assert await count(app, TelegramLink) == 1


async def test_library_flow_nonce_is_required_and_single_use():
    async with client_for() as (client, app, _fake):
        response, token = await lib_login(client)
        assert response.json()['status'] == 'signed_in'
        replay = await client.post(f'{S}/telegram', json={'id_token': token})
        assert replay.json()['code'] == 'social_state_invalid'
        no_nonce = await client.post(
            f'{S}/telegram', json={'id_token': make_token(tg_claims())}
        )
        assert no_nonce.status_code == 401 and no_nonce.json()['code'] == 'social_token_invalid'
        unknown = await client.post(
            f'{S}/telegram', json={'id_token': make_token(tg_claims(nonce='n' * 43))}
        )
        assert unknown.json()['code'] == 'social_state_invalid'
        bad_sig = await client.post(f'{S}/telegram/nonce')
        forged = make_token(tg_claims(nonce=bad_sig.json()['nonce']), key=EVIL_KEY)
        refused = await client.post(f'{S}/telegram', json={'id_token': forged})
        assert refused.json()['code'] == 'social_token_invalid'
        assert await count(app, User) == 1


async def test_library_flow_withheld_phone_and_link_nonce_scoping():
    async with client_for() as (client, app, _fake):
        response, _token = await lib_login(
            client, {'phone_number': None, 'phone_number_verified': None}
        )
        assert response.json()['status'] == 'phone_required'
        assert await count(app, User) == 0
        # A link nonce belongs to the signed-in user: it cannot sign anyone in.
        code = await code_for(client, OTHER)
        tokens = (
            await client.post(f'{A}/otp/verify', json={'phone_number': OTHER, 'code': code})
        ).json()
        headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
        link_nonce = (await client.post(f'{S}/telegram/link/nonce', headers=headers)).json()
        token = make_token(tg_claims(nonce=link_nonce['nonce'], sub='tg-sub-9'))
        misuse = await client.post(f'{S}/telegram', json={'id_token': token})
        assert misuse.json()['code'] == 'social_state_invalid'
        linked, _token = await lib_login(client, {'sub': 'tg-sub-9'}, headers=headers, link=True)
        assert linked.json()['status'] == 'linked'
