"""Account profile photos for every user (owner decision 2026-11-14).

Visibility: the owner of the photos, admins, and the companion side of a booking that the
customer created (any status). Never in discovery, never to other customers or companions.
Clients reach a customer's photos only through ``booking_id``: no customer user id is exposed.
"""

import asyncio
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from anyio import to_thread
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select

from yondo_api.admin.models import AdminAuditEvent
from yondo_api.api.errors import ApplicationError
from yondo_api.bookings.models import Booking
from yondo_api.companions import service
from yondo_api.companions.dependencies import Admin, Principal, Session, object_storage
from yondo_api.companions.models import CompanionApplication, CompanionProfile
from yondo_api.companions.photos import (
    IMAGE_TYPES,
    PROFILE_PHOTO_LIMIT,
    compensate_upload,
    process_image,
    reconcile_failed_save,
)
from yondo_api.companions.schemas import PhotoDownload
from yondo_api.models.user import AccountStatus, User
from yondo_api.safety.models import UserBlock
from yondo_api.userphotos.models import UserPhoto

router = APIRouter(prefix='/user-photos', tags=['user photos'])


class UserPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content_type: str
    size_bytes: int
    width: int
    height: int
    position: int
    created_at: datetime


class UserPhotoOrder(BaseModel):
    model_config = ConfigDict(extra='forbid')
    photo_ids: list[UUID] = Field(max_length=PROFILE_PHOTO_LIMIT)

    @field_validator('photo_ids')
    @classmethod
    def unique_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError('photo_ids must be unique')
        return value


async def _owner(principal: Principal, session: Session) -> User:
    user = await service.locked_user(session, principal.user.id)
    if user.account_status not in {AccountStatus.ACTIVE, AccountStatus.VERIFICATION_PENDING}:
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    return user


Owner = Annotated[User, Depends(_owner)]


async def visible_user_photos(session, user_id: UUID) -> list[UserPhoto]:
    return list(
        await session.scalars(
            select(UserPhoto)
            .where(UserPhoto.user_id == user_id, UserPhoto.deleted_at.is_(None))
            .order_by(UserPhoto.position)
        )
    )


async def _owned(session, photo_id: UUID, user_id: UUID) -> UserPhoto:
    photo = await session.scalar(
        select(UserPhoto).where(
            UserPhoto.id == photo_id,
            UserPhoto.user_id == user_id,
            UserPhoto.deleted_at.is_(None),
        )
    )
    if photo is None:
        raise ApplicationError('user_photo_not_found', 'Photo not found', 404)
    return photo


async def _download(request: Request, photo: UserPhoto) -> PhotoDownload:
    storage = object_storage(request)
    try:
        return PhotoDownload(url=await storage.create_download_url(photo.storage_key))
    except Exception as exc:
        raise ApplicationError('storage_unavailable', 'Photo download is unavailable', 503) from exc


def _tombstone(photo: UserPhoto) -> None:
    photo.deleted_at = datetime.now(UTC)
    photo.position = None


@router.get('/me', response_model=list[UserPhotoResponse])
async def list_my_photos(owner: Owner, session: Session):
    return await visible_user_photos(session, owner.id)


