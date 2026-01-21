"""aftr - CLI for bootstrapping Python data projects."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("aftr")
except PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback for development
