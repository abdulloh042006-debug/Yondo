"""Stories: 24-hour availability / note cards. Public read, owner write, report, admin removal."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import update

from yondo_api.companions.integrations import IdentityStatus
from yondo_api.stories.models import CompanionStory

from .conftest import approve
from .test_photos import upload

ME = '/api/v1/companions/me/stories'
PUBLIC = '/api/v1/discovery'
ADMIN = '/api/v1/stories/admin'
NONE_ID = '00000000-0000-0000-0000-000000000001'


def iso(moment):
    return moment.strftime('%Y-%m-%dT%H:%M:%SZ')


async def activate(e, with_availability=True, with_photo=False):
    """An approved, verified, active companion with one service and (optionally) 6 free hours."""
    client = e['client']
    service = await client.post(
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
    assert service.status_code == 201, service.text
    now = datetime.now(UTC).replace(microsecond=0)
    e['window'] = (now + timedelta(hours=2), now + timedelta(hours=8))
    if with_availability:
        availability = await client.post(
            '/api/v1/companions/me/availability',
            headers=e['owner'],
            json={
                'starts_at': iso(e['window'][0]),
                'ends_at': iso(e['window'][1]),
                'timezone': 'Asia/Tashkent',
            },
        )
        assert availability.status_code == 201, availability.text
    if with_photo:  # before approval: a new photo sends the profile back to review
        e['photo'] = (await upload(e)).json()
    await approve(e)
    e['identity'].status = IdentityStatus.VERIFIED
    activated = await client.post('/api/v1/companions/me/activate', headers=e['owner'])
    assert activated.status_code == 200
    e['service'] = service.json()
    return e


async def post(e, **body):
    return await e['client'].post(ME, headers=e['owner'], json=body)


async def book(e, start, minutes):
    return await e['client'].post(
        '/api/v1/bookings',
        headers=e['customer'],
        json={
            'service_id': e['service']['id'],
            'starts_at': iso(start),
            'duration_minutes': minutes,
            'timezone': 'Asia/Tashkent',
            'meeting_place': 'Central public cafe',
        },
    )


@pytest.mark.asyncio
async def test_availability_story_shows_live_free_windows_to_anyone(prepared):
    e = await activate(prepared)
    created = await post(e, kind='availability', service_id=e['service']['id'])
    assert created.status_code == 201, created.text
    story = created.json()
    assert story['state'] == 'active'
    assert len(story['windows']) == 1
    assert story['service']['id'] == e['service']['id']
    ring = (await e['client'].get(f'{PUBLIC}/stories')).json()  # anonymous
    assert [(r['profile_id'], r['count'], r['has_availability']) for r in ring] == [
        (e['profile']['id'], 1, True)
    ]
    assert ring[0]['verified'] is True
    slides = await e['client'].get(f'{PUBLIC}/companions/{e["profile"]["id"]}/stories')
    assert slides.status_code == 200
    assert [s['id'] for s in slides.json()] == [story['id']]
    assert 'removal_note' not in slides.json()[0] and 'state' not in slides.json()[0]


@pytest.mark.asyncio
async def test_a_booking_shrinks_the_window_and_a_full_booking_hides_the_card(prepared):
    e = await activate(prepared)
    await post(e, kind='availability')
    start = e['window'][0]
    booked = await book(e, start, 60)
    assert booked.status_code == 201, booked.text
    url = f'{PUBLIC}/companions/{e["profile"]["id"]}/stories'
    window = (await e['client'].get(url)).json()[0]['windows'][0]
    assert window['starts_at'].startswith(iso(start + timedelta(hours=1))[:16])
    # Book the rest (5 h): nothing true is left to show, so the card and the ring disappear.
    rest = await book(e, start + timedelta(hours=1), 300)
    assert rest.status_code == 201, rest.text
    assert (await e['client'].get(f'{PUBLIC}/stories')).json() == []
    assert (await e['client'].get(url)).json() == []


@pytest.mark.asyncio
async def test_availability_story_needs_free_time(prepared):
    e = await activate(prepared, with_availability=False)
    refused = await post(e, kind='availability')
    assert refused.status_code == 409
    assert refused.json()['code'] == 'story_no_free_windows'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'caption',
    ['Call 90 123 45 67', 'write @someone', 'see https://x.test', 'my site shop.uz', 't.me/abc'],
)
async def test_captions_with_contact_details_are_refused(prepared, caption):
    e = await activate(prepared)
    refused = await post(e, kind='note', caption=caption)
    assert refused.status_code == 422
    assert refused.json()['code'] == 'story_caption_contact_info'


@pytest.mark.asyncio
async def test_note_needs_a_caption_and_may_use_own_photo_and_service_only(prepared):
    e = await activate(prepared, with_photo=True)
    assert (await post(e, kind='note', caption='   ')).json()['code'] == 'story_caption_required'
    assert (await post(e, kind='note', caption='x' * 81)).status_code == 422
    photo = e['photo']
    ok = await post(e, kind='note', caption='Bugun  qahva\nichamiz', photo_id=photo['id'])
    assert ok.status_code == 201, ok.text
    assert ok.json()['caption'] == 'Bugun qahva ichamiz'
    assert ok.json()['photo']['id'] == photo['id']
    assert (await post(e, kind='note', caption='Hi', photo_id=NONE_ID)).status_code == 404
    assert (await post(e, kind='note', caption='Hi', service_id=NONE_ID)).status_code == 404


@pytest.mark.asyncio
async def test_only_an_active_public_companion_may_post(prepared):
    e = prepared  # profile exists but was never approved or activated
    refused = await post(e, kind='note', caption='Hello')
    assert refused.status_code == 409
    assert refused.json()['code'] == 'story_profile_not_active'
    as_customer = await e['client'].post(
        ME, headers=e['customer'], json={'kind': 'note', 'caption': 'x'}
    )
    assert as_customer.status_code == 403


@pytest.mark.asyncio
async def test_quotas_and_owner_delete(prepared):
    e = await activate(prepared)
    ids = []
    for i in range(5):
        r = await post(e, kind='note', caption=f'Card {i}')
        assert r.status_code == 201, r.text
        ids.append(r.json()['id'])
    full = await post(e, kind='note', caption='One more')
    assert (full.status_code, full.json()['code']) == (409, 'story_limit_reached')
    assert (await e['client'].delete(f'{ME}/{ids[0]}', headers=e['owner'])).status_code == 204
    assert (await e['client'].delete(f'{ME}/{ids[0]}', headers=e['owner'])).status_code == 204
    stranger = await e['client'].delete(f'{ME}/{ids[1]}', headers=e['other'])
    assert stranger.status_code in (403, 404)
    assert (await post(e, kind='note', caption='Replacement')).status_code == 201
    own = (await e['client'].get(ME, headers=e['owner'])).json()
    assert sorted(s['state'] for s in own) == ['active'] * 5 + ['removed']
    # Deleting does not reset the daily budget: 6 posted so far, 4 more allowed, then 429.
    for i in range(4):
        await e['client'].delete(f'{ME}/{ids[1 + i]}', headers=e['owner'])
        assert (await post(e, kind='note', caption=f'Fill {i}')).status_code == 201
    # The daily budget (10) is spent: even with a free slot the next card is refused.
    own = (await e['client'].get(ME, headers=e['owner'])).json()
    first_active = next(s for s in own if s['state'] == 'active')
    await e['client'].delete(f'{ME}/{first_active["id"]}', headers=e['owner'])
    limited = await post(e, kind='note', caption='Too many')
    assert (limited.status_code, limited.json()['code']) == (429, 'story_rate_limited')


@pytest.mark.asyncio
async def test_expired_cards_leave_the_public_view_but_stay_visible_to_the_owner(prepared):
    e = await activate(prepared)
    first = (await post(e, kind='note', caption='Gone soon')).json()
    await post(e, kind='note', caption='Stays')
    async with e['app'].state.db_session_factory() as session:
        await session.execute(
            update(CompanionStory)
            .where(CompanionStory.id == UUID(first['id']))
            .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )
        await session.commit()
    slides = (await e['client'].get(f'{PUBLIC}/companions/{e["profile"]["id"]}/stories')).json()
    assert [s['caption'] for s in slides] == ['Stays']
    own = {s['caption']: s['state'] for s in (await e['client'].get(ME, headers=e['owner'])).json()}
    assert own == {'Gone soon': 'expired', 'Stays': 'active'}


@pytest.mark.asyncio
async def test_unlisted_companion_has_no_public_stories(prepared):
    e = await activate(prepared)
    await post(e, kind='note', caption='Hello')
    e['identity'].status = IdentityStatus.UNKNOWN  # no longer publicly active
    assert (await e['client'].get(f'{PUBLIC}/stories')).json() == []
    gone = await e['client'].get(f'{PUBLIC}/companions/{e["profile"]["id"]}/stories')
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_customer_reports_by_story_id_and_admin_removes_with_audit(prepared):
    e = await activate(prepared)
    story = (await post(e, kind='note', caption='Questionable')).json()
    c = e['client']
    url = f'{PUBLIC}/stories/{story["id"]}/report'
    assert (await c.post(url, json={'category': 'other'})).status_code == 401
    assert (await c.post(url, headers=e['owner'], json={'category': 'other'})).status_code == 422
    sent = await c.post(
        url, headers=e['customer'], json={'category': 'fake_profile', 'description': 'Looks fake'}
    )
    assert sent.status_code == 201, sent.text
    assert 'reported_user_id' not in sent.json()
    again = await c.post(url, headers=e['customer'], json={'category': 'other'})
    assert (again.status_code, again.json()['code']) == (409, 'story_already_reported')
    # The report lands in the normal safety queue against the author, with the story marker.
    reports = (await c.get('/api/v1/admin/safety/reports', headers=e['admin'])).json()
    assert any(
        r['reported_user_id'] == e['owner_id'] and story['id'] in r['description'] for r in reports
    )

    queue = (await c.get(ADMIN, headers=e['admin'])).json()
    assert [(q['id'], q['report_count'], q['state']) for q in queue] == [(story['id'], 1, 'active')]
    assert (await c.get(ADMIN, headers=e['customer'])).status_code == 403
    remove = f'{ADMIN}/{story["id"]}/remove'
    assert (await c.post(remove, headers=e['admin'], json={'note': 'x'})).status_code == 422
    removed = await c.post(remove, headers=e['admin'], json={'note': 'Not allowed'})
    assert removed.status_code == 200 and removed.json()['state'] == 'removed'
    twice = await c.post(remove, headers=e['admin'], json={'note': 'Not allowed'})
    assert twice.status_code == 409
    assert (await c.get(f'{PUBLIC}/stories')).json() == []
    own = (await c.get(ME, headers=e['owner'])).json()
    assert (own[0]['state'], own[0]['removal_note']) == ('removed', 'Not allowed')
    events = (
        await c.get(
            '/api/v1/admin/audit-events', headers=e['admin'], params={'action_prefix': 'story:'}
        )
    ).json()
    assert [(x['action'], x['reason']) for x in events] == [('story:remove', 'Not allowed')]
    gone = await c.post(url, headers=e['customer'], json={'category': 'other'})
    assert gone.status_code == 404
