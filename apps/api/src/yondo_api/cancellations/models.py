"""Cancellation tracking, review cases, booking restrictions and their audit trail.

Design and placeholder policy values: docs/cancellation-policy.md. No money is stored or moved here.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
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

EVENT_KINDS = ('cancelled', 'declined', 'no_show', 'expired')
EVENT_PARTIES = ('customer', 'companion', 'admin', 'system')
SUBJECT_ROLES = ('customer', 'companion')
EXCUSE_STATES = ('none', 'claimed', 'granted', 'rejected')
REVIEW_STATES = ('none', 'open', 'reviewed')
CASE_TRIGGERS = ('cancellations', 'last_minute', 'no_shows', 'emergency_claims')


def _in(column: str, values: tuple[str, ...]) -> str:
    return f'{column} IN (' + ', '.join(f"'{value}'" for value in values) + ')'


class CancellationEvent(TimestampMixin, Base):
    """One recorded cancellation, decline, no-show or system expiry of a booking."""

    __tablename__ = 'cancellation_events'
    __table_args__ = (
        CheckConstraint(_in('kind', EVENT_KINDS), name='ck_cancellation_event_kind'),
        CheckConstraint(_in('party', EVENT_PARTIES), name='ck_cancellation_event_party'),
        CheckConstraint(
            'subject_role IS NULL OR ' + _in('subject_role', SUBJECT_ROLES),
            name='ck_cancellation_event_subject_role',
        ),
        CheckConstraint(_in('excuse_state', EXCUSE_STATES), name='ck_cancellation_event_excuse'),
        CheckConstraint(_in('review_state', REVIEW_STATES), name='ck_cancellation_event_review'),
        UniqueConstraint(
            'booking_id', 'kind', 'subject_user_id', name='uq_cancellation_event_once'
        ),
        Index('ix_cancellation_events_subject', 'subject_user_id', 'subject_role', 'occurred_at'),
        Index('ix_cancellation_events_booking', 'booking_id'),
        Index('ix_cancellation_events_review', 'review_state', 'occurred_at'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey('bookings.id', ondelete='RESTRICT'))
    kind: Mapped[str] = mapped_column(String(16))
    # Who performed the action; `subject_*` is the user the event is counted against.
    party: Mapped[str] = mapped_column(String(16))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    subject_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('users.id', ondelete='RESTRICT')
    )
    subject_role: Mapped[str | None] = mapped_column(String(16))
    booking_status_before: Mapped[str] = mapped_column(String(16))
    booking_starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Seconds from the event to the booking start (negative once the start has passed).
    lead_seconds: Mapped[int] = mapped_column(BigInteger)
    last_minute: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(Text, default='')
    excuse_state: Mapped[str] = mapped_column(String(8), default='none')
    review_state: Mapped[str] = mapped_column(String(8), default='none')
    dispute_note: Mapped[str | None] = mapped_column(Text)
    disputed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)


class CancellationCase(TimestampMixin, Base):
    """'Needs admin review': a counter crossed its configured threshold. Never a restriction."""

    __tablename__ = 'cancellation_cases'
    __table_args__ = (
        CheckConstraint(_in('role', SUBJECT_ROLES), name='ck_cancellation_case_role'),
        CheckConstraint(_in('trigger', CASE_TRIGGERS), name='ck_cancellation_case_trigger'),
        CheckConstraint("status IN ('open', 'closed')", name='ck_cancellation_case_status'),
        CheckConstraint(
            "resolution IS NULL OR resolution IN ('no_action', 'restricted')",
            name='ck_cancellation_case_resolution',
        ),
        Index(
            'uq_cancellation_case_open',
            'user_id',
            'role',
            'trigger',
            unique=True,
            postgresql_where=text("status = 'open'"),
            sqlite_where=text("status = 'open'"),
        ),
        Index('ix_cancellation_cases_status', 'status', 'opened_at'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    role: Mapped[str] = mapped_column(String(16))
    trigger: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(8), default='open')
    # {count, threshold, window_days} at the moment the case was opened.
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    resolution: Mapped[str | None] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(Text)


class BookingRestriction(TimestampMixin, Base):
    """Temporary restriction created by an admin only. Active = not lifted and not yet ended."""

    __tablename__ = 'booking_restrictions'
    __table_args__ = (
        CheckConstraint(_in('role', SUBJECT_ROLES), name='ck_booking_restriction_role'),
        CheckConstraint('ends_at > starts_at', name='ck_booking_restriction_interval'),
        Index('ix_booking_restrictions_user', 'user_id', 'role', 'ends_at'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    # 'customer' blocks creating booking requests; 'companion' blocks accepting new requests.
    role: Mapped[str] = mapped_column(String(16))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text)  # Internal: never returned to the restricted user.
    case_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('cancellation_cases.id', ondelete='RESTRICT')
    )
    created_by: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    lifted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lifted_by: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    lift_reason: Mapped[str | None] = mapped_column(Text)


class CancellationAuditEntry(TimestampMixin, Base):
    """Append-only trail: every record, warning, review, restriction change (previous -> new)."""

    __tablename__ = 'cancellation_audit_entries'
    __table_args__ = (
        CheckConstraint(
            "actor_kind IN ('customer', 'companion', 'admin', 'system')",
            name='ck_cancellation_audit_actor',
        ),
        Index('ix_cancellation_audit_subject', 'subject_user_id', 'created_at'),
        Index('ix_cancellation_audit_event', 'event_id'),
        Index('ix_cancellation_audit_restriction', 'restriction_id'),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    action: Mapped[str] = mapped_column(String(40))
    actor_kind: Mapped[str] = mapped_column(String(16))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    subject_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('users.id', ondelete='RESTRICT')
    )
    booking_id: Mapped[UUID | None] = mapped_column(ForeignKey('bookings.id', ondelete='RESTRICT'))
    event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('cancellation_events.id', ondelete='RESTRICT')
    )
    case_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('cancellation_cases.id', ondelete='RESTRICT')
    )
    restriction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey('booking_restrictions.id', ondelete='RESTRICT')
    )
    previous_state: Mapped[dict | None] = mapped_column(JSON)
    new_state: Mapped[dict | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)
