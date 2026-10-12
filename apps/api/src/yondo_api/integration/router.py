"""Booking and gift basket combined quote; financial completion is deliberately disabled."""
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select

from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.gifts.router import preview_checkout, require_role
from yondo_api.models.user import UserRoleType

router = APIRouter(prefix='/integration', tags=['booking and gifts'])
MAX_MINOR = 9_223_372_036_854_775_807

async def eligible_booking(booking_id: UUID, principal: Principal, session: Session) -> Booking:
    await require_role(principal, session, UserRoleType.CUSTOMER)
    booking = await session.scalar(select(Booking).where(Booking.id == booking_id))
    if booking is None or booking.customer_id != principal.user.id:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    if booking.status != BookingStatus.ACCEPTED:
        raise ApplicationError('booking_not_payable', 'Booking is not accepted', 409)
    return booking

@router.get('/bookings/{booking_id}/preview')
async def preview_booking_gifts(booking_id: UUID, principal: Principal, session: Session):
    booking = await eligible_booking(booking_id, principal, session)
    gifts = await preview_checkout(principal, session)
    if booking.currency != gifts['currency']:
        raise ApplicationError('gift_currency_mismatch', 'Gift and booking currency differ', 409)
    subtotal = booking.price_minor + gifts['subtotal_minor']
    if subtotal > MAX_MINOR:
        raise ApplicationError('booking_gift_overflow', 'Combined subtotal too large', 422)
    return {
        'booking_id': booking.id,
        'booking_service_minor': booking.price_minor,
        'gift_items': gifts['items'],
        'gift_subtotal_minor': gifts['subtotal_minor'],
        'subtotal_minor': subtotal,
        'currency': booking.currency,
        'platform_fee_minor': None,
        'delivery_fee_minor': None,
        'total_minor': None,
        'checkout_available': False,
        'reason': 'combined_payment_and_delivery_policy_unconfigured',
    }

@router.post('/bookings/{booking_id}/checkout', status_code=503)
async def combined_checkout(booking_id: UUID, principal: Principal, session: Session):
    await eligible_booking(booking_id, principal, session)
    raise ApplicationError(
        'combined_checkout_unavailable',
        'Combined payment and gift fulfillment are not configured',
        503,
    )
