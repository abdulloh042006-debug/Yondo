"""Companion stories: 24-hour availability / note cards (no media of their own).

Revision ID: 20261029_0019
Revises: 20261028_0018

Additive: one new table. Downgrade drops it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261029_0019'
down_revision: str | None = '20261028_0018'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'companion_stories',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column(
            'profile_id',
            sa.Uuid(),
            sa.ForeignKey('companion_profiles.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('caption', sa.String(80), nullable=False),
        sa.Column(
            'photo_id',
            sa.Uuid(),
            sa.ForeignKey('companion_photos.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column(
            'service_id',
            sa.Uuid(),
            sa.ForeignKey('companion_services.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'removed_by',
            sa.Uuid(),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('removal_note', sa.Text(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("kind IN ('availability', 'note')", name='ck_companion_story_kind'),
        sa.CheckConstraint(
            "kind = 'availability' OR length(caption) > 0", name='ck_companion_story_note_caption'
        ),
    )
    op.create_index(
        'ix_companion_stories_profile_expires', 'companion_stories', ['profile_id', 'expires_at']
    )


def downgrade() -> None:
    op.drop_index('ix_companion_stories_profile_expires', table_name='companion_stories')
    op.drop_table('companion_stories')
