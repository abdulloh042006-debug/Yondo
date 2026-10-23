from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class AccountDeletionRequest(TimestampMixin, Base):
    """A user's request to delete their account; kept after completion as the record of erasure."""

    __tablename__ = 'account_deletion_requests'
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'cancelled', 'completed')",
            name='ck_account_deletion_status',
        ),
        # At most one open request per user (partial unique index on both databases).
        Index(
            'uq_account_deletion_pending',
            'user_id',
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    status: Mapped[str] = mapped_column(String(16), default='pending')
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserConsent(Base):
    """Evidence that a user accepted a specific version of a legal document."""

    __tablename__ = 'user_consents'
    __table_args__ = (
        CheckConstraint("document IN ('terms', 'privacy')", name='ck_user_consent_document'),
        UniqueConstraint('user_id', 'document', 'version', name='uq_user_consent_version'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    document: Mapped[str] = mapped_column(String(16))
    version: Mapped[str] = mapped_column(String(32))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SupportRequest(TimestampMixin, Base):
    """In-app support request (the support channel chosen by the owner; no e-mail or phone)."""

    __tablename__ = 'support_requests'
    __table_args__ = (
        CheckConstraint(
            "category IN ('account', 'booking', 'payment', 'safety', 'technical', 'other')",
            name='ck_support_request_category',
        ),
        CheckConstraint(
            "status IN ('open', 'answered', 'closed')", name='ck_support_request_status'
        ),
        Index('ix_support_requests_status', 'status'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True)
    category: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default='open')
    reply: Mapped[str | None] = mapped_column(Text)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replied_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
