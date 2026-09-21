"""
GhanyxConfig — the core configuration container.

This class is responsible for:
    - Holding configuration data in a nested dict.
    - Providing safe, typed access to values.
    - Validating values against known rules.
    - Supporting both property access (config.log_level) and
      dynamic access (config.get("logging.level")).

Design principles:
    - Immutable after construction (no surprise mutations).
    - Fail loud, fail early: invalid values raise immediately.
    - Sensible defaults: every known key has a fallback.
    - Dot-notation for nesting: "logging.level" → config["logging"]["level"].
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Iterator

from ghanyx.config.defaults import (
    DEFAULTS,
    VALID_ENVIRONMENTS,
    VALID_LANGUAGES,
    VALID_LOG_LEVELS,
    VALID_THEMES,
)
from ghanyx.config.exceptions import (
    ConfigMissingKeyError,
    ConfigTypeError,
    ConfigValidationError,
)


# ============================================================
# GhanyxConfig
# ============================================================
class GhanyxConfig:
    """
    Holds the merged configuration for an application.

    Construction:
        data = {"app": {"name": "myapp"}, "logging": {"level": "DEBUG"}}
        config = GhanyxConfig(data, source="config.toml")

    Access:
        config.app_name                       # → "myapp"
        config.log_level                      # → "DEBUG"
        config.get("app.name")                # → "myapp"
        config.get("missing.key", default=42) # → 42
        config["app.name"]                    # → "myapp"  (dict-style)
    """

    # Keys that MUST be present after loading (no defaults).
    REQUIRED_KEYS: tuple[str, ...] = ()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def __init__(
        self,
        data: dict[str, Any] | None = None,
        *,
        source: str = "",
        validate: bool = True,
    ) -> None:
        """
        Initialize the config.

        Args:
            data: Nested dict of configuration values.
            source: Human-readable source description (for debugging).
            validate: Whether to validate values immediately.

        Raises:
            ConfigValidationError: if any value fails validation.
            ConfigMissingKeyError: if any required key is missing.
        """
        merged = self._merge_with_defaults(data or {})
        self._data: dict[str, Any] = merged
        self._source: str = source
        self._validated: bool = False

        if validate:
            self._validate()

    # ------------------------------------------------------------------
    # Merging
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_with_defaults(user_data: dict[str, Any]) -> dict[str, Any]:
        """
        Merge user data with the built-in defaults.

        Rule: user_data wins, but any missing leaf falls back to the
        default (if one exists).
        """
        result: dict[str, Any] = {}

        for dotted_key, default_value in DEFAULTS.items():
            value = _get_nested(user_data, dotted_key, _MISSING)
            if value is _MISSING:
                _set_nested(result, dotted_key, default_value)
            else:
                _set_nested(result, dotted_key, value)

        # Also copy any extra keys the user provided that aren't in DEFAULTS
        for key, value in user_data.items():
            if key not in result:
                result[key] = value

        return result

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate(self) -> None:
        """Run all validation rules. Raises on first failure."""
        # Required keys
        for key in self.REQUIRED_KEYS:
            if self.get(key, default=None) is None:
                raise ConfigMissingKeyError(key)

        # Environment
        env = self.get("app.environment", default="development")
        if env not in VALID_ENVIRONMENTS:
            raise ConfigValidationError(
                "app.environment",
                env,
                f"must be one of {VALID_ENVIRONMENTS}",
            )

        # Language
        lang = self.get("app.language", default="ar")
        if lang not in VALID_LANGUAGES:
            raise ConfigValidationError(
                "app.language",
                lang,
                f"must be one of {VALID_LANGUAGES}",
            )

        # Log level
        level = str(self.get("logging.level", default="INFO")).upper()
        if level not in VALID_LOG_LEVELS:
            raise ConfigValidationError(
                "logging.level",
                level,
                f"must be one of {VALID_LOG_LEVELS}",
            )

        # Theme
        theme = self.get("ui.theme", default="dark")
        if theme not in VALID_THEMES:
            raise ConfigValidationError(
                "ui.theme",
                theme,
                f"must be one of {VALID_THEMES}",
            )

        # Numeric bounds
        self._check_positive_int("logging.max_bytes")
        self._check_positive_int("logging.backup_count")
        self._check_positive_int("ui.window_width")
        self._check_positive_int("ui.window_height")

        self._validated = True

    def _check_positive_int(self, key: str) -> None:
        value = self.get(key, default=None)
        if value is None:
            return
        if not isinstance(value, int):
            raise ConfigTypeError(key, int, type(value))
        if value <= 0:
            raise ConfigValidationError(key, value, "must be > 0")

    # ------------------------------------------------------------------
    # Core access
    # ------------------------------------------------------------------
    def get(
        self,
        key: str,
        default: Any = None,
        *,
        required: bool = False,
    ) -> Any:
        """
        Retrieve a value by dot-notation key.

        Args:
            key: Dotted key (e.g., "logging.level").
            default: Value to return if the key is missing.
            required: If True and the key is missing, raise.

        Returns:
            The value, or `default` if missing.

        Raises:
            ConfigMissingKeyError: if required=True and key is missing.
        """
        value = _get_nested(self._data, key, _MISSING)
        if value is _MISSING:
            if required:
                raise ConfigMissingKeyError(key)
            return default
        return value

    def get_typed(
        self,
        key: str,
        expected_type: type,
        default: Any = None,
        *,
        required: bool = False,
    ) -> Any:
        """
        Retrieve a value and enforce its type.

        Args:
            key: Dotted key.
            expected_type: Type to enforce (int, str, bool, etc.).
            default: Default if missing.
            required: Raise if missing.

        Raises:
            ConfigMissingKeyError: if required and missing.
            ConfigTypeError: if value has wrong type.
        """
        value = self.get(key, default=default, required=required)
        if value is None and default is None:
            return None
        if not isinstance(value, expected_type):
            raise ConfigTypeError(key, expected_type, type(value))
        return value

    def __getitem__(self, key: str) -> Any:
        """Support dict-style access: config["app.name"]."""
        value = _get_nested(self._data, key, _MISSING)
        if value is _MISSING:
            raise KeyError(key)
        return value

    def __contains__(self, key: str) -> bool:
        """Support `"app.name" in config`."""
        return _get_nested(self._data, key, _MISSING) is not _MISSING

    def __iter__(self) -> Iterator[str]:
        """Iterate over top-level keys."""
        return iter(self._data.keys())

    # ------------------------------------------------------------------
    # Mutation (deliberately limited)
    # ------------------------------------------------------------------
    def set(self, key: str, value: Any) -> None:
        """
        Set a value by dot-notation key.

        Note: mutation is allowed but discouraged. Prefer
        constructing a new config via load_config() instead.
        """
        _set_nested(self._data, key, value)

    def to_dict(self, *, deep: bool = True) -> dict[str, Any]:
        """Return a copy of the underlying data."""
        return copy.deepcopy(self._data) if deep else dict(self._data)

    # ------------------------------------------------------------------
    # Properties — App
    # ------------------------------------------------------------------
    @property
    def app_name(self) -> str:
        return str(self.get("app.name", default="ghanyx"))

    @property
    def environment(self) -> str:
        return str(self.get("app.environment", default="development"))

    @property
    def language(self) -> str:
        return str(self.get("app.language", default="ar"))

    @property
    def timezone(self) -> str:
        return str(self.get("app.timezone", default="Africa/Cairo"))

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_staging(self) -> bool:
        return self.environment == "staging"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_debug(self) -> bool:
        """True in development, False otherwise."""
        return self.is_development

    # ------------------------------------------------------------------
    # Properties — Logging
    # ------------------------------------------------------------------
    @property
    def log_level(self) -> str:
        return str(self.get("logging.level", default="INFO")).upper()

    @property
    def log_dir(self) -> Path:
        return Path(str(self.get("logging.dir", default="logs")))

    @property
    def log_max_bytes(self) -> int:
        return int(self.get("logging.max_bytes", default=5 * 1024 * 1024))

    @property
    def log_backup_count(self) -> int:
        return int(self.get("logging.backup_count", default=5))

    @property
    def log_console(self) -> bool:
        return bool(self.get("logging.console", default=True))

    @property
    def log_colors(self) -> bool:
        return bool(self.get("logging.colors", default=True))

    # ------------------------------------------------------------------
    # Properties — Database
    # ------------------------------------------------------------------
    @property
    def db_filename(self) -> str:
        return str(self.get("database.filename", default="data.db"))

    @property
    def db_dir(self) -> Path:
        return Path(str(self.get("database.dir", default="data")))

    @property
    def db_path(self) -> Path:
        """Full path to the database file."""
        return self.db_dir / self.db_filename

    # ------------------------------------------------------------------
    # Properties — UI
    # ------------------------------------------------------------------
    @property
    def theme(self) -> str:
        return str(self.get("ui.theme", default="dark"))

    @property
    def window_width(self) -> int:
        return int(self.get("ui.window_width", default=1400))

    @property
    def window_height(self) -> int:
        return int(self.get("ui.window_height", default=850))

    # ------------------------------------------------------------------
    # Properties — Paths
    # ------------------------------------------------------------------
    @property
    def data_dir(self) -> Path:
        return Path(str(self.get("paths.data_dir", default="data")))

    @property
    def backups_dir(self) -> Path:
        return Path(str(self.get("paths.backups_dir", default="backups")))

    @property
    def exports_dir(self) -> Path:
        return Path(self.get("paths.exports_dir", default="exports"))

    # ------------------------------------------------------------------
    # Debug / repr
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"GhanyxConfig(env={self.environment!r}, "
            f"app={self.app_name!r}, "
            f"source={self._source!r})"
        )

    def describe(self) -> str:
        """Return a human-readable summary of the config."""
        lines = [
            f"GhanyxConfig (source: {self._source or 'defaults'})",
            f"  app.name         = {self.app_name}",
            f"  app.environment  = {self.environment}",
            f"  app.language     = {self.language}",
            f"  logging.level    = {self.log_level}",
            f"  logging.dir      = {self.log_dir}",
            f"  database.path    = {self.db_path}",
            f"  ui.theme         = {self.theme}",
        ]
        return "\n".join(lines)


# ============================================================
# Internal helpers — nested dict access
# ============================================================
_MISSING = object()


def _get_nested(data: dict[str, Any], dotted_key: str, default: Any) -> Any:
    """
    Retrieve a value from a nested dict using dot-notation.

    _get_nested({"a": {"b": 1}}, "a.b")  →  1
    _get_nested({"a": {}}, "a.b", "x")   →  "x"
    """
    parts = dotted_key.split(".")
    current: Any = data

    for part in parts:
        if not isinstance(current, dict):
            return default
        if part not in current:
            return default
        current = current[part]

    return current


def _set_nested(data: dict[str, Any], dotted_key: str, value: Any) -> None:
    """
    Set a value in a nested dict using dot-notation, creating
    intermediate dicts as needed.

    _set_nested({}, "a.b", 1)  →  {"a": {"b": 1}}
    """
    parts = dotted_key.split(".")
    current = data

    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]

    current[parts[-1]] = value