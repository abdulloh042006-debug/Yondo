"""Admin console contract: queues, audit trail and authorization boundaries."""

from uuid import uuid4

import pytest

from .conftest import create_profile, login
from .test_bookings import booking_payload, setup_bookable_companion

ROOT = '/api/v1'
ADMIN_READS = [
    '/companions/admin/applications',
    '/admin/audit-events',
    '/admin/users',
    '/admin/summary',
    '/admin/bookings',
    '/admin/reports',
]


@pytest.mark.parametrize('path', ADMIN_READS)
async def test_admin_reads_reject_anonymous_customer_and_companion(prepared, path):
    client = prepared['client']
    assert (await client.get(ROOT + path)).status_code == 401
    assert (await client.get(ROOT + path, headers=prepared['customer'])).status_code == 403
    assert (await client.get(ROOT + path, headers=prepared['owner'])).status_code == 403
    assert (await client.get(ROOT + path, headers=prepared['admin'])).status_code == 200


async def test_application_queue_filters_paginates_and_hides_private_content(prepared):
    e, client = prepared, prepared['client']
    root = f'{ROOT}/companions'
    queue = await client.get(f'{root}/admin/applications', headers=e['admin'])
    assert queue.status_code == 200
    assert [row['status'] for row in queue.json()] == ['draft']
    assert (
        await client.get(
            f'{root}/admin/applications', headers=e['admin'], params={'status': 'submitted'}
        )
    ).json() == []
    assert (
        await client.get(
            f'{root}/admin/applications', headers=e['admin'], params={'status': 'bogus'}
        )
    ).status_code == 422
    await client.post(f'{root}/me/application/submit', headers=e['owner'])
    submitted = await client.get(
        f'{root}/admin/applications', headers=e['admin'], params={'status': 'submitted'}
    )
    row = submitted.json()[0]
    assert row['user_id'] == e['owner_id']
    assert row['display_name'] == 'Test companion'
    # The queue exposes lifecycle state only, never the applicant's statement or bio.
    assert 'statement' not in row and 'bio' not in row
    page = await client.get(
        f'{root}/admin/applications', headers=e['admin'], params={'limit': 1, 'offset': 1}
    )
    assert page.status_code == 200 and page.json() == []
    assert (
        await client.get(
            f'{root}/admin/applications', headers=e['admin'], params={'limit': 101}
        )
    ).status_code == 422


async def test_every_companion_decision_is_audited_with_actor_target_and_reason(prepared):
    e, client = prepared, prepared['client']
    root = f'{ROOT}/companions'
    await client.post(f'{root}/me/application/submit', headers=e['owner'])
    revision = (await client.get(f'{root}/me/application', headers=e['owner'])).json()['revision']
    decision = await client.post(
        f'{root}/admin/applications/{e["application"]["id"]}/decision',
        headers=e['admin'],
        json={'expected_revision': revision, 'decision': 'reject', 'note': 'Photo unclear'},
    )
    assert decision.status_code == 200
    stale = await client.post(
        f'{root}/admin/applications/{e["application"]["id"]}/decision',
        headers=e['admin'],
        json={'expected_revision': revision, 'decision': 'approve', 'note': 'Too late'},
    )
    assert stale.status_code == 409  # Failed decisions must not leave audit rows.
    events = (await client.get(f'{ROOT}/admin/audit-events', headers=e['admin'])).json()
    assert [(x['action'], x['target_id'], x['reason']) for x in events] == [
        ('companion_application:reject', e['owner_id'], 'Photo unclear')
    ]
    assert events[0]['admin_id'] != e['owner_id']
    filtered = await client.get(
        f'{ROOT}/admin/audit-events',
        headers=e['admin'],
        params={'action_prefix': 'companion_content'},
    )
    assert filtered.json() == []
    assert (
        await client.get(
            f'{ROOT}/admin/audit-events', headers=e['admin'], params={'action_prefix': "x'; --"}
        )
    ).status_code == 422


