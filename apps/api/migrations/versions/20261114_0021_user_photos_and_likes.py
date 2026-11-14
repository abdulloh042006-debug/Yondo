"""account photos for every user and public companion likes

Additive: two new tables. ``user_photos`` holds account (customer) photos, at most 6 visible
per user (enforced in the API). ``companion_likes`` holds one like per user per profile.

Revision ID: 20261114_0021
Revises: 20261111_0020
Create Date: 2026-11-14 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261114_0021'
down_revision: str | None = '20261111_0020'
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
        'user_photos',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('content_type', sa.String(length=64), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint('position IS NULL OR position >= 0', name='ck_user_photo_position'),
        sa.CheckConstraint(
            'size_bytes > 0 AND width > 0 AND height > 0', name='ck_user_photo_dimensions'
        ),
        sa.CheckConstraint(
            '(deleted_at IS NULL AND position IS NOT NULL) OR '
            '(deleted_at IS NOT NULL AND position IS NULL)',
            name='ck_user_photo_deleted_position',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('storage_key'),
        sa.UniqueConstraint('user_id', 'position', name='uq_user_photo_position'),
    )
    op.create_index('ix_user_photos_user_id', 'user_photos', ['user_id'])
    op.create_table(
        'companion_likes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('profile_id', sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['companion_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'profile_id', name='uq_companion_like'),
    )
    op.create_index('ix_companion_likes_user_id', 'companion_likes', ['user_id'])
    op.create_index('ix_companion_likes_profile_id', 'companion_likes', ['profile_id'])


def downgrade() -> None:
    op.drop_index('ix_companion_likes_profile_id', table_name='companion_likes')
    op.drop_index('ix_companion_likes_user_id', table_name='companion_likes')
    op.drop_table('companion_likes')
    op.drop_index('ix_user_photos_user_id', table_name='user_photos')
    op.drop_table('user_photos')
