import hashlib
import hmac
import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from yondo_api.config import Settings
from yondo_api.main import create_application
from yondo_api.payments.provider import UnconfiguredPaymentProvider
from yondo_api.payments.tezcheck import TezCheckError, TezCheckPaymentProvider

from .test_bookings import setup_bookable_companion
from .test_payments import accepted_booking

SECRET = 'whsec_' + 'a' * 32
NOW = 1_800_000_000


def sign(
    body: bytes, *, timestamp: int = NOW, delivery: str = 'whd_1', secret: str = SECRET
) -> dict[str, str]:
    digest = hmac.new(
        secret.encode(), f'{timestamp}.{delivery}.'.encode() + body, hashlib.sha256
    ).hexdigest()
    return {
        'x-checkout-timestamp': str(timestamp),
        'x-checkout-delivery': delivery,
        'x-checkout-signature': f'v1={digest}',
        'x-checkout-event': 'payment.succeeded',
    }


def event(
    type_: str = 'payment.succeeded',
    *,
    bill: str = 'bill_1',
    environment: str = 'live',
    event_id: str = 'oev_1',
):
    return json.dumps(
        {
            'id': event_id,
            'type': type_,
            'schema_version': 1,
            'created_at': '2026-10-28T10:00:00Z',
            'data': {
                'payment_id': 'pay_1',
                'state': type_.split('.')[-1],
                'amount_minor': 15000000,
                'bill_id': bill,
                'environment': environment,
                'external_reference': 'x',
                'sequence': 1,
            },
        },
        separators=(',', ':'),
    ).encode()


def provider(handler=None, **kwargs):
    transport = httpx.MockTransport(handler) if handler else None
    return TezCheckPaymentProvider(
        api_url='https://api.tezcheck.uz/api/merchant/v1',
        token='tok_secret',
        webhook_secret=SECRET,
        cash_desk_code='cdk_desk',
        transport=transport,
        clock=lambda: NOW,
        **kwargs,
    )


@pytest.mark.asyncio
async def test_create_checkout_sends_the_documented_bill_request():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen['url'], seen['headers'], seen['body'] = (
            str(request.url),
            request.headers,
            json.loads(request.content),
        )
        return httpx.Response(
            201,
            json={
                'data': {
                    'bill': {'id': 'bill_9', 'state': 'active'},
                    'payment_url': 'https://pay.tezcheck.uz/p/abc',
                }
            },
        )

    session = await provider(handler, return_url='https://yondo.example/bookings').create_checkout(
        idempotency_key='3f1c0d6e-0000-4000-8000-000000000001',
        amount_minor=15000000,
        currency='UZS',
        description='Yondo booking 42',
    )
    assert (session.provider_reference, session.checkout_url) == (
        'bill_9',
        'https://pay.tezcheck.uz/p/abc',
    )
    assert seen['url'] == 'https://api.tezcheck.uz/api/merchant/v1/bills'
    assert seen['headers']['authorization'] == 'Bearer tok_secret'
    assert seen['headers']['x-cash-desk-code'] == 'cdk_desk'
    assert seen['headers']['idempotency-key'] == '3f1c0d6e-0000-4000-8000-000000000001'
    assert seen['body'] == {
        'amount_minor': 15000000,
        'title': 'Yondo bron',
        'description': 'Yondo booking 42',
        'external_reference': '3f1c0d6e-0000-4000-8000-000000000001',
        'return_url': 'https://yondo.example/bookings',
    }
    assert isinstance(seen['body']['amount_minor'], int)


@pytest.mark.asyncio
async def test_create_checkout_refuses_other_currencies_and_provider_errors():
    with pytest.raises(TezCheckError):
        await provider().create_checkout(
            idempotency_key='k' * 8, amount_minor=100, currency='USD', description='d'
        )
    refused = provider(
        lambda r: httpx.Response(
            422,
            json={
                'error': {
                    'code': 'payment_link.amount_out_of_range',
                    'status': 422,
                    'request_id': 'req_1',
                }
            },
        )
    )
    with pytest.raises(TezCheckError):
        await refused.create_checkout(
            idempotency_key='k' * 8, amount_minor=100, currency='UZS', description='d'
        )
    malformed = provider(lambda r: httpx.Response(201, json={'data': {'bill': {}}}))
    with pytest.raises(TezCheckError):
        await malformed.create_checkout(
            idempotency_key='k' * 8, amount_minor=100000, currency='UZS', description='d'
        )


@pytest.mark.asyncio
async def test_verify_event_maps_signed_succeeded_and_failed_events():
    body = event()
    parsed = await provider().verify_event(body, sign(body))
    assert (parsed.event_id, parsed.provider_reference, parsed.status) == (
        'oev_1',
        'bill_1',
        'succeeded',
    )
    failed = event('payment.failed', event_id='oev_2')
    assert (await provider().verify_event(failed, sign(failed))).status == 'failed'
    mixed_case = {name.title(): value for name, value in sign(body).items()}
    assert (await provider().verify_event(body, mixed_case)).provider_reference == 'bill_1'


