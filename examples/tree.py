# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "muxy @ file:///${PROJECT_ROOT}/../muxy",
# ]
# ///
import asyncio
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from functools import reduce
from typing import Literal

from muxy.rsgi import (
    HTTPProtocol,
    HTTPScope,
    HTTPStreamTransport,
    Scope,
)
from muxy.tree import (
    CatchAllNode,
    FrozenDict,
    LeafKey,
    Node,
    WildCardNode,
    add_route,
    construct_route_tree,
    find_handler,
    merge_trees,
    path_params,
)


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
    tree = construct_route_tree(
        LeafKey.GET, "/user/{id}/profile", _test_user_profile_handler
    )
    pprint(tree)
    handler, middleware, params = find_handler("/user/42/profile", LeafKey.GET, tree)
    wrapped_handler = reduce(lambda h, m: m(h), reversed(middleware), handler)
    with path_params.set(params):
        await wrapped_handler(_test_scope("/user/42/profile", "GET"), _test_proto)
    del tree, handler, middleware, params, wrapped_handler
    print("-" * 80)
    print()

    # test tree merging
    tree1 = construct_route_tree(LeafKey.GET, "/user/{id}", _test_user_id_handler)
    tree2 = construct_route_tree(
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
    tree = construct_route_tree(LeafKey.GET, "/user/{id}", _test_user_id_handler)
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


if __name__ == "__main__":
    asyncio.run(main())
