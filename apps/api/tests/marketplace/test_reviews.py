from datetime import timedelta

from support import API

from yondo_api.core.time import utc_now

from .helpers import B, completed_booking, request_booking, shift_booking


async def test_two_way_reviews_and_public_aggregates(market):
    companion = await market.companion()
    pending = await request_booking(market, companion, start_hours=30)
    early = await market.client.post(
        f'{B}/{pending["id"]}/review', headers=market.customer, json={'rating': 5}
    )
    assert early.status_code == 409
    booking, _ = await completed_booking(market, companion)
    url = f'{B}/{booking["id"]}/review'
    bad_criteria = await market.client.post(
        url, headers=market.customer, json={'rating': 5, 'criteria': {'respect': 5}}
    )
    assert bad_criteria.json()['code'] == 'invalid_criteria'
    bad_tags = await market.client.post(
        url, headers=market.customer, json={'rating': 5, 'tags': ['made_up']}
    )
    assert bad_tags.json()['code'] == 'invalid_tags'
    assert (
        await market.client.post(url, headers=market.customer, json={'rating': 6})
    ).status_code == 422
    review = await market.client.post(
        url,
        headers=market.customer,
        json={
            'rating': 4,
            'criteria': {'punctuality': 5, 'communication': 4},
            'tags': ['punctual', 'friendly'],
            'text': 'Ajoyib suhbat',
        },
    )
    assert review.status_code == 201, review.text
    assert review.json()['direction'] == 'customer_to_companion'
    duplicate = await market.client.post(url, headers=market.customer, json={'rating': 3})
    assert duplicate.json()['code'] == 'review_exists'
    back = await market.client.post(
        url, headers=companion.headers, json={'rating': 5, 'criteria': {'respect': 5}}
    )
    assert back.status_code == 201
    both = await market.client.get(f'{B}/{booking["id"]}/reviews', headers=market.customer)
    assert len(both.json()) == 2
    card = (await market.client.get(f'{API}/discovery/companions', headers=market.customer)).json()[
        'items'
    ][0]
    assert card['stats'] == {'rating_average': 4.0, 'rating_count': 1, 'completed_bookings': 1}
    public = await market.client.get(
        f'{API}/discovery/companions/{companion.profile_id}/reviews', headers=market.customer
    )
    body = public.json()
    assert body['rating_average'] == 4.0
    assert body['criteria_average'] == {'communication': 4.0, 'punctuality': 5.0}
    assert body['tag_counts'] == {'punctual': 1, 'friendly': 1}
    assert body['items'][0]['author_name'] == 'Sardor'
    seen_by_companion = await market.client.get(f'{B}/{booking["id"]}', headers=companion.headers)
    assert seen_by_companion.json()['customer']['rating_average'] == 5.0
    received = await market.client.get(f'{API}/reviews/me', headers=companion.headers)
    assert received.json()['items'][0]['rating'] == 4


async def test_review_window_closes(market):
    companion = await market.companion()
    booking, _ = await completed_booking(market, companion)
    await shift_booking(market, booking['id'], ended_at=utc_now() - timedelta(days=30))
    late = await market.client.post(
        f'{B}/{booking["id"]}/review', headers=market.customer, json={'rating': 5}
    )
    assert late.json()['code'] == 'review_window_closed'
