from importlib.metadata import version

from .router import Router, http_route, path_params

__all__ = [
    "Router",
    "__version__",
    "http_route",
    "path_params",
]

__version__ = version("muxy")
