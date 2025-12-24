"""Zero dependency router implementation with path params

Heavily inspired by go 1.22+ net/http's ServeMux
"""

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from http import HTTPMethod

# --- IMPLEMENTATION -----------------------------------------------------------
type Handler = Callable[[dict[str, str]], None]  # placeholder for ASGI/RSGI app


@dataclass
class Node[T]:
    """Segment-based trie node"""

    not_found_handler: T
    method_not_allowed_handler: T
    handler: T | None = field(default=None)
    children: dict[str | HTTPMethod | None, Node] = field(default_factory=dict)
    wildcard: WildCardNode | None = field(default=None)
    catchall: CatchAllNode | None = field(default=None)


@dataclass
class WildCardNode[T]:
    name: str
    child: Node[T]


@dataclass
class CatchAllNode[T]:
    name: str
    child: Node[T]


def find_handler[T](
    path: str,
    method: HTTPMethod,
    tree: Node[T],
) -> tuple[T, dict[str, str]]:
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
        return current.not_found_handler, params

    leaf = current.children.get(method)
    if leaf is None:
        leaf = current.children.get(None)  # fallback to any method handler
        if leaf is None:
            return current.method_not_allowed_handler, params

    if leaf.handler is None:
        return current.not_found_handler, params

    return leaf.handler, params


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
"""
tree: Node[Handler] = Node(
    children={
        "admin": Node(
            children={
                HTTPMethod.GET: Node(
                    handler=admin_home_handler,
                    not_found_handler=admin_not_found_handler,
                    method_not_allowed_handler=method_not_allowed_handler,
                ),
                "user": Node(
                    wildcard=WildCardNode(
                        name="id",
                        child=Node(
                            children={
                                "rename": Node(
                                    children={
                                        HTTPMethod.POST: Node(
                                            handler=admin_user_rename_handler,
                                            not_found_handler=admin_not_found_handler,
                                            method_not_allowed_handler=method_not_allowed_handler,
                                        ),
                                    },
                                    not_found_handler=admin_not_found_handler,
                                    method_not_allowed_handler=method_not_allowed_handler,
                                ),
                                "transaction": Node(
                                    wildcard=WildCardNode(
                                        name="tx",
                                        child=Node(
                                            children={
                                                HTTPMethod.GET: Node(
                                                    handler=admin_user_transaction_view_handler,
                                                    not_found_handler=admin_not_found_handler,
                                                    method_not_allowed_handler=method_not_allowed_handler,
                                                ),
                                            },
                                            not_found_handler=admin_not_found_handler,
                                            method_not_allowed_handler=method_not_allowed_handler,
                                        ),
                                    ),
                                    not_found_handler=admin_not_found_handler,
                                    method_not_allowed_handler=method_not_allowed_handler,
                                ),
                            },
                            not_found_handler=admin_not_found_handler,
                            method_not_allowed_handler=method_not_allowed_handler,
                        ),
                    ),
                    not_found_handler=admin_not_found_handler,
                    method_not_allowed_handler=method_not_allowed_handler,
                ),
            },
            not_found_handler=admin_not_found_handler,
            method_not_allowed_handler=method_not_allowed_handler,
        ),
        "static": Node(
            catchall=CatchAllNode(
                name="path",
                child=Node(
                    children={
                        HTTPMethod.GET: Node(
                            handler=static_handler,
                            not_found_handler=not_found_handler,
                            method_not_allowed_handler=static_method_not_allowed_handler,
                        ),
                    },
                    not_found_handler=not_found_handler,
                    method_not_allowed_handler=static_method_not_allowed_handler,
                ),
            ),
            not_found_handler=not_found_handler,
            method_not_allowed_handler=static_method_not_allowed_handler,
        ),
        "": Node(  # "" is trailing slash (because result of "/foo/".split("/") == ["foo", ""])
            children={
                None: Node(  # None is any method
                    handler=home_handler,
                    not_found_handler=not_found_handler,
                    method_not_allowed_handler=method_not_allowed_handler,
                ),
            },
            not_found_handler=not_found_handler,
            method_not_allowed_handler=method_not_allowed_handler,
        ),
    },
    not_found_handler=not_found_handler,
    method_not_allowed_handler=method_not_allowed_handler,
)


def main() -> None:
    tests = [
        # simple, any method
        ("/", HTTPMethod.PATCH, home_handler),
        # simple, with method
        ("/admin", HTTPMethod.GET, admin_home_handler),
        # 404
        ("/some/nonexistent/route", HTTPMethod.GET, not_found_handler),
        # 404 on trailing slash
        ("/admin/", HTTPMethod.GET, admin_not_found_handler),
        # 405
        ("/admin", HTTPMethod.DELETE, method_not_allowed_handler),
        # 405
        ("/static/bleugh.txt", HTTPMethod.OPTIONS, static_method_not_allowed_handler),
        # wildcard param
        ("/admin/user/1/rename", HTTPMethod.POST, admin_user_rename_handler),
        # multiple wildcard params
        (
            "/admin/user/1/transaction/2",
            HTTPMethod.GET,
            admin_user_transaction_view_handler,
        ),
        # catchall param
        ("/static/lib/datastar.min.js", HTTPMethod.GET, static_handler),
    ]

    for path, method, expected_handler in tests:
        print(method, path)

        start = time.perf_counter()
        handler, params = find_handler(path, method, tree)
        end = time.perf_counter()

        print(f"took {end - start:.2E} seconds", file=sys.stderr, flush=True)

        handler(params)

        assert handler is expected_handler


if __name__ == "__main__":
    main()
