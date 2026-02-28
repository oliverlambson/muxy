"""Proxy headers middleware for applications behind reverse proxies (e.g. AWS ALB).

Parses X-Forwarded-For, X-Forwarded-Proto, and X-Forwarded-Port headers from
trusted proxies and overrides scope.client and scope.scheme so downstream
handlers see the real client information.

Headers left in scope.headers for direct access:
    - x-forwarded-port
    - x-amzn-trace-id
    - x-amzn-tls-version
    - x-amzn-tls-cipher-suite
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast, overload

if TYPE_CHECKING:
    from collections.abc import Callable

    from muxy.rsgi import (
        HTTPProtocol,
        HTTPScope,
        RSGIHandler,
        RSGIHTTPHandler,
        RSGIWebsocketHandler,
        WebsocketProtocol,
        WebsocketScope,
    )


class _ProxiedHTTPScope:
    """Lightweight wrapper that overrides client/scheme on an HTTPScope."""

    __slots__ = ("_scope", "client", "scheme")

    def __init__(self, scope: HTTPScope, client: str, scheme: str) -> None:
        self._scope = scope
        self.client = client
        self.scheme = scheme

    def __getattr__(self, name: str) -> object:
        return getattr(self._scope, name)


class _ProxiedWebsocketScope:
    """Lightweight wrapper that overrides client/scheme on a WebsocketScope."""

    __slots__ = ("_scope", "client", "scheme")

    def __init__(self, scope: WebsocketScope, client: str, scheme: str) -> None:
        self._scope = scope
        self.client = client
        self.scheme = scheme

    def __getattr__(self, name: str) -> object:
        return getattr(self._scope, name)


_WS_SCHEME_MAP = {"https": "wss", "http": "ws"}


def proxy_headers(
    *,
    trusted_proxies: frozenset[str],
    num_proxies: int = 1,
) -> Callable[[RSGIHandler], RSGIHandler]:
    """Create proxy headers middleware.

    Parses `X-Forwarded-For` and `X-Forwarded-Proto` from trusted proxies
    and overrides `scope.client` and `scope.scheme` so downstream handlers
    see the real client information. Other proxy headers (`X-Forwarded-Port`,
    `X-Amzn-Trace-Id`, etc.) remain in `scope.headers` for direct access.

    Args:
        trusted_proxies: Set of proxy IP addresses to trust. Use
            `frozenset({"*"})` to trust all connecting clients.
        num_proxies: Number of proxy hops. The real client IP is extracted
            from X-Forwarded-For at position `-(num_proxies)` from the right.
            Default `1` is correct for a single proxy (e.g. ALB only).
            Use `2` for two proxy layers (e.g. CloudFront + ALB).

    Returns:
        Middleware function that wraps handlers with proxy header parsing.

    Example:
        router.use(proxy_headers(trusted_proxies=frozenset({"*"})))

        # Only trust specific proxy IPs
        router.use(proxy_headers(
            trusted_proxies=frozenset({"10.0.0.1", "10.0.0.2"}),
        ))

        # CloudFront + ALB (two proxy hops)
        router.use(proxy_headers(
            trusted_proxies=frozenset({"*"}),
            num_proxies=2,
        ))
    """
    if num_proxies < 1:
        msg = f"num_proxies must be >= 1, got {num_proxies}"
        raise ValueError(msg)
    if not trusted_proxies:
        msg = "trusted_proxies must not be empty"
        raise ValueError(msg)

    # Pre-compute at creation time
    trust_all = "*" in trusted_proxies
    xff_index = -num_proxies

    def middleware(handler: RSGIHandler) -> RSGIHandler:
        @overload
        async def proxied_handler(scope: HTTPScope, proto: HTTPProtocol) -> None: ...
        @overload
        async def proxied_handler(
            scope: WebsocketScope, proto: WebsocketProtocol
        ) -> None: ...
        async def proxied_handler(
            scope: HTTPScope | WebsocketScope,
            proto: HTTPProtocol | WebsocketProtocol,
        ) -> None:
            nonlocal handler

            # Fast path: untrusted proxy, passthrough with zero overhead
            if not (trust_all or scope.client in trusted_proxies):
                if scope.proto == "http":
                    handler = cast("RSGIHTTPHandler", handler)
                    scope = cast("HTTPScope", scope)
                    proto = cast("HTTPProtocol", proto)
                    await handler(scope, proto)
                else:
                    handler = cast("RSGIWebsocketHandler", handler)
                    scope = cast("WebsocketScope", scope)
                    proto = cast("WebsocketProtocol", proto)
                    await handler(scope, proto)
                return

            headers = scope.headers
            xff = headers.get("x-forwarded-for")
            xfp = headers.get("x-forwarded-proto")

            # No proxy headers present, passthrough
            if xff is None and xfp is None:
                if scope.proto == "http":
                    handler = cast("RSGIHTTPHandler", handler)
                    scope = cast("HTTPScope", scope)
                    proto = cast("HTTPProtocol", proto)
                    await handler(scope, proto)
                else:
                    handler = cast("RSGIWebsocketHandler", handler)
                    scope = cast("WebsocketScope", scope)
                    proto = cast("WebsocketProtocol", proto)
                    await handler(scope, proto)
                return

            # Parse X-Forwarded-For
            client = scope.client
            if xff is not None:
                # rsplit with maxsplit avoids splitting the full string
                parts = xff.rsplit(",", maxsplit=num_proxies)
                if parts:
                    idx = xff_index if len(parts) >= num_proxies else 0
                    candidate = parts[idx].strip()
                    if candidate:
                        client = candidate

            # Parse X-Forwarded-Proto (comma-separated in multi-hop, like XFF)
            scheme = scope.scheme
            if xfp is not None:
                parts = xfp.rsplit(",", maxsplit=num_proxies)
                if parts:
                    idx = xff_index if len(parts) >= num_proxies else 0
                    candidate = parts[idx].strip()
                    if candidate:
                        scheme = candidate

            # Wrap scope with overridden fields
            if scope.proto == "http":
                handler = cast("RSGIHTTPHandler", handler)
                proto = cast("HTTPProtocol", proto)
                wrapped = _ProxiedHTTPScope(cast("HTTPScope", scope), client, scheme)
                await handler(wrapped, proto)  # type: ignore[arg-type]
            else:
                handler = cast("RSGIWebsocketHandler", handler)
                proto = cast("WebsocketProtocol", proto)
                # Map HTTP scheme to WS scheme for websocket
                ws_scheme = _WS_SCHEME_MAP.get(scheme, scheme)
                wrapped_ws = _ProxiedWebsocketScope(
                    cast("WebsocketScope", scope), client, ws_scheme
                )
                await handler(wrapped_ws, proto)  # type: ignore[arg-type]

        return proxied_handler

    return middleware
