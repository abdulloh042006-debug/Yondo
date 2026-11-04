"""trust safety and admin

Revision ID: 20261104_0010
Revises: 20261104_0009
Create Date: 2026-11-04 13:58:50.482211
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261104_0010'
down_revision: str | None = '20261104_0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'admin_audit_log',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('admin_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('target_type', sa.String(length=32), nullable=False),
        sa.Column('target_id', sa.Uuid(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_admin_audit_target',
        'admin_audit_log',
        ['target_type', 'target_id', 'created_at'],
        unique=False,
    )
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
        sa.ForeignKeyConstraint(
            ['reviewed_by'],
            ['users.id'],
        ),
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
    op.create_table(
        'trusted_contacts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('phone_number', sa.String(length=32), nullable=False),
        sa.Column('relationship', sa.String(length=64), nullable=False),
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
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_trusted_contacts_user_id'), 'trusted_contacts', ['user_id'], unique=False
    )
    op.create_table(
        'booking_shares',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('trusted_contact_id', sa.Uuid(), nullable=True),
        sa.Column('token_hash', sa.LargeBinary(length=32), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['trusted_contact_id'], ['trusted_contacts.id'], ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
    )
    op.create_index(
        op.f('ix_booking_shares_booking_id'), 'booking_shares', ['booking_id'], unique=False
    )
    op.create_table(
        'reports',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('reporter_id', sa.Uuid(), nullable=False),
        sa.Column('reported_user_id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=True),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
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
            "status IN ('open', 'in_review', 'resolved', 'dismissed')", name='ck_reports_status'
        ),
        sa.CheckConstraint('reporter_id <> reported_user_id', name='ck_reports_distinct'),
        sa.ForeignKeyConstraint(
            ['booking_id'],
            ['bookings.id'],
        ),
        sa.ForeignKeyConstraint(
            ['reported_user_id'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['reporter_id'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['resolved_by'],
            ['users.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_reports_reported_user', 'reports', ['reported_user_id'], unique=False)
    op.create_index('ix_reports_status_created', 'reports', ['status', 'created_at'], unique=False)
    op.create_table(
        'sos_alerts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('booking_id', sa.Uuid(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('handled_by', sa.Uuid(), nullable=True),
        sa.Column('handled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
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
            "status IN ('open', 'acknowledged', 'resolved')", name='ck_sos_alerts_status'
        ),
        sa.ForeignKeyConstraint(
            ['booking_id'],
            ['bookings.id'],
        ),
        sa.ForeignKeyConstraint(
            ['handled_by'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_sos_alerts_status_created', 'sos_alerts', ['status', 'created_at'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_sos_alerts_status_created', table_name='sos_alerts')
    op.drop_table('sos_alerts')
    op.drop_index('ix_reports_status_created', table_name='reports')
    op.drop_index('ix_reports_reported_user', table_name='reports')
    op.drop_table('reports')
    op.drop_index(op.f('ix_booking_shares_booking_id'), table_name='booking_shares')
    op.drop_table('booking_shares')
    op.drop_index(op.f('ix_trusted_contacts_user_id'), table_name='trusted_contacts')
    op.drop_table('trusted_contacts')
    op.drop_index('ix_identity_verifications_user_created', table_name='identity_verifications')
    op.drop_index('ix_identity_verifications_status', table_name='identity_verifications')
    op.drop_table('identity_verifications')
    op.drop_index('ix_admin_audit_target', table_name='admin_audit_log')
    op.drop_table('admin_audit_log')
