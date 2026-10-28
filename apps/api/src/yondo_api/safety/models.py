from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class UserBlock(TimestampMixin, Base):
    __tablename__ = 'user_blocks'
    __table_args__ = (
        UniqueConstraint('blocker_id', 'blocked_id', name='uq_user_block_pair'),
        CheckConstraint('blocker_id != blocked_id', name='ck_user_block_not_self'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    blocker_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    blocked_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))


class SafetyReport(TimestampMixin, Base):
    __tablename__ = 'safety_reports'
    __table_args__ = (
        CheckConstraint(
            "category IN ('harassment', 'inappropriate_request', 'fake_profile', "
            "'fraud', 'unsafe_behavior', 'no_show', 'payment_issue', 'other')",
            name='ck_safety_report_category',
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    reporter_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    reported_user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    booking_id: Mapped[UUID | None] = mapped_column(ForeignKey('bookings.id', ondelete='RESTRICT'))
    category: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default='open')


class TrustedContact(TimestampMixin, Base):
    __tablename__ = 'trusted_contacts'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    name: Mapped[str] = mapped_column(String(128))
    phone_number: Mapped[str] = mapped_column(String(32))


class SafetyAlert(TimestampMixin, Base):
    __tablename__ = 'safety_alerts'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id', ondelete='RESTRICT'))
    creator_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))



class SafetyAcknowledgement(TimestampMixin, Base):
    """One auditable manual acknowledgement for an incident, not a resolution."""

    __tablename__ = 'safety_acknowledgements'
    __table_args__ = (
        CheckConstraint(
            '(report_id IS NULL AND alert_id IS NOT NULL) OR '
            '(report_id IS NOT NULL AND alert_id IS NULL)',
            name='ck_safety_ack_single_subject',
        ),
        UniqueConstraint('report_id', name='uq_safety_ack_report'),
        UniqueConstraint('alert_id', name='uq_safety_ack_alert'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('safety_reports.id', ondelete='RESTRICT'), nullable=True
    )
    alert_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('safety_alerts.id', ondelete='RESTRICT'), nullable=True
    )
    admin_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    note: Mapped[str] = mapped_column(Text)
