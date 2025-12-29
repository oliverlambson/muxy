from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Literal

import pytest

from muxy.router import Router, path_params
from muxy.rsgi import HTTPProtocol, HTTPScope, HTTPStreamTransport, RSGIHandler


# --- Mock objects -------------------------------------------------------------
@dataclass
class MockHTTPScope:
    proto: Literal["http"] = "http"
    http_version: Literal["1", "1.1", "2"] = "1.1"
    rsgi_version: str = "1.0"
    server: str = "localhost"
    client: str = "127.0.0.1"
    scheme: str = "http"
    method: str = "GET"
    path: str = "/"
    query_string: str = ""
    headers: Mapping[str, str] = field(default_factory=dict)
    authority: str | None = None


class MockHTTPProtocol:
    async def __call__(self) -> bytes:
        raise NotImplementedError

    def __aiter__(self) -> bytes:
        raise NotImplementedError

    async def client_disconnect(self) -> None:
        raise NotImplementedError

    def response_empty(self, status: int, headers: list[tuple[str, str]]) -> None:
        raise NotImplementedError

    def response_str(
        self, status: int, headers: list[tuple[str, str]], body: str
    ) -> None:
        raise NotImplementedError

    def response_bytes(
        self, status: int, headers: list[tuple[str, str]], body: bytes
    ) -> None:
        raise NotImplementedError

    def response_file(
        self, status: int, headers: list[tuple[str, str]], file: str
    ) -> None:
        raise NotImplementedError

    def response_file_range(
        self,
        status: int,
        headers: list[tuple[str, str]],
        file: str,
        start: int,
        end: int,
    ) -> None:
        raise NotImplementedError

    def response_stream(
        self, status: int, headers: list[tuple[str, str]]
    ) -> HTTPStreamTransport:
        raise NotImplementedError


def mock_scope(path: str = "/", method: str = "GET") -> HTTPScope:
    return MockHTTPScope(path=path, method=method)


mock_proto = MockHTTPProtocol()


# --- HTTP method tests --------------------------------------------------------
@pytest.mark.parametrize(
    "method_name,http_method",
    [
        ("get", "GET"),
        ("post", "POST"),
        ("put", "PUT"),
        ("patch", "PATCH"),
        ("delete", "DELETE"),
        ("head", "HEAD"),
        ("options", "OPTIONS"),
        ("connect", "CONNECT"),
        ("trace", "TRACE"),
    ],
)
@pytest.mark.asyncio
async def test_router_http_methods(method_name: str, http_method: str) -> None:
    """Test each HTTP method convenience method registers and matches correctly."""
    called: list[str] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append(http_method)

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("404")

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("405")

    router = Router()
    getattr(router, method_name)("/test", handler)
    router.not_found(not_found)  # just to allow finalize()
    router.method_not_allowed(method_not_allowed)  # just to allow finalize()
    router.finalize()

    await router.__rsgi__(mock_scope("/test", http_method), mock_proto)
    assert called == [http_method]


@pytest.mark.asyncio
async def test_router_method_generic() -> None:
    """Test the generic method() registration."""
    called: list[str] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("handler")

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("404")

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("405")

    router = Router()
    router.method("PUT", "/test", handler)
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    await router.__rsgi__(mock_scope("/test", "PUT"), mock_proto)
    assert called == ["handler"]


# --- Path params tests --------------------------------------------------------
@pytest.mark.asyncio
async def test_path_params_wildcard() -> None:
    """Test wildcard path parameter extraction."""
    captured_params: list[dict[str, str]] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        captured_params.append(path_params.get())

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    router = Router()
    router.get("/user/{id}", handler)
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    await router.__rsgi__(mock_scope("/user/42", "GET"), mock_proto)
    assert captured_params == [{"id": "42"}]


@pytest.mark.asyncio
async def test_path_params_multiple() -> None:
    """Test multiple wildcard parameters."""
    captured_params: list[dict[str, str]] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        captured_params.append(path_params.get())

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    router = Router()
    router.get("/user/{id}/transaction/{tx}", handler)
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    await router.__rsgi__(mock_scope("/user/1/transaction/2", "GET"), mock_proto)
    assert captured_params == [{"id": "1", "tx": "2"}]


