"""push notifications: device registry and the Web Push VAPID key pair

Additive: two new tables. ``push_devices`` holds Android FCM tokens and browser Web Push
subscriptions (unique per token / endpoint). ``push_vapid_keys`` holds at most one row: the
server-generated VAPID key pair, used only when the env does not supply a private key.

Revision ID: 20261118_0024
Revises: 20261115_0023
Create Date: 2026-11-18 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261118_0024'
down_revision: str | None = '20261115_0023'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        'push_devices',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('platform', sa.String(length=16), nullable=False),
        sa.Column('fcm_token', sa.String(length=1024), nullable=True),
        sa.Column('endpoint', sa.String(length=1024), nullable=True),
        sa.Column('p256dh', sa.String(length=128), nullable=True),
        sa.Column('auth_secret', sa.String(length=64), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('disabled_at', sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("platform IN ('android', 'web')", name='ck_push_device_platform'),
        sa.CheckConstraint(
            "(platform = 'android' AND fcm_token IS NOT NULL AND endpoint IS NULL "
            'AND p256dh IS NULL AND auth_secret IS NULL) OR '
            "(platform = 'web' AND fcm_token IS NULL AND endpoint IS NOT NULL "
            'AND p256dh IS NOT NULL AND auth_secret IS NOT NULL)',
            name='ck_push_device_target',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fcm_token'),
        sa.UniqueConstraint('endpoint'),
    )
    op.create_index('ix_push_devices_user', 'push_devices', ['user_id'])
    op.create_table(
        'push_vapid_keys',
        sa.Column('id', sa.SmallInteger(), nullable=False),
        sa.Column('private_key', sa.Text(), nullable=False),
        sa.Column('public_key', sa.String(length=128), nullable=False),
        *_timestamps(),
        sa.CheckConstraint('id = 1', name='ck_push_vapid_single_row'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('push_vapid_keys')
    op.drop_index('ix_push_devices_user', table_name='push_devices')
    op.drop_table('push_devices')
