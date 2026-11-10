"""identity verifications

Revision ID: 20261105_0018
Revises: 20261023_0017
Create Date: 2026-11-05 04:59:06.390436
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261105_0018'
down_revision: str | None = '20261023_0017'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'identity_verifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('document_type', sa.String(length=32), nullable=False),
        sa.Column('document_key', sa.String(length=512), nullable=True),
        sa.Column('selfie_key', sa.String(length=512), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
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
            "document_type IN ('passport', 'id_card', 'driver_license')",
            name='ck_identity_verifications_document',
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'pending', 'verified', 'rejected')",
            name='ck_identity_verifications_status',
        ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_identity_verifications_status', 'identity_verifications', ['status'], unique=False
    )
    op.create_index(
        'ix_identity_verifications_user_created',
        'identity_verifications',
        ['user_id', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_identity_verifications_user_created', table_name='identity_verifications')
    op.drop_index('ix_identity_verifications_status', table_name='identity_verifications')
    op.drop_table('identity_verifications')
