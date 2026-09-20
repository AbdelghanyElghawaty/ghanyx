"""
Version information for Ghanyx.

This module is the single source of truth for the framework's version.
It is imported by both `pyproject.toml` (via setuptools-scm, optional)
and the package itself.

Keep this in sync with the version declared in `pyproject.toml`.
"""

__version__ = "0.1.0"
__version_info__ = (0, 1, 0)

__author__ = "Abdelghany Elghawaty"
__author_email__ = "abdelghany.elghawaty@gmail.com"

__license__ = "MIT"

__description__ = (
    "A modular Python framework for building desktop business applications."
)


def version_string() -> str:
    """Return a human-readable version string."""
    return f"Ghanyx {__version__}"


def version_tuple() -> tuple:
    """Return the version as a tuple of integers."""
    return __version_info__