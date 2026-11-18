"""Social sign-in: external identities (Telegram, Google; Apple-ready) and flow challenges."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin

PROVIDERS = ('telegram', 'google', 'apple')


class ExternalIdentity(TimestampMixin, Base):
    """One account at an identity provider (its stable ``sub``) linked to one Yondo user."""

    __tablename__ = 'external_identities'
    __table_args__ = (
        CheckConstraint(
            "provider IN ('telegram', 'google', 'apple')", name='ck_external_identity_provider'
        ),
        UniqueConstraint('provider', 'provider_subject', name='uq_external_identity_subject'),
        UniqueConstraint('user_id', 'provider', name='uq_external_identity_user_provider'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(16))
    provider_subject: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)


class SocialLoginChallenge(TimestampMixin, Base):
    """Single-use state for one social flow.

    kind 'authorize': an OIDC redirect (state, nonce, PKCE verifier; ``user_id`` set when a
    signed-in user links a provider). kind 'nonce': a nonce for the official Telegram JS library,
    which hands the ID token straight to the browser (``token_hash`` = hash of the nonce).
    kind 'signup': a verified provider identity waiting for a phone code (accounts are
    phone-anchored). Only SHA-256 hashes of the browser-held values (state, flow token, nonce of
    the JS flow, signup token) are stored.
    """

    __tablename__ = 'social_login_challenges'
    __table_args__ = (
        CheckConstraint(
            "provider IN ('telegram', 'google', 'apple')", name='ck_social_challenge_provider'
        ),
        CheckConstraint(
            "kind IN ('authorize', 'nonce', 'signup')", name='ck_social_challenge_kind'
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(16))
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True)
    binding_hash: Mapped[bytes | None] = mapped_column(LargeBinary(32))
    nonce: Mapped[str | None] = mapped_column(String(64))
    code_verifier: Mapped[str | None] = mapped_column(String(128))
    redirect_uri: Mapped[str | None] = mapped_column(String(512))
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    provider_subject: Mapped[str | None] = mapped_column(String(255))
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
