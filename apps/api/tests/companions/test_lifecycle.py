from uuid import UUID

import pytest

from yondo_api.companions import service
from yondo_api.companions.integrations import IdentityStatus, UnconfiguredIdentityEligibility
from yondo_api.models.user import AccountStatus, User

from .conftest import approve

ROOT = '/api/v1/companions'
ME = ROOT + '/me'


async def test_application_creation_ownership_and_duplicate(env):
    client = env['client']
    response = await client.post(
        f'{ME}/application', headers=env['owner'], json={'statement': 'Hello'}
    )
    assert response.status_code == 201
    assert response.json()['user_id'] == env['owner_id']
    assert response.json()['status'] == 'draft'
    assert (await client.get(f'{ME}/application', headers=env['other'])).status_code == 404
    duplicate = await client.post(f'{ME}/application', headers=env['owner'], json={})
    assert duplicate.status_code == 409
    assert duplicate.json()['code'] == 'companion_record_conflict'
    assert (await client.get(f'{ME}/application', headers=env['owner'])).json()[
        'statement'
    ] == 'Hello'


async def test_profile_create_update_and_duplicate(prepared):
    e = prepared
    client = e['client']
    payload = {'display_name': 'Changed', 'bio': 'New bio', 'languages': ['uz'], 'interests': []}
    assert (await client.post(f'{ME}/profile', headers=e['owner'], json=payload)).status_code == 409
    result = await client.put(f'{ME}/profile', headers=e['owner'], json=payload)
    assert result.status_code == 200
    assert result.json()['bio'] == 'New bio'
    assert (await client.get(f'{ME}/profile', headers=e['other'])).status_code == 404


async def test_profile_requires_application(env):
    result = await env['client'].post(
        f'{ME}/profile',
        headers=env['owner'],
        json={'display_name': 'Test'},
    )
    assert result.status_code == 404


@pytest.mark.parametrize(
    'path', ['/application', '/profile', '/services', '/availability', '/photos', '/status']
)
async def test_customer_and_anonymous_cannot_access_companion_resources(prepared, path):
    client = prepared['client']
    assert (await client.get(ME + path, headers=prepared['customer'])).status_code == 403
    assert (await client.get(ME + path)).status_code == 401


@pytest.mark.parametrize(
    'path,payload',
    [
        ('/application', {}),
        ('/profile', {'display_name': 'Test'}),
        (
            '/services',
            {'service_code': 'coffee', 'price_minor': 10, 'currency': 'UZS', 'unit_minutes': 60},
        ),
        (
            '/availability',
            {
                'starts_at': '2027-01-01T10:00:00Z',
                'ends_at': '2027-01-01T11:00:00Z',
                'timezone': 'Asia/Tashkent',
            },
        ),
    ],
)
async def test_customer_cannot_write(prepared, path, payload):
    result = await prepared['client'].post(ME + path, headers=prepared['customer'], json=payload)
    assert result.status_code == 403


async def test_invalid_status_transitions_and_admin_authorization(prepared):
    e, payload = prepared, {'expected_revision': 2, 'decision': 'approve', 'note': 'Checked'}
    client = e['client']
    application_url = f'{ROOT}/admin/applications/{e["application"]["id"]}/decision'
    profile_url = f'{ROOT}/admin/profiles/{e["profile"]["id"]}/decision'
    assert (await client.post(application_url, headers=e['owner'], json=payload)).status_code == 403
    assert (await client.post(application_url, headers=e['admin'], json=payload)).status_code == 409
    assert (await client.post(profile_url, headers=e['admin'], json=payload)).status_code == 409
    assert (await client.post(f'{ME}/activate', headers=e['owner'])).status_code == 409
    assert (await client.post(f'{ME}/application/submit', headers=e['owner'])).status_code == 200
    assert (await client.post(f'{ME}/application/submit', headers=e['owner'])).status_code == 409
    assert (await client.put(f'{ME}/application', headers=e['owner'], json={})).status_code == 409


