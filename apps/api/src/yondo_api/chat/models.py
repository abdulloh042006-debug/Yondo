from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.core.time import utc_now
from yondo_api.db.base import Base


class MessageKind(StrEnum):
    TEXT = 'text'
    IMAGE = 'image'
    MEETING_POINT = 'meeting_point'
    BOOKING_DETAILS = 'booking_details'
    SYSTEM = 'system'


class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    __table_args__ = (
        CheckConstraint(
            "kind IN ('text', 'image', 'meeting_point', 'booking_details', 'system')",
            name='ck_chat_messages_kind',
        ),
        CheckConstraint(
            "(sender_id IS NULL) = (kind IN ('system', 'booking_details'))",
            name='ck_chat_messages_sender',
        ),
        Index('ix_chat_messages_booking_created', 'booking_id', 'created_at'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id', ondelete='CASCADE'))
    sender_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    kind: Mapped[str] = mapped_column(String(32))
    body: Mapped[str] = mapped_column(Text, default='')
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ChatReadState(Base):
    __tablename__ = 'chat_read_states'

    booking_id: Mapped[UUID] = mapped_column(
        ForeignKey('bookings.id', ondelete='CASCADE'), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), primary_key=True
    )
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
