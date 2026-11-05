import json
import re
from uuid import UUID

import pytest
from sqlalchemy import select

from yondo_api.admin.models import AdminAuditEvent
from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.config import ManualPaymentCard, Settings
from yondo_api.main import select_payment_provider
from yondo_api.models.user import UserRole, UserRoleType
from yondo_api.payments.manual import ManualTransferPaymentProvider
from yondo_api.payments.provider import UnconfiguredPaymentProvider
from yondo_api.payments.tezcheck import TezCheckPaymentProvider

from .test_bookings import setup_bookable_companion
from .test_payments import accepted_booking

# Obviously fake numbers: real card numbers live only in the host's environment.
CARDS = (
    ManualPaymentCard(label='Uzcard', number='8600000000000001', holder='DEMO Owner'),
    ManualPaymentCard(label='Humo', number='9860 0000 0000 0002', holder='DEMO Owner'),
)
REF = re.compile(r'^YND-[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}$')


def manual_mode(e, fee_bps=0):
    e['app'].state.settings = e['app'].state.settings.model_copy(
        update={
            'payment_provider': 'manual',
            'manual_payment_cards': CARDS,
            'public_web_url': 'https://yondo.example',
            'platform_fee_bps': fee_bps,
        }
    )
    e['app'].state.payment_provider = ManualTransferPaymentProvider('https://yondo.example')


def test_settings_require_cards_and_https_page_and_pick_the_provider():
    base = {'environment': 'test'}
    with pytest.raises(ValueError, match='MANUAL_PAYMENT_CARDS'):
        Settings(**base, payment_provider='manual', public_web_url='https://yondo.example')
    with pytest.raises(ValueError, match='https'):
        Settings(
            **base,
            payment_provider='manual',
            manual_payment_cards=CARDS,
            public_web_url='http://yondo.example',
        )
    with pytest.raises(ValueError, match='TEZCHECK_TOKEN'):
        Settings(**base, payment_provider='tezcheck')
    with pytest.raises(ValueError, match='16 to 19 digits'):
        ManualPaymentCard(label='X', number='8600 0000 0000 000', holder='Y')
    # The env value is JSON; numbers are normalised to groups of four for display.
    manual = Settings(
        **base,
        payment_provider='manual',
        public_web_url='https://yondo.example',
        manual_payment_cards=json.loads(
            '[{"label":"Uzcard","number":"8600000000000001","holder":"DEMO Owner"}]'
        ),
    )
    assert manual.manual_payment_cards[0].number == '8600 0000 0000 0001'
    assert isinstance(select_payment_provider(manual), ManualTransferPaymentProvider)
    assert isinstance(select_payment_provider(Settings(**base)), UnconfiguredPaymentProvider)
    # "One button" back to the provider: the same keys, a different YONDO_PAYMENT_PROVIDER.
    tez = Settings(
        **base,
        payment_provider='tezcheck',
        tezcheck_token='t' * 20,
        tezcheck_webhook_secret='s' * 20,
        tezcheck_cash_desk_code='desk',
    )
    assert isinstance(select_payment_provider(tez), TezCheckPaymentProvider)


