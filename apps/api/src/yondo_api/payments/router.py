from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Header, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.bookings.router import _participant
from yondo_api.chat.service import append_system_message, publish
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.payments.models import Payment, PaymentEventReceipt, PaymentStatus
from yondo_api.payments.provider import PaymentEvent
from yondo_api.payments.schemas import PaymentResponse
from yondo_api.payments.service import apply_payment_event, platform_fee

router = APIRouter(prefix='/payments', tags=['payments'])


@router.post('/bookings/{booking_id}', response_model=PaymentResponse, status_code=201)
async def create_checkout(
    booking_id: UUID,
    request: Request,
    principal: Principal,
    session: Session,
    idempotency_key: str = Header(alias='Idempotency-Key', min_length=8, max_length=128),
):
    booking = await session.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    is_customer, _ = await _participant(session, booking, principal.user.id)
    customer_id = principal.user.id
    if not is_customer:
        raise ApplicationError('customer_role_required', 'Only the customer can pay', 403)
    if booking.status != BookingStatus.ACCEPTED:
        raise ApplicationError('booking_not_payable', 'Only an accepted booking can be paid', 409)
    existing = await session.scalar(
        select(Payment).where(
            Payment.customer_id == customer_id,
            Payment.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.booking_id != booking.id:
            raise ApplicationError(
                'idempotency_key_conflict', 'Idempotency key was used for another booking', 409
            )
        if existing.status != PaymentStatus.CREATING:
            return existing
        payment = existing
    else:
        if booking.status != BookingStatus.ACCEPTED:
            raise ApplicationError(
                'booking_not_payable', 'Only an accepted booking can be paid', 409
            )
        settings = request.app.state.settings
        fee_bps = settings.platform_fee_bps
        if fee_bps is None:
            raise ApplicationError(
                'payment_configuration_unavailable', 'Platform fee is not configured', 503
            )
        fee = platform_fee(booking.price_minor, fee_bps)
        if booking.price_minor + fee > 9_223_372_036_854_775_807:
            raise ApplicationError('payment_amount_overflow', 'Payment amount is too large', 422)
        payment = Payment(
            booking_id=booking.id,
            customer_id=customer_id,
            idempotency_key=idempotency_key,
            status=PaymentStatus.CREATING,
            subtotal_minor=booking.price_minor,
            platform_fee_minor=fee,
            amount_minor=booking.price_minor + fee,
            currency=booking.currency,
        )
        session.add(payment)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            payment = await session.scalar(
                select(Payment).where(
                    Payment.customer_id == customer_id,
                    Payment.idempotency_key == idempotency_key,
                )
            )
            if payment is None or payment.booking_id != booking.id:
                raise ApplicationError(
                    'idempotency_key_conflict', 'Idempotency key was already used', 409
                ) from None
            if payment.status != PaymentStatus.CREATING:
                return payment

    if booking.status != BookingStatus.ACCEPTED:
        raise ApplicationError('booking_not_payable', 'Booking is not payable', 409)
    provider = request.app.state.payment_provider
    try:
        checkout = await provider.create_checkout(
            idempotency_key=str(payment.id),
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            description=f'Yondo booking {booking.id}',
        )
    except Exception as exc:
        raise ApplicationError(
            'payment_provider_unavailable', 'Checkout could not be created', 503
        ) from exc
    parsed_checkout_url = urlsplit(checkout.checkout_url)
    if parsed_checkout_url.scheme != 'https' or not parsed_checkout_url.netloc:
        raise ApplicationError('payment_provider_unavailable', 'Checkout could not be created', 503)
    payment.provider_reference = checkout.provider_reference
    payment.checkout_url = checkout.checkout_url
    payment.status = PaymentStatus.PENDING
    await session.commit()
    await session.refresh(payment)
    return payment


@router.get('/bookings/{booking_id}', response_model=list[PaymentResponse])
async def list_booking_payments(booking_id: UUID, principal: Principal, session: Session):
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    await _participant(session, booking, principal.user.id)
    return list(
        await session.scalars(
            select(Payment)
            .where(Payment.booking_id == booking.id)
            .order_by(Payment.created_at.desc())
        )
    )


@router.post('/webhook', status_code=204)
async def payment_webhook(request: Request, session: Session):
    provider = request.app.state.payment_provider
    body = await request.body()
    try:
        event: PaymentEvent = await provider.verify_event(body, dict(request.headers))
    except Exception as exc:
        raise ApplicationError(
            'invalid_payment_event', 'Payment event could not be verified', 401
        ) from exc
    if event.status not in {'succeeded', 'failed'}:
        raise ApplicationError('invalid_payment_event', 'Payment event status is invalid', 422)
    payment = await session.scalar(
        select(Payment).where(Payment.provider_reference == event.provider_reference)
    )
    if payment is None:
        raise ApplicationError('payment_not_found', 'Payment not found', 404)
    booking = await session.get(Booking, payment.booking_id)
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    try:
        was_confirmed = booking.status == BookingStatus.CONFIRMED
        already_paid = payment.status == PaymentStatus.SUCCEEDED
        applied = await apply_payment_event(session, payment, booking, event.event_id, event.status)
        system_message = None
        if (
            applied
            and not already_paid
            and not was_confirmed
            and event.status == 'succeeded'
            and booking.status == BookingStatus.CONFIRMED
        ):
            system_message = append_system_message(
                session, booking.id, 'payment_confirmed', {'status': booking.status}
            )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        # Duplicate webhook delivery or a concurrent success event is safe to retry.
        receipt = await session.scalar(
            select(PaymentEventReceipt.id).where(
                PaymentEventReceipt.provider_event_id == event.event_id
            )
        )
        if receipt is None:
            raise ApplicationError(
                'payment_event_conflict', 'Payment event was not applied', 409
            ) from exc
    if system_message is not None:
        await session.refresh(system_message)
        await publish(request, system_message)
