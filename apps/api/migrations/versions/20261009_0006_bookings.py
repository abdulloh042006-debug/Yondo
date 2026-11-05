"""Add booking contracts and enforce non-overlapping reservations."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ExcludeConstraint

revision: str = '20261009_0006'
down_revision: str | None = '20261009_0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_context().dialect.name == 'postgresql':
        op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
    op.create_table(
        'bookings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('profile_id', sa.Uuid(), nullable=False),
        sa.Column('service_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('service_code', sa.String(64), nullable=False),
        sa.Column('service_description', sa.Text(), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timezone', sa.String(64), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('meeting_place', sa.String(512), nullable=False),
        sa.Column('price_minor', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('customer_contract_accepted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('companion_contract_accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'confirmed', 'active', 'completed', "
            "'cancelled', 'no-show', 'disputed')",
            name='ck_booking_status',
        ),
        sa.CheckConstraint('ends_at > starts_at', name='ck_booking_interval'),
        sa.CheckConstraint('duration_minutes > 0', name='ck_booking_duration'),
        sa.CheckConstraint('price_minor >= 0', name='ck_booking_price'),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['profile_id'], ['companion_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['service_id'], ['companion_services.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        ExcludeConstraint(
            ('profile_id', '='),
            (sa.func.tstzrange(sa.column('starts_at'), sa.column('ends_at'), '[)'), '&&'),
            where=sa.text("status IN ('pending', 'accepted', 'confirmed', 'active')"),
            name='ex_booking_active_overlap',
            using='gist',
        ).ddl_if(dialect='postgresql'),
    )
    op.create_index('ix_bookings_customer_created', 'bookings', ['customer_id', 'created_at'])
    op.create_index('ix_bookings_profile_start', 'bookings', ['profile_id', 'starts_at'])


def downgrade() -> None:
    op.drop_index('ix_bookings_profile_start', table_name='bookings')
    op.drop_index('ix_bookings_customer_created', table_name='bookings')
    op.drop_table('bookings')
