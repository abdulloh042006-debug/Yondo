"""Telegram Gateway OTP adapter: two-step request flow, error mapping, secrecy, no retries.

No network: every call goes through `httpx.MockTransport`. The flow (`checkSendAbility`, then
`sendVerificationMessage` with the check's `request_id`) was verified live on 2026-10-28 with the
owner's own number; the Telegram *error strings* below are still the unverified ones from
docs/otp-telegram-gateway.md, so these tests pin our *mapping*, not Telegram's wording.
"""

import asyncio
import json
import os
import traceback
from contextlib import asynccontextmanager

import httpx
import pytest
from sqlalchemy import func, select, text
from structlog.testing import capture_logs

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.providers import OtpDelivery
from yondo_api.auth.telegram_gateway import TelegramGatewayOtpProvider
from yondo_api.config import Settings
from yondo_api.main import create_application
from yondo_api.models.auth import OtpChallenge
from yondo_api.models.user import User

TOKEN = '777:tg-gateway-secret-token'
PHONE = '+998901234567'
LOCAL_PHONE = '901234567'
CODE = '482915'
PEPPER = 'test-only-auth-pepper-0123456789abcdef'

CHANNEL_UNAVAILABLE = ('otp_channel_unavailable', 422)
DELIVERY_FAILED = ('otp_delivery_failed', 502)

CHECK_PATH = '/checkSendAbility'
SEND_PATH = '/sendVerificationMessage'
# Which call fails -> the requests the provider may make before giving up. If the check fails
# there is NO send; if the send fails there were exactly two requests and no retry.
STAGES = ['check', 'send']
PATHS_UNTIL = {'check': [CHECK_PATH], 'send': [CHECK_PATH, SEND_PATH]}
METHOD_OF = {'check': 'checkSendAbility', 'send': 'sendVerificationMessage'}


def ok_response(request_id: str | None = 'req_abc123') -> httpx.Response:
    result: dict[str, object] = {
        'phone_number': PHONE,
        'request_cost': 0.01,
        'remaining_balance': 1.5,
    }
    if request_id is not None:
        result['request_id'] = request_id
    return httpx.Response(200, json={'ok': True, 'result': result})


def error_response(error: object, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json={'ok': False, 'error': error})


def serve(outcome, request: httpx.Request) -> httpx.Response:
    if isinstance(outcome, Exception):
        raise outcome
    if isinstance(outcome, httpx.Response):  # a fresh copy per call: responses are one-shot
        return httpx.Response(outcome.status_code, content=outcome.content)
    return outcome(request)


