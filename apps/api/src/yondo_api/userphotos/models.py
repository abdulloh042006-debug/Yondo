from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class UserPhoto(TimestampMixin, Base):
    """Account (customer) profile photo. Never public: see userphotos/router.py for access."""

    __tablename__ = 'user_photos'
    __table_args__ = (
        UniqueConstraint('user_id', 'position', name='uq_user_photo_position'),
        CheckConstraint('position IS NULL OR position >= 0', name='ck_user_photo_position'),
        CheckConstraint(
            'size_bytes > 0 AND width > 0 AND height > 0', name='ck_user_photo_dimensions'
        ),
        CheckConstraint(
            '(deleted_at IS NULL AND position IS NOT NULL) OR '
            '(deleted_at IS NOT NULL AND position IS NULL)',
            name='ck_user_photo_deleted_position',
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    content_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    position: Mapped[int | None] = mapped_column(Integer)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
