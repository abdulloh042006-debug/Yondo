from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class BetaEnrollment(TimestampMixin, Base):
    __tablename__ = 'beta_enrollments'
    __table_args__ = (UniqueConstraint('user_id', name='uq_beta_enrollment_user'),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    invited_by_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    enabled: Mapped[bool] = mapped_column(default=False, server_default='false')

class BetaFeedback(TimestampMixin, Base):
    __tablename__ = 'beta_feedback'
    __table_args__ = (
        CheckConstraint('rating BETWEEN 1 AND 5', name='ck_beta_feedback_rating'),
        CheckConstraint(
            "category IN ('bug','usability','safety','pricing','other')",
            name='ck_beta_feedback_category',
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    category: Mapped[str] = mapped_column(String(32))
    rating: Mapped[int] = mapped_column()
    description: Mapped[str] = mapped_column(Text)
