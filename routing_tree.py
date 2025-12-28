"""Zero dependency router implementation with path param support.

Heavily inspired by go 1.22+ net/http's ServeMux
"""

import asyncio
import sys
import time
from collections.abc import Callable, Mapping
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache, reduce
from typing import Literal, Never, overload

from rsgisrv.rsgi.proto import (
    HTTPProtocol,
    HTTPScope,
    HTTPStreamTransport,
    RSGIHandler,
    RSGIHTTPHandler,
    RSGIWebsocketHandler,
    Scope,
    WebsocketProtocol,
    WebsocketScope,
)

# --- IMPLEMENTATION -----------------------------------------------------------
type Middleware[T] = Callable[[T], T]
type HTTPMethod = Literal[
    "CONNECT", "DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT", "TRACE"
]
type WebsocketMethod = Literal["WEBSOCKET"]


path_params: ContextVar[dict[str, str]] = ContextVar("path_params")


class Router:
    __slots__ = ("_tree",)
    _tree: Node[RSGIHandler]

    def __init__(self) -> None:
        self._tree = Node()

    @overload
    async def __rsgi__(self, scope: HTTPScope, proto: HTTPProtocol) -> None: ...
    @overload
    async def __rsgi__(
        self, scope: WebsocketScope, proto: WebsocketProtocol
    ) -> None: ...
    async def __rsgi__(
        self, scope: Scope, proto: HTTPProtocol | WebsocketProtocol
    ) -> None:
        handler, params = self._handler(
            LeafKey(scope.method.upper())
            if scope.proto == "http"
            else LeafKey.WEBSOCKET,
            scope.path,
        )
        with path_params.set(params):
            await handler(scope, proto)  # ty: ignore[invalid-argument-type]  -- handler will be correct type for scope.proto

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
    ) -> tuple[RSGIHTTPHandler, dict[str, str]]: ...
    @overload
    def _handler(
        self, method: Literal[LeafKey.WEBSOCKET], path: str
    ) -> tuple[RSGIWebsocketHandler, dict[str, str]]: ...
    def _handler(
        self, method: LeafKey, path: str
    ) -> tuple[RSGIHandler, dict[str, str]]:
        """Returns the handler to use for the request."""
        # path is unescaped by the rsgi server, so we don't need to use urllib.parse.(un)quote
        handler, middleware, params = find_handler(path, method, self._tree)
        wrapped_handler = reduce(lambda h, m: m(h), reversed(middleware), handler)
        return wrapped_handler, params

    @overload
    def handle(
        self,
        method: HTTPMethod,
        path: str,
        handler: RSGIHTTPHandler,
        middleware: tuple[Middleware[RSGIHandler], ...] = (),
    ) -> None: ...
    @overload
    def handle(
        self,
        method: WebsocketMethod,
        path: str,
        handler: RSGIWebsocketHandler,
        middleware: tuple[Middleware[RSGIHandler], ...] = (),
    ) -> None: ...
    def handle(
        self,
        method: HTTPMethod | WebsocketMethod,
        path: str,
        handler: RSGIHandler,
        middleware: tuple[Middleware[RSGIHandler], ...] = (),
    ) -> None:
        """Registers handler in tree at path for method, with optional middleware."""
        self._tree = add_route(self._tree, LeafKey(method), path, handler, middleware)

    def use(self, path: str, *middleware: Middleware[RSGIHandler]) -> None:
        """Adds middleware to tree at current node."""
        raise NotImplementedError

    def route(self, path: str, child: Node[RSGIHandler]) -> None:
        """Merges child tree into current tree at path."""
        raise NotImplementedError