async def test_independent_approval_and_identity_gates(prepared):
    e, client = prepared, prepared['client']
    await approve(e)
    assert (await client.post(f'{ME}/activate', headers=e['owner'])).status_code == 409
    status = (await client.get(f'{ME}/status', headers=e['owner'])).json()
    assert status['blockers'] == ['identity_not_verified']
    assert status['content_status'] == 'approved'
    assert status['identity_status'] == 'unknown'
    e['identity'].status = IdentityStatus.VERIFIED
    active = await client.post(f'{ME}/activate', headers=e['owner'])
    assert active.status_code == 200
    assert active.json()['publicly_active'] is True
    assert (await client.post(f'{ME}/activate', headers=e['owner'])).status_code == 409
    e['identity'].status = IdentityStatus.REJECTED
    assert (await client.get(f'{ME}/status', headers=e['owner'])).json()['publicly_active'] is False


async def test_identity_verified_does_not_approve_content(prepared):
    e = prepared
    e['identity'].status = IdentityStatus.VERIFIED
    assert (await e['client'].post(f'{ME}/activate', headers=e['owner'])).status_code == 409
    status = (await e['client'].get(f'{ME}/status', headers=e['owner'])).json()
    assert set(status['blockers']) == {'application_not_approved', 'content_not_approved'}


async def test_unconfigured_identity_is_fail_closed(prepared):
    e = prepared
    await approve(e)
    e['app'].state.identity_eligibility = UnconfiguredIdentityEligibility()
    assert (await e['client'].post(f'{ME}/activate', headers=e['owner'])).status_code == 409


async def test_content_edits_revoke_approval_and_activation(prepared):
    e = prepared
    await approve(e)
    e['identity'].status = IdentityStatus.VERIFIED
    await e['client'].post(f'{ME}/activate', headers=e['owner'])
    response = await e['client'].put(
        f'{ME}/profile', headers=e['owner'], json={'display_name': 'New'}
    )
    assert response.json()['content_status'] == 'draft'
    assert response.json()['activation_requested'] is False
    assert (await e['client'].post(f'{ME}/activate', headers=e['owner'])).status_code == 409


@pytest.mark.parametrize('status', list(AccountStatus))
async def test_account_gate_and_dynamic_revocation(prepared, status):
    e = prepared
    await approve(e)
    e['identity'].status = IdentityStatus.VERIFIED
    await e['client'].post(f'{ME}/activate', headers=e['owner'])
    async with e['app'].state.db_session_factory() as session:
        user = await session.get(User, UUID(e['owner_id']))
        user.account_status = status
        await session.commit()
        profile = await service.profile_for(session, user.id)
        eligibility = await service.companion_status(session, user, profile, e['identity'])
        assert eligibility.publicly_active == (status == AccountStatus.ACTIVE)
    result = await e['client'].get(f'{ME}/status', headers=e['owner'])
    assert result.status_code == (
        200
        if status
        in {
            AccountStatus.ACTIVE,
            AccountStatus.VERIFICATION_PENDING,
        }
        else 403
    )


async def test_removed_role_is_not_publicly_active(prepared):
    e = prepared
    await approve(e)
    e['identity'].status = IdentityStatus.VERIFIED
    await e['client'].post(f'{ME}/activate', headers=e['owner'])
    await e['client'].put('/api/v1/auth/roles', headers=e['owner'], json={'roles': ['customer']})
    assert (await e['client'].get(f'{ME}/profile', headers=e['owner'])).status_code == 403
    async with e['app'].state.db_session_factory() as session:
        user = await session.get(User, UUID(e['owner_id']))
        profile = await service.profile_for(session, user.id)
        result = await service.companion_status(session, user, profile, e['identity'])
        assert result.publicly_active is False
        assert 'companion_role_required' in result.blockers


