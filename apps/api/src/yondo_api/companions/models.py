from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    column,
    func,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from yondo_api.db.base import Base, TimestampMixin


class ApplicationStatus(StrEnum):
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    WITHDRAWN = 'withdrawn'


class ContentStatus(StrEnum):
    DRAFT = 'draft'
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class CompanionApplication(TimestampMixin, Base):
    __tablename__ = 'companion_applications'
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'rejected', 'withdrawn')",
            name='ck_companion_application_status',
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(16), default=ApplicationStatus.DRAFT)
    statement: Mapped[str] = mapped_column(Text, default='')
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    review_note: Mapped[str | None] = mapped_column(Text)


class CompanionProfile(TimestampMixin, Base):
    __tablename__ = 'companion_profiles'
    __table_args__ = (
        CheckConstraint(
            "content_status IN ('draft', 'pending', 'approved', 'rejected')",
            name='ck_companion_profile_content_status',
        ),
        CheckConstraint(
            "NOT activation_requested OR content_status = 'approved'",
            name='ck_companion_profile_activation_content',
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey('companion_applications.id', ondelete='CASCADE'),
        unique=True,
    )
    display_name: Mapped[str] = mapped_column(String(128))
    bio: Mapped[str] = mapped_column(Text, default='')
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    content_status: Mapped[str] = mapped_column(String(16), default=ContentStatus.DRAFT)
    activation_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id'))
    review_note: Mapped[str | None] = mapped_column(Text)


class CompanionService(TimestampMixin, Base):
    __tablename__ = 'companion_services'
    __table_args__ = (
        UniqueConstraint('profile_id', 'service_code', name='uq_companion_service_code'),
        CheckConstraint('price_minor >= 0', name='ck_companion_service_price'),
        CheckConstraint('unit_minutes > 0', name='ck_companion_service_unit'),
        CheckConstraint('length(currency) = 3', name='ck_companion_service_currency'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey('companion_profiles.id', ondelete='CASCADE'),
        index=True,
    )
    service_code: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default='')
    price_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3))
    unit_minutes: Mapped[int] = mapped_column(Integer)


class CompanionPhoto(TimestampMixin, Base):
    __tablename__ = 'companion_photos'
    __table_args__ = (
        UniqueConstraint('profile_id', 'position', name='uq_companion_photo_position'),
        CheckConstraint('position IS NULL OR position >= 0', name='ck_companion_photo_position'),
        CheckConstraint(
            'size_bytes > 0 AND width > 0 AND height > 0', name='ck_companion_photo_dimensions'
        ),
        CheckConstraint(
            '(deleted_at IS NULL AND position IS NOT NULL) OR '
            '(deleted_at IS NOT NULL AND position IS NULL)',
            name='ck_companion_photo_deleted_position',
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey('companion_profiles.id', ondelete='CASCADE'),
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    content_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    position: Mapped[int | None] = mapped_column(Integer)
    caption: Mapped[str] = mapped_column(String(512), default='')
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CompanionAvailability(TimestampMixin, Base):
    __tablename__ = 'companion_availability'
    __table_args__ = (
        CheckConstraint('ends_at > starts_at', name='ck_companion_availability_interval'),
        Index('ix_companion_availability_profile_start', 'profile_id', 'starts_at'),
        ExcludeConstraint(
            ('profile_id', '='),
            (
                func.tstzrange(
                    # Half-open ranges permit adjacent windows.
                    column('starts_at'),
                    column('ends_at'),
                    '[)',
                ),
                '&&',
            ),
            name='ex_companion_availability_overlap',
            using='gist',
        ).ddl_if(dialect='postgresql'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey('companion_profiles.id', ondelete='CASCADE')
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64))
