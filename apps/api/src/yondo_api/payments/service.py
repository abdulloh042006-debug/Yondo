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


def companion_commission(payment: Payment) -> int:
    """Commission deducted from the companion's payout for this payment.

    Owner decision (docs/product-decisions.md): the commission is deducted from the companion's
    side and the customer pays only the service amount (amount_minor == subtotal_minor). Payments
    created under the earlier rule charged the fee to the customer on top
    (amount_minor == subtotal_minor + platform_fee_minor); for those the commission was already
    paid by the customer, so nothing is deducted again.
    """
    if payment.amount_minor == payment.subtotal_minor:
        return payment.platform_fee_minor
    return 0


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
    gross = payment.subtotal_minor
    commission = companion_commission(payment)
    deductions = 0  # not defined by the owner yet (docs/product-decisions.md)
    payout = CompanionPayout(
        booking_id=booking.id,
        companion_user_id=companion.id,
        gross_minor=gross,
        commission_minor=commission,
        deductions_minor=deductions,
        amount_minor=gross - commission - deductions,
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
