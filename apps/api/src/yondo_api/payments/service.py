from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings import service as bookings
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.config import Settings
from yondo_api.core.money import BPS_DENOMINATOR, apply_bps
from yondo_api.core.time import as_utc, utc_now
from yondo_api.models.user import User
from yondo_api.notifications.service import notify
from yondo_api.payments.models import (
    PAID_STATUSES,
    Payment,
    PaymentEvent,
    PaymentStatus,
    Payout,
    PayoutStatus,
    Refund,
    RefundStatus,
)
from yondo_api.payments.providers import PaymentProvider, WebhookEvent

logger = structlog.get_logger(__name__)


def provider_for(app_state: Any, name: str | None = None) -> PaymentProvider:
    settings: Settings = app_state.settings
    selected = name or settings.effective_payment_provider
    provider = app_state.payment_providers.get(selected)
    if provider is None:
        raise ApplicationError('payment_unavailable', 'Payments are not available', 503)
    return provider


async def lock_payment(session: AsyncSession, **criteria: Any) -> Payment | None:
    query = select(Payment).with_for_update().execution_options(populate_existing=True)
    for key, value in criteria.items():
        query = query.where(getattr(Payment, key) == value)
    return await session.scalar(query)


async def checkout_booking(
    session: AsyncSession,
    app_state: Any,
    customer: User,
    booking_id: UUID,
    idempotency_key: str,
) -> Payment:
    """Start (or resume) payment for an accepted booking. Idempotent per key and booking."""
    existing = await session.scalar(
        select(Payment).where(
            Payment.payer_id == customer.id, Payment.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        if existing.booking_id != booking_id:
            raise ApplicationError(
                'idempotency_key_reused', 'Idempotency key was used for another checkout', 409
            )
        return existing
    booking, role = await bookings.participant_booking(session, booking_id, customer, lock=True)
    if role != 'customer':
        raise bookings.not_found()
    now = utc_now()
    if bookings.expire_if_due(session, booking, now):
        await bookings.save(session)
        raise ApplicationError('booking_expired', 'The payment window has expired', 409)
    if booking.status != BookingStatus.ACCEPTED:
        raise ApplicationError('booking_not_payable', 'This booking cannot be paid now', 409)
    live = await session.scalar(
        select(Payment).where(
            Payment.booking_id == booking.id,
            Payment.status.in_((PaymentStatus.PENDING, PaymentStatus.SUCCEEDED)),
        )
    )
    if live is not None:
        if live.status == PaymentStatus.SUCCEEDED:
            raise ApplicationError('already_paid', 'This booking is already paid', 409)
        return live
    breakdown: dict[str, Any] = {
        'service_amount_minor': booking.service_amount_minor,
        'platform_fee_minor': booking.platform_fee_minor,
        'gifts_subtotal_minor': 0,
        'delivery_fee_minor': 0,
        'gift_platform_fee_minor': 0,
    }
    amount = booking.total_minor
    provider = provider_for(app_state)
    payment = Payment(
        payer_id=customer.id,
        booking_id=booking.id,
        provider=provider.name,
        idempotency_key=idempotency_key,
        status=PaymentStatus.PENDING,
        currency=booking.currency,
        amount_minor=amount,
        refunded_minor=0,
        breakdown=breakdown,
        expires_at=booking.payment_due_at,
    )
    session.add(payment)
    await session.flush()
    return await start_provider_checkout(session, provider, payment, f'Yondo booking {booking.id}')


async def start_provider_checkout(
    session: AsyncSession, provider: PaymentProvider, payment: Payment, description: str
) -> Payment:
    try:
        checkout = await provider.create_checkout(
            str(payment.id), payment.amount_minor, payment.currency, description
        )
    except ApplicationError:
        await session.rollback()
        raise
    except Exception as exc:
        await session.rollback()
        logger.exception('payment_checkout_failed', provider=provider.name)
        raise ApplicationError(
            'payment_unavailable', 'Payment provider is unavailable', 503
        ) from exc
    payment.provider_payment_id = checkout.provider_payment_id
    payment.checkout_url = checkout.checkout_url
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ApplicationError(
            'payment_in_progress', 'A payment for this order is already in progress', 409
        ) from exc
    return payment


async def handle_webhook(
    session: AsyncSession, provider: PaymentProvider, event: WebhookEvent, payload: dict[str, Any]
) -> str:
    """Apply a verified provider event exactly once. Returns the recorded outcome."""
    payment = await lock_payment(
        session, provider=provider.name, provider_payment_id=event.provider_payment_id
    )
    outcome = 'ignored'
    if payment is None:
        outcome = 'unknown_payment'
        logger.warning('payment_webhook_unknown_payment', provider=provider.name)
    elif event.amount_minor != payment.amount_minor or event.currency != payment.currency:
        outcome = 'amount_mismatch'
        logger.error('payment_amount_mismatch', payment_id=str(payment.id))
        if payment.status == PaymentStatus.PENDING:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = 'amount_mismatch'
    elif event.status == 'failed':
        if payment.status == PaymentStatus.PENDING:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = (event.failure_reason or 'declined')[:200]
            notify(
                session,
                payment.payer_id,
                'payment_failed',
                "To'lov amalga oshmadi",
                "To'lovni qayta urinib ko'ring.",
                {'payment_id': payment.id, 'booking_id': payment.booking_id or ''},
            )
            outcome = 'failed'
    elif payment.status in PAID_STATUSES:
        outcome = 'duplicate'
    else:
        outcome = await capture(session, payment)
    session.add(
        PaymentEvent(
            provider=provider.name,
            event_id=event.event_id,
            payment_id=payment.id if payment else None,
            outcome=outcome,
            payload=payload,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        # The same provider event was already processed (concurrent redelivery).
        await session.rollback()
        return 'duplicate'
    return outcome


async def capture(session: AsyncSession, payment: Payment) -> str:
    """Record captured money and confirm the order, refunding money for dead orders."""
    now = utc_now()
    was_cancelled = payment.status in {PaymentStatus.CANCELLED, PaymentStatus.FAILED}
    payment.status = PaymentStatus.SUCCEEDED
    payment.paid_at = now
    payment.failure_reason = None
    notify(
        session,
        payment.payer_id,
        'payment_succeeded',
        "To'lov qabul qilindi",
        f"{payment.amount_minor} {payment.currency} to'lov qabul qilindi.",
        {'payment_id': payment.id, 'booking_id': payment.booking_id or ''},
    )
    booking = await bookings.lock_booking(session, payment.booking_id)
    other_paid = await session.scalar(
        select(Payment.id).where(
            Payment.booking_id == booking.id,
            Payment.id != payment.id,
            Payment.status.in_(PAID_STATUSES),
        )
    )
    if booking.status != BookingStatus.ACCEPTED or other_paid is not None or was_cancelled:
        # Late or duplicate money: return it in full automatically.
        queue_refund(session, payment, payment.amount_minor, 'order_not_payable')
        return 'refunded_unpayable'
    booking.confirmed_at = now
    booking.payment_due_at = None
    bookings.transition(
        session,
        booking,
        BookingStatus.CONFIRMED,
        'payment_confirmed',
        actor_id=None,
        data={'payment_id': str(payment.id)},
    )
    session.add(
        Payout(
            beneficiary_id=booking.companion_id,
            booking_id=booking.id,
            amount_minor=booking.companion_payout_minor,
            currency=booking.currency,
            status=PayoutStatus.HELD,
        )
    )
    when = bookings.fmt_local(booking.starts_at, booking.timezone)
    for party, title in (
        (booking.customer_id, 'Bron tasdiqlandi'),
        (booking.companion_id, "Bron to'landi va tasdiqlandi"),
    ):
        bookings.booking_notice(
            session, booking, party, 'booking_confirmed', title, f'Uchrashuv vaqti: {when}.'
        )
    return 'captured'


def queue_refund(session: AsyncSession, payment: Payment, amount_minor: int, reason: str) -> None:
    """Record a refund for the outbox processor; never exceeds the refundable balance."""
    refundable = payment.amount_minor - payment.refunded_minor
    amount = min(amount_minor, refundable)
    if amount <= 0:
        return
    payment.refunded_minor += amount
    payment.status = (
        PaymentStatus.REFUNDED
        if payment.refunded_minor == payment.amount_minor
        else PaymentStatus.PARTIALLY_REFUNDED
    )
    session.add(
        Refund(
            payment_id=payment.id, amount_minor=amount, status=RefundStatus.PENDING, reason=reason
        )
    )
    notify(
        session,
        payment.payer_id,
        'refund_initiated',
        'Pul qaytarilmoqda',
        f'{amount} {payment.currency} qaytarish jarayoni boshlandi.',
        {'payment_id': payment.id},
    )


async def booking_payment(session: AsyncSession, booking_id: UUID) -> Payment | None:
    return await session.scalar(
        select(Payment)
        .where(Payment.booking_id == booking_id, Payment.status.in_(PAID_STATUSES))
        .with_for_update()
        .execution_options(populate_existing=True)
    )


async def booking_payout(session: AsyncSession, booking_id: UUID) -> Payout | None:
    return await session.scalar(
        select(Payout)
        .where(Payout.booking_id == booking_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


async def settle_cancellation(session: AsyncSession, booking: Booking, refund_bps: int) -> None:
    """Refund the customer's share and adjust the companion payout after a paid cancellation."""
    payment = await booking_payment(session, booking.id)
    if payment is not None and booking.refund_minor > 0:
        queue_refund(session, payment, booking.refund_minor, booking.cancellation_reason or '')
    payout = await booking_payout(session, booking.id)
    if payout is None or payout.status == PayoutStatus.PAID:
        return
    retained_bps = BPS_DENOMINATOR - refund_bps
    payout.amount_minor = apply_bps(booking.companion_payout_minor, retained_bps)
    if payout.amount_minor == 0:
        payout.status = PayoutStatus.CANCELLED
    else:
        # Late-cancellation compensation for the companion's reserved time.
        payout.status = PayoutStatus.SCHEDULED
        payout.available_at = utc_now()


async def schedule_payout(session: AsyncSession, booking: Booking, settings: Settings) -> None:
    """Completed booking: release the companion payout after the configured hold."""
    payout = await booking_payout(session, booking.id)
    if payout is None or payout.status != PayoutStatus.HELD:
        return
    payout.status = PayoutStatus.SCHEDULED
    payout.available_at = utc_now() + timedelta(hours=settings.payout_release_delay_hours)


async def hold_payout(session: AsyncSession, booking_id: UUID, note: str) -> None:
    """Disputes hold the payout until an administrator decides (TZ §27)."""
    payout = await booking_payout(session, booking_id)
    if payout is not None and payout.status in {PayoutStatus.HELD, PayoutStatus.SCHEDULED}:
        payout.status = PayoutStatus.HELD
        payout.available_at = None
        payout.note = note


async def process_refunds(session: AsyncSession, app_state: Any, limit: int = 50) -> int:
    """Outbox processor: send pending refunds to their provider."""
    ids = list(
        await session.scalars(
            select(Refund.id)
            .where(Refund.status == RefundStatus.PENDING, Refund.attempts < 10)
            .order_by(Refund.created_at)
            .limit(limit)
        )
    )
    done = 0
    for refund_id in ids:
        refund = await session.scalar(
            select(Refund)
            .where(Refund.id == refund_id, Refund.status == RefundStatus.PENDING)
            .with_for_update(skip_locked=True)
        )
        if refund is None:
            continue
        payment = await session.get(Payment, refund.payment_id)
        refund.attempts += 1
        try:
            provider = provider_for(app_state, payment.provider)
            result = await provider.refund(
                payment.provider_payment_id or '', str(refund.id), refund.amount_minor
            )
        except Exception:
            logger.exception('refund_failed', refund_id=str(refund.id))
            await session.commit()
            continue
        refund.provider_refund_id = result.provider_refund_id
        if result.succeeded:
            refund.status = RefundStatus.SUCCEEDED
            refund.completed_at = utc_now()
            notify(
                session,
                payment.payer_id,
                'refund_completed',
                'Pul qaytarildi',
                f'{refund.amount_minor} {payment.currency} qaytarildi.',
                {'payment_id': payment.id},
            )
            done += 1
        await session.commit()
    return done


async def expire_pending_payments(session: AsyncSession, now: datetime | None = None) -> int:
    now = now or utc_now()
    unpayable_bookings = select(Booking.id).where(Booking.status != BookingStatus.ACCEPTED)
    payments = list(
        await session.scalars(
            select(Payment)
            .where(
                Payment.status == PaymentStatus.PENDING,
                or_(Payment.expires_at <= now, Payment.booking_id.in_(unpayable_bookings)),
            )
            .with_for_update(skip_locked=True)
        )
    )
    for payment in payments:
        payment.status = PaymentStatus.CANCELLED
        payment.failure_reason = 'expired'
    await session.commit()
    return len(payments)


def is_due(payout: Payout, now: datetime) -> bool:
    return (
        payout.status == PayoutStatus.SCHEDULED
        and payout.available_at is not None
        and as_utc(payout.available_at) <= now
    )
