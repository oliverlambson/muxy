"""Zero dependency router implementation with path param support.

Heavily inspired by go 1.22+ net/http's ServeMux
"""

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache, reduce

# --- IMPLEMENTATION -----------------------------------------------------------
type Handler = Callable[[dict[str, str]], None]  # placeholder for ASGI/RSGI app
type Middleware[T] = Callable[[T], T]


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


class FrozenDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hash = None

    def __hash__(self):
        if self._hash is None:
            self._hash = hash(frozenset(self.items()))
        return self._hash

    def _immutable(self, *args, **kwargs):
        msg = "FrozenDict is immutable"
        raise TypeError(msg)

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _immutable


@dataclass(slots=True, frozen=True)
class Node[T]:
    """Segment-based trie node"""

    not_found_handler: T
    method_not_allowed_handler: T
    handler: T | None = field(default=None)
    children: FrozenDict[str | LeafKey, Node[T]] = field(default_factory=FrozenDict)
    wildcard: WildCardNode[T] | None = field(default=None)
    catchall: CatchAllNode[T] | None = field(default=None)
    middleware: tuple[Middleware[T], ...] = field(default_factory=tuple)


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
) -> tuple[T, list[Middleware[T]], dict[str, str]]:
    """Traverses the tree to find the best match handler.

    Each path segment priority is: exact match > wildcard match  > catchall match
    If no matching node is found for the path, return not found handler
    If matching node for path does not support method, return method not supported handler
    """
    segments = path[1:].split("/")  # assumes leading "/"

    current = tree
    child = None
    params = {}
    middleware = [*current.middleware]
    for i, seg in enumerate(segments):
        child = current.children.get(seg)
        if child is not None:  # exact match
            middleware.extend(child.middleware)
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
        return current.not_found_handler, [], {}

    leaf = current.children.get(method)
    if leaf is None:
        leaf = current.children.get(LeafKey.ANY_HTTP)  # fallback to any method handler
        if leaf is None:
            return current.method_not_allowed_handler, [], params

    if leaf.handler is None:
        return current.not_found_handler, [], {}

    middleware.extend(leaf.middleware)
    return leaf.handler, middleware, params


# --- END IMPLEMENTATION -------------------------------------------------------


# handlers
admin_home_handler = lambda _: print("> admin home")  # noqa: E731
admin_user_rename_handler = lambda params: print(f"> admin user {params['id']} rename")  # noqa: E731
admin_user_transaction_view_handler = lambda params: print(  # noqa: E731
    f"> admin user {params['id']} transaction {params['tx']}"
)
static_handler = lambda params: print(f"> static {params['path']}")  # noqa: E731
home_handler = lambda _: print("> home")  # noqa: E731

# not found handlers
not_found_handler = lambda _: print("> 404")  # noqa: E731
admin_not_found_handler = lambda _: print("> admin 404")  # noqa: E731

# method not allowed handlers
method_not_allowed_handler = lambda _: print("> 405")  # noqa: E731
static_method_not_allowed_handler = lambda _: print("> static 405")  # noqa: E731


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
# - persist the error handlers at every node so that the lookup is faster at runtime
# - should probably persist the middleware at every node too, rather than constructing at
# runtime
tree: Node[Handler] = Node(
    children=FrozenDict(
        {
            "admin": Node(
                children=FrozenDict(
                    {
                        LeafKey.GET: Node(
                            handler=admin_home_handler,
                            not_found_handler=admin_not_found_handler,
                            method_not_allowed_handler=method_not_allowed_handler,
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
                                                                admin_user_rename_middleware,
                                                            ),
                                                        ),
                                                    }
                                                ),
                                                not_found_handler=admin_not_found_handler,
                                                method_not_allowed_handler=method_not_allowed_handler,
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
                                                                ),
                                                            }
                                                        ),
                                                        not_found_handler=admin_not_found_handler,
                                                        method_not_allowed_handler=method_not_allowed_handler,
                                                    ),
                                                ),
                                                not_found_handler=admin_not_found_handler,
                                                method_not_allowed_handler=method_not_allowed_handler,
                                            ),
                                        }
                                    ),
                                    not_found_handler=admin_not_found_handler,
                                    method_not_allowed_handler=method_not_allowed_handler,
                                ),
                            ),
                            not_found_handler=admin_not_found_handler,
                            method_not_allowed_handler=method_not_allowed_handler,
                            middleware=(admin_user_middleware,),
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
                                ),
                            }
                        ),
                        not_found_handler=not_found_handler,
                        method_not_allowed_handler=static_method_not_allowed_handler,
                    ),
                ),
                not_found_handler=not_found_handler,
                method_not_allowed_handler=static_method_not_allowed_handler,
            ),
            "": Node(  # "" is trailing slash (because result of "/foo/".split("/") == ["foo", ""])
                children=FrozenDict(
                    {
                        LeafKey.ANY_HTTP: Node(  # None is any method
                            handler=home_handler,
                            not_found_handler=not_found_handler,
                            method_not_allowed_handler=method_not_allowed_handler,
                        ),
                    }
                ),
                not_found_handler=not_found_handler,
                method_not_allowed_handler=method_not_allowed_handler,
            ),
        }
    ),
    not_found_handler=not_found_handler,
    method_not_allowed_handler=method_not_allowed_handler,
)


def main() -> None:
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
        handler, middleware, params = find_handler(path, method, tree)
        end = time.perf_counter()

        print(f"lookup took {end - start:.2E} seconds", file=sys.stderr, flush=True)

        assert handler is expected_handler, f"{handler=} is {expected_handler=}"
        assert middleware == list(expected_middleware), (
            f"{middleware=} == {expected_middleware=}"
        )

        # apply middleware stack
        wrapped_handler = reduce(lambda h, m: m(h), reversed(middleware), handler)
        # call handler
        wrapped_handler(params)


if __name__ == "__main__":
    main()
