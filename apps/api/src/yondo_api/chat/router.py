from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking
from yondo_api.bookings.router import _participant
from yondo_api.chat.models import ChatAccessTicket, ChatMessage, ChatReadCursor
from yondo_api.chat.schemas import (
    ChatMessageResponse,
    ChatMessageWrite,
    ChatReadResult,
    ChatSocketTicket,
    ChatUnreadItem,
)
from yondo_api.chat.service import booking_chat_enabled, now_utc, publish, ticket_digest
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.companions.models import CompanionApplication, CompanionProfile

router = APIRouter(prefix='/chat', tags=['booking chat'])


async def _booking(session: Session, booking_id: UUID, user_id: UUID) -> Booking:
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    await _participant(session, booking, user_id)
    return booking


@router.get('/bookings/{booking_id}/messages', response_model=list[ChatMessageResponse])
async def list_messages(
    booking_id: UUID,
    principal: Principal,
    session: Session,
    before: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=50, ge=1, le=100),
):
    await _booking(session, booking_id, principal.user.id)
    query = select(ChatMessage).where(ChatMessage.booking_id == booking_id)
    if before:
        try:
            before_at = datetime.fromisoformat(before.replace('Z', '+00:00'))
        except ValueError as exc:
            raise ApplicationError('invalid_chat_cursor', 'Message cursor is invalid', 422) from exc
        if before_at.tzinfo is None or before_at.utcoffset() is None:
            raise ApplicationError(
                'invalid_chat_cursor', 'Message cursor must include timezone', 422
            )
        query = query.where(ChatMessage.created_at < before_at)
    query = query.order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(limit)
    messages = list(await session.scalars(query))
    return list(reversed(messages))


