"""Firebase Cloud Messaging HTTP v1 sender (Android).

Authenticates with a Google service account (JSON from the env, a secret): a self-signed RS256
JWT is exchanged for a one-hour OAuth access token, cached in memory. The JSON and the tokens
are never logged.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from yondo_api.push.webpush import b64url

SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
DEFAULT_TOKEN_URI = 'https://oauth2.googleapis.com/token'
FCM_BASE_URL = 'https://fcm.googleapis.com'


class FcmConfigError(ValueError):
    """The service-account JSON is unusable (the message never includes its content)."""


@dataclass(frozen=True)
class ServiceAccount:
    client_email: str
    private_key: rsa.RSAPrivateKey
    token_uri: str
    project_id: str

    @classmethod
    def from_json(cls, raw: str, project_id: str | None = None) -> ServiceAccount:
        try:
            data = json.loads(raw)
            key = serialization.load_pem_private_key(data['private_key'].encode(), password=None)
            email = str(data['client_email'])
        except (ValueError, KeyError, TypeError, AttributeError):
            raise FcmConfigError('FCM service-account JSON is not valid') from None
        if not isinstance(key, rsa.RSAPrivateKey):
            raise FcmConfigError('FCM service-account key is not an RSA key')
        token_uri = str(data.get('token_uri') or DEFAULT_TOKEN_URI)
        if not token_uri.startswith('https://oauth2.googleapis.com/'):
            token_uri = DEFAULT_TOKEN_URI
        project = project_id or data.get('project_id')
        if not project:
            raise FcmConfigError('FCM project id is missing')
        return cls(email, key, token_uri, str(project))

    def assertion(self, now: int) -> str:
        header = b64url(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode())
        claims = b64url(json.dumps({
            'iss': self.client_email,
            'scope': SCOPE,
            'aud': self.token_uri,
            'iat': now,
            'exp': now + 3600,
        }).encode())
        signing_input = f'{header}.{claims}'.encode('ascii')
        signature = self.private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        return f'{header}.{claims}.{b64url(signature)}'


class FcmSender:
    def __init__(self, account: ServiceAccount, *, base_url: str = FCM_BASE_URL):
        self.account = account
        self.base_url = base_url.rstrip('/')
        self._token: tuple[str, float] | None = None
        self._lock = asyncio.Lock()

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        async with self._lock:
            if self._token and self._token[1] > time.time() + 60:
                return self._token[0]
            response = await client.post(
                self.account.token_uri,
                data={
                    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                    'assertion': self.account.assertion(int(time.time())),
                },
            )
            response.raise_for_status()
            body = response.json()
            self._token = (body['access_token'], time.time() + int(body.get('expires_in', 3600)))
            return self._token[0]

    async def send(self, client: httpx.AsyncClient, token: str, message: dict) -> str:
        """Send one message. Returns 'ok', 'invalid' (prune the token) or 'error'."""
        access = await self._access_token(client)
        response = await client.post(
            f'{self.base_url}/v1/projects/{self.account.project_id}/messages:send',
            headers={'Authorization': f'Bearer {access}'},
            json={'message': {**message, 'token': token}},
        )
        if response.status_code == 200:
            return 'ok'
        if response.status_code in (404, 410) or _error_code(response) == 'UNREGISTERED':
            return 'invalid'
        if response.status_code == 401:
            self._token = None
        return 'error'


def _error_code(response: httpx.Response) -> str | None:
    try:
        for detail in response.json().get('error', {}).get('details', []):
            if detail.get('errorCode'):
                return str(detail['errorCode'])
    except (ValueError, AttributeError):
        return None
    return None
