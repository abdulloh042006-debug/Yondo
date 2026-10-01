import asyncio
import threading
from io import BytesIO

import pytest
from PIL import Image

from yondo_api.companions import photos, service
from yondo_api.companions.models import CompanionPhoto

from .conftest import MemoryStorage, create_profile, login
from .test_photos import upload

ME = '/api/v1/companions/me'
ADMIN = '/api/v1/companions/admin'


async def snapshot(e):
    response = await e['client'].get(
        f'{ADMIN}/users/{e["owner_id"]}/content-review', headers=e['admin']
    )
    assert response.status_code == 200
    return response.json()


async def decide(e, resource, revision, decision='approve'):
    kind = 'application' if resource == 'applications' else 'profile'
    return await e['client'].post(
        f'{ADMIN}/{resource}/{e[kind]["id"]}/decision',
        headers=e['admin'],
        json={'expected_revision': revision, 'decision': decision, 'note': 'Reviewed'},
    )


async def test_stale_application_after_edit_resubmit(prepared):
    e, c = prepared, prepared['client']
    old = (await c.post(f'{ME}/application/submit', headers=e['owner'])).json()['revision']
    assert (await decide(e, 'applications', old, 'reject')).status_code == 200
    assert (
        await c.put(f'{ME}/application', headers=e['owner'], json={'statement': 'Changed'})
    ).status_code == 200
    new = (await c.post(f'{ME}/application/submit', headers=e['owner'])).json()['revision']
    for decision in ['approve', 'reject']:
        stale = await decide(e, 'applications', old, decision)
        assert stale.status_code == 409
        assert stale.json()['code'] == 'stale_companion_revision'
    assert (await decide(e, 'applications', new)).status_code == 200


@pytest.mark.parametrize(
    'mutation',
    [
        'profile',
        'service_add',
        'service_edit',
        'service_delete',
        'photo_add',
        'photo_delete',
        'caption',
        'order',
        'resubmit',
    ],
)
async def test_stale_aggregate_after_mutation_resubmit(prepared, mutation):
    e, c, owner = prepared, prepared['client'], prepared['owner']
    payload = {'service_code': 'coffee', 'price_minor': 10, 'currency': 'UZS', 'unit_minutes': 60}
    item = (await c.post(f'{ME}/services', headers=owner, json=payload)).json()
    a, b = (await upload(e)).json(), (await upload(e)).json()
    await c.post(f'{ME}/profile/submit', headers=owner)
    reviewed = await snapshot(e)
    old = reviewed['profile']['revision']
    assert len(reviewed['services']) == 1 and len(reviewed['photos']) == 2
    if mutation == 'profile':
        result = await c.put(f'{ME}/profile', headers=owner, json={'display_name': 'Changed'})
    elif mutation == 'service_add':
        result = await c.post(
            f'{ME}/services', headers=owner, json={**payload, 'service_code': 'walking'}
        )
    elif mutation == 'service_edit':
        result = await c.put(
            f'{ME}/services/{item["id"]}', headers=owner, json={**payload, 'price_minor': 11}
        )
    elif mutation == 'service_delete':
        result = await c.delete(f'{ME}/services/{item["id"]}', headers=owner)
    elif mutation == 'photo_add':
        result = await upload(e)
    elif mutation == 'photo_delete':
        result = await c.delete(f'{ME}/photos/{a["id"]}', headers=owner)
    elif mutation == 'caption':
        result = await c.patch(f'{ME}/photos/{a["id"]}', headers=owner, json={'caption': 'Changed'})
    elif mutation == 'order':
        result = await c.put(
            f'{ME}/photos/order', headers=owner, json={'photo_ids': [b['id'], a['id']]}
        )
    else:
        result = await decide(e, 'profiles', old, 'reject')
    assert result.status_code in {200, 201, 204}, result.text
    await c.post(f'{ME}/profile/submit', headers=owner)
    current = await snapshot(e)
    assert current['profile']['revision'] > old
    for decision in ['approve', 'reject']:
        stale = await decide(e, 'profiles', old, decision)
        assert stale.status_code == 409
        assert stale.json()['code'] == 'stale_companion_revision'
    assert (await decide(e, 'profiles', current['profile']['revision'])).status_code == 200


async def test_revision_is_required_and_not_owner_writable(prepared):
    e = prepared
    response = await e['client'].post(
        f'{ADMIN}/profiles/{e["profile"]["id"]}/decision',
        headers=e['admin'],
        json={'decision': 'approve', 'note': 'No revision'},
    )
    assert response.status_code == 422
    response = await e['client'].put(
        f'{ME}/profile',
        headers=e['owner'],
        json={'display_name': 'X', 'revision': 9},
    )
    assert response.status_code == 422