def gateway(*, check=None, send=None):
    """MockTransport handler + the list of requests it saw.

    `check` / `send` is what the matching Telegram method answers: a Response (served again for
    every call), an exception instance to raise, or a callable(request) -> Response. The default
    for both is a success carrying a `request_id`.
    """
    seen: list[httpx.Request] = []
    outcomes = {
        CHECK_PATH: check if check is not None else ok_response(),
        SEND_PATH: send if send is not None else ok_response(),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return serve(outcomes[request.url.path], request)

    return handler, seen


def paths(seen: list[httpx.Request]) -> list[str]:
    return [request.url.path for request in seen]


def make_provider(handler, **kwargs) -> TelegramGatewayOtpProvider:
    return TelegramGatewayOtpProvider(TOKEN, transport=httpx.MockTransport(handler), **kwargs)


async def run(*, check=None, send=None, **kwargs):
    """Deliver once; return (result, error, requests seen, captured log events)."""
    handler, seen = gateway(check=check, send=send)
    provider = make_provider(handler, **kwargs)
    result = error = None
    with capture_logs() as logs:
        try:
            result = await provider.deliver(PHONE, CODE)
        except ApplicationError as exc:
            error = exc
    return result, error, seen, logs


async def run_failing(stage: str, outcome):
    """Make the given call (check or send) answer `outcome`; the other one succeeds."""
    return await run(**{stage: outcome})


def assert_failure(error: ApplicationError | None, expected: tuple[str, int]) -> None:
    assert error is not None
    assert (error.code, error.status_code) == expected


def assert_nothing_secret(text_: str) -> None:
    for secret in (TOKEN, PHONE, PHONE.lstrip('+'), LOCAL_PHONE, CODE):
        assert secret not in text_, secret


# --- request shape: two steps ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_checks_then_sends_our_code_with_the_request_id_and_reports_the_channel():
    result, error, seen, logs = await run()
    assert error is None
    assert result == OtpDelivery(development_code=None, channel='telegram')

    # Exactly two requests, check first, both POST with the Bearer token and a JSON body.
    assert paths(seen) == [CHECK_PATH, SEND_PATH]
    for request in seen:
        assert request.method == 'POST'
        assert request.headers['authorization'] == f'Bearer {TOKEN}'
        assert request.headers['content-type'].startswith('application/json')
        # The secret travels only in the header: not in the URL, not in the body.
        assert TOKEN not in str(request.url) and TOKEN.encode() not in request.content
    check, send = seen
    assert str(check.url) == 'https://gatewayapi.telegram.org/checkSendAbility'
    assert json.loads(check.content) == {'phone_number': PHONE}  # nothing but the number
    assert str(send.url) == 'https://gatewayapi.telegram.org/sendVerificationMessage'

    body = json.loads(send.content)
    assert set(body) == {'phone_number', 'code', 'ttl', 'payload', 'request_id'}  # no callback_url
    assert body['phone_number'] == PHONE
    assert body['code'] == CODE
    assert body['ttl'] == 300 and isinstance(body['ttl'], int)
    assert body['request_id'] == 'req_abc123'  # taken from the check's answer
    # Opaque id: short, and carries neither the phone nor the code.
    assert isinstance(body['payload'], str) and 1 <= len(body['payload'].encode()) <= 128
    assert PHONE.lstrip('+') not in body['payload'] and CODE not in body['payload']

    assert [(e['event'], e['log_level']) for e in logs] == [
        ('telegram_gateway_checked', 'info'),
        ('telegram_gateway_sent', 'info'),
    ]
    assert all(event['telegram_request_id'] == 'req_abc123' for event in logs)
    assert_nothing_secret(json.dumps(logs, default=str))


@pytest.mark.asyncio
async def test_request_id_is_passed_on_from_the_checks_answer_only():
    def check_answer(request: httpx.Request) -> httpx.Response:
        return ok_response(request_id='chk-777.a:b')

    _, error, seen, _ = await run(check=check_answer)
    assert error is None
    assert json.loads(seen[1].content)['request_id'] == 'chk-777.a:b'

    # A check answer without a request id: the send simply omits the field.
    _, error, seen, _ = await run(check=ok_response(request_id=None))
    assert error is None
    assert paths(seen) == [CHECK_PATH, SEND_PATH]
    assert 'request_id' not in json.loads(seen[1].content)

    # A request id that is not a plain identifier is neither logged nor sent back.
    _, error, seen, logs = await run(check=ok_response(request_id=f'{PHONE} {CODE}'))
    assert error is None
    assert 'request_id' not in json.loads(seen[1].content)
    assert_nothing_secret(json.dumps(logs, default=str))
    # ... and the send's own request id is never confused with the check's.
    assert json.loads(seen[0].content) == {'phone_number': PHONE}


@pytest.mark.asyncio
async def test_configured_url_timeout_and_ttl_are_used_and_payload_is_random_per_send():
    handler, seen = gateway()
    provider = make_provider(
        handler, base_url='https://gateway.example.test/', timeout_seconds=7.5, ttl_seconds=120
    )
    await provider.deliver(PHONE, CODE)
    await provider.deliver(PHONE, CODE)

    assert len(seen) == 4
    assert [str(request.url) for request in seen[:2]] == [
        'https://gateway.example.test/checkSendAbility',
        'https://gateway.example.test/sendVerificationMessage',
    ]
    for request in seen:
        assert request.extensions['timeout'] == {
            'connect': 7.5,
            'read': 7.5,
            'write': 7.5,
            'pool': 7.5,
        }
    first, second = (json.loads(request.content) for request in (seen[1], seen[3]))
    assert first['ttl'] == 120
    assert first['payload'] != second['payload']


# --- error mapping (applied to BOTH calls) ---------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', STAGES)
@pytest.mark.parametrize(
    'response',
    [
        error_response('PHONE_NUMBER_NOT_FOUND'),
        error_response('PHONE_NUMBER_NOT_OCCUPIED'),
        error_response('PHONE_NUMBER_NOT_AVAILABLE'),
        error_response('PHONE_NUMBER_INVALID'),
        error_response('phone_number_not_found'),  # case is not trusted
        error_response(' PHONE_NUMBER_NOT_FOUND '),
        # The HTTP status for an unknown number is undocumented: the body decides on a 4xx.
        error_response('PHONE_NUMBER_NOT_FOUND', status=400),
        error_response('PHONE_NUMBER_NOT_FOUND', status=404),
    ],
    ids=lambda response: f'{response.status_code}-{response.json()["error"].strip()}',
)
async def test_phone_number_errors_mean_the_channel_is_unavailable(stage, response):
    result, error, seen, logs = await run_failing(stage, response)
    assert result is None
    assert_failure(error, CHANNEL_UNAVAILABLE)
    assert paths(seen) == PATHS_UNTIL[stage]
    event = logs[-1]
    assert event['log_level'] == 'info'
    assert event['telegram_method'] == METHOD_OF[stage]
    assert event['telegram_error'] == response.json()['error'].strip().upper()
    assert_nothing_secret(json.dumps(logs, default=str))


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', STAGES)
@pytest.mark.parametrize(
    ('error_string', 'level'),
    [
        ('BALANCE_NOT_ENOUGH', 'error'),
        ('ACCESS_TOKEN_INVALID', 'error'),
        ('ACCESS_TOKEN_REQUIRED', 'error'),
        ('FLOOD_WAIT_5', 'warning'),
        ('REQUEST_ID_INVALID', 'warning'),
        ('CODE_INVALID', 'warning'),
        ('TTL_INVALID', 'warning'),
        ('SOMETHING_TELEGRAM_ADDED_LATER', 'warning'),
    ],
)
async def test_every_other_telegram_error_is_a_delivery_failure_with_the_right_log_level(
    stage, error_string, level
):
    result, error, seen, logs = await run_failing(stage, error_response(error_string))
    assert result is None
    assert_failure(error, DELIVERY_FAILED)
    assert paths(seen) == PATHS_UNTIL[stage]
    assert len(logs) == len(seen)
    event = logs[-1]
    assert (event['event'], event['log_level']) == ('telegram_gateway_rejected', level)
    assert event['telegram_method'] == METHOD_OF[stage]
    assert event['telegram_error'] == error_string
    assert event['http_status'] == 200


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', STAGES)
@pytest.mark.parametrize(
    'response',
    [
        pytest.param(httpx.Response(500, text='Internal Server Error'), id='http500-text'),
        pytest.param(httpx.Response(502, html='<html>Bad gateway</html>'), id='http502-html'),
        pytest.param(httpx.Response(429, json={'ok': False, 'error': 'FLOOD_WAIT_9'}), id='429'),
        pytest.param(error_response('ACCESS_TOKEN_INVALID', status=401), id='401-token'),
        # 5xx is never trusted, even when the body looks like a "no Telegram" answer.
        pytest.param(error_response('PHONE_NUMBER_NOT_FOUND', status=500), id='500-phone'),
        pytest.param(httpx.Response(200, text='not json'), id='non-json'),
        pytest.param(httpx.Response(200, content=b''), id='empty-body'),
        pytest.param(httpx.Response(200, json=[]), id='json-list'),
        pytest.param(httpx.Response(200, json={}), id='ok-missing'),
        pytest.param(httpx.Response(200, json={'result': {}}), id='ok-missing-with-result'),
        pytest.param(httpx.Response(200, json={'ok': 'true'}), id='ok-not-a-bool'),
        pytest.param(httpx.Response(200, json={'ok': False}), id='ok-false-no-error'),
        pytest.param(error_response(''), id='error-empty'),
        pytest.param(error_response(None), id='error-null'),
        pytest.param(error_response(404), id='error-not-a-string'),
        # A success flag on a failing HTTP status is not a delivery we can rely on.
        pytest.param(httpx.Response(500, json={'ok': True, 'result': {}}), id='500-ok-true'),
        pytest.param(httpx.Response(403, json={'ok': True, 'result': {}}), id='403-ok-true'),
    ],
)
async def test_malformed_or_http_error_answers_are_delivery_failures(stage, response):
    result, error, seen, logs = await run_failing(stage, response)
    assert result is None
    assert_failure(error, DELIVERY_FAILED)
    assert paths(seen) == PATHS_UNTIL[stage]
    assert logs[-1]['log_level'] in {'warning', 'error'}
    assert logs[-1]['telegram_method'] == METHOD_OF[stage]
    assert_nothing_secret(json.dumps(logs, default=str))


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', STAGES)
@pytest.mark.parametrize(
    'failure',
    [
        pytest.param(httpx.ReadTimeout('timed out'), id='read-timeout'),
        pytest.param(httpx.ConnectTimeout('timed out'), id='connect-timeout'),
        pytest.param(httpx.ConnectError('connection refused'), id='connect-error'),
        pytest.param(httpx.RemoteProtocolError('server disconnected'), id='protocol-error'),
        pytest.param(
            httpx.ConnectError(f'proxy: Authorization: Bearer {TOKEN} for {PHONE} code {CODE}'),
            id='message-carries-secrets',
        ),
        pytest.param(RuntimeError(f'unexpected: {TOKEN}'), id='unexpected-exception'),
    ],
)
async def test_transport_failures_are_delivery_failures_without_leaking_anything(stage, failure):
    result, error, seen, logs = await run_failing(stage, failure)
    assert result is None
    assert_failure(error, DELIVERY_FAILED)
    # Never retried (a blind retry of a send can be billed twice); a failed check sends nothing.
    assert paths(seen) == PATHS_UNTIL[stage]
    event = logs[-1]
    assert (event['event'], event['log_level']) == ('telegram_gateway_unreachable', 'warning')
    assert event['telegram_method'] == METHOD_OF[stage]
    assert event['error_type'] == type(failure).__name__
    # The raised error does not chain the httpx exception (its request holds the Bearer token).
    assert error.__cause__ is None and error.__context__ is None
    assert_nothing_secret(
        json.dumps(logs, default=str)
        + str(error)
        + repr(error)
        + error.message
        + ''.join(traceback.format_exception(error))
    )


@pytest.mark.asyncio
async def test_a_failed_check_means_no_code_is_ever_sent():
    for failure in (
        error_response('PHONE_NUMBER_NOT_FOUND'),
        error_response('BALANCE_NOT_ENOUGH'),
        httpx.Response(503, text='maintenance'),
        httpx.ConnectTimeout('timed out'),
    ):
        _, error, seen, _ = await run(check=failure)
        assert error is not None
        assert paths(seen) == [CHECK_PATH]
        assert all(CODE.encode() not in request.content for request in seen)


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', STAGES)
async def test_a_hostile_error_string_is_never_echoed_into_logs(stage):
    hostile = f'WEIRD {PHONE} {CODE} Bearer {TOKEN}\nforged_log_line'
    _, error, seen, logs = await run_failing(stage, error_response(hostile))
    assert_failure(error, DELIVERY_FAILED)
    assert paths(seen) == PATHS_UNTIL[stage]
    assert logs[-1]['telegram_error'] == 'UNPARSEABLE'
    assert_nothing_secret(json.dumps(logs, default=str))


@pytest.mark.asyncio
@pytest.mark.parametrize('stage', STAGES)
async def test_telegram_request_id_is_logged_on_errors_when_present_and_sane(stage):
    body = {'ok': False, 'error': 'BALANCE_NOT_ENOUGH', 'result': {'request_id': 'req-9f.1:x'}}
    _, error, _, logs = await run_failing(stage, httpx.Response(200, json=body))
    assert_failure(error, DELIVERY_FAILED)
    assert logs[-1]['telegram_request_id'] == 'req-9f.1:x'

    body['result'] = {'request_id': f'{PHONE} {CODE}'}  # not an identifier: dropped, not logged
    _, error, _, logs = await run_failing(stage, httpx.Response(200, json=body))
    assert logs[-1]['telegram_request_id'] is None
    assert_nothing_secret(json.dumps(logs, default=str))


# --- through the application -----------------------------------------------------------------


def make_settings(**overrides) -> Settings:
    values = {
        'environment': 'test',
        'database_url': 'sqlite+aiosqlite:///:memory:',
        'redis_url': 'redis://localhost:6379/15',
        'auth_otp_pepper': PEPPER,
        'telegram_gateway_token': None,
        **overrides,
    }
    return Settings(_env_file=None, **values)


@asynccontextmanager
async def make_client(provider):
    app = create_application(make_settings(), otp_provider=provider)
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.begin() as connection:
            await connection.run_sync(User.metadata.create_all)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            yield client, app


async def request_code(client):
    return await client.post('/api/v1/auth/otp/request', json={'phone_number': LOCAL_PHONE})


async def challenge_count(app) -> int:
    async with app.state.db_session_factory() as session:
        return await session.scalar(select(func.count()).select_from(OtpChallenge))


@pytest.mark.asyncio
async def test_login_through_telegram_end_to_end():
    handler, seen = gateway()
    async with make_client(make_provider(handler)) as (client, app):
        with capture_logs() as logs:
            response = await request_code(client)
        assert response.status_code == 202
        body = response.json()
        assert body['delivery_channel'] == 'telegram'
        assert 'development_otp' not in body

        # Telegram was asked about the number first, then got exactly the code we hashed; the
        # API response and logs never show it.
        assert paths(seen) == [CHECK_PATH, SEND_PATH]
        assert json.loads(seen[0].content) == {'phone_number': PHONE}
        sent = json.loads(seen[1].content)
        assert sent['phone_number'] == PHONE and sent['request_id'] == 'req_abc123'
        code = sent['code']
        assert len(code) == 6 and code.isdigit() and code not in response.text
        assert TOKEN not in response.text
        blob = json.dumps(logs, default=str)
        assert code not in blob and TOKEN not in blob and LOCAL_PHONE not in blob
        assert 'telegram_gateway_sent' in blob  # the capture really saw the adapter's log lines

        verified = await client.post(
            '/api/v1/auth/otp/verify', json={'phone_number': PHONE, 'code': code}
        )
        assert verified.status_code == 200
        tokens = verified.json()
        assert tokens['token_type'] == 'bearer' and tokens['refresh_token']
        me = await client.get(
            '/api/v1/auth/me', headers={'Authorization': f'Bearer {tokens["access_token"]}'}
        )
        assert me.status_code == 200 and me.json()['phone_number'] == PHONE


@pytest.mark.asyncio
async def test_number_without_telegram_gets_422_before_any_code_is_sent_and_no_cooldown():
    state = {'check': error_response('PHONE_NUMBER_NOT_FOUND')}
    handler, seen = gateway(check=lambda request: serve(state['check'], request))
    async with make_client(make_provider(handler)) as (client, app):
        first = await request_code(client)
        assert first.status_code == 422
        assert first.json()['code'] == 'otp_channel_unavailable'
        assert await challenge_count(app) == 0
        assert paths(seen) == [CHECK_PATH]  # the check said no: nothing was sent

        # No resend cooldown: an immediate retry reaches Telegram again and gets the same 422.
        second = await request_code(client)
        assert second.status_code == 422
        assert second.json()['code'] == 'otp_channel_unavailable'
        assert paths(seen) == [CHECK_PATH, CHECK_PATH]

        # And once the number can receive codes there is nothing to wait for.
        state['check'] = ok_response()
        third = await request_code(client)
        assert third.status_code == 202
        assert third.json()['delivery_channel'] == 'telegram'
        assert paths(seen) == [CHECK_PATH, CHECK_PATH, CHECK_PATH, SEND_PATH]
        assert await challenge_count(app) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('stage', 'outcome'),
    [
        ('check', error_response('BALANCE_NOT_ENOUGH')),
        ('check', httpx.Response(503, text='maintenance')),
        ('check', httpx.ReadTimeout('timed out')),
        ('send', error_response('BALANCE_NOT_ENOUGH')),
        ('send', httpx.Response(503, text='maintenance')),
        ('send', httpx.ReadTimeout('timed out')),
        # A send that Telegram rejects after a good check is still a neutral 502, not a 422.
        ('send', error_response('PHONE_NUMBER_NOT_FOUND', status=500)),
    ],
    ids=[
        'check-balance',
        'check-http503',
        'check-timeout',
        'send-balance',
        'send-http503',
        'send-timeout',
        'send-http500-phone',
    ],
)
async def test_provider_trouble_is_a_neutral_502_with_no_challenge_and_no_cooldown(stage, outcome):
    handler, seen = gateway(**{stage: outcome})
    async with make_client(make_provider(handler)) as (client, app):
        response = await request_code(client)
        assert response.status_code == 502
        body = response.json()
        assert body['code'] == 'otp_delivery_failed'
        assert body['message'] == 'The verification code could not be delivered; try again later'
        assert_nothing_secret(response.text)
        assert 'BALANCE' not in response.text  # Telegram's reason is for the logs only
        assert await challenge_count(app) == 0
        assert paths(seen) == PATHS_UNTIL[stage]

        again = await request_code(client)
        assert again.status_code == 502  # not 429: nothing was sent, so no cooldown started
        assert paths(seen) == PATHS_UNTIL[stage] * 2  # no hidden retries, one attempt per request


