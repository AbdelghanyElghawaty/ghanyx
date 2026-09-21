"""
Config loader — reads configuration from multiple sources.

Sources (in priority order, highest wins):
    1. Environment variables (os.environ)
    2. .env file
    3. config.toml file
    4. Built-in defaults (in defaults.py)

Public API:
    load_config()      → Read all sources, return GhanyxConfig.
    get_config()       → Return global config (loads on first call).
    reload_config()    → Reload the global config.
    set_config(cfg)    → Replace global config (mainly for tests).
    reset_config()     → Clear global config (mainly for tests).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from ghanyx.config.base import GhanyxConfig
from ghanyx.config.defaults import ENVIRONMENT_OVERRIDES
from ghanyx.config.exceptions import (
    ConfigFileNotFoundError,
    ConfigParseError,
)

# ============================================================
# TOML reader — stdlib for 3.11+, fallback for 3.10
# ============================================================
if sys.version_info >= (3, 11):
    import tomllib as _toml

    def _load_toml(path: Path) -> dict[str, Any]:
        with path.open("rb") as f:
            return _toml.load(f)
else:
    try:
        import tomli as _toml  # type: ignore[no-redef]

        def _load_toml(path: Path) -> dict[str, Any]:
            with path.open("rb") as f:
                return _toml.load(f)
    except ImportError:
        def _load_toml(path: Path) -> dict[str, Any]:
            raise ConfigParseError(
                str(path),
                "TOML support requires Python 3.11+ or `pip install tomli`",
            )


# ============================================================
# .env reader
# ============================================================
def _load_env_file(path: Path) -> dict[str, str]:
    """
    Load a .env file into a dict.

    Uses python-dotenv if available (it also updates os.environ,
    which we do NOT want here — so we parse manually first).
    """
    if not path.exists():
        return {}

    try:
        from dotenv import dotenv_values
        values = dotenv_values(path)
        return {k: v for k, v in values.items() if v is not None}
    except ImportError:
        # Fallback: simple manual parser
        return _parse_env_simple(path)


def _parse_env_simple(path: Path) -> dict[str, str]:
    """Minimal .env parser (used only if python-dotenv is missing)."""
    result: dict[str, str] = {}
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                result[key] = value
    except OSError as e:
        raise ConfigParseError(str(path), str(e)) from e
    return result


# ============================================================
# ENV var → config key mapping
# ============================================================
# Environment variables use SCREAMING_SNAKE_CASE with a prefix.
# We map them to our dotted keys.
#
# Example: GHANYX_LOG_LEVEL → "logging.level"
#          GHANYX_APP_NAME  → "app.name"
# ============================================================
_ENV_PREFIX = "GHANYX_"

_ENV_KEY_MAP: dict[str, str] = {
    # App
    "GHANYX_APP_NAME": "app.name",
    "GHANYX_ENV": "app.environment",
    "GHANYX_ENVIRONMENT": "app.environment",
    "GHANYX_LANGUAGE": "app.language",
    "GHANYX_TIMEZONE": "app.timezone",

    # Logging
    "GHANYX_LOG_LEVEL": "logging.level",
    "GHANYX_LOG_DIR": "logging.dir",
    "GHANYX_LOG_MAX_BYTES": "logging.max_bytes",
    "GHANYX_LOG_BACKUP_COUNT": "logging.backup_count",
    "GHANYX_LOG_CONSOLE": "logging.console",
    "GHANYX_LOG_COLORS": "logging.colors",

    # Database
    "GHANYX_DB_FILENAME": "database.filename",
    "GHANYX_DB_DIR": "database.dir",

    # UI
    "GHANYX_THEME": "ui.theme",
    "GHANYX_WINDOW_WIDTH": "ui.window_width",
    "GHANYX_WINDOW_HEIGHT": "ui.window_height",

    # Paths
    "GHANYX_DATA_DIR": "paths.data_dir",
    "GHANYX_BACKUPS_DIR": "paths.backups_dir",
    "GHANYX_EXPORTS_DIR": "paths.exports_dir",
}


def _coerce_env_value(raw: str) -> Any:
    """Convert env string to an appropriate Python type."""
    low = raw.strip().lower()

    if low in ("true", "1", "yes", "on"):
        return True
    if low in ("false", "0", "no", "off"):
        return False

    try:
        return int(raw)
    except ValueError:
        pass

    try:
        return float(raw)
    except ValueError:
        pass

    return raw


def _read_env_vars(use_environment: bool) -> dict[str, Any]:
    """Read known GHANYX_* variables from os.environ."""
    if not use_environment:
        return {}

    result: dict[str, Any] = {}
    for env_name, dotted_key in _ENV_KEY_MAP.items():
        if env_name in os.environ:
            raw = os.environ[env_name]
            if raw is not None and raw != "":
                result[dotted_key] = _coerce_env_value(raw)
    return result


def _read_env_file_vars(env_path: Path | None) -> dict[str, Any]:
    """Read known GHANYX_* variables from a .env file."""
    if env_path is None or not env_path.exists():
        return {}

    raw = _load_env_file(env_path)
    result: dict[str, Any] = {}
    for env_name, dotted_key in _ENV_KEY_MAP.items():
        if env_name in raw:
            value = raw[env_name]
            if value is not None and value != "":
                result[dotted_key] = _coerce_env_value(value)
    return result


# ============================================================
# TOML → dotted dict
# ============================================================
def _flatten_toml(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten nested TOML into dotted keys."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten_toml(value, dotted))
        else:
            result[dotted] = value
    return result


def _read_toml_file(toml_path: Path) -> dict[str, Any]:
    """Read a TOML file and return a flat dict."""
    if not toml_path.exists():
        return {}
    try:
        data = _load_toml(toml_path)
    except Exception as e:
        raise ConfigParseError(str(toml_path), str(e)) from e
    return _flatten_toml(data)


# ============================================================
# Unflatten (dotted → nested)
# ============================================================
def _unflatten(flat: dict[str, Any]) -> dict[str, Any]:
    """Convert a dotted dict back to a nested dict."""
    nested: dict[str, Any] = {}
    for dotted_key, value in flat.items():
        parts = dotted_key.split(".")
        current = nested
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    return nested


# ============================================================
# Public API
# ============================================================
def load_config(
    *,
    toml_path: str | os.PathLike[str] | None = None,
    env_path: str | os.PathLike[str] | None = None,
    use_environment: bool = True,
    apply_env_overrides: bool = True,
    validate: bool = True,
) -> GhanyxConfig:
    """
    Load configuration from all sources and merge them.

    Priority (highest first):
        1. Environment variables (os.environ)
        2. .env file
        3. config.toml file
        4. Built-in defaults

    Args:
        toml_path: Path to config.toml. If None, looks for ./config.toml.
        env_path: Path to .env. If None, looks for ./.env.
        use_environment: Read from os.environ.
        apply_env_overrides: Apply environment-specific defaults
            (e.g., DEBUG log level in development).
        validate: Run validation on the final config.

    Returns:
        A validated GhanyxConfig instance.
    """
    project_root = Path.cwd()

    # ---------- Resolve default paths ----------
    if toml_path is None:
        toml_path = project_root / "config.toml"
    else:
        toml_path = Path(toml_path)

    if env_path is None:
        env_path = project_root / ".env"
    else:
        env_path = Path(env_path)

    # ---------- Read each source ----------
    flat: dict[str, Any] = {}

    # Layer 1: TOML (lowest)
    flat.update(_read_toml_file(toml_path))

    # Layer 2: .env
    flat.update(_read_env_file_vars(env_path))

    # Layer 3: os.environ (highest)
    flat.update(_read_env_vars(use_environment))

    # ---------- Environment-specific overrides ----------
    if apply_env_overrides:
        env_name = flat.get("app.environment")
        if env_name and env_name in ENVIRONMENT_OVERRIDES:
            for key, value in ENVIRONMENT_OVERRIDES[env_name].items():
                flat.setdefault(key, value)

    # ---------- Build config ----------
    nested = _unflatten(flat)
    source_parts = []
    if toml_path.exists():
        source_parts.append(str(toml_path))
    if env_path and env_path.exists():
        source_parts.append(str(env_path))
    if use_environment:
        source_parts.append("os.environ")

    return GhanyxConfig(
        data=nested,
        source=" + ".join(source_parts) or "defaults",
        validate=validate,
    )


# ============================================================
# Global singleton
# ============================================================
_global_config: GhanyxConfig | None = None


def get_config() -> GhanyxConfig:
    """
    Return the global config, loading it on first call.

    The global config is cached, so subsequent calls are instant.
    Use `reload_config()` to force a fresh load.
    """
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config


def reload_config(
    *,
    toml_path: str | os.PathLike[str] | None = None,
    env_path: str | os.PathLike[str] | None = None,
) -> GhanyxConfig:
    """Force a fresh load and replace the global config."""
    global _global_config
    _global_config = load_config(toml_path=toml_path, env_path=env_path)
    return _global_config


def set_config(config: GhanyxConfig) -> None:
    """Replace the global config (mainly for tests)."""
    global _global_config
    if not isinstance(config, GhanyxConfig):
        raise TypeError(
            f"set_config expects GhanyxConfig, got {type(config).__name__}"
        )
    _global_config = config


def reset_config() -> None:
    """Clear the global config (mainly for tests)."""
    global _global_config
    _global_config = None