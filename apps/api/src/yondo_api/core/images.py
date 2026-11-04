"""Shared private-image upload: validation, metadata stripping and storage with cleanup."""

from __future__ import annotations

import asyncio

from anyio import to_thread
from fastapi import Request

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import object_storage
from yondo_api.companions.photos import IMAGE_TYPES, compensate_upload, process_image

IMAGE_REQUEST_BODY = {
    'requestBody': {
        'required': True,
        'content': {
            mime: {'schema': {'type': 'string', 'format': 'binary'}}
            for mime in IMAGE_TYPES.values()
        },
    }
}


async def read_image(request: Request) -> tuple[bytes, int, int]:
    """Read a raw JPEG/PNG/WebP body and return a clean re-encoded JPEG and its size."""
    settings = request.app.state.settings
    content_type = request.headers.get('content-type', '').split(';')[0].strip()
    if content_type not in IMAGE_TYPES.values():
        raise ApplicationError('invalid_photo_type', 'A JPEG, PNG or WebP image is required', 415)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > settings.companion_photo_max_bytes:
            raise ApplicationError('photo_too_large', 'Image exceeds the byte limit', 413)
        data.extend(chunk)
    return await to_thread.run_sync(
        process_image,
        data,
        content_type,
        settings,
        limiter=request.app.state.companion_image_limiter,
    )


async def store_image(request: Request, key: str, content: bytes) -> None:
    storage = object_storage(request)

    async def chunks():
        yield content

    try:
        await storage.upload(key, chunks(), 'image/jpeg')
    except asyncio.CancelledError:
        await compensate_upload(storage, key)
        raise
    except Exception as exc:
        await compensate_upload(storage, key)
        raise ApplicationError('storage_unavailable', 'Image upload failed', 503) from exc


async def discard_image(request: Request, key: str) -> None:
    storage = request.app.state.object_storage
    if storage is not None:
        await compensate_upload(storage, key)


async def signed_url(request: Request, key: str | None, seconds: int = 600) -> str | None:
    storage = request.app.state.object_storage
    if not key or storage is None:
        return None
    try:
        return await storage.create_download_url(key, seconds)
    except Exception:
        return None
