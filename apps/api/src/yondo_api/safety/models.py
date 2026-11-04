from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.core.time import utc_now
from yondo_api.db.base import Base, TimestampMixin


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


class DisputeStatus(StrEnum):
    OPEN = 'open'
    UNDER_REVIEW = 'under_review'
    RESOLVED = 'resolved'


class Dispute(TimestampMixin, Base):
    """TZ §23 Dispute Center: booking issue with evidence, decided by an administrator."""

    __tablename__ = 'disputes'
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'under_review', 'resolved')", name='ck_disputes_status'
        ),
        CheckConstraint('refund_minor IS NULL OR refund_minor >= 0', name='ck_disputes_refund'),
        CheckConstraint('payout_minor IS NULL OR payout_minor >= 0', name='ck_disputes_payout'),
        Index('ix_disputes_status', 'status'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id'), unique=True)
    opened_by: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    category: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default=DisputeStatus.OPEN)
    previous_booking_status: Mapped[str] = mapped_column(String(16))
    booking_outcome: Mapped[str | None] = mapped_column(String(16))
    refund_minor: Mapped[int | None] = mapped_column(BigInteger)
    payout_minor: Mapped[int | None] = mapped_column(BigInteger)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DisputeEvidence(Base):
    __tablename__ = 'dispute_evidence'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dispute_id: Mapped[UUID] = mapped_column(
        ForeignKey('disputes.id', ondelete='CASCADE'), index=True
    )
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    kind: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(Text, default='')
    storage_key: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
