from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.bookings.models import Booking
from yondo_api.chat.models import ChatMessage


def append_system_message(
    session: AsyncSession, booking_id: UUID, code: str, payload: dict | None = None
) -> ChatMessage:
    message = ChatMessage(
        booking_id=booking_id,
        sender_id=None,
        kind='system',
        body=code.replace('_', ' '),
        payload=payload or {},
        system_code=code,
    )
    session.add(message)
    return message


async def publish(request: Request, message: ChatMessage) -> None:
    try:
        await request.app.state.redis.publish(
            f'yondo:chat:{message.booking_id}',
            json.dumps(
                {
                    'id': str(message.id),
                    'booking_id': str(message.booking_id),
                    'sender_id': str(message.sender_id) if message.sender_id else None,
                    'kind': message.kind,
                    'body': message.body,
                    'payload': message.payload,
                    'system_code': message.system_code,
                    'created_at': message.created_at.isoformat(),
                }
            ),
        )
    except Exception:
        # Persistence is authoritative; reconnecting clients can recover via history.
        logging.getLogger(__name__).exception('Chat realtime publish failed')


def ticket_digest(ticket: str) -> str:
    return hashlib.sha256(ticket.encode()).hexdigest()


def booking_chat_enabled(booking: Booking) -> bool:
    return booking.status in {'pending', 'accepted', 'confirmed', 'active'}


def now_utc() -> datetime:
    return datetime.now(UTC)
