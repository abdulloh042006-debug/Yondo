from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from yondo_api.meetings import router as meeting_module
from yondo_api.safety.models import SafetyAcknowledgement, SafetyReport

from .test_bookings import booking_payload, setup_bookable_companion
from .test_phases11_15 import confirmed_booking


@pytest.mark.asyncio
async def test_admin_can_acknowledge_report_once_without_disclosing_review_notes(prepared):
    e, client = prepared, prepared['client']
    service = await setup_bookable_companion(e)
    booked = await client.post(
        '/api/v1/bookings', headers=e['customer'],
        json=booking_payload(service['id']),
    )
    assert booked.status_code == 201, booked.text
    report = await client.post(
        '/api/v1/safety/reports', headers=e['customer'],
        json={
            'reported_user_id': e['owner_id'],
            'booking_id': booked.json()['id'],
            'category': 'unsafe_behavior',
            'description': 'Private safety report requiring a review',
        },
    )
    assert report.status_code == 201, report.text
    rid = report.json()['id']
    root = '/api/v1/admin/safety'
    ack_url = f'{root}/reports/{rid}/acknowledge'
    assert (await client.get(f'{root}/reports', headers=e['owner'])).status_code == 403
    assert (
        await client.post(
            ack_url, headers=e['owner'], json={'note': 'Cannot acknowledge this'}
        )
    ).status_code == 403
    assert (
        await client.post(
            f'{root}/reports/{uuid4()}/acknowledge',
            headers=e['admin'], json={'note': 'Unknown case'},
        )
    ).status_code == 404
    summary = await client.get(f'{root}/summary', headers=e['admin'])
    assert summary.status_code == 200 and summary.json()['open_reports'] == 1
    queue = await client.get(f'{root}/reports', headers=e['admin'], params={'status': 'open'})
    assert queue.status_code == 200 and len(queue.json()) == 1
    assert queue.json()[0]['description'] == 'Private safety report requiring a review'
    accepted = await client.post(
        ack_url, headers=e['admin'], json={'note': 'Reviewed by a safety operator'}
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()['report_id'] == rid
    assert accepted.json()['alert_id'] is None
    second = await client.post(
        ack_url, headers=e['admin'], json={'note': 'Attempt to overwrite the audit'}
    )
    assert second.status_code == 200, second.text
    assert second.json()['id'] == accepted.json()['id']
    assert second.json()['note'] == accepted.json()['note']
    assert (await client.get(f'{root}/reports', headers=e['admin'],
                             params={'status': 'open'})).json() == []
    own = await client.get('/api/v1/safety/reports', headers=e['customer'])
    assert own.status_code == 200 and own.json()[0]['status'] == 'in_review'
    assert 'Reviewed by a safety operator' not in own.text
    async with e['app'].state.db_session_factory() as session:
        rows = list(
            await session.scalars(
                select(SafetyAcknowledgement).where(
                    SafetyAcknowledgement.report_id == UUID(rid)
                )
            )
        )
        assert len(rows) == 1
        stored = await session.get(SafetyReport, UUID(rid))
        assert stored.status == 'in_review'


@pytest.mark.asyncio
async def test_sos_is_admin_visible_but_never_marked_as_dispatched(prepared, monkeypatch):
    e, client = prepared, prepared['client']
    bid = await confirmed_booking(e)
    base = f'/api/v1/meetings/bookings/{bid}'
    assert (await client.post(base + '/check-in', headers=e['customer'])).status_code == 200
    assert (await client.post(base + '/check-in', headers=e['owner'])).status_code == 200

    class TestMeetingClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2027, 1, 10, 7, 0, tzinfo=UTC)

    monkeypatch.setattr(meeting_module, 'datetime', TestMeetingClock)
    assert (await client.post(base + '/start', headers=e['owner'])).status_code == 200
    reported = await client.post(
        f'/api/v1/safety/bookings/{bid}/sos',
        headers=e['customer'],
        params={'confirmed': True},
    )
    assert reported.status_code == 201, reported.text
    assert reported.json()['emergency_service_contacted'] is False
    alert_id = reported.json()['id']
    root = '/api/v1/admin/safety'
    assert (await client.get(f'{root}/alerts', headers=e['customer'])).status_code == 403
    pending = await client.get(
        f'{root}/alerts', headers=e['admin'], params={'unacknowledged_only': True}
    )
    assert pending.status_code == 200 and len(pending.json()) == 1
    assert pending.json()[0]['id'] == alert_id
    assert pending.json()[0]['emergency_service_contacted'] is False
    first = await client.post(
        f'{root}/alerts/{alert_id}/acknowledge',
        headers=e['admin'], json={'note': 'Recorded for manual incident triage'},
    )
    assert first.status_code == 200, first.text
    assert first.json()['alert_id'] == alert_id
    repeated = await client.post(
        f'{root}/alerts/{alert_id}/acknowledge',
        headers=e['admin'], json={'note': 'Cannot overwrite previous audit'},
    )
    assert repeated.status_code == 200
    assert repeated.json()['id'] == first.json()['id']
    assert (
        await client.get(
            f'{root}/alerts', headers=e['admin'],
            params={'unacknowledged_only': True},
        )
    ).json() == []
    summary = await client.get(f'{root}/summary', headers=e['admin'])
    assert summary.json()['unacknowledged_sos'] == 0
    assert summary.json()['emergency_dispatch_configured'] is False
