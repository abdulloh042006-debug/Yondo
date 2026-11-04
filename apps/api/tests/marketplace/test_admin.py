from datetime import timedelta

from support import API

from yondo_api.core.time import utc_now

from .helpers import B, completed_booking, confirmed_booking, request_booking, shift_booking

A = f'{API}/admin'


async def test_admin_endpoints_require_admin(market):
    for path in ('/users', '/bookings', '/payouts', '/analytics', '/disputes', '/sos', '/audit'):
        assert (await market.client.get(A + path, headers=market.customer)).status_code == 403
        assert (await market.client.get(A + path)).status_code == 401


async def test_user_search_detail_roles_and_moderation(market):
    companion = await market.companion()
    booking, payment = await confirmed_booking(market, companion)
    search = await market.client.get(f'{A}/users', headers=market.admin, params={'q': 'Malika'})
    assert [u['display_name'] for u in search.json()['items']] == ['Malika']
    assert search.json()['items'][0]['identity_status'] == 'verified'
    by_role = await market.client.get(f'{A}/users', headers=market.admin, params={'role': 'admin'})
    assert len(by_role.json()['items']) == 1
    detail = await market.client.get(f'{A}/users/{companion.user_id}', headers=market.admin)
    assert detail.json()['bookings_as_companion'] == 1
    assert (
        await market.client.post(
            f'{A}/users/{market.admin_id}/moderation',
            headers=market.admin,
            json={'action': 'ban', 'reason': 'x'},
        )
    ).status_code == 403
    suspended = await market.client.post(
        f'{A}/users/{companion.user_id}/moderation',
        headers=market.admin,
        json={'action': 'suspend', 'reason': 'Safety investigation'},
    )
    assert suspended.json()['account_status'] == 'suspended'
    assert (await market.client.get(f'{API}/auth/me', headers=companion.headers)).status_code == 401
    state = await market.client.get(f'{B}/{booking["id"]}', headers=market.customer)
    assert state.json()['status'] == 'cancelled'
    assert state.json()['cancellation_reason'] == 'admin_cancelled'
    assert state.json()['refund_minor'] == 110_000
    paid = await market.client.get(f'{API}/payments/{payment["id"]}', headers=market.customer)
    assert paid.json()['status'] == 'refunded'
    listed = await market.client.get(f'{API}/discovery/companions', headers=market.customer)
    assert listed.json()['total'] == 0
    reinstated = await market.client.post(
        f'{A}/users/{companion.user_id}/moderation',
        headers=market.admin,
        json={'action': 'reinstate', 'reason': 'Cleared'},
    )
    assert reinstated.json()['account_status'] == 'active'
    history = await market.client.get(f'{A}/users/{companion.user_id}', headers=market.admin)
    assert [h['action'] for h in history.json()['history']] == ['user.reinstate', 'user.suspend']
    granted = await market.client.post(
        f'{A}/users/{market.customer_id}/roles',
        headers=market.admin,
        json={'role': 'vendor', 'action': 'grant'},
    )
    assert 'vendor' in granted.json()['roles']
    demote_self = await market.client.post(
        f'{A}/users/{market.admin_id}/roles',
        headers=market.admin,
        json={'role': 'admin', 'action': 'revoke'},
    )
    assert demote_self.status_code == 403


