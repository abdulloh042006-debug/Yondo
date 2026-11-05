from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class ChatMessage(TimestampMixin, Base):
    __tablename__ = 'chat_messages'
    __table_args__ = (
        CheckConstraint(
            "kind IN ('text', 'meeting_point', 'booking_details', 'system')",
            name='ck_chat_message_kind',
        ),
        CheckConstraint(
            "(kind = 'system' AND sender_id IS NULL AND system_code IS NOT NULL) OR "
            "(kind != 'system' AND sender_id IS NOT NULL AND system_code IS NULL)",
            name='ck_chat_message_sender',
        ),
        CheckConstraint(
            "(kind = 'booking_details' AND payload IS NOT NULL) OR "
            "(kind != 'booking_details' AND body IS NOT NULL)",
            name='ck_chat_message_content',
        ),
        Index('ix_chat_messages_booking_created', 'booking_id', 'created_at', 'id'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id', ondelete='RESTRICT'))
    sender_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    kind: Mapped[str] = mapped_column(String(24))
    body: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSON)
    system_code: Mapped[str | None] = mapped_column(String(64))


class ChatReadCursor(TimestampMixin, Base):
    __tablename__ = 'chat_read_cursors'
    __table_args__ = (UniqueConstraint('booking_id', 'user_id', name='uq_chat_read_cursor'),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id', ondelete='CASCADE'))
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ChatAccessTicket(TimestampMixin, Base):
    __tablename__ = 'chat_access_tickets'
    __table_args__ = (UniqueConstraint('token_hash', name='uq_chat_ticket_hash'),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id', ondelete='CASCADE'))
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
