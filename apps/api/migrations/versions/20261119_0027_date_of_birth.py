"""18+ for everyone (owner, 2026-11-19): users.date_of_birth, users.age_restricted_at, age_blocks

Additive: two nullable columns and one table. Existing accounts give the date once at their next
sign-in. age_blocks keeps only a salted phone hash and the end of a 30-day cooldown.

Revision ID: 20261119_0027
Revises: 20261119_0026
Create Date: 2026-11-19 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261119_0027'
down_revision: str | None = '20261119_0026'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column(
        'users', sa.Column('age_restricted_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        'age_blocks',
        sa.Column('phone_hash', sa.LargeBinary(length=32), nullable=False),
        sa.Column('blocked_until', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('phone_hash'),
    )


def downgrade() -> None:
    op.drop_table('age_blocks')
    op.drop_column('users', 'age_restricted_at')
    op.drop_column('users', 'date_of_birth')