@pytest.mark.parametrize('format', ['JPEG', 'WEBP'])
async def test_real_exif_gps_orientation_and_supported_formats(prepared, format):
    image = Image.new('RGB', (24, 16), 'red')
    exif = Image.Exif()
    exif[274] = 6
    exif[315] = 'Private author'
    exif[34853] = {1: 'N', 2: (41.0, 0.0, 0.0), 3: 'E', 4: (69.0, 0.0, 0.0)}
    data = BytesIO()
    image.save(data, format=format, exif=exif)
    with Image.open(BytesIO(data.getvalue())) as source:
        assert source.getexif()[274] == 6
        assert source.getexif().get_ifd(34853)[1] == 'N'
    result = await prepared['client'].post(
        f'{ME}/photos',
        headers={**prepared['owner'], 'Content-Type': f'image/{format.lower()}'},
        content=data.getvalue(),
    )
    assert result.status_code == 201
    assert (result.json()['width'], result.json()['height']) == (16, 24)
    stored, _ = next(iter(prepared['storage'].objects.values()))
    with Image.open(BytesIO(stored)) as clean:
        assert clean.size == (16, 24)
        assert not clean.getexif()
        assert 'exif' not in clean.info


@pytest.mark.parametrize('format', ['PNG', 'WEBP'])
async def test_animated_images_rejected(prepared, format):
    data = BytesIO()
    Image.new('RGB', (24, 16), 'red').save(
        data,
        format=format,
        save_all=True,
        append_images=[Image.new('RGB', (24, 16), 'blue')],
        duration=100,
        loop=0,
    )
    response = await prepared['client'].post(
        f'{ME}/photos',
        headers={**prepared['owner'], 'Content-Type': f'image/{format.lower()}'},
        content=data.getvalue(),
    )
    assert response.status_code == 422
    assert not prepared['storage'].objects


@pytest.mark.parametrize('failure', ['upload', 'database'])
@pytest.mark.parametrize('cleanup_fails', [False, True])
async def test_upload_compensation(prepared, monkeypatch, caplog, failure, cleanup_fails):
    class FailingStorage(MemoryStorage):
        async def upload(self, *args):
            await super().upload(*args)
            if failure == 'upload':
                raise OSError('persisted then failed')

        async def delete(self, key):
            if cleanup_fails:
                raise OSError('cleanup unavailable')
            await super().delete(key)

    storage = FailingStorage()
    prepared['app'].state.object_storage = storage
    if failure == 'database':
        original_save = service.save

        async def fail_save(session):
            # Exercise a real DB constraint violation and the production rollback path.
            for item in session.new:
                if isinstance(item, CompanionPhoto):
                    item.width = 0
            await original_save(session)

        monkeypatch.setattr(service, 'save', fail_save)
    response = await upload(prepared)
    assert response.status_code == (503 if failure == 'upload' else 409)
    assert 'persisted then failed' not in response.text
    assert 'cleanup unavailable' not in response.text
    assert (await prepared['client'].get(f'{ME}/photos', headers=prepared['owner'])).json() == []
    assert bool(storage.objects) == cleanup_fails
    if cleanup_fails:
        records = [
            r
            for r in caplog.records
            if r.message.startswith('Companion upload compensation failed:')
        ]
        assert len(records) == 1
        assert records[0].storage_key in storage.objects


@pytest.mark.parametrize('boundary', ['0001-01-01T00:00:00+01:00', '9999-12-31T23:59:59-01:00'])
@pytest.mark.parametrize('field', ['starts_at', 'ends_at'])
async def test_utc_overflow_is_structured_422(prepared, boundary, field):
    payload = {
        'starts_at': '2027-01-01T10:00:00Z',
        'ends_at': '2027-01-01T11:00:00Z',
        'timezone': 'UTC',
    }
    payload[field] = boundary
    result = await prepared['client'].post(
        f'{ME}/availability', headers=prepared['owner'], json=payload
    )
    assert result.status_code == 422
    assert result.json()['code'] == 'validation_error'
    assert result.json()['request_id']


async def test_image_processing_does_not_block_endpoint(prepared, monkeypatch):
    started, release = threading.Event(), threading.Event()
    original = photos.process_image

    def slow_image(*args):
        started.set()
        assert release.wait(10)
        return original(*args)

    monkeypatch.setattr(photos, 'process_image', slow_image)
    task = asyncio.create_task(upload(prepared))
    try:
        for _ in range(200):
            if started.is_set():
                break
            await asyncio.sleep(0.01)
        assert started.is_set()
        result = await asyncio.wait_for(prepared['client'].get('/health'), 2)
        assert result.status_code == 200
    finally:
        release.set()
        result = await task
    assert result.status_code == 201


async def test_native_concurrent_decision_and_mutation(prepared):
    e, c = prepared, prepared['client']
    if e['app'].state.db_engine.dialect.name != 'postgresql':
        pytest.skip('Requires native PostgreSQL row locks')
    await c.post(f'{ME}/profile/submit', headers=e['owner'])
    revision = (await snapshot(e))['profile']['revision']
    decision, mutation = await asyncio.gather(
        decide(e, 'profiles', revision),
        c.put(f'{ME}/profile', headers=e['owner'], json={'display_name': 'Concurrent edit'}),
    )
    assert decision.status_code in {200, 409}
    assert mutation.status_code == 200
    current = await snapshot(e)
    assert current['profile']['content_status'] == 'draft'
    assert current['profile']['revision'] > revision
    assert not current['profile']['activation_requested']


