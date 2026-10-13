"""Transactional in-app gift test notifications; never external push/SMS."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.gifts.orders_models import GiftTestOrder
from yondo_api.models.user import AccountStatus, User, UserRole, UserRoleType
from yondo_api.notifications.models import UserNotification

GIFT_NOTICE_KINDS = frozenset({
    'gift_order_created', 'gift_test_paid', 'gift_preparing',
    'gift_out_for_delivery', 'gift_delivered', 'gift_cancelled',
})


async def enqueue_gift_notice(
    session: AsyncSession,
    order: GiftTestOrder,
    kind: str,
    *,
    actor_id: UUID | None = None,
) -> None:
    """Queue exactly one notice per recipient, order and state transition.

    Database uniqueness provides the final duplicate guard. Call before the
    order's transaction commits to avoid phantom notifications.
    """
    if kind not in GIFT_NOTICE_KINDS:
        raise ValueError('Unrecognized gift notification kind')

    if kind == 'gift_order_created':
        # The project owner handles order preparation/delivery via an admin role.
        recipients = set(await session.scalars(
            select(UserRole.user_id).join(User, User.id == UserRole.user_id).where(
                UserRole.role == UserRoleType.ADMIN,
                User.account_status == AccountStatus.ACTIVE,
            )
        ))
        recipients.discard(order.customer_id)
    else:
        recipients = {order.customer_id}

    for recipient_id in recipients:
        session.add(
            UserNotification(
                recipient_id=recipient_id,
                actor_id=actor_id,
                booking_id=None,
                gift_order_id=order.id,
                kind=kind,
                source_key=f'{kind}:{order.id}',
                details={
                    'gift_order_id': str(order.id),
                    'status': str(order.status),
                    'is_test_order': True,
                    'real_money_moved': False,
                },
                created_at=datetime.now(UTC),
            )
        )
