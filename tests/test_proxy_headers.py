from __future__ import annotations

from typing import cast

import pytest
from conftest import MockHTTPProtocol, mock_scope

from muxy.middleware.proxy_headers import proxy_headers
from muxy.rsgi import HTTPProtocol, HTTPScope, RSGIHTTPHandler


# --- helpers -----------------------------------------------------------------
async def _echo_handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
    """Handler that echoes client and scheme back as response body."""
    proto.response_str(
        200,
        [("content-type", "text/plain")],
        f"client={scope.client} scheme={scope.scheme}",
    )


def _make_middleware(
    *,
    trusted_proxies: frozenset[str] = frozenset({"*"}),
    num_proxies: int = 1,
) -> RSGIHTTPHandler:
    mw = proxy_headers(trusted_proxies=trusted_proxies, num_proxies=num_proxies)
    return cast("RSGIHTTPHandler", mw(_echo_handler))


# --- validation --------------------------------------------------------------
def test_num_proxies_must_be_positive() -> None:
    with pytest.raises(ValueError, match="num_proxies must be >= 1"):
        proxy_headers(trusted_proxies=frozenset({"*"}), num_proxies=0)


def test_trusted_proxies_must_not_be_empty() -> None:
    with pytest.raises(ValueError, match="trusted_proxies must not be empty"):
        proxy_headers(trusted_proxies=frozenset())


# --- trust gate --------------------------------------------------------------
@pytest.mark.asyncio
async def test_untrusted_proxy_passthrough() -> None:
    handler = _make_middleware(trusted_proxies=frozenset({"10.0.0.1"}))
    scope = mock_scope(
        client="192.168.1.1:54321",
        headers={"x-forwarded-for": "1.2.3.4", "x-forwarded-proto": "https"},
    )
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    assert proto.response_body == b"client=192.168.1.1:54321 scheme=http"


@pytest.mark.asyncio
async def test_trusted_proxy_overrides() -> None:
    """Trusted proxy check matches IP even when scope.client includes port."""
    handler = _make_middleware(trusted_proxies=frozenset({"10.0.0.1"}))
    scope = mock_scope(
        client="10.0.0.1:12345",
        headers={"x-forwarded-for": "1.2.3.4", "x-forwarded-proto": "https"},
    )
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    assert proto.response_body == b"client=1.2.3.4 scheme=https"


@pytest.mark.asyncio
async def test_trusted_proxy_bare_ip() -> None:
    """Trusted proxy check also works with bare IP (no port)."""
    handler = _make_middleware(trusted_proxies=frozenset({"10.0.0.1"}))
    scope = mock_scope(
        client="10.0.0.1",
        headers={"x-forwarded-for": "1.2.3.4", "x-forwarded-proto": "https"},
    )
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    assert proto.response_body == b"client=1.2.3.4 scheme=https"


@pytest.mark.asyncio
async def test_wildcard_trusts_all() -> None:
    handler = _make_middleware(trusted_proxies=frozenset({"*"}))
    scope = mock_scope(
        client="anything:9999",
        headers={"x-forwarded-for": "1.2.3.4", "x-forwarded-proto": "https"},
    )
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    assert proto.response_body == b"client=1.2.3.4 scheme=https"


# --- x-forwarded-for parsing ------------------------------------------------
@pytest.mark.asyncio
async def test_xff_single_ip() -> None:
    handler = _make_middleware(num_proxies=1)
    scope = mock_scope(headers={"x-forwarded-for": "203.0.113.50"})
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    assert proto.response_body == b"client=203.0.113.50 scheme=http"


@pytest.mark.asyncio
async def test_xff_chain_num_proxies_1() -> None:
    handler = _make_middleware(num_proxies=1)
    scope = mock_scope(headers={"x-forwarded-for": "203.0.113.50, 70.41.3.18"})
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    # num_proxies=1: take last entry (the one ALB appended)
    assert proto.response_body == b"client=70.41.3.18 scheme=http"


@pytest.mark.asyncio
async def test_xff_chain_num_proxies_2() -> None:
    handler = _make_middleware(num_proxies=2)
    scope = mock_scope(
        headers={"x-forwarded-for": "203.0.113.50, 70.41.3.18, 10.0.0.1"}
    )
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    # num_proxies=2: skip 2 from right, take 203.0.113.50
    assert proto.response_body == b"client=70.41.3.18 scheme=http"


@pytest.mark.asyncio
async def test_xff_fewer_entries_than_num_proxies() -> None:
    handler = _make_middleware(num_proxies=3)
    scope = mock_scope(headers={"x-forwarded-for": "203.0.113.50"})
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    # Falls back to leftmost entry
    assert proto.response_body == b"client=203.0.113.50 scheme=http"


@pytest.mark.asyncio
async def test_xff_whitespace_stripped() -> None:
    handler = _make_middleware(num_proxies=1)
    scope = mock_scope(headers={"x-forwarded-for": "  203.0.113.50  "})
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    assert proto.response_body == b"client=203.0.113.50 scheme=http"


@pytest.mark.asyncio
async def test_xff_empty_passthrough() -> None:
    handler = _make_middleware()
    scope = mock_scope(client="10.0.0.1:9999", headers={"x-forwarded-for": ""})
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    # Empty XFF → keep original client IP (port stripped)
    assert proto.response_body == b"client=10.0.0.1 scheme=http"


