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
            if any(isinstance(k, LeafKey) for k in current.children.keys()):
                if current.method_not_allowed_handler is None:
                    msg = "No method not allowed handler set"
                    raise ValueError(msg)
                return current.method_not_allowed_handler, (), params
            if current.not_found_handler is None:
                msg = "No not found handler set"
                raise ValueError(msg)
            return current.not_found_handler, (), {}

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
    new_tree = _construct_route_tree(method, path, handler, middleware)
    return _merge_trees(tree, new_tree)


def mount_tree[T](path: str, parent: Node[T], child: Node[T]) -> Node[T]:
    sub_tree = _construct_sub_tree(path, child)
    return _merge_trees(parent, sub_tree)


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