async def test_native_concurrent_photo_uploads(prepared):
    e = prepared
    if e['app'].state.db_engine.dialect.name != 'postgresql':
        pytest.skip('Requires native PostgreSQL row locks')
    results = await asyncio.gather(upload(e), upload(e))
    assert [r.status_code for r in results] == [201, 201]
    assert sorted(r.json()['position'] for r in results) == [0, 1]
    assert len((await snapshot(e))['photos']) == 2


async def test_native_image_worker_concurrency_is_bounded(prepared, monkeypatch):
    e = prepared
    if e['app'].state.db_engine.dialect.name != 'postgresql':
        pytest.skip('Independent endpoint transactions require native PostgreSQL')
    third, _ = await login(e['client'], e['app'], '901000005')
    await create_profile(e, e['other'])
    await create_profile(e, third)
    lock, release = threading.Lock(), threading.Event()
    active = peak = entered = 0
    original = photos.process_image

    def slow_image(*args):
        nonlocal active, peak, entered
        with lock:
            active += 1
            entered += 1
            peak = max(peak, active)
        try:
            assert release.wait(10)
            return original(*args)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(photos, 'process_image', slow_image)
    tasks = [asyncio.create_task(upload(e, headers=h)) for h in [e['owner'], e['other'], third]]
    try:
        for _ in range(300):
            stats = e['app'].state.companion_image_limiter.statistics()
            if stats.tasks_waiting == 1:
                break
            await asyncio.sleep(0.01)
        assert stats.borrowed_tokens == 2 and stats.tasks_waiting == 1
        assert entered == 2
        assert (await e['client'].get('/health')).status_code == 200
    finally:
        release.set()
        results = await asyncio.gather(*tasks)
    assert all(r.status_code == 201 for r in results)
    assert peak == 2 and entered == 3


@pytest.mark.parametrize('limit', [1, 2])
async def test_deleted_photos_do_not_reset_retained_storage_limit(prepared, limit):
    e, c = prepared, prepared['client']
    e['app'].state.settings.companion_max_photos = limit
    for _ in range(limit):
        result = await upload(e)
        assert result.status_code == 201
        assert (
            await c.delete(f'{ME}/photos/{result.json()["id"]}', headers=e['owner'])
        ).status_code == 204
    assert (await c.get(f'{ME}/photos', headers=e['owner'])).json() == []
    for _ in range(4):
        result = await upload(e)
        assert result.status_code == 422
        assert result.json()['code'] == 'photo_limit'
    assert len(e['storage'].objects) == limit
    # One owner's retained objects must not consume another owner's quota.
    await create_profile(e, e['other'])
    assert (await upload(e, headers=e['other'])).status_code == 201


async def test_native_concurrent_uploads_respect_retained_limit(prepared):
    e = prepared
    if e['app'].state.db_engine.dialect.name != 'postgresql':
        pytest.skip('Requires native PostgreSQL row locks')
    e['app'].state.settings.companion_max_photos = 2
    first = await upload(e)
    assert first.status_code == 201
    assert (
        await e['client'].delete(f'{ME}/photos/{first.json()["id"]}', headers=e['owner'])
    ).status_code == 204
    results = await asyncio.gather(upload(e), upload(e))
    assert sorted(r.status_code for r in results) == [201, 422]
    assert len(e['storage'].objects) == 2
    assert len((await snapshot(e))['photos']) == 1


@pytest.mark.parametrize('zone', ['America', 'Etc'])
async def test_timezone_directory_names_are_structured_422(prepared, zone):
    response = await prepared['client'].post(
        f'{ME}/availability',
        headers=prepared['owner'],
        json={
            'starts_at': '2027-01-01T10:00:00Z',
            'ends_at': '2027-01-01T11:00:00Z',
            'timezone': zone,
        },
    )
    assert response.status_code == 422
    assert response.json()['code'] == 'validation_error'
    assert response.json()['request_id']


async def test_timezone_directory_oserror_is_structured_422(prepared, monkeypatch):
    from yondo_api.companions import schemas

    def directory_zone(value):
        # Unix zoneinfo directories raise this; Windows tzdata can raise KeyError.
        raise IsADirectoryError('private zoneinfo path')

    monkeypatch.setattr(schemas, 'ZoneInfo', directory_zone)
    response = await prepared['client'].post(
        f'{ME}/availability',
        headers=prepared['owner'],
        json={
            'starts_at': '2027-01-01T10:00:00Z',
            'ends_at': '2027-01-01T11:00:00Z',
            'timezone': 'America',
        },
    )
    assert response.status_code == 422
    assert response.json()['code'] == 'validation_error'
    assert 'private zoneinfo path' not in response.text