async def test_withdraw_and_resubmit_reuses_application(prepared):
    e, client = prepared, prepared['client']
    await approve(e)
    e['identity'].status = IdentityStatus.VERIFIED
    await client.post(f'{ME}/activate', headers=e['owner'])
    assert (await client.post(f'{ME}/application/withdraw', headers=e['owner'])).status_code == 200
    assert (await client.get(f'{ME}/status', headers=e['owner'])).json()['publicly_active'] is False
    assert (await client.post(f'{ME}/application/withdraw', headers=e['owner'])).status_code == 409
    edited = await client.put(
        f'{ME}/application', headers=e['owner'], json={'statement': 'Reapply'}
    )
    assert edited.json()['id'] == e['application']['id']
    assert edited.json()['status'] == 'draft'
    assert (await client.post(f'{ME}/application/submit', headers=e['owner'])).status_code == 200


async def test_rejection_and_resubmission(prepared):
    e, c = prepared, prepared['client']
    await c.post(f'{ME}/application/submit', headers=e['owner'])
    rejected = await c.post(
        f'{ROOT}/admin/applications/{e["application"]["id"]}/decision',
        headers=e['admin'],
        json={'expected_revision': 2, 'decision': 'reject', 'note': 'Needs changes'},
    )
    assert rejected.json()['status'] == 'rejected'
    assert (await c.put(f'{ME}/application', headers=e['owner'], json={})).json()[
        'status'
    ] == 'draft'
    await c.post(f'{ME}/profile/submit', headers=e['owner'])
    rejected = await c.post(
        f'{ROOT}/admin/profiles/{e["profile"]["id"]}/decision',
        headers=e['admin'],
        json={'expected_revision': 2, 'decision': 'reject', 'note': 'Needs changes'},
    )
    assert rejected.json()['content_status'] == 'rejected'
    assert (await c.post(f'{ME}/profile/submit', headers=e['owner'])).status_code == 200


async def test_deactivation(prepared):
    e = prepared
    assert (await e['client'].post(f'{ME}/deactivate', headers=e['owner'])).status_code == 409
    await approve(e)
    e['identity'].status = IdentityStatus.VERIFIED
    await e['client'].post(f'{ME}/activate', headers=e['owner'])
    assert (await e['client'].post(f'{ME}/deactivate', headers=e['owner'])).status_code == 204
    assert (await e['client'].get(f'{ME}/status', headers=e['owner'])).json()[
        'publicly_active'
    ] is False


@pytest.mark.parametrize(
    'extra', ['user_id', 'content_status', 'activation_requested', 'identity_status']
)
async def test_mass_assignment_is_rejected(prepared, extra):
    response = await prepared['client'].put(
        f'{ME}/profile',
        headers=prepared['owner'],
        json={
            'display_name': 'Test',
            extra: 'approved',
        },
    )
    assert response.status_code == 422
    assert response.json()['code'] == 'validation_error'
    assert response.json()['request_id']


@pytest.mark.parametrize(
    'payload',
    [
        {'display_name': ' '},
        {'display_name': 'Test', 'languages': ['en', 'EN']},
        {'display_name': 'Test', 'interests': ['  ']},
        {'display_name': 'Test', 'bio': None},
        {'display_name': 'Test', 'bio': 'x' * 8001},
    ],
)
async def test_profile_api_validation(prepared, payload):
    response = await prepared['client'].put(
        f'{ME}/profile', headers=prepared['owner'], json=payload
    )
    assert response.status_code == 422
    assert response.json()['code'] == 'validation_error'


async def test_no_public_discovery_or_out_of_scope_routes(prepared):
    paths = set(prepared['app'].openapi()['paths'])
    assert '/api/v1/companions' not in paths
    for path in paths:
        assert not any(
            word in path for word in ['booking', 'payment', '/chat', '/calls', '/discovery']
        )


async def test_identity_provider_failure_does_not_activate(prepared):
    await approve(prepared)

    class UnavailableIdentity:
        async def get_status(self, session, user_id):
            raise OSError('provider internal information')

    prepared['app'].state.identity_eligibility = UnavailableIdentity()
    result = await prepared['client'].post(f'{ME}/activate', headers=prepared['owner'])
    assert result.status_code == 503
    assert result.json()['code'] == 'identity_status_unavailable'
    assert 'provider internal information' not in result.text
    profile = await prepared['client'].get(f'{ME}/profile', headers=prepared['owner'])
    assert profile.json()['activation_requested'] is False