# --- serialising concurrent first requests (PostgreSQL only) ---------------------------------


class SlowProvider:
    """Stands in for a paid, slow Telegram send; counts how many sends were attempted."""

    def __init__(self) -> None:
        self.sends = 0

    async def deliver(self, phone_number: str, code: str) -> OtpDelivery:
        self.sends += 1
        await asyncio.sleep(0.3)
        return OtpDelivery(channel='telegram')


@pytest.mark.asyncio
async def test_concurrent_first_requests_for_one_phone_send_exactly_one_code():
    url = os.environ.get('YONDO_TEST_DATABASE_URL', '')
    if not url.startswith('postgresql'):
        pytest.skip('Requires YONDO_TEST_DATABASE_URL pointing to a migrated PostgreSQL database')
    provider = SlowProvider()
    app = create_application(make_settings(database_url=url), otp_provider=provider)
    async with app.router.lifespan_context(app):
        async with app.state.db_engine.begin() as connection:
            await connection.execute(text('TRUNCATE otp_challenges'))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test'
        ) as client:
            results = await asyncio.gather(
                *(request_code(client) for _ in range(3)), return_exceptions=True
            )
        # Without the per-phone advisory lock the losers also call the provider (paid) and then
        # fail on the primary key: an IntegrityError instead of a clean 429.
        assert all(isinstance(result, httpx.Response) for result in results), results
        assert sorted(result.status_code for result in results) == [202, 429, 429]
        assert {r.json()['code'] for r in results if r.status_code == 429} == {
            'otp_resend_cooldown'
        }
        assert provider.sends == 1
        assert await challenge_count(app) == 1
