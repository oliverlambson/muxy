"""Zero dependency routing tree implementation with path param support.

Inspired by go 1.22+ net/http's routingNode
"""

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Literal, Never

path_params: ContextVar[dict[str, str]] = ContextVar("path_params")
http_route: ContextVar[str] = ContextVar("http_route")

type Middleware[T] = Callable[[T], T]
type HTTPMethod = Literal[
    "CONNECT", "DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT", "TRACE"
]
type WebsocketMethod = Literal["WEBSOCKET"]


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

    def update(
        self,
        handler: T | None = None,
        middleware: tuple[Middleware[T], ...] | None = None,
        children: FrozenDict[str | LeafKey, Node[T]] | None = None,
        wildcard: WildCardNode[T] | None = None,
        catchall: CatchAllNode[T] | None = None,
        not_found_handler: T | None = None,
        method_not_allowed_handler: T | None = None,
    ) -> Node[T]:
        return Node(
            handler=handler if handler is not None else self.handler,
            middleware=middleware if middleware is not None else self.middleware,
            children=children if children is not None else self.children,
            wildcard=wildcard if wildcard is not None else self.wildcard,
            catchall=catchall if catchall is not None else self.catchall,
            not_found_handler=not_found_handler
            if not_found_handler is not None
            else self.not_found_handler,
            method_not_allowed_handler=method_not_allowed_handler
            if method_not_allowed_handler is not None
            else self.method_not_allowed_handler,
        )


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
) -> tuple[T, tuple[Middleware[T], ...], dict[str, str], str]:
    """Traverses the tree to find the best match handler.

    Each path segment priority is: exact match > wildcard match  > catchall match
    If no matching node is found for the path, return not found handler
    If matching node for path does not support method, return method not supported handler

    Returns (handler, middleware, params, route_pattern) where route_pattern
    is the matched route (e.g. "/user/{id}") or "" for error handlers.
    """
    segments = path[1:].split("/")  # assumes leading "/"

    current = tree
    child = None
    params = {}
    route_parts: list[str] = []
    for i, seg in enumerate(segments):
        child = current.children.get(seg)
        if child is not None:  # exact match
            route_parts.append(seg)
            current = child  # traverse to child
            continue
        if current.wildcard is not None:  # fallback to wildcard match
            params[current.wildcard.name] = seg
            route_parts.append("{" + current.wildcard.name + "}")
            current = current.wildcard.child  # traverse to wildcard child
            continue
        if current.catchall is not None:  # fallback to catchall match
            params[current.catchall.name] = "/".join(segments[i:])
            route_parts.append("{" + current.catchall.name + "...}")
            current = current.catchall.child  # traverse to catchall child
            break
        # no match
        if current.not_found_handler is None:
            msg = "No not found handler set"
            raise ValueError(msg)
        return current.not_found_handler, (), {}, ""

    leaf = current.children.get(method)
    if leaf is None:
        leaf = current.children.get(LeafKey.ANY_HTTP)  # fallback to any method handler
        if leaf is None:
            if any(isinstance(k, LeafKey) for k in current.children.keys()):
                if current.method_not_allowed_handler is None:
                    msg = "No method not allowed handler set"
                    raise ValueError(msg)
                return current.method_not_allowed_handler, (), params, ""
            if current.not_found_handler is None:
                msg = "No not found handler set"
                raise ValueError(msg)
            return current.not_found_handler, (), {}, ""

    if leaf.handler is None:
        if current.not_found_handler is None:
            msg = "No not found handler set"
            raise ValueError(msg)
        return current.not_found_handler, (), {}, ""

    return leaf.handler, leaf.middleware, params, "/" + "/".join(route_parts)


def add_route[T](
    tree: Node[T],
    method: LeafKey,
    path: str,
    handler: T,
    middleware: tuple[Middleware[T], ...] = (),
) -> Node[T]:
    """add route to tree for handler on method/path with optional middleware"""
    new_tree = _construct_route_tree(method, path, handler, middleware)
    return _merge_trees(tree, new_tree)


def mount_tree[T](path: str, parent: Node[T], child: Node[T]) -> Node[T]:
    # Pre-cascade child's middleware so it stays with child routes after merge
    if child.middleware:
        child = _cascade_middleware(child, ())
    if path == "/":
        return _merge_trees(parent, child)  # root mount: merge trees directly
    sub_tree = _construct_sub_tree(path, child)
    return _merge_trees(parent, sub_tree)


