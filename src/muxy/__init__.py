from importlib.metadata import version

from .router import Router, path_params

__all__ = [
    "Router",
    "__version__",
    "path_params",
]

__version__ = version("muxy")
