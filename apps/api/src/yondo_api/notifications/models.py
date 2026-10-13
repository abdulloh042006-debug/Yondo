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
            "'booking_cancelled','payment_confirmed','chat_message',"
            "'review_reminder','gift_order_created','gift_test_paid','gift_preparing',"
            "'gift_out_for_delivery','gift_delivered','gift_cancelled',"
            "'meeting_reminder_24h','meeting_reminder_1h')",
            name='ck_user_notification_kind',
        ),
        UniqueConstraint('recipient_id', 'source_key', name='uq_notice_recipient_source'),
        CheckConstraint(
            '(booking_id IS NOT NULL AND gift_order_id IS NULL) OR '
            '(booking_id IS NULL AND gift_order_id IS NOT NULL)',
            name='ck_notification_single_resource',
        ),
        Index('ix_user_notifications_recipient_created', 'recipient_id', 'created_at'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    booking_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('bookings.id', ondelete='RESTRICT'), nullable=True
    )
    gift_order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('gift_test_orders.id', ondelete='RESTRICT'), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    source_key: Mapped[str] = mapped_column(String(160))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
