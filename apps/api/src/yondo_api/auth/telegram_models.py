"""Telegram bot login: phone <-> Telegram chat links and single-use link challenges."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class LinkChallengeStatus(StrEnum):
    PENDING = 'pending'  # shown to the browser as "awaiting_contact"
    LINKED = 'linked'  # contact verified by the bot; code not (yet) sent
    OTP_SENT = 'otp_sent'
    FAILED = 'failed'
    EXPIRED = 'expired'  # computed for pending rows past expires_at; stored by cleanup


class TelegramLink(TimestampMixin, Base):
    """Verified mapping: one phone <-> one Telegram user (private chat with the bot)."""

    __tablename__ = 'telegram_links'
    phone_number: Mapped[str] = mapped_column(String(16), primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    # Private chats: chat id == user id, stored separately as Telegram returns it.
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TelegramLinkChallenge(TimestampMixin, Base):
    __tablename__ = 'telegram_link_challenges'
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'linked', 'otp_sent', 'failed', 'expired')",
            name='ck_telegram_link_challenge_status',
        ),
        Index('ix_telegram_link_challenges_phone_created', 'phone_number', 'created_at'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    # Only SHA-256 hashes are stored: the start payload (in the deep link) and the
    # browser poll secret (returned once to the browser that started the flow).
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    poll_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    phone_number: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default=LinkChallengeStatus.PENDING)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
