"""Dependency-free S3-compatible object storage adapter (AWS Signature Version 4).

Works with AWS S3, MinIO and other S3-compatible providers. Objects are private;
reads use short-lived presigned URLs.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from urllib.parse import quote, urlsplit

import httpx

_EMPTY_SHA256 = hashlib.sha256(b'').hexdigest()


def _sign(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


def _signing_key(secret_key: str, date: str, region: str) -> bytes:
    key = _sign(f'AWS4{secret_key}'.encode(), date)
    key = _sign(key, region)
    key = _sign(key, 's3')
    return _sign(key, 'aws4_request')


def _uri_encode(value: str, *, keep_slash: bool) -> str:
    return quote(value, safe='/~' if keep_slash else '~')


class S3ObjectStorage:
    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str,
        path_style: bool = True,
        public_endpoint: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not access_key or not secret_key or not bucket:
            raise ValueError('S3 storage requires bucket, access key and secret key')
        self.endpoint = endpoint.rstrip('/')
        self.public_endpoint = (public_endpoint or endpoint).rstrip('/')
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.path_style = path_style
        self._client = client

    def _location(self, base: str, key: str) -> tuple[str, str]:
        parts = urlsplit(base)
        encoded_key = _uri_encode(key, keep_slash=True)
        if self.path_style:
            host = parts.netloc
            path = f'{parts.path}/{self.bucket}/{encoded_key}'
        else:
            host = f'{self.bucket}.{parts.netloc}'
            path = f'{parts.path}/{encoded_key}'
        return f'{parts.scheme}://{host}{path}', host

    def _canonical_path(self, url: str) -> str:
        return urlsplit(url).path or '/'

    def presign(
        self,
        method: str,
        key: str,
        expires_in_seconds: int,
        *,
        now: datetime | None = None,
        base: str | None = None,
    ) -> str:
        moment = (now or datetime.now(UTC)).astimezone(UTC)
        amz_date = moment.strftime('%Y%m%dT%H%M%SZ')
        date = moment.strftime('%Y%m%d')
        url, host = self._location(base or self.public_endpoint, key)
        scope = f'{date}/{self.region}/s3/aws4_request'
        query = {
            'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
            'X-Amz-Credential': f'{self.access_key}/{scope}',
            'X-Amz-Date': amz_date,
            'X-Amz-Expires': str(expires_in_seconds),
            'X-Amz-SignedHeaders': 'host',
        }
        canonical_query = '&'.join(
            f'{_uri_encode(name, keep_slash=False)}={_uri_encode(value, keep_slash=False)}'
            for name, value in sorted(query.items())
        )
        canonical_request = '\n'.join(
            [
                method,
                self._canonical_path(url),
                canonical_query,
                f'host:{host}\n',
                'host',
                'UNSIGNED-PAYLOAD',
            ]
        )
        string_to_sign = '\n'.join(
            [
                'AWS4-HMAC-SHA256',
                amz_date,
                scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            ]
        )
        signature = hmac.new(
            _signing_key(self.secret_key, date, self.region),
            string_to_sign.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f'{url}?{canonical_query}&X-Amz-Signature={signature}'

    def _signed_headers(
        self, method: str, url: str, host: str, payload_hash: str, extra: dict[str, str]
    ) -> dict[str, str]:
        moment = datetime.now(UTC)
        amz_date = moment.strftime('%Y%m%dT%H%M%SZ')
        date = moment.strftime('%Y%m%d')
        headers = {
            'host': host,
            'x-amz-content-sha256': payload_hash,
            'x-amz-date': amz_date,
            **{name.lower(): value for name, value in extra.items()},
        }
        signed = ';'.join(sorted(headers))
        canonical_headers = ''.join(f'{name}:{headers[name].strip()}\n' for name in sorted(headers))
        canonical_request = '\n'.join(
            [method, self._canonical_path(url), '', canonical_headers, signed, payload_hash]
        )
        scope = f'{date}/{self.region}/s3/aws4_request'
        string_to_sign = '\n'.join(
            [
                'AWS4-HMAC-SHA256',
                amz_date,
                scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            ]
        )
        signature = hmac.new(
            _signing_key(self.secret_key, date, self.region),
            string_to_sign.encode(),
            hashlib.sha256,
        ).hexdigest()
        headers['authorization'] = (
            f'AWS4-HMAC-SHA256 Credential={self.access_key}/{scope}, '
            f'SignedHeaders={signed}, Signature={signature}'
        )
        headers.pop('host')
        return headers

    async def _request(self, method: str, key: str, body: bytes = b'', **extra: str) -> None:
        url, host = self._location(self.endpoint, key)
        payload_hash = hashlib.sha256(body).hexdigest() if body else _EMPTY_SHA256
        headers = self._signed_headers(method, url, host, payload_hash, extra)
        if self._client is not None:
            response = await self._client.request(method, url, content=body, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(method, url, content=body, headers=headers)
        if method == 'DELETE' and response.status_code == 404:
            return
        response.raise_for_status()

    async def upload(self, key: str, content: AsyncIterator[bytes], content_type: str) -> None:
        body = b''.join([chunk async for chunk in content])
        await self._request('PUT', key, body, **{'content-type': content_type})

    async def create_download_url(self, key: str, expires_in_seconds: int = 300) -> str:
        return self.presign('GET', key, expires_in_seconds)

    async def delete(self, key: str) -> None:
        await self._request('DELETE', key)
