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