async def test_queues_bookings_payouts_and_analytics(market):
    applicant = await market.companion('Queued', activate=False, verified=False)
    assert applicant
    companion = await market.companion()
    await request_booking(market, companion, start_hours=30)
    booking, _ = await completed_booking(market, companion)
    applications = await market.client.get(
        f'{A}/companions/applications', headers=market.admin, params={'status': 'approved'}
    )
    assert len(applications.json()['items']) == 2
    bookings = await market.client.get(
        f'{A}/bookings', headers=market.admin, params={'status': 'completed'}
    )
    assert bookings.json()['items'][0]['role'] == 'admin'
    detail = await market.client.get(f'{A}/bookings/{booking["id"]}', headers=market.admin)
    assert [p['status'] for p in detail.json()['payments']] == ['succeeded']
    assert 'payment_confirmed' in [e['event'] for e in detail.json()['events']]
    payouts = await market.client.get(f'{A}/payouts', headers=market.admin)
    payout = payouts.json()['items'][0]
    assert payout['status'] == 'scheduled' and payout['due'] is False
    early = await market.client.post(
        f'{A}/payouts/{payout["id"]}/mark-paid', headers=market.admin, json={'reference': 'TX1'}
    )
    assert early.json()['code'] == 'payout_not_due'
    from uuid import UUID

    from yondo_api.payments.models import Payout

    async with market.app.state.db_session_factory() as session:
        item = await session.get(Payout, UUID(payout['id']))
        item.available_at = utc_now() - timedelta(minutes=1)
        await session.commit()
    due = await market.client.get(f'{A}/payouts', headers=market.admin, params={'due_only': True})
    assert len(due.json()['items']) == 1
    paid = await market.client.post(
        f'{A}/payouts/{payout["id"]}/mark-paid', headers=market.admin, json={'reference': 'TX1'}
    )
    assert paid.json()['status'] == 'paid'
    earnings = await market.client.get(f'{API}/payouts/me', headers=companion.headers)
    assert earnings.json()['summary'][0]['paid_minor'] == 100_000
    metrics = await market.client.get(f'{A}/analytics', headers=market.admin)
    body = metrics.json()
    assert body['booking_requests'] == 2
    assert body['completed_bookings'] == 1
    assert body['active_companions'] == 1
    assert body['gross_volume_minor'] == 110_000
    assert body['platform_fee_minor'] == 10_000
    audit = await market.client.get(
        f'{A}/audit', headers=market.admin, params={'target_type': 'payout'}
    )
    assert audit.json()['items'][0]['action'] == 'payout.paid'


async def test_admin_cancel_and_dispute_resolution_and_review_hiding(market):
    companion = await market.companion()
    booking, payment = await confirmed_booking(market, companion)
    cancelled = await market.client.post(
        f'{A}/bookings/{booking["id"]}/cancel',
        headers=market.admin,
        json={'reason': 'Safety', 'refund_bps': 10_000},
    )
    assert cancelled.json()['status'] == 'cancelled'
    second, _ = await completed_booking(market, companion, start_hours=28)
    review = await market.client.post(
        f'{B}/{second["id"]}/review', headers=market.customer, json={'rating': 1, 'text': 'Bad'}
    )
    dispute = await market.client.post(
        f'{B}/{second["id"]}/dispute',
        headers=market.customer,
        json={'category': 'unsafe_behavior', 'description': 'Rude'},
    )
    dispute_id = dispute.json()['id']
    taken = await market.client.post(f'{A}/disputes/{dispute_id}/review', headers=market.admin)
    assert taken.json()['status'] == 'under_review'
    too_much = await market.client.post(
        f'{A}/disputes/{dispute_id}/resolve',
        headers=market.admin,
        json={'outcome': 'completed', 'refund_minor': 999_999, 'payout_minor': 0, 'note': 'x'},
    )
    assert too_much.json()['code'] == 'invalid_refund'
    resolved = await market.client.post(
        f'{A}/disputes/{dispute_id}/resolve',
        headers=market.admin,
        json={
            'outcome': 'completed',
            'refund_minor': 0,
            'payout_minor': 100_000,
            'note': 'No violation found',
        },
    )
    assert resolved.json()['status'] == 'resolved'
    hidden = await market.client.post(
        f'{A}/reviews/{review.json()["id"]}/moderation',
        headers=market.admin,
        json={'action': 'hide', 'reason': 'Retaliation during dispute'},
    )
    assert hidden.json()['status'] == 'hidden'
    card = (await market.client.get(f'{API}/discovery/companions', headers=market.customer)).json()
    assert card['items'][0]['stats']['rating_count'] == 0
    assert shift_booking and payment
