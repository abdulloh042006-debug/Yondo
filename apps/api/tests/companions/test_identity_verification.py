import asyncio
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
                select(AdminAuditEvent).where(
                    AdminAuditEvent.action.in_(['identity_verified', 'identity_rejected'])
                )
            )
        ).one()
    assert audit.action == 'identity_verified' and str(audit.target_id) == env['owner_id']
    # The free-text note is user-visible and erasable; the durable audit row keeps only the id.
    assert audit.reason == f'identity_verification:{decided.json()["id"]}'


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


async def test_erasure_without_storage_or_with_a_failing_delete_keeps_the_keys(env):
    client, storage = env['client'], env['storage']
    item = await submit(client, env['owner'])
    stored = {key for key in storage.objects if key.startswith('verifications/')}
    assert len(stored) == 2

    class FailingStorage:
        async def delete(self, key):
            raise OSError('bucket unreachable')

    for broken in (None, FailingStorage()):
        async with env['app'].state.db_session_factory() as session:
            user = await session.get(User, UUID(env['owner_id']))
            await erase_account(session, user, broken, datetime.now(UTC))
            await session.commit()
            kept = await session.get(IdentityVerification, UUID(item['id']))
            # The keys still point at the objects, so a run with storage can remove them.
            assert {kept.document_key, kept.selfie_key} == stored
            assert kept.review_note is None
    assert stored <= set(storage.objects)
    async with env['app'].state.db_session_factory() as session:
        user = await session.get(User, UUID(env['owner_id']))
        await erase_account(session, user, storage, datetime.now(UTC))
        await session.commit()
        cleared = await session.get(IdentityVerification, UUID(item['id']))
        assert cleared.document_key is None and cleared.selfie_key is None
    assert not stored & set(storage.objects)


