import asyncio
from datetime import UTC, datetime

import pytest
from support import API, create_user, running_app, sign_in

from yondo_api.core.money import apply_bps
from yondo_api.integrations.local_storage import LocalObjectStorage
from yondo_api.integrations.s3 import S3ObjectStorage
from yondo_api.notifications.service import notify
from yondo_api.realtime.broker import user_channel


def test_apply_bps_rounds_half_up_with_integers():
    assert apply_bps(10_000, 1000) == 1000
    assert apply_bps(15, 5000) == 8
    assert apply_bps(0, 1234) == 0
    with pytest.raises(ValueError):
        apply_bps(-1, 10)


def test_s3_presigned_url_matches_aws_reference_vector():
    # AWS documentation example for a presigned GET with virtual-hosted style URL.
    storage = S3ObjectStorage(
        endpoint='https://s3.amazonaws.com',
        bucket='examplebucket',
        access_key='AKIAIOSFODNN7EXAMPLE',
        secret_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
        region='us-east-1',
        path_style=False,
    )
    url = storage.presign('GET', 'test.txt', 86400, now=datetime(2013, 5, 24, tzinfo=UTC))
    assert url.startswith('https://examplebucket.s3.amazonaws.com/test.txt?')
    assert url.endswith(
        'X-Amz-Signature=aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404'
    )


def test_s3_requires_credentials():
    with pytest.raises(ValueError):
        S3ObjectStorage(
            endpoint='http://localhost:9000',
            bucket='b',
            access_key='',
            secret_key='',
            region='us-east-1',
        )


async def test_local_storage_round_trip_and_signed_download(tmp_path):
    storage = LocalObjectStorage(str(tmp_path), b'secret', 'http://test/api/v1/storage/local')

    async def chunks():
        yield b'image-bytes'

    async with running_app(storage=storage) as (app, client):
        await storage.upload('a/b.jpg', chunks(), 'image/jpeg')
        url = await storage.create_download_url('a/b.jpg')
        response = await client.get(url.removeprefix('http://test'))
        assert response.status_code == 200
        assert response.content == b'image-bytes'
        tampered = url.replace('signature=', 'signature=0')
        assert (await client.get(tampered.removeprefix('http://test'))).status_code == 404
        await storage.delete('a/b.jpg')
        assert (await client.get(url.removeprefix('http://test'))).status_code == 404
    with pytest.raises(ValueError):
        storage.path_for('../escape')


async def test_profile_completion_activates_pending_account_only_when_adult():
    async with running_app() as (app, client):
        headers, _ = await sign_in(client, '901110001')
        me = (await client.get(f'{API}/auth/me', headers=headers)).json()
        assert me['account_status'] == 'verification_pending'
        assert me['profile_complete'] is False
        minor = await client.put(
            f'{API}/auth/profile',
            headers=headers,
            json={'display_name': 'Ali', 'age': 16, 'gender': 'male', 'city': 'Tashkent'},
        )
        assert minor.json()['profile_complete'] is True
        assert minor.json()['account_status'] == 'verification_pending'
        adult = await client.put(f'{API}/auth/profile', headers=headers, json={'age': 20})
        assert adult.json()['account_status'] == 'active'
        assert adult.json()['display_name'] == 'Ali'


async def test_notifications_list_read_and_realtime_after_commit():
    async with running_app() as (app, client):
        headers, user_id = await create_user(app, client, '901110002')
        broker = app.state.realtime_broker
        async with broker.subscribe(user_channel(user_id)) as events:
            async with app.state.db_session_factory() as session:
                session.info['realtime_broker'] = broker
                notify(session, user_id, 'test', 'Salom', 'Body', {'x': 1})
                await session.rollback()
                notify(session, user_id, 'test', 'Committed', 'Body', {'x': 2})
                await session.commit()
            event = await asyncio.wait_for(anext(events), 2)
            assert event['notification']['title'] == 'Committed'
            assert event['notification']['data'] == {'x': '2'}
        listed = await client.get(f'{API}/notifications', headers=headers)
        assert [item['title'] for item in listed.json()['items']] == ['Committed']
        count = await client.get(f'{API}/notifications/unread-count', headers=headers)
        assert count.json() == {'unread': 1}
        item_id = listed.json()['items'][0]['id']
        read = await client.post(f'{API}/notifications/{item_id}/read', headers=headers)
        assert read.json()['read_at'] is not None
        other, _ = await create_user(app, client, '901110003')
        assert (
            await client.post(f'{API}/notifications/{item_id}/read', headers=other)
        ).status_code == 404
        assert (
            await client.post(f'{API}/notifications/read-all', headers=headers)
        ).status_code == 204


async def test_cors_is_opt_in_per_origin():
    async with running_app(cors_allow_origins=('http://localhost:5173',)) as (_, client):
        allowed = await client.options(
            f'{API}/auth/me',
            headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET'},
        )
        assert allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'
        denied = await client.options(
            f'{API}/auth/me',
            headers={'Origin': 'https://evil.test', 'Access-Control-Request-Method': 'GET'},
        )
        assert 'access-control-allow-origin' not in denied.headers
    async with running_app() as (_, client):
        response = await client.get('/health', headers={'Origin': 'http://localhost:5173'})
        assert 'access-control-allow-origin' not in response.headers


async def test_device_registration_moves_token_between_accounts():
    async with running_app() as (app, client):
        first, _ = await create_user(app, client, '901110004')
        second, _ = await create_user(app, client, '901110005')
        payload = {'token': 'device-token-1234', 'platform': 'android'}
        assert (
            await client.put(f'{API}/notifications/devices', headers=first, json=payload)
        ).status_code == 204
        assert (
            await client.put(f'{API}/notifications/devices', headers=second, json=payload)
        ).status_code == 204
        bad = await client.put(
            f'{API}/notifications/devices', headers=second, json={'token': 'x', 'platform': 'pc'}
        )
        assert bad.status_code == 422
        removed = await client.post(
            f'{API}/notifications/devices/remove', headers=second, json={'token': payload['token']}
        )
        assert removed.status_code == 204
