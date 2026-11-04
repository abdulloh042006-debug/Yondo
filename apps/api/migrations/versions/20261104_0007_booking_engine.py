"""booking engine

Revision ID: 20261104_0007
Revises: 20261104_0006
Create Date: 2026-11-04 13:29:38.826375
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20261104_0007'
down_revision: str | None = '20261104_0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


HELD = "status IN ('accepted', 'confirmed', 'active')"


def held_overlap_exclusions() -> list:
    """Database-level double-booking protection; requires btree_gist (migration 0003)."""
    if op.get_context().dialect.name != 'postgresql':
        return []
    return [
        postgresql.ExcludeConstraint(
            (sa.column(party), '='),
            (sa.text("tstzrange(starts_at, ends_at, '[)')"), '&&'),
            where=sa.text(HELD),
            using='gist',
            name=f'ex_bookings_{party.removesuffix("_id")}_overlap',
        )
        for party in ('companion_id', 'customer_id')
    ]


def upgrade() -> None:
    op.create_table(
        'bookings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('companion_id', sa.Uuid(), nullable=False),
        sa.Column('profile_id', sa.Uuid(), nullable=False),
        sa.Column('service_id', sa.Uuid(), nullable=True),
        sa.Column('rebooked_from_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('service_code', sa.String(length=64), nullable=False),
        sa.Column('unit_price_minor', sa.BigInteger(), nullable=False),
        sa.Column('unit_minutes', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('timezone', sa.String(length=64), nullable=False),
        sa.Column('meeting_place_name', sa.String(length=200), nullable=False),
        sa.Column('meeting_address', sa.String(length=500), nullable=False),
        sa.Column('meeting_latitude', sa.Float(), nullable=True),
        sa.Column('meeting_longitude', sa.Float(), nullable=True),
        sa.Column('customer_note', sa.Text(), nullable=False),
        sa.Column('service_amount_minor', sa.BigInteger(), nullable=False),
        sa.Column('platform_fee_minor', sa.BigInteger(), nullable=False),
        sa.Column('total_minor', sa.BigInteger(), nullable=False),
        sa.Column('companion_payout_minor', sa.BigInteger(), nullable=False),
        sa.Column('refund_minor', sa.BigInteger(), nullable=False),
        sa.Column('contract', sa.JSON(), nullable=False),
        sa.Column('contract_version', sa.String(length=64), nullable=False),
        sa.Column('customer_accepted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('companion_accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('request_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payment_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_by', sa.Uuid(), nullable=True),
        sa.Column('cancellation_reason', sa.String(length=32), nullable=True),
        sa.Column('cancellation_note', sa.Text(), nullable=True),
        sa.Column('customer_checked_in_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('companion_checked_in_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_by', sa.Uuid(), nullable=True),
        sa.Column('no_show_reported_by', sa.Uuid(), nullable=True),
        sa.Column('no_show_party', sa.String(length=16), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        *held_overlap_exclusions(),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'confirmed', 'active', 'completed', "
            "'cancelled', 'no_show', 'disputed')",
            name='ck_bookings_status',
        ),
        sa.CheckConstraint('customer_id <> companion_id', name='ck_bookings_distinct_parties'),
        sa.CheckConstraint('duration_minutes > 0', name='ck_bookings_duration'),
        sa.CheckConstraint('ends_at > starts_at', name='ck_bookings_interval'),
        sa.CheckConstraint(
            'service_amount_minor >= 0 AND platform_fee_minor >= 0 AND total_minor >= 0 '
            'AND companion_payout_minor >= 0 AND refund_minor >= 0',
            name='ck_bookings_amounts',
        ),
        sa.ForeignKeyConstraint(
            ['cancelled_by'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['companion_id'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['customer_id'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['ended_by'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['no_show_reported_by'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['profile_id'],
            ['companion_profiles.id'],
        ),
        sa.ForeignKeyConstraint(['rebooked_from_id'], ['bookings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['service_id'], ['companion_services.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_bookings_companion_start', 'bookings', ['companion_id', 'starts_at'], unique=False
    )
    op.create_index(
        'ix_bookings_customer_start', 'bookings', ['customer_id', 'starts_at'], unique=False
    )
    op.create_index('ix_bookings_status', 'bookings', ['status'], unique=False)
    op.create_table(
        'booking_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('event', sa.String(length=64), nullable=False),
        sa.Column('from_status', sa.String(length=16), nullable=True),
        sa.Column('to_status', sa.String(length=16), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_booking_events_booking_created',
        'booking_events',
        ['booking_id', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_booking_events_booking_created', table_name='booking_events')
    op.drop_table('booking_events')
    op.drop_index('ix_bookings_status', table_name='bookings')
    op.drop_index('ix_bookings_customer_start', table_name='bookings')
    op.drop_index('ix_bookings_companion_start', table_name='bookings')
    op.drop_table('bookings')
