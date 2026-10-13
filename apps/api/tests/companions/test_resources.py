from uuid import uuid4

import pytest

from .conftest import approve, create_profile

ME = '/api/v1/companions/me'
SERVICE = {'service_code': 'coffee', 'price_minor': 12500, 'currency': 'UZS', 'unit_minutes': 60}
WINDOW = {
    'starts_at': '2027-01-01T10:00:00+05:00',
    'ends_at': '2027-01-01T11:00:00+05:00',
    'timezone': 'Asia/Tashkent',
}


async def test_service_crud_ownership_and_duplicate(prepared):
    e, c = prepared, prepared['client']
    await create_profile(e, e['other'])
    created = await c.post(f'{ME}/services', headers=e['owner'], json=SERVICE)
    assert created.status_code == 201
    data = created.json()
    assert data['price_minor'] == 12500
    assert isinstance(data['price_minor'], int)
    url = f'{ME}/services/{data["id"]}'
    assert (await c.put(url, headers=e['other'], json=SERVICE)).status_code == 404
    assert (await c.delete(url, headers=e['other'])).status_code == 404
    assert (await c.post(f'{ME}/services', headers=e['owner'], json=SERVICE)).status_code == 409
    changed = await c.put(url, headers=e['owner'], json={**SERVICE, 'price_minor': 20000})
    assert changed.json()['price_minor'] == 20000
    assert len((await c.get(f'{ME}/services', headers=e['owner'])).json()) == 1
    assert (await c.delete(url, headers=e['owner'])).status_code == 204
    assert (await c.delete(url, headers=e['owner'])).status_code == 404
    assert (await c.get(f'{ME}/services', headers=e['owner'])).json() == []


@pytest.mark.parametrize(
    'updates',
    [
        {'price_minor': -1},
        {'price_minor': 1.25},
        {'price_minor': 1.0},
        {'price_minor': True},
        {'price_minor': '123'},
        {'price_minor': 9223372036854775808},
        {'currency': 'usd'},
        {'currency': 'US'},
        {'unit_minutes': 0},
        {'unit_minutes': 1.5},
        {'unit_minutes': True},
        {'service_code': 'online_call'},
        {'service_code': 'custom_experience'},
        {'profile_id': str(uuid4())},
    ],
)
async def test_service_validation(prepared, updates):
    result = await prepared['client'].post(
        f'{ME}/services',
        headers=prepared['owner'],
        json={**SERVICE, **updates},
    )
    assert result.status_code == 422


async def test_service_config_hooks_and_exact_large_money(prepared):
    e, c, settings = prepared, prepared['client'], prepared['app'].state.settings
    settings.companion_allowed_currencies = ('UZS',)
    settings.companion_price_min_minor = 100
    settings.companion_price_max_minor = 50000
    settings.companion_allowed_unit_minutes = (30, 60)
    for change in [
        {'currency': 'USD'},
        {'price_minor': 1},
        {'price_minor': 50001},
        {'unit_minutes': 45},
    ]:
        result = await c.post(f'{ME}/services', headers=e['owner'], json={**SERVICE, **change})
        assert result.status_code == 422
    settings.companion_price_max_minor = None
    huge = 9_007_199_254_740_993
    result = await c.post(
        f'{ME}/services', headers=e['owner'], json={**SERVICE, 'price_minor': huge}
    )
    assert result.status_code == 201
    assert result.json()['price_minor'] == huge
    assert (await c.get(f'{ME}/services', headers=e['owner'])).json()[0]['price_minor'] == huge


async def test_service_edit_invalidates_approval(prepared):
    await approve(prepared)
    result = await prepared['client'].post(
        f'{ME}/services', headers=prepared['owner'], json=SERVICE
    )
    assert result.status_code == 201
    profile = (await prepared['client'].get(f'{ME}/profile', headers=prepared['owner'])).json()
    assert profile['content_status'] == 'draft'


