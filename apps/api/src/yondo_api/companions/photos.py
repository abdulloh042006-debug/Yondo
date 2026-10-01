import logging
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID, uuid4

from anyio import to_thread
from fastapi import APIRouter, Request, Response
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select

from yondo_api.api.errors import ApplicationError
from yondo_api.companions import service
from yondo_api.companions.dependencies import Owner, Session, object_storage
from yondo_api.companions.models import CompanionPhoto
from yondo_api.companions.schemas import PhotoCaption, PhotoDownload, PhotoOrder, PhotoResponse

router = APIRouter(prefix='/companions/me/photos', tags=['companion photos'])
IMAGE_TYPES = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'WEBP': 'image/webp'}


def process_image(data, content_type, settings):
    try:
        with Image.open(BytesIO(data)) as picture:
            if IMAGE_TYPES.get(picture.format) != content_type:
                raise ValueError('Content type does not match image')
            width, height = picture.size
            if width * height > settings.companion_photo_max_pixels:
                raise ValueError('Image exceeds the configured pixel limit')
            if getattr(picture, 'n_frames', 1) != 1:
                raise ValueError('Only still images are supported')
            picture.verify()
        # Decode and re-encode to remove EXIF/location metadata and trailing payloads.
        with Image.open(BytesIO(data)) as picture:
            clean = ImageOps.exif_transpose(picture).convert('RGB')
            width, height = clean.size
            output = BytesIO()
            clean.save(output, format='JPEG', quality=90)
            content = output.getvalue()
        if len(content) > settings.companion_photo_max_bytes:
            raise ValueError('Processed image exceeds the configured byte limit')
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ApplicationError(
            'invalid_photo', 'Image is invalid or exceeds configured limits', 422
        ) from exc
    return content, width, height


async def visible_photos(session: Session, profile_id: UUID) -> list[CompanionPhoto]:
    return list(
        await session.scalars(
            select(CompanionPhoto)
            .where(
                CompanionPhoto.profile_id == profile_id,
                CompanionPhoto.deleted_at.is_(None),
            )
            .order_by(CompanionPhoto.position)
        )
    )


@router.get('', response_model=list[PhotoResponse])
async def list_photos(owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    return await visible_photos(session, profile.id)


@router.post(
    '',
    response_model=PhotoResponse,
    status_code=201,
    openapi_extra={
        'requestBody': {
            'required': True,
            'content': {
                mime: {'schema': {'type': 'string', 'format': 'binary'}}
                for mime in IMAGE_TYPES.values()
            },
        }
    },
)
async def upload_photo(request: Request, owner: Owner, session: Session):
    """Upload raw JPEG/PNG/WebP bytes. Keys and metadata are always server-generated."""
    profile = await service.profile_for(session, owner.id)
    storage = object_storage(request)
    settings = request.app.state.settings
    photos = await visible_photos(session, profile.id)
    # Deleted objects remain retained until a retention/GC policy exists. Count
    # their tombstones too, under the owner lock, so delete cannot reset quota.
    retained_count = await session.scalar(
        select(func.count())
        .select_from(CompanionPhoto)
        .where(CompanionPhoto.profile_id == profile.id)
    )
    if retained_count >= settings.companion_max_photos:
        raise ApplicationError('photo_limit', 'Configured photo limit reached', 422)
    content_type = request.headers.get('content-type', '').split(';')[0].strip()
    if content_type not in IMAGE_TYPES.values():
        raise ApplicationError('invalid_photo_type', 'A JPEG, PNG or WebP image is required', 415)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > settings.companion_photo_max_bytes:
            raise ApplicationError(
                'photo_too_large', 'Photo exceeds the configured byte limit', 413
            )
        data.extend(chunk)
    content, width, height = await to_thread.run_sync(
        process_image,
        data,
        content_type,
        settings,
        limiter=request.app.state.companion_image_limiter,
    )
    photo_id = uuid4()
    key = f'companions/{profile.id}/{photo_id}.jpg'

    async def chunks():
        yield content

    try:
        await storage.upload(key, chunks(), 'image/jpeg')
    except Exception as exc:
        await compensate_upload(storage, key)
        raise ApplicationError('storage_unavailable', 'Photo upload failed', 503) from exc
    item = CompanionPhoto(
        id=photo_id,
        profile_id=profile.id,
        storage_key=key,
        content_type='image/jpeg',
        size_bytes=len(content),
        width=width,
        height=height,
        position=max((photo.position for photo in photos), default=-1) + 1,
    )
    session.add(item)
    service.invalidate_content(profile)
    try:
        await service.save(session)
    except Exception:
        # Best-effort compensation. The key is never exposed by this API.
        await compensate_upload(storage, key)
        raise
    return item


@router.put('/order', response_model=list[PhotoResponse])
async def reorder_photos(payload: PhotoOrder, owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    photos = await visible_photos(session, profile.id)
    by_id = {photo.id: photo for photo in photos}
    if set(payload.photo_ids) != set(by_id):
        raise ApplicationError(
            'invalid_photo_order', 'Supply every current photo exactly once', 422
        )
    # A temporary disjoint positive range preserves the unique constraint while swapping.
    offset = max((photo.position for photo in photos), default=-1) + 1
    for index, photo in enumerate(photos):
        photo.position = offset + index
    await session.flush()
    for index, photo_id in enumerate(payload.photo_ids):
        by_id[photo_id].position = index
    service.invalidate_content(profile)
    await service.save(session)
    return [by_id[photo_id] for photo_id in payload.photo_ids]


@router.patch('/{photo_id}', response_model=PhotoResponse)
async def edit_caption(photo_id: UUID, payload: PhotoCaption, owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    item = await service.owned_resource(session, CompanionPhoto, photo_id, profile.id)
    item.caption = payload.caption
    service.invalidate_content(profile)
    await service.save(session)
    return item


@router.get('/{photo_id}/download', response_model=PhotoDownload)
async def download_photo(photo_id: UUID, request: Request, owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    item = await service.owned_resource(session, CompanionPhoto, photo_id, profile.id)
    return await download_url(request, item)


async def download_url(request: Request, photo: CompanionPhoto) -> PhotoDownload:
    storage = object_storage(request)
    try:
        return PhotoDownload(url=await storage.create_download_url(photo.storage_key))
    except Exception as exc:
        raise ApplicationError('storage_unavailable', 'Photo download is unavailable', 503) from exc


@router.delete('/{photo_id}', status_code=204)
async def delete_photo(photo_id: UUID, owner: Owner, session: Session):
    profile = await service.profile_for(session, owner.id)
    item = await service.owned_resource(session, CompanionPhoto, photo_id, profile.id)
    # Retain a private tombstone so eventual retention/GC can safely reconcile the object.
    item.deleted_at = datetime.now(UTC)
    item.position = None
    service.invalidate_content(profile)
    await service.save(session)
    return Response(status_code=204)


async def compensate_upload(storage, key):
    try:
        await storage.delete(key)
    except Exception:
        # Private structured key lets operators reconcile without exposing it to clients.
        logging.getLogger(__name__).exception(
            'Companion upload compensation failed: storage_key=%s',
            key,
            extra={'storage_key': key},
        )
