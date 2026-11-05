"""Add private booking chat messages, read cursors, and one-use socket tickets."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261009_0008'
down_revision: str | None = '20261009_0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=False),
        sa.Column('sender_id', sa.Uuid(), nullable=True),
        sa.Column('kind', sa.String(24), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('system_code', sa.String(64), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "kind IN ('text', 'meeting_point', 'booking_details', 'system')",
            name='ck_chat_message_kind',
        ),
        sa.CheckConstraint(
            "(kind = 'system' AND sender_id IS NULL AND system_code IS NOT NULL) "
            "OR (kind != 'system' AND sender_id IS NOT NULL AND system_code IS NULL)",
            name='ck_chat_message_sender',
        ),
        sa.CheckConstraint(
            "(kind = 'booking_details' AND payload IS NOT NULL) "
            "OR (kind != 'booking_details' AND body IS NOT NULL)",
            name='ck_chat_message_content',
        ),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_chat_messages_booking_created', 'chat_messages', ['booking_id', 'created_at', 'id']
    )

    op.create_table(
        'chat_read_cursors',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('last_read_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_id', 'user_id', name='uq_chat_read_cursor'),
    )

    op.create_table(
        'chat_access_tickets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_chat_ticket_hash'),
    )


def downgrade() -> None:
    op.drop_table('chat_access_tickets')
    op.drop_table('chat_read_cursors')
    op.drop_index('ix_chat_messages_booking_created', table_name='chat_messages')
    op.drop_table('chat_messages')
