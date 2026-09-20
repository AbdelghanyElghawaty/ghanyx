"""
Tests for ghanyx.logging.

Coverage:
    - setup_logging is idempotent
    - get_logger namespacing
    - Console / File / JSON formatters
    - File creation and rotation basics
    - shutdown_logging cleans handlers
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from ghanyx.logging import (
    setup_logging,
    get_logger,
    shutdown_logging,
    is_configured,
)
from ghanyx.logging.formatters import (
    ConsoleFormatter,
    FileFormatter,
    JsonFormatter,
)


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture(autouse=True)
def clean_logging():
    """Ensure clean logging state before and after each test."""
    shutdown_logging()
    yield
    shutdown_logging()


@pytest.fixture
def tmp_logs(tmp_path: Path) -> Path:
    """A temporary directory for log files."""
    d = tmp_path / "logs"
    d.mkdir()
    return d


# ============================================================
# Helper
# ============================================================
def _ghanyx_handlers(logger: logging.Logger) -> list:
    """Return only handlers that were added by Ghanyx."""
    return [
        h for h in logger.handlers
        if getattr(h, "_ghanyx_handler", False)
    ]


# ============================================================
# setup_logging
# ============================================================
class TestSetupLogging:
    def test_returns_logger(self, tmp_logs: Path):
        root = setup_logging(app_name="testapp", log_dir=tmp_logs)
        assert isinstance(root, logging.Logger)
        assert is_configured() is True

    def test_is_idempotent(self, tmp_logs: Path):
        setup_logging(app_name="testapp", log_dir=tmp_logs)
        root = logging.getLogger("ghanyx")
        count_after_first = len(_ghanyx_handlers(root))

        setup_logging(app_name="testapp", log_dir=tmp_logs)
        count_after_second = len(_ghanyx_handlers(root))

        assert count_after_first == count_after_second

    def test_force_reconfigures(self, tmp_logs: Path):
        setup_logging(app_name="testapp", log_dir=tmp_logs)
        root = logging.getLogger("ghanyx")
        first_count = len(_ghanyx_handlers(root))

        setup_logging(app_name="testapp", log_dir=tmp_logs, force=True)
        second_count = len(_ghanyx_handlers(root))

        assert first_count == second_count

    def test_creates_log_file(self, tmp_logs: Path):
        setup_logging(app_name="testapp", log_dir=tmp_logs)
        logger = get_logger("test")

        logger.info("hello world")
        for h in logging.getLogger("ghanyx").handlers:
            h.flush()

        log_file = tmp_logs / "testapp.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "hello world" in content

    def test_error_file_created(self, tmp_logs: Path):
        setup_logging(app_name="testapp", log_dir=tmp_logs)
        logger = get_logger("test")

        logger.error("something bad")
        for h in logging.getLogger("ghanyx").handlers:
            h.flush()

        err_file = tmp_logs / "testapp.error.log"
        assert err_file.exists()
        content = err_file.read_text(encoding="utf-8")
        assert "something bad" in content

    def test_never_raises_on_bad_input(self):
        # Passing a bad log_dir should not crash.
        root = setup_logging(app_name="testapp", log_dir="\x00bad")
        assert isinstance(root, logging.Logger)

    def test_arabic_log_message(self, tmp_logs: Path):
        setup_logging(app_name="testapp", log_dir=tmp_logs)
        logger = get_logger("test")

        logger.info("مرحباً بالعالم")
        for h in logging.getLogger("ghanyx").handlers:
            h.flush()

        content = (tmp_logs / "testapp.log").read_text(encoding="utf-8")
        assert "مرحباً بالعالم" in content


# ============================================================
# get_logger
# ============================================================
class TestGetLogger:
    def test_namespace_prefix(self):
        logger = get_logger("mymodule")
        assert logger.name == "ghanyx.mymodule"

    def test_no_double_prefix(self):
        logger = get_logger("ghanyx.mymodule")
        assert logger.name == "ghanyx.mymodule"

    def test_none_returns_root(self):
        logger = get_logger(None)
        assert logger.name == "ghanyx"

    def test_root_name_returns_root(self):
        logger = get_logger("ghanyx")
        assert logger.name == "ghanyx"


# ============================================================
# shutdown_logging
# ============================================================
class TestShutdown:
    def test_cleans_handlers(self, tmp_logs: Path):
        setup_logging(app_name="testapp", log_dir=tmp_logs)
        root = logging.getLogger("ghanyx")

        # Only our own handlers
        assert len(_ghanyx_handlers(root)) > 0

        shutdown_logging()

        # All Ghanyx handlers should be gone
        assert len(_ghanyx_handlers(root)) == 0
        assert is_configured() is False

    def test_can_call_multiple_times(self):
        shutdown_logging()
        shutdown_logging()
        shutdown_logging()


# ============================================================
# Formatters
# ============================================================
class TestFormatters:
    def _make_record(self, level: int = logging.INFO, msg: str = "test"):
        return logging.LogRecord(
            name="ghanyx.test",
            level=level,
            pathname=__file__,
            lineno=42,
            msg=msg,
            args=(),
            exc_info=None,
        )

    def test_console_formatter_basic(self):
        fmt = ConsoleFormatter(use_colors=False)
        record = self._make_record()
        output = fmt.format(record)
        assert "INFO" in output
        assert "test" in output

    def test_console_formatter_colors(self):
        fmt = ConsoleFormatter(use_colors=True)
        record = self._make_record()
        output = fmt.format(record)
        assert "\033[" in output  # ANSI escape code present

    def test_file_formatter(self):
        fmt = FileFormatter()
        record = self._make_record()
        output = fmt.format(record)
        assert "INFO" in output
        assert "test" in output
        assert "42" in output  # line number

    def test_json_formatter_structure(self):
        fmt = JsonFormatter()
        record = self._make_record(msg="hello")
        output = fmt.format(record)

        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["message"] == "hello"
        assert data["logger"] == "ghanyx.test"
        assert data["line"] == 42

    def test_json_formatter_arabic(self):
        fmt = JsonFormatter()
        record = self._make_record(msg="مرحباً")
        output = fmt.format(record)

        data = json.loads(output)
        assert data["message"] == "مرحباً"