@router.post(
    '/me',
    response_model=UserPhotoResponse,
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
async def upload_my_photo(request: Request, owner: Owner, session: Session):
    """Upload raw JPEG/PNG/WebP bytes (re-encoded to JPEG without EXIF). At most 6 photos."""
    storage = object_storage(request)
    settings = request.app.state.settings
    photos = await visible_user_photos(session, owner.id)
    # Tombstones count toward the retained cap (under the owner row lock), as for companions.
    retained = await session.scalar(
        select(func.count()).select_from(UserPhoto).where(UserPhoto.user_id == owner.id)
    )
    if len(photos) >= PROFILE_PHOTO_LIMIT or retained >= settings.companion_max_photos:
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
    key = f'users/{owner.id}/{photo_id}.jpg'

    async def chunks():
        yield content

    try:
        await storage.upload(key, chunks(), 'image/jpeg')
    except asyncio.CancelledError:
        await compensate_upload(storage, key)
        raise
    except Exception as exc:
        await compensate_upload(storage, key)
        raise ApplicationError('storage_unavailable', 'Photo upload failed', 503) from exc
    item = UserPhoto(
        id=photo_id,
        user_id=owner.id,
        storage_key=key,
        content_type='image/jpeg',
        size_bytes=len(content),
        width=width,
        height=height,
        position=max((photo.position for photo in photos), default=-1) + 1,
    )
    session.add(item)
    try:
        await service.save(session)
    except asyncio.CancelledError:
        await reconcile_failed_save(request, storage, item)
        raise
    except Exception:
        if await reconcile_failed_save(request, storage, item):
            return item
        raise
    await session.refresh(item)
    return item


@router.put('/me/order', response_model=list[UserPhotoResponse])
async def reorder_my_photos(payload: UserPhotoOrder, owner: Owner, session: Session):
    photos = await visible_user_photos(session, owner.id)
    by_id = {photo.id: photo for photo in photos}
    if set(payload.photo_ids) != set(by_id):
        raise ApplicationError(
            'invalid_photo_order', 'Supply every current photo exactly once', 422
        )
    offset = max((photo.position for photo in photos), default=-1) + 1
    for index, photo in enumerate(photos):
        photo.position = offset + index
    await session.flush()
    for index, photo_id in enumerate(payload.photo_ids):
        by_id[photo_id].position = index
    await service.save(session)
    return [by_id[photo_id] for photo_id in payload.photo_ids]


@router.get('/me/{photo_id}/download', response_model=PhotoDownload)
async def download_my_photo(photo_id: UUID, request: Request, owner: Owner, session: Session):
    return await _download(request, await _owned(session, photo_id, owner.id))


@router.delete('/me/{photo_id}', status_code=204)
async def delete_my_photo(photo_id: UUID, owner: Owner, session: Session):
    _tombstone(await _owned(session, photo_id, owner.id))
    await service.save(session)
    return Response(status_code=204)


async def _booking_customer(session, booking_id: UUID, caller: User) -> UUID:
    """Customer user id of a booking, only for the booking's companion or its customer."""
    booking = await session.get(Booking, booking_id)
    if booking is None:
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    companion_user_id = await session.scalar(
        select(CompanionApplication.user_id)
        .join(CompanionProfile, CompanionProfile.application_id == CompanionApplication.id)
        .where(CompanionProfile.id == booking.profile_id)
    )
    if caller.id not in {booking.customer_id, companion_user_id}:
        # Same answer as for a missing booking: outsiders learn nothing.
        raise ApplicationError('booking_not_found', 'Booking not found', 404)
    if caller.account_status != AccountStatus.ACTIVE:
        raise ApplicationError('account_unavailable', 'The account is unavailable', 403)
    if caller.id == companion_user_id and companion_user_id != booking.customer_id:
        blocked = await session.scalar(
            select(func.count())
            .select_from(UserBlock)
            .where(
                or_(
                    (UserBlock.blocker_id == booking.customer_id)
                    & (UserBlock.blocked_id == companion_user_id),
                    (UserBlock.blocker_id == companion_user_id)
                    & (UserBlock.blocked_id == booking.customer_id),
                )
            )
        )
        if blocked:
            raise ApplicationError('customer_photos_unavailable', 'Photos are unavailable', 403)
    return booking.customer_id


@router.get('/bookings/{booking_id}', response_model=list[UserPhotoResponse])
async def list_booking_customer_photos(booking_id: UUID, principal: Principal, session: Session):
    """The booking customer's photos, for the companion who received the request."""
    customer_id = await _booking_customer(session, booking_id, principal.user)
    return await visible_user_photos(session, customer_id)


@router.get('/bookings/{booking_id}/{photo_id}/download', response_model=PhotoDownload)
async def download_booking_customer_photo(
    booking_id: UUID, photo_id: UUID, request: Request, principal: Principal, session: Session
):
    customer_id = await _booking_customer(session, booking_id, principal.user)
    return await _download(request, await _owned(session, photo_id, customer_id))


@router.get('/admin/users/{user_id}', response_model=list[UserPhotoResponse])
async def admin_list_photos(user_id: UUID, admin: Admin, session: Session):
    return await visible_user_photos(session, user_id)


@router.get('/admin/users/{user_id}/{photo_id}/download', response_model=PhotoDownload)
async def admin_download_photo(
    user_id: UUID, photo_id: UUID, request: Request, admin: Admin, session: Session
):
    return await _download(request, await _owned(session, photo_id, user_id))


@router.delete('/admin/users/{user_id}/{photo_id}', status_code=204)
async def admin_remove_photo(user_id: UUID, photo_id: UUID, admin: Admin, session: Session):
    """Moderation: hide an inappropriate photo (tombstoned, audited)."""
    _tombstone(await _owned(session, photo_id, user_id))
    session.add(
        AdminAuditEvent(
            admin_id=admin.id,
            target_id=user_id,
            action='user_photo_removed',
            reason=f'photo {photo_id}',
        )
    )
    await service.save(session)
    return Response(status_code=204)
