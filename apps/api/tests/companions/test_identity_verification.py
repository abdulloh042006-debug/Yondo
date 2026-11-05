from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from yondo_api.account.deletion import erase_account
from yondo_api.admin.models import AdminAuditEvent
from yondo_api.models.user import User
from yondo_api.verification.models import IdentityVerification
from yondo_api.verification.service import DatabaseIdentityEligibility

from .conftest import approve, png

V = '/api/v1/verification/me'
ADMIN = '/api/v1/admin/verifications'


async def submit(client, headers):
    started = await client.post(V, headers=headers, json={'document_type': 'passport'})
    assert started.status_code == 201, started.text
    incomplete = await client.post(f'{V}/submit', headers=headers)
    assert incomplete.status_code == 422
    for part in ('document', 'selfie'):
        uploaded = await client.post(
            f'{V}/{part}', headers={**headers, 'Content-Type': 'image/png'}, content=png()
        )
        assert uploaded.status_code == 200, uploaded.text
    submitted = await client.post(f'{V}/submit', headers=headers)
    assert submitted.json()['status'] == 'pending'
    return submitted.json()


async def test_verification_feeds_the_companion_activation_gate(prepared):
    env = prepared
    client, app = env['client'], env['app']
    app.state.identity_eligibility = DatabaseIdentityEligibility()
    await approve(env)
    blocked = await client.post('/api/v1/companions/me/activate', headers=env['owner'])
    assert blocked.status_code == 409
    item = await submit(client, env['owner'])
    assert {key.split('/')[0] for key in env['storage'].objects} >= {'verifications'}
    assert (
        await client.post(V, headers=env['owner'], json={'document_type': 'id_card'})
    ).status_code == 409
    assert (await client.get(ADMIN, headers=env['customer'])).status_code == 403
    queue = await client.get(ADMIN, headers=env['admin'])
    assert queue.json()[0]['document_url'].startswith('https://storage.test/private/')
    decided = await client.post(
        f'{ADMIN}/{item["id"]}/decision',
        headers=env['admin'],
        json={'decision': 'approve', 'note': 'Document and selfie match'},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()['status'] == 'verified'
    status = await client.get('/api/v1/companions/me/status', headers=env['owner'])
    assert status.json()['identity_status'] == 'verified'
    activated = await client.post('/api/v1/companions/me/activate', headers=env['owner'])
    assert activated.status_code == 200, activated.text
    async with app.state.db_session_factory() as session:
        audit = (
            await session.scalars(
                select(AdminAuditEvent).where(AdminAuditEvent.action.like('identity_%'))
            )
        ).one()
    assert audit.action == 'identity_verified' and str(audit.target_id) == env['owner_id']


async def test_rejection_allows_a_new_attempt_and_self_review_is_refused(env):
    client = env['client']
    item = await submit(client, env['other'])
    rejected = await client.post(
        f'{ADMIN}/{item["id"]}/decision',
        headers=env['admin'],
        json={'decision': 'reject', 'note': 'Blurry photo'},
    )
    assert rejected.json()['status'] == 'rejected'
    again = await client.post(
        f'{ADMIN}/{item["id"]}/decision',
        headers=env['admin'],
        json={'decision': 'approve', 'note': 'x'},
    )
    assert again.status_code == 409
    mine = await client.get(V, headers=env['other'])
    assert mine.json()['status'] == 'rejected' and mine.json()['review_note'] == 'Blurry photo'
    restart = await client.post(V, headers=env['other'], json={'document_type': 'id_card'})
    assert restart.status_code == 201 and restart.json()['status'] == 'draft'
    # A draft never counts: identity stays "rejected" until the new attempt is submitted.
    async with env['app'].state.db_session_factory() as session:
        status = await DatabaseIdentityEligibility().get_status(session, UUID(env['other_id']))
    assert status == 'rejected'
    admin_item = await submit(client, env['admin'])
    self_review = await client.post(
        f'{ADMIN}/{admin_item["id"]}/decision',
        headers=env['admin'],
        json={'decision': 'approve', 'note': 'me'},
    )
    assert self_review.status_code == 403


async def test_uploads_need_storage_and_a_draft(env):
    client = env['client']
    no_draft = await client.post(
        f'{V}/document', headers={**env['owner'], 'Content-Type': 'image/png'}, content=png()
    )
    assert no_draft.status_code == 409
    await client.post(V, headers=env['owner'], json={'document_type': 'passport'})
    wrong_type = await client.post(
        f'{V}/document', headers={**env['owner'], 'Content-Type': 'text/plain'}, content=b'x'
    )
    assert wrong_type.status_code == 415
    env['app'].state.object_storage = None
    unavailable = await client.post(
        f'{V}/document', headers={**env['owner'], 'Content-Type': 'image/png'}, content=png()
    )
    assert unavailable.status_code == 503
    assert (await client.get(V)).status_code == 401


async def test_account_erasure_deletes_verification_images(env):
    client, storage = env['client'], env['storage']
    item = await submit(client, env['owner'])
    assert any(key.startswith('verifications/') for key in storage.objects)
    async with env['app'].state.db_session_factory() as session:
        user = await session.get(User, UUID(env['owner_id']))
        await erase_account(session, user, storage, datetime.now(UTC))
        await session.commit()
        kept = await session.get(IdentityVerification, UUID(item['id']))
        assert kept.document_key is None and kept.selfie_key is None
    assert not any(key.startswith('verifications/') for key in storage.objects)
