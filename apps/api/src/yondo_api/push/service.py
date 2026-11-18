"""Push delivery: after a transaction that created in-app notifications commits, send a short
push to each recipient's active devices in the background.

The send never blocks or fails the request: it runs as a separate task with short timeouts, every
error is logged (without tokens, keys or message text) and swallowed. Providers that are not
configured are no-ops.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import httpx
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yondo_api.config import Settings
from yondo_api.db.session import YondoSession
from yondo_api.models.user import AccountStatus, User
from yondo_api.notifications.models import UserNotification
from yondo_api.push import webpush
from yondo_api.push.fcm import FcmConfigError, FcmSender, ServiceAccount
from yondo_api.push.messages import push_text
from yondo_api.push.models import PushDevice, PushVapidKey

logger = logging.getLogger(__name__)

ANDROID_CHANNEL_ID = 'yondo'


@dataclass
class VapidKeys:
    private_key: ec.EllipticCurvePrivateKey
    public_key: str
    source: str  # 'env' or 'database'


def build_fcm_sender(settings: Settings) -> FcmSender | None:
    if settings.fcm_service_account_json is None:
        logger.info('push: Android (FCM) not configured; Android push is off')
        return None
    try:
        account = ServiceAccount.from_json(
            settings.fcm_service_account_json.get_secret_value(), settings.fcm_project_id
        )
    except FcmConfigError as exc:
        logger.error('push: Android (FCM) disabled: %s', exc)
        return None
    logger.info('push: Android (FCM) enabled')
    return FcmSender(account, base_url=settings.fcm_base_url)


async def load_vapid_keys(
    session_factory: async_sessionmaker[AsyncSession], settings: Settings
) -> VapidKeys:
    """Env key wins; otherwise the key pair stored in the database, generated on first use."""
    if settings.webpush_vapid_private_key is not None:
        key = webpush.private_from_raw(
            webpush.b64url_decode(settings.webpush_vapid_private_key.get_secret_value())
        )
        return VapidKeys(key, webpush.b64url(webpush.public_bytes(key.public_key())), 'env')
    async with session_factory() as session:
        row = await session.get(PushVapidKey, 1)
        if row is None:
            private, public = webpush.generate_vapid_keypair()
            session.add(PushVapidKey(id=1, private_key=private, public_key=public))
            try:
                await session.commit()
            except IntegrityError:  # another worker generated it first: use theirs
                await session.rollback()
            row = await session.get(PushVapidKey, 1, populate_existing=True)
        key = webpush.private_from_raw(webpush.b64url_decode(row.private_key))
        return VapidKeys(key, row.public_key, 'database')


def deep_link(notification: UserNotification) -> str:
    if notification.booking_id is not None:
        return f'/bookings/{notification.booking_id}'
    return '/notifications'


class PushDispatcher:
    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        fcm: FcmSender | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings
        self.session_factory = session_factory
        self.fcm = fcm
        self.web_enabled = settings.webpush_enabled
        self.transport = transport
        self._vapid: VapidKeys | None = None
        self._vapid_lock = asyncio.Lock()
        self._tasks: set[asyncio.Task] = set()

    @property
    def android_enabled(self) -> bool:
        return self.fcm is not None

    async def vapid(self) -> VapidKeys:
        async with self._vapid_lock:
            if self._vapid is None:
                self._vapid = await load_vapid_keys(self.session_factory, self.settings)
            return self._vapid

    def schedule(self, notification_ids: list[UUID]) -> None:
        if not notification_ids or not (self.web_enabled or self.android_enabled):
            return
        try:
            task = asyncio.get_running_loop().create_task(self.deliver(notification_ids))
        except RuntimeError:  # no running loop (sync caller): push is best effort
            return
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self) -> None:
        """Wait for scheduled sends (tests and graceful shutdown)."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def deliver(self, notification_ids: list[UUID]) -> None:
        try:
            await self._deliver(notification_ids)
        except Exception:  # never let a push failure escape the background task
            logger.exception('push: delivery failed')

    async def _deliver(self, notification_ids: list[UUID]) -> None:
        async with self.session_factory() as session:
            rows = (await session.execute(
                select(UserNotification, User.ui_locale)
                .join(User, User.id == UserNotification.recipient_id)
                .where(
                    UserNotification.id.in_(notification_ids),
                    User.account_status == AccountStatus.ACTIVE,
                )
            )).all()
            if not rows:
                return
            platforms = [p for p, on in (('web', self.web_enabled),
                                         ('android', self.android_enabled)) if on]
            devices = list(await session.scalars(
                select(PushDevice).where(
                    PushDevice.user_id.in_({n.recipient_id for n, _ in rows}),
                    PushDevice.disabled_at.is_(None),
                    PushDevice.platform.in_(platforms),
                )
            ))
            if not devices:
                return
            by_user: dict[UUID, list[PushDevice]] = {}
            for device in devices:
                by_user.setdefault(device.user_id, []).append(device)
            jobs = []
            timeout = httpx.Timeout(self.settings.push_send_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout, transport=self.transport) as client:
                for notification, locale in rows:
                    title, body = push_text(notification.kind, locale)
                    data = {
                        'notification_id': str(notification.id),
                        'kind': notification.kind,
                        'url': deep_link(notification),
                    }
                    for device in by_user.get(notification.recipient_id, []):
                        jobs.append(self._send(client, device, title, body, data))
                results = await asyncio.gather(*jobs, return_exceptions=True)
            invalid = {r for r in results if isinstance(r, UUID)}
            if invalid:
                now = datetime.now(UTC)
                for device in devices:
                    if device.id in invalid:
                        device.disabled_at = now
                await session.commit()
                logger.info('push: disabled %d device(s) the provider reported invalid',
                            len(invalid))

    async def _send(self, client, device: PushDevice, title: str, body: str, data: dict):
        """Returns the device id when the provider says the target is gone."""
        try:
            if device.platform == 'android':
                outcome = await self.fcm.send(client, device.fcm_token, {
                    'notification': {'title': title, 'body': body},
                    'data': data,
                    'android': {
                        'priority': 'high',
                        'notification': {
                            'channel_id': ANDROID_CHANNEL_ID,
                            'sound': 'yondo_notify',  # Android < 8 (no channels)
                            'tag': data['notification_id'],
                        },
                    },
                })
            else:
                outcome = await self._send_web(client, device, title, body, data)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning('push: %s send failed (%s)', device.platform, type(exc).__name__)
            return None
        if outcome == 'invalid':
            return device.id
        if outcome != 'ok':
            logger.warning('push: %s send rejected (device %s)', device.platform, device.id)
        return None

    async def _send_web(self, client, device: PushDevice, title, body, data) -> str:
        if not webpush.endpoint_allowed(device.endpoint, self.settings.webpush_allowed_hosts):
            return 'invalid'
        keys = await self.vapid()
        request = webpush.build_request(
            endpoint=device.endpoint,
            p256dh=device.p256dh,
            auth=device.auth_secret,
            payload={'title': title, 'body': body, **data},
            private_key=keys.private_key,
            subject=self.settings.webpush_subject_value,
        )
        response = await client.post(request.url, headers=request.headers, content=request.body)
        if response.status_code in (200, 201, 202):
            return 'ok'
        if response.status_code in (404, 410):
            return 'invalid'
        return 'error'


def collect_new_notifications(session, _flush_context) -> None:
    """after_flush hook: remember notifications inserted in this transaction."""
    new = [obj.id for obj in session.new if isinstance(obj, UserNotification)]
    if new:
        session.info.setdefault('push_pending', []).extend(new)


def dispatch_after_commit(session) -> None:
    pending = session.info.pop('push_pending', None)
    state = session.info.get('app_state')
    dispatcher = getattr(state, 'push_dispatcher', None) if state is not None else None
    if pending and dispatcher is not None:
        dispatcher.schedule(pending)


def discard_pending(session, *_args) -> None:
    session.info.pop('push_pending', None)


event.listen(YondoSession, 'after_flush', collect_new_notifications)
event.listen(YondoSession, 'after_commit', dispatch_after_commit)
event.listen(YondoSession, 'after_rollback', discard_pending)
