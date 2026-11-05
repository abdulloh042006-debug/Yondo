"""Account deletion requests, legal consents, in-app support requests; 'deleted' account status.

Revision ID: 20261023_0016
Revises: 20261023_0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261023_0016'
down_revision: str | None = '20261023_0015'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_STATUSES = (
    "account_status IN ('active', 'verification_pending', 'restricted', 'suspended', 'banned')"
)
NEW_STATUSES = (
    "account_status IN ('active', 'verification_pending', 'restricted', 'suspended', "
    "'banned', 'deleted')"
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
    ]


def upgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.drop_constraint('ck_users_account_status', type_='check')
        batch.create_check_constraint('ck_users_account_status', NEW_STATUSES)

    op.create_table(
        'account_deletion_requests',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("status IN ('pending', 'cancelled', 'completed')",
                           name='ck_account_deletion_status'),
    )
    op.create_index('ix_account_deletion_requests_user_id', 'account_deletion_requests',
                    ['user_id'])
    op.create_index('ix_account_deletion_requests_due_at', 'account_deletion_requests',
                    ['due_at'])
    op.create_index(
        'uq_account_deletion_pending', 'account_deletion_requests', ['user_id'], unique=True,
        postgresql_where=sa.text("status = 'pending'"), sqlite_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        'user_consents',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('document', sa.String(16), nullable=False),
        sa.Column('version', sa.String(32), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("document IN ('terms', 'privacy')", name='ck_user_consent_document'),
        sa.UniqueConstraint('user_id', 'document', 'version', name='uq_user_consent_version'),
    )
    op.create_index('ix_user_consents_user_id', 'user_consents', ['user_id'])

    op.create_table(
        'support_requests',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('category', sa.String(16), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('reply', sa.Text(), nullable=True),
        sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replied_by', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'),
                  nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "category IN ('account', 'booking', 'payment', 'safety', 'technical', 'other')",
            name='ck_support_request_category',
        ),
        sa.CheckConstraint("status IN ('open', 'answered', 'closed')",
                           name='ck_support_request_status'),
    )
    op.create_index('ix_support_requests_user_id', 'support_requests', ['user_id'])
    op.create_index('ix_support_requests_status', 'support_requests', ['status'])


def downgrade() -> None:
    op.drop_table('support_requests')
    op.drop_table('user_consents')
    op.drop_table('account_deletion_requests')
    # Erased accounts cannot be represented by the old constraint; keep them unusable as 'banned'
    # (their personal data stays erased).
    op.execute("UPDATE users SET account_status = 'banned' WHERE account_status = 'deleted'")
    with op.batch_alter_table('users') as batch:
        batch.drop_constraint('ck_users_account_status', type_='check')
        batch.create_check_constraint('ck_users_account_status', OLD_STATUSES)
