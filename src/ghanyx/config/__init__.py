"""
Ghanyx config — unified configuration management.

Public API:
    get_config()             → Return the global config instance.
    load_config(...)         → Load a fresh config from files/env.
    reload_config()          → Reload the global config.
    set_config(config)       → Replace the global config (for tests).
    reset_config()           → Clear the global config (for tests).

Quick start:
    from ghanyx.config import get_config

    config = get_config()
    print(config.app_name)         # → "ghanyx"
    print(config.log_level)        # → "INFO"
    print(config.environment)      # → "development"

Priority (highest wins):
    1. Environment variables (os.environ)
    2. .env file
    3. config.toml file
    4. Built-in defaults
"""

from ghanyx.config.base import GhanyxConfig
from ghanyx.config.loader import (
    load_config,
    get_config,
    reload_config,
    set_config,
    reset_config,
)
from ghanyx.config.exceptions import (
    ConfigError,
    ConfigFileNotFoundError,
    ConfigParseError,
    ConfigValidationError,
    ConfigMissingKeyError,
    ConfigTypeError,
)

__all__ = [
    # Core
    "GhanyxConfig",
    "load_config",
    "get_config",
    "reload_config",
    "set_config",
    "reset_config",

    # Exceptions
    "ConfigError",
    "ConfigFileNotFoundError",
    "ConfigParseError",
    "ConfigValidationError",
    "ConfigMissingKeyError",
    "ConfigTypeError",
]