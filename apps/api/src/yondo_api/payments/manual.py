"""Manual card-transfer payments for the beta (owner decision 2026-11-05).

The customer moves the money in their own bank app to a card the owner configured and
writes the payment's reference in the transfer comment; an admin checks the bank and
presses "received". That goes through the same idempotent event path as a provider
webhook, so the booking becomes `confirmed` exactly as with TezCheck. The app never moves,
holds or refunds money, and invents no amount: booking price plus the configured fee.

Card numbers come only from the host's environment (`YONDO_MANUAL_PAYMENT_CARDS`): the
repository is public. Only the customer who has to pay sees them.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from yondo_api.admin.models import AdminAuditEvent
from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.expiry import is_stale
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.companions.dependencies import Admin, Principal, Session
from yondo_api.companions.models import CompanionApplication, CompanionProfile
from yondo_api.payments.models import Payment, PaymentEventReceipt, PaymentStatus
from yondo_api.payments.provider import CheckoutSession, PaymentEvent
from yondo_api.payments.router import MANUAL_REFERENCE_PREFIX as REFERENCE_PREFIX
from yondo_api.payments.router import apply_verified_event

# No 0/O, 1/I/L: the reference is typed by hand into a bank transfer comment.
_ALPHABET = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'


def new_reference() -> str:
    chars = ''.join(secrets.choice(_ALPHABET) for _ in range(8))
    return f'{REFERENCE_PREFIX}{chars[:4]}-{chars[4:]}'


class ManualTransferPaymentProvider:
    """Checkout = a page of the web app with the cards, the exact amount and the reference."""

    def __init__(self, public_web_url: str) -> None:
        if not public_web_url.startswith('https://'):
            raise ValueError('The manual payment page must be https (checkout URLs must be)')
        self.public_web_url = public_web_url.rstrip('/')

    async def create_checkout(
        self, *, idempotency_key: str, amount_minor: int, currency: str, description: str
    ) -> CheckoutSession:
        reference = new_reference()
        return CheckoutSession(
            provider_reference=reference, checkout_url=f'{self.public_web_url}/pay/{reference}'
        )

    async def verify_event(self, body: bytes, headers: dict[str, str]) -> PaymentEvent:
        # Manual payments are confirmed by an admin, never by an inbound webhook.
        raise ValueError('manual payments have no webhook')


class ManualCardRead(BaseModel):
    label: str
    number: str
    holder: str


ManualState = Literal['open', 'confirmed', 'refund_required', 'closed']


class ManualPaymentRead(BaseModel):
    reference: str
    booking_id: UUID
    status: str
    amount_minor: int
    currency: str
    created_at: datetime
    cards: list[ManualCardRead] = Field(description='Only while the state is "open".')
    state: ManualState = Field(
        description=(
            'open: transfer now; confirmed: money recorded and booking confirmed; '
            'refund_required: money recorded for a cancelled/expired booking; closed: do not pay.'
        )
    )


class AdminManualPaymentRead(BaseModel):
    reference: str
    payment_id: UUID
    booking_id: UUID
    customer_id: UUID
    status: str
    booking_status: str
    amount_minor: int
    currency: str
    refund_required: bool
    created_at: datetime


router = APIRouter(prefix='/payments/manual', tags=['payments'])
admin_router = APIRouter(prefix='/admin/payments/manual', tags=['admin payments'])


def _cards(request: Request) -> list[ManualCardRead]:
    return [
        ManualCardRead(label=c.label, number=c.number, holder=c.holder)
        for c in request.app.state.settings.manual_payment_cards
    ]


async def _manual_payment(session, reference: str) -> Payment:
    payment = None
    if reference.startswith(REFERENCE_PREFIX):
        payment = await session.scalar(
            select(Payment).where(Payment.provider_reference == reference)
        )
    if payment is None:
        raise ApplicationError('payment_not_found', 'Payment not found', 404)
    return payment


def _state(payment: Payment, booking: Booking) -> str:
    if payment.status == PaymentStatus.SUCCEEDED:
        return 'refund_required' if payment.refund_required else 'confirmed'
    # Money is asked for only while the booking can still be paid (accepted and not overdue);
    # otherwise a transfer would have to be refunded by hand.
    if (
        payment.status == PaymentStatus.PENDING
        and booking.status == BookingStatus.ACCEPTED
        and not is_stale(booking)
    ):
        return 'open'
    return 'closed'


@router.get('/{reference}', response_model=ManualPaymentRead)
async def manual_payment(reference: str, request: Request, principal: Principal, session: Session):
    """Transfer instructions, for the customer who has to pay (anyone else gets 404)."""
    payment = await _manual_payment(session, reference)
    if payment.customer_id != principal.user.id:
        raise ApplicationError('payment_not_found', 'Payment not found', 404)
    booking = await session.get(Booking, payment.booking_id)
    state = _state(payment, booking)
    return ManualPaymentRead(
        reference=reference,
        booking_id=payment.booking_id,
        status=payment.status,
        amount_minor=payment.amount_minor,
        currency=payment.currency,
        created_at=payment.created_at,
        cards=_cards(request) if state == 'open' else [],
        state=state,
    )


def _admin_read(payment: Payment, booking_status: str) -> AdminManualPaymentRead:
    return AdminManualPaymentRead(
        reference=payment.provider_reference or '',
        payment_id=payment.id,
        booking_id=payment.booking_id,
        customer_id=payment.customer_id,
        status=payment.status,
        booking_status=booking_status,
        amount_minor=payment.amount_minor,
        currency=payment.currency,
        refund_required=payment.refund_required,
        created_at=payment.created_at,
    )


@admin_router.get('', response_model=list[AdminManualPaymentRead])
async def manual_queue(
    admin: Admin,
    session: Session,
    status: Literal['pending', 'succeeded'] = 'pending',
    limit: int = Query(default=50, ge=1, le=100),
):
    """Open manual transfers to look for in the bank; oldest first so nothing waits forever."""
    rows = await session.execute(
        select(Payment, Booking.status)
        .join(Booking, Booking.id == Payment.booking_id)
        .where(
            Payment.provider_reference.like(f'{REFERENCE_PREFIX}%'),
            Payment.status == PaymentStatus(status),
        )
        .order_by(Payment.created_at, Payment.id)
        .limit(limit)
    )
    return [_admin_read(payment, booking_status) for payment, booking_status in rows]


@admin_router.post('/{reference}/received', response_model=AdminManualPaymentRead)
async def mark_received(reference: str, request: Request, admin: Admin, session: Session):
    """The admin saw the exact amount with this reference arrive on a configured card."""
    payment = await _manual_payment(session, reference)
    if payment.status not in {PaymentStatus.PENDING, PaymentStatus.SUCCEEDED}:
        raise ApplicationError('payment_not_pending', 'Payment is not waiting for a transfer', 409)
    payment_id, customer_id = payment.id, payment.customer_id
    # Same lock order as the webhook path (booking, then payment): concurrent presses queue here.
    booking = await session.scalar(
        select(Booking)
        .where(Booking.id == payment.booking_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    companion_id = await session.scalar(
        select(CompanionApplication.user_id)
        .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
        .where(CompanionProfile.id == booking.profile_id)
    )
    if admin.id in {customer_id, companion_id}:
        raise ApplicationError('self_approval_forbidden', 'Self approval is not permitted', 403)
    if is_stale(booking):
        # The start time passed: expire it exactly as the hourly sweep would, so late money is
        # flagged for a refund instead of confirming a booking that can no longer happen.
        booking.status = BookingStatus.EXPIRED
    event_id = f'manual:{payment_id}:received'
    already = await session.scalar(
        select(PaymentEventReceipt.id).where(PaymentEventReceipt.provider_event_id == event_id)
    )
    if already is None:
        session.add(
            AdminAuditEvent(
                admin_id=admin.id,
                target_id=customer_id,
                action='manual_payment_received',
                reason=f'payment:{payment_id}',  # no free text: audit rows outlive erasure
            )
        )
    await session.flush()
    # One event id per payment: pressing twice (or two admins at once) applies it once.
    await apply_verified_event(request, session, PaymentEvent(event_id, reference, 'succeeded'))
    refreshed = await session.get(Payment, payment_id, populate_existing=True)
    booking = await session.get(Booking, refreshed.booking_id, populate_existing=True)
    return _admin_read(refreshed, booking.status)
