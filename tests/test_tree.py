from collections.abc import Callable

import pytest

from muxy.tree import (
    CatchAllNode,
    FrozenDict,
    LeafKey,
    Node,
    WildCardNode,
    _construct_route_tree,
    _construct_sub_tree,
    _merge_trees,
    add_route,
    finalize_tree,
    find_handler,
    format_routes,
    mount_tree,
)


def test__merge_trees() -> None:
    user_profile_handler = lambda: "user_profile_handler"  # noqa: E731
    user_id_handler = lambda: "user_id_handler"  # noqa: E731
    tree1 = Node(
        children=FrozenDict(
            {
                "user": Node(
                    wildcard=WildCardNode(
                        name="id",
                        child=Node(
                            children=FrozenDict(
                                {
                                    "profile": Node(
                                        children=FrozenDict(
                                            {
                                                LeafKey.GET: Node(
                                                    handler=user_profile_handler
                                                )
                                            }
                                        )
                                    )
                                }
                            )
                        ),
                    )
                )
            }
        )
    )
    tree2 = Node(
        children=FrozenDict(
            {
                "user": Node(
                    wildcard=WildCardNode(
                        name="id",
                        child=Node(
                            children=FrozenDict(
                                {
                                    LeafKey.GET: Node(handler=user_id_handler),
                                }
                            )
                        ),
                    )
                )
            }
        )
    )
    tree = _merge_trees(tree1, tree2)
    expected_tree = Node(
        children=FrozenDict(
            {
                "user": Node(
                    wildcard=WildCardNode(
                        name="id",
                        child=Node(
                            children=FrozenDict(
                                {
                                    LeafKey.GET: Node(handler=user_id_handler),
                                    "profile": Node(
                                        children=FrozenDict(
                                            {
                                                LeafKey.GET: Node(
                                                    handler=user_profile_handler
                                                )
                                            }
                                        )
                                    ),
                                }
                            )
                        ),
                    )
                )
            }
        )
    )
    assert tree == expected_tree


def test__construct_sub_tree() -> None:
    user_profile_handler = lambda: "user_profile_handler"  # noqa: E731
    child = Node(
        wildcard=WildCardNode(
            name="id",
            child=Node(
                children=FrozenDict(
                    {
                        "profile": Node(
                            children=FrozenDict(
                                {LeafKey.GET: Node(handler=user_profile_handler)}
                            )
                        )
                    }
                )
            ),
        )
    )
    expected_tree = Node(children=FrozenDict({"user": child}))
    tree = _construct_sub_tree("/user", child)
    assert tree == expected_tree


def test__construct_route_tree() -> None:
    user_profile_handler = lambda: "user_profile_handler"  # noqa: E731
    tree = _construct_route_tree(
        LeafKey.GET, "/user/{id}/profile", user_profile_handler
    )
    expected_tree = Node(
        children=FrozenDict(
            {
                "user": Node(
                    wildcard=WildCardNode(
                        name="id",
                        child=Node(
                            children=FrozenDict(
                                {
                                    "profile": Node(
                                        children=FrozenDict(
                                            {
                                                LeafKey.GET: Node(
                                                    handler=user_profile_handler
                                                )
                                            }
                                        )
                                    )
                                }
                            )
                        ),
                    )
                )
            }
        )
    )
    assert tree == expected_tree


def test_finalize_tree() -> None:
    tree = finalize_tree(
        unfinalized_tree,
        not_found_handler=not_found_handler,
        method_not_allowed_handler=method_not_allowed_handler,
        middleware=(),
    )
    assert tree == finalized_tree


def test_mount_tree() -> None:
    parent_handler = lambda: "parent_handler"  # noqa: E731
    child_handler = lambda: "child_handler"  # noqa: E731
    parent = Node(
        children=FrozenDict(
            {
                LeafKey.GET: Node(handler=parent_handler),
            }
        )
    )
    child = Node(
        children=FrozenDict(
            {
                LeafKey.GET: Node(handler=child_handler),
            }
        )
    )
    tree = mount_tree("/api", parent, child)
    expected_tree = Node(
        children=FrozenDict(
            {
                LeafKey.GET: Node(handler=parent_handler),
                "api": Node(
                    children=FrozenDict(
                        {
                            LeafKey.GET: Node(handler=child_handler),
                        }
                    )
                ),
            }
        )
    )
    assert tree == expected_tree