@pytest.mark.asyncio
async def test_verify_event_rejects_bad_signatures_stale_timestamps_and_other_events():
    body = event()
    good = sign(body)
    for headers in (
        {**good, 'x-checkout-signature': 'v1=' + '0' * 64},
        sign(body, secret='whsec_' + 'b' * 32),
        sign(body, delivery='whd_other') | {'x-checkout-delivery': 'whd_1'},
        sign(body, timestamp=NOW - 301),
        sign(body, timestamp=NOW + 301),
        {k: v for k, v in good.items() if k != 'x-checkout-timestamp'},
        {**good, 'x-checkout-signature': ''},
    ):
        with pytest.raises(TezCheckError):
            await provider().verify_event(body, headers)
    tampered = body.replace(b'bill_1', b'bill_2')
    with pytest.raises(TezCheckError):
        await provider().verify_event(tampered, good)
    for other in ('payment.processing', 'payment.refunded', 'payment.disputed'):
        unsupported = event(other)
        with pytest.raises(TezCheckError):
            await provider().verify_event(unsupported, sign(unsupported))


@pytest.mark.asyncio
async def test_verify_event_accepts_any_signature_during_secret_rotation():
    body = event()
    new = sign(body)['x-checkout-signature']
    old = sign(body, secret='whsec_' + 'c' * 32)['x-checkout-signature']
    headers = {**sign(body), 'x-checkout-signature': f'{old}, {new}'}
    assert (await provider().verify_event(body, headers)).status == 'succeeded'


@pytest.mark.asyncio
async def test_test_environment_payments_are_refused_unless_explicitly_accepted():
    body = event(environment='test')
    with pytest.raises(TezCheckError):
        await provider().verify_event(body, sign(body))
    assert (
        await provider(accept_test_payments=True).verify_event(body, sign(body))
    ).status == 'succeeded'
    unlabeled = json.dumps(
        {'id': 'oev_3', 'type': 'payment.succeeded', 'data': {'bill_id': 'b'}}
    ).encode()
    with pytest.raises(TezCheckError):
        await provider(accept_test_payments=True).verify_event(unlabeled, sign(unlabeled))


def test_settings_validate_tezcheck_configuration():
    base = {'environment': 'production', 'auth_otp_pepper': 'p' * 40}
    configured = {'tezcheck_token': SecretStr('tok'), 'tezcheck_webhook_secret': SecretStr(SECRET)}
    assert Settings(**base, **configured).tezcheck_token.get_secret_value() == 'tok'
    assert (
        Settings(**base).tezcheck_token.get_secret_value() == ''
    )  # unset = not configured, nothing to validate
    with pytest.raises(
        ValidationError
    ):  # a token without a webhook secret would accept unsigned events
        Settings(**base, tezcheck_token=SecretStr('tok'))
    with pytest.raises(ValidationError):
        Settings(
            **base, tezcheck_token=SecretStr('tok'), tezcheck_webhook_secret=SecretStr('short')
        )
    with pytest.raises(ValidationError):  # the API URL must be https
        Settings(**base, **configured, tezcheck_api_url='http://api.tezcheck.uz/api/merchant/v1')
    with pytest.raises(ValidationError):  # test payments never in production
        Settings(**base, **configured, tezcheck_accept_test_payments=True)
    assert Settings(environment='test', **configured, tezcheck_accept_test_payments=True)


def test_application_uses_tezcheck_only_when_configured():
    plain = create_application(Settings(environment='test'))
    assert isinstance(plain.state.payment_provider, UnconfiguredPaymentProvider)
    wired = create_application(
        Settings(
            environment='test',
            tezcheck_token=SecretStr('tok'),
            tezcheck_webhook_secret=SecretStr(SECRET),
        )
    )
    assert isinstance(wired.state.payment_provider, TezCheckPaymentProvider)


@pytest.mark.asyncio
async def test_real_adapter_through_checkout_and_signed_webhook(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booking_id = await accepted_booking(e, service)
    bills = []

    def handler(request: httpx.Request) -> httpx.Response:
        bills.append(json.loads(request.content))
        return httpx.Response(
            201,
            json={
                'data': {'bill': {'id': 'bill_77'}, 'payment_url': 'https://pay.tezcheck.uz/p/77'}
            },
        )

    e['app'].state.payment_provider = provider(handler, accept_test_payments=True)
    e['app'].state.settings = e['app'].state.settings.model_copy(update={'platform_fee_bps': 500})
    created = await client.post(
        f'/api/v1/payments/bookings/{booking_id}',
        headers={**e['customer'], 'Idempotency-Key': 'booking-payment-tez-1'},
    )
    assert created.status_code == 201, created.text
    assert created.json()['checkout_url'] == 'https://pay.tezcheck.uz/p/77'
    assert bills[0]['amount_minor'] == 52500  # 50 000 + 5 % fee, integer tiyin
    body = event(bill='bill_77', environment='test')
    unsigned = await client.post('/api/v1/payments/webhook', content=body)
    assert unsigned.status_code == 401
    assert (await client.get(f'/api/v1/bookings/{booking_id}', headers=e['customer'])).json()[
        'status'
    ] == 'accepted'
    signed = await client.post('/api/v1/payments/webhook', content=body, headers=sign(body))
    assert signed.status_code == 204, signed.text
    again = await client.post(
        '/api/v1/payments/webhook', content=body, headers=sign(body, delivery='whd_2')
    )
    assert again.status_code == 204  # a redelivery with the same event id is safe
    assert (await client.get(f'/api/v1/bookings/{booking_id}', headers=e['customer'])).json()[
        'status'
    ] == 'confirmed'
