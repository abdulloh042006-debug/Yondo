"""Cancellation tracking, review cases, booking restrictions, audit trail; new notice kinds.

Revision ID: 20261028_0018
Revises: 20261023_0017

Additive: four new tables and a wider CHECK on user_notifications (more kinds, and notices that
belong to no booking: restriction notices). No existing row is changed. Downgrade drops the new
tables and removes the notices of the new kinds (the old constraint cannot hold them).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261028_0018'
down_revision: str | None = '20261023_0017'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_KINDS = (
    "kind IN ('booking_requested','booking_accepted','booking_declined',"
    "'booking_cancelled','payment_confirmed','chat_message',"
    "'review_reminder','gift_order_created','gift_test_paid','gift_preparing',"
    "'gift_out_for_delivery','gift_delivered','gift_cancelled')"
)
NEW_KINDS = (
    "kind IN ('booking_requested','booking_accepted','booking_declined',"
    "'booking_cancelled','payment_confirmed','chat_message',"
    "'review_reminder','gift_order_created','gift_test_paid','gift_preparing',"
    "'gift_out_for_delivery','gift_delivered','gift_cancelled',"
    "'booking_no_show','cancellation_warning','booking_restricted',"
    "'booking_restriction_lifted')"
)
OLD_RESOURCE = (
    '(booking_id IS NOT NULL AND gift_order_id IS NULL) OR '
    '(booking_id IS NULL AND gift_order_id IS NOT NULL)'
)
NEW_RESOURCE = (
    OLD_RESOURCE + ' OR '
    "(booking_id IS NULL AND gift_order_id IS NULL AND "
    "kind IN ('booking_restricted','booking_restriction_lifted'))"
)
NEW_KIND_VALUES = (
    "('booking_no_show','cancellation_warning','booking_restricted','booking_restriction_lifted')"
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
    ]


def _user_fk(name: str, nullable: bool = True) -> sa.Column:
    return sa.Column(name, sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'),
                     nullable=nullable)


def _in(column: str, values: tuple[str, ...]) -> str:
    return f'{column} IN (' + ', '.join(f"'{v}'" for v in values) + ')'


def upgrade() -> None:
    op.create_table(
        'cancellation_cases',
        sa.Column('id', sa.Uuid(), primary_key=True),
        _user_fk('user_id', nullable=False),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('trigger', sa.String(24), nullable=False),
        sa.Column('status', sa.String(8), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        _user_fk('closed_by'),
        sa.Column('resolution', sa.String(16), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(_in('role', ('customer', 'companion')),
                           name='ck_cancellation_case_role'),
        sa.CheckConstraint(
            _in('trigger', ('cancellations', 'last_minute', 'no_shows', 'emergency_claims')),
            name='ck_cancellation_case_trigger'),
        sa.CheckConstraint("status IN ('open', 'closed')", name='ck_cancellation_case_status'),
        sa.CheckConstraint("resolution IS NULL OR resolution IN ('no_action', 'restricted')",
                           name='ck_cancellation_case_resolution'),
    )
    op.create_index('uq_cancellation_case_open', 'cancellation_cases',
                    ['user_id', 'role', 'trigger'], unique=True,
                    postgresql_where=sa.text("status = 'open'"),
                    sqlite_where=sa.text("status = 'open'"))
    op.create_index('ix_cancellation_cases_status', 'cancellation_cases', ['status', 'opened_at'])

    op.create_table(
        'cancellation_events',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('booking_id', sa.Uuid(), sa.ForeignKey('bookings.id', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('party', sa.String(16), nullable=False),
        _user_fk('actor_user_id'),
        _user_fk('subject_user_id'),
        sa.Column('subject_role', sa.String(16), nullable=True),
        sa.Column('booking_status_before', sa.String(16), nullable=False),
        sa.Column('booking_starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('lead_seconds', sa.BigInteger(), nullable=False),
        sa.Column('last_minute', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('excuse_state', sa.String(8), nullable=False),
        sa.Column('review_state', sa.String(8), nullable=False),
        sa.Column('dispute_note', sa.Text(), nullable=True),
        sa.Column('disputed_at', sa.DateTime(timezone=True), nullable=True),
        _user_fk('reviewed_by'),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(_in('kind', ('cancelled', 'declined', 'no_show', 'expired')),
                           name='ck_cancellation_event_kind'),
        sa.CheckConstraint(_in('party', ('customer', 'companion', 'admin', 'system')),
                           name='ck_cancellation_event_party'),
        sa.CheckConstraint("subject_role IS NULL OR subject_role IN ('customer', 'companion')",
                           name='ck_cancellation_event_subject_role'),
        sa.CheckConstraint(_in('excuse_state', ('none', 'claimed', 'granted', 'rejected')),
                           name='ck_cancellation_event_excuse'),
        sa.CheckConstraint(_in('review_state', ('none', 'open', 'reviewed')),
                           name='ck_cancellation_event_review'),
        sa.UniqueConstraint('booking_id', 'kind', 'subject_user_id',
                            name='uq_cancellation_event_once'),
    )
    op.create_index('ix_cancellation_events_subject', 'cancellation_events',
                    ['subject_user_id', 'subject_role', 'occurred_at'])
    op.create_index('ix_cancellation_events_booking', 'cancellation_events', ['booking_id'])
    op.create_index('ix_cancellation_events_review', 'cancellation_events',
                    ['review_state', 'occurred_at'])

    op.create_table(
        'booking_restrictions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        _user_fk('user_id', nullable=False),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('case_id', sa.Uuid(), sa.ForeignKey('cancellation_cases.id',
                                                       ondelete='RESTRICT'), nullable=True),
        _user_fk('created_by', nullable=False),
        sa.Column('lifted_at', sa.DateTime(timezone=True), nullable=True),
        _user_fk('lifted_by'),
        sa.Column('lift_reason', sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(_in('role', ('customer', 'companion')),
                           name='ck_booking_restriction_role'),
        sa.CheckConstraint('ends_at > starts_at', name='ck_booking_restriction_interval'),
    )
    op.create_index('ix_booking_restrictions_user', 'booking_restrictions',
                    ['user_id', 'role', 'ends_at'])

    op.create_table(
        'cancellation_audit_entries',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('action', sa.String(40), nullable=False),
        sa.Column('actor_kind', sa.String(16), nullable=False),
        _user_fk('actor_user_id'),
        _user_fk('subject_user_id'),
        sa.Column('booking_id', sa.Uuid(), sa.ForeignKey('bookings.id', ondelete='RESTRICT'),
                  nullable=True),
        sa.Column('event_id', sa.Uuid(), sa.ForeignKey('cancellation_events.id',
                                                        ondelete='RESTRICT'), nullable=True),
        sa.Column('case_id', sa.Uuid(), sa.ForeignKey('cancellation_cases.id',
                                                       ondelete='RESTRICT'), nullable=True),
        sa.Column('restriction_id', sa.Uuid(), sa.ForeignKey('booking_restrictions.id',
                                                              ondelete='RESTRICT'), nullable=True),
        sa.Column('previous_state', sa.JSON(), nullable=True),
        sa.Column('new_state', sa.JSON(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("actor_kind IN ('customer', 'companion', 'admin', 'system')",
                           name='ck_cancellation_audit_actor'),
    )
    op.create_index('ix_cancellation_audit_subject', 'cancellation_audit_entries',
                    ['subject_user_id', 'created_at'])
    op.create_index('ix_cancellation_audit_event', 'cancellation_audit_entries', ['event_id'])
    op.create_index('ix_cancellation_audit_restriction', 'cancellation_audit_entries',
                    ['restriction_id'])

    with op.batch_alter_table('user_notifications') as batch:
        batch.drop_constraint('ck_user_notification_kind', type_='check')
        batch.drop_constraint('ck_notification_single_resource', type_='check')
        batch.create_check_constraint('ck_user_notification_kind', NEW_KINDS)
        batch.create_check_constraint('ck_notification_single_resource', NEW_RESOURCE)


def downgrade() -> None:
    # The old constraints cannot hold the new notice kinds: those notices are removed.
    op.execute(f'DELETE FROM user_notifications WHERE kind IN {NEW_KIND_VALUES}')
    with op.batch_alter_table('user_notifications') as batch:
        batch.drop_constraint('ck_user_notification_kind', type_='check')
        batch.drop_constraint('ck_notification_single_resource', type_='check')
        batch.create_check_constraint('ck_user_notification_kind', OLD_KINDS)
        batch.create_check_constraint('ck_notification_single_resource', OLD_RESOURCE)
    op.drop_table('cancellation_audit_entries')
    op.drop_table('booking_restrictions')
    op.drop_table('cancellation_events')
    op.drop_table('cancellation_cases')
