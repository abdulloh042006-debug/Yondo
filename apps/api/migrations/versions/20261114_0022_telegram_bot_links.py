"""telegram bot login: phone <-> chat links and single-use link challenges

Additive: two new tables. Only SHA-256 hashes of the deep-link token and of the browser poll
token are stored.

Revision ID: 20261114_0022
Revises: 20261111_0020
Create Date: 2026-11-14 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261114_0022'
# NOTE: re-chain onto 20261114_0021 if PR #34 (user photos and likes) merges first.
down_revision: str | None = '20261111_0020'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
        'telegram_links',
        sa.Column('phone_number', sa.String(length=16), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=False),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint('phone_number'),
        sa.UniqueConstraint('telegram_user_id'),
    )
    op.create_table(
        'telegram_link_challenges',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.LargeBinary(length=32), nullable=False),
        sa.Column('poll_hash', sa.LargeBinary(length=32), nullable=False),
        sa.Column('phone_number', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('failure_code', sa.String(length=64), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending', 'linked', 'otp_sent', 'failed', 'expired')",
            name='ck_telegram_link_challenge_status',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
        sa.UniqueConstraint('poll_hash'),
    )
    op.create_index(
        'ix_telegram_link_challenges_phone_created',
        'telegram_link_challenges',
        ['phone_number', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_telegram_link_challenges_phone_created', table_name='telegram_link_challenges'
    )
    op.drop_table('telegram_link_challenges')
    op.drop_table('telegram_links')
