"""chat reviews disputes

Revision ID: 20261104_0009
Revises: 20261104_0008
Create Date: 2026-11-04 13:49:50.094305
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261104_0009'
down_revision: str | None = '20261104_0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=False),
        sa.Column('sender_id', sa.Uuid(), nullable=True),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(sender_id IS NULL) = (kind IN ('system', 'booking_details'))",
            name='ck_chat_messages_sender',
        ),
        sa.CheckConstraint(
            "kind IN ('text', 'image', 'meeting_point', 'booking_details', 'system')",
            name='ck_chat_messages_kind',
        ),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_chat_messages_booking_created',
        'chat_messages',
        ['booking_id', 'created_at'],
        unique=False,
    )
    op.create_table(
        'chat_read_states',
        sa.Column('booking_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('last_read_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('booking_id', 'user_id'),
    )
    op.create_table(
        'disputes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=False),
        sa.Column('opened_by', sa.Uuid(), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('previous_booking_status', sa.String(length=16), nullable=False),
        sa.Column('booking_outcome', sa.String(length=16), nullable=True),
        sa.Column('refund_minor', sa.BigInteger(), nullable=True),
        sa.Column('payout_minor', sa.BigInteger(), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.Uuid(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('open', 'under_review', 'resolved')", name='ck_disputes_status'
        ),
        sa.CheckConstraint('payout_minor IS NULL OR payout_minor >= 0', name='ck_disputes_payout'),
        sa.CheckConstraint('refund_minor IS NULL OR refund_minor >= 0', name='ck_disputes_refund'),
        sa.ForeignKeyConstraint(
            ['booking_id'],
            ['bookings.id'],
        ),
        sa.ForeignKeyConstraint(
            ['opened_by'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['resolved_by'],
            ['users.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_id'),
    )
    op.create_index('ix_disputes_status', 'disputes', ['status'], unique=False)
    op.create_table(
        'reviews',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=False),
        sa.Column('author_id', sa.Uuid(), nullable=False),
        sa.Column('subject_id', sa.Uuid(), nullable=False),
        sa.Column('direction', sa.String(length=32), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('criteria', sa.JSON(), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('hidden_reason', sa.Text(), nullable=True),
        sa.Column('hidden_by', sa.Uuid(), nullable=True),
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
            "direction IN ('customer_to_companion', 'companion_to_customer')",
            name='ck_reviews_direction',
        ),
        sa.CheckConstraint("status IN ('published', 'hidden')", name='ck_reviews_status'),
        sa.CheckConstraint('author_id <> subject_id', name='ck_reviews_distinct'),
        sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_reviews_rating'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['hidden_by'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(['subject_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_id', 'author_id', name='uq_reviews_booking_author'),
    )
    op.create_index(
        'ix_reviews_subject_direction',
        'reviews',
        ['subject_id', 'direction', 'status'],
        unique=False,
    )
    op.create_table(
        'dispute_evidence',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('dispute_id', sa.Uuid(), nullable=False),
        sa.Column('uploaded_by', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dispute_id'], ['disputes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['uploaded_by'],
            ['users.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_dispute_evidence_dispute_id'), 'dispute_evidence', ['dispute_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_dispute_evidence_dispute_id'), table_name='dispute_evidence')
    op.drop_table('dispute_evidence')
    op.drop_index('ix_reviews_subject_direction', table_name='reviews')
    op.drop_table('reviews')
    op.drop_index('ix_disputes_status', table_name='disputes')
    op.drop_table('disputes')
    op.drop_table('chat_read_states')
    op.drop_index('ix_chat_messages_booking_created', table_name='chat_messages')
    op.drop_table('chat_messages')
