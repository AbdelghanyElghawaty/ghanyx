"""
Ghanyx — A modular Python framework for building desktop business applications.

Public API:
    from ghanyx import __version__
    from ghanyx.logging import setup_logging, get_logger
    from ghanyx.config import get_config
    from ghanyx.errors import GhanyxError

For full documentation, see: https://github.com/AbdelghanyElghawaty/ghanyx
"""

from ghanyx.version import __version__, __author__, __license__

# Re-export the most commonly used pieces at the top level,
# so users can do `from ghanyx import get_config` if they prefer.
from ghanyx.config import (
    GhanyxConfig,
    get_config,
    load_config,
    reload_config,
)
from ghanyx.errors import GhanyxError

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",

    # Config
    "GhanyxConfig",
    "get_config",
    "load_config",
    "reload_config",

    # Errors
    "GhanyxError",
]