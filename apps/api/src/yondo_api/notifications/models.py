from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.core.time import utc_now
from yondo_api.db.base import Base, TimestampMixin


class PushStatus(StrEnum):
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'
    SKIPPED = 'skipped'


class Notification(TimestampMixin, Base):
    __tablename__ = 'notifications'
    __table_args__ = (
        CheckConstraint(
            "push_status IN ('pending', 'sent', 'failed', 'skipped')",
            name='ck_notifications_push_status',
        ),
        Index('ix_notifications_user_created', 'user_id', 'created_at'),
        Index('ix_notifications_push_status', 'push_status'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    kind: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default='')
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    push_status: Mapped[str] = mapped_column(String(16), default=PushStatus.PENDING)
    push_attempts: Mapped[int] = mapped_column(Integer, default=0)


class NotificationKey(Base):
    """Idempotency keys for scheduled notices (reminders are sent at most once)."""

    __tablename__ = 'notification_keys'

    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DeviceToken(TimestampMixin, Base):
    __tablename__ = 'device_tokens'
    __table_args__ = (
        CheckConstraint("platform IN ('android', 'ios', 'web')", name='ck_device_tokens_platform'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    token: Mapped[str] = mapped_column(String(512), unique=True)
    platform: Mapped[str] = mapped_column(String(16))
