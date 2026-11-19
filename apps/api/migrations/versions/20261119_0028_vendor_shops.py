"""gift vendors: shop profiles, product rejection notes, one order per vendor, shop notices

Additive (one table, nullable columns); the two notification CHECK constraints are widened.
Existing single-vendor test orders get their vendor_id backfilled.

Revision ID: 20261119_0028
Revises: 20261119_0027
Create Date: 2026-11-19 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261119_0028'
down_revision: str | None = '20261119_0027'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_KINDS = (
    "kind IN ('booking_requested','booking_accepted','booking_declined',"
    "'booking_cancelled','payment_confirmed','chat_message',"
    "'review_reminder','gift_order_created','gift_test_paid','gift_preparing',"
    "'gift_out_for_delivery','gift_delivered','gift_cancelled')"
)
NEW_KINDS = OLD_KINDS[:-1] + (
    ",'vendor_approved','vendor_rejected','vendor_suspended','gift_product_rejected')"
)
OLD_SINGLE = (
    '(booking_id IS NOT NULL AND gift_order_id IS NULL) OR '
    '(booking_id IS NULL AND gift_order_id IS NOT NULL)'
)
NEW_SINGLE = (
    '(booking_id IS NOT NULL AND gift_order_id IS NULL AND vendor_shop_id IS NULL) OR '
    '(booking_id IS NULL AND gift_order_id IS NOT NULL AND vendor_shop_id IS NULL) OR '
    '(booking_id IS NULL AND gift_order_id IS NULL AND vendor_shop_id IS NOT NULL)'
)


def upgrade() -> None:
    op.create_table(
        'vendor_shops',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('city', sa.String(length=128), nullable=False),
        sa.Column('delivery_area', sa.String(length=500), nullable=False),
        sa.Column('logo_key', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'suspended')",
            name='ck_vendor_shop_status',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.add_column('gift_products', sa.Column('rejection_note', sa.Text(), nullable=True))
    with op.batch_alter_table('gift_test_orders') as batch:
        batch.add_column(sa.Column('vendor_id', sa.Uuid(), nullable=True))
        batch.add_column(sa.Column('cancel_reason', sa.Text(), nullable=True))
        batch.create_foreign_key(
            'fk_gift_test_orders_vendor_id', 'users', ['vendor_id'], ['id'], ondelete='RESTRICT'
        )
        batch.create_index('ix_gift_test_orders_vendor_id', ['vendor_id'])
    # Backfill: an existing order whose items all come from one vendor belongs to that vendor.
    op.execute(
        """
        UPDATE gift_test_orders SET vendor_id = (
            SELECT p.vendor_id FROM gift_test_order_items i
            JOIN gift_products p ON p.id = i.product_id WHERE i.order_id = gift_test_orders.id
            LIMIT 1
        )
        WHERE (
            SELECT COUNT(DISTINCT p.vendor_id) FROM gift_test_order_items i
            JOIN gift_products p ON p.id = i.product_id WHERE i.order_id = gift_test_orders.id
        ) = 1
        """
    )
    with op.batch_alter_table('user_notifications') as batch:
        batch.add_column(sa.Column('vendor_shop_id', sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            'fk_user_notifications_vendor_shop_id',
            'vendor_shops',
            ['vendor_shop_id'],
            ['id'],
            ondelete='RESTRICT',
        )
        batch.drop_constraint('ck_notification_single_resource', type_='check')
        batch.drop_constraint('ck_user_notification_kind', type_='check')
        batch.create_check_constraint('ck_user_notification_kind', NEW_KINDS)
        batch.create_check_constraint('ck_notification_single_resource', NEW_SINGLE)


def downgrade() -> None:
    op.execute('DELETE FROM user_notifications WHERE vendor_shop_id IS NOT NULL')
    with op.batch_alter_table('user_notifications') as batch:
        batch.drop_constraint('ck_notification_single_resource', type_='check')
        batch.drop_constraint('ck_user_notification_kind', type_='check')
        batch.drop_constraint('fk_user_notifications_vendor_shop_id', type_='foreignkey')
        batch.drop_column('vendor_shop_id')
        batch.create_check_constraint('ck_user_notification_kind', OLD_KINDS)
        batch.create_check_constraint('ck_notification_single_resource', OLD_SINGLE)
    with op.batch_alter_table('gift_test_orders') as batch:
        batch.drop_index('ix_gift_test_orders_vendor_id')
        batch.drop_constraint('fk_gift_test_orders_vendor_id', type_='foreignkey')
        batch.drop_column('cancel_reason')
        batch.drop_column('vendor_id')
    op.drop_column('gift_products', 'rejection_note')
    op.drop_table('vendor_shops')
