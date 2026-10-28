from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class CompanionFavorite(TimestampMixin, Base):
    __tablename__ = 'companion_favorites'
    __table_args__ = (UniqueConstraint('customer_id', 'profile_id', name='uq_companion_favorite'),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), index=True
    )
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey('companion_profiles.id', ondelete='CASCADE'), index=True
    )
