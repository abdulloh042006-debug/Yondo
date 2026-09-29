'''Create users and roles.

Revision ID: 20260928_0001
Revises:
Create Date: 2026-09-28
'''
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20260928_0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_VALUES = ('customer', 'companion', 'vendor', 'admin')
ACCOUNT_STATUS_VALUES = (
    'active',
    'verification_pending',
    'restricted',
    'suspended',
    'banned',
)


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('phone_number', sa.String(length=32), nullable=False),
        sa.Column('account_status', sa.String(length=32), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.CheckConstraint(
            f'account_status IN {ACCOUNT_STATUS_VALUES}', name='ck_users_account_status'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number', name='uq_users_phone_number'),
    )
    op.create_index('ix_users_account_status', 'users', ['account_status'], unique=False)
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.CheckConstraint(f'role IN {ROLE_VALUES}', name='ck_user_roles_role'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role'),
    )
    op.create_index('ix_user_roles_role', 'user_roles', ['role'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_roles_role', table_name='user_roles')
    op.drop_table('user_roles')
    op.drop_index('ix_users_account_status', table_name='users')
    op.drop_table('users')
