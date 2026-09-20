"""
Custom log formatters for Ghanyx.

Provides:
    - ConsoleFormatter  → colored, human-friendly output for terminals.
    - FileFormatter     → detailed, timestamped output for log files.
    - JsonFormatter     → machine-readable output for log aggregation.

All formatters are safe to use with Unicode (Arabic, emoji, etc.).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


# ============================================================
# ANSI color codes (no external dependency)
# ============================================================
class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"


# ============================================================
# Level → color / label mapping
# ============================================================
_LEVEL_COLORS = {
    logging.DEBUG: Colors.CYAN,
    logging.INFO: Colors.BRIGHT_GREEN,
    logging.WARNING: Colors.BRIGHT_YELLOW,
    logging.ERROR: Colors.BRIGHT_RED,
    logging.CRITICAL: Colors.BOLD + Colors.BRIGHT_RED,
}

_LEVEL_LABELS = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO ",
    logging.WARNING: "WARN ",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRIT ",
}


# ============================================================
# Console Formatter — colored output for terminals
# ============================================================
class ConsoleFormatter(logging.Formatter):
    """
    Human-friendly, colored formatter for console output.

    Format:
        12:34:56  INFO   [myapp.module]  Message here
    """

    def __init__(self, use_colors: bool = True) -> None:
        super().__init__()
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        # Timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")

        # Level
        level_label = _LEVEL_LABELS.get(record.levelno, record.levelname)
        level_color = _LEVEL_COLORS.get(record.levelno, "")

        # Logger name (shortened)
        logger_name = record.name
        if len(logger_name) > 30:
            logger_name = "..." + logger_name[-27:]

        # Message
        message = record.getMessage()

        # Exception info (if any)
        exc_text = ""
        if record.exc_info:
            exc_text = "\n" + self.formatException(record.exc_info)

        if self.use_colors:
            return (
                f"{Colors.DIM}{timestamp}{Colors.RESET}  "
                f"{level_color}{level_label}{Colors.RESET}  "
                f"{Colors.DIM}[{logger_name}]{Colors.RESET}  "
                f"{message}{exc_text}"
            )
        else:
            return (
                f"{timestamp}  {level_label}  [{logger_name}]  "
                f"{message}{exc_text}"
            )


# ============================================================
# File Formatter — detailed output for log files
# ============================================================
class FileFormatter(logging.Formatter):
    """
    Detailed, timestamped formatter for log files.

    Format:
        2026-09-21 12:34:56,789 | INFO     | myapp.module:function:42 | Message
    """

    DEFAULT_FORMAT = (
        "%(asctime)s | %(levelname)-8s | "
        "%(name)s:%(funcName)s:%(lineno)d | %(message)s"
    )

    def __init__(self, fmt: str | None = None, datefmt: str | None = None) -> None:
        super().__init__(
            fmt=fmt or self.DEFAULT_FORMAT,
            datefmt=datefmt or "%Y-%m-%d %H:%M:%S",
        )


# ============================================================
# JSON Formatter — machine-readable output
# ============================================================
class JsonFormatter(logging.Formatter):
    """
    Emit each log record as a single-line JSON object.

    Useful for shipping logs to aggregation systems
    (ELK, Loki, CloudWatch, etc.).

    Fields:
        time, level, logger, message, module, function, line,
        exception (optional), extra (optional)
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include exception traceback if present
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Include any custom fields the caller attached
        # (e.g., logger.info("...", extra={"user_id": 42}))
        reserved = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "asctime", "taskName",
        }
        extra = {
            k: v for k, v in record.__dict__.items()
            if k not in reserved and not k.startswith("_")
        }
        if extra:
            payload["extra"] = extra

        return json.dumps(payload, ensure_ascii=False, default=str)