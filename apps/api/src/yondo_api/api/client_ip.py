"""Resolve the real client IP once, so every per-IP limit uses a key a client cannot forge.

Modes (``YONDO_CLIENT_IP_MODE``, docs/client-ip.md):
- ``peer`` (default): the TCP peer address. Never trusts a header. Behind a proxy every client
  then shares the proxy's address, which is safe but coarse.
- ``header``: the value of ``YONDO_CLIENT_IP_HEADER`` (for example a header the edge sets and
  overwrites itself), used only when the TCP peer is a trusted proxy.
- ``xff``: the ``YONDO_CLIENT_IP_XFF_HOPS``-th entry from the RIGHT of X-Forwarded-For, used only
  when the TCP peer is a trusted proxy. Entries further left can be written by the client.

The uvicorn proxy-header handling must be off (``--no-proxy-headers``); this middleware replaces it.
"""

from __future__ import annotations

import ipaddress

from starlette.types import ASGIApp, Receive, Scope, Send


def _ip(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if candidate.startswith('[') and ']' in candidate:  # [v6]:port
        candidate = candidate[1 : candidate.index(']')]
    elif candidate.count(':') == 1:  # v4:port
        candidate = candidate.split(':', 1)[0]
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


class ClientIpMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        mode: str = 'peer',
        header: str = '',
        hops: int = 1,
        trusted_proxies: str = '',
    ) -> None:
        self.app = app
        self.mode = mode
        self.header = header.strip().lower().encode()
        self.hops = hops
        self.trusted = [
            ipaddress.ip_network(part.strip(), strict=False)
            for part in trusted_proxies.split(',')
            if part.strip()
        ]

    def _trusted(self, peer: str | None) -> bool:
        address = _ip(peer)
        if address is None:
            return False
        parsed = ipaddress.ip_address(address)
        return any(parsed in network for network in self.trusted)

    def _from_headers(self, headers: list[tuple[bytes, bytes]]) -> str | None:
        if self.mode == 'header':
            values = [v for k, v in headers if k.lower() == self.header]
            return _ip(values[-1].decode('latin-1')) if len(values) == 1 else None
        if self.mode == 'xff':
            parts: list[str] = []
            for key, value in headers:
                if key.lower() == b'x-forwarded-for':
                    parts.extend(p.strip() for p in value.decode('latin-1').split(','))
            parts = [p for p in parts if p]
            return _ip(parts[-self.hops]) if len(parts) >= self.hops else None
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] in ('http', 'websocket'):
            client = scope.get('client')
            peer = client[0] if client else None
            scope.setdefault('state', {})['peer_ip'] = peer
            if self.mode != 'peer' and self._trusted(peer):
                resolved = self._from_headers(scope.get('headers', []))
                if resolved is not None:
                    scope['client'] = (resolved, client[1] if client else 0)
        await self.app(scope, receive, send)
