"""payments refunds payouts

Revision ID: 20261104_0008
Revises: 20261104_0007
Create Date: 2026-11-04 13:38:47.543493
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261104_0008'
down_revision: str | None = '20261104_0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'payments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('payer_id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=True),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('provider_payment_id', sa.String(length=128), nullable=True),
        sa.Column('idempotency_key', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('amount_minor', sa.BigInteger(), nullable=False),
        sa.Column('refunded_minor', sa.BigInteger(), nullable=False),
        sa.Column('breakdown', sa.JSON(), nullable=False),
        sa.Column('checkout_url', sa.String(length=1024), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.String(length=200), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'cancelled', 'refunded', "
            "'partially_refunded')",
            name='ck_payments_status',
        ),
        sa.CheckConstraint('amount_minor > 0', name='ck_payments_amount'),
        sa.CheckConstraint(
            'refunded_minor >= 0 AND refunded_minor <= amount_minor', name='ck_payments_refunded'
        ),
        sa.ForeignKeyConstraint(
            ['booking_id'],
            ['bookings.id'],
        ),
        sa.ForeignKeyConstraint(
            ['payer_id'],
            ['users.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('payer_id', 'idempotency_key', name='uq_payments_idempotency'),
        sa.UniqueConstraint('provider', 'provider_payment_id', name='uq_payments_provider_id'),
    )
    op.create_index(
        'ix_payments_payer_created', 'payments', ['payer_id', 'created_at'], unique=False
    )
    op.create_index('ix_payments_status', 'payments', ['status'], unique=False)
    op.create_index(
        'uq_payments_live_booking',
        'payments',
        ['booking_id'],
        unique=True,
        postgresql_where=sa.text("booking_id IS NOT NULL AND status IN ('pending', 'succeeded')"),
        sqlite_where=sa.text("booking_id IS NOT NULL AND status IN ('pending', 'succeeded')"),
    )
    op.create_table(
        'payouts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('beneficiary_id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=True),
        sa.Column('gift_order_id', sa.Uuid(), nullable=True),
        sa.Column('amount_minor', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('available_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_by', sa.Uuid(), nullable=True),
        sa.Column('reference', sa.String(length=200), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('held', 'scheduled', 'paid', 'cancelled')", name='ck_payouts_status'
        ),
        sa.CheckConstraint(
            '(booking_id IS NOT NULL) <> (gift_order_id IS NOT NULL)', name='ck_payouts_source'
        ),
        sa.CheckConstraint('amount_minor >= 0', name='ck_payouts_amount'),
        sa.ForeignKeyConstraint(
            ['beneficiary_id'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['booking_id'],
            ['bookings.id'],
        ),
        sa.ForeignKeyConstraint(
            ['paid_by'],
            ['users.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_id'),
        sa.UniqueConstraint('gift_order_id'),
    )
    op.create_index(
        'ix_payouts_beneficiary_status', 'payouts', ['beneficiary_id', 'status'], unique=False
    )
    op.create_table(
        'payment_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('event_id', sa.String(length=128), nullable=False),
        sa.Column('payment_id', sa.Uuid(), nullable=True),
        sa.Column('outcome', sa.String(length=32), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['payment_id'],
            ['payments.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'event_id', name='uq_payment_events_provider_event'),
    )
    op.create_table(
        'refunds',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('payment_id', sa.Uuid(), nullable=False),
        sa.Column('amount_minor', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('reason', sa.String(length=64), nullable=False),
        sa.Column('provider_refund_id', sa.String(length=128), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed')", name='ck_refunds_status'
        ),
        sa.CheckConstraint('amount_minor > 0', name='ck_refunds_amount'),
        sa.ForeignKeyConstraint(
            ['payment_id'],
            ['payments.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_refunds_payment_id'), 'refunds', ['payment_id'], unique=False)
    op.create_index('ix_refunds_status', 'refunds', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_refunds_status', table_name='refunds')
    op.drop_index(op.f('ix_refunds_payment_id'), table_name='refunds')
    op.drop_table('refunds')
    op.drop_table('payment_events')
    op.drop_index('ix_payouts_beneficiary_status', table_name='payouts')
    op.drop_table('payouts')
    op.drop_index(
        'uq_payments_live_booking',
        table_name='payments',
        postgresql_where=sa.text("booking_id IS NOT NULL AND status IN ('pending', 'succeeded')"),
        sqlite_where=sa.text("booking_id IS NOT NULL AND status IN ('pending', 'succeeded')"),
    )
    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_index('ix_payments_payer_created', table_name='payments')
    op.drop_table('payments')
