from uuid import UUID

from fastapi.testclient import TestClient
from support import API, png

from yondo_api.safety.models import UserBlock

from .helpers import B, request_booking

C = f'{API}/chat'


async def test_booking_chat_flow_and_unread_counts(market):
    companion = await market.companion()
    booking = await request_booking(market, companion)
    url = f'{C}/bookings/{booking["id"]}/messages'
    history = await market.client.get(url, headers=market.customer)
    assert [m['kind'] for m in history.json()] == ['booking_details']
    assert history.json()[0]['payload']['total_minor'] == 110_000
    sent = await market.client.post(
        url, headers=market.customer, json={'kind': 'text', 'body': 'Salom!'}
    )
    assert sent.status_code == 201, sent.text
    unread = await market.client.get(f'{C}/unread', headers=companion.headers)
    assert unread.json() == {'unread': 2}
    conversations = await market.client.get(f'{C}/conversations', headers=companion.headers)
    convo = conversations.json()[0]
    assert convo['counterpart_name'] == 'Sardor'
    assert convo['last_message']['body'] == 'Salom!'
    assert convo['can_send'] is True
    assert (
        await market.client.post(f'{C}/bookings/{booking["id"]}/read', headers=companion.headers)
    ).status_code == 204
    assert (await market.client.get(f'{C}/unread', headers=companion.headers)).json() == {
        'unread': 0
    }
    point = await market.client.post(
        url,
        headers=companion.headers,
        json={'kind': 'meeting_point', 'meeting_point': {'name': 'Gate 2'}, 'body': 'Here'},
    )
    assert point.json()['payload']['name'] == 'Gate 2'
    image = await market.client.post(
        f'{C}/bookings/{booking["id"]}/images',
        headers={**market.customer, 'Content-Type': 'image/png'},
        content=png(),
    )
    assert image.status_code == 201, image.text
    assert image.json()['image_url'].startswith('https://storage.test/private/chat/')
    assert 'storage_key' not in image.json()['payload']
    newer = await market.client.get(
        url, headers=companion.headers, params={'after': sent.json()['created_at']}
    )
    assert [m['kind'] for m in newer.json()] == ['meeting_point', 'image']
    stranger, _ = await market.user()
    assert (await market.client.get(url, headers=stranger)).status_code == 404
    empty = await market.client.post(
        url, headers=market.customer, json={'kind': 'text', 'body': ''}
    )
    assert empty.status_code == 422


async def test_chat_closes_after_cancellation_and_respects_blocks(market):
    companion = await market.companion()
    booking = await request_booking(market, companion)
    url = f'{C}/bookings/{booking["id"]}/messages'
    async with market.app.state.db_session_factory() as session:
        session.add(UserBlock(blocker_id=companion.user_id, blocked_id=market.customer_id))
        await session.commit()
    blocked = await market.client.post(url, headers=market.customer, json={'body': 'Hi'})
    assert blocked.status_code == 403
    await market.client.post(f'{B}/{booking["id"]}/cancel', headers=market.customer, json={})
    closed = await market.client.post(url, headers=companion.headers, json={'body': 'Hi'})
    assert closed.status_code == 409 and closed.json()['code'] == 'chat_closed'
    events = [
        m['payload'].get('event')
        for m in (await market.client.get(url, headers=market.customer)).json()
    ]
    assert events == ['requested', 'customer_cancelled']


def test_websocket_streams_events_after_commit(tmp_path):
    from support import MemoryStorage, PerUserIdentity

    from yondo_api.config import Settings
    from yondo_api.db.base import Base
    from yondo_api.main import create_application

    app = create_application(
        Settings(environment='test', database_url=f'sqlite+aiosqlite:///{tmp_path}/ws.db'),
        object_storage=MemoryStorage(),
        identity_eligibility=PerUserIdentity(),
    )
    with TestClient(app) as client:

        async def create_schema():
            async with app.state.db_engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

        client.portal.call(create_schema)
        issued = client.post(f'{API}/auth/otp/request', json={'phone_number': '901234000'})
        tokens = client.post(
            f'{API}/auth/otp/verify',
            json={'phone_number': '901234000', 'code': issued.json()['development_otp']},
        ).json()
        with client.websocket_connect(
            f'{API}/realtime/ws?access_token={tokens["access_token"]}'
        ) as socket:
            ready = socket.receive_json()
            assert ready['type'] == 'ready'
            socket.send_text('ping')
            assert socket.receive_text() == 'pong'
            user_id = UUID(ready['user_id'])

            async def notify_user():
                from yondo_api.notifications.service import notify

                async with app.state.db_session_factory() as session:
                    session.info['realtime_broker'] = app.state.realtime_broker
                    notify(session, user_id, 'test', 'Hello', 'World')
                    await session.commit()

            client.portal.call(notify_user)
            event = socket.receive_json()
            assert event['type'] == 'notification'
            assert event['notification']['title'] == 'Hello'
        # Preferred flow: credentials in the first message, never in the URL.
        with client.websocket_connect(f'{API}/realtime/ws') as socket:
            socket.send_json({'type': 'auth', 'access_token': tokens['access_token']})
            assert socket.receive_json()['type'] == 'ready'
        try:
            with client.websocket_connect(f'{API}/realtime/ws?access_token=bad') as socket:
                socket.receive_json()
            raise AssertionError('unauthenticated socket must be closed')
        except Exception as exc:  # starlette raises WebSocketDisconnect with code 4401
            assert getattr(exc, 'code', 4401) == 4401
