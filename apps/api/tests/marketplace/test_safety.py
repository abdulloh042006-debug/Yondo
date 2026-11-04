from datetime import timedelta

import pytest_asyncio
from sqlalchemy import select
from support import API, MemoryStorage, create_user, png, running_app

from yondo_api.core.time import utc_now
from yondo_api.models.user import UserRoleType
from yondo_api.notifications.models import Notification

from .conftest import Market
from .helpers import B, confirmed_booking, request_booking, shift_booking

V = f'{API}/verification/me'


@pytest_asyncio.fixture
async def db_market():
    """Market using the real database identity adapter (no test override)."""
    storage = MemoryStorage()
    async with running_app(identity=None, storage=storage) as (app, client):
        m = Market(app, client, None, storage)
        m.admin, m.admin_id = await m.user((UserRoleType.ADMIN,), name='Admin')
        m.customer, m.customer_id = await m.user(name='Sardor', gender='male', age=27)

        async def verify(user_id):
            raise AssertionError('use the verification API in this fixture')

        m.verify_identity = verify
        yield m


async def submit_verification(market, headers):
    client = market.client
    started = await client.post(V, headers=headers, json={'document_type': 'passport'})
    assert started.status_code == 201, started.text
    incomplete = await client.post(f'{V}/submit', headers=headers)
    assert incomplete.status_code == 422
    for part in ('document', 'selfie'):
        uploaded = await client.post(
            f'{V}/{part}', headers={**headers, 'Content-Type': 'image/png'}, content=png()
        )
        assert uploaded.status_code == 200, uploaded.text
    submitted = await client.post(f'{V}/submit', headers=headers)
    assert submitted.json()['status'] == 'pending'
    return submitted.json()


async def test_identity_verification_unlocks_companion_activation(db_market):
    market = db_market
    companion = await market.companion('Feruza', verified=False, activate=False)
    blocked = await market.client.post(f'{API}/companions/me/activate', headers=companion.headers)
    assert blocked.status_code == 409
    item = await submit_verification(market, companion.headers)
    assert len(market.storage.objects) == 3  # profile photo + document + selfie
    again = await market.client.post(
        V, headers=companion.headers, json={'document_type': 'id_card'}
    )
    assert again.status_code == 409
    queue = await market.client.get(f'{API}/admin/verifications', headers=market.admin)
    assert queue.json()['items'][0]['document_url'].startswith('https://storage.test/')
    self_decide = await market.client.post(
        f'{API}/admin/verifications/{item["id"]}/decision',
        headers=companion.headers,
        json={'decision': 'approve', 'note': 'ok'},
    )
    assert self_decide.status_code == 403
    decided = await market.client.post(
        f'{API}/admin/verifications/{item["id"]}/decision',
        headers=market.admin,
        json={'decision': 'approve', 'note': 'Documents match'},
    )
    assert decided.json()['status'] == 'verified'
    status = await market.client.get(f'{API}/companions/me/status', headers=companion.headers)
    assert status.json()['identity_status'] == 'verified'
    activated = await market.client.post(f'{API}/companions/me/activate', headers=companion.headers)
    assert activated.status_code == 200
    listed = await market.client.get(f'{API}/discovery/companions', headers=market.customer)
    assert listed.json()['total'] == 1


async def test_rejected_verification_can_restart(db_market):
    market = db_market
    headers, _ = await market.user()
    item = await submit_verification(market, headers)
    await market.client.post(
        f'{API}/admin/verifications/{item["id"]}/decision',
        headers=market.admin,
        json={'decision': 'reject', 'note': 'Blurry photo'},
    )
    mine = await market.client.get(V, headers=headers)
    assert mine.json()['status'] == 'rejected' and mine.json()['review_note'] == 'Blurry photo'
    restart = await market.client.post(V, headers=headers, json={'document_type': 'id_card'})
    assert restart.status_code == 201 and restart.json()['status'] == 'draft'


async def test_blocking_hides_profiles_and_prevents_booking(market):
    companion = await market.companion()
    block = await market.client.put(f'{API}/blocks/{companion.user_id}', headers=market.customer)
    assert block.status_code == 204
    listed = await market.client.get(f'{API}/discovery/companions', headers=market.customer)
    assert listed.json()['total'] == 0
    from .helpers import booking_payload

    booked = await market.client.post(B, headers=market.customer, json=booking_payload(companion))
    assert booked.status_code == 404
    blocks = await market.client.get(f'{API}/blocks', headers=market.customer)
    assert blocks.json()[0]['display_name'] == 'Malika'
    assert (
        await market.client.put(f'{API}/blocks/{market.customer_id}', headers=market.customer)
    ).status_code == 422
    await market.client.delete(f'{API}/blocks/{companion.user_id}', headers=market.customer)
    listed = await market.client.get(f'{API}/discovery/companions', headers=market.customer)
    assert listed.json()['total'] == 1


