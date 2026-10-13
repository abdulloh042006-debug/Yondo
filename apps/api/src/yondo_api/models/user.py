from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from yondo_api.db.base import Base, TimestampMixin


class UserRoleType(StrEnum):
    CUSTOMER = 'customer'
    COMPANION = 'companion'
    VENDOR = 'vendor'
    ADMIN = 'admin'


class AccountStatus(StrEnum):
    ACTIVE = 'active'
    VERIFICATION_PENDING = 'verification_pending'
    RESTRICTED = 'restricted'
    SUSPENDED = 'suspended'
    BANNED = 'banned'


class User(TimestampMixin, Base):
    __tablename__ = 'users'
    __table_args__ = (
        CheckConstraint(
            '''account_status IN ('active', 'verification_pending', 'restricted',
            'suspended', 'banned')''',
            name='ck_users_account_status',
        ),
        Index('ix_users_account_status', 'account_status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    age: Mapped[int | None] = mapped_column()
    gender: Mapped[str | None] = mapped_column(String(64))
    city: Mapped[str | None] = mapped_column(String(128))
    account_status: Mapped[AccountStatus] = mapped_column(
        Enum(
            AccountStatus,
            native_enum=False,
            length=32,
            values_callable=lambda values: [value.value for value in values],
        ),
        default=AccountStatus.VERIFICATION_PENDING,
        nullable=False,
    )
    roles: Mapped[list[UserRole]] = relationship(
        back_populates='user', cascade='all, delete-orphan', lazy='selectin'
    )


class UserRole(Base):
    __tablename__ = 'user_roles'
    __table_args__ = (
        CheckConstraint(
            '''role IN ('customer', 'companion', 'vendor', 'admin')''',
            name='ck_user_roles_role',
        ),
        Index('ix_user_roles_role', 'role'),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), primary_key=True
    )
    role: Mapped[UserRoleType] = mapped_column(
        Enum(
            UserRoleType,
            native_enum=False,
            length=32,
            values_callable=lambda values: [value.value for value in values],
        ),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user: Mapped[User] = relationship(back_populates='roles')
