from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class UserNotification(TimestampMixin, Base):
    __tablename__ = 'user_notifications'
    __table_args__ = (
        CheckConstraint(
            "kind IN ('booking_requested','booking_accepted','booking_declined',"
            "'booking_cancelled','payment_confirmed','chat_message')",
            name='ck_user_notification_kind',
        ),
        UniqueConstraint('recipient_id', 'source_key', name='uq_notice_recipient_source'),
        Index('ix_user_notifications_recipient_created', 'recipient_id', 'created_at'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id', ondelete='RESTRICT'))
    kind: Mapped[str] = mapped_column(String(40))
    source_key: Mapped[str] = mapped_column(String(160))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