class LeafKey(Enum):
    """Valid keys for leaf nodes: HTTP methods or websocket.

    Methods from the following RFCs are all observed:

        * RFC 9110: HTTP Semantics, obsoletes 7231, which obsoleted 2616
        * RFC 5789: PATCH Method for HTTP

    ANY_HTTP represents any http method
    WEBSOCKET matches a websocket connection
    """

    CONNECT = "CONNECT"  # Establish a connection to the server.
    DELETE = "DELETE"  # Remove the target.
    GET = "GET"  # Retrieve the target.
    HEAD = "HEAD"  # Same as GET, but only retrieve status line and header section.
    OPTIONS = "OPTIONS"  # Describe the communication options for the target.
    PATCH = "PATCH"  # Apply partial modifications to a target.
    POST = "POST"  # Perform target-specific processing with the request payload.
    PUT = "PUT"  # Replace the target with the request payload.
    TRACE = "TRACE"  # Perform a message loop-back test along the path to the target.

    ANY_HTTP = "ANY_HTTP"  # Any HTTP method.
    WEBSOCKET = "WEBSOCKET"  # Websocket connection. (The HTTP connection is upgraded before it's passed to the RSGI app.)

    def __repr__(self) -> str:
        return str(self.value)


class FrozenDict[K, V](dict[K, V]):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._hash: int | None = None

    def __hash__(self) -> int:
        if self._hash is None:
            self._hash = hash(frozenset(self.items()))
        return self._hash

    def _immutable(self, *args, **kwargs) -> Never:
        msg = "FrozenDict is immutable"
        raise TypeError(msg)

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _immutable


@dataclass(slots=True, frozen=True)
class Node[T]:
    """Segment-based trie node"""

    handler: T | None = field(default=None)
    middleware: tuple[Middleware[T], ...] = field(default=())
    children: FrozenDict[str | LeafKey, Node[T]] = field(default_factory=FrozenDict)
    wildcard: WildCardNode[T] | None = field(default=None)
    catchall: CatchAllNode[T] | None = field(default=None)
    not_found_handler: T | None = None
    method_not_allowed_handler: T | None = None


@dataclass(slots=True, frozen=True)
class WildCardNode[T]:
    name: str
    child: Node[T]


@dataclass(slots=True, frozen=True)
class CatchAllNode[T]:
    name: str
    child: Node[T]


@lru_cache(maxsize=1024)
def find_handler[T](
    path: str,
    method: LeafKey,
    tree: Node[T],
) -> tuple[T, tuple[Middleware[T], ...], dict[str, str]]:
    """Traverses the tree to find the best match handler.

    Each path segment priority is: exact match > wildcard match  > catchall match
    If no matching node is found for the path, return not found handler
    If matching node for path does not support method, return method not supported handler
    """
    segments = path[1:].split("/")  # assumes leading "/"

    current = tree
    child = None
    params = {}
    for i, seg in enumerate(segments):
        child = current.children.get(seg)
        if child is not None:  # exact match
            current = child  # traverse to child
            continue
        if current.wildcard is not None:  # fallback to wildcard match
            params[current.wildcard.name] = seg
            current = current.wildcard.child  # traverse to wildcard child
            continue
        if current.catchall is not None:  # fallback to catchall match
            params[current.catchall.name] = "/".join(segments[i:])
            current = current.catchall.child  # traverse to catchall child
            break
        # no match
        if current.not_found_handler is None:
            msg = "No not found handler set"
            raise ValueError(msg)
        return current.not_found_handler, (), {}

    leaf = current.children.get(method)
    if leaf is None:
        leaf = current.children.get(LeafKey.ANY_HTTP)  # fallback to any method handler
        if leaf is None:
            if current.method_not_allowed_handler is None:
                msg = "No method not allowed handler set"
                raise ValueError(msg)
            return current.method_not_allowed_handler, (), params

    if leaf.handler is None:
        if current.not_found_handler is None:
            msg = "No not found handler set"
            raise ValueError(msg)
        return current.not_found_handler, (), {}

    return leaf.handler, leaf.middleware, params


def add_route[T](
    tree: Node[T],
    method: LeafKey,
    path: str,
    handler: T,
    middleware: tuple[Middleware[T], ...] = (),
) -> Node[T]:
    """add route to tree for handler on method/path with optional middleware"""
    new_tree = construct_tree(method, path, handler, middleware)
    return merge_trees(tree, new_tree)


