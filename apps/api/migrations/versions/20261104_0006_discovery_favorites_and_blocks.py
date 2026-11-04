"""discovery favorites and blocks

Revision ID: 20261104_0006
Revises: 20261104_0005
Create Date: 2026-11-04 13:22:07.076593
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261104_0006'
down_revision: str | None = '20261104_0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'user_blocks',
        sa.Column('blocker_id', sa.Uuid(), nullable=False),
        sa.Column('blocked_id', sa.Uuid(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.CheckConstraint('blocker_id <> blocked_id', name='ck_user_blocks_self'),
        sa.ForeignKeyConstraint(['blocked_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['blocker_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('blocker_id', 'blocked_id'),
    )
    op.create_index(op.f('ix_user_blocks_blocked_id'), 'user_blocks', ['blocked_id'], unique=False)
    op.create_table(
        'favorite_companions',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('profile_id', sa.Uuid(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['profile_id'], ['companion_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'profile_id'),
    )
    op.create_index(
        op.f('ix_favorite_companions_profile_id'),
        'favorite_companions',
        ['profile_id'],
        unique=False,
    )
    op.add_column('companion_profiles', sa.Column('area', sa.String(length=128), nullable=True))
    op.add_column('companion_profiles', sa.Column('approx_latitude', sa.Float(), nullable=True))
    op.add_column('companion_profiles', sa.Column('approx_longitude', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('companion_profiles', 'approx_longitude')
    op.drop_column('companion_profiles', 'approx_latitude')
    op.drop_column('companion_profiles', 'area')
    op.drop_index(op.f('ix_favorite_companions_profile_id'), table_name='favorite_companions')
    op.drop_table('favorite_companions')
    op.drop_index(op.f('ix_user_blocks_blocked_id'), table_name='user_blocks')
    op.drop_table('user_blocks')