def _cascade_middleware[T](
    tree: Node[T], middleware: tuple[Middleware[T], ...]
) -> Node[T]:
    """Cascade middleware down through tree, only setting on leaf nodes (with handlers)."""
    if tree.middleware:
        middleware = middleware + tree.middleware

    if tree.handler is not None:
        tree = tree.update(middleware=middleware)
    else:
        tree = tree.update(middleware=())

    if tree.wildcard is not None:
        tree = tree.update(
            wildcard=WildCardNode(
                name=tree.wildcard.name,
                child=_cascade_middleware(tree.wildcard.child, middleware),
            )
        )

    if tree.catchall is not None:
        tree = tree.update(
            catchall=CatchAllNode(
                name=tree.catchall.name,
                child=_cascade_middleware(tree.catchall.child, middleware),
            )
        )

    tree = tree.update(
        children=FrozenDict(
            {
                k: _cascade_middleware(child, middleware)
                for k, child in tree.children.items()
            }
        )
    )

    return tree


def finalize_tree[T](
    tree: Node[T],
    not_found_handler: T,
    method_not_allowed_handler: T,
    middleware: tuple[Middleware[T], ...],
) -> Node[T]:
    """
    cascade not_found_handler, method_not_allowed_handler, and middleware down
    through tree
    """
    if tree.not_found_handler is None:  # cascade default
        tree = tree.update(not_found_handler=not_found_handler)
    else:  # update default
        not_found_handler = tree.not_found_handler

    if tree.method_not_allowed_handler is None:  # cascade default
        tree = tree.update(method_not_allowed_handler=method_not_allowed_handler)
    else:  # update default
        method_not_allowed_handler = tree.method_not_allowed_handler

    if tree.middleware:
        middleware += tree.middleware
    if middleware:
        tree = tree.update(middleware=middleware)

    if tree.wildcard is not None:
        tree = tree.update(
            wildcard=WildCardNode(
                name=tree.wildcard.name,
                child=finalize_tree(
                    tree.wildcard.child,
                    not_found_handler,
                    method_not_allowed_handler,
                    middleware,
                ),
            )
        )

    if tree.catchall is not None:
        tree = tree.update(
            catchall=CatchAllNode(
                name=tree.catchall.name,
                child=finalize_tree(
                    tree.catchall.child,
                    not_found_handler,
                    method_not_allowed_handler,
                    middleware,
                ),
            )
        )

    tree = tree.update(
        children=FrozenDict(
            {
                k: finalize_tree(
                    child,
                    not_found_handler,
                    method_not_allowed_handler,
                    middleware,
                )
                for k, child in tree.children.items()
            }
        )
    )

    return tree


def _construct_route_tree[T](
    method: LeafKey,
    path: str,
    handler: T,
    middleware: tuple[Middleware[T], ...] = (),
) -> Node[T]:
    """construct tree for handler on method/path with optional middleware"""
    leaf = Node(
        middleware=middleware,
        handler=handler,
    )
    child: Node[T] = Node(
        children=FrozenDict({method: leaf}),
    )
    return _construct_sub_tree(path, child)


def _construct_sub_tree[T](path: str, child: Node[T]) -> Node[T]:
    """construct sub tree for existing node on path"""
    if not path.startswith("/"):
        msg = f"path must start with '/', provided {path=}"
        raise ValueError(msg)
    segments = path[1:].split("/")

    # construct tree
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


def format_routes[T](
    root: Node[T], *, verbose: bool = False, tree: bool = False
) -> str:
    """Format registered routes from a finalized tree as a human-readable string.

    By default produces a column-aligned flat route list:

        *      /                                   home_handler
        GET    /admin                              admin_home_handler                    [admin_middleware]
        POST   /admin/user/{id}/rename             admin_user_rename_handler             [admin_middleware > admin_user_middleware > admin_user_rename_middleware]
        GET    /admin/user/{id}/transaction/{tx}   admin_user_transaction_view_handler   [admin_middleware > admin_user_middleware]
        GET    /static/{path...}                   static_handler

    With `tree=True`, produces a visual tree instead:

        /
        ├── [*] home_handler
        ├── admin
        │   ├── [GET] admin_home_handler [admin_middleware]
        │   └── user
        │       └── {id}
        │           ├── rename
        │           │   └── [POST] admin_user_rename_handler [admin_middleware > admin_user_middleware > admin_user_rename_middleware]
        │           └── transaction
        │               └── {tx}
        │                   └── [GET] admin_user_transaction_view_handler [admin_middleware > admin_user_middleware]
        └── static
            └── {path...}
                └── [GET] static_handler

    With `verbose=True`, error handler overrides are included in both formats.
    """
    if tree:
        return _format_tree(root, verbose=verbose)
    return _format_route_list(root, verbose=verbose)


