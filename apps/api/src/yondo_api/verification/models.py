from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class VerificationStatus(StrEnum):
    DRAFT = 'draft'
    PENDING = 'pending'
    VERIFIED = 'verified'
    REJECTED = 'rejected'


DOCUMENT_TYPES = ('passport', 'id_card', 'driver_license')


class IdentityVerification(TimestampMixin, Base):
    """One submission. Images are private storage objects, visible only to administrators."""

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
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'))
    review_note: Mapped[str | None] = mapped_column(Text)
