from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base


class UserBlock(Base):
    """TZ §25: a block hides profiles, prevents new chat and prevents new bookings."""

    __tablename__ = 'user_blocks'
    __table_args__ = (CheckConstraint('blocker_id <> blocked_id', name='ck_user_blocks_self'),)

    blocker_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), primary_key=True
    )
    blocked_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
