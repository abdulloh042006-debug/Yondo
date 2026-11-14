"""Owner decisions 2026-11-14: photos (A), likes (B), filters/sort (C), stars (D), cards (E)."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from yondo_api.bookings.models import Booking, BookingStatus
from yondo_api.models.user import UserRoleType

from .conftest import create_profile, login, png
from .test_bookings import booking_payload, setup_bookable_companion

UP = '/api/v1/user-photos'
DISC = '/api/v1/discovery/companions'


async def upload(e, headers, url=f'{UP}/me'):
    return await e['client'].post(
        url, headers={**headers, 'Content-Type': 'image/png'}, content=png()
    )


async def me_id(e, headers):
    return (await e['client'].get('/api/v1/auth/me', headers=headers)).json()['id']


async def second_companion(e):
    """Make e['other'] a second publicly visible companion; returns its profile id."""
    application, profile = await create_profile(e, e['other'])
    swapped = {
        **e,
        'owner': e['other'],
        'owner_id': e['other_id'],
        'application': application,
        'profile': profile,
    }
    service = await setup_bookable_companion(swapped)
    return profile['id'], service


async def set_status(e, booking_id, status):
    async with e['app'].state.db_session_factory() as session:
        booking = await session.get(Booking, UUID(booking_id))
        booking.status = status
        await session.commit()


@pytest.mark.asyncio
async def test_customer_photos_crud_limit_and_order(prepared):
    e, c = prepared, prepared['client']
    assert (await c.get(f'{UP}/me')).status_code == 401
    ids = []
    for _ in range(6):
        result = await upload(e, e['customer'])
        assert result.status_code == 201, result.text
        assert 'storage_key' not in result.json() and 'user_id' not in result.json()
        ids.append(result.json()['id'])
    seventh = await upload(e, e['customer'])
    assert seventh.status_code == 422 and seventh.json()['code'] == 'photo_limit'
    order = await c.put(f'{UP}/me/order', headers=e['customer'], json={'photo_ids': ids[::-1]})
    assert order.status_code == 200
    assert [p['id'] for p in order.json()] == ids[::-1]
    bad = await c.put(f'{UP}/me/order', headers=e['customer'], json={'photo_ids': ids[:2]})
    assert bad.status_code == 422
    download = await c.get(f'{UP}/me/{ids[0]}/download', headers=e['customer'])
    assert download.status_code == 200 and '/users/' in download.json()['url']
    assert (await c.delete(f'{UP}/me/{ids[0]}', headers=e['customer'])).status_code == 204
    assert (await c.get(f'{UP}/me/{ids[0]}/download', headers=e['customer'])).status_code == 404
    assert len((await c.get(f'{UP}/me', headers=e['customer'])).json()) == 5
    # A slot frees up after delete; somebody else's photo is never reachable via /me.
    assert (await upload(e, e['customer'])).status_code == 201
    assert (await c.get(f'{UP}/me/{ids[1]}/download', headers=e['owner'])).status_code == 404
    assert (await c.delete(f'{UP}/me/{ids[1]}', headers=e['owner'])).status_code == 404


@pytest.mark.asyncio
async def test_companion_photos_capped_at_six(prepared):
    e = prepared
    for _ in range(6):
        assert (await upload(e, e['owner'], '/api/v1/companions/me/photos')).status_code == 201
    seventh = await upload(e, e['owner'], '/api/v1/companions/me/photos')
    assert seventh.status_code == 422 and seventh.json()['code'] == 'photo_limit'


@pytest.mark.asyncio
async def test_customer_photo_visibility_matrix(prepared):
    e, c = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    await create_profile(e, e['other'])  # another companion, not part of the booking
    stranger, _ = await login(c, e['app'], '901000005', UserRoleType.CUSTOMER)
    photo = (await upload(e, e['customer'])).json()
    stranger_photo = (await upload(e, stranger)).json()
    booking = await c.post(
        '/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id'])
    )
    assert booking.status_code == 201, booking.text
    bid = booking.json()['id']
    listing, download = f'{UP}/bookings/{bid}', f'{UP}/bookings/{bid}/{photo["id"]}/download'

    # Companion who received the request: allowed (list + download).
    seen = await c.get(listing, headers=e['owner'])
    assert seen.status_code == 200 and [p['id'] for p in seen.json()] == [photo['id']]
    assert 'user_id' not in seen.json()[0]
    assert (await c.get(download, headers=e['owner'])).status_code == 200
    # Still visible after the request is declined ("any booking between them").
    await set_status(e, bid, BookingStatus.CANCELLED)
    assert (await c.get(listing, headers=e['owner'])).status_code == 200
    # Another customer's photo id through this booking: not found.
    other_dl = f'{UP}/bookings/{bid}/{stranger_photo["id"]}/download'
    assert (await c.get(other_dl, headers=e['owner'])).status_code == 404
    # The customer himself: allowed.
    assert (await c.get(listing, headers=e['customer'])).status_code == 200
    assert len((await c.get(f'{UP}/me', headers=e['customer'])).json()) == 1
    # Stranger, other companion, anonymous, unknown booking: denied with no detail.
    for headers in (stranger, e['other'], e['admin']):
        assert (await c.get(listing, headers=headers)).status_code == 404
        assert (await c.get(download, headers=headers)).status_code == 404
    assert (await c.get(listing)).status_code == 401
    assert (await c.get(f'{UP}/bookings/{uuid4()}', headers=e['owner'])).status_code == 404
    # Admin reads through the admin routes (moderation), and can remove a photo.
    customer_id = await me_id(e, e['customer'])
    admin_list = await c.get(f'{UP}/admin/users/{customer_id}', headers=e['admin'])
    assert admin_list.status_code == 200 and len(admin_list.json()) == 1
    admin_dl = f'{UP}/admin/users/{customer_id}/{photo["id"]}/download'
    assert (await c.get(admin_dl, headers=e['admin'])).status_code == 200
    for headers in (e['owner'], e['customer'], stranger):
        denied = await c.get(f'{UP}/admin/users/{customer_id}', headers=headers)
        assert denied.status_code == 403
    # Never in discovery.
    public = (await c.get(DISC)).text + (await c.get(f'{DISC}/{e["profile"]["id"]}')).text
    assert photo['id'] not in public and customer_id not in public
    # A block (either direction) hides the photos from the companion.
    blocked = await c.put(f'/api/v1/safety/bookings/{bid}/block', headers=e['customer'])
    assert blocked.status_code in (200, 201, 204), blocked.text
    hidden = await c.get(listing, headers=e['owner'])
    assert hidden.status_code == 403 and hidden.json()['code'] == 'customer_photos_unavailable'
    unblock = f'/api/v1/safety/bookings/{bid}/block'
    assert (await c.delete(unblock, headers=e['customer'])).status_code in (200, 204)
    assert (await c.get(listing, headers=e['owner'])).status_code == 200
    # Moderation removal is audited and hides the photo.
    removed = await c.delete(f'{UP}/admin/users/{customer_id}/{photo["id"]}', headers=e['admin'])
    assert removed.status_code == 204
    assert (await c.get(listing, headers=e['owner'])).json() == []


@pytest.mark.asyncio
async def test_likes_are_public_counts_and_separate_from_favorites(prepared):
    e, c = prepared, prepared['client']
    await setup_bookable_companion(e)
    pid = e['profile']['id']
    url = f'{DISC}/{pid}/like'
    assert (await c.put(url)).status_code == 401
    liked = await c.put(url, headers=e['customer'])
    assert liked.status_code == 200, liked.text
    assert liked.json() == {'profile_id': pid, 'like_count': 1, 'liked_by_me': True}
    assert (await c.put(url, headers=e['customer'])).json()['like_count'] == 1  # idempotent
    assert (await c.put(url, headers=e['other'])).json()['like_count'] == 2  # any signed-in user
    own = await c.put(url, headers=e['owner'])
    assert own.status_code == 409 and own.json()['code'] == 'like_own_profile'
    assert (await c.put(f'{DISC}/{uuid4()}/like', headers=e['customer'])).status_code == 404
    anonymous = (await c.get(f'{DISC}/{pid}')).json()
    assert anonymous['like_count'] == 2 and anonymous['liked_by_me'] is None
    mine = (await c.get(f'{DISC}/{pid}', headers=e['customer'])).json()
    assert mine['liked_by_me'] is True
    listed = (await c.get(DISC, headers=e['admin'])).json()['items'][0]
    assert listed['like_count'] == 2 and listed['liked_by_me'] is False
    # A stale token does not break public discovery.
    stale = {'Authorization': 'Bearer not-a-token'}
    assert (await c.get(DISC, headers=stale)).json()['items'][0]['liked_by_me'] is None
    # Liking does not favourite (favourites stay private and separate).
    assert (await c.get('/api/v1/discovery/favorites', headers=e['customer'])).json() == []
    unliked = await c.delete(url, headers=e['customer'])
    assert unliked.json() == {'profile_id': pid, 'like_count': 1, 'liked_by_me': False}
    assert (await c.delete(url, headers=e['customer'])).status_code == 200


@pytest.mark.asyncio
async def test_stars_only_from_reviews_of_completed_meetings(prepared):
    e, c = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    bid = (
        await c.post('/api/v1/bookings', headers=e['customer'], json=booking_payload(service['id']))
    ).json()['id']
    url = f'/api/v1/reviews/bookings/{bid}'
    for status in (BookingStatus.PENDING, BookingStatus.ACCEPTED, BookingStatus.CONFIRMED,
                   BookingStatus.ACTIVE, BookingStatus.CANCELLED, BookingStatus.DISPUTED):
        await set_status(e, bid, status)
        early = await c.post(url, headers=e['customer'], json={'stars': 5})
        assert early.status_code == 409 and early.json()['code'] == 'review_not_ready'
    card = (await c.get(f'{DISC}/{e["profile"]["id"]}')).json()
    assert card['rating'] is None and card['review_count'] == 0 and card['meeting_count'] == 0
    await set_status(e, bid, BookingStatus.COMPLETED)
    assert (await c.post(url, headers=e['customer'], json={'stars': 4})).status_code == 201
    # The companion's review of the customer never counts toward the companion's stars.
    assert (await c.post(url, headers=e['owner'], json={'stars': 1})).status_code == 201
    card = (await c.get(f'{DISC}/{e["profile"]["id"]}')).json()
    assert (card['rating'], card['review_count'], card['meeting_count']) == (4.0, 1, 1)


@pytest.mark.asyncio
async def test_discovery_sort_and_rating_filter_with_stable_pagination(prepared):
    e, c = prepared, prepared['client']
    service_a = await setup_bookable_companion(e)
    a = e['profile']['id']
    b, _ = await second_companion(e)
    bid = (
        await c.post(
            '/api/v1/bookings', headers=e['customer'], json=booking_payload(service_a['id'])
        )
    ).json()['id']
    await set_status(e, bid, BookingStatus.COMPLETED)
    assert (
        await c.post(f'/api/v1/reviews/bookings/{bid}', headers=e['customer'], json={'stars': 4})
    ).status_code == 201
    for headers in (e['customer'], e['admin']):
        assert (await c.put(f'{DISC}/{b}/like', headers=headers)).status_code == 200

    async def order(**params):
        page = (await c.get(DISC, params=params)).json()
        return [item['id'] for item in page['items']], page['has_more']

    assert (await order(sort='rating'))[0] == [a, b]
    assert (await order(sort='meetings'))[0] == [a, b]
    assert (await order(sort='likes'))[0] == [b, a]
    assert (await order(sort='likes', limit=1)) == ([b], True)
    assert (await order(sort='likes', limit=1, offset=1)) == ([a], False)
    assert sorted((await order())[0]) == sorted([a, b])
    assert (await order(rating_min=4))[0] == [a]
    assert (await order(rating_min=4.5))[0] == []
    assert (await c.get(DISC, params={'sort': 'dislikes'})).status_code == 422
    assert (await c.get(DISC, params={'rating_min': 6})).status_code == 422
    # Card fields for the card feed: name, city, photos, services (price), stars, likes, meetings.
    card = (await c.get(DISC, params={'sort': 'likes'})).json()['items'][0]
    for field in ('display_name', 'city', 'photos', 'services', 'rating', 'like_count',
                  'meeting_count', 'verified'):
        assert field in card
    async with e['app'].state.db_session_factory() as session:
        assert (await session.scalar(select(Booking.status).where(Booking.id == UUID(bid)))) == (
            BookingStatus.COMPLETED
        )


@pytest.mark.asyncio
async def test_account_erasure_removes_photos_and_likes(prepared):
    from datetime import UTC, datetime

    from yondo_api.account.deletion import erase_account
    from yondo_api.discovery.models import CompanionLike
    from yondo_api.models.user import User
    from yondo_api.userphotos.models import UserPhoto

    e, c = prepared, prepared['client']
    await setup_bookable_companion(e)
    await upload(e, e['customer'])
    like = await c.put(f'{DISC}/{e["profile"]["id"]}/like', headers=e['customer'])
    assert like.status_code == 200
    customer_id = UUID(await me_id(e, e['customer']))
    async with e['app'].state.db_session_factory() as session:
        user = await session.get(User, customer_id)
        await erase_account(session, user, e['storage'], datetime.now(UTC))
        await session.commit()
        photos = list(await session.scalars(select(UserPhoto)))
        assert photos and all(p.deleted_at is not None and p.position is None for p in photos)
        assert list(await session.scalars(select(CompanionLike))) == []
    assert not any(key.startswith('users/') for key in e['storage'].objects)
    assert (await c.get(f'{DISC}/{e["profile"]["id"]}')).json()['like_count'] == 0
