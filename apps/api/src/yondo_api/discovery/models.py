from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base


class FavoriteCompanion(Base):
    __tablename__ = 'favorite_companions'

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), primary_key=True
    )
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey('companion_profiles.id', ondelete='CASCADE'), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