@pytest.mark.asyncio
async def test_manual_transfer_is_confirmed_by_an_admin_and_confirms_the_booking(prepared):
    e, client = prepared, prepared['client']
    manual_mode(e)
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    created = await client.post(
        f'/api/v1/payments/bookings/{booking_id}',
        headers={**e['customer'], 'Idempotency-Key': 'manual-payment-0001'},
    )
    assert created.status_code == 201, created.text
    payment = created.json()
    assert payment['status'] == 'pending'
    assert payment['platform_fee_minor'] == 0 and payment['amount_minor'] == 50000
    reference = payment['checkout_url'].rsplit('/', 1)[1]
    assert payment['checkout_url'] == f'https://yondo.example/pay/{reference}'
    assert REF.match(reference), reference

    # Only the paying customer sees the cards; everyone else gets 404, as for an unknown reference.
    page = await client.get(f'/api/v1/payments/manual/{reference}', headers=e['customer'])
    assert page.status_code == 200, page.text
    body = page.json()
    assert body['amount_minor'] == 50000 and body['reference'] == reference
    assert [c['number'] for c in body['cards']] == ['8600 0000 0000 0001', '9860 0000 0000 0002']
    assert body['state'] == 'open'
    for headers in (e['owner'], e['other'], e['admin']):
        hidden = await client.get(f'/api/v1/payments/manual/{reference}', headers=headers)
        assert hidden.status_code == 404
    assert (
        await client.get('/api/v1/payments/manual/YND-AAAA-AAAA', headers=e['customer'])
    ).status_code == 404

    # The admin queue lists it; non-admins cannot see the queue or confirm.
    assert (
        await client.get('/api/v1/admin/payments/manual', headers=e['customer'])
    ).status_code == 403
    queue = await client.get('/api/v1/admin/payments/manual', headers=e['admin'])
    assert [p['reference'] for p in queue.json()] == [reference]
    denied = await client.post(
        f'/api/v1/admin/payments/manual/{reference}/received', headers=e['owner']
    )
    assert denied.status_code == 403

    received = await client.post(
        f'/api/v1/admin/payments/manual/{reference}/received', headers=e['admin']
    )
    assert received.status_code == 200, received.text
    assert received.json()['status'] == 'succeeded'
    again = await client.post(
        f'/api/v1/admin/payments/manual/{reference}/received', headers=e['admin']
    )
    assert again.status_code == 200 and again.json()['status'] == 'succeeded'

    booking = await client.get(f'/api/v1/bookings/{booking_id}', headers=e['customer'])
    assert booking.json()['status'] == 'confirmed'
    page = (await client.get(f'/api/v1/payments/manual/{reference}', headers=e['customer'])).json()
    assert page['state'] == 'confirmed' and page['cards'] == []
    assert (await client.get('/api/v1/admin/payments/manual', headers=e['admin'])).json() == []
    done = await client.get(
        '/api/v1/admin/payments/manual', headers=e['admin'], params={'status': 'succeeded'}
    )
    assert [p['reference'] for p in done.json()] == [reference]
    async with e['app'].state.db_session_factory() as session:
        audits = list(
            await session.scalars(
                select(AdminAuditEvent).where(AdminAuditEvent.action == 'manual_payment_received')
            )
        )
    assert len(audits) == 1 and audits[0].reason == f'payment:{received.json()["payment_id"]}'

    # Nothing outside can confirm a manual payment: the webhook refuses every event.
    forged = await client.post(
        '/api/v1/payments/webhook',
        content=json.dumps({'provider_reference': reference, 'status': 'succeeded'}),
    )
    assert forged.status_code == 401


@pytest.mark.asyncio
async def test_admin_cannot_confirm_own_payment_and_late_money_is_flagged_for_refund(prepared):
    e, client = prepared, prepared['client']
    manual_mode(e, fee_bps=500)
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    created = await client.post(
        f'/api/v1/payments/bookings/{booking_id}',
        headers={**e['customer'], 'Idempotency-Key': 'manual-payment-0002'},
    )
    payment = created.json()
    assert payment['platform_fee_minor'] == 2500 and payment['amount_minor'] == 52500
    reference = payment['checkout_url'].rsplit('/', 1)[1]

    # The customer is also an admin: a second person has to confirm the money.
    customer_id = (await client.get('/api/v1/auth/me', headers=e['customer'])).json()['id']
    async with e['app'].state.db_session_factory() as session:
        session.add(UserRole(user_id=UUID(customer_id), role=UserRoleType.ADMIN))
        await session.commit()
    own = await client.post(
        f'/api/v1/admin/payments/manual/{reference}/received', headers=e['customer']
    )
    assert own.status_code == 403 and own.json()['code'] == 'self_approval_forbidden'

    # Cancelled before the money was seen: the booking stays cancelled, flagged for a refund.
    cancelled = await client.post(
        f'/api/v1/bookings/{booking_id}/cancel', headers=e['customer'], json={'reason': ''}
    )
    assert cancelled.status_code == 200, cancelled.text
    late = await client.post(
        f'/api/v1/admin/payments/manual/{reference}/received', headers=e['admin']
    )
    assert late.status_code == 200, late.text
    assert late.json()['refund_required'] is True
    async with e['app'].state.db_session_factory() as session:
        booking = await session.get(Booking, UUID(booking_id))
        assert booking.status == BookingStatus.CANCELLED


