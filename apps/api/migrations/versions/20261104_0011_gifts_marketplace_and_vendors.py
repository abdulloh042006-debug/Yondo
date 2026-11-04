"""gifts marketplace and vendors

Revision ID: 20261104_0011
Revises: 20261104_0010
Create Date: 2026-11-04 14:09:08.069951
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261104_0011'
down_revision: str | None = '20261104_0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'vendors',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('city', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('delivery_fee_minor', sa.BigInteger(), nullable=False),
        sa.Column('delivery_time_minutes', sa.Integer(), nullable=False),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('pending', 'approved', 'rejected', 'suspended')", name='ck_vendors_status'
        ),
        sa.CheckConstraint('delivery_fee_minor >= 0', name='ck_vendors_delivery_fee'),
        sa.CheckConstraint('length(currency) = 3', name='ck_vendors_currency'),
        sa.ForeignKeyConstraint(
            ['reviewed_by'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_table(
        'products',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('vendor_id', sa.Uuid(), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('price_minor', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('stock', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('hidden_by_admin', sa.Boolean(), nullable=False),
        sa.Column('hidden_reason', sa.Text(), nullable=True),
        sa.Column('delivery_time_minutes', sa.Integer(), nullable=True),
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
            "category IN ('flowers', 'chocolate', 'gift_box', 'toys', 'birthday', 'romantic', "
            "'custom')",
            name='ck_products_category',
        ),
        sa.CheckConstraint('price_minor > 0', name='ck_products_price'),
        sa.CheckConstraint('stock >= 0', name='ck_products_stock'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_products_category_active', 'products', ['category', 'is_active'], unique=False
    )
    op.create_index('ix_products_vendor', 'products', ['vendor_id'], unique=False)
    op.create_table(
        'cart_items',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('note', sa.String(length=500), nullable=False),
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
        sa.CheckConstraint('quantity > 0', name='ck_cart_items_quantity'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'product_id'),
    )
    op.create_table(
        'favorite_products',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'product_id'),
    )
    op.create_index(
        op.f('ix_favorite_products_product_id'), 'favorite_products', ['product_id'], unique=False
    )
    op.create_table(
        'product_images',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'position', name='uq_product_image_position'),
        sa.UniqueConstraint('storage_key'),
    )
    op.create_index(
        op.f('ix_product_images_product_id'), 'product_images', ['product_id'], unique=False
    )
    op.create_table(
        'gift_orders',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('vendor_id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=True),
        sa.Column('payment_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=24), nullable=False),
        sa.Column('recipient_name', sa.String(length=128), nullable=False),
        sa.Column('recipient_phone', sa.String(length=32), nullable=False),
        sa.Column('delivery_address', sa.String(length=500), nullable=False),
        sa.Column('delivery_latitude', sa.Float(), nullable=True),
        sa.Column('delivery_longitude', sa.Float(), nullable=True),
        sa.Column('delivery_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('subtotal_minor', sa.BigInteger(), nullable=False),
        sa.Column('delivery_fee_minor', sa.BigInteger(), nullable=False),
        sa.Column('platform_fee_minor', sa.BigInteger(), nullable=False),
        sa.Column('total_minor', sa.BigInteger(), nullable=False),
        sa.Column('cancelled_reason', sa.String(length=64), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('pending_payment', 'new', 'accepted', 'preparing', 'courier_assigned', "
            "'delivering', 'delivered', 'cancelled')",
            name='ck_gift_orders_status',
        ),
        sa.CheckConstraint(
            'subtotal_minor > 0 AND delivery_fee_minor >= 0 AND platform_fee_minor >= 0 '
            'AND total_minor = subtotal_minor + delivery_fee_minor + platform_fee_minor',
            name='ck_gift_orders_amounts',
        ),
        sa.ForeignKeyConstraint(
            ['booking_id'],
            ['bookings.id'],
        ),
        sa.ForeignKeyConstraint(
            ['customer_id'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['payment_id'],
            ['payments.id'],
        ),
        sa.ForeignKeyConstraint(
            ['vendor_id'],
            ['vendors.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_gift_orders_booking', 'gift_orders', ['booking_id'], unique=False)
    op.create_index(
        'ix_gift_orders_customer_created',
        'gift_orders',
        ['customer_id', 'created_at'],
        unique=False,
    )
    op.create_index('ix_gift_orders_payment', 'gift_orders', ['payment_id'], unique=False)
    op.create_index(
        'ix_gift_orders_vendor_status', 'gift_orders', ['vendor_id', 'status'], unique=False
    )
    op.create_table(
        'gift_order_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('order_id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=True),
        sa.Column('product_name', sa.String(length=200), nullable=False),
        sa.Column('unit_price_minor', sa.BigInteger(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('note', sa.String(length=500), nullable=False),
        sa.CheckConstraint('quantity > 0', name='ck_gift_order_items_quantity'),
        sa.ForeignKeyConstraint(['order_id'], ['gift_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_gift_order_items_order_id'), 'gift_order_items', ['order_id'], unique=False
    )
    op.create_table(
        'gift_reviews',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('order_id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('vendor_id', sa.Uuid(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
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
        sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_gift_reviews_rating'),
        sa.ForeignKeyConstraint(
            ['customer_id'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(['order_id'], ['gift_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['vendor_id'],
            ['vendors.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id'),
    )
    op.create_index('ix_gift_reviews_vendor', 'gift_reviews', ['vendor_id'], unique=False)
    op.create_foreign_key(
        'fk_payouts_gift_order_id', 'payouts', 'gift_orders', ['gift_order_id'], ['id']
    )


def downgrade() -> None:
    # WARNING: constraint name is None; this directive will fail as
    # rendered.  Add a name, or use a naming convention; see
    # https://alembic.sqlalchemy.org/en/latest/naming.html
    op.drop_constraint('fk_payouts_gift_order_id', 'payouts', type_='foreignkey')
    op.drop_index('ix_gift_reviews_vendor', table_name='gift_reviews')
    op.drop_table('gift_reviews')
    op.drop_index(op.f('ix_gift_order_items_order_id'), table_name='gift_order_items')
    op.drop_table('gift_order_items')
    op.drop_index('ix_gift_orders_vendor_status', table_name='gift_orders')
    op.drop_index('ix_gift_orders_payment', table_name='gift_orders')
    op.drop_index('ix_gift_orders_customer_created', table_name='gift_orders')
    op.drop_index('ix_gift_orders_booking', table_name='gift_orders')
    op.drop_table('gift_orders')
    op.drop_index(op.f('ix_product_images_product_id'), table_name='product_images')
    op.drop_table('product_images')
    op.drop_index(op.f('ix_favorite_products_product_id'), table_name='favorite_products')
    op.drop_table('favorite_products')
    op.drop_table('cart_items')
    op.drop_index('ix_products_vendor', table_name='products')
    op.drop_index('ix_products_category_active', table_name='products')
    op.drop_table('products')
    op.drop_table('vendors')
