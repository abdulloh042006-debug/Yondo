from datetime import UTC, datetime

import httpx
import pytest

from yondo_api.config import Settings
from yondo_api.integrations.s3 import S3ObjectStorage
from yondo_api.main import create_application


def test_presigned_url_matches_aws_reference_vector():
    # AWS documentation example: presigned GET, virtual-hosted style, 2013-05-24, 86400 s.
    storage = S3ObjectStorage(
        endpoint='https://s3.amazonaws.com',
        bucket='examplebucket',
        access_key='AKIAIOSFODNN7EXAMPLE',
        secret_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
        region='us-east-1',
        path_style=False,
    )
    url = storage.presign('GET', 'test.txt', 86400, now=datetime(2013, 5, 24, tzinfo=UTC))
    assert url.startswith('https://examplebucket.s3.amazonaws.com/test.txt?')
    assert url.endswith(
        'X-Amz-Signature=aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404'
    )


def test_credentials_are_required():
    with pytest.raises(ValueError):
        S3ObjectStorage(
            endpoint='http://minio:9000',
            bucket='b',
            access_key='',
            secret_key='',
            region='us-east-1',
        )


async def test_upload_and_delete_are_signed_path_style_requests():
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(404 if request.method == 'DELETE' else 200)

    storage = S3ObjectStorage(
        endpoint='http://minio:9000',
        bucket='yondo',
        access_key='key',
        secret_key='secret',
        region='us-east-1',
        public_endpoint='https://files.example.test',
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    async def chunks():
        yield b'jpeg-bytes'

    await storage.upload('companions/p/photo 1.jpg', chunks(), 'image/jpeg')
    await storage.delete('companions/p/photo 1.jpg')  # 404 on delete is not an error
    put, delete = calls
    assert (
        put.method == 'PUT' and str(put.url) == 'http://minio:9000/yondo/companions/p/photo%201.jpg'
    )
    assert put.content == b'jpeg-bytes'
    assert put.headers['content-type'] == 'image/jpeg'
    assert put.headers['authorization'].startswith('AWS4-HMAC-SHA256 Credential=key/')
    assert (
        'SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date'
        in put.headers['authorization']
    )
    assert delete.method == 'DELETE'
    url = await storage.create_download_url('companions/p/photo 1.jpg')
    # Presigned for the public origin clients use, private object, short lifetime.
    assert url.startswith('https://files.example.test/yondo/companions/p/photo%201.jpg?')
    assert 'X-Amz-Expires=300' in url


def test_storage_backend_setting_selects_the_adapter():
    disabled = create_application(Settings(environment='test'))
    assert disabled.state.object_storage is None
    configured = create_application(
        Settings(
            environment='test',
            storage_backend='s3',
            storage_access_key='key',
            storage_secret_key='secret',
        )
    )
    assert isinstance(configured.state.object_storage, S3ObjectStorage)


@pytest.mark.parametrize(
    ('endpoint', 'expected_host'),
    [
        ('https://user:pw@Spaces.Example:443', 'spaces.example'),
        ('http://minio:80', 'minio'),
        ('http://minio:9000', 'minio:9000'),
        ('https://[::1]:9443', '[::1]:9443'),
    ],
)
async def test_signed_host_is_the_host_httpx_sends(endpoint, expected_host):
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200)

    storage = S3ObjectStorage(
        endpoint=endpoint,
        bucket='b',
        access_key='key',
        secret_key='secret',
        region='us-east-1',
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    url, host = storage._location(endpoint, 'k')
    assert host == expected_host
    assert '@' not in url
    await storage.delete('k')
    assert sent[0].headers['host'] == expected_host


def test_scheduled_job_erases_with_the_configured_storage(monkeypatch):
    from yondo_api import jobs

    seen = []

    async def fake_main(storage=None):
        seen.append(storage)
        return 0

    monkeypatch.setattr(jobs, 'main', fake_main)
    monkeypatch.setattr(
        jobs,
        'get_settings',
        lambda: Settings(
            environment='test',
            storage_backend='s3',
            storage_access_key='key',
            storage_secret_key='secret',
        ),
    )
    assert jobs.run() == 0
    monkeypatch.setattr(jobs, 'get_settings', lambda: Settings(environment='test'))
    assert jobs.run() == 0
    assert isinstance(seen[0], S3ObjectStorage)
    assert seen[1] is None


def test_production_storage_hands_out_https_urls_only():
    base = {
        'environment': 'production',
        'auth_otp_pepper': 'p' * 40,
        'storage_backend': 's3',
        'storage_access_key': 'key',
        'storage_secret_key': 'secret',
    }
    with pytest.raises(ValueError, match='https'):
        Settings(**base, storage_endpoint='http://minio:9000')
    # A private-network endpoint is fine when clients get an https public origin.
    ok = Settings(
        **base,
        storage_endpoint='http://minio:9000',
        storage_public_endpoint='https://files.example.test',
    )
    assert ok.storage_public_endpoint == 'https://files.example.test'
    assert Settings(environment='test', storage_backend='s3').storage_backend == 's3'


def test_old_job_alias_uses_the_same_storage_wiring(monkeypatch):
    import runpy

    from yondo_api import jobs

    called = []
    monkeypatch.setattr(jobs, 'run', lambda: called.append(True) or 0)
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module('yondo_api.account.jobs', run_name='__main__')
    assert exit_info.value.code == 0 and called == [True]
