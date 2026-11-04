"""Push delivery providers: a development log provider and Firebase Cloud Messaging HTTP v1."""

from __future__ import annotations

import base64
import json
import time
from typing import Any

import httpx
import structlog

from yondo_api.integrations.notifications import PushMessage

logger = structlog.get_logger(__name__)

FCM_SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
TOKEN_URL = 'https://oauth2.googleapis.com/token'


class InvalidPushToken(Exception):
    """The device token is no longer registered and should be deleted."""


class LogPushProvider:
    """Development provider: records the push in logs instead of sending it."""

    def __init__(self) -> None:
        self.sent: list[PushMessage] = []

    async def send(self, message: PushMessage) -> str:
        self.sent.append(message)
        logger.info('push_logged', title=message.title, data_keys=sorted(message.data))
        return 'logged'


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


class FcmPushProvider:
    """FCM HTTP v1 using a Google service account (JWT bearer grant, RS256)."""

    def __init__(
        self,
        service_account: dict[str, Any],
        project_id: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        from cryptography.hazmat.primitives import serialization

        self.client_email = service_account['client_email']
        self.key_id = service_account.get('private_key_id', '')
        self.project_id = project_id or service_account['project_id']
        self.private_key = serialization.load_pem_private_key(
            service_account['private_key'].encode(), password=None
        )
        self.client = client or httpx.AsyncClient(timeout=15)
        self._token: str | None = None
        self._token_expires = 0.0

    @classmethod
    def from_file(cls, path: str, project_id: str | None = None) -> FcmPushProvider:
        with open(path, encoding='utf-8') as handle:
            return cls(json.load(handle), project_id or None)

    def assertion(self, now: float | None = None) -> str:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        issued = int(now or time.time())
        header = {'alg': 'RS256', 'typ': 'JWT', 'kid': self.key_id}
        claims = {
            'iss': self.client_email,
            'scope': FCM_SCOPE,
            'aud': TOKEN_URL,
            'iat': issued,
            'exp': issued + 3600,
        }
        signing_input = f'{_b64(json.dumps(header).encode())}.{_b64(json.dumps(claims).encode())}'
        signature = self.private_key.sign(
            signing_input.encode(), padding.PKCS1v15(), hashes.SHA256()
        )
        return f'{signing_input}.{_b64(signature)}'

    async def access_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        response = await self.client.post(
            TOKEN_URL,
            data={
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion': self.assertion(),
            },
        )
        response.raise_for_status()
        body = response.json()
        self._token = body['access_token']
        self._token_expires = time.time() + int(body.get('expires_in', 3600))
        return self._token

    async def send(self, message: PushMessage) -> str:
        token = await self.access_token()
        response = await self.client.post(
            f'https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'message': {
                    'token': message.token,
                    'notification': {'title': message.title, 'body': message.body},
                    'data': message.data,
                }
            },
        )
        if response.status_code in {400, 404}:
            details = json.dumps(response.json()) if response.content else ''
            if 'UNREGISTERED' in details or 'INVALID_ARGUMENT' in details:
                raise InvalidPushToken(message.token)
        response.raise_for_status()
        return response.json().get('name', '')
