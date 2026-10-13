"""Offline CLICK-simulated gift orders and manual-operator fulfillment.

Revision ID: 20261013_0013
Revises: 20261013_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261013_0013'
down_revision: str | None = '20261013_0012'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def stamps():
    return (
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )


def upgrade() -> None:
    op.create_table(
        'gift_test_orders',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column(
            'customer_id', sa.Uuid(),
            sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False,
        ),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('subtotal_minor', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('delivery_method', sa.String(24), nullable=False),
        sa.Column('delivery_note', sa.Text(), nullable=True),
        sa.Column('click_trans_id', sa.BigInteger(), nullable=True),
        sa.Column('prepared_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('test_paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'status_changed_by', sa.Uuid(),
            sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('awaiting_test_payment','test_paid','preparing',"
            "'out_for_delivery','delivered','cancelled')",
            name='ck_gift_test_order_status',
        ),
        sa.CheckConstraint(
            "delivery_method IN ('pickup','manual_delivery')",
            name='ck_gift_test_delivery_method',
        ),
        sa.CheckConstraint('subtotal_minor >= 0', name='ck_gift_test_order_amount'),
        sa.UniqueConstraint('click_trans_id', name='uq_gift_test_click_trans'),
        *stamps(),
    )
    op.create_index(
        'ix_gift_test_order_customer', 'gift_test_orders',
        ['customer_id', 'created_at'],
    )
    op.create_index(
        'ix_gift_test_order_status', 'gift_test_orders',
        ['status', 'created_at'],
    )
    op.create_table(
        'gift_test_order_items',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column(
            'order_id', sa.Uuid(),
            sa.ForeignKey('gift_test_orders.id', ondelete='RESTRICT'), nullable=False,
        ),
        sa.Column(
            'product_id', sa.Uuid(),
            sa.ForeignKey('gift_products.id', ondelete='RESTRICT'), nullable=False,
        ),
        sa.Column('name_snapshot', sa.String(160), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price_minor', sa.BigInteger(), nullable=False),
        sa.Column('line_total_minor', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('order_id', 'product_id', name='uq_gift_test_order_product'),
        sa.CheckConstraint(
            'quantity BETWEEN 1 AND 100',
            name='ck_gift_test_order_item_quantity',
        ),
        sa.CheckConstraint(
            'unit_price_minor >= 0 AND line_total_minor >= 0',
            name='ck_gift_test_order_item_amounts',
        ),
        *stamps(),
    )


def downgrade() -> None:
    op.drop_table('gift_test_order_items')
    op.drop_index('ix_gift_test_order_status', table_name='gift_test_orders')
    op.drop_index('ix_gift_test_order_customer', table_name='gift_test_orders')
    op.drop_table('gift_test_orders')
