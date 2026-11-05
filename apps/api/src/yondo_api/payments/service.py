from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.models.user import User
from yondo_api.payments.models import (
    CompanionPayout,
    Payment,
    PaymentEventReceipt,
    PaymentStatus,
)


def platform_fee(subtotal_minor: int, fee_bps: int) -> int:
    """Calculate minor units, rounding half up to the nearest minor unit."""
    return (subtotal_minor * fee_bps + 5_000) // 10_000


async def release_payout_for_completed_booking(
    session: AsyncSession, booking: Booking, companion: User
) -> CompanionPayout | None:
    """Create a held payout from a successful payment after meeting completion."""
    if booking.status != BookingStatus.COMPLETED:
        return None
    payment = await session.scalar(
        select(Payment)
        .where(Payment.booking_id == booking.id, Payment.status == PaymentStatus.SUCCEEDED)
        .order_by(Payment.created_at)
    )
    if payment is None:
        return None
    existing = await session.scalar(
        select(CompanionPayout).where(CompanionPayout.booking_id == booking.id)
    )
    if existing is not None:
        return existing
    payout = CompanionPayout(
        booking_id=booking.id,
        companion_user_id=companion.id,
        amount_minor=payment.subtotal_minor,
        currency=payment.currency,
        status='ready',
        released_at=datetime.now(UTC),
    )
    session.add(payout)
    await session.flush()
    return payout


async def apply_payment_event(
    session: AsyncSession,
    payment: Payment,
    booking: Booking,
    event_id: str,
    event_status: str,
) -> bool:
    """Apply one verified, idempotent provider event. Return False for duplicates."""
    if await session.scalar(
        select(PaymentEventReceipt.id).where(PaymentEventReceipt.provider_event_id == event_id)
    ):
        return False
    session.add(
        PaymentEventReceipt(payment_id=payment.id, provider_event_id=event_id, status=event_status)
    )
    if event_status == 'succeeded' and payment.status != PaymentStatus.SUCCEEDED:
        payment.status = PaymentStatus.SUCCEEDED
        if booking.status == BookingStatus.ACCEPTED:
            booking.status = BookingStatus.CONFIRMED
        else:
            # A late success after cancellation must remain visible for refund handling.
            payment.refund_required = True
    elif event_status == 'failed' and payment.status != PaymentStatus.SUCCEEDED:
        payment.status = PaymentStatus.FAILED
    payment.updated_at = datetime.now(UTC)
    await session.flush()
    return True