async def test_reports_flow(market):
    companion = await market.companion()
    booking = await request_booking(market, companion)
    report = await market.client.post(
        f'{API}/reports',
        headers=market.customer,
        json={
            'reported_user_id': str(companion.user_id),
            'booking_id': booking['id'],
            'category': 'inappropriate_request',
            'description': 'Asked to meet privately',
        },
    )
    assert report.status_code == 201, report.text
    stranger, stranger_id = await market.user()
    invalid = await market.client.post(
        f'{API}/reports',
        headers=market.customer,
        json={
            'reported_user_id': str(stranger_id),
            'booking_id': booking['id'],
            'category': 'fraud',
        },
    )
    assert invalid.status_code == 422
    bad_category = await market.client.post(
        f'{API}/reports',
        headers=market.customer,
        json={'reported_user_id': str(stranger_id), 'category': 'spam'},
    )
    assert bad_category.status_code == 422
    mine = await market.client.get(f'{API}/reports/me', headers=market.customer)
    assert len(mine.json()) == 1
    admin_list = await market.client.get(
        f'{API}/admin/reports', headers=market.admin, params={'status': 'open'}
    )
    assert admin_list.json()['items'][0]['category'] == 'inappropriate_request'
    resolved = await market.client.post(
        f'{API}/admin/reports/{report.json()["id"]}/status',
        headers=market.admin,
        json={'status': 'resolved', 'note': 'Warned the companion'},
    )
    assert resolved.json()['status'] == 'resolved'
    closed = await market.client.post(
        f'{API}/admin/reports/{report.json()["id"]}/status',
        headers=market.admin,
        json={'status': 'dismissed'},
    )
    assert closed.status_code == 409


async def test_trusted_contacts_share_and_sos(market):
    companion = await market.companion()
    url = f'{API}/safety/contacts'
    contact = await market.client.post(
        url,
        headers=market.customer,
        json={'name': 'Ona', 'phone_number': '90 123 45 67', 'relationship': 'mother'},
    )
    assert contact.status_code == 201
    assert contact.json()['phone_number'] == '+998901234567'
    for index in range(4):
        await market.client.post(
            url, headers=market.customer, json={'name': f'C{index}', 'phone_number': '901234567'}
        )
    limit = await market.client.post(
        url, headers=market.customer, json={'name': 'X', 'phone_number': '901234567'}
    )
    assert limit.json()['code'] == 'contact_limit'
    other, _ = await market.user()
    assert (
        await market.client.delete(f'{url}/{contact.json()["id"]}', headers=other)
    ).status_code == 404
    pending = await request_booking(market, companion, start_hours=30)
    early = await market.client.post(f'{B}/{pending["id"]}/share', headers=market.customer, json={})
    assert early.status_code == 409
    booking, _ = await confirmed_booking(market, companion)
    shared = await market.client.post(
        f'{B}/{booking["id"]}/share',
        headers=market.customer,
        json={'trusted_contact_id': contact.json()['id']},
    )
    assert shared.status_code == 201, shared.text
    view = await market.client.get(shared.json()['path'])
    assert view.status_code == 200
    assert view.json()['companion_name'] == 'Malika' and view.json()['sos_active'] is False
    assert 'phone' not in view.text
    assert (await market.client.get(f'{API}/safety/shared/forged')).status_code == 404
    soon = utc_now() + timedelta(minutes=10)
    await shift_booking(market, booking['id'], starts_at=soon, ends_at=soon + timedelta(hours=1))
    center = await market.client.get(f'{API}/safety/center', headers=market.customer)
    assert center.json()['active_booking_id'] == booking['id']
    assert {'service': 'unified_emergency', 'number': '112'} in center.json()['emergency_numbers']
    unconfirmed = await market.client.post(f'{API}/safety/sos', headers=market.customer, json={})
    assert unconfirmed.status_code == 422
    sos = await market.client.post(
        f'{API}/safety/sos',
        headers=market.customer,
        json={'confirm': True, 'latitude': 41.3, 'longitude': 69.2, 'message': 'Help'},
    )
    assert sos.status_code == 201
    assert sos.json()['booking_id'] == booking['id']
    assert len(sos.json()['trusted_contacts']) == 5
    async with market.app.state.db_session_factory() as session:
        alerts = list(
            await session.scalars(
                select(Notification).where(
                    Notification.user_id == market.admin_id, Notification.kind == 'sos_alert'
                )
            )
        )
    assert len(alerts) == 1
    assert (await market.client.get(shared.json()['path'])).json()['sos_active'] is True
    queue = await market.client.get(f'{API}/admin/sos', headers=market.admin)
    alert_id = queue.json()['items'][0]['id']
    ack = await market.client.post(
        f'{API}/admin/sos/{alert_id}/status',
        headers=market.admin,
        json={'status': 'acknowledged', 'note': 'Calling the user'},
    )
    assert ack.json()['status'] == 'acknowledged'


async def test_create_user_helper_roles(market):
    headers, _ = await create_user(market.app, market.client, '909999999', (UserRoleType.VENDOR,))
    me = await market.client.get(f'{API}/auth/me', headers=headers)
    assert me.json()['roles'] == ['vendor']