@router.post('/bookings/{booking_id}/messages', response_model=ChatMessageResponse, status_code=201)
async def send_message(
    booking_id: UUID,
    payload: ChatMessageWrite,
    request: Request,
    principal: Principal,
    session: Session,
):
    booking = await _booking(session, booking_id, principal.user.id)
    if not booking_chat_enabled(booking):
        raise ApplicationError('chat_closed', 'This booking chat is read-only', 409)
    from yondo_api.safety.service import blocked_between

    companion_id = await session.scalar(
        select(CompanionApplication.user_id)
        .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
        .where(CompanionProfile.id == booking.profile_id)
    )
    if await blocked_between(session, booking.customer_id, companion_id):
        raise ApplicationError('chat_blocked', 'Chat is unavailable', 403)
    message = ChatMessage(
        booking_id=booking.id,
        sender_id=principal.user.id,
        kind=payload.kind,
        body=payload.body,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    await publish(request, message)
    return message


@router.get('/bookings/{booking_id}/unread', response_model=ChatReadResult)
async def unread_count(booking_id: UUID, principal: Principal, session: Session):
    await _booking(session, booking_id, principal.user.id)
    cursor = await session.scalar(
        select(ChatReadCursor).where(
            ChatReadCursor.booking_id == booking_id,
            ChatReadCursor.user_id == principal.user.id,
        )
    )
    query = (
        select(func.count())
        .select_from(ChatMessage)
        .where(
            ChatMessage.booking_id == booking_id,
            ChatMessage.sender_id != principal.user.id,
        )
    )
    if cursor is not None:
        query = query.where(ChatMessage.created_at > cursor.last_read_at)
    count = await session.scalar(query)
    return ChatReadResult(booking_id=booking_id, unread_count=count or 0)


@router.get('/unread', response_model=list[ChatUnreadItem])
async def all_unread(principal: Principal, session: Session):
    companion_user_id = (
        select(CompanionApplication.user_id)
        .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
        .where(CompanionProfile.id == Booking.profile_id)
        .scalar_subquery()
    )
    bookings = list(
        await session.scalars(
            select(Booking).where(
                (Booking.customer_id == principal.user.id)
                | (companion_user_id == principal.user.id)
            )
        )
    )
    result = []
    for booking in bookings:
        try:
            await _participant(session, booking, principal.user.id)
        except ApplicationError:
            continue
        cursor = await session.scalar(
            select(ChatReadCursor).where(
                ChatReadCursor.booking_id == booking.id,
                ChatReadCursor.user_id == principal.user.id,
            )
        )
        query = (
            select(func.count())
            .select_from(ChatMessage)
            .where(
                ChatMessage.booking_id == booking.id,
                ChatMessage.sender_id != principal.user.id,
            )
        )
        if cursor is not None:
            query = query.where(ChatMessage.created_at > cursor.last_read_at)
        count = await session.scalar(query)
        if count:
            result.append(ChatUnreadItem(booking_id=booking.id, unread_count=count))
    return result


@router.post('/bookings/{booking_id}/read', response_model=ChatReadResult)
async def mark_read(booking_id: UUID, principal: Principal, session: Session):
    await _booking(session, booking_id, principal.user.id)
    now = now_utc()
    cursor = await session.scalar(
        select(ChatReadCursor).where(
            ChatReadCursor.booking_id == booking_id,
            ChatReadCursor.user_id == principal.user.id,
        )
    )
    if cursor is None:
        cursor = ChatReadCursor(booking_id=booking_id, user_id=principal.user.id, last_read_at=now)
        session.add(cursor)
    else:
        cursor.last_read_at = now
    await session.commit()
    return ChatReadResult(booking_id=booking_id, unread_count=0)


@router.post('/bookings/{booking_id}/socket-ticket', response_model=ChatSocketTicket)
async def create_socket_ticket(booking_id: UUID, principal: Principal, session: Session):
    await _booking(session, booking_id, principal.user.id)
    token = secrets.token_urlsafe(32)
    ticket = ChatAccessTicket(
        booking_id=booking_id,
        user_id=principal.user.id,
        token_hash=ticket_digest(token),
        expires_at=now_utc() + timedelta(seconds=90),
    )
    session.add(ticket)
    await session.commit()
    return ChatSocketTicket(ticket=token)


@router.websocket('/ws/{booking_id}')
async def chat_socket(websocket: WebSocket, booking_id: UUID, ticket: str = Query(default='')):
    factory = websocket.app.state.db_session_factory
    async with factory() as session:
        row = await session.scalar(
            select(ChatAccessTicket)
            .where(
                ChatAccessTicket.booking_id == booking_id,
                ChatAccessTicket.token_hash == ticket_digest(ticket),
                ChatAccessTicket.consumed_at.is_(None),
                ChatAccessTicket.expires_at > now_utc(),
            )
            .with_for_update()
        )
        if row is None:
            await websocket.close(code=4401)
            return
        booking = await session.get(Booking, booking_id)
        if booking is None:
            await websocket.close(code=4403)
            return
        try:
            await _participant(session, booking, row.user_id)
        except ApplicationError:
            await websocket.close(code=4403)
            return
        row.consumed_at = now_utc()
        await session.commit()
    await websocket.accept()
    channel = f'yondo:chat:{booking_id}'
    pubsub = websocket.app.state.redis.pubsub()
    try:
        await pubsub.subscribe(channel)
        socket_task = asyncio.create_task(websocket.receive_text())
        redis_task = asyncio.create_task(
            pubsub.get_message(ignore_subscribe_messages=True, timeout=10)
        )
        while True:
            done, _ = await asyncio.wait(
                {socket_task, redis_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if socket_task in done:
                try:
                    data = socket_task.result()
                except WebSocketDisconnect:
                    break
                if data == 'ping':
                    await websocket.send_text('pong')
                socket_task = asyncio.create_task(websocket.receive_text())
            if redis_task in done:
                item = redis_task.result()
                if item and item.get('type') == 'message':
                    await websocket.send_text(item['data'])
                redis_task = asyncio.create_task(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=10)
                )
    except WebSocketDisconnect:
        pass
    finally:
        for task in (locals().get('socket_task'), locals().get('redis_task')):
            if task is not None and not task.done():
                task.cancel()
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        try:
            await websocket.close()
        except RuntimeError:
            pass
