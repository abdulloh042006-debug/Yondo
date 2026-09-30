"""Companion supply domain, with independent application/content approval gates.

Revision ID: 20260930_0003
Revises: 20260929_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ExcludeConstraint

revision: str = '20260930_0003'
down_revision: str | None = '20260929_0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def approval_columns() -> list[sa.Column]:
    return [
        sa.Column('reviewed_at', sa.DateTime(timezone=True)),
        sa.Column('reviewed_by', sa.Uuid(), sa.ForeignKey('users.id')),
        sa.Column('review_note', sa.Text()),
    ]


def upgrade() -> None:
    op.create_table(
        'companion_applications',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column(
            'user_id',
            sa.Uuid(),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            unique=True,
        ),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True)),
        *approval_columns(),
        *timestamps(),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'rejected', 'withdrawn')",
            name='ck_companion_application_status',
        ),
    )
    op.create_table(
        'companion_profiles',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column(
            'application_id',
            sa.Uuid(),
            sa.ForeignKey('companion_applications.id', ondelete='CASCADE'),
            nullable=False,
            unique=True,
        ),
        sa.Column('display_name', sa.String(128), nullable=False),
        sa.Column('bio', sa.Text(), nullable=False),
        sa.Column('languages', sa.JSON(), nullable=False),
        sa.Column('interests', sa.JSON(), nullable=False),
        sa.Column('content_status', sa.String(16), nullable=False),
        sa.Column('activation_requested', sa.Boolean(), nullable=False),
        *approval_columns(),
        *timestamps(),
        sa.CheckConstraint(
            "content_status IN ('draft', 'pending', 'approved', 'rejected')",
            name='ck_companion_profile_content_status',
        ),
        sa.CheckConstraint(
            "NOT activation_requested OR content_status = 'approved'",
            name='ck_companion_profile_activation_content',
        ),
    )
    op.create_table(
        'companion_services',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column(
            'profile_id',
            sa.Uuid(),
            sa.ForeignKey('companion_profiles.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('service_code', sa.String(64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('price_minor', sa.BigInteger(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('unit_minutes', sa.Integer(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint('profile_id', 'service_code', name='uq_companion_service_code'),
        sa.CheckConstraint('price_minor >= 0', name='ck_companion_service_price'),
        sa.CheckConstraint('unit_minutes > 0', name='ck_companion_service_unit'),
        sa.CheckConstraint('length(currency) = 3', name='ck_companion_service_currency'),
    )
    op.create_index('ix_companion_services_profile_id', 'companion_services', ['profile_id'])
    op.create_table(
        'companion_photos',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column(
            'profile_id',
            sa.Uuid(),
            sa.ForeignKey('companion_profiles.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('storage_key', sa.String(512), unique=True, nullable=False),
        sa.Column('content_type', sa.String(64), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('caption', sa.String(512), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint('profile_id', 'position', name='uq_companion_photo_position'),
        sa.CheckConstraint('position IS NULL OR position >= 0', name='ck_companion_photo_position'),
        sa.CheckConstraint(
            'size_bytes > 0 AND width > 0 AND height > 0', name='ck_companion_photo_dimensions'
        ),
        sa.CheckConstraint(
            '(deleted_at IS NULL AND position IS NOT NULL) OR '
            '(deleted_at IS NOT NULL AND position IS NULL)',
            name='ck_companion_photo_deleted_position',
        ),
    )
    op.create_index('ix_companion_photos_profile_id', 'companion_photos', ['profile_id'])
    overlap_constraints = []
    if op.get_context().dialect.name == 'postgresql':
        # Required for UUID equality in the GiST exclusion index. Do not drop this shared
        # extension on downgrade; other domains may rely on it later.
        op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
        overlap_constraints.append(
            ExcludeConstraint(
                ('profile_id', '='),
                (sa.func.tstzrange(sa.column('starts_at'), sa.column('ends_at'), '[)'), '&&'),
                name='ex_companion_availability_overlap',
                using='gist',
            )
        )
    op.create_table(
        'companion_availability',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column(
            'profile_id',
            sa.Uuid(),
            sa.ForeignKey('companion_profiles.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timezone', sa.String(64), nullable=False),
        *timestamps(),
        *overlap_constraints,
        sa.CheckConstraint('ends_at > starts_at', name='ck_companion_availability_interval'),
    )
    op.create_index(
        'ix_companion_availability_profile_start',
        'companion_availability',
        ['profile_id', 'starts_at'],
    )


def downgrade() -> None:
    op.drop_table('companion_availability')
    op.drop_table('companion_photos')
    op.drop_table('companion_services')
    op.drop_table('companion_profiles')
    op.drop_table('companion_applications')
