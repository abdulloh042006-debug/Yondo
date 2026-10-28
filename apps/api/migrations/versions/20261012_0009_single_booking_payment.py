"""Restrict bookings to one provider payment attempt.

A pre-existing database with multiple payment rows for the same booking will
refuse this migration instead of silently discarding financial records.
"""

from collections.abc import Sequence

from alembic import op

revision: str = '20261012_0009'
down_revision: str | None = '20261009_0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index('uq_payment_single_booking', 'payments', ['booking_id'], unique=True)


def downgrade() -> None:
    op.drop_index('uq_payment_single_booking', table_name='payments')
