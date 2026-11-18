"""Minimal OpenID Connect ID-token verification (JWS compact, RS256 / ES256) with a JWKS cache.

Uses only ``cryptography`` (already a dependency). Tokens, codes and keys are never logged.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from yondo_api.api.errors import ApplicationError

JWKS_TTL_SECONDS = 3600
# A token with an unknown key id may force one early refetch, at most this often.
JWKS_MIN_REFRESH_SECONDS = 60
CLOCK_SKEW_SECONDS = 60
ALGORITHMS = ('RS256', 'ES256')


def invalid_token() -> ApplicationError:
    return ApplicationError('social_token_invalid', 'The sign-in token is invalid', 401)


def provider_unreachable() -> ApplicationError:
    return ApplicationError(
        'social_provider_unreachable', 'The sign-in provider cannot be reached; try again', 503
    )


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def _int(value: str) -> int:
    return int.from_bytes(b64url_decode(value), 'big')


def _public_key(jwk: dict[str, Any]):
    if jwk.get('kty') == 'RSA':
        return rsa.RSAPublicNumbers(_int(jwk['e']), _int(jwk['n'])).public_key()
    if jwk.get('kty') == 'EC' and jwk.get('crv') == 'P-256':
        return ec.EllipticCurvePublicNumbers(
            _int(jwk['x']), _int(jwk['y']), ec.SECP256R1()
        ).public_key()
    return None


@dataclass
class JwksCache:
    url: str
    keys: dict[str, dict[str, Any]] = field(default_factory=dict)
    fetched_at: float = 0.0

    async def _fetch(self, client: httpx.AsyncClient) -> None:
        try:
            response = await client.get(self.url)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise provider_unreachable() from exc
        keys = {}
        for jwk in data.get('keys', []) if isinstance(data, dict) else []:
            if isinstance(jwk, dict) and isinstance(jwk.get('kid'), str):
                keys[jwk['kid']] = jwk
        self.keys, self.fetched_at = keys, time.monotonic()

    async def key(self, client: httpx.AsyncClient, kid: str) -> dict[str, Any] | None:
        age = time.monotonic() - self.fetched_at
        if not self.fetched_at or age > JWKS_TTL_SECONDS:
            await self._fetch(client)
        elif kid not in self.keys and age > JWKS_MIN_REFRESH_SECONDS:
            await self._fetch(client)  # key rotation
        return self.keys.get(kid)


def _verify_signature(alg: str, jwk: dict[str, Any], signed: bytes, signature: bytes) -> bool:
    key = _public_key(jwk)
    if key is None or jwk.get('alg', alg) != alg:
        return False
    try:
        if alg == 'RS256' and isinstance(key, rsa.RSAPublicKey):
            key.verify(signature, signed, padding.PKCS1v15(), hashes.SHA256())
            return True
        if alg == 'ES256' and isinstance(key, ec.EllipticCurvePublicKey) and len(signature) == 64:
            der = encode_dss_signature(
                int.from_bytes(signature[:32], 'big'), int.from_bytes(signature[32:], 'big')
            )
            key.verify(der, signed, ec.ECDSA(hashes.SHA256()))
            return True
    except InvalidSignature:
        return False
    return False


async def verify_id_token(
    token: str,
    *,
    jwks: JwksCache,
    client: httpx.AsyncClient,
    issuers: tuple[str, ...],
    audiences: list[str],
    now: float | None = None,
) -> dict[str, Any]:
    """Check signature, ``iss``, ``aud`` and ``exp``/``iat``; return the claims."""
    parts = token.split('.') if isinstance(token, str) and len(token) < 16_384 else []
    if len(parts) != 3:
        raise invalid_token()
    try:
        header = json.loads(b64url_decode(parts[0]))
        claims = json.loads(b64url_decode(parts[1]))
        signature = b64url_decode(parts[2])
    except (ValueError, UnicodeDecodeError) as exc:
        raise invalid_token() from exc
    if not isinstance(header, dict) or not isinstance(claims, dict):
        raise invalid_token()
    alg, kid = header.get('alg'), header.get('kid')
    if alg not in ALGORITHMS or not isinstance(kid, str):
        raise invalid_token()
    jwk = await jwks.key(client, kid)
    if jwk is None or not _verify_signature(
        alg, jwk, f'{parts[0]}.{parts[1]}'.encode(), signature
    ):
        raise invalid_token()
    current = time.time() if now is None else now
    if claims.get('iss') not in issuers:
        raise invalid_token()
    aud = claims.get('aud')
    aud_list = aud if isinstance(aud, list) else [aud]
    if not any(isinstance(a, str) and a in audiences for a in aud_list):
        raise invalid_token()
    exp, iat = claims.get('exp'), claims.get('iat')
    if not isinstance(exp, int | float) or current > exp + CLOCK_SKEW_SECONDS:
        raise invalid_token()
    if isinstance(iat, int | float) and iat > current + CLOCK_SKEW_SECONDS:
        raise invalid_token()
    sub = claims.get('sub')
    if not isinstance(sub, str) or not sub or len(sub) > 255:
        raise invalid_token()
    return claims