def test_add_route() -> None:
    user_id_handler = lambda: "user_id_handler"  # noqa: E731
    user_profile_handler = lambda: "user_profile_handler"  # noqa: E731
    tree1 = Node(
        children=FrozenDict(
            {
                "user": Node(
                    wildcard=WildCardNode(
                        name="id",
                        child=Node(
                            children=FrozenDict(
                                {
                                    LeafKey.GET: Node(handler=user_id_handler),
                                }
                            )
                        ),
                    )
                )
            }
        )
    )
    tree = add_route(tree1, LeafKey.GET, "/user/{id}/profile", user_profile_handler)
    expected_tree = Node(
        children=FrozenDict(
            {
                "user": Node(
                    wildcard=WildCardNode(
                        name="id",
                        child=Node(
                            children=FrozenDict(
                                {
                                    LeafKey.GET: Node(handler=user_id_handler),
                                    "profile": Node(
                                        children=FrozenDict(
                                            {
                                                LeafKey.GET: Node(
                                                    handler=user_profile_handler
                                                )
                                            }
                                        )
                                    ),
                                }
                            )
                        ),
                    )
                )
            }
        )
    )
    assert tree == expected_tree


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


# handlers
def admin_home_handler():
    return "admin_home"


def admin_user_rename_handler():
    return "admin_user_rename"


def admin_user_transaction_view_handler():
    return "admin_user_transaction_view"


def static_handler():
    return "static"


def home_handler():
    return "home"


def not_found_handler():
    return "not_found"


def admin_not_found_handler():
    return "admin_not_found"


def method_not_allowed_handler():
    return "method_not_allowed"


def static_method_not_allowed_handler():
    return "static_method_not_allowed"


# middleware
def admin_middleware(s):
    return s + ".admin_middleware"


def admin_user_middleware(s):
    return s + ".admin_user_middleware"


def admin_user_rename_middleware(s):
    return s + ".admin_user_rename_middleware"


