"""Push notifications: device registry, public config, background delivery (providers mocked)."""
import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import delete, func, select

from yondo_api.account.deletion import erase_account
from yondo_api.models.user import User
from yondo_api.push import webpush
from yondo_api.push.fcm import FcmSender, ServiceAccount
from yondo_api.push.messages import push_text, resolve_locale
from yondo_api.push.models import PushDevice, PushVapidKey
from yondo_api.push.service import load_vapid_keys

from .test_bookings import booking_payload, setup_bookable_companion

ROOT = '/api/v1/push'


def browser_subscription(host='fcm.googleapis.com', n=1):
    """A real P-256 key pair, as a browser would create it; the private half lets us decrypt."""
    key = ec.generate_private_key(ec.SECP256R1())
    auth = bytes(range(16))
    return key, auth, {
        'platform': 'web',
        'endpoint': f'https://{host}/fcm/send/device-{n}',
        'p256dh': webpush.b64url(webpush.public_bytes(key.public_key())),
        'auth': webpush.b64url(auth),
    }


def decrypt(body: bytes, ua_private, auth: bytes) -> dict:
    """The receiving browser's side of RFC 8291, to prove the payload is readable."""
    import hashlib
    import hmac

    def h(k, d):
        return hmac.new(k, d, hashlib.sha256).digest()

    salt, idlen = body[:16], body[20]
    as_public = body[21:21 + idlen]
    shared = ua_private.exchange(
        ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_public)
    )
    ua_public = webpush.public_bytes(ua_private.public_key())
    ikm = h(h(auth, shared), b'WebPush: info\x00' + ua_public + as_public + b'\x01')
    prk = h(salt, ikm)
    cek = h(prk, b'Content-Encoding: aes128gcm\x00\x01')[:16]
    nonce = h(prk, b'Content-Encoding: nonce\x00\x01')[:12]
    plain = AESGCM(cek).decrypt(nonce, body[21 + idlen:], None)
    assert plain.endswith(b'\x02')
    return json.loads(plain[:-1])


def service_account_json():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return json.dumps({
        'type': 'service_account', 'project_id': 'yondo-test', 'private_key': pem,
        'client_email': 'push@yondo-test.iam.gserviceaccount.com',
        'token_uri': 'https://oauth2.googleapis.com/token',
    })


