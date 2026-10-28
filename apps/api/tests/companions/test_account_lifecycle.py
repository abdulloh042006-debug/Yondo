from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from yondo_api.account.deletion import process_due_deletions
from yondo_api.account.legal import LEGAL_DOCUMENTS
from yondo_api.bookings.models import Booking
from yondo_api.companions.integrations import IdentityStatus
from yondo_api.companions.models import CompanionProfile
from yondo_api.models.user import AccountStatus, User
from yondo_api.safety.models import TrustedContact

from .conftest import login
from .test_bookings import booking_payload, setup_bookable_companion

DELETION = '/api/v1/account/deletion'
CONFIRM = {'confirm': True}


@pytest.mark.asyncio
async def test_account_deletion_request_hide_cancel_and_erase(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    e['identity'].status = IdentityStatus.VERIFIED
    booking = await client.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert booking.status_code == 201, booking.text
    await client.post(
        '/api/v1/safety/trusted-contacts',
        headers=e['owner'],
        json={'name': 'Sister', 'phone_number': '+998901112233'},
    )

    unconfirmed = await client.post(
        '/api/v1/account/deletion', headers=e['owner'], json={'confirm': False}
    )
    assert unconfirmed.json()['code'] == 'deletion_confirmation_required'
    blocked = await client.post(DELETION, headers=e['owner'], json=CONFIRM)
    assert blocked.status_code == 409
    assert blocked.json()['code'] == 'deletion_open_bookings'
    cancel_url = f'/api/v1/bookings/{booking.json()["id"]}/cancel'
    cancelled = await client.post(cancel_url, headers=e['customer'], json={'reason': ''})
    assert cancelled.status_code == 200, cancelled.text

    requested = await client.post(
        '/api/v1/account/deletion', headers=e['owner'], json={'confirm': True}
    )
    assert requested.status_code == 201, requested.text
    state = requested.json()
    assert state['pending'] is True and state['window_days'] == 30
    due = datetime.fromisoformat(state['due_at'])
    assert timedelta(days=28) < due - datetime.now(UTC) <= timedelta(days=29)
    again = await client.post(DELETION, headers=e['owner'], json=CONFIRM)
    assert again.json()['code'] == 'deletion_already_requested'

    # Pending: hidden from discovery and not bookable.
    assert (await client.get('/api/v1/discovery/companions')).json()['items'] == []
    refused = await client.post(
        '/api/v1/bookings',
        headers=e['customer'],
        json=booking_payload(service['id'], start='2027-01-10T07:00:00Z'),
    )
    assert refused.status_code == 404

    # Cancel restores visibility.
    assert (await client.delete('/api/v1/account/deletion', headers=e['owner'])).status_code == 204
    assert len((await client.get('/api/v1/discovery/companions')).json()['items']) == 1
    missing = await client.delete('/api/v1/account/deletion', headers=e['owner'])
    assert missing.json()['code'] == 'deletion_not_found'

    # Not due yet: the admin-run job erases nothing.
    await client.post(DELETION, headers=e['owner'], json=CONFIRM)
    run = await client.post('/api/v1/admin/account-deletions/process-due', headers=e['admin'])
    assert run.status_code == 200, run.text
    assert run.json()['erased'] == []
    forbidden = await client.post(
        '/api/v1/admin/account-deletions/process-due', headers=e['customer']
    )
    assert forbidden.status_code == 403

    # 30 days later the daily job erases the account.
    owner_id = UUID(e['owner_id'])
    async with e['app'].state.db_session_factory() as session:
        erased, skipped = await process_due_deletions(
            session, e['storage'], datetime.now(UTC) + timedelta(days=30)
        )
    assert erased == [owner_id] and skipped == []
    async with e['app'].state.db_session_factory() as session:
        user = await session.get(User, owner_id)
        assert user.account_status == AccountStatus.DELETED
        assert user.phone_number.startswith('deleted-')
        assert user.city is None and user.age is None
        assert list(
            await session.scalars(select(TrustedContact).where(TrustedContact.owner_id == owner_id))
        ) == []
        profile = await session.get(CompanionProfile, UUID(e['profile']['id']))
        assert profile.display_name == 'deleted' and profile.bio == ''
        # Retained record: the booking still exists, now pointing at a de-identified account.
        assert await session.get(Booking, UUID(booking.json()['id'])) is not None
    assert (await client.get('/api/v1/auth/me', headers=e['owner'])).status_code in {401, 403}
    locked = await client.post(
        f'/api/v1/admin/users/{e["owner_id"]}/status',
        headers=e['admin'],
        json={'status': 'active', 'reason': 'Trying to revive a deleted account'},
    )
    assert locked.json()['code'] == 'account_deleted_status_locked'
    listed = await client.get('/api/v1/admin/account-deletions', headers=e['admin'])
    assert [r['status'] for r in listed.json()][:1] == ['completed']
    # The phone number is free again: logging in creates a brand-new account.
    _, new_id = await login(client, e['app'], '901000001')
    assert new_id != e['owner_id']


@pytest.mark.asyncio
async def test_legal_consents_are_versioned(prepared):
    e, client = prepared, prepared['client']
    versions = (await client.get('/api/v1/legal/versions')).json()
    assert versions == LEGAL_DOCUMENTS
    state = (await client.get('/api/v1/account/consents', headers=e['customer'])).json()
    assert {r['document'] for r in state['required']} == {'terms', 'privacy'}
    stale = await client.post(
        '/api/v1/account/consents',
        headers=e['customer'],
        json={'document': 'terms', 'version': 'old-version'},
    )
    assert stale.status_code == 409
    assert stale.json()['code'] == 'consent_version_outdated'
    for document in ('terms', 'privacy'):
        body = {'document': document, 'version': versions[document]}
        first = await client.post('/api/v1/account/consents', headers=e['customer'], json=body)
        assert first.status_code == 201, first.text
        repeat = await client.post('/api/v1/account/consents', headers=e['customer'], json=body)
        assert repeat.json()['accepted_at'] == first.json()['accepted_at']
    state = (await client.get('/api/v1/account/consents', headers=e['customer'])).json()
    assert state['required'] == []
    assert len(state['accepted']) == 2
    assert (await client.get('/api/v1/account/consents')).status_code == 401


@pytest.mark.asyncio
async def test_support_requests_and_admin_reply(prepared):
    e, client = prepared, prepared['client']
    short = await client.post(
        '/api/v1/support/requests',
        headers=e['customer'],
        json={'category': 'other', 'message': 'hi'},
    )
    assert short.status_code == 422
    created = await client.post(
        '/api/v1/support/requests',
        headers=e['customer'],
        json={'category': 'account', 'message': 'Cannot change my city field'},
    )
    assert created.status_code == 201, created.text
    assert created.json()['status'] == 'open' and created.json()['reply'] is None
    assert (await client.get('/api/v1/support/requests', headers=e['other'])).json() == []
    as_customer = await client.get('/api/v1/admin/support/requests', headers=e['customer'])
    assert as_customer.status_code == 403
    queue = await client.get(
        '/api/v1/admin/support/requests', headers=e['admin'], params={'status': 'open'}
    )
    assert [r['id'] for r in queue.json()] == [created.json()['id']]
    replied = await client.post(
        f'/api/v1/admin/support/requests/{created.json()["id"]}/reply',
        headers=e['admin'],
        json={'reply': 'Fixed, please try again.'},
    )
    assert replied.status_code == 200, replied.text
    assert replied.json()['status'] == 'answered'
    mine = (await client.get('/api/v1/support/requests', headers=e['customer'])).json()
    assert mine[0]['reply'] == 'Fixed, please try again.'
    audit = await client.get('/api/v1/admin/audit-events', headers=e['admin'])
    assert any(event['action'] == 'support_reply' for event in audit.json())
