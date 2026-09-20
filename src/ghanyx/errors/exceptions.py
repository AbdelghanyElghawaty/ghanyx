"""
Ghanyx custom exceptions.

All exceptions in this module inherit from `GhanyxError`, so callers
can catch a single base class to handle any framework-related error.

Design principles:
    - Every error carries a `message` and optional `details`.
    - Specific subclasses exist for common failure modes.
    - No exception should be silently swallowed; log it.
"""

from __future__ import annotations

from typing import Any


# ============================================================
# Base
# ============================================================
class GhanyxError(Exception):
    """
    Base exception for all Ghanyx errors.

    Attributes:
        message: Short human-readable error message.
        details: Optional additional context (e.g., which file, which record).
        context: Optional dict with extra structured data.
    """

    def __init__(
        self,
        message: str = "Ghanyx error",
        *,
        details: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        self.context = context or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} — {self.details}"
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation (useful for logging)."""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "context": self.context,
        }


# ============================================================
# Configuration
# ============================================================
class ConfigError(GhanyxError):
    """Raised when configuration is missing, malformed, or invalid."""


# ============================================================
# Database
# ============================================================
class DatabaseError(GhanyxError):
    """Raised when a database operation fails."""


class NotFoundError(DatabaseError):
    """Raised when a requested record does not exist."""


class DuplicateError(DatabaseError):
    """Raised when trying to insert a record that violates a unique constraint."""


class IntegrityError(DatabaseError):
    """Raised when a foreign key or integrity constraint is violated."""


# ============================================================
# Logging
# ============================================================
class LoggingError(GhanyxError):
    """Raised when logging setup or a logging operation fails."""


# ============================================================
# Validation
# ============================================================
class ValidationError(GhanyxError):
    """Raised when user input or domain data fails validation."""


# ============================================================
# Permissions / Auth
# ============================================================
class AuthenticationError(GhanyxError):
    """Raised when authentication fails (wrong credentials, etc.)."""


class PermissionDeniedError(GhanyxError):
    """Raised when a user lacks the required permission for an action."""


# ============================================================
# License
# ============================================================
class LicenseError(GhanyxError):
    """Base class for license-related errors."""


class LicenseExpiredError(LicenseError):
    """Raised when the license has expired."""


class LicenseInvalidError(LicenseError):
    """Raised when the license signature is invalid or tampered with."""


class LicenseDeviceMismatchError(LicenseError):
    """Raised when the license was issued for a different device."""