type _Route = tuple[str, str, str, list[str]]
type _ErrorOverride = tuple[str, str, str]


def _format_route_list[T](root: Node[T], *, verbose: bool) -> str:
    """Column-aligned flat route list."""
    routes, errors = _collect_routes(
        root,
        [],
        root.not_found_handler,
        root.method_not_allowed_handler,
    )
    routes.sort(key=lambda r: (r[1], r[0]))
    if not routes:
        return ""

    method_w = max(len(r[0]) for r in routes)
    path_w = max(len(r[1]) for r in routes)
    handler_w = max(len(r[2]) for r in routes)

    lines: list[str] = []
    for method, path, handler, mw in routes:
        if mw:
            lines.append(
                f"{method:<{method_w}}   {path:<{path_w}}   "
                f"{handler:<{handler_w}}   [{' > '.join(mw)}]"
            )
        else:
            lines.append(f"{method:<{method_w}}   {path:<{path_w}}   {handler}")

    if verbose:
        root_errors: list[_ErrorOverride] = []
        if root.not_found_handler is not None:
            root_errors.append(("404", "/", _qualname(root.not_found_handler)))
        if root.method_not_allowed_handler is not None:
            root_errors.append(("405", "/", _qualname(root.method_not_allowed_handler)))
        all_errors = root_errors + sorted(errors, key=lambda e: (e[1], e[0]))
        if all_errors:
            lines.append("")
            status_w = max(len(e[0]) for e in all_errors)
            err_path_w = max(len(e[1]) for e in all_errors)
            for status, path, handler in all_errors:
                lines.append(f"{status:<{status_w}}   {path:<{err_path_w}}   {handler}")

    return "\n".join(lines)


def _collect_routes[T](
    node: Node[T],
    parts: list[str],
    parent_nfh: T | None,
    parent_mah: T | None,
) -> tuple[list[_Route], list[_ErrorOverride]]:
    """Walk the trie, returning route entries and error handler transitions."""
    routes: list[_Route] = []
    errors: list[_ErrorOverride] = []

    if node.not_found_handler is not parent_nfh:
        errors.append(("404", "/" + "/".join(parts), _qualname(node.not_found_handler)))
    if node.method_not_allowed_handler is not parent_mah:
        errors.append(
            ("405", "/" + "/".join(parts), _qualname(node.method_not_allowed_handler))
        )

    for key, child in node.children.items():
        if isinstance(key, LeafKey):
            if child.handler is not None:
                method_str = "*" if key == LeafKey.ANY_HTTP else key.value
                path = "/" + "/".join(parts)
                mw = [_qualname(m) for m in child.middleware]
                routes.append((method_str, path, _qualname(child.handler), mw))
        else:
            sub_routes, sub_errors = _collect_routes(
                child,
                [*parts, key],
                node.not_found_handler,
                node.method_not_allowed_handler,
            )
            routes.extend(sub_routes)
            errors.extend(sub_errors)

    if node.wildcard is not None:
        sub_routes, sub_errors = _collect_routes(
            node.wildcard.child,
            [*parts, "{" + node.wildcard.name + "}"],
            node.not_found_handler,
            node.method_not_allowed_handler,
        )
        routes.extend(sub_routes)
        errors.extend(sub_errors)

    if node.catchall is not None:
        sub_routes, sub_errors = _collect_routes(
            node.catchall.child,
            [*parts, "{" + node.catchall.name + "...}"],
            node.not_found_handler,
            node.method_not_allowed_handler,
        )
        routes.extend(sub_routes)
        errors.extend(sub_errors)

    return routes, errors


def _format_tree[T](root: Node[T], *, verbose: bool) -> str:
    """Visual tree with box-drawing characters."""
    root_label = "/"
    if verbose:
        annotations: list[str] = []
        if root.not_found_handler is not None:
            annotations.append(f"404: {_qualname(root.not_found_handler)}")
        if root.method_not_allowed_handler is not None:
            annotations.append(f"405: {_qualname(root.method_not_allowed_handler)}")
        if annotations:
            root_label += " (" + ", ".join(annotations) + ")"
    lines: list[str] = [root_label]
    _render_tree(root, "", verbose=verbose, lines=lines)
    return "\n".join(lines)


