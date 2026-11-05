"""Add payment attempts, verified provider events, and companion payout records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261009_0007'
down_revision: str | None = '20261009_0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'payments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('idempotency_key', sa.String(128), nullable=False),
        sa.Column('provider_reference', sa.String(256), nullable=True),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('subtotal_minor', sa.BigInteger(), nullable=False),
        sa.Column('platform_fee_minor', sa.BigInteger(), nullable=False),
        sa.Column('amount_minor', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('checkout_url', sa.String(2048), nullable=True),
        sa.Column('refund_required', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('creating', 'pending', 'succeeded', 'failed')",
            name='ck_payment_status',
        ),
        sa.CheckConstraint(
            'subtotal_minor >= 0 AND platform_fee_minor >= 0 AND amount_minor >= 0',
            name='ck_payment_amounts',
        ),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_reference'),
        sa.UniqueConstraint('customer_id', 'idempotency_key', name='uq_payment_idempotency'),
    )
    op.create_index('ix_payments_booking_id', 'payments', ['booking_id'])
    op.create_index(
        'uq_successful_payment_per_booking',
        'payments',
        ['booking_id'],
        unique=True,
        postgresql_where=sa.text("status = 'succeeded'"),
        sqlite_where=sa.text("status = 'succeeded'"),
    )
    op.create_table(
        'payment_event_receipts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('payment_id', sa.Uuid(), nullable=False),
        sa.Column('provider_event_id', sa.String(256), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_event_id', name='uq_payment_provider_event'),
    )
    op.create_table(
        'companion_payouts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=False),
        sa.Column('companion_user_id', sa.Uuid(), nullable=False),
        sa.Column('amount_minor', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint('amount_minor >= 0', name='ck_companion_payout_amount'),
        sa.CheckConstraint(
            "status IN ('held', 'ready', 'paid')", name='ck_companion_payout_status'
        ),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['companion_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_id', name='uq_companion_payout_booking'),
    )


def downgrade() -> None:
    op.drop_table('companion_payouts')
    op.drop_table('payment_event_receipts')
    op.drop_index('uq_successful_payment_per_booking', table_name='payments')
    op.drop_index('ix_payments_booking_id', table_name='payments')
    op.drop_table('payments')
