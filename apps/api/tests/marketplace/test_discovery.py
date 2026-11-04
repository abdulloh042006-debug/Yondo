from datetime import UTC, datetime, timedelta

from support import API

from .conftest import hour_from_now

D = f'{API}/discovery'


async def test_only_fully_gated_companions_are_listed(market):
    visible = await market.companion('Malika')
    await market.companion('Hidden', verified=False, activate=False)
    inactive = await market.companion('Inactive', activate=False)
    response = await market.client.get(f'{D}/companions', headers=market.customer)
    assert response.status_code == 200, response.text
    body = response.json()
    assert [item['profile_id'] for item in body['items']] == [visible.profile_id]
    card = body['items'][0]
    assert card['display_name'] == 'Malika'
    assert card['badges'] == ['verified', 'new']
    assert card['primary_photo']['url'].startswith('https://storage.test/')
    assert card['min_price_minor'] == 100_000
    assert 'phone_number' not in card
    # Identity revocation hides the profile immediately even with activation intent.
    market.identity.statuses.pop(visible.user_id)
    assert (await market.client.get(f'{D}/companions', headers=market.customer)).json()[
        'total'
    ] == 0
    hidden = await market.client.get(
        f'{D}/companions/{inactive.profile_id}', headers=market.customer
    )
    assert hidden.status_code == 404


async def test_filters_and_sorting(market):
    cheap = await market.companion(
        'Aziza',
        services=(('coffee', 50_000, 60), ('walking', 70_000, 60)),
        age=22,
        languages=('uz',),
        interests=('Art',),
        location=(41.31, 69.28, 'Yunusobod'),
    )
    pricey = await market.companion(
        'Bekzod',
        services=(('cinema', 300_000, 120),),
        gender='male',
        age=30,
        languages=('ru', 'en'),
        interests=('Movies',),
        location=(41.35, 69.35, 'Chilonzor'),
        city='Samarkand',
    )
    get = lambda **params: market.client.get(  # noqa: E731
        f'{D}/companions', headers=market.customer, params=params
    )

    def ids(response):
        assert response.status_code == 200, response.text
        return [item['profile_id'] for item in response.json()['items']]

    assert ids(await get(service='cinema')) == [pricey.profile_id]
    assert ids(await get(gender='MALE')) == [pricey.profile_id]
    assert ids(await get(age_max=25)) == [cheap.profile_id]
    assert ids(await get(price_max=100_000)) == [cheap.profile_id]
    assert ids(await get(language='EN')) == [pricey.profile_id]
    assert ids(await get(interest='art')) == [cheap.profile_id]
    assert ids(await get(city='samarkand')) == [pricey.profile_id]
    assert ids(await get(q='aziz')) == [cheap.profile_id]
    assert ids(await get(q='%')) == []
    assert ids(await get(sort='price_asc')) == [cheap.profile_id, pricey.profile_id]
    assert ids(await get(sort='price_desc')) == [pricey.profile_id, cheap.profile_id]
    near = await get(latitude=41.311, longitude=69.279, radius_km=3, sort='distance')
    assert ids(near) == [cheap.profile_id]
    assert near.json()['items'][0]['distance_km'] < 3
    assert ids(await get(latitude=41.311, longitude=69.279, sort='distance')) == [
        cheap.profile_id,
        pricey.profile_id,
    ]
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()
    assert len(ids(await get(available_on=tomorrow))) in {1, 2}
    far = (datetime.now(UTC) + timedelta(days=30)).date().isoformat()
    assert ids(await get(available_on=far)) == []
    assert (await get(age_min=30, age_max=20)).status_code == 422
    assert (await get(radius_km=5)).status_code == 422
    assert (await get(unknown='x')).status_code == 422
    paged = await get(limit=1)
    assert paged.json()['total'] == 2 and paged.json()['next_offset'] == 1


async def test_public_profile_hides_private_fields_and_lists_free_slots(market):
    companion = await market.companion('Dilnoza', location=(41.299, 69.240, 'Mirobod'))
    response = await market.client.get(
        f'{D}/companions/{companion.profile_id}', headers=market.customer
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['area'] == 'Mirobod'
    assert 'approx_latitude' not in body and 'phone_number' not in body
    assert body['languages'] == ['uz', 'en']
    assert len(body['photos']) == 1 and body['service_details'][0]['service_code'] == 'coffee'
    assert body['availability'][0]['starts_at'] == hour_from_now(24).isoformat().replace(
        '+00:00', 'Z'
    )
    profile = await market.client.get(f'{API}/companions/me/profile', headers=companion.headers)
    assert profile.json()['approx_latitude'] == 41.3
    slots = await market.client.get(
        f'{D}/companions/{companion.profile_id}/availability', headers=market.customer
    )
    assert len(slots.json()) == 1


async def test_location_update_keeps_content_approval(market):
    companion = await market.companion('Nodira')
    located = await market.client.put(
        f'{API}/companions/me/location',
        headers=companion.headers,
        json={'area': 'Sergeli', 'latitude': 41.226789, 'longitude': 69.219999},
    )
    assert located.status_code == 200
    assert located.json()['content_status'] == 'approved'
    assert located.json()['approx_longitude'] == 69.22
    assert (
        await market.client.put(
            f'{API}/companions/me/location', headers=companion.headers, json={'latitude': 41.0}
        )
    ).status_code == 422


async def test_home_sections(market):
    await market.companion('Lola')
    response = await market.client.get(
        f'{D}/home', headers=market.customer, params={'latitude': 41.3, 'longitude': 69.2}
    )
    assert response.status_code == 200, response.text
    sections = {section['key']: section for section in response.json()['sections']}
    assert {'available_today', 'nearby', 'top_rated', 'new_companions', 'recommended'} <= set(
        sections
    )
    assert len(sections['new_companions']['items']) == 1
    assert response.json()['popular_experiences'] == [{'service_code': 'coffee', 'companions': 1}]


async def test_favorites(market):
    companion = await market.companion('Zarina')
    hidden = await market.companion('Gulnora', activate=False)
    path = f'{API}/favorites/companions'
    assert (
        await market.client.put(f'{path}/{companion.profile_id}', headers=market.customer)
    ).status_code == 204
    assert (
        await market.client.put(f'{path}/{companion.profile_id}', headers=market.customer)
    ).status_code == 204
    assert (
        await market.client.put(f'{path}/{hidden.profile_id}', headers=market.customer)
    ).status_code == 404
    listed = await market.client.get(path, headers=market.customer)
    assert [item['profile_id'] for item in listed.json()] == [companion.profile_id]
    assert listed.json()[0]['is_favorite'] is True
    only = await market.client.get(
        f'{D}/companions', headers=market.customer, params={'favorites_only': True}
    )
    assert only.json()['total'] == 1
    assert (
        await market.client.delete(f'{path}/{companion.profile_id}', headers=market.customer)
    ).status_code == 204
    assert (await market.client.get(path, headers=market.customer)).json() == []


async def test_discovery_requires_authentication(market):
    assert (await market.client.get(f'{D}/companions')).status_code == 401