@pytest.mark.asyncio
async def test_path_params_catchall() -> None:
    """Test catch-all path parameter extraction."""
    captured_params: list[dict[str, str]] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        captured_params.append(path_params.get())

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    router = Router()
    router.get("/static/{path...}", handler)
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    await router.__rsgi__(mock_scope("/static/lib/datastar.min.js", "GET"), mock_proto)
    assert captured_params == [{"path": "lib/datastar.min.js"}]


# --- Error handler tests ------------------------------------------------------
@pytest.mark.asyncio
async def test_not_found_handler() -> None:
    """Test 404 handler is called for non-existent routes."""
    called: list[str] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("handler")

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("404")

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("405")

    router = Router()
    router.get("/exists", handler)
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    await router.__rsgi__(mock_scope("/does-not-exist", "GET"), mock_proto)
    assert called == ["404"]


@pytest.mark.asyncio
async def test_method_not_allowed_handler() -> None:
    """Test 405 handler is called for wrong HTTP method."""
    called: list[str] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("handler")

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("404")

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("405")

    router = Router()
    router.get("/test", handler)
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    await router.__rsgi__(mock_scope("/test", "POST"), mock_proto)
    assert called == ["405"]


# --- Error case tests (ValueError) --------------------------------------------
def test_finalize_without_not_found_raises() -> None:
    """Test finalize without not_found_handler raises ValueError."""

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    router = Router()
    router.get("/test", handler)
    router.method_not_allowed(method_not_allowed)

    with pytest.raises(ValueError, match="Router does not have not_found_handler"):
        router.finalize()


def test_finalize_without_method_not_allowed_raises() -> None:
    """Test finalize without method_not_allowed_handler raises ValueError."""

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    router = Router()
    router.get("/test", handler)
    router.not_found(not_found)

    with pytest.raises(
        ValueError, match="Router does not have method_not_allowed_handler"
    ):
        router.finalize()


