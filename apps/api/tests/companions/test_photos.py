from io import BytesIO
from uuid import uuid4

from PIL import Image

from .conftest import approve, create_profile, png

ME = '/api/v1/companions/me'


async def upload(e, content=None, headers=None):
    return await e['client'].post(
        f'{ME}/photos',
        headers={**(headers or e['owner']), 'Content-Type': 'image/png'},
        content=content if content is not None else png(),
    )


async def test_photo_metadata_order_caption_delete_and_download(prepared):
    e, c = prepared, prepared['client']
    first, second = await upload(e), await upload(e)
    assert first.status_code == second.status_code == 201
    a, b = first.json(), second.json()
    assert (a['position'], b['position']) == (0, 1)
    assert (a['width'], a['height']) == (24, 16)
    assert a['content_type'] == 'image/jpeg'
    assert 'storage_key' not in a
    stored, mime = next(iter(e['storage'].objects.values()))
    assert a['size_bytes'] == len(stored)
    with Image.open(BytesIO(stored)) as image:
        assert image.format == 'JPEG'
        assert len(image.getexif()) == 0
    response = await c.put(
        f'{ME}/photos/order', headers=e['owner'], json={'photo_ids': [b['id'], a['id']]}
    )
    assert response.status_code == 200
    assert [p['id'] for p in response.json()] == [b['id'], a['id']]
    assert [p['position'] for p in response.json()] == [0, 1]
    caption = await c.patch(
        f'{ME}/photos/{a["id"]}', headers=e['owner'], json={'caption': 'Portrait'}
    )
    assert caption.json()['caption'] == 'Portrait'
    assert (await c.get(f'{ME}/photos/{a["id"]}/download', headers=e['owner'])).status_code == 200
    assert (await c.delete(f'{ME}/photos/{a["id"]}', headers=e['owner'])).status_code == 204
    assert (await c.get(f'{ME}/photos/{a["id"]}/download', headers=e['owner'])).status_code == 404
    assert (await c.delete(f'{ME}/photos/{a["id"]}', headers=e['owner'])).status_code == 404
    assert len((await c.get(f'{ME}/photos', headers=e['owner'])).json()) == 1
    assert len(e['storage'].objects) == 2


async def test_photo_ownership_and_invalid_order(prepared):
    e, c = prepared, prepared['client']
    await create_profile(e, e['other'])
    a = (await upload(e)).json()
    b = (await upload(e, headers=e['other'])).json()
    assert (await c.get(f'{ME}/photos/{a["id"]}/download', headers=e['other'])).status_code == 404
    assert (
        await c.patch(f'{ME}/photos/{a["id"]}', headers=e['other'], json={'caption': 'x'})
    ).status_code == 404
    assert (await c.delete(f'{ME}/photos/{a["id"]}', headers=e['other'])).status_code == 404
    for ids in [[], [a['id'], a['id']], [b['id']], [str(uuid4())]]:
        result = await c.put(f'{ME}/photos/order', headers=e['owner'], json={'photo_ids': ids})
        assert result.status_code == 422
    assert (await upload(e, headers=e['customer'])).status_code == 403


async def test_photo_content_validation_and_limits(prepared):
    e, c, settings = prepared, prepared['client'], prepared['app'].state.settings
    assert (await upload(e, b'not an image')).status_code == 422
    assert (await upload(e, b'')).status_code == 422
    for mime, body, status in [('image/jpeg', png(), 422), ('image/svg+xml', b'<svg/>', 415)]:
        result = await c.post(
            f'{ME}/photos', headers={**e['owner'], 'Content-Type': mime}, content=body
        )
        assert result.status_code == status
    settings.companion_photo_max_bytes = 10
    assert (await upload(e)).status_code == 413
    settings.companion_photo_max_bytes = 1048576
    settings.companion_photo_max_pixels = 10
    assert (await upload(e)).status_code == 422
    settings.companion_photo_max_pixels = 10000
    settings.companion_max_photos = 1
    assert (await upload(e)).status_code == 201
    assert (await upload(e)).status_code == 422


async def test_storage_missing_and_failure_are_structured(prepared):
    e = prepared
    e['app'].state.object_storage = None
    result = await upload(e)
    assert result.status_code == 503
    assert result.json()['code'] == 'storage_unavailable'

    class BrokenStorage:
        async def upload(self, *args):
            raise OSError('private storage details')

    e['app'].state.object_storage = BrokenStorage()
    result = await upload(e)
    assert result.status_code == 503
    assert 'private storage details' not in result.text
    assert (await e['client'].get(f'{ME}/photos', headers=e['owner'])).json() == []


async def test_photo_edits_revoke_pending_review(prepared):
    e = prepared
    a = (await upload(e)).json()
    await e['client'].post(f'{ME}/profile/submit', headers=e['owner'])
    await e['client'].patch(
        f'{ME}/photos/{a["id"]}', headers=e['owner'], json={'caption': 'Changed'}
    )
    result = await e['client'].post(
        f'/api/v1/companions/admin/profiles/{e["profile"]["id"]}/decision',
        headers=e['admin'],
        json={'expected_revision': 2, 'decision': 'approve', 'note': 'Checked old content'},
    )
    assert result.status_code == 409


async def test_admin_can_inspect_content_and_owner_cannot_moderate(prepared):
    e, c = prepared, prepared['client']
    a = (await upload(e)).json()
    root = f'/api/v1/companions/admin/users/{e["owner_id"]}'
    for path in ['/profile', '/services', '/photos', f'/photos/{a["id"]}/download']:
        assert (await c.get(root + path, headers=e['admin'])).status_code == 200
        assert (await c.get(root + path, headers=e['customer'])).status_code == 403
    await approve(e)
    await upload(e)
    assert (await c.get(f'{ME}/profile', headers=e['owner'])).json()['content_status'] == 'draft'
