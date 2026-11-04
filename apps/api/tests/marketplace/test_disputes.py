from uuid import UUID

from sqlalchemy import select
from support import API, png

from yondo_api.payments.models import Payment, Payout
from yondo_api.payments.service import process_refunds
from yondo_api.safety.disputes import resolve_dispute

from .helpers import B, completed_booking, request_booking


async def test_dispute_with_evidence_and_admin_resolution(market):
    companion = await market.companion()
    pending = await request_booking(market, companion, start_hours=30)
    not_allowed = await market.client.post(
        f'{B}/{pending["id"]}/dispute',
        headers=market.customer,
        json={'category': 'fraud', 'description': 'x'},
    )
    assert not_allowed.status_code == 409
    booking, payment = await completed_booking(market, companion)
    created = await market.client.post(
        f'{B}/{booking["id"]}/dispute',
        headers=market.customer,
        json={'category': 'unsafe_behavior', 'description': 'Left early and was rude'},
    )
    assert created.status_code == 201, created.text
    dispute = created.json()
    assert dispute['previous_booking_status'] == 'completed'
    again = await market.client.post(
        f'{B}/{booking["id"]}/dispute',
        headers=companion.headers,
        json={'category': 'other', 'description': 'x'},
    )
    assert again.status_code == 409
    note = await market.client.post(
        f'{API}/disputes/{dispute["id"]}/evidence',
        headers=companion.headers,
        json={'note': 'My side of the story'},
    )
    assert note.status_code == 201
    image = await market.client.post(
        f'{API}/disputes/{dispute["id"]}/evidence/image',
        headers={**market.customer, 'Content-Type': 'image/png'},
        content=png(),
    )
    assert image.status_code == 201, image.text
    stranger, _ = await market.user()
    assert (
        await market.client.get(f'{B}/{booking["id"]}/dispute', headers=stranger)
    ).status_code == 404
    view = await market.client.get(f'{B}/{booking["id"]}/dispute', headers=market.customer)
    assert [e['kind'] for e in view.json()['evidence']] == ['text', 'image']
    assert view.json()['evidence'][1]['url'].startswith('https://storage.test/')
    async with market.app.state.db_session_factory() as session:
        payout = (await session.scalars(select(Payout))).one()
        assert payout.status == 'held'
        from yondo_api.models.user import User

        admin = await session.get(User, market.admin_id)
        resolved = await resolve_dispute(
            session,
            UUID(dispute['id']),
            admin,
            outcome='completed',
            refund_minor=30_000,
            payout_minor=80_000,
            note='Partial refund',
        )
        assert resolved.status == 'resolved'
        await process_refunds(session, market.app.state)
        refreshed = await session.get(Payment, UUID(payment['id']))
        await session.refresh(refreshed)
        assert refreshed.status == 'partially_refunded' and refreshed.refunded_minor == 30_000
        payout = (await session.scalars(select(Payout))).one()
        await session.refresh(payout)
        assert (payout.status, payout.amount_minor) == ('scheduled', 80_000)
    state = await market.client.get(f'{B}/{booking["id"]}', headers=market.customer)
    assert state.json()['status'] == 'completed'
    closed = await market.client.post(
        f'{API}/disputes/{dispute["id"]}/evidence', headers=market.customer, json={'note': 'more'}
    )
    assert closed.status_code == 409
