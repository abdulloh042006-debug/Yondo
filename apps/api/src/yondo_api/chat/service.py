from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.chat.models import ChatMessage, ChatReadState, MessageKind
from yondo_api.chat.schemas import MessageResponse
from yondo_api.core.time import as_utc, utc_now
from yondo_api.realtime.broker import queue_event

SENDABLE_STATUSES = {
    BookingStatus.PENDING,
    BookingStatus.ACCEPTED,
    BookingStatus.CONFIRMED,
    BookingStatus.ACTIVE,
}
IMAGE_URL_SECONDS = 3600

# Uzbek system texts; clients may localize from the event code in ``payload['event']``.
SYSTEM_TEXTS = {
    'requested': "Bron so'rovi yuborildi.",
    'accepted': 'Companion bronni qabul qildi.',
    'payment_confirmed': "To'lov qabul qilindi. Bron tasdiqlandi.",
    'declined': "Bron so'rovi rad etildi.",
    'customer_cancelled': 'Mijoz bronni bekor qildi.',
    'companion_cancelled': 'Companion bronni bekor qildi.',
    'request_expired': "So'rov muddati tugadi.",
    'payment_expired': "To'lov muddati tugadi.",
    'admin_cancelled': 'Bron administrator tomonidan bekor qilindi.',
    'checked_in': 'Uchrashuv joyiga yetib keldi.',
    'started': 'Uchrashuv boshlandi.',
    'ended': 'Uchrashuv yakunlandi.',
    'no_show_reported': 'Kelmaganlik (no-show) haqida xabar berildi.',
    'dispute_opened': 'Nizo ochildi. Administrator ko‘rib chiqadi.',
    'dispute_resolved': 'Nizo hal qilindi.',
}


def _publish(session: AsyncSession, booking: Booking, message: ChatMessage) -> None:
    event = {
        'type': 'chat_message',
        'message': {
            'id': str(message.id),
            'booking_id': str(booking.id),
            'sender_id': str(message.sender_id) if message.sender_id else None,
            'kind': message.kind,
            'body': message.body,
            'payload': message.payload,
            'created_at': as_utc(message.created_at).isoformat(),
        },
    }
    for party in (booking.customer_id, booking.companion_id):
        queue_event(session, party, event)


def post_system_message(
    session: AsyncSession, booking: Booking, event: str, data: dict[str, Any]
) -> ChatMessage:
    if event == 'requested':
        kind, body = MessageKind.BOOKING_DETAILS, SYSTEM_TEXTS['requested']
        payload = {
            'event': event,
            'service_code': booking.service_code,
            'starts_at': as_utc(booking.starts_at).isoformat(),
            'ends_at': as_utc(booking.ends_at).isoformat(),
            'meeting_place': booking.meeting_place_name,
            'total_minor': booking.total_minor,
            'currency': booking.currency,
        }
    else:
        kind, body = MessageKind.SYSTEM, SYSTEM_TEXTS.get(event, event)
        payload = {'event': event, **{key: str(value) for key, value in data.items()}}
    message = ChatMessage(
        id=uuid4(),
        booking_id=booking.id,
        sender_id=None,
        kind=kind,
        body=body,
        payload=payload,
        created_at=utc_now(),
    )
    session.add(message)
    _publish(session, booking, message)
    return message


async def ensure_can_send(session: AsyncSession, booking: Booking, sender_id: UUID) -> None:
    from yondo_api.safety.service import ensure_not_blocked

    if booking.status not in SENDABLE_STATUSES:
        raise ApplicationError('chat_closed', 'This conversation is closed', 409)
    await ensure_not_blocked(session, booking.customer_id, booking.companion_id)


async def add_message(
    session: AsyncSession,
    booking: Booking,
    sender_id: UUID,
    kind: MessageKind,
    body: str,
    payload: dict[str, Any] | None = None,
) -> ChatMessage:
    message = ChatMessage(
        id=uuid4(),
        booking_id=booking.id,
        sender_id=sender_id,
        kind=kind,
        body=body,
        payload=payload or {},
        created_at=utc_now(),
    )
    session.add(message)
    _publish(session, booking, message)
    await set_read(session, booking.id, sender_id, message.created_at)
    return message


async def set_read(session: AsyncSession, booking_id: UUID, user_id: UUID, when: datetime) -> None:
    state = await session.get(ChatReadState, (booking_id, user_id))
    if state is None:
        session.add(ChatReadState(booking_id=booking_id, user_id=user_id, last_read_at=when))
    elif as_utc(state.last_read_at) < as_utc(when):
        state.last_read_at = when


async def unread_counts(
    session: AsyncSession, user_id: UUID, booking_ids: list[UUID]
) -> dict[UUID, int]:
    if not booking_ids:
        return {}
    read_at = {
        state.booking_id: state.last_read_at
        for state in await session.scalars(
            select(ChatReadState).where(
                ChatReadState.user_id == user_id, ChatReadState.booking_id.in_(booking_ids)
            )
        )
    }
    counts: dict[UUID, int] = {}
    rows = await session.execute(
        select(ChatMessage.booking_id, ChatMessage.created_at).where(
            ChatMessage.booking_id.in_(booking_ids),
            (ChatMessage.sender_id.is_(None)) | (ChatMessage.sender_id != user_id),
        )
    )
    for booking_id, created_at in rows:
        last = read_at.get(booking_id)
        if last is None or as_utc(created_at) > as_utc(last):
            counts[booking_id] = counts.get(booking_id, 0) + 1
    return counts


async def message_view(request: Request, message: ChatMessage) -> MessageResponse:
    view = MessageResponse.model_validate(message)
    key = message.payload.get('storage_key') if message.kind == MessageKind.IMAGE else None
    storage = request.app.state.object_storage
    if key and storage is not None:
        try:
            view.image_url = await storage.create_download_url(key, IMAGE_URL_SECONDS)
        except Exception:
            view.image_url = None
    view.payload = {k: v for k, v in message.payload.items() if k != 'storage_key'}
    return view


async def last_messages(session: AsyncSession, booking_ids: list[UUID]) -> dict[UUID, ChatMessage]:
    if not booking_ids:
        return {}
    latest = (
        select(ChatMessage.booking_id, func.max(ChatMessage.created_at).label('latest'))
        .where(ChatMessage.booking_id.in_(booking_ids))
        .group_by(ChatMessage.booking_id)
        .subquery()
    )
    rows = await session.scalars(
        select(ChatMessage).join(
            latest,
            (ChatMessage.booking_id == latest.c.booking_id)
            & (ChatMessage.created_at == latest.c.latest),
        )
    )
    return {message.booking_id: message for message in rows}
