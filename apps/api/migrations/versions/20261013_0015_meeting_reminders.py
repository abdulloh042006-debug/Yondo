"""Allow durable 24-hour and 1-hour meeting reminders.

Revision ID: 20261013_0015
Revises: 20261013_0014
"""

from collections.abc import Sequence

from alembic import op

revision: str = '20261013_0015'
down_revision: str | None = '20261013_0014'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_KINDS = (
    "kind IN ('booking_requested','booking_accepted','booking_declined',"
    "'booking_cancelled','payment_confirmed','chat_message',"
    "'review_reminder','gift_order_created','gift_test_paid','gift_preparing',"
    "'gift_out_for_delivery','gift_delivered','gift_cancelled')"
)
NEW_KINDS = (
    "kind IN ('booking_requested','booking_accepted','booking_declined',"
    "'booking_cancelled','payment_confirmed','chat_message',"
    "'review_reminder','gift_order_created','gift_test_paid','gift_preparing',"
    "'gift_out_for_delivery','gift_delivered','gift_cancelled',"
    "'meeting_reminder_24h','meeting_reminder_1h')"
)


def upgrade() -> None:
    with op.batch_alter_table('user_notifications') as batch:
        batch.drop_constraint('ck_user_notification_kind', type_='check')
        batch.create_check_constraint('ck_user_notification_kind', NEW_KINDS)


def downgrade() -> None:
    # The older notification check constraint does not permit reminders.
    op.execute(
        "DELETE FROM user_notifications WHERE "
        "kind IN ('meeting_reminder_24h', 'meeting_reminder_1h')"
    )
    with op.batch_alter_table('user_notifications') as batch:
        batch.drop_constraint('ck_user_notification_kind', type_='check')
        batch.create_check_constraint('ck_user_notification_kind', OLD_KINDS)
