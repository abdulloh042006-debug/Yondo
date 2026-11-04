from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Protocol
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


def user_channel(user_id: UUID | str) -> str:
    return f'yondo:user:{user_id}'


class RealtimeBroker(Protocol):
    async def publish(self, channel: str, event: dict[str, Any]) -> None: ...

    def subscribe(self, channel: str) -> Any:
        """Async context manager yielding an async iterator of events."""


class InMemoryBroker:
    """Single-process broker for development and tests."""

    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        for queue in list(self._queues.get(channel, ())):
            queue.put_nowait(event)

    @asynccontextmanager
    async def subscribe(self, channel: str) -> AsyncIterator[AsyncIterator[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        self._queues[channel].add(queue)

        async def events() -> AsyncIterator[dict[str, Any]]:
            while True:
                yield await queue.get()

        try:
            yield events()
        finally:
            self._queues[channel].discard(queue)
            if not self._queues[channel]:
                self._queues.pop(channel, None)


class RedisBroker:
    """Multi-instance broker using Redis pub/sub."""

    def __init__(self, client: Any) -> None:
        self.client = client

    async def publish(self, channel: str, event: dict[str, Any]) -> None:
        await self.client.publish(channel, json.dumps(event, default=str))

    @asynccontextmanager
    async def subscribe(self, channel: str) -> AsyncIterator[AsyncIterator[dict[str, Any]]]:
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)

        async def events() -> AsyncIterator[dict[str, Any]]:
            async for message in pubsub.listen():
                if message.get('type') == 'message':
                    yield json.loads(message['data'])

        try:
            yield events()
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


_background: set[asyncio.Task[None]] = set()


async def _publish_safely(broker: RealtimeBroker, channel: str, event: dict[str, Any]) -> None:
    try:
        await broker.publish(channel, event)
    except Exception:
        logger.warning('realtime_publish_failed', channel=channel, event_type=event.get('type'))


def queue_event(session: Any, user_id: UUID, event: dict[str, Any]) -> None:
    """Queue an event to publish only after the surrounding transaction commits."""
    session.info.setdefault('pending_realtime', []).append((user_channel(user_id), event))


def flush_after_commit(sync_session: Any) -> None:
    events = sync_session.info.pop('pending_realtime', [])
    broker = sync_session.info.get('realtime_broker')
    if broker is None or not events:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    for channel, event in events:
        task = loop.create_task(_publish_safely(broker, channel, event))
        _background.add(task)
        task.add_done_callback(_background.discard)


def discard_after_rollback(sync_session: Any) -> None:
    sync_session.info.pop('pending_realtime', None)
