from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class BookingReview(TimestampMixin, Base):
    __tablename__ = 'booking_reviews'
    __table_args__ = (
        UniqueConstraint('booking_id', 'reviewer_id', name='uq_review_once_per_booking'),
        CheckConstraint('stars BETWEEN 1 AND 5', name='ck_review_stars'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id', ondelete='RESTRICT'))
    reviewer_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    reviewee_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    stars: Mapped[int] = mapped_column()
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    comment: Mapped[str] = mapped_column(Text, default='')
