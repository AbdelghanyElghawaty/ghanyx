"""
Ghanyx — A modular Python framework for building desktop business applications.

Public API:
    from ghanyx import __version__
    from ghanyx.logging import setup_logging, get_logger
    from ghanyx.config import get_config
    from ghanyx.database import get_db
    from ghanyx.auth import AuthManager, User
    from ghanyx.errors import GhanyxError

For full documentation, see: https://github.com/AbdelghanyElghawaty/ghanyx
"""

from ghanyx.version import __version__, __author__, __license__

# ----- Config -----
from ghanyx.config import (
    GhanyxConfig,
    get_config,
    load_config,
    reload_config,
)

# ----- Database -----
from ghanyx.database import (
    Database,
    SQLiteDatabase,
    get_db,
    set_db,
    reset_db,
)

# ----- Auth (highlights only) -----
from ghanyx.auth import (
    User,
    AuthManager,
    Permission,
    PermissionSet,
)

# ----- Errors -----
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

    # Database
    "Database",
    "SQLiteDatabase",
    "get_db",
    "set_db",
    "reset_db",

    # Auth
    "User",
    "AuthManager",
    "Permission",
    "PermissionSet",

    # Errors
    "GhanyxError",
]