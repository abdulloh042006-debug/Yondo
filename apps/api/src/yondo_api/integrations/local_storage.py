"""Filesystem storage for local development only; never enabled in staging/production."""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import AsyncIterator
from pathlib import Path

from anyio import Path as AsyncPath


class LocalObjectStorage:
    def __init__(self, root: str, secret: bytes, public_base_url: str) -> None:
        self.root = Path(root).resolve()
        self.secret = secret
        self.public_base_url = public_base_url.rstrip('/')

    def path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('Invalid storage key')
        return path

    def signature(self, key: str, expires: int) -> str:
        return hmac.new(self.secret, f'{key}:{expires}'.encode(), hashlib.sha256).hexdigest()

    def verify(self, key: str, expires: int, signature: str) -> bool:
        return expires >= int(time.time()) and hmac.compare_digest(
            self.signature(key, expires), signature
        )

    async def upload(self, key: str, content: AsyncIterator[bytes], content_type: str) -> None:
        path = AsyncPath(self.path_for(key))
        await path.parent.mkdir(parents=True, exist_ok=True)
        data = b''.join([chunk async for chunk in content])
        await path.write_bytes(data)

    async def create_download_url(self, key: str, expires_in_seconds: int = 300) -> str:
        expires = int(time.time()) + expires_in_seconds
        signature = self.signature(key, expires)
        return f'{self.public_base_url}/{key}?expires={expires}&signature={signature}'

    async def delete(self, key: str) -> None:
        path = AsyncPath(self.path_for(key))
        if await path.exists():
            await path.unlink()
