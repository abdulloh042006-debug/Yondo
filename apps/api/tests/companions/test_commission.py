"""Commission deducted from the companion's side (docs/product-decisions.md)."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.models.user import User
from yondo_api.payments.models import Payment, PaymentStatus
from yondo_api.payments.service import (
    companion_commission,
    platform_fee,
    release_payout_for_completed_booking,
)

from .test_bookings import setup_bookable_companion
from .test_payments import FakePaymentProvider, accepted_booking


@pytest.mark.parametrize(
    ('subtotal', 'bps', 'fee'),
    [
        (50_000, 500, 2_500),
        (1, 500, 0),  # 0.05 rounds down
        (10, 500, 1),  # 0.5 rounds half up
        (9, 500, 0),  # 0.45 rounds down
        (11, 500, 1),  # 0.55 rounds up
        (12_345, 500, 617),  # 617.25
        (12_347, 500, 617),  # 617.35
        (12_350, 500, 618),  # 617.5 rounds half up
        (99_999, 0, 0),
        (99_999, 10_000, 99_999),
    ],
)
def test_platform_fee_rounds_half_up_in_integer_tiyin(subtotal, bps, fee):
    assert platform_fee(subtotal, bps) == fee
    assert isinstance(platform_fee(subtotal, bps), int)


def payment(subtotal: int, fee: int, amount: int) -> Payment:
    return Payment(
        booking_id=uuid4(),
        customer_id=uuid4(),
        idempotency_key='k',
        status=PaymentStatus.SUCCEEDED,
        subtotal_minor=subtotal,
        platform_fee_minor=fee,
        amount_minor=amount,
        currency='UZS',
    )


def test_commission_comes_off_the_companion_only_when_the_customer_did_not_pay_it():
    assert companion_commission(payment(12_350, 618, 12_350)) == 618
    # Earlier rule: the customer already paid the fee on top, so nothing is deducted again.
    assert companion_commission(payment(12_350, 618, 12_968)) == 0
    assert companion_commission(payment(12_350, 0, 12_350)) == 0


async def pay_and_complete(e, bps, key, price=None):
    client = e['client']
    booking_id = await accepted_booking(e, await setup_bookable_companion(e))
    if price is not None:  # an odd amount, so the half-up rounding is exercised end to end
        async with e['app'].state.db_session_factory() as session:
            (await session.get(Booking, UUID(booking_id))).price_minor = price
            await session.commit()
    e['app'].state.payment_provider = FakePaymentProvider()
    e['app'].state.settings = e['app'].state.settings.model_copy(update={'platform_fee_bps': bps})
    created = await client.post(
        f'/api/v1/payments/bookings/{booking_id}',
        headers={**e['customer'], 'Idempotency-Key': key},
    )
    return booking_id, created


@pytest.mark.asyncio
async def test_odd_tiyin_customer_pays_subtotal_and_companion_gets_net(prepared):
    e = prepared
    booking_id, created = await pay_and_complete(e, 500, 'commission-odd-0001', price=12_350)
    assert created.status_code == 201, created.text
    body = created.json()
    fee = 618  # 12 350 x 5 % = 617.5 tiyin, rounded half up
    assert body['subtotal_minor'] == 12_350
    assert body['amount_minor'] == body['subtotal_minor']  # no fee on top
    assert body['platform_fee_minor'] == fee
    assert (await e['client'].post('/api/v1/payments/webhook', content=b'x')).status_code == 204
    async with e['app'].state.db_session_factory() as session:
        booking = await session.get(Booking, UUID(booking_id))
        booking.status = BookingStatus.COMPLETED
        companion = await session.get(User, UUID(e['owner_id']))
        await session.commit()
        payout = await release_payout_for_completed_booking(session, booking, companion)
        await session.commit()
        assert payout.gross_minor == body['subtotal_minor']
        assert payout.commission_minor == fee
        assert payout.deductions_minor == 0
        assert payout.amount_minor == 11_732  # net = 12 350 - 618


@pytest.mark.asyncio
async def test_unset_rate_still_answers_503_and_creates_nothing(prepared):
    e = prepared
    booking_id, created = await pay_and_complete(e, None, 'commission-unset-01')
    assert created.status_code == 503
    assert created.json()['code'] == 'payment_configuration_unavailable'
    async with e['app'].state.db_session_factory() as session:
        assert await session.get(Booking, UUID(booking_id)) is not None
        assert await session.scalar(select(func.count()).select_from(Payment)) == 0
