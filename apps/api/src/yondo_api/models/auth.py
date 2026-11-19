from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class OtpChallenge(TimestampMixin, Base):
    __tablename__ = 'otp_challenges'

    phone_number: Mapped[str] = mapped_column(String(16), primary_key=True)
    code_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OtpIssue(Base):
    """One row per code sent: the per-phone hourly and daily limits count these.

    Rows older than a day are pruned by the hourly job (`python -m yondo_api.jobs`) and on the
    phone's next request.
    """

    __tablename__ = 'otp_issues'
    __table_args__ = (Index('ix_otp_issues_phone_issued', 'phone_number', 'issued_at'),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(16), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthSession(TimestampMixin, Base):
    __tablename__ = 'auth_sessions'

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True
    )
    access_token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True, nullable=False)
    refresh_token_hash: Mapped[bytes] = mapped_column(
        LargeBinary(32), unique=True, nullable=False
    )
    access_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refresh_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # How the session was created: 'otp', 'password' (NULL for sessions older than this column).
    via: Mapped[str | None] = mapped_column(String(16))


class PasswordLoginGuard(TimestampMixin, Base):
    """Failed password attempts per subject: 'user:<id>', or 'login:<hash>' for unknown logins."""

    __tablename__ = 'password_login_guards'

    subject: Mapped[str] = mapped_column(String(64), primary_key=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