# --- x-forwarded-proto -------------------------------------------------------
@pytest.mark.asyncio
async def test_xfp_https() -> None:
    handler = _make_middleware()
    scope = mock_scope(headers={"x-forwarded-proto": "https"})
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    assert proto.response_body == b"client=127.0.0.1 scheme=https"


@pytest.mark.asyncio
async def test_xfp_only_no_xff() -> None:
    handler = _make_middleware()
    scope = mock_scope(client="10.0.0.1:9999", headers={"x-forwarded-proto": "https"})
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    # No XFF → client IP from scope (port stripped)
    assert proto.response_body == b"client=10.0.0.1 scheme=https"


@pytest.mark.asyncio
async def test_xfp_multi_hop_num_proxies_1() -> None:
    handler = _make_middleware(num_proxies=1)
    scope = mock_scope(headers={"x-forwarded-proto": "https, http"})
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    # num_proxies=1: take last entry (the proxy→backend hop)
    assert proto.response_body == b"client=127.0.0.1 scheme=http"


@pytest.mark.asyncio
async def test_xfp_multi_hop_num_proxies_2() -> None:
    handler = _make_middleware(num_proxies=2)
    scope = mock_scope(headers={"x-forwarded-proto": "https, http"})
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    # num_proxies=2: take second-to-last (the client→first proxy hop)
    assert proto.response_body == b"client=127.0.0.1 scheme=https"


# --- missing/no headers -----------------------------------------------------
@pytest.mark.asyncio
async def test_no_proxy_headers_passthrough() -> None:
    handler = _make_middleware()
    scope = mock_scope(client="10.0.0.1")
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    # No proxy headers at all → passthrough unchanged
    assert proto.response_body == b"client=10.0.0.1 scheme=http"


@pytest.mark.asyncio
async def test_xff_only_no_xfp() -> None:
    handler = _make_middleware()
    scope = mock_scope(headers={"x-forwarded-for": "1.2.3.4"})
    proto = MockHTTPProtocol()
    await handler(scope, proto)
    assert proto.response_body == b"client=1.2.3.4 scheme=http"


# --- scope wrapper delegation ------------------------------------------------
@pytest.mark.asyncio
async def test_delegated_attributes() -> None:
    """Wrapped scope delegates non-overridden attributes to original scope."""

    captured: dict[str, object] = {}

    async def capture_handler(scope: HTTPScope, proto: HTTPProtocol) -> None:
        captured["proto"] = scope.proto
        captured["method"] = scope.method
        captured["path"] = scope.path
        captured["headers"] = scope.headers
        captured["http_version"] = scope.http_version
        captured["client"] = scope.client
        captured["scheme"] = scope.scheme
        proto.response_empty(200, [])

    mw = proxy_headers(trusted_proxies=frozenset({"*"}))
    wrapped = cast("RSGIHTTPHandler", mw(capture_handler))

    scope = mock_scope(
        path="/test",
        method="POST",
        headers={"x-forwarded-for": "1.2.3.4", "x-forwarded-proto": "https"},
    )
    proto = MockHTTPProtocol()
    await wrapped(scope, proto)

    assert captured["proto"] == "http"
    assert captured["method"] == "POST"
    assert captured["path"] == "/test"
    assert captured["client"] == "1.2.3.4"
    assert captured["scheme"] == "https"


# --- websocket scheme mapping ------------------------------------------------


@pytest.mark.asyncio
async def test_websocket_scheme_mapped_https_to_wss() -> None:
    """X-Forwarded-Proto 'https' maps to 'wss' for websocket scopes."""
    captured: dict[str, object] = {}

    async def ws_handler(scope: object, proto: object) -> None:
        captured["scheme"] = scope.scheme  # type: ignore[attr-defined]
        captured["client"] = scope.client  # type: ignore[attr-defined]

    class FakeWsScope:
        proto = "ws"
        http_version = "1.1"
        rsgi_version = "1.0"
        server = "localhost"
        client = "10.0.0.1"
        scheme = "ws"
        method = "GET"
        path = "/"
        query_string = ""
        headers: dict[str, str] = {
            "x-forwarded-for": "1.2.3.4",
            "x-forwarded-proto": "https",
        }
        authority = None

    mw = proxy_headers(trusted_proxies=frozenset({"*"}))
    wrapped = mw(ws_handler)
    await wrapped(FakeWsScope(), None)  # type: ignore[arg-type]

    assert captured["scheme"] == "wss"
    assert captured["client"] == "1.2.3.4"


@pytest.mark.asyncio
async def test_websocket_scheme_mapped_http_to_ws() -> None:
    """X-Forwarded-Proto 'http' maps to 'ws' for websocket scopes."""
    captured: dict[str, object] = {}

    async def ws_handler(scope: object, proto: object) -> None:
        captured["scheme"] = scope.scheme  # type: ignore[attr-defined]

    class FakeWsScope:
        proto = "ws"
        http_version = "1.1"
        rsgi_version = "1.0"
        server = "localhost"
        client = "10.0.0.1"
        scheme = "ws"
        method = "GET"
        path = "/"
        query_string = ""
        headers: dict[str, str] = {"x-forwarded-proto": "http"}
        authority = None

    mw = proxy_headers(trusted_proxies=frozenset({"*"}))
    wrapped = mw(ws_handler)
    await wrapped(FakeWsScope(), None)  # type: ignore[arg-type]

    assert captured["scheme"] == "ws"
