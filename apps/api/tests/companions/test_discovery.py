from uuid import UUID

import pytest

from yondo_api.companions.integrations import IdentityStatus
from yondo_api.models.user import User

from .conftest import approve


@pytest.mark.asyncio
async def test_discovery_filters_and_public_profile_hide_private_fields(prepared):
    e, client = prepared, prepared['client']
    await client.post(
        '/api/v1/companions/me/services',
        headers=e['owner'],
        json={
            'service_code': 'coffee',
            'description': 'Coffee companion',
            'price_minor': 50000,
            'currency': 'UZS',
            'unit_minutes': 60,
        },
    )
    await client.post(
        '/api/v1/companions/me/availability',
        headers=e['owner'],
        json={
            'starts_at': '2027-01-10T10:00:00+05:00',
            'ends_at': '2027-01-10T13:00:00+05:00',
            'timezone': 'Asia/Tashkent',
        },
    )
    async with e['app'].state.db_session_factory() as session:
        user = await session.get(User, UUID(e['owner_id']))
        user.age, user.gender, user.city = 22, 'woman', 'Tashkent'
        await session.commit()
    await approve(e)
    e['identity'].status = IdentityStatus.VERIFIED
    activated = await client.post('/api/v1/companions/me/activate', headers=e['owner'])
    assert activated.status_code == 200

    response = await client.get(
        '/api/v1/discovery/companions',
        params={
            'city': 'tashkent',
            'gender': 'WOMAN',
            'age_min': 20,
            'age_max': 25,
            'service_code': 'coffee',
            'language': 'UZ',
            'interest': 'reading',
            'price_max_minor': 60000,
            'available_from': '2027-01-10T06:00:00Z',
            'available_until': '2027-01-10T07:00:00Z',
        },
    )
    assert response.status_code == 200, response.text
    page = response.json()
    assert len(page['items']) == 1
    assert page['items'][0]['id'] == e['profile']['id']
    assert page['items'][0]['verified'] is True
    assert page['items'][0]['services'][0]['price_minor'] == 50000
    assert 'phone_number' not in page['items'][0]
    assert 'activation_requested' not in page['items'][0]

    detail = await client.get(f'/api/v1/discovery/companions/{e["profile"]["id"]}')
    assert detail.status_code == 200
    assert detail.json()['display_name'] == 'Test companion'


@pytest.mark.asyncio
async def test_discovery_fails_closed_and_hides_revoked_identity(prepared):
    e, client = prepared, prepared['client']
    await approve(e)
    e['identity'].status = IdentityStatus.VERIFIED
    await client.post('/api/v1/companions/me/activate', headers=e['owner'])
    assert len((await client.get('/api/v1/discovery/companions')).json()['items']) == 1
    e['identity'].status = IdentityStatus.REJECTED
    assert (await client.get('/api/v1/discovery/companions')).json()['items'] == []
    hidden = await client.get(f'/api/v1/discovery/companions/{e["profile"]["id"]}')
    assert hidden.status_code == 404


@pytest.mark.asyncio
async def test_favorites_are_customer_scoped_and_only_show_visible_profiles(prepared):
    e, client = prepared, prepared['client']
    await approve(e)
    e['identity'].status = IdentityStatus.VERIFIED
    await client.post('/api/v1/companions/me/activate', headers=e['owner'])
    url = f'/api/v1/discovery/favorites/{e["profile"]["id"]}'
    added = await client.put(url, headers=e['customer'])
    assert added.status_code == 201, added.text
    listed = await client.get('/api/v1/discovery/favorites', headers=e['customer'])
    assert [item['id'] for item in listed.json()] == [e['profile']['id']]
    denied = await client.get('/api/v1/discovery/favorites', headers=e['owner'])
    assert denied.status_code == 403
    e['identity'].status = IdentityStatus.REJECTED
    assert (await client.get('/api/v1/discovery/favorites', headers=e['customer'])).json() == []
    assert (await client.delete(url, headers=e['customer'])).status_code == 204


@pytest.mark.asyncio
async def test_discovery_rejects_invalid_filter_combinations(prepared):
    client = prepared['client']
    age = await client.get('/api/v1/discovery/companions', params={'age_min': 30, 'age_max': 20})
    assert age.status_code == 422
    interval = await client.get(
        '/api/v1/discovery/companions',
        params={'available_from': '2027-01-10T10:00:00Z'},
    )
    assert interval.status_code == 422
    bounds = await client.get(
        '/api/v1/discovery/companions',
        params={'price_min_minor': 100, 'price_max_minor': 10},
    )
    assert bounds.status_code == 422


@pytest.mark.asyncio
async def test_discovery_fails_closed_when_identity_provider_is_unavailable(prepared):
    e = prepared
    await approve(e)
    e['identity'].status = IdentityStatus.VERIFIED
    await e['client'].post('/api/v1/companions/me/activate', headers=e['owner'])

    class UnavailableIdentity:
        async def get_status(self, session, user_id):
            raise OSError('private provider details')

    e['app'].state.identity_eligibility = UnavailableIdentity()
    response = await e['client'].get('/api/v1/discovery/companions')
    assert response.status_code == 503
    assert response.json()['code'] == 'identity_status_unavailable'
    assert 'private provider details' not in response.text
