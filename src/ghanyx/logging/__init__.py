"""
Ghanyx logging — unified, production-ready logging system.

Public API:
    setup_logging(...)   → Configure logging for the whole app.
    get_logger(name)     → Get a logger instance (recommended over logging.getLogger).
    shutdown_logging()   → Flush and close all handlers (call on app exit).

Quick start:
    from ghanyx.logging import setup_logging, get_logger

    setup_logging(app_name="myapp", log_dir="logs")
    logger = get_logger(__name__)

    logger.info("App started")
    logger.error("Something went wrong", exc_info=True)
"""

from ghanyx.logging.setup import (
    setup_logging,
    get_logger,
    shutdown_logging,
    is_configured,
)

__all__ = [
    "setup_logging",
    "get_logger",
    "shutdown_logging",
    "is_configured",
]