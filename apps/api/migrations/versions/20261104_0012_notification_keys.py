"""notification keys

Revision ID: 20261104_0012
Revises: 20261104_0011
Create Date: 2026-11-04 14:23:58.342712
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261104_0012'
down_revision: str | None = '20261104_0011'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'notification_keys',
        sa.Column('key', sa.String(length=160), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    op.drop_table('notification_keys')
