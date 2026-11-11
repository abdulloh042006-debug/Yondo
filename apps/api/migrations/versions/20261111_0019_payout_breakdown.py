"""companion payout breakdown: gross, commission, deductions (net stays in amount_minor)

Owner decision (docs/product-decisions.md): the platform commission is deducted from the
companion's side. Additive only: existing payouts keep their amount as gross and net, with
commission and deductions 0, which is what they were paid under the earlier rule.

Revision ID: 20261111_0019
Revises: 20261105_0018
Create Date: 2026-11-11 01:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261111_0019'
down_revision: str | None = '20261105_0018'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BREAKDOWN = (
    'gross_minor >= 0 AND commission_minor >= 0 AND deductions_minor >= 0 '
    'AND amount_minor = gross_minor - commission_minor - deductions_minor'
)


def upgrade() -> None:
    with op.batch_alter_table('companion_payouts') as batch:
        for column in ('gross_minor', 'commission_minor', 'deductions_minor'):
            batch.add_column(sa.Column(column, sa.BigInteger(), nullable=False, server_default='0'))
    op.execute('UPDATE companion_payouts SET gross_minor = amount_minor')
    with op.batch_alter_table('companion_payouts') as batch:
        batch.create_check_constraint('ck_companion_payout_breakdown', BREAKDOWN)


def downgrade() -> None:
    with op.batch_alter_table('companion_payouts') as batch:
        batch.drop_constraint('ck_companion_payout_breakdown', type_='check')
        for column in ('deductions_minor', 'commission_minor', 'gross_minor'):
            batch.drop_column(column)
