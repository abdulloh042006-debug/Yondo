from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from yondo_api.api.errors import ApplicationError
from yondo_api.auth.dependencies import resolve_access_token
from yondo_api.realtime.broker import user_channel

router = APIRouter(prefix='/realtime', tags=['realtime'])
AUTH_TIMEOUT_SECONDS = 10


async def _first_message_token(websocket: WebSocket) -> str:
    try:
        message = await asyncio.wait_for(websocket.receive_json(), AUTH_TIMEOUT_SECONDS)
    except (TimeoutError, ValueError, WebSocketDisconnect):
        return ''
    if isinstance(message, dict) and message.get('type') == 'auth':
        return str(message.get('access_token') or '')
    return ''


@router.websocket('/ws')
async def realtime_socket(websocket: WebSocket):
    """Per-user event stream: chat messages, booking updates and notifications.

    Preferred: connect without credentials and send ``{"type": "auth", "access_token": ...}``
    as the first message, so the token never appears in URLs or proxy access logs.
    ``?access_token=`` is still accepted for simple clients; deployments then must not log
    WebSocket query strings (the Docker image runs uvicorn with ``--no-access-log``).
    """
    await websocket.accept()
    token = websocket.query_params.get('access_token') or await _first_message_token(websocket)
    factory = websocket.app.state.db_session_factory
    try:
        async with factory() as session:
            principal = await resolve_access_token(session, token)
    except ApplicationError:
        await websocket.close(code=4401)
        return
    broker = websocket.app.state.realtime_broker
    async with broker.subscribe(user_channel(principal.user.id)) as events:

        async def forward() -> None:
            async for event in events:
                await websocket.send_json(event)

        async def receive() -> None:
            while True:
                message = await websocket.receive_text()
                if message == 'ping':
                    await websocket.send_text('pong')

        tasks = [asyncio.create_task(forward()), asyncio.create_task(receive())]
        try:
            await websocket.send_json({'type': 'ready', 'user_id': str(principal.user.id)})
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                with contextlib.suppress(WebSocketDisconnect, RuntimeError):
                    task.result()
        except WebSocketDisconnect:
            pass
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
