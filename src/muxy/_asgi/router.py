"""HTTP+Websocket router/multiplexer implementation.

Inspired by go-chi/mux's Mux
"""

from collections.abc import Callable
from functools import reduce
from typing import Literal, overload

from muxy.tree import (
    LeafKey,
    Node,
    add_route,
    finalize_tree,
    find_handler,
    mount_tree,
    path_params,
)

from .types import (
    ASGIHandler,
    ASGIHTTPHandler,
    ASGIWebsocketHandler,
    HTTPReceive,
    HTTPScope,
    HTTPSend,
    WebsocketReceive,
    WebsocketScope,
    WebsocketSend,
)

# --- IMPLEMENTATION -----------------------------------------------------------
type Middleware[T] = Callable[[T], T]
type HTTPMethod = Literal[
    "CONNECT", "DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT", "TRACE"
]
type WebsocketMethod = Literal["WEBSOCKET"]


class Router:
    __slots__ = ("_tree",)
    _tree: Node[ASGIHandler]

    def __init__(
        self,
        *,
        not_found_handler: ASGIHTTPHandler | None = None,
        method_not_allowed_handler: ASGIHTTPHandler | None = None,
    ) -> None:
        self._tree = Node(
            not_found_handler=not_found_handler,
            method_not_allowed_handler=method_not_allowed_handler,
        )

    @overload
    async def __call__(
        self, scope: HTTPScope, receive: HTTPReceive, send: HTTPSend
    ) -> None: ...
    @overload
    async def __call__(
        self, scope: WebsocketScope, receive: WebsocketReceive, send: WebsocketSend
    ) -> None: ...
    async def __call__(
        self,
        scope: HTTPScope | WebsocketScope,
        receive: HTTPReceive | WebsocketReceive,
        send: HTTPSend | WebsocketSend,
    ) -> None:
        if scope["type"] == "lifespan":
            pass  # TODO: implement lifespan handler
        else:
            handler, params = self._handler(
                LeafKey(scope["method"].upper())
                if scope["type"] == "http"
                else LeafKey.WEBSOCKET,
                scope.get("path", ""),
            )
            with path_params.set(params):
                await handler(scope, receive, send)  # ty: ignore[invalid-argument-type]  - is correct just want to avoid casting

    @overload
    def _handler(
        self,
        method: Literal[
            LeafKey.CONNECT,
            LeafKey.DELETE,
            LeafKey.GET,
            LeafKey.HEAD,
            LeafKey.OPTIONS,
            LeafKey.PATCH,
            LeafKey.POST,
            LeafKey.PUT,
            LeafKey.TRACE,
            LeafKey.ANY_HTTP,
        ],
        path: str,
    ) -> tuple[ASGIHTTPHandler, dict[str, str]]: ...
    @overload
    def _handler(
        self, method: Literal[LeafKey.WEBSOCKET], path: str
    ) -> tuple[ASGIWebsocketHandler, dict[str, str]]: ...
    def _handler(
        self, method: LeafKey, path: str
    ) -> tuple[ASGIHandler, dict[str, str]]:
        """Returns the handler to use for the request."""
        # path is unescaped by the rsgi server, so we don't need to use urllib.parse.(un)quote
        handler, middleware, params = find_handler(path, method, self._tree)
        wrapped_handler = reduce(lambda h, m: m(h), reversed(middleware), handler)
        return wrapped_handler, params

    def handle(
        self,
        path: str,
        handler: ASGIHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers handler in tree at path for any http method or websocket, with optional middleware.

        This can be useful if you have a fully independent ASGI app you want to mount.
        """
        self._tree = add_route(self._tree, LeafKey.ANY_HTTP, path, handler, middleware)

    @overload
    def method(
        self,
        method: HTTPMethod | None,
        path: str,
        handler: ASGIHTTPHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None: ...
    @overload
    def method(
        self,
        method: WebsocketMethod,
        path: str,
        handler: ASGIWebsocketHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None: ...
    def method(
        self,
        method: HTTPMethod | WebsocketMethod | None,
        path: str,
        handler: ASGIHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers handler in tree at path for method, with optional middleware."""
        self._tree = add_route(
            self._tree,
            LeafKey(method) if method is not None else LeafKey.ANY_HTTP,
            path,
            handler,
            middleware,
        )

    def connect(
        self,
        path: str,
        handler: ASGIHTTPHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers http handler in tree at path for CONNECT, with optional middleware."""
        self._tree = add_route(self._tree, LeafKey.CONNECT, path, handler, middleware)

    def delete(
        self,
        path: str,
        handler: ASGIHTTPHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers http handler in tree at path for DELETE, with optional middleware."""
        self._tree = add_route(self._tree, LeafKey.DELETE, path, handler, middleware)

    def get(
        self,
        path: str,
        handler: ASGIHTTPHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers http handler in tree at path for GET, with optional middleware."""
        self._tree = add_route(self._tree, LeafKey.GET, path, handler, middleware)

    def head(
        self,
        path: str,
        handler: ASGIHTTPHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers http handler in tree at path for HEAD, with optional middleware."""
        self._tree = add_route(self._tree, LeafKey.HEAD, path, handler, middleware)

    def options(
        self,
        path: str,
        handler: ASGIHTTPHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers http handler in tree at path for OPTIONS, with optional middleware."""
        self._tree = add_route(self._tree, LeafKey.OPTIONS, path, handler, middleware)

    def patch(
        self,
        path: str,
        handler: ASGIHTTPHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers http handler in tree at path for PATCH, with optional middleware."""
        self._tree = add_route(self._tree, LeafKey.PATCH, path, handler, middleware)

    def post(
        self,
        path: str,
        handler: ASGIHTTPHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers http handler in tree at path for POST, with optional middleware."""
        self._tree = add_route(self._tree, LeafKey.POST, path, handler, middleware)

    def put(
        self,
        path: str,
        handler: ASGIHTTPHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers http handler in tree at path for PUT, with optional middleware."""
        self._tree = add_route(self._tree, LeafKey.PUT, path, handler, middleware)

    def trace(
        self,
        path: str,
        handler: ASGIHTTPHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers http handler in tree at path for TRACE, with optional middleware."""
        self._tree = add_route(self._tree, LeafKey.TRACE, path, handler, middleware)

    def websocket(
        self,
        path: str,
        handler: ASGIWebsocketHandler,
        middleware: tuple[Middleware[ASGIHandler], ...] = (),
    ) -> None:
        """Registers websocket handler in tree at path, with optional middleware."""
        self._tree = add_route(self._tree, LeafKey.WEBSOCKET, path, handler, middleware)

    def not_found(self, handler: ASGIHTTPHandler) -> None:
        """Registers http handler for paths that can't be found."""
        if self._tree.not_found_handler is not None:
            msg = "not found handler is already set"
            raise ValueError(msg)
        self._tree = self._tree.update(not_found_handler=handler)

    def method_not_allowed(self, handler: ASGIHTTPHandler) -> None:
        """Registers http handler for paths where the method is unresolved."""
        if self._tree.method_not_allowed_handler is not None:
            msg = "method not allowed handler is already set"
            raise ValueError(msg)
        self._tree = self._tree.update(method_not_allowed_handler=handler)

    def use(self, *middleware: Middleware[ASGIHandler]) -> None:
        """Adds middleware to tree."""
        self._tree = self._tree.update(middleware=self._tree.middleware + middleware)

    def mount(self, path: str, router: Router) -> None:
        """Merges in another router at path."""
        if path.endswith("/"):
            msg = "mount path cannot end in /"
            raise ValueError(msg)
        self._tree = mount_tree(path, self._tree, router._tree)

    def finalize(self) -> None:
        """
        Cascades not_found_handler, method_not_allowed_handler, and middleware down
        through the routing tree.
        """
        if self._tree.not_found_handler is None:
            msg = "Router does not have not_found_handler"
            raise ValueError(msg)
        if self._tree.method_not_allowed_handler is None:
            msg = "Router does not have method_not_allowed_handler"
            raise ValueError(msg)
        self._tree = finalize_tree(
            self._tree,
            self._tree.not_found_handler,
            self._tree.method_not_allowed_handler,
            (),
        )