unfinalized_tree = Node(
    children=FrozenDict(
        {
            "admin": Node(
                children=FrozenDict(
                    {
                        LeafKey.GET: Node(handler=admin_home_handler),
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
                                                            middleware=(
                                                                admin_user_rename_middleware,
                                                            ),
                                                        ),
                                                    }
                                                ),
                                            ),
                                            "transaction": Node(
                                                wildcard=WildCardNode(
                                                    name="tx",
                                                    child=Node(
                                                        children=FrozenDict(
                                                            {
                                                                LeafKey.GET: Node(
                                                                    handler=admin_user_transaction_view_handler
                                                                ),
                                                            }
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        }
                                    ),
                                ),
                            ),
                            middleware=(admin_user_middleware,),
                        ),
                    }
                ),
                not_found_handler=admin_not_found_handler,
                middleware=(admin_middleware,),
            ),
            "static": Node(
                catchall=CatchAllNode(
                    name="path",
                    child=Node(
                        children=FrozenDict(
                            {
                                LeafKey.GET: Node(handler=static_handler),
                            }
                        ),
                    ),
                ),
                method_not_allowed_handler=static_method_not_allowed_handler,
            ),
            "": Node(  # "" is trailing slash (because result of "/foo/".split("/") == ["foo", ""])
                children=FrozenDict(
                    {
                        LeafKey.ANY_HTTP: Node(
                            handler=home_handler,
                        ),
                    }
                ),
            ),
        }
    ),
)
finalized_tree = Node(
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


@pytest.mark.parametrize(
    "path, method, expected_handler, expected_middleware, expected_params",
    [
        # simple, any method
        ("/", LeafKey.PATCH, home_handler, (), {}),
        # simple, with method
        ("/admin", LeafKey.GET, admin_home_handler, (admin_middleware,), {}),
        # 404
        ("/some/nonexistent/route", LeafKey.GET, not_found_handler, (), {}),
        # 404 on trailing slash
        ("/admin/", LeafKey.GET, admin_not_found_handler, (), {}),
        # 404 on route with no handlers
        ("/admin/user/", LeafKey.GET, admin_not_found_handler, (), {}),
        # 405
        ("/admin", LeafKey.DELETE, method_not_allowed_handler, (), {}),
        # 405
        (
            "/static/bleugh.txt",
            LeafKey.OPTIONS,
            static_method_not_allowed_handler,
            (),
            {"path": "bleugh.txt"},
        ),
        # wildcard param
        (
            "/admin/user/1/rename",
            LeafKey.POST,
            admin_user_rename_handler,
            (admin_middleware, admin_user_middleware, admin_user_rename_middleware),
            {"id": "1"},
        ),
        (
            "/admin/user/1/rename",
            LeafKey.POST,
            admin_user_rename_handler,
            (admin_middleware, admin_user_middleware, admin_user_rename_middleware),
            {"id": "1"},
        ),
        # multiple wildcard params
        (
            "/admin/user/1/transaction/2",
            LeafKey.GET,
            admin_user_transaction_view_handler,
            (admin_middleware, admin_user_middleware),
            {"id": "1", "tx": "2"},
        ),
        # catchall param
        (
            "/static/lib/datastar.min.js",
            LeafKey.GET,
            static_handler,
            (),
            {"path": "lib/datastar.min.js"},
        ),
    ],
)
def test_find_handler(
    path: str,
    method: LeafKey,
    expected_handler: Callable[[], None],
    expected_middleware: tuple[Callable[[Callable[[], None]], Callable[[], None]], ...],
    expected_params: dict[str, str],
) -> None:
    handler, middleware, params = find_handler(path, method, finalized_tree)
    assert handler is expected_handler
    assert middleware == expected_middleware
    assert params == expected_params


def test_format_routes() -> None:
    expected = "\n".join(
        [
            "*      /                                   home_handler",
            "GET    /admin                              admin_home_handler                    [admin_middleware]",
            "POST   /admin/user/{id}/rename             admin_user_rename_handler             [admin_middleware > admin_user_middleware > admin_user_rename_middleware]",
            "GET    /admin/user/{id}/transaction/{tx}   admin_user_transaction_view_handler   [admin_middleware > admin_user_middleware]",
            "GET    /static/{path...}                   static_handler",
        ]
    )
    assert format_routes(finalized_tree) == expected


def test_format_routes_verbose() -> None:
    expected = "\n".join(
        [
            "*      /                                   home_handler",
            "GET    /admin                              admin_home_handler                    [admin_middleware]",
            "POST   /admin/user/{id}/rename             admin_user_rename_handler             [admin_middleware > admin_user_middleware > admin_user_rename_middleware]",
            "GET    /admin/user/{id}/transaction/{tx}   admin_user_transaction_view_handler   [admin_middleware > admin_user_middleware]",
            "GET    /static/{path...}                   static_handler",
            "",
            "404   /         not_found_handler",
            "405   /         method_not_allowed_handler",
            "404   /admin    admin_not_found_handler",
            "405   /static   static_method_not_allowed_handler",
        ]
    )
    assert format_routes(finalized_tree, verbose=True) == expected


def test_format_tree() -> None:
    expected = "\n".join(
        [
            "/",
            "├── [*] home_handler",
            "├── admin",
            "│   ├── [GET] admin_home_handler [admin_middleware]",
            "│   └── user",
            "│       └── {id}",
            "│           ├── rename",
            "│           │   └── [POST] admin_user_rename_handler [admin_middleware > admin_user_middleware > admin_user_rename_middleware]",
            "│           └── transaction",
            "│               └── {tx}",
            "│                   └── [GET] admin_user_transaction_view_handler [admin_middleware > admin_user_middleware]",
            "└── static",
            "    └── {path...}",
            "        └── [GET] static_handler",
        ]
    )
    assert format_routes(finalized_tree, tree=True) == expected


def test_format_tree_verbose() -> None:
    expected = "\n".join(
        [
            "/ (404: not_found_handler, 405: method_not_allowed_handler)",
            "├── [*] home_handler",
            "├── admin (404: admin_not_found_handler)",
            "│   ├── [GET] admin_home_handler [admin_middleware]",
            "│   └── user",
            "│       └── {id}",
            "│           ├── rename",
            "│           │   └── [POST] admin_user_rename_handler [admin_middleware > admin_user_middleware > admin_user_rename_middleware]",
            "│           └── transaction",
            "│               └── {tx}",
            "│                   └── [GET] admin_user_transaction_view_handler [admin_middleware > admin_user_middleware]",
            "└── static (405: static_method_not_allowed_handler)",
            "    └── {path...}",
            "        └── [GET] static_handler",
        ]
    )
    assert format_routes(finalized_tree, verbose=True, tree=True) == expected
