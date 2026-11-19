"""social sign-in: external identities (Telegram, Google; Apple-ready) and flow challenges

Additive: two new tables. Only SHA-256 hashes of browser-held values are stored.

Revision ID: 20261118_0025
Revises: 20261118_0024
Create Date: 2026-11-18 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261118_0025'
down_revision: str | None = '20261118_0024'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PROVIDERS = "provider IN ('telegram', 'google', 'apple')"


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        'external_identities',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('provider', sa.String(length=16), nullable=False),
        sa.Column('provider_subject', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(_PROVIDERS, name='ck_external_identity_provider'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_subject', name='uq_external_identity_subject'),
        sa.UniqueConstraint('user_id', 'provider', name='uq_external_identity_user_provider'),
    )
    op.create_index('ix_external_identities_user_id', 'external_identities', ['user_id'])
    op.create_table(
        'social_login_challenges',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('provider', sa.String(length=16), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('token_hash', sa.LargeBinary(length=32), nullable=False),
        sa.Column('binding_hash', sa.LargeBinary(length=32), nullable=True),
        sa.Column('nonce', sa.String(length=64), nullable=True),
        sa.Column('code_verifier', sa.String(length=128), nullable=True),
        sa.Column('redirect_uri', sa.String(length=512), nullable=True),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('provider_subject', sa.String(length=255), nullable=True),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(_PROVIDERS, name='ck_social_challenge_provider'),
        sa.CheckConstraint(
            "kind IN ('authorize', 'nonce', 'signup')", name='ck_social_challenge_kind'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )


def downgrade() -> None:
    op.drop_table('social_login_challenges')
    op.drop_index('ix_external_identities_user_id', table_name='external_identities')
    op.drop_table('external_identities')
