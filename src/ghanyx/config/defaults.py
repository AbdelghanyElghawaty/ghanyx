"""
Default configuration values for Ghanyx.

These values are used when nothing is specified in `.env`, `config.toml`,
or environment variables.

Priority (highest wins):
    1. Environment variables (os.environ)
    2. .env file
    3. config.toml file
    4. These defaults

Rule of thumb:
    - Every setting here MUST have a safe, production-ready default.
    - Never put secrets here — use .env instead.
"""

from __future__ import annotations

from typing import Any

# ============================================================
# App
# ============================================================
DEFAULT_APP_NAME = "ghanyx"
DEFAULT_ENVIRONMENT = "development"  # development | staging | production
DEFAULT_LANGUAGE = "ar"              # ar | en
DEFAULT_TIMEZONE = "Africa/Cairo"

# ============================================================
# Logging
# ============================================================
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_MAX_BYTES = 5 * 1024 * 1024   # 5 MB
DEFAULT_LOG_BACKUP_COUNT = 5
DEFAULT_LOG_CONSOLE = True
DEFAULT_LOG_COLORS = True

# ============================================================
# Database
# ============================================================
DEFAULT_DB_FILENAME = "data.db"
DEFAULT_DB_DIR = "data"

# ============================================================
# UI
# ============================================================
DEFAULT_THEME = "dark"       # dark | light
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 850

# ============================================================
# Paths
# ============================================================
DEFAULT_DATA_DIR = "data"
DEFAULT_BACKUPS_DIR = "backups"
DEFAULT_EXPORTS_DIR = "exports"


# ============================================================
# The complete defaults dict
# ============================================================
# This is the single source of truth for default values.
# Other modules import this instead of hard-coding values.
#
# Keys use dot-notation to support nesting:
#     "logging.level"  →  config["logging"]["level"]
# ============================================================
DEFAULTS: dict[str, Any] = {
    # App
    "app.name": DEFAULT_APP_NAME,
    "app.environment": DEFAULT_ENVIRONMENT,
    "app.language": DEFAULT_LANGUAGE,
    "app.timezone": DEFAULT_TIMEZONE,

    # Logging
    "logging.level": DEFAULT_LOG_LEVEL,
    "logging.dir": DEFAULT_LOG_DIR,
    "logging.max_bytes": DEFAULT_LOG_MAX_BYTES,
    "logging.backup_count": DEFAULT_LOG_BACKUP_COUNT,
    "logging.console": DEFAULT_LOG_CONSOLE,
    "logging.colors": DEFAULT_LOG_COLORS,

    # Database
    "database.filename": DEFAULT_DB_FILENAME,
    "database.dir": DEFAULT_DB_DIR,

    # UI
    "ui.theme": DEFAULT_THEME,
    "ui.window_width": DEFAULT_WINDOW_WIDTH,
    "ui.window_height": DEFAULT_WINDOW_HEIGHT,

    # Paths
    "paths.data_dir": DEFAULT_DATA_DIR,
    "paths.backups_dir": DEFAULT_BACKUPS_DIR,
    "paths.exports_dir": DEFAULT_EXPORTS_DIR,
}


# ============================================================
# Environment-specific overrides
# ============================================================
# These values are applied ON TOP of DEFAULTS depending on
# the value of `app.environment`.
#
# Example:
#     In development → log level = DEBUG
#     In production  → log level = INFO
# ============================================================
ENVIRONMENT_OVERRIDES: dict[str, dict[str, Any]] = {
    "development": {
        "logging.level": "DEBUG",
        "logging.console": True,
        "logging.colors": True,
    },
    "staging": {
        "logging.level": "INFO",
        "logging.console": True,
        "logging.colors": False,
    },
    "production": {
        "logging.level": "INFO",
        "logging.console": False,
        "logging.colors": False,
    },
}


# ============================================================
# Valid choices for validation
# ============================================================
VALID_ENVIRONMENTS = ("development", "staging", "production")
VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
VALID_LANGUAGES = ("ar", "en")
VALID_THEMES = ("dark", "light")