def construct_tree[T](
    method: LeafKey,
    path: str,
    handler: T,
    middleware: tuple[Middleware[T], ...] = (),
) -> Node[T]:
    """construct tree for handler on method/path with optional middleware"""
    if not path.startswith("/"):
        msg = f"path must start with '/', provided {path=}"
        raise ValueError(msg)
    segments = path[1:].split("/")

    # construct tree
    leaf = Node(
        middleware=middleware,
        handler=handler,
    )
    child: Node[T] = Node(
        children=FrozenDict({method: leaf}),
    )
    for seg in reversed(segments):
        if seg.startswith("{") and seg.endswith("...}"):
            name = seg[1:-4]
            child = Node(
                catchall=CatchAllNode(
                    name=name,
                    child=child,
                ),
            )
        elif seg.startswith("{") and seg.endswith("}"):
            name = seg[1:-1]
            child = Node(
                wildcard=WildCardNode(
                    name=name,
                    child=child,
                ),
            )
        else:
            child = Node(
                children=FrozenDict({seg: child}),
            )

    return child


def merge_trees[T](tree1: Node[T], tree2: Node[T]) -> Node[T]:
    """merge tree1 and tree2, error on conflict"""
    if (
        tree1.handler is not None
        and tree2.handler is not None
        and tree1.handler is not tree2.handler
    ):
        msg = "nodes have conflicting handlers"
        raise ValueError(msg)
    handler = tree1.handler or tree2.handler
    if (
        tree1.not_found_handler is not None
        and tree2.not_found_handler is not None
        and tree1.not_found_handler is not tree2.not_found_handler
    ):
        msg = "nodes have conflicting not found handlers"
        raise ValueError(msg)
    not_found_handler = tree1.not_found_handler or tree2.not_found_handler
    if (
        tree1.method_not_allowed_handler is not None
        and tree2.method_not_allowed_handler is not None
        and tree1.method_not_allowed_handler is not tree2.method_not_allowed_handler
    ):
        msg = "nodes have conflicting method not allowed handlers"
        raise ValueError(msg)
    method_not_allowed_handler = (
        tree1.method_not_allowed_handler or tree2.method_not_allowed_handler
    )

    if tree1.middleware != tree2.middleware:
        msg = "nodes have conflicting middleware"
        raise ValueError(msg)
    middleware = tree1.middleware or tree2.middleware

    if tree1.wildcard is not None and tree2.wildcard and tree2.wildcard is not None:
        if tree1.wildcard.name != tree2.wildcard.name:
            msg = "nodes have conflicting wildcards"
            raise ValueError(msg)
        wildcard: WildCardNode[T] | None = WildCardNode(
            name=tree1.wildcard.name,
            child=merge_trees(tree1.wildcard.child, tree2.wildcard.child),
        )
    else:
        wildcard = tree1.wildcard or tree2.wildcard

    if tree1.catchall is not None and tree2.catchall is not None:
        if tree1.catchall.name != tree2.catchall.name:
            msg = "nodes have conclicting catchalls"
            raise ValueError(msg)
        catchall: CatchAllNode[T] | None = CatchAllNode(
            name=tree1.catchall.name,
            child=merge_trees(tree1.catchall.child, tree2.catchall.child),
        )
    else:
        catchall = tree1.catchall or tree2.catchall

    tree1_keys = set(tree1.children.keys())
    tree2_keys = set(tree2.children.keys())
    unique_tree1_keys = tree1_keys.difference(tree2_keys)
    unique_tree2_keys = tree2_keys.difference(tree1_keys)
    common_keys = tree1_keys.intersection(tree2_keys)
    children: FrozenDict[str | LeafKey, Node[T]] = FrozenDict(
        {k: tree1.children[k] for k in unique_tree1_keys}
        | {k: tree2.children[k] for k in unique_tree2_keys}
        | {k: merge_trees(tree1.children[k], tree2.children[k]) for k in common_keys}
    )

    return Node(
        handler=handler,
        middleware=middleware,
        children=children,
        wildcard=wildcard,
        catchall=catchall,
        not_found_handler=not_found_handler,
        method_not_allowed_handler=method_not_allowed_handler,
    )


def finalize_tree[T](tree: Node[T]) -> Node[T]:
    """
    cascade not_found_handler, method_not_allowed_handler, and middleware down
    through tree
    """
    raise NotImplementedError


# --- END IMPLEMENTATION -------------------------------------------------------


# handlers
async def admin_home_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> admin home")


async def admin_user_rename_handler(s: Scope, p: HTTPProtocol) -> None:
    print(f"> admin user {path_params.get()['id']} rename")


async def admin_user_transaction_view_handler(s: Scope, p: HTTPProtocol) -> None:
    print(
        f"> admin user {path_params.get()['id']} transaction {path_params.get()['tx']}"
    )


async def static_handler(s: Scope, p: HTTPProtocol) -> None:
    print(f"> static {path_params.get()['path']}")


async def home_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> home")


# not found handlers
async def not_found_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> 404")


async def admin_not_found_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> admin 404")


# method not allowed handlers
async def method_not_allowed_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> 405")


async def static_method_not_allowed_handler(s: Scope, p: HTTPProtocol) -> None:
    print("> static 405")


# middleware
def admin_middleware[T](f: T) -> T:
    print(">> admin middleware")
    return f


def admin_user_middleware[T](f: T) -> T:
    print(">> admin user middleware")
    return f


def admin_user_rename_middleware[T](f: T) -> T:
    print(">> admin user rename middleware")
    return f


"""
handlers:
POST    /admin/user/{id}/rename             admin_user_rename_handler
GET     /admin/user/{id}/transaction/{tx}   admin_user_transaction_view_handler
GET     /admin                              admin_home_handler
GET     /static/{path...}                   static_handler
<any>   /                                   home_handler

not found handlers:
<fallback>  not_found_handler
/admin      admin_not_found_handler

method not allowed handlers:
<fallback>  method_not_allowed_handler
/static     static_method_not_allowed_handler

middleware:
/admin                          admin_middleware
/admin/user                     admin_user_middleware
POST /admin/user/{id}/rename    admin_user_rename_middleware
"""
# manually create the tree (we'll make nicer ways to construct this later)
# - persist the error handlers and middleware at every node so that the lookup is faster at runtime
manual_tree = Node(
    children=FrozenDict(
        {
            "admin": Node(
                children=FrozenDict(
                    {
                        LeafKey.GET: Node(
                            handler=admin_home_handler,
                            not_found_handler=admin_not_found_handler,
                            method_not_allowed_handler=method_not_allowed_handler,
                            middleware=(admin_middleware,),
                        ),
                        "user": Node(
                            wildcard=WildCardNode(
                                name="id",
                                child=Node(
                                    children=FrozenDict(
                                        {
                                            "rename": Node(
                                                children=FrozenDict(
                                                    {
                                                        LeafKey.POST: Node(
                                                            handler=admin_user_rename_handler,
                                                            not_found_handler=admin_not_found_handler,
                                                            method_not_allowed_handler=method_not_allowed_handler,
                                                            middleware=(
                                                                admin_middleware,
                                                                admin_user_middleware,
                                                                admin_user_rename_middleware,
                                                            ),
                                                        ),
                                                    }
                                                ),
                                                not_found_handler=admin_not_found_handler,
                                                method_not_allowed_handler=method_not_allowed_handler,
                                                middleware=(
                                                    admin_middleware,
                                                    admin_user_middleware,
                                                ),
                                            ),
                                            "transaction": Node(
                                                wildcard=WildCardNode(
                                                    name="tx",
                                                    child=Node(
                                                        children=FrozenDict(
                                                            {
                                                                LeafKey.GET: Node(
                                                                    handler=admin_user_transaction_view_handler,
                                                                    not_found_handler=admin_not_found_handler,
                                                                    method_not_allowed_handler=method_not_allowed_handler,
                                                                    middleware=(
                                                                        admin_middleware,
                                                                        admin_user_middleware,
                                                                    ),
                                                                ),
                                                            }
                                                        ),
                                                        not_found_handler=admin_not_found_handler,
                                                        method_not_allowed_handler=method_not_allowed_handler,
                                                        middleware=(
                                                            admin_middleware,
                                                            admin_user_middleware,
                                                        ),
                                                    ),
                                                ),
                                                not_found_handler=admin_not_found_handler,
                                                method_not_allowed_handler=method_not_allowed_handler,
                                                middleware=(
                                                    admin_middleware,
                                                    admin_user_middleware,
                                                ),
                                            ),
                                        }
                                    ),
                                    not_found_handler=admin_not_found_handler,
                                    method_not_allowed_handler=method_not_allowed_handler,
                                    middleware=(
                                        admin_middleware,
                                        admin_user_middleware,
                                    ),
                                ),
                            ),
                            not_found_handler=admin_not_found_handler,
                            method_not_allowed_handler=method_not_allowed_handler,
                            middleware=(
                                admin_middleware,
                                admin_user_middleware,
                            ),
                        ),
                    }
                ),
                not_found_handler=admin_not_found_handler,
                method_not_allowed_handler=method_not_allowed_handler,
                middleware=(admin_middleware,),
            ),
            "static": Node(
                catchall=CatchAllNode(
                    name="path",
                    child=Node(
                        children=FrozenDict(
                            {
                                LeafKey.GET: Node(
                                    handler=static_handler,
                                    not_found_handler=not_found_handler,
                                    method_not_allowed_handler=static_method_not_allowed_handler,
                                    middleware=(),
                                ),
                            }
                        ),
                        not_found_handler=not_found_handler,
                        method_not_allowed_handler=static_method_not_allowed_handler,
                        middleware=(),
                    ),
                ),
                not_found_handler=not_found_handler,
                method_not_allowed_handler=static_method_not_allowed_handler,
                middleware=(),
            ),
            "": Node(  # "" is trailing slash (because result of "/foo/".split("/") == ["foo", ""])
                children=FrozenDict(
                    {
                        LeafKey.ANY_HTTP: Node(  # None is any method
                            handler=home_handler,
                            not_found_handler=not_found_handler,
                            method_not_allowed_handler=method_not_allowed_handler,
                            middleware=(),
                        ),
                    }
                ),
                not_found_handler=not_found_handler,
                method_not_allowed_handler=method_not_allowed_handler,
                middleware=(),
            ),
        }
    ),
    not_found_handler=not_found_handler,
    method_not_allowed_handler=method_not_allowed_handler,
    middleware=(),
)


