from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import or_, select

from yondo_api.bookings.models import Booking
from yondo_api.bookings.service import participant_booking, role_of
from yondo_api.chat import service
from yondo_api.chat.models import ChatMessage, MessageKind
from yondo_api.chat.schemas import (
    Conversation,
    MeetingPointMessage,
    MessageResponse,
    OutgoingMessage,
    UnreadTotal,
)
from yondo_api.companions.dependencies import object_storage
from yondo_api.core.db import commit
from yondo_api.core.deps import CurrentUser, Session
from yondo_api.core.images import IMAGE_REQUEST_BODY, discard_image, read_image, store_image
from yondo_api.core.time import utc_now

router = APIRouter(prefix='/chat', tags=['chat'])


@router.get('/conversations', response_model=list[Conversation])
async def conversations(request: Request, user: CurrentUser, session: Session):
    bookings = list(
        await session.scalars(
            select(Booking)
            .where(or_(Booking.customer_id == user.id, Booking.companion_id == user.id))
            .order_by(Booking.starts_at.desc())
            .limit(100)
        )
    )
    ids = [booking.id for booking in bookings]
    unread = await service.unread_counts(session, user.id, ids)
    latest = await service.last_messages(session, ids)
    from yondo_api.bookings.service import _profile_names
    from yondo_api.models.user import User

    names = await _profile_names(session, {booking.profile_id for booking in bookings})
    customers = (
        {
            item.id: item.display_name
            for item in await session.scalars(
                select(User).where(User.id.in_({b.customer_id for b in bookings}))
            )
        }
        if bookings
        else {}
    )
    result = []
    for booking in bookings:
        is_customer = role_of(booking, user) == 'customer'
        message = latest.get(booking.id)
        result.append(
            Conversation(
                booking_id=booking.id,
                booking_status=booking.status,
                counterpart_id=booking.companion_id if is_customer else booking.customer_id,
                counterpart_name=(
                    names.get(booking.profile_id)
                    if is_customer
                    else customers.get(booking.customer_id)
                ),
                starts_at=booking.starts_at,
                last_message=await service.message_view(request, message) if message else None,
                unread=unread.get(booking.id, 0),
                can_send=booking.status in service.SENDABLE_STATUSES,
            )
        )
    result.sort(
        key=lambda c: c.last_message.created_at if c.last_message else c.starts_at, reverse=True
    )
    return result


@router.get('/unread', response_model=UnreadTotal)
async def unread_total(user: CurrentUser, session: Session):
    ids = list(
        await session.scalars(
            select(Booking.id).where(
                or_(Booking.customer_id == user.id, Booking.companion_id == user.id)
            )
        )
    )
    return UnreadTotal(unread=sum((await service.unread_counts(session, user.id, ids)).values()))


@router.get('/bookings/{booking_id}/messages', response_model=list[MessageResponse])
async def messages(
    booking_id: UUID,
    request: Request,
    user: CurrentUser,
    session: Session,
    before: datetime | None = None,
    after: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """Messages in chronological order. ``before`` pages back; ``after`` polls for new ones."""
    await participant_booking(session, booking_id, user)
    query = select(ChatMessage).where(ChatMessage.booking_id == booking_id)
    if after is not None:
        rows = list(
            await session.scalars(
                query.where(ChatMessage.created_at > after)
                .order_by(ChatMessage.created_at)
                .limit(limit)
            )
        )
    else:
        if before is not None:
            query = query.where(ChatMessage.created_at < before)
        rows = list(
            await session.scalars(query.order_by(ChatMessage.created_at.desc()).limit(limit))
        )
        rows.reverse()
    return [await service.message_view(request, row) for row in rows]


async def _send(session, request, user, booking_id, kind, body, payload=None):
    booking, _ = await participant_booking(session, booking_id, user, lock=True)
    await service.ensure_can_send(session, booking, user.id)
    message = await service.add_message(session, booking, user.id, kind, body, payload)
    await commit(session)
    return await service.message_view(request, message)


@router.post('/bookings/{booking_id}/messages', response_model=MessageResponse, status_code=201)
async def send_message(
    booking_id: UUID,
    payload: OutgoingMessage,
    request: Request,
    user: CurrentUser,
    session: Session,
):
    if isinstance(payload, MeetingPointMessage):
        return await _send(
            session,
            request,
            user,
            booking_id,
            MessageKind.MEETING_POINT,
            payload.body,
            payload.meeting_point.model_dump(),
        )
    return await _send(session, request, user, booking_id, MessageKind.TEXT, payload.body)


@router.post(
    '/bookings/{booking_id}/images',
    response_model=MessageResponse,
    status_code=201,
    openapi_extra=IMAGE_REQUEST_BODY,
)
async def send_image(booking_id: UUID, request: Request, user: CurrentUser, session: Session):
    """Raw JPEG/PNG/WebP upload; metadata is stripped and the image re-encoded."""
    booking, _ = await participant_booking(session, booking_id, user)
    await service.ensure_can_send(session, booking, user.id)
    object_storage(request)
    content, width, height = await read_image(request)
    key = f'chat/{booking.id}/{uuid4()}.jpg'
    await store_image(request, key, content)
    try:
        booking, _ = await participant_booking(session, booking_id, user, lock=True)
        await service.ensure_can_send(session, booking, user.id)
        message = await service.add_message(
            session,
            booking,
            user.id,
            MessageKind.IMAGE,
            '',
            {'storage_key': key, 'width': width, 'height': height},
        )
        await commit(session)
    except BaseException:
        await discard_image(request, key)
        raise
    return await service.message_view(request, message)


@router.post('/bookings/{booking_id}/read', status_code=204)
async def mark_read(booking_id: UUID, user: CurrentUser, session: Session):
    await participant_booking(session, booking_id, user)
    await service.set_read(session, booking_id, user.id, utc_now())
    await commit(session)
    return Response(status_code=204)
