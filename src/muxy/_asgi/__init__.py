import warnings

from .router import Router, path_params

warnings.warn(
    "The implementation of muxy-asgi is incomplete. It's primary use is in benchmarking.",
    stacklevel=2,
)

__all__ = [
    "Router",
    "path_params",
]