async def test_failed_save_deletes_the_new_upload_but_keeps_a_committed_one(env, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    from yondo_api.verification import router as verification_router

    client, storage = env['client'], env['storage']
    started = await client.post(V, headers=env['owner'], json={'document_type': 'passport'})
    assert started.status_code == 201, started.text
    headers = {**env['owner'], 'Content-Type': 'image/png'}
    images = lambda: {key for key in storage.objects if key.startswith('verifications/')}  # noqa: E731

    # 1) The save fails before commit: the new object is removed again.
    real_draft_for = verification_router.draft_for
    lookups = []

    async def second_lookup_fails(session, user_id):
        lookups.append(user_id)
        if len(lookups) == 2:  # the lookup after the upload, inside the save
            raise RuntimeError('database went away before commit')
        return await real_draft_for(session, user_id)

    monkeypatch.setattr(verification_router, 'draft_for', second_lookup_fails)
    try:
        await client.post(f'{V}/document', headers=headers, content=png())
    except RuntimeError:
        pass
    assert images() == set()
    monkeypatch.setattr(verification_router, 'draft_for', real_draft_for)

    # 2) The commit succeeds but its outcome is lost: the row uses the object, so it stays.
    real_commit = AsyncSession.commit

    async def commit_then_fail(self):
        saving = any(
            isinstance(row, IdentityVerification) and row.document_key
            for row in self.sync_session.dirty
        )
        await real_commit(self)
        if saving:
            raise ConnectionError('connection lost after COMMIT')

    monkeypatch.setattr(AsyncSession, 'commit', commit_then_fail)
    try:
        await client.post(f'{V}/document', headers=headers, content=png())
    except ConnectionError:
        pass
    monkeypatch.setattr(AsyncSession, 'commit', real_commit)
    async with env['app'].state.db_session_factory() as session:
        row = await session.get(IdentityVerification, UUID(started.json()['id']))
        assert row.document_key is not None
    assert images() == {row.document_key}


def verification_images(storage):
    return {key for key in storage.objects if key.startswith('verifications/')}


async def decide(client, env, item, decision='approve'):
    return await client.post(
        f'{ADMIN}/{item["id"]}/decision',
        headers=env['admin'],
        json={'decision': decision, 'note': 'checked'},
    )


async def test_decision_deletes_images_and_clears_keys(env):
    client, storage = env['client'], env['storage']
    item = await submit(client, env['other'])
    assert len(verification_images(storage)) == 2
    decided = await decide(client, env, item, 'reject')
    assert decided.status_code == 200
    body = decided.json()
    assert body['has_document'] is False and body['has_selfie'] is False
    assert body['document_url'] is None
    assert verification_images(storage) == set()
    async with env['app'].state.db_session_factory() as session:
        row = await session.get(IdentityVerification, UUID(item['id']))
        assert row.document_key is None and row.selfie_key is None


async def test_failed_delete_at_decision_keeps_keys_and_job_retries(env):
    from yondo_api.verification.service import purge_decided_images

    client, storage = env['client'], env['storage']
    item = await submit(client, env['other'])
    real_delete = storage.delete

    async def broken(key):
        raise OSError('down')

    storage.delete = broken
    assert (await decide(client, env, item)).status_code == 200
    assert len(verification_images(storage)) == 2
    storage.delete = real_delete
    async with env['app'].state.db_session_factory() as session:
        assert await purge_decided_images(session, storage, 0) == 1
    assert verification_images(storage) == set()


async def test_retention_keeps_images_until_the_job_runs(env):
    from datetime import timedelta

    from yondo_api.verification.service import purge_decided_images

    client, storage = env['client'], env['storage']
    env['app'].state.settings.identity_image_retention_days = 7
    item = await submit(client, env['other'])
    decided = await decide(client, env, item)
    assert decided.json()['document_url'] is not None
    assert len(verification_images(storage)) == 2
    async with env['app'].state.db_session_factory() as session:
        assert await purge_decided_images(session, storage, 7) == 0
        later = datetime.now(UTC) + timedelta(days=8)
        assert await purge_decided_images(session, storage, 7, later) == 1
    assert verification_images(storage) == set()


async def test_admin_image_access_is_audited_without_url_or_key(env):
    client = env['client']
    env['app'].state.settings.identity_image_retention_days = 7
    item = await submit(client, env['other'])
    assert (await client.get(ADMIN, headers=env['admin'])).status_code == 200
    async with env['app'].state.db_session_factory() as session:
        events = list(
            await session.scalars(
                select(AdminAuditEvent).where(AdminAuditEvent.action == 'identity_image_viewed')
            )
        )
    assert {e.reason for e in events} == {
        f'identity_verification:{item["id"]}:document',
        f'identity_verification:{item["id"]}:selfie',
    }
    admin_id = (await client.get('/api/v1/auth/me', headers=env['admin'])).json()['id']
    assert all(str(e.admin_id) == admin_id and 'storage.test' not in e.reason for e in events)


async def test_url_failure_is_logged_not_swallowed(env, caplog):
    client, storage = env['client'], env['storage']
    await submit(client, env['other'])

    async def broken(key, expires_in_seconds=300):
        raise OSError('presign failed')

    storage.create_download_url = broken
    with caplog.at_level('WARNING'):
        queue = await client.get(ADMIN, headers=env['admin'])
    assert queue.json()[0]['document_url'] is None
    assert 'Verification image URL unavailable' in caplog.text
    assert 'verifications/' not in caplog.text


async def test_submissions_are_capped_per_user(env):
    client = env['client']
    env['app'].state.settings.identity_max_submissions_per_user = 2
    for _ in range(2):
        await asyncio.sleep(1.1)  # SQLite timestamps are per second: keep `latest` unambiguous
        item = await submit(client, env['other'])
        assert (await decide(client, env, item, 'reject')).status_code == 200
    blocked = await client.post(V, headers=env['other'], json={'document_type': 'passport'})
    assert blocked.status_code == 429
    assert 'verification_attempts_exceeded' in blocked.text


async def test_job_removes_abandoned_drafts_with_their_objects(env):
    from datetime import timedelta

    from yondo_api.verification.service import purge_abandoned_drafts

    client, storage = env['client'], env['storage']
    await client.post(V, headers=env['owner'], json={'document_type': 'passport'})
    await client.post(
        f'{V}/document', headers={**env['owner'], 'Content-Type': 'image/png'}, content=png()
    )
    assert len(verification_images(storage)) == 1
    async with env['app'].state.db_session_factory() as session:
        assert await purge_abandoned_drafts(session, storage) == 0  # fresh draft stays
        later = datetime.now(UTC) + timedelta(hours=25)
        assert await purge_abandoned_drafts(session, storage, later) == 1
        rows = (await session.scalars(select(IdentityVerification))).all()
    assert rows == [] and verification_images(storage) == set()


def test_alembic_has_a_single_head():
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'migrations'))
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1