def test_duplicate_not_found_raises() -> None:
    """Test setting not_found twice raises ValueError."""

    async def not_found1(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def not_found2(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    router = Router()
    router.not_found(not_found1)

    with pytest.raises(ValueError, match="not found handler is already set"):
        router.not_found(not_found2)


def test_duplicate_method_not_allowed_raises() -> None:
    """Test setting method_not_allowed twice raises ValueError."""

    async def method_not_allowed1(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def method_not_allowed2(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    router = Router()
    router.method_not_allowed(method_not_allowed1)

    with pytest.raises(ValueError, match="method not allowed handler is already set"):
        router.method_not_allowed(method_not_allowed2)


def test_mount_trailing_slash_raises() -> None:
    """Test mount with trailing slash raises ValueError."""
    router = Router()
    child = Router()

    with pytest.raises(ValueError, match="mount path cannot end in /"):
        router.mount("/api/", child)


# --- Middleware tests ---------------------------------------------------------
@pytest.mark.asyncio
async def test_middleware_use() -> None:
    """Test router.use() applies middleware to routes."""
    call_order: list[str] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        call_order.append("handler")

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    def middleware(f: RSGIHandler) -> RSGIHandler:
        call_order.append("middleware")
        return f

    router = Router()
    router.use(middleware)
    router.get("/test", handler)
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    await router.__rsgi__(mock_scope("/test", "GET"), mock_proto)
    assert call_order == ["middleware", "handler"]


@pytest.mark.asyncio
async def test_middleware_use_order_independent() -> None:
    """Test router.use() works the same regardless of when called relative to routes."""

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    def make_middleware(call_order: list[str]) -> Callable[[RSGIHandler], RSGIHandler]:
        def middleware(f: RSGIHandler) -> RSGIHandler:
            call_order.append("mw")
            return f

        return middleware

    # use() before routes
    call_order_before: list[str] = []
    router_before = Router()
    router_before.use(make_middleware(call_order_before))
    router_before.get("/test", handler)
    router_before.not_found(not_found)
    router_before.method_not_allowed(method_not_allowed)
    router_before.finalize()

    # use() after routes
    call_order_after: list[str] = []
    router_after = Router()
    router_after.get("/test", handler)
    router_after.use(make_middleware(call_order_after))
    router_after.not_found(not_found)
    router_after.method_not_allowed(method_not_allowed)
    router_after.finalize()

    await router_before.__rsgi__(mock_scope("/test", "GET"), mock_proto)
    await router_after.__rsgi__(mock_scope("/test", "GET"), mock_proto)

    assert call_order_before == call_order_after == ["mw"]


@pytest.mark.asyncio
async def test_middleware_order() -> None:
    """Test middleware is applied in correct order (first added = outermost)."""
    call_order: list[str] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        call_order.append("handler")

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    def middleware1(f: RSGIHandler) -> RSGIHandler:
        call_order.append("middleware1")
        return f

    def middleware2(f: RSGIHandler) -> RSGIHandler:
        call_order.append("middleware2")
        return f

    router = Router()
    router.get("/test", handler)
    router.use(middleware1, middleware2)
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    await router.__rsgi__(mock_scope("/test", "GET"), mock_proto)
    # Middleware is applied via reduce with reversed order, so:
    # - middleware2 wraps handler first (innermost)
    # - middleware1 wraps that result (outermost)
    # During wrapping, middleware2 is called first, then middleware1
    assert call_order == ["middleware2", "middleware1", "handler"]


@pytest.mark.asyncio
async def test_middleware_per_route() -> None:
    """Test middleware passed directly to route method."""
    call_order: list[str] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        call_order.append("handler")

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        pass

    def route_middleware(f: RSGIHandler) -> RSGIHandler:
        call_order.append("route_middleware")
        return f

    router = Router()
    router.get("/test", handler, middleware=(route_middleware,))
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    await router.__rsgi__(mock_scope("/test", "GET"), mock_proto)
    assert call_order == ["route_middleware", "handler"]


# --- Router composition tests -------------------------------------------------
@pytest.mark.asyncio
async def test_mount_router() -> None:
    """Test mounting a child router at a path."""
    called: list[str] = []

    async def child_handler(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("child")

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("404")

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("405")

    child = Router()
    child.get("/users", child_handler)

    parent = Router()
    parent.mount("/api", child)
    parent.not_found(not_found)
    parent.method_not_allowed(method_not_allowed)
    parent.finalize()

    await parent.__rsgi__(mock_scope("/api/users", "GET"), mock_proto)
    assert called == ["child"]


@pytest.mark.asyncio
async def test_mount_preserves_handlers() -> None:
    """Test both parent and child handlers work after mount."""
    called: list[str] = []

    async def parent_handler(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("parent")

    async def child_handler(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("child")

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("404")

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("405")

    child = Router()
    child.get("/users", child_handler)

    parent = Router()
    parent.get("/", parent_handler)
    parent.mount("/api", child)
    parent.not_found(not_found)
    parent.method_not_allowed(method_not_allowed)
    parent.finalize()

    await parent.__rsgi__(mock_scope("/", "GET"), mock_proto)
    assert called == ["parent"]

    called.clear()
    await parent.__rsgi__(mock_scope("/api/users", "GET"), mock_proto)
    assert called == ["child"]


# --- Edge case tests ----------------------------------------------------------
@pytest.mark.asyncio
async def test_handle_any_method() -> None:
    """Test router.handle() matches any HTTP method."""
    called: list[str] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append(s.method)

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("404")

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("405")

    router = Router()
    router.handle("/any", handler)
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
        called.clear()
        await router.__rsgi__(mock_scope("/any", method), mock_proto)
        assert called == [method]


@pytest.mark.asyncio
async def test_trailing_slash_404() -> None:
    """Test /admin/ is different from /admin (trailing slash = 404)."""
    called: list[str] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("handler")

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("404")

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("405")

    router = Router()
    router.get("/admin", handler)
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    # Without trailing slash - should match
    await router.__rsgi__(mock_scope("/admin", "GET"), mock_proto)
    assert called == ["handler"]

    # With trailing slash - should 404
    called.clear()
    await router.__rsgi__(mock_scope("/admin/", "GET"), mock_proto)
    assert called == ["404"]


@pytest.mark.asyncio
async def test_root_path() -> None:
    """Test / route works correctly."""
    called: list[str] = []

    async def handler(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("root")

    async def not_found(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("404")

    async def method_not_allowed(s: HTTPScope, p: HTTPProtocol) -> None:
        called.append("405")

    router = Router()
    router.get("/", handler)
    router.not_found(not_found)
    router.method_not_allowed(method_not_allowed)
    router.finalize()

    await router.__rsgi__(mock_scope("/", "GET"), mock_proto)
    assert called == ["root"]
