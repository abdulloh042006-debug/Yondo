"""Shared helpers for the cancellation / restriction / abuse-guard tests."""

from datetime import UTC, datetime

from yondo_api.cancellations import abuse, admin, router, service

from .test_bookings import booking_payload

API = '/api/v1'
ADMIN = f'{API}/admin/cancellations'
STARTS = datetime(2027, 1, 10, 6, 0, tzinfo=UTC)  # booking_payload's default slot


def configure(e, **updates):
    """Override settings on the running app (the same pattern other suites use)."""
    e['app'].state.settings = e['app'].state.settings.model_copy(update=updates)


def freeze(monkeypatch, when: datetime):
    """Make the cancellation clock return `when` everywhere it is imported by name."""
    for module in (service, abuse, router, admin):
        monkeypatch.setattr(module, 'utcnow', lambda: when)


async def user_id(e, headers):
    return (await e['client'].get(f'{API}/auth/me', headers=headers)).json()['id']


async def book(e, service_item, start='2027-01-10T06:00:00Z', *, accept=True, expect=201):
    client = e['client']
    created = await client.post(
        f'{API}/bookings', headers=e['customer'], json=booking_payload(service_item['id'], start)
    )
    assert created.status_code == expect, created.text
    if expect != 201:
        return created
    booking_id = created.json()['id']
    if accept:
        accepted = await client.post(f'{API}/bookings/{booking_id}/accept', headers=e['owner'])
        assert accepted.status_code == 200, accepted.text
    return booking_id


async def cancel(e, who, booking_id, **body):
    return await e['client'].post(
        f'{API}/bookings/{booking_id}/cancel', headers=e[who], json=body
    )


async def admin_events(e, **params):
    response = await e['client'].get(f'{ADMIN}/events', headers=e['admin'], params=params)
    assert response.status_code == 200, response.text
    return response.json()


async def summary(e, uid, role='customer'):
    response = await e['client'].get(f'{ADMIN}/users/{uid}/summary', headers=e['admin'])
    assert response.status_code == 200, response.text
    return next(item for item in response.json()['roles'] if item['role'] == role)


async def notices(e, who):
    response = await e['client'].get(f'{API}/notifications', headers=e[who])
    assert response.status_code == 200, response.text
    return response.json()
