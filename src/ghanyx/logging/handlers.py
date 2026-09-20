"""
Custom log handlers for Ghanyx.

Provides:
    - SafeRotatingFileHandler    → rotating file handler that is
                                    safe on Windows (no rename-while-open).
    - make_console_handler(...)  → configured StreamHandler.
    - make_file_handler(...)     → configured rotating file handler.
    - make_error_file_handler()  → separate file for ERROR+ only.

Why a custom rotating handler?
    Python's built-in RotatingFileHandler fails on Windows when the
    log file is open by another process (antivirus, editor, etc.).
    SafeRotatingFileHandler catches that and retries on next emit.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

from ghanyx.logging.formatters import (
    ConsoleFormatter,
    FileFormatter,
)


# ============================================================
# Safe Rotating File Handler (Windows-friendly)
# ============================================================
class SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    RotatingFileHandler that does not crash when rotation fails
    (e.g., on Windows when another process holds the file open).

    On failure, it logs the problem to stderr and keeps writing
    to the current file until rotation succeeds next time.
    """

    def doRollover(self) -> None:
        try:
            super().doRollover()
        except (PermissionError, OSError) as e:
            # Can't rotate right now — write a warning and continue.
            print(
                f"[ghanyx.logging] Could not rotate log file "
                f"'{self.baseFilename}': {e}",
                file=sys.stderr,
            )


# ============================================================
# Factory functions
# ============================================================
def make_console_handler(
    level: int = logging.INFO,
    use_colors: bool = True,
) -> logging.Handler:
    """
    Build a StreamHandler that writes to stderr with colors.

    Args:
        level: Minimum level to emit (default: INFO).
        use_colors: Whether to use ANSI colors.

    Returns:
        Configured StreamHandler.
    """
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(ConsoleFormatter(use_colors=use_colors))
    return handler


def make_file_handler(
    log_file: str | os.PathLike[str],
    level: int = logging.DEBUG,
    max_bytes: int = 5 * 1024 * 1024,   # 5 MB
    backup_count: int = 5,
    encoding: str = "utf-8",
) -> logging.Handler:
    """
    Build a SafeRotatingFileHandler.

    Args:
        log_file: Path to the log file.
        level: Minimum level to emit (default: DEBUG — capture everything).
        max_bytes: Rotate after this many bytes (default: 5 MB).
        backup_count: How many rotated files to keep (default: 5).
        encoding: File encoding (default: utf-8 — supports Arabic).

    Returns:
        Configured SafeRotatingFileHandler.
    """
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    handler = SafeRotatingFileHandler(
        filename=str(path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding,
        delay=True,   # don't create the file until first record
    )
    handler.setLevel(level)
    handler.setFormatter(FileFormatter())
    return handler


def make_error_file_handler(
    error_file: str | os.PathLike[str],
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 5,
    encoding: str = "utf-8",
) -> logging.Handler:
    """
    Build a SafeRotatingFileHandler that only receives ERROR+ records.

    Useful for keeping a separate, smaller file with only problems,
    so you can find issues quickly without digging through debug spam.

    Args:
        error_file: Path to the error log file.
        max_bytes: Rotate after this many bytes.
        backup_count: How many rotated files to keep.
        encoding: File encoding.

    Returns:
        Configured SafeRotatingFileHandler (level=ERROR).
    """
    handler = make_file_handler(
        log_file=error_file,
        level=logging.ERROR,
        max_bytes=max_bytes,
        backup_count=backup_count,
        encoding=encoding,
    )
    return handler