"""
Remote clipboard client and server package.

The package exposes CLI entrypoints:
- remoclip: client CLI
- remoclip_server: server CLI
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("remoclip")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = ["__version__"]
