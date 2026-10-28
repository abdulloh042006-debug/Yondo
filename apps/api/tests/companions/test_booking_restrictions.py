"""Admin-created temporary booking restrictions: enforcement, privacy, audit, lift, expiry."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from .cancellation_helpers import (
    ADMIN,
    API,
    STARTS,
    book,
    cancel,
    configure,
    freeze,
    notices,
    user_id,
)
from .test_bookings import booking_payload, setup_bookable_companion


async def restrict(e, who='customer', **body):
    uid = await user_id(e, e[who]) if who != 'owner' else e['owner_id']
    payload = {
        'user_id': uid,
        'role': 'companion' if who == 'owner' else 'customer',
        'reason': 'Repeated last-minute cancellations reviewed',
        **body,
    }
    return await e['client'].post(f'{ADMIN}/restrictions', headers=e['admin'], json=payload)


@pytest.mark.asyncio
async def test_admin_restricts_a_customer_who_then_gets_a_coded_error(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    existing = await book(e, service)
    created = await restrict(e, duration_days=3)
    assert created.status_code == 201, created.text
    row = created.json()
    assert row['active'] is True and row['role'] == 'customer' and row['lifted_at'] is None
    ends = datetime.fromisoformat(row['ends_at'])
    assert timedelta(days=2, hours=23) < ends - datetime.now(UTC) <= timedelta(days=3)

    blocked = await client.post(
        f'{API}/bookings', headers=e['customer'],
        json=booking_payload(service['id'], '2027-01-10T07:00:00Z'))
    assert blocked.status_code == 403
    body = blocked.json()
    assert body['code'] == 'booking_restricted'
    assert datetime.fromisoformat(body['details']['ends_at']) == ends
    assert body['details']['role'] == 'customer'
    # Neither the admin's reason nor admin ids are ever shown to the restricted user.
    assert 'reviewed' not in blocked.text and e['owner_id'] not in blocked.text
    # Restrictions never stop a user from cancelling or reading what they already have.
    assert (await cancel(e, 'customer', existing)).status_code == 200
    assert (await client.get(f'{API}/bookings', headers=e['customer'])).status_code == 200

    mine = (await client.get(f'{API}/cancellations/me/restrictions', headers=e['customer'])).json()
    assert [(m['id'], m['active']) for m in mine] == [(row['id'], True)]
    assert set(mine[0]) == {'id', 'role', 'starts_at', 'ends_at', 'active', 'lifted_at'}
    kinds = [n for n in await notices(e, 'customer') if n['kind'] == 'booking_restricted']
    assert len(kinds) == 1 and kinds[0]['booking_id'] is None
    assert kinds[0]['details']['ends_at'] == row['ends_at'] and 'reason' not in kinds[0]['details']


@pytest.mark.asyncio
async def test_lifting_unblocks_and_every_step_is_audited(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    row = (await restrict(e)).json()
    default_days = (datetime.fromisoformat(row['ends_at']) - datetime.fromisoformat(
        row['starts_at'])).days
    assert default_days == 7  # the configured placeholder default
    assert (await restrict(e)).json()['code'] == 'restriction_already_active'
    lift_url = f'{ADMIN}/restrictions/{row["id"]}/lift'
    for who in ('customer', 'owner'):
        assert (await client.post(lift_url, headers=e[who], json={'reason': 'Please lift'})
                ).status_code == 403
    assert (await client.post(lift_url, headers=e['admin'], json={'reason': 'short'})
            ).status_code == 422
    lifted = await client.post(lift_url, headers=e['admin'],
                               json={'reason': 'Appeal accepted after review'})
    assert lifted.status_code == 200, lifted.text
    assert lifted.json()['active'] is False and lifted.json()['lift_reason']
    assert lifted.json()['lifted_by'] and lifted.json()['lifted_at']
    again = await client.post(lift_url, headers=e['admin'], json={'reason': 'Lift it twice'})
    assert again.status_code == 409 and again.json()['code'] == 'restriction_not_active'
    await book(e, service)  # booking works again
    assert 'booking_restriction_lifted' in [n['kind'] for n in await notices(e, 'customer')]

    trail = (await client.get(
        f'{ADMIN}/audit', headers=e['admin'], params={'restriction_id': row['id']})).json()
    assert [t['action'] for t in trail] == ['restriction_lifted', 'restriction_created']
    lift, create = trail
    assert create['previous_state'] == {'active': False} and create['new_state']['active'] is True
    assert lift['previous_state']['active'] is True and lift['new_state']['active'] is False
    assert create['actor_user_id'] == lift['actor_user_id'] and lift['reason']
    assert all(t['actor_kind'] == 'admin' and t['created_at'] for t in trail)
    console = await client.get(f'{API}/admin/audit-events', headers=e['admin'],
                               params={'action_prefix': 'booking_restriction'})
    assert {a['action'] for a in console.json()} == {
        'booking_restriction:create', 'booking_restriction:lift'}
    listed = (await client.get(f'{ADMIN}/restrictions', headers=e['admin'],
                               params={'active': False})).json()
    assert [r['id'] for r in listed] == [row['id']]
    assert (await client.get(f'{ADMIN}/restrictions', headers=e['admin'],
                             params={'active': True})).json() == []


@pytest.mark.asyncio
async def test_a_restriction_ends_by_itself(prepared, monkeypatch):
    e = prepared
    service = await setup_bookable_companion(e)
    row = (await restrict(e, duration_days=1)).json()
    assert (await book(e, service, expect=403)).json()['code'] == 'booking_restricted'
    freeze(monkeypatch, datetime.fromisoformat(row['ends_at']) + timedelta(seconds=1))
    await book(e, service)
    lift = await e['client'].post(
        f'{ADMIN}/restrictions/{row["id"]}/lift', headers=e['admin'], json={'reason': 'Too late'})
    assert lift.status_code == 409  # already over
    # ...and a new one may be placed afterwards.
    assert (await restrict(e)).status_code == 201


@pytest.mark.asyncio
async def test_restriction_requests_are_validated(prepared):
    e, client = prepared, prepared['client']
    await setup_bookable_companion(e)
    customer = await user_id(e, e['customer'])
    admin_id = await user_id(e, e['admin'])
    post = lambda **b: client.post(  # noqa: E731
        f'{ADMIN}/restrictions', headers=e['admin'],
        json={'user_id': customer, 'role': 'customer', 'reason': 'Reviewed repeated no-shows', **b})
    too_long = await post(duration_days=31)  # the configured maximum is a placeholder 30
    assert too_long.status_code == 422 and too_long.json()['code'] == 'restriction_too_long'
    assert (await post(duration_days=0)).status_code == 422
    assert (await post(reason='short')).status_code == 422
    assert (await post(user_id=str(uuid4()))).json()['code'] == 'user_not_found'
    assert (await post(role='companion')).json()['code'] == 'restriction_role_mismatch'
    assert (await post(user_id=admin_id)).json()['code'] == 'admin_self_change_forbidden'
    configure(e, booking_restriction_max_days=60)
    assert (await post(duration_days=45)).status_code == 201
    for who in ('customer', 'owner'):
        assert (await client.post(
            f'{ADMIN}/restrictions', headers=e[who],
            json={'user_id': customer, 'role': 'customer', 'reason': 'Not an admin at all'}
        )).status_code == 403
    assert (await client.post(f'{ADMIN}/restrictions', json={})).status_code == 401


@pytest.mark.asyncio
async def test_restricted_companion_cannot_accept_but_can_still_decline_and_cancel(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    pending = await book(e, service, '2027-01-10T05:00:00Z', accept=False)
    declinable = await book(e, service, '2027-01-10T07:00:00Z', accept=False)
    accepted_first = await book(e, service, '2027-01-10T06:00:00Z')
    created = await restrict(e, 'owner', duration_days=2)
    assert created.status_code == 201, created.text
    refused = await client.post(f'{API}/bookings/{pending}/accept', headers=e['owner'])
    assert refused.status_code == 403 and refused.json()['code'] == 'booking_restricted'
    assert 'ends_at' in refused.json()['details']
    assert (await client.post(f'{API}/bookings/{declinable}/decline', headers=e['owner'],
                              json={})).status_code == 200
    assert (await cancel(e, 'owner', accepted_first)).status_code == 200
    # Customers cannot send new requests to them, and learn nothing about why.
    blocked = await book(e, service, '2027-01-10T06:00:00Z', expect=409)
    assert blocked.json()['code'] == 'companion_not_accepting_requests'
    assert 'details' not in blocked.json() and 'restrict' not in blocked.text.lower().replace(
        'companion_not_accepting_requests', '')
    assert 'booking_restricted' in [n['kind'] for n in await notices(e, 'owner')]


@pytest.mark.asyncio
async def test_restriction_closes_the_review_case_it_resolves(prepared):
    e, client = prepared, prepared['client']
    configure(e, cancellation_review_threshold=2, cancellation_warning_threshold=0)
    service = await setup_bookable_companion(e)
    for _ in range(2):
        await cancel(e, 'customer', await book(e, service))
    (case,) = (await client.get(f'{ADMIN}/cases', headers=e['admin'])).json()
    wrong = await client.post(
        f'{ADMIN}/restrictions', headers=e['admin'],
        json={'user_id': e['owner_id'], 'role': 'companion', 'case_id': case['id'],
              'reason': 'Case belongs to someone else'})
    assert wrong.status_code == 422 and wrong.json()['code'] == 'case_user_mismatch'
    done = await restrict(e, case_id=case['id'])
    assert done.status_code == 201 and done.json()['case_id'] == case['id']
    (closed,) = (await client.get(f'{ADMIN}/cases', headers=e['admin'],
                                  params={'status': 'closed'})).json()
    assert (closed['id'], closed['resolution'], closed['closed_by']) == (
        case['id'], 'restricted', done.json()['created_by'])
    actions = {t['action'] for t in (await client.get(
        f'{ADMIN}/audit', headers=e['admin'], params={'case_id': case['id']})).json()}
    assert actions == {'case_opened', 'case_closed', 'restriction_created'}
    assert STARTS  # frozen-clock helpers are shared with the other suites
