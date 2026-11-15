"""username + password login (additive)

users.username / password_hash / password_changed_at, auth_sessions.via and the
password_login_guards table. Existing rows are untouched (NULL = not set up yet).

Revision ID: 20261115_0023
Revises: 20261114_0022
Create Date: 2026-11-15 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261115_0023'
down_revision: str | None = '20261114_0022'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('username', sa.String(length=30), nullable=True))
        batch.add_column(sa.Column('password_hash', sa.String(length=255), nullable=True))
        batch.add_column(
            sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True)
        )
        batch.create_unique_constraint('uq_users_username', ['username'])
    with op.batch_alter_table('auth_sessions') as batch:
        batch.add_column(sa.Column('via', sa.String(length=16), nullable=True))
    op.create_table(
        'password_login_guards',
        sa.Column('subject', sa.String(length=64), nullable=False),
        sa.Column('failed_attempts', sa.Integer(), nullable=False),
        sa.Column('blocked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint('subject'),
    )


def downgrade() -> None:
    op.drop_table('password_login_guards')
    with op.batch_alter_table('auth_sessions') as batch:
        batch.drop_column('via')
    with op.batch_alter_table('users') as batch:
        batch.drop_constraint('uq_users_username', type_='unique')
        batch.drop_column('password_changed_at')
        batch.drop_column('password_hash')
        batch.drop_column('username')
