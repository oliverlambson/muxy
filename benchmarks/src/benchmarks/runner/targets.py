"""Generate benchmark target URLs from route definitions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

from benchmarks.app._common import root_router

# Number of unique IDs to generate for parameterized routes
# This exceeds muxy's LRU cache size (1024) when combined with route count
NUM_IDS = 100

# Sample paths for catch-all routes
CATCHALL_PATHS = [
    "file.css",
    "js/app.js",
    "images/logo.png",
    "vendor/lib/module.min.js",
]


def extract_routes(router: dict, prefix: str = "") -> Iterator[tuple[str, str]]:
    """Recursively extract (method, path) tuples from router definition."""
    for method, path, _handler in router.get("handlers", []):
        yield (method, prefix + path)

    for mount_path, sub_router in router.get("mounts", []):
        yield from extract_routes(sub_router, prefix + mount_path)


def expand_route(method: str, path: str) -> Iterator[tuple[str, str]]:
    """Expand parameterized routes into concrete URLs."""
    # Catch-all routes: {path...}
    if "{path...}" in path:
        base = path.replace("{path...}", "")
        for sample_path in CATCHALL_PATHS:
            yield (method, base + sample_path)
        return

    # Check for parameters like {id}, {token}
    param_match = re.search(r"\{(\w+)\}", path)
    if param_match:
        param_name = param_match.group(1)
        for i in range(1, NUM_IDS + 1):
            if param_name == "token":
                value = f"token_{i}"
            else:
                value = str(i)
            concrete_path = re.sub(r"\{" + param_name + r"\}", value, path)
            yield (method, concrete_path)
        return

    # No parameters - yield as-is
    yield (method, path)


def generate_targets() -> list[tuple[str, str]]:
    """Generate all concrete (method, path) targets for benchmarking."""
    targets = []
    for method, path in extract_routes(root_router):
        targets.extend(expand_route(method, path))
    return targets


def main() -> None:
    """Output targets in format readable by wrk Lua script."""
    targets = generate_targets()
    for method, path in targets:
        print(f"{method} {path}")


if __name__ == "__main__":
    main()