def _render_tree[T](
    node: Node[T], prefix: str, *, verbose: bool, lines: list[str]
) -> None:
    """Recursively render a node's children with tree-drawing prefixes."""
    items: list[tuple[str, Node[T] | None]] = []

    # Handler entries from "" child (root "/" path handlers)
    empty_child = node.children.get("")
    if empty_child is not None:
        for key, leaf in _sorted_leaf_keys(empty_child.children):
            if leaf.handler is not None:
                items.append((_handler_label(key, leaf), None))

    # Handler entries from own LeafKey children
    for key, leaf in _sorted_leaf_keys(node.children):
        if leaf.handler is not None:
            items.append((_handler_label(key, leaf), None))

    # Named segment children (sorted, excluding "")
    for seg, child in sorted(
        ((k, v) for k, v in node.children.items() if isinstance(k, str) and k != ""),
        key=lambda x: x[0],
    ):
        annotation = _error_annotation(child, node) if verbose else ""
        items.append((f"{seg}{annotation}", child))

    # Wildcard
    if node.wildcard is not None:
        child = node.wildcard.child
        annotation = _error_annotation(child, node) if verbose else ""
        items.append((f"{{{node.wildcard.name}}}{annotation}", child))

    # Catchall
    if node.catchall is not None:
        child = node.catchall.child
        annotation = _error_annotation(child, node) if verbose else ""
        items.append((f"{{{node.catchall.name}...}}{annotation}", child))

    for i, (label, child) in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{label}")
        if child is not None:
            extension = "    " if is_last else "│   "
            _render_tree(child, prefix + extension, verbose=verbose, lines=lines)


def _qualname(obj: object) -> str:
    """Extract __qualname__ from a callable, falling back to repr."""
    return str(obj.__qualname__) if hasattr(obj, "__qualname__") else repr(obj)


def _sorted_leaf_keys[T](
    children: FrozenDict[str | LeafKey, Node[T]],
) -> list[tuple[LeafKey, Node[T]]]:
    """Filter and sort a node's children to LeafKey entries only."""
    return sorted(
        ((k, v) for k, v in children.items() if isinstance(k, LeafKey)),
        key=lambda x: x[0].value,
    )


def _handler_label[T](key: LeafKey, leaf: Node[T]) -> str:
    """Format a handler entry: [METHOD] name [middleware]."""
    method = "*" if key == LeafKey.ANY_HTTP else key.value
    label = f"[{method}] {_qualname(leaf.handler)}"
    if leaf.middleware:
        mw = " > ".join(_qualname(m) for m in leaf.middleware)
        label += f" [{mw}]"
    return label


def _error_annotation[T](child: Node[T], parent: Node[T]) -> str:
    """Annotate error handler transitions from parent to child."""
    parts: list[str] = []
    if child.not_found_handler is not parent.not_found_handler:
        parts.append(f"404: {_qualname(child.not_found_handler)}")
    if child.method_not_allowed_handler is not parent.method_not_allowed_handler:
        parts.append(f"405: {_qualname(child.method_not_allowed_handler)}")
    if not parts:
        return ""
    return " (" + ", ".join(parts) + ")"


def _merge_trees[T](tree1: Node[T], tree2: Node[T]) -> Node[T]:
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

    if tree2.middleware and tree1.middleware != tree2.middleware:
        msg = "node being merged in has conflicting middleware"
        raise ValueError(msg)
    middleware = tree1.middleware or tree2.middleware

    if tree1.wildcard is not None and tree2.wildcard and tree2.wildcard is not None:
        if tree1.wildcard.name != tree2.wildcard.name:
            msg = "nodes have conflicting wildcards"
            raise ValueError(msg)
        wildcard: WildCardNode[T] | None = WildCardNode(
            name=tree1.wildcard.name,
            child=_merge_trees(tree1.wildcard.child, tree2.wildcard.child),
        )
    else:
        wildcard = tree1.wildcard or tree2.wildcard

    if tree1.catchall is not None and tree2.catchall is not None:
        if tree1.catchall.name != tree2.catchall.name:
            msg = "nodes have conclicting catchalls"
            raise ValueError(msg)
        catchall: CatchAllNode[T] | None = CatchAllNode(
            name=tree1.catchall.name,
            child=_merge_trees(tree1.catchall.child, tree2.catchall.child),
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
        | {k: _merge_trees(tree1.children[k], tree2.children[k]) for k in common_keys}
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