async def _manual_payment(e, key):
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    created = await e['client'].post(
        f'/api/v1/payments/bookings/{booking_id}',
        headers={**e['customer'], 'Idempotency-Key': key},
    )
    assert created.status_code == 201, created.text
    return booking_id, created.json()['checkout_url'].rsplit('/', 1)[1]


@pytest.mark.asyncio
async def test_cards_are_hidden_once_the_booking_cannot_be_paid_and_late_money_says_refund(
    prepared,
):
    e, client = prepared, prepared['client']
    manual_mode(e)
    booking_id, reference = await _manual_payment(e, 'manual-payment-0003')
    cancelled = await client.post(
        f'/api/v1/bookings/{booking_id}/cancel', headers=e['owner'], json={'reason': ''}
    )
    assert cancelled.status_code == 200, cancelled.text
    page = (await client.get(f'/api/v1/payments/manual/{reference}', headers=e['customer'])).json()
    assert page['state'] == 'closed' and page['cards'] == []
    # Late money is recorded, but the customer is never told the booking is confirmed.
    late = await client.post(
        f'/api/v1/admin/payments/manual/{reference}/received', headers=e['admin']
    )
    assert late.status_code == 200 and late.json()['refund_required'] is True
    assert late.json()['booking_status'] == 'cancelled'
    page = (await client.get(f'/api/v1/payments/manual/{reference}', headers=e['customer'])).json()
    assert page['state'] == 'refund_required' and page['cards'] == []


@pytest.mark.asyncio
async def test_an_overdue_booking_is_expired_before_the_money_is_recorded(prepared):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    e, client = prepared, prepared['client']
    manual_mode(e)
    booking_id, reference = await _manual_payment(e, 'manual-payment-0004')
    # The start time passed and the hourly sweep has not run yet.
    async with e['app'].state.db_session_factory() as session:
        past = datetime.now(UTC) - timedelta(hours=3)
        await session.execute(
            update(Booking)
            .where(Booking.id == UUID(booking_id))
            .values(starts_at=past, ends_at=past + timedelta(hours=1))
        )
        await session.commit()
    page = (await client.get(f'/api/v1/payments/manual/{reference}', headers=e['customer'])).json()
    assert page['state'] == 'closed' and page['cards'] == []
    late = await client.post(
        f'/api/v1/admin/payments/manual/{reference}/received', headers=e['admin']
    )
    assert late.status_code == 200, late.text
    assert late.json()['booking_status'] == 'expired' and late.json()['refund_required'] is True


@pytest.mark.asyncio
async def test_companion_who_is_admin_cannot_confirm_and_webhook_refuses_manual_refs(prepared):
    from yondo_api.payments.provider import PaymentEvent

    e, client = prepared, prepared['client']
    manual_mode(e)
    booking_id, reference = await _manual_payment(e, 'manual-payment-0005')
    owner_id = (await client.get('/api/v1/auth/me', headers=e['owner'])).json()['id']
    async with e['app'].state.db_session_factory() as session:
        session.add(UserRole(user_id=UUID(owner_id), role=UserRoleType.ADMIN))
        await session.commit()
    own = await client.post(
        f'/api/v1/admin/payments/manual/{reference}/received', headers=e['owner']
    )
    assert own.status_code == 403 and own.json()['code'] == 'self_approval_forbidden'

    class ForgingProvider:
        async def verify_event(self, body, headers):
            return PaymentEvent('forged-1', reference, 'succeeded')

    # Even a provider whose signature check passed cannot confirm a manual (YND-) payment.
    e['app'].state.payment_provider = ForgingProvider()
    forged = await client.post('/api/v1/payments/webhook', content=b'{}')
    assert forged.status_code == 401
    booking = await client.get(f'/api/v1/bookings/{booking_id}', headers=e['customer'])
    assert booking.json()['status'] == 'accepted'
