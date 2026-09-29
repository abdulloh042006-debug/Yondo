from collections.abc import AsyncIterator
from typing import Protocol


class ObjectStorage(Protocol):
    async def upload(self, key: str, content: AsyncIterator[bytes], content_type: str) -> None: ...

    async def create_download_url(self, key: str, expires_in_seconds: int = 300) -> str: ...

    async def delete(self, key: str) -> None: ...

