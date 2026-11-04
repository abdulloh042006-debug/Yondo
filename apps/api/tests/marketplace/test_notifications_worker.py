import json
from datetime import timedelta

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select
from support import API

from yondo_api.core.time import utc_now
from yondo_api.integrations.notifications import PushMessage
from yondo_api.integrations.push import FcmPushProvider, InvalidPushToken
from yondo_api.notifications.models import DeviceToken, Notification
from yondo_api.worker import run_jobs

from .helpers import B, completed_booking, confirmed_booking, shift_booking


async def kinds_for(market, user_id):
    async with market.app.state.db_session_factory() as session:
        return list(
            await session.scalars(select(Notification.kind).where(Notification.user_id == user_id))
        )


async def test_worker_sends_reminders_once_and_dispatches_push(market):
    companion = await market.companion()
    booking, _ = await confirmed_booking(market, companion)
    soon = utc_now() + timedelta(minutes=30)
    await shift_booking(market, booking['id'], starts_at=soon, ends_at=soon + timedelta(hours=1))
    await market.client.put(
        f'{API}/notifications/devices',
        headers=market.customer,
        json={'token': 'customer-device-1', 'platform': 'android'},
    )
    first = await run_jobs(market.app.state)
    second = await run_jobs(market.app.state)
    assert first['meeting_reminders'] == 2 and second['meeting_reminders'] == 0
    assert first['dispatch_push'] >= 1
    assert all(value >= 0 for value in first.values())
    assert (await kinds_for(market, market.customer_id)).count('meeting_reminder') == 1
    pushed = market.app.state.push_provider.sent
    assert any(
        m.token == 'customer-device-1' and m.data['kind'] == 'meeting_reminder' for m in pushed
    )
    async with market.app.state.db_session_factory() as session:
        statuses = {
            n.push_status
            for n in await session.scalars(
                select(Notification).where(Notification.user_id == companion.user_id)
            )
        }
    assert statuses == {'skipped'}  # the companion has no registered device


async def test_review_reminders_skip_parties_who_reviewed(market):
    companion = await market.companion()
    booking, _ = await completed_booking(market, companion)
    await market.client.post(
        f'{B}/{booking["id"]}/review', headers=market.customer, json={'rating': 5}
    )
    await shift_booking(market, booking['id'], ended_at=utc_now() - timedelta(hours=3))
    results = await run_jobs(market.app.state)
    assert results['review_reminders'] == 1
    assert 'review_reminder' in await kinds_for(market, companion.user_id)
    assert 'review_reminder' not in await kinds_for(market, market.customer_id)


def service_account():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    return key, {
        'client_email': 'push@yondo-test.iam.gserviceaccount.com',
        'private_key_id': 'kid-1',
        'private_key': pem,
        'project_id': 'yondo-test',
    }


async def test_fcm_provider_signs_assertion_and_sends(tmp_path):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    key, account = service_account()
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.host == 'oauth2.googleapis.com':
            return httpx.Response(200, json={'access_token': 'token-1', 'expires_in': 3600})
        body = json.loads(request.content)
        if body['message']['token'] == 'dead':
            return httpx.Response(
                404,
                json={'error': {'status': 'NOT_FOUND', 'details': [{'errorCode': 'UNREGISTERED'}]}},
            )
        return httpx.Response(200, json={'name': 'projects/yondo-test/messages/1'})

    provider = FcmPushProvider(
        account, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    assertion = provider.assertion(now=1_700_000_000)
    header, claims, signature = assertion.split('.')
    import base64

    def decode(part):
        return base64.urlsafe_b64decode(part + '=' * (-len(part) % 4))

    assert json.loads(decode(header))['kid'] == 'kid-1'
    assert json.loads(decode(claims))['scope'].endswith('firebase.messaging')
    key.public_key().verify(
        decode(signature), f'{header}.{claims}'.encode(), padding.PKCS1v15(), hashes.SHA256()
    )
    name = await provider.send(PushMessage('device', 'Salom', 'Body', {'a': '1'}))
    assert name == 'projects/yondo-test/messages/1'
    assert calls[-1].headers['authorization'] == 'Bearer token-1'
    await provider.send(PushMessage('device', 'Again', '', {}))
    assert sum(1 for call in calls if call.url.host == 'oauth2.googleapis.com') == 1
    try:
        await provider.send(PushMessage('dead', 'x', '', {}))
        raise AssertionError('expected InvalidPushToken')
    except InvalidPushToken:
        pass
    path = tmp_path / 'sa.json'
    path.write_text(json.dumps(account))
    assert FcmPushProvider.from_file(str(path)).project_id == 'yondo-test'


async def test_invalid_device_tokens_are_removed(market):
    class Rejecting:
        async def send(self, message):
            raise InvalidPushToken(message.token)

    await market.client.put(
        f'{API}/notifications/devices',
        headers=market.customer,
        json={'token': 'stale-device-1', 'platform': 'ios'},
    )
    from yondo_api.notifications.jobs import dispatch_push
    from yondo_api.notifications.service import notify

    async with market.app.state.db_session_factory() as session:
        notify(session, market.customer_id, 'test', 'Hello')
        await session.commit()
        await dispatch_push(session, Rejecting())
        assert list(await session.scalars(select(DeviceToken))) == []