class FakePushServices:
    """Mock transport for FCM (OAuth + send) and Web Push endpoints."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.web_status = 201
        self.fcm_status = 200
        self.fcm_error = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.host == 'oauth2.googleapis.com':
            return httpx.Response(200, json={'access_token': 'test-access', 'expires_in': 3600})
        if request.url.path.endswith('messages:send'):
            if self.fcm_error:
                return httpx.Response(self.fcm_status, json={'error': {
                    'status': 'NOT_FOUND',
                    'details': [{'errorCode': self.fcm_error}],
                }})
            return httpx.Response(self.fcm_status, json={'name': 'projects/x/messages/1'})
        return httpx.Response(self.web_status)

    def sent(self, kind):
        if kind == 'fcm':
            return [r for r in self.requests if r.url.path.endswith('messages:send')]
        return [r for r in self.requests if r.url.host != 'oauth2.googleapis.com'
                and not r.url.path.endswith('messages:send')]


def install(e, *, android=True):
    fake = FakePushServices()
    push = e['app'].state.push_dispatcher
    push.transport = httpx.MockTransport(fake)
    push.fcm = FcmSender(ServiceAccount.from_json(service_account_json())) if android else None
    return fake, push


async def booking_request(e):
    service = await setup_bookable_companion(e)
    created = await e['client'].post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert created.status_code == 201, created.text
    return created.json()['id']


@pytest.mark.asyncio
async def test_config_is_public_and_vapid_key_is_generated_once(prepared):
    e, client = prepared, prepared['client']
    first = await client.get(f'{ROOT}/config')
    assert first.status_code == 200
    body = first.json()
    assert body['web']['enabled'] is True and body['android'] == {'enabled': False}
    key = webpush.b64url_decode(body['web']['vapid_public_key'])
    assert len(key) == 65 and key[0] == 4
    # A fresh dispatcher (another worker / a restart) reuses the stored key pair.
    e['app'].state.push_dispatcher._vapid = None
    again = (await client.get(f'{ROOT}/config')).json()
    assert again['web']['vapid_public_key'] == body['web']['vapid_public_key']
    assert 'private' not in json.dumps(again)
    async with e['app'].state.db_session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(PushVapidKey)) == 1


@pytest.mark.asyncio
async def test_register_requires_auth_validates_and_is_unique(prepared):
    e, client = prepared, prepared['client']
    _, _, sub = browser_subscription()
    assert (await client.put(f'{ROOT}/devices', json=sub)).status_code == 401
    bad_host = {**sub, 'endpoint': 'https://169.254.169.254/latest'}
    refused = await client.put(f'{ROOT}/devices', headers=e['customer'], json=bad_host)
    assert refused.status_code == 422 and refused.json()['code'] == 'push_endpoint_not_allowed'
    bad_keys = {**sub, 'p256dh': 'A' * 87}
    refused = await client.put(f'{ROOT}/devices', headers=e['customer'], json=bad_keys)
    assert refused.json()['code'] == 'push_keys_invalid'
    mixed = {**sub, 'token': 'x' * 40}
    assert (await client.put(f'{ROOT}/devices', headers=e['customer'], json=mixed)
            ).status_code == 422
    android = await client.put(
        f'{ROOT}/devices', headers=e['customer'], json={'platform': 'android', 'token': 'f' * 64}
    )
    assert android.status_code == 503 and android.json()['code'] == 'push_unavailable'

    first = await client.put(f'{ROOT}/devices', headers=e['customer'], json=sub)
    assert first.status_code == 200, first.text
    again = await client.put(f'{ROOT}/devices', headers=e['customer'], json=sub)
    assert again.json()['id'] == first.json()['id']
    # Same browser, another account signs in: the subscription moves, it is not duplicated.
    moved = await client.put(f'{ROOT}/devices', headers=e['owner'], json=sub)
    assert moved.json()['id'] == first.json()['id']
    async with e['app'].state.db_session_factory() as session:
        rows = list(await session.scalars(select(PushDevice)))
    assert len(rows) == 1 and str(rows[0].user_id) == e['owner_id']

    device_id = first.json()['id']
    assert (await client.delete(f'{ROOT}/devices/{device_id}', headers=e['customer'])
            ).status_code == 404
    assert (await client.delete(f'{ROOT}/devices/{device_id}', headers=e['owner'])
            ).status_code == 204
    assert (await client.delete(f'{ROOT}/devices/{device_id}', headers=e['owner'])
            ).status_code == 404


@pytest.mark.asyncio
async def test_notification_triggers_push_to_web_and_android(prepared):
    e, client = prepared, prepared['client']
    fake, push = install(e)
    config = (await client.get(f'{ROOT}/config')).json()
    assert config['android']['enabled'] is True
    ua_key, auth, sub = browser_subscription()
    assert (await client.put(f'{ROOT}/devices', headers=e['owner'], json=sub)).status_code == 200
    android = await client.put(
        f'{ROOT}/devices', headers=e['owner'], json={'platform': 'android', 'token': 't' * 80}
    )
    assert android.status_code == 200, android.text
    async with e['app'].state.db_session_factory() as session:
        owner = await session.get(User, UUID(e['owner_id']))
        owner.ui_locale = 'ru'
        await session.commit()

    booking_id = await booking_request(e)  # the companion (owner) gets booking_requested
    await push.drain()

    web = fake.sent('web')
    assert len(web) == 1
    request = web[0]
    assert request.headers['content-encoding'] == 'aes128gcm'
    assert request.headers['authorization'].startswith('vapid t=')
    assert request.headers['authorization'].endswith('k=' + config['web']['vapid_public_key'])
    payload = decrypt(request.content, ua_key, auth)
    assert payload['title'] == 'Yondo'
    assert payload['body'] == 'Новое уведомление: новый запрос на бронь'
    assert payload['url'] == f'/bookings/{booking_id}'
    assert payload['kind'] == 'booking_requested'
    # No personal data on the lock screen.
    assert 'Test companion' not in json.dumps(payload, ensure_ascii=False)

    fcm = fake.sent('fcm')
    assert len(fcm) == 1
    assert fcm[0].url.path == '/v1/projects/yondo-test/messages:send'
    assert fcm[0].headers['authorization'] == 'Bearer test-access'
    message = json.loads(fcm[0].content)['message']
    assert message['token'] == 't' * 80
    assert message['notification']['body'] == 'Новое уведомление: новый запрос на бронь'
    assert message['android']['notification']['channel_id'] == 'yondo'
    assert message['data']['url'] == f'/bookings/{booking_id}'
    # The customer (the actor) has no devices and gets nothing.
    assert len(fake.requests) == 3  # oauth + fcm + web


@pytest.mark.asyncio
async def test_vapid_key_survives_a_lost_insert(prepared):
    """CI flake (2026-11-18): on a connection shared with other sessions, another session's
    rollback could discard our insert before its commit; the re-read found nothing and the web
    send crashed silently. Now the next attempt, in a fresh session, stores the key."""
    app = prepared['app']
    factory = app.state.db_session_factory
    async with factory() as session:
        await session.execute(delete(PushVapidKey))
        await session.commit()
    lost = []

    def losing_factory():
        session = factory()
        if not lost:
            lost.append(True)

            async def commit_that_gets_rolled_back():
                await session.rollback()

            session.commit = commit_that_gets_rolled_back
        return session

    keys = await load_vapid_keys(losing_factory, app.state.settings)
    async with factory() as session:
        stored = await session.get(PushVapidKey, 1)
    assert lost and stored is not None and keys.public_key == stored.public_key


@pytest.mark.asyncio
async def test_drain_never_spins_on_a_finished_task(prepared):
    """CI hang (2026-11-18): a finished task left in the set (its done callback had not removed
    it) made drain() loop for ever. drain() now drops finished tasks itself and has a deadline."""
    push = prepared['app'].state.push_dispatcher

    async def nothing():
        return None

    finished = asyncio.get_running_loop().create_task(nothing())
    await finished
    push._tasks.add(finished)  # as if the done callback never ran
    await asyncio.wait_for(push.drain(), timeout=2)
    assert not push._tasks

    never = asyncio.get_running_loop().create_task(asyncio.Event().wait())
    push._tasks.add(never)
    await asyncio.wait_for(push.drain(timeout=0.05), timeout=2)  # gives up, does not hang
    never.cancel()
    push._tasks.discard(never)


@pytest.mark.asyncio
async def test_concurrent_first_use_yields_one_key_pair(prepared):
    app = prepared['app']
    factory = app.state.db_session_factory
    async with factory() as session:
        await session.execute(delete(PushVapidKey))
        await session.commit()
    results = await asyncio.gather(
        *(load_vapid_keys(factory, app.state.settings) for _ in range(4))
    )
    assert len({k.public_key for k in results}) == 1
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(PushVapidKey)) == 1


@pytest.mark.asyncio
async def test_invalid_tokens_are_pruned_and_failures_never_break_requests(prepared):
    e, client = prepared, prepared['client']
    fake, push = install(e)
    # The key pair exists before the background send: first-use generation is covered on its own
    # (test_vapid_key_survives_a_lost_insert), so this test never depends on task timing.
    await push.vapid()
    _, _, sub = browser_subscription()
    await client.put(f'{ROOT}/devices', headers=e['owner'], json=sub)
    await client.put(
        f'{ROOT}/devices', headers=e['owner'], json={'platform': 'android', 'token': 'u' * 80}
    )
    fake.web_status, fake.fcm_status, fake.fcm_error = 410, 404, 'UNREGISTERED'
    booking_id = await booking_request(e)
    await push.drain()
    async with e['app'].state.db_session_factory() as session:
        devices = list(await session.scalars(select(PushDevice)))
    assert len(devices) == 2 and all(d.disabled_at is not None for d in devices)

    # Re-registering re-enables a disabled device.
    reenabled = await client.put(f'{ROOT}/devices', headers=e['owner'], json=sub)
    assert reenabled.status_code == 200
    async with e['app'].state.db_session_factory() as session:
        web = await session.scalar(select(PushDevice).where(PushDevice.platform == 'web'))
    assert web.disabled_at is None

    # A provider that is down (timeouts) never fails the request that made the notice, and a
    # timeout does not prune the device.
    def broken(request):
        raise httpx.ConnectTimeout('down')

    push.transport = httpx.MockTransport(broken)
    _, _, customer_sub = browser_subscription(n=2)
    await client.put(f'{ROOT}/devices', headers=e['customer'], json=customer_sub)
    accepted = await client.post(f'/api/v1/bookings/{booking_id}/accept', headers=e['owner'])
    assert accepted.status_code == 200, accepted.text
    await push.drain()
    async with e['app'].state.db_session_factory() as session:
        disabled = await session.scalar(
            select(func.count()).select_from(PushDevice).where(PushDevice.disabled_at.is_not(None))
        )
    assert disabled == 1  # only the Android token reported UNREGISTERED earlier


@pytest.mark.asyncio
async def test_rolled_back_notifications_are_not_pushed(prepared):
    e = prepared
    fake, push = install(e, android=False)
    _, _, sub = browser_subscription()
    await e['client'].put(f'{ROOT}/devices', headers=e['owner'], json=sub)
    from yondo_api.notifications.models import UserNotification

    async with e['app'].state.db_session_factory() as session:
        booking_id = await booking_request(e)
        await push.drain()
        fake.requests.clear()
        session.add(UserNotification(
            recipient_id=UUID(e['owner_id']), booking_id=UUID(booking_id), kind='chat_message',
            source_key='chat_message:rollback', details={}, created_at=datetime.now(UTC),
        ))
        await session.flush()
        await session.rollback()
    await push.drain()
    assert fake.requests == []


@pytest.mark.asyncio
async def test_account_deletion_removes_devices(prepared):
    e = prepared
    install(e)
    _, _, sub = browser_subscription()
    await e['client'].put(f'{ROOT}/devices', headers=e['owner'], json=sub)
    async with e['app'].state.db_session_factory() as session:
        user = await session.get(User, UUID(e['owner_id']))
        await erase_account(session, user, e['storage'], datetime.now(UTC))
        await session.commit()
        left = await session.scalar(select(func.count()).select_from(PushDevice))
    assert left == 0


def test_lock_screen_texts_and_locales():
    assert push_text('booking_accepted', 'uz-Latn-1995') == (
        'Yondo', 'Yangi bildirishnoma: bron qabul qilindi'
    )
    assert push_text('payment_confirmed', 'uz-Latn-2026')[1] == (
        'Yangi bildirişnoma: tölov tasdiqlandi'
    )
    assert push_text('gift_delivered', 'en')[1] == 'New notification: gift order updated'
    assert push_text('unknown_kind', 'en')[1] == 'New notification'
    from datetime import date
    assert resolve_locale(None, date(2026, 11, 18)) == 'uz-Latn-1995'
    assert resolve_locale(None, date(2027, 4, 22)) == 'uz-Latn-2026'


def test_rfc8291_vector_and_endpoint_allowlist():
    as_private = webpush.private_from_raw(
        webpush.b64url_decode('yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw')
    )
    out = webpush.encrypt(
        b'When I grow up, I want to be a watermelon',
        webpush.b64url_decode(
            'BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIA'
            'iw4'
        ),
        webpush.b64url_decode('BTBZMqHH6r4Tts7J_aSIgg'),
        salt=webpush.b64url_decode('DGv6ra1nlYgDCS1FRnbzlw'),
        as_private=as_private,
    )
    assert webpush.b64url(out) == (
        'DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmY'
        'WAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQe'
        'xSgSxsj_Qulcy4a-fN'
    )
    hosts = ('fcm.googleapis.com', 'push.apple.com')
    assert webpush.endpoint_allowed('https://web.push.apple.com/abc', hosts)
    assert not webpush.endpoint_allowed('http://fcm.googleapis.com/x', hosts)
    assert not webpush.endpoint_allowed('https://evilpush.apple.com.example/x', hosts)
    assert not webpush.endpoint_allowed('https://fcm.googleapis.com:8443/x', hosts)
    assert not webpush.endpoint_allowed('https://u@fcm.googleapis.com/x', hosts)


def test_bad_service_account_json_is_rejected_without_echoing_it():
    from yondo_api.push.fcm import FcmConfigError

    with pytest.raises(FcmConfigError) as caught:
        ServiceAccount.from_json('{"private_key": "SECRET-MATERIAL", "client_email": "a"}')
    assert 'SECRET' not in str(caught.value)
