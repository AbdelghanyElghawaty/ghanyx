"""
Ghanyx logging — core setup and configuration.

This module is the single entry point for configuring logging
across an entire application.

Design goals:
    - One call to configure everything: `setup_logging(...)`.
    - Safe by default: never crash on logging errors.
    - Windows-friendly: uses SafeRotatingFileHandler.
    - Unicode-safe: handles Arabic, emoji, etc.
    - Never duplicates handlers on repeated calls (idempotent).
    - Provides `get_logger()` that returns a properly namespaced logger.

Typical usage:
    from ghanyx.logging import setup_logging, get_logger, shutdown_logging

    setup_logging(app_name="myapp", log_dir="logs")
    logger = get_logger(__name__)
    logger.info("Hello")
    ...
    shutdown_logging()   # at app exit
"""

from __future__ import annotations

import atexit
import logging
import os
import sys
from pathlib import Path
from typing import Final

from ghanyx.logging.handlers import (
    make_console_handler,
    make_error_file_handler,
    make_file_handler,
)

# ============================================================
# Constants
# ============================================================
ROOT_LOGGER_NAME: Final[str] = "ghanyx"

DEFAULT_LOG_FORMAT: Final[str] = (
    "%(asctime)s | %(levelname)-8s | "
    "%(name)s:%(funcName)s:%(lineno)d | %(message)s"
)

#: Marker attribute we set on handlers we create,
#: so we can safely remove only OUR handlers on re-setup.
_GHANYX_HANDLER_FLAG: Final[str] = "_ghanyx_handler"


# ============================================================
# Internal state
# ============================================================
_configured: bool = False
_log_file_path: Path | None = None
_error_file_path: Path | None = None


# ============================================================
# Public API
# ============================================================
def setup_logging(
    app_name: str = "app",
    *,
    log_dir: str | os.PathLike[str] = "logs",
    level: int | str = logging.INFO,
    console: bool = True,
    console_colors: bool = True,
    file_logging: bool = True,
    error_file: bool = True,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
    capture_warnings: bool = True,
    force: bool = False,
) -> logging.Logger:
    """
    Configure the Ghanyx root logger and its handlers.

    This function is idempotent: calling it multiple times will not
    add duplicate handlers. Pass `force=True` to reconfigure from scratch.

    Args:
        app_name: Name used for log file naming (e.g., "myapp").
        log_dir: Directory where log files will be written.
        level: Minimum level for the root logger (name or int).
        console: Enable colored console output.
        console_colors: Use ANSI colors (ignored if console=False).
        file_logging: Enable writing to a rotating log file.
        error_file: Additionally write ERROR+ to a separate file.
        max_bytes: Rotate each log file after this size.
        backup_count: Number of rotated files to keep.
        capture_warnings: Route `warnings.warn()` through logging.
        force: If True, remove existing handlers and reconfigure.

    Returns:
        The configured root logger.

    Raises:
        None — this function never raises. On failure it prints to stderr.
    """
    global _configured, _log_file_path, _error_file_path

    try:
        # ---------- 1. Normalize level ----------
        numeric_level = _coerce_level(level)

        # ---------- 2. Get / create root logger ----------
        root = logging.getLogger(ROOT_LOGGER_NAME)
        root.setLevel(numeric_level)
        root.propagate = False  # don't bubble up to Python's root

        # ---------- 3. Idempotency ----------
        if _configured and not force:
            return root

        if force:
            _remove_ghanyx_handlers(root)

        # ---------- 4. Console handler ----------
        if console:
            root.addHandler(
                _tag(make_console_handler(
                    level=numeric_level,
                    use_colors=console_colors,
                ))
            )

        # ---------- 5. File handlers ----------
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)

        if file_logging:
            _log_file_path = log_dir_path / f"{app_name}.log"
            root.addHandler(
                _tag(make_file_handler(
                    log_file=_log_file_path,
                    level=logging.DEBUG,
                    max_bytes=max_bytes,
                    backup_count=backup_count,
                ))
            )

        if file_logging and error_file:
            _error_file_path = log_dir_path / f"{app_name}.error.log"
            root.addHandler(
                _tag(make_error_file_handler(
                    error_file=_error_file_path,
                    max_bytes=max_bytes,
                    backup_count=backup_count,
                ))
            )

        # ---------- 6. Capture warnings ----------
        if capture_warnings:
            logging.captureWarnings(True)

        # ---------- 7. Register cleanup ----------
        atexit.register(shutdown_logging)

        _configured = True
        root.debug(
            "Logging configured — app=%s level=%s log_dir=%s",
            app_name, logging.getLevelName(numeric_level), log_dir_path,
        )
        return root

    except Exception as e:  # never crash the app because of logging
        print(
            f"[ghanyx.logging] Failed to configure logging: {e}",
            file=sys.stderr,
        )
        return logging.getLogger(ROOT_LOGGER_NAME)


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Return a logger namespaced under the Ghanyx root.

    Use this instead of `logging.getLogger(__name__)` so that all
    logs flow through the configured root.

    Args:
        name: Usually `__name__`. If None, returns the root logger.

    Returns:
        A logging.Logger instance.
    """
    if not name:
        return logging.getLogger(ROOT_LOGGER_NAME)

    # Prevent double-prefixing: ghanyx.ghanyx.foo
    if name.startswith(ROOT_LOGGER_NAME + "."):
        return logging.getLogger(name)
    if name == ROOT_LOGGER_NAME:
        return logging.getLogger(name)

    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")


def shutdown_logging() -> None:
    """
    Flush and close all Ghanyx handlers.

    Safe to call multiple times. Called automatically at process exit.
    """
    global _configured

    try:
        root = logging.getLogger(ROOT_LOGGER_NAME)
        for handler in list(root.handlers):
            if getattr(handler, _GHANYX_HANDLER_FLAG, False):
                try:
                    handler.flush()
                    handler.close()
                except Exception:
                    pass
                root.removeHandler(handler)
        _configured = False
    except Exception:
        pass


def is_configured() -> bool:
    """Return True if setup_logging() has been called successfully."""
    return _configured


def get_log_file_path() -> Path | None:
    """Return the path to the main log file, if file logging is enabled."""
    return _log_file_path


def get_error_log_file_path() -> Path | None:
    """Return the path to the error log file, if enabled."""
    return _error_file_path


# ============================================================
# Internal helpers
# ============================================================
def _coerce_level(level: int | str) -> int:
    """Accept either an int or a level name string."""
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        value = logging.getLevelName(level.upper())
        if isinstance(value, int):
            return value
    return logging.INFO


def _tag(handler: logging.Handler) -> logging.Handler:
    """Mark a handler as owned by Ghanyx."""
    setattr(handler, _GHANYX_HANDLER_FLAG, True)
    return handler


def _remove_ghanyx_handlers(logger: logging.Logger) -> None:
    """Remove only handlers created by Ghanyx."""
    for handler in list(logger.handlers):
        if getattr(handler, _GHANYX_HANDLER_FLAG, False):
            try:
                handler.close()
            except Exception:
                pass
            logger.removeHandler(handler)