"""
Configuration-specific exceptions.

These inherit from GhanyxError, so callers can catch either:
    - ConfigError   → for config-specific handling
    - GhanyxError   → for generic framework handling

Usage:
    from ghanyx.config.exceptions import ConfigError

    try:
        config = load_config()
    except ConfigError as e:
        logger.error("Bad configuration: %s", e)
"""

from __future__ import annotations

from ghanyx.errors import ConfigError


# ============================================================
# Base (re-export for clarity)
# ============================================================
# ConfigError is defined in ghanyx.errors, but we re-export
# it here so users can import from either place:
#
#     from ghanyx.errors import ConfigError
#     from ghanyx.config.exceptions import ConfigError
#
__all__ = [
    "ConfigError",
    "ConfigFileNotFoundError",
    "ConfigParseError",
    "ConfigValidationError",
    "ConfigMissingKeyError",
    "ConfigTypeError",
]


# ============================================================
# Specific errors
# ============================================================
class ConfigFileNotFoundError(ConfigError):
    """
    Raised when an explicitly requested config file does not exist.

    Note: this is NOT raised when a config file is simply missing
    during the search process — only when the user explicitly
    points to a file that isn't there.
    """

    def __init__(self, path: str, *, details: str = "") -> None:
        super().__init__(
            f"Config file not found: {path}",
            details=details,
        )
        self.path = path


class ConfigParseError(ConfigError):
    """
    Raised when a config file cannot be parsed (bad TOML / bad .env syntax).
    """

    def __init__(self, path: str, reason: str, *, details: str = "") -> None:
        super().__init__(
            f"Failed to parse config file: {path}",
            details=f"{reason}. {details}".strip(),
        )
        self.path = path
        self.reason = reason


class ConfigValidationError(ConfigError):
    """
    Raised when a configuration value fails validation.

    Example:
        log_level = "INVALID"  → not in VALID_LOG_LEVELS
    """

    def __init__(
        self,
        key: str,
        value: object,
        reason: str,
        *,
        details: str = "",
    ) -> None:
        super().__init__(
            f"Invalid value for '{key}': {value!r}",
            details=f"{reason}. {details}".strip(),
            context={"key": key, "value": value},
        )
        self.key = key
        self.value = value
        self.reason = reason


class ConfigMissingKeyError(ConfigError):
    """
    Raised when a required configuration key is missing.

    Note: most keys have defaults, so this is only raised for
    keys explicitly marked as required.
    """

    def __init__(self, key: str, *, details: str = "") -> None:
        super().__init__(
            f"Required config key is missing: '{key}'",
            details=details,
            context={"key": key},
        )
        self.key = key


class ConfigTypeError(ConfigError):
    """
    Raised when a configuration value has the wrong type.

    Example:
        window_width = "wide"  → expected int
    """

    def __init__(
        self,
        key: str,
        expected: type,
        actual: type,
        *,
        details: str = "",
    ) -> None:
        super().__init__(
            f"Wrong type for '{key}': expected {expected.__name__}, "
            f"got {actual.__name__}",
            details=details,
            context={
                "key": key,
                "expected": expected.__name__,
                "actual": actual.__name__,
            },
        )
        self.key = key
        self.expected = expected
        self.actual = actual