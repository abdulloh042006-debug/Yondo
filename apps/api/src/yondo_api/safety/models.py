from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    func,
)
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


class VerificationStatus(StrEnum):
    DRAFT = 'draft'
    PENDING = 'pending'
    VERIFIED = 'verified'
    REJECTED = 'rejected'


class IdentityVerification(TimestampMixin, Base):
    """ID document + selfie review (TZ §4, §14). Images are private storage objects."""

    __tablename__ = 'identity_verifications'
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending', 'verified', 'rejected')",
            name='ck_identity_verifications_status',
        ),
        CheckConstraint(
            "document_type IN ('passport', 'id_card', 'driver_license')",
            name='ck_identity_verifications_document',
        ),
        Index('ix_identity_verifications_user_created', 'user_id', 'created_at'),
        Index('ix_identity_verifications_status', 'status'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    status: Mapped[str] = mapped_column(String(16), default=VerificationStatus.DRAFT)
    document_type: Mapped[str] = mapped_column(String(32))
    document_key: Mapped[str | None] = mapped_column(String(512))
    selfie_key: Mapped[str | None] = mapped_column(String(512))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    review_note: Mapped[str | None] = mapped_column(Text)


class ReportStatus(StrEnum):
    OPEN = 'open'
    IN_REVIEW = 'in_review'
    RESOLVED = 'resolved'
    DISMISSED = 'dismissed'


class Report(TimestampMixin, Base):
    __tablename__ = 'reports'
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_review', 'resolved', 'dismissed')", name='ck_reports_status'
        ),
        CheckConstraint('reporter_id <> reported_user_id', name='ck_reports_distinct'),
        Index('ix_reports_status_created', 'status', 'created_at'),
        Index('ix_reports_reported_user', 'reported_user_id'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    reporter_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    reported_user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    booking_id: Mapped[UUID | None] = mapped_column(ForeignKey('bookings.id'))
    category: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(16), default=ReportStatus.OPEN)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TrustedContact(TimestampMixin, Base):
    __tablename__ = 'trusted_contacts'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(128))
    phone_number: Mapped[str] = mapped_column(String(32))
    relationship: Mapped[str] = mapped_column(String(64), default='')


class BookingShare(Base):
    """Read-only link letting a trusted contact follow a meeting (TZ §17)."""

    __tablename__ = 'booking_shares'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        ForeignKey('bookings.id', ondelete='CASCADE'), index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    trusted_contact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('trusted_contacts.id', ondelete='SET NULL')
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SosStatus(StrEnum):
    OPEN = 'open'
    ACKNOWLEDGED = 'acknowledged'
    RESOLVED = 'resolved'


class SosAlert(TimestampMixin, Base):
    __tablename__ = 'sos_alerts'
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved')", name='ck_sos_alerts_status'
        ),
        Index('ix_sos_alerts_status_created', 'status', 'created_at'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id'))
    booking_id: Mapped[UUID | None] = mapped_column(ForeignKey('bookings.id'))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    message: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(16), default=SosStatus.OPEN)
    handled_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)


class AdminAuditLog(Base):
    """Every administrative mutation, including user moderation (TZ §39)."""

    __tablename__ = 'admin_audit_log'
    __table_args__ = (Index('ix_admin_audit_target', 'target_type', 'target_id', 'created_at'),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    admin_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[UUID] = mapped_column()
    reason: Mapped[str] = mapped_column(Text, default='')
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
