"""Web Push (RFC 8030) with VAPID (RFC 8292) and aes128gcm payload encryption (RFC 8291).

Implemented on top of ``cryptography`` only, so the sender stays async (httpx) and adds a
single, widely used dependency instead of pywebpush (sync ``requests`` + three more packages).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import struct
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

RECORD_SIZE = 4096


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def _hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def public_bytes(key: ec.EllipticCurvePublicKey) -> bytes:
    return key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )


def private_from_raw(raw: bytes) -> ec.EllipticCurvePrivateKey:
    if len(raw) != 32:
        raise ValueError('VAPID private key must be a raw 32-byte P-256 scalar')
    return ec.derive_private_key(int.from_bytes(raw, 'big'), ec.SECP256R1())


def generate_vapid_keypair() -> tuple[str, str]:
    """Return (private, public) as base64url: raw 32-byte scalar and 65-byte uncompressed point."""
    key = ec.generate_private_key(ec.SECP256R1())
    raw = key.private_numbers().private_value.to_bytes(32, 'big')
    return b64url(raw), b64url(public_bytes(key.public_key()))


def valid_client_keys(p256dh: str, auth: str) -> bool:
    try:
        point, secret = b64url_decode(p256dh), b64url_decode(auth)
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), point)
    except (ValueError, TypeError):
        return False
    return len(point) == 65 and len(secret) == 16


def encrypt(
    plaintext: bytes,
    ua_public: bytes,
    auth_secret: bytes,
    *,
    salt: bytes | None = None,
    as_private: ec.EllipticCurvePrivateKey | None = None,
) -> bytes:
    """Encrypt one push message as a single aes128gcm record (RFC 8291 §3.4, RFC 8188)."""
    salt = salt or os.urandom(16)
    as_private = as_private or ec.generate_private_key(ec.SECP256R1())
    as_public = public_bytes(as_private.public_key())
    receiver = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public)
    shared = as_private.exchange(ec.ECDH(), receiver)
    prk_key = _hmac(auth_secret, shared)
    ikm = _hmac(prk_key, b'WebPush: info\x00' + ua_public + as_public + b'\x01')
    prk = _hmac(salt, ikm)
    cek = _hmac(prk, b'Content-Encoding: aes128gcm\x00\x01')[:16]
    nonce = _hmac(prk, b'Content-Encoding: nonce\x00\x01')[:12]
    if len(plaintext) + 17 > RECORD_SIZE:
        raise ValueError('Push payload too large')
    ciphertext = AESGCM(cek).encrypt(nonce, plaintext + b'\x02', None)
    header = salt + struct.pack('!IB', RECORD_SIZE, len(as_public)) + as_public
    return header + ciphertext


def vapid_authorization(
    endpoint: str, private_key: ec.EllipticCurvePrivateKey, subject: str, *, ttl: int = 43_200
) -> str:
    parts = urlsplit(endpoint)
    claims = {
        'aud': f'{parts.scheme}://{parts.netloc}',
        'exp': int(time.time()) + ttl,
        'sub': subject,
    }
    header = b64url(json.dumps({'typ': 'JWT', 'alg': 'ES256'}, separators=(',', ':')).encode())
    body = b64url(json.dumps(claims, separators=(',', ':')).encode())
    signing_input = f'{header}.{body}'.encode('ascii')
    r, s = decode_dss_signature(private_key.sign(signing_input, ec.ECDSA(hashes.SHA256())))
    signature = b64url(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))
    public = b64url(public_bytes(private_key.public_key()))
    return f'vapid t={header}.{body}.{signature}, k={public}'


def endpoint_allowed(endpoint: str, allowed_hosts: tuple[str, ...]) -> bool:
    """Only https endpoints of known push services: the server POSTs to this URL (no SSRF)."""
    try:
        parts = urlsplit(endpoint)
    except ValueError:
        return False
    host = (parts.hostname or '').lower()
    if parts.scheme != 'https' or not host or parts.port not in (None, 443) or parts.username:
        return False
    return any(host == allowed or host.endswith('.' + allowed) for allowed in allowed_hosts)


@dataclass(frozen=True)
class WebPushRequest:
    url: str
    headers: dict[str, str]
    body: bytes


def build_request(
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    payload: dict,
    private_key: ec.EllipticCurvePrivateKey,
    subject: str,
    ttl_seconds: int = 86_400,
) -> WebPushRequest:
    body = encrypt(
        json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8'),
        b64url_decode(p256dh),
        b64url_decode(auth),
    )
    return WebPushRequest(
        url=endpoint,
        headers={
            'Authorization': vapid_authorization(endpoint, private_key, subject),
            'Content-Encoding': 'aes128gcm',
            'Content-Type': 'application/octet-stream',
            'TTL': str(ttl_seconds),
            'Urgency': 'normal',
        },
        body=body,
    )
