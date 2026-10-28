"""Admin safety incident acknowledgements.

Revision ID: 20261013_0012
Revises: 20261013_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261013_0012'
down_revision: str | None = '20261013_0011'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'safety_acknowledgements',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column(
            'report_id', sa.Uuid(),
            sa.ForeignKey('safety_reports.id', ondelete='RESTRICT'), nullable=True,
        ),
        sa.Column(
            'alert_id', sa.Uuid(),
            sa.ForeignKey('safety_alerts.id', ondelete='RESTRICT'), nullable=True,
        ),
        sa.Column(
            'admin_id', sa.Uuid(),
            sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False,
        ),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.CheckConstraint(
            '(report_id IS NULL AND alert_id IS NOT NULL) OR '
            '(report_id IS NOT NULL AND alert_id IS NULL)',
            name='ck_safety_ack_single_subject',
        ),
        sa.UniqueConstraint('report_id', name='uq_safety_ack_report'),
        sa.UniqueConstraint('alert_id', name='uq_safety_ack_alert'),
    )


def downgrade() -> None:
    op.drop_table('safety_acknowledgements')