@dataclass
class TestHttpScope:
    proto: Literal["http"]
    http_version: Literal["1", "1.1", "2"]
    rsgi_version: str
    server: str
    client: str
    scheme: str
    method: str
    path: str
    query_string: str
    headers: Mapping[str, str]
    authority: str | None


def _test_scope(path: str, method: str) -> HTTPScope:
    return TestHttpScope(
        proto="http",
        http_version="1.1",
        rsgi_version="",
        server="",
        client="",
        scheme="",
        method=method,
        path=path,
        query_string="",
        headers={},
        authority=None,
    )


class TestHTTPProto:
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


_test_proto = TestHTTPProto()


async def _test_user_id_handler(s: Scope, p: HTTPProtocol) -> None:
    print(f"hi user {path_params.get()['id']}")


async def _test_user_profile_handler(s: Scope, p: HTTPProtocol) -> None:
    print(f"user profile: {path_params.get()['id']}")


async def main() -> None:
    from pprint import pprint

    # test tree construction
    tree = construct_tree(LeafKey.GET, "/user/{id}/profile", _test_user_profile_handler)
    pprint(tree)
    handler, middleware, params = find_handler("/user/42/profile", LeafKey.GET, tree)
    wrapped_handler = reduce(lambda h, m: m(h), reversed(middleware), handler)
    with path_params.set(params):
        await wrapped_handler(_test_scope("/user/42/profile", "GET"), _test_proto)
    del tree, handler, middleware, params, wrapped_handler
    print("-" * 80)
    print()

    # test tree merging
    tree1 = construct_tree(LeafKey.GET, "/user/{id}", _test_user_id_handler)
    tree2 = construct_tree(
        LeafKey.GET, "/user/{id}/profile", _test_user_profile_handler
    )
    tree = merge_trees(tree1, tree2)
    pprint(tree)
    handler, middleware, params = find_handler("/user/42", LeafKey.GET, tree)
    wrapped_handler = reduce(lambda h, m: m(h), reversed(middleware), handler)
    with path_params.set(params):
        await wrapped_handler(_test_scope("/user/42", "GET"), _test_proto)
    handler, middleware, params = find_handler("/user/42/profile", LeafKey.GET, tree)
    wrapped_handler = reduce(lambda h, m: m(h), reversed(middleware), handler)
    with path_params.set(params):
        await wrapped_handler(_test_scope("/user/42/profile", "GET"), _test_proto)
    del tree, tree1, tree2, handler, middleware, params, wrapped_handler
    print("-" * 80)
    print()

    # test add route
    tree = construct_tree(LeafKey.GET, "/user/{id}", _test_user_id_handler)
    tree = add_route(
        tree, LeafKey.GET, "/user/{id}/profile", _test_user_profile_handler
    )
    pprint(tree)
    handler, middleware, params = find_handler("/user/42", LeafKey.GET, tree)
    wrapped_handler = reduce(lambda h, m: m(h), reversed(middleware), handler)
    with path_params.set(params):
        await wrapped_handler(_test_scope("/user/42", "GET"), _test_proto)
    handler, middleware, params = find_handler("/user/42/profile", LeafKey.GET, tree)
    wrapped_handler = reduce(lambda h, m: m(h), reversed(middleware), handler)
    with path_params.set(params):
        await wrapped_handler(_test_scope("/user/42/profile", "GET"), _test_proto)
    del tree, handler, middleware, params, wrapped_handler
    print("-" * 80)
    print()

    # test routing
    tests = [
        # simple, any method
        ("/", LeafKey.PATCH, home_handler, ()),
        # simple, with method
        ("/admin", LeafKey.GET, admin_home_handler, (admin_middleware,)),
        # 404
        ("/some/nonexistent/route", LeafKey.GET, not_found_handler, ()),
        # 404 on trailing slash
        ("/admin/", LeafKey.GET, admin_not_found_handler, ()),
        # 405
        ("/admin", LeafKey.DELETE, method_not_allowed_handler, ()),
        # 405
        (
            "/static/bleugh.txt",
            LeafKey.OPTIONS,
            static_method_not_allowed_handler,
            (),
        ),
        # wildcard param
        (
            "/admin/user/1/rename",
            LeafKey.POST,
            admin_user_rename_handler,
            (admin_middleware, admin_user_middleware, admin_user_rename_middleware),
        ),
        (
            "/admin/user/1/rename",
            LeafKey.POST,
            admin_user_rename_handler,
            (admin_middleware, admin_user_middleware, admin_user_rename_middleware),
        ),
        # multiple wildcard params
        (
            "/admin/user/1/transaction/2",
            LeafKey.GET,
            admin_user_transaction_view_handler,
            (admin_middleware, admin_user_middleware),
        ),
        # catchall param
        ("/static/lib/datastar.min.js", LeafKey.GET, static_handler, ()),
    ]

    for path, method, expected_handler, expected_middleware in tests:
        print(method, path, file=sys.stderr, flush=True, end=" ")

        start = time.perf_counter()
        handler, middleware, params = find_handler(path, method, manual_tree)
        end = time.perf_counter()

        print(f"lookup took {end - start:.2E} seconds", file=sys.stderr, flush=True)

        assert handler is expected_handler, f"{handler=} is {expected_handler=}"
        assert middleware == expected_middleware, (
            f"{middleware=} == {expected_middleware=}"
        )

        # apply middleware stack
        wrapped_handler = reduce(lambda h, m: m(h), reversed(middleware), handler)
        # call handler
        with path_params.set(params):
            await wrapped_handler(_test_scope(path, method.value), _test_proto)

    # test router
    router = Router()
    router.handle("GET", "/user/{id}", _test_user_id_handler)
    router.handle("GET", "/user/{id}/profile", _test_user_profile_handler)
    await router.__rsgi__(_test_scope("/user/42", "GET"), _test_proto)
    await router.__rsgi__(_test_scope("/user/42/profile", "GET"), _test_proto)


if __name__ == "__main__":
    asyncio.run(main())