async def test_content_decision_and_user_status_change_share_one_audit_trail(prepared):
    e, client = prepared, prepared['client']
    root = f'{ROOT}/companions'
    await client.post(f'{root}/me/application/submit', headers=e['owner'])
    await client.post(f'{root}/me/profile/submit', headers=e['owner'])
    review = (
        await client.get(f'{root}/admin/users/{e["owner_id"]}/content-review', headers=e['admin'])
    ).json()
    approved = await client.post(
        f'{root}/admin/profiles/{e["profile"]["id"]}/decision',
        headers=e['admin'],
        json={
            'expected_revision': review['profile']['revision'],
            'decision': 'approve',
            'note': 'Content looks fine',
        },
    )
    assert approved.status_code == 200
    suspended = await client.post(
        f'{ROOT}/admin/users/{e["other_id"]}/status',
        headers=e['admin'],
        json={'status': 'suspended', 'reason': 'Repeated policy violations'},
    )
    assert suspended.status_code == 200
    actions = {
        x['action']
        for x in (await client.get(f'{ROOT}/admin/audit-events', headers=e['admin'])).json()
    }
    assert actions == {'companion_content:approve', 'account_status:suspended'}
    for_target = await client.get(
        f'{ROOT}/admin/audit-events', headers=e['admin'], params={'target_id': e['other_id']}
    )
    assert [x['action'] for x in for_target.json()] == ['account_status:suspended']
    # Content approval is not identity verification: activation stays gated.
    status = await client.get(f'{root}/me/status', headers=e['owner'])
    assert status.json()['publicly_active'] is False


async def test_self_approval_is_denied_and_not_audited(env):
    client, app = env['client'], env['app']
    both, both_id = await login(client, app, '901000099')
    async with app.state.db_session_factory() as session:
        from yondo_api.models.user import UserRole, UserRoleType

        session.add(UserRole(user_id=__import__('uuid').UUID(both_id), role=UserRoleType.ADMIN))
        await session.commit()
    application, _ = await create_profile(env, both)
    await client.post(f'{ROOT}/companions/me/application/submit', headers=both)
    denied = await client.post(
        f'{ROOT}/companions/admin/applications/{application["id"]}/decision',
        headers=both,
        json={'expected_revision': 1, 'decision': 'approve', 'note': 'Approving myself'},
    )
    assert denied.status_code == 403
    assert denied.json()['code'] == 'self_approval_forbidden'
    assert (await client.get(f'{ROOT}/admin/audit-events', headers=env['admin'])).json() == []


async def test_user_list_masks_phone_filters_and_protects_admins(prepared):
    e, client = prepared, prepared['client']
    listing = await client.get(f'{ROOT}/admin/users', headers=e['admin'])
    assert listing.status_code == 200
    body = listing.text
    assert '901000001' not in body and '901000004' not in body  # raw phones never leave
    assert all(len(row['phone_masked']) >= 3 for row in listing.json())
    admin_row = next(r for r in listing.json() if 'admin' in r['roles'])
    assert admin_row['roles'] == ['admin']
    by_phone = await client.get(
        f'{ROOT}/admin/users', headers=e['admin'], params={'phone': '901000001'}
    )
    assert [r['id'] for r in by_phone.json()] == [e['owner_id']]
    assert (
        await client.get(f'{ROOT}/admin/users', headers=e['admin'], params={'phone': '12'})
    ).status_code == 422
    assert (
        await client.get(
            f'{ROOT}/admin/users', headers=e['admin'], params={'phone': "1%' OR '1"}
        )
    ).status_code == 422
    blocked = await client.post(
        f'{ROOT}/admin/users/{admin_row["id"]}/status',
        headers=e['admin'],
        json={'status': 'banned', 'reason': 'Trying to ban an admin'},
    )
    assert blocked.status_code == 403
    assert (
        await client.post(
            f'{ROOT}/admin/users/{uuid4()}/status',
            headers=e['owner'],
            json={'status': 'banned', 'reason': 'Not an administrator'},
        )
    ).status_code == 403


async def test_safety_acknowledgement_is_audited_once(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booked = await client.post(
        f'{ROOT}/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    report = await client.post(
        f'{ROOT}/safety/reports',
        headers=e['customer'],
        json={
            'reported_user_id': e['owner_id'],
            'booking_id': booked.json()['id'],
            'category': 'unsafe_behavior',
            'description': 'Safety signal that needs a review',
        },
    )
    url = f'{ROOT}/admin/safety/reports/{report.json()["id"]}/acknowledge'
    for _ in range(2):  # Retried acknowledgements must not duplicate the audit row.
        assert (
            await client.post(url, headers=e['admin'], json={'note': 'Reviewed by operator'})
        ).status_code == 200
    events = (
        await client.get(
            f'{ROOT}/admin/audit-events',
            headers=e['admin'],
            params={'action_prefix': 'safety_report'},
        )
    ).json()
    assert [(x['action'], x['target_id']) for x in events] == [
        ('safety_report:acknowledge', e['owner_id'])
    ]
