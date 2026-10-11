"""Add customer companion favorites."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261009_0005'
down_revision: str | None = '20261001_0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'companion_favorites',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('profile_id', sa.Uuid(), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profile_id'], ['companion_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_id', 'profile_id', name='uq_companion_favorite'),
    )
    op.create_index('ix_companion_favorites_customer_id', 'companion_favorites', ['customer_id'])
    op.create_index('ix_companion_favorites_profile_id', 'companion_favorites', ['profile_id'])


def downgrade() -> None:
    op.drop_index('ix_companion_favorites_profile_id', table_name='companion_favorites')
    op.drop_index('ix_companion_favorites_customer_id', table_name='companion_favorites')
    op.drop_table('companion_favorites')
