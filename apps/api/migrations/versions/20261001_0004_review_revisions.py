"""Bind companion decisions to reviewed revisions."""

import sqlalchemy as sa
from alembic import op

revision = '20261001_0004'
down_revision = '20260930_0003'
branch_labels = None
depends_on = None


def upgrade():
    for table in ('companion_applications', 'companion_profiles'):
        op.add_column(
            table, sa.Column('revision', sa.BigInteger(), nullable=False, server_default='1')
        )


def downgrade():
    for table in ('companion_profiles', 'companion_applications'):
        op.drop_column(table, 'revision')
