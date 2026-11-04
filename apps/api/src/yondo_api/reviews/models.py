from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class ReviewDirection(StrEnum):
    FOR_COMPANION = 'customer_to_companion'
    FOR_CUSTOMER = 'companion_to_customer'


# TZ §13 rating criteria per direction.
CRITERIA = {
    ReviewDirection.FOR_COMPANION: (
        'punctuality',
        'communication',
        'friendliness',
        'professionalism',
        'profile_accuracy',
    ),
    ReviewDirection.FOR_CUSTOMER: (
        'respect',
        'punctuality',
        'communication',
        'safety',
        'rule_compliance',
    ),
}


class Review(TimestampMixin, Base):
    __tablename__ = 'reviews'
    __table_args__ = (
        UniqueConstraint('booking_id', 'author_id', name='uq_reviews_booking_author'),
        CheckConstraint('rating BETWEEN 1 AND 5', name='ck_reviews_rating'),
        CheckConstraint(
            "direction IN ('customer_to_companion', 'companion_to_customer')",
            name='ck_reviews_direction',
        ),
        CheckConstraint("status IN ('published', 'hidden')", name='ck_reviews_status'),
        CheckConstraint('author_id <> subject_id', name='ck_reviews_distinct'),
        Index('ix_reviews_subject_direction', 'subject_id', 'direction', 'status'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id', ondelete='CASCADE'))
    author_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    subject_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    direction: Mapped[str] = mapped_column(String(32))
    rating: Mapped[int] = mapped_column(Integer)
    criteria: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    text: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(16), default='published')
    hidden_reason: Mapped[str | None] = mapped_column(Text)
    hidden_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
