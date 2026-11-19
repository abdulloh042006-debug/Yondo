"""otp issues: one row per code sent, for the per-phone hourly and daily limits

Additive: one table. Rows older than a day are deleted when the next code is requested.

Revision ID: 20261119_0026
Revises: 20261118_0025
Create Date: 2026-11-19 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261119_0026'
down_revision: str | None = '20261118_0025'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'otp_issues',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('phone_number', sa.String(length=16), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_otp_issues_phone_issued', 'otp_issues', ['phone_number', 'issued_at'])


def downgrade() -> None:
    op.drop_index('ix_otp_issues_phone_issued', table_name='otp_issues')
    op.drop_table('otp_issues')