async def test_availability_crud_overlap_adjacent_and_owner_scoping(prepared):
    e, c = prepared, prepared['client']
    await create_profile(e, e['other'])
    result = await c.post(f'{ME}/availability', headers=e['owner'], json=WINDOW)
    assert result.status_code == 201
    item = result.json()
    assert item['starts_at'] == '2027-01-01T05:00:00Z'
    url = f'{ME}/availability/{item["id"]}'
    assert (await c.post(f'{ME}/availability', headers=e['owner'], json=WINDOW)).status_code == 409
    assert (await c.post(f'{ME}/availability', headers=e['other'], json=WINDOW)).status_code == 201
    adjacent = {**WINDOW, 'starts_at': WINDOW['ends_at'], 'ends_at': '2027-01-01T12:00:00+05:00'}
    assert (
        await c.post(f'{ME}/availability', headers=e['owner'], json=adjacent)
    ).status_code == 201
    assert (await c.put(url, headers=e['owner'], json=WINDOW)).status_code == 200
    assert (await c.put(url, headers=e['owner'], json=adjacent)).status_code == 409
    assert (await c.put(url, headers=e['other'], json=WINDOW)).status_code == 404
    assert (await c.delete(url, headers=e['other'])).status_code == 404
    assert (await c.delete(url, headers=e['owner'])).status_code == 204
    assert (await c.delete(url, headers=e['owner'])).status_code == 404
    assert len((await c.get(f'{ME}/availability', headers=e['owner'])).json()) == 1


@pytest.mark.parametrize(
    'start,end',
    [
        ('04:00', '05:30'),
        ('05:30', '06:30'),
        ('05:15', '05:45'),
        ('04:00', '07:00'),
    ],
)
async def test_all_overlap_shapes(prepared, start, end):
    e, c = prepared, prepared['client']
    await c.post(f'{ME}/availability', headers=e['owner'], json=WINDOW)
    response = await c.post(
        f'{ME}/availability',
        headers=e['owner'],
        json={
            'starts_at': f'2027-01-01T{start}:00Z',
            'ends_at': f'2027-01-01T{end}:00Z',
            'timezone': 'UTC',
        },
    )
    assert response.status_code == 409
    assert response.json()['code'] == 'availability_overlap'


@pytest.mark.parametrize(
    'updates',
    [
        {'starts_at': '2027-01-01T10:00:00'},
        {'ends_at': '2027-01-01T11:00:00'},
        {'ends_at': WINDOW['starts_at']},
        {'ends_at': '2026-01-01T10:00:00Z'},
        {'timezone': 'Invalid/Zone'},
        {'timezone': '../etc/passwd'},
        {'timezone': ''},
        {'starts_at': None},
        {'profile_id': str(uuid4())},
    ],
)
async def test_availability_validation(prepared, updates):
    result = await prepared['client'].post(
        f'{ME}/availability',
        headers=prepared['owner'],
        json={**WINDOW, **updates},
    )
    assert result.status_code == 422
    assert result.json()['code'] == 'validation_error'


async def test_dst_offsets_are_unambiguous_instants(prepared):
    result = await prepared['client'].post(
        f'{ME}/availability',
        headers=prepared['owner'],
        json={
            'starts_at': '2027-11-07T01:30:00-04:00',
            'ends_at': '2027-11-07T01:30:00-05:00',
            'timezone': 'America/New_York',
        },
    )
    assert result.status_code == 201
    assert result.json()['starts_at'] == '2027-11-07T05:30:00Z'
    assert result.json()['ends_at'] == '2027-11-07T06:30:00Z'


async def test_availability_does_not_revoke_content_approval(prepared):
    await approve(prepared)
    await prepared['client'].post(f'{ME}/availability', headers=prepared['owner'], json=WINDOW)
    response = await prepared['client'].get(f'{ME}/profile', headers=prepared['owner'])
    assert response.json()['content_status'] == 'approved'
