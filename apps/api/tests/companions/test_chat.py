from uuid import UUID

import pytest
from sqlalchemy import select

from yondo_api.chat.models import ChatAccessTicket, ChatMessage
from yondo_api.chat.service import ticket_digest

from .test_bookings import booking_payload, setup_bookable_companion


@pytest.mark.asyncio
async def test_booking_chat_private_messages_read_cursors_and_one_time_ticket(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert booking.status_code == 201
    booking_id = booking.json()['id']

    posted = await client.post(
        f'/api/v1/chat/bookings/{booking_id}/messages',
        headers=e['customer'],
        json={'kind': 'meeting_point', 'body': 'Main entrance'},
    )
    assert posted.status_code == 201, posted.text
    assert posted.json()['kind'] == 'meeting_point'
    history = await client.get(f'/api/v1/chat/bookings/{booking_id}/messages', headers=e['owner'])
    assert history.status_code == 200
    assert [message['kind'] for message in history.json()] == ['system', 'meeting_point']
    assert history.json()[0]['system_code'] == 'booking_requested'

    unread = await client.get('/api/v1/chat/unread', headers=e['owner'])
    assert unread.status_code == 200
    assert unread.json() == [{'booking_id': booking_id, 'unread_count': 1}]
    read = await client.post(f'/api/v1/chat/bookings/{booking_id}/read', headers=e['owner'])
    assert read.json()['unread_count'] == 0
    assert (await client.get('/api/v1/chat/unread', headers=e['owner'])).json() == []

    ticket_response = await client.post(
        f'/api/v1/chat/bookings/{booking_id}/socket-ticket', headers=e['customer']
    )
    assert ticket_response.status_code == 200
    digest = ticket_digest(ticket_response.json()['ticket'])
    async with e['app'].state.db_session_factory() as session:
        ticket = await session.scalar(
            select(ChatAccessTicket).where(ChatAccessTicket.token_hash == digest)
        )
        assert ticket is not None
        ticket.consumed_at = ticket.expires_at
        await session.commit()
    outsider = await client.get(f'/api/v1/chat/bookings/{booking_id}/messages', headers=e['other'])
    assert outsider.status_code == 404
    async with e['app'].state.db_session_factory() as session:
        messages = list(
            await session.scalars(
                select(ChatMessage).where(ChatMessage.booking_id == UUID(booking_id))
            )
        )
        assert len(messages) == 2


@pytest.mark.asyncio
async def test_chat_rejects_closed_booking_and_invalid_messages(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    booking_id = booking.json()['id']
    cancelled = await client.post(
        f'/api/v1/bookings/{booking_id}/cancel', headers=e['customer'], json={}
    )
    assert cancelled.status_code == 200
    closed = await client.post(
        f'/api/v1/chat/bookings/{booking_id}/messages',
        headers=e['customer'],
        json={'body': 'hello'},
    )
    assert closed.status_code == 409
