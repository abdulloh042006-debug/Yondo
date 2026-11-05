"""Unify booking and manual gift test notifications.

Revision ID: 20261013_0014
Revises: 20261013_0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '20261013_0014'
down_revision: str | None = '20261013_0013'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_KINDS = (
    "kind IN ('booking_requested','booking_accepted','booking_declined',"
    "'booking_cancelled','payment_confirmed','chat_message')"
)
NEW_KINDS = (
    "kind IN ('booking_requested','booking_accepted','booking_declined',"
    "'booking_cancelled','payment_confirmed','chat_message','review_reminder',"
    "'gift_order_created','gift_test_paid','gift_preparing','gift_out_for_delivery',"
    "'gift_delivered','gift_cancelled')"
)
SINGLE_RESOURCE = (
    '(booking_id IS NOT NULL AND gift_order_id IS NULL) OR '
    '(booking_id IS NULL AND gift_order_id IS NOT NULL)'
)


def upgrade() -> None:
    # batch mode recreates the notification table on SQLite and alters in place
    # on PostgreSQL. Existing booking notices remain intact.
    with op.batch_alter_table('user_notifications') as batch:
        batch.drop_constraint('ck_user_notification_kind', type_='check')
        batch.alter_column('booking_id', existing_type=sa.Uuid(), nullable=True)
        batch.add_column(sa.Column('gift_order_id', sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            'fk_user_notifications_gift_order_id', 'gift_test_orders',
            ['gift_order_id'], ['id'], ondelete='RESTRICT',
        )
        batch.create_check_constraint('ck_user_notification_kind', NEW_KINDS)
        batch.create_check_constraint('ck_notification_single_resource', SINGLE_RESOURCE)


def downgrade() -> None:
    # Gift-only test notifications have no booking FK and cannot be represented
    # by the older schema. Delete only those test-domain rows before reverting.
    op.execute('DELETE FROM user_notifications WHERE gift_order_id IS NOT NULL')
    with op.batch_alter_table('user_notifications') as batch:
        batch.drop_constraint('ck_notification_single_resource', type_='check')
        batch.drop_constraint('ck_user_notification_kind', type_='check')
        batch.drop_constraint('fk_user_notifications_gift_order_id', type_='foreignkey')
        batch.drop_column('gift_order_id')
        batch.alter_column('booking_id', existing_type=sa.Uuid(), nullable=False)
        batch.create_check_constraint('ck_user_notification_kind', OLD_KINDS)
