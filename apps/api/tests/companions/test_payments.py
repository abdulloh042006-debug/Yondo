from uuid import UUID

import pytest
from sqlalchemy import select

from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.models.user import User
from yondo_api.payments.models import CompanionPayout, Payment, PaymentStatus
from yondo_api.payments.provider import CheckoutSession, PaymentEvent
from yondo_api.payments.service import release_payout_for_completed_booking

from .test_bookings import booking_payload, setup_bookable_companion


class FakePaymentProvider:
    def __init__(self):
        self.checkouts = []
        self.event = PaymentEvent('event-1', 'provider-1', 'succeeded')

    async def create_checkout(self, **kwargs):
        self.checkouts.append(kwargs)
        return CheckoutSession('provider-1', 'https://pay.example/checkout/1')

    async def verify_event(self, body, headers):
        return self.event


async def accepted_booking(e, service):
    client = e['client']
    created = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert created.status_code == 201, created.text
    booking_id = created.json()['id']
    accepted = await client.post(f'/api/v1/bookings/{booking_id}/accept', headers=e['owner'])
    assert accepted.status_code == 200
    return booking_id


@pytest.mark.asyncio
async def test_checkout_idempotency_verified_webhook_and_payout(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    provider = FakePaymentProvider()
    e['app'].state.payment_provider = provider
    e['app'].state.settings = e['app'].state.settings.model_copy(update={'platform_fee_bps': 500})
    headers = {**e['customer'], 'Idempotency-Key': 'booking-payment-001'}
    created = await client.post(f'/api/v1/payments/bookings/{booking_id}', headers=headers)
    assert created.status_code == 201, created.text
    payment = created.json()
    assert payment['subtotal_minor'] == 50000
    assert payment['platform_fee_minor'] == 2500
    assert payment['amount_minor'] == 52500
    assert payment['status'] == 'pending'
    assert payment['checkout_url'].startswith('https://')
    repeated = await client.post(f'/api/v1/payments/bookings/{booking_id}', headers=headers)
    assert repeated.status_code == 201
    assert repeated.json()['id'] == payment['id']
    assert len(provider.checkouts) == 1
    assert (
        await client.get(f'/api/v1/payments/bookings/{booking_id}', headers=e['owner'])
    ).status_code == 200
    assert (
        await client.get(f'/api/v1/payments/bookings/{booking_id}', headers=e['other'])
    ).status_code == 404

    applied = await client.post('/api/v1/payments/webhook', content=b'provider-payload')
    assert applied.status_code == 204
    duplicate = await client.post('/api/v1/payments/webhook', content=b'provider-payload')
    assert duplicate.status_code == 204
    booking = await client.get(f'/api/v1/bookings/{booking_id}', headers=e['customer'])
    assert booking.json()['status'] == 'confirmed'
    async with e['app'].state.db_session_factory() as session:
        stored_booking = await session.get(Booking, UUID(booking_id))
        stored_booking.status = BookingStatus.COMPLETED
        companion = await session.get(User, UUID(e['owner_id']))
        await session.commit()
        payout = await release_payout_for_completed_booking(session, stored_booking, companion)
        await session.commit()
        assert payout.status == 'ready'
        assert payout.amount_minor == 50000
        assert await session.scalar(
            select(CompanionPayout.id).where(CompanionPayout.booking_id == stored_booking.id)
        )


@pytest.mark.asyncio
async def test_checkout_fails_closed_without_fee_or_provider(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    response = await client.post(
        f'/api/v1/payments/bookings/{booking_id}',
        headers={**e['customer'], 'Idempotency-Key': 'booking-payment-002'},
    )
    assert response.status_code == 503
    assert response.json()['code'] == 'payment_configuration_unavailable'


@pytest.mark.asyncio
async def test_provider_failure_can_retry_with_same_idempotency_key(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    e['app'].state.settings = e['app'].state.settings.model_copy(update={'platform_fee_bps': 0})

    class FlakyProvider(FakePaymentProvider):
        async def create_checkout(self, **kwargs):
            self.checkouts.append(kwargs)
            if len(self.checkouts) == 1:
                raise OSError('secret connection error')
            return CheckoutSession('provider-retry', 'https://pay.example/retry')

    provider = FlakyProvider()
    e['app'].state.payment_provider = provider
    headers = {**e['customer'], 'Idempotency-Key': 'booking-payment-003'}
    failed = await client.post(f'/api/v1/payments/bookings/{booking_id}', headers=headers)
    assert failed.status_code == 503
    assert 'secret connection error' not in failed.text
    retried = await client.post(f'/api/v1/payments/bookings/{booking_id}', headers=headers)
    assert retried.status_code == 201, retried.text
    assert retried.json()['status'] == 'pending'
    assert len(provider.checkouts) == 2


@pytest.mark.asyncio
async def test_late_success_after_cancellation_is_flagged_for_refund(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    provider = FakePaymentProvider()
    e['app'].state.payment_provider = provider
    e['app'].state.settings = e['app'].state.settings.model_copy(update={'platform_fee_bps': 0})
    checkout = await client.post(
        f'/api/v1/payments/bookings/{booking_id}',
        headers={**e['customer'], 'Idempotency-Key': 'booking-payment-004'},
    )
    assert checkout.status_code == 201
    await client.post(f'/api/v1/bookings/{booking_id}/cancel', headers=e['customer'], json={})
    callback = await client.post('/api/v1/payments/webhook', content=b'provider-payload')
    assert callback.status_code == 204
    async with e['app'].state.db_session_factory() as session:
        payment = await session.get(Payment, UUID(checkout.json()['id']))
        booking = await session.get(Booking, UUID(booking_id))
        assert payment.status == PaymentStatus.SUCCEEDED
        assert payment.refund_required is True
        assert booking.status == BookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_payment_requires_https_checkout_url(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    e['app'].state.settings = e['app'].state.settings.model_copy(update={'platform_fee_bps': 0})

    class UnsafeProvider(FakePaymentProvider):
        async def create_checkout(self, **kwargs):
            self.checkouts.append(kwargs)
            return CheckoutSession('unsafe', 'javascript:alert(1)')

    e['app'].state.payment_provider = UnsafeProvider()
    response = await client.post(
        f'/api/v1/payments/bookings/{booking_id}',
        headers={**e['customer'], 'Idempotency-Key': 'booking-payment-005'},
    )
    assert response.status_code == 503
    async with e['app'].state.db_session_factory() as session:
        payment = await session.scalar(
            select(Payment).where(Payment.booking_id == UUID(booking_id))
        )
        assert payment.status == PaymentStatus.CREATING
