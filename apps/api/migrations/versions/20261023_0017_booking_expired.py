"""Booking status 'expired': start time passed while still pending/accepted; slot released.

Revision ID: 20261023_0017
Revises: 20261023_0016
"""

from collections.abc import Sequence

from alembic import op

revision: str = '20261023_0017'
down_revision: str | None = '20261023_0016'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = (
    "status IN ('pending', 'accepted', 'confirmed', 'active', 'completed', "
    "'cancelled', 'no-show', 'disputed')"
)
NEW = (
    "status IN ('pending', 'accepted', 'confirmed', 'active', 'completed', "
    "'cancelled', 'no-show', 'disputed', 'expired')"
)


def upgrade() -> None:
    # The GiST exclusion only covers reserving statuses, so 'expired' never blocks a slot.
    with op.batch_alter_table('bookings') as batch:
        batch.drop_constraint('ck_booking_status', type_='check')
        batch.create_check_constraint('ck_booking_status', NEW)


def downgrade() -> None:
    # The old schema has no 'expired'; such bookings did not take place, closest state is cancelled.
    op.execute("UPDATE bookings SET status = 'cancelled' WHERE status = 'expired'")
    with op.batch_alter_table('bookings') as batch:
        batch.drop_constraint('ck_booking_status', type_='check')
        batch.create_check_constraint('ck_booking_status', OLD)
