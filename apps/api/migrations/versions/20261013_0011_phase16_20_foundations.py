"""Phase 16–20 durable notifications and invite-only beta records.

Revision ID: 20261013_0011
Revises: 20261012_0010
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261013_0011'
down_revision: str | None = '20261012_0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def stamp_columns():
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
    ]

def upgrade():
    op.create_table(
        'user_notifications',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('recipient_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('actor_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT')),
        sa.Column('booking_id', sa.Uuid(), sa.ForeignKey('bookings.id', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('kind', sa.String(40), nullable=False),
        sa.Column('source_key', sa.String(160), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "kind IN ('booking_requested','booking_accepted','booking_declined',"
            "'booking_cancelled','payment_confirmed','chat_message')",
            name='ck_user_notification_kind',
        ),
        sa.UniqueConstraint('recipient_id', 'source_key', name='uq_notice_recipient_source'),
        *stamp_columns(),
    )
    op.create_index('ix_user_notifications_recipient_created', 'user_notifications',
                    ['recipient_id', 'created_at'])
    op.create_table(
        'beta_enrollments',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('invited_by_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.UniqueConstraint('user_id', name='uq_beta_enrollment_user'),
        *stamp_columns(),
    )
    op.create_table(
        'beta_feedback',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='RESTRICT'),
                  nullable=False),
        sa.Column('category', sa.String(32), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_beta_feedback_rating'),
        sa.CheckConstraint(
            "category IN ('bug','usability','safety','pricing','other')",
            name='ck_beta_feedback_category',
        ),
        *stamp_columns(),
    )

def downgrade():
    op.drop_table('beta_feedback')
    op.drop_table('beta_enrollments')
    op.drop_index('ix_user_notifications_recipient_created', table_name='user_notifications')
    op.drop_table('user_notifications')
