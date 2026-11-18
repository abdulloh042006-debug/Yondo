"""Push device registration and the public push configuration (docs/push-notifications.md)."""
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from yondo_api.api.errors import ApplicationError
from yondo_api.companions.dependencies import Principal, Session
from yondo_api.notifications.router import check_active
from yondo_api.push import webpush
from yondo_api.push.models import PushDevice

router = APIRouter(prefix='/push', tags=['push'])


class WebPushConfig(BaseModel):
    enabled: bool
    vapid_public_key: str | None


class AndroidPushConfig(BaseModel):
    enabled: bool


class PushConfig(BaseModel):
    web: WebPushConfig
    android: AndroidPushConfig


class DeviceRegister(BaseModel):
    platform: Literal['android', 'web']
    token: Annotated[str | None, Field(min_length=20, max_length=1024)] = None
    endpoint: Annotated[str | None, Field(min_length=12, max_length=1024)] = None
    p256dh: Annotated[str | None, Field(min_length=80, max_length=128)] = None
    auth: Annotated[str | None, Field(min_length=16, max_length=64)] = None

    @model_validator(mode='after')
    def one_target(self):
        web_fields = (self.endpoint, self.p256dh, self.auth)
        if self.platform == 'android' and (self.token is None or any(web_fields)):
            raise ValueError('android devices need token only')
        if self.platform == 'web' and (self.token is not None or not all(web_fields)):
            raise ValueError('web devices need endpoint, p256dh and auth')
        return self


class DeviceRead(BaseModel):
    id: UUID
    platform: str
    created_at: datetime
    last_seen_at: datetime


def dispatcher(request: Request):
    return request.app.state.push_dispatcher


@router.get('/config', response_model=PushConfig)
async def push_config(request: Request):
    """Public: which platforms can receive push, and the Web Push VAPID public key."""
    push = dispatcher(request)
    public_key = (await push.vapid()).public_key if push.web_enabled else None
    return PushConfig(
        web=WebPushConfig(enabled=push.web_enabled, vapid_public_key=public_key),
        android=AndroidPushConfig(enabled=push.android_enabled),
    )


@router.put('/devices', response_model=DeviceRead)
async def register_device(
    body: DeviceRegister, request: Request, principal: Principal, session: Session
):
    """Register or refresh this device. A token seen before moves to the signed-in user."""
    check_active(principal)
    push = dispatcher(request)
    settings = request.app.state.settings
    if body.platform == 'web':
        if not push.web_enabled:
            raise ApplicationError('push_unavailable', 'Web push is not configured', 503)
        if not webpush.endpoint_allowed(body.endpoint, settings.webpush_allowed_hosts):
            raise ApplicationError('push_endpoint_not_allowed', 'Unsupported push service', 422)
        if not webpush.valid_client_keys(body.p256dh, body.auth):
            raise ApplicationError('push_keys_invalid', 'Invalid subscription keys', 422)
        match = PushDevice.endpoint == body.endpoint
    else:
        if not push.android_enabled:
            raise ApplicationError('push_unavailable', 'Android push is not configured', 503)
        match = PushDevice.fcm_token == body.token
    now = datetime.now(UTC)
    device = await session.scalar(select(PushDevice).where(match).with_for_update())
    if device is None:
        device = PushDevice(
            platform=body.platform, fcm_token=body.token, endpoint=body.endpoint,
            created_at=now,
        )
        session.add(device)
    device.user_id = principal.user.id
    device.p256dh, device.auth_secret = body.p256dh, body.auth
    device.last_seen_at, device.disabled_at = now, None
    await session.commit()
    return DeviceRead(
        id=device.id, platform=device.platform,
        created_at=device.created_at or now, last_seen_at=device.last_seen_at,
    )


@router.delete('/devices/{device_id}', status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device(device_id: UUID, principal: Principal, session: Session):
    """Remove this device (sign-out, or push switched off). Works for any account status."""
    device = await session.scalar(
        select(PushDevice).where(
            PushDevice.id == device_id, PushDevice.user_id == principal.user.id
        )
    )
    if device is None:
        raise ApplicationError('push_device_not_found', 'Device not found', 404)
    await session.delete(device)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

