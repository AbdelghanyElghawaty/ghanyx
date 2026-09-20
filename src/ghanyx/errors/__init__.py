"""
Ghanyx exceptions — unified error hierarchy.

Every custom exception in the framework inherits from `GhanyxError`,
so consumers can catch a single base class to handle any framework
error gracefully.

Example:
    from ghanyx.errors import GhanyxError

    try:
        do_something()
    except GhanyxError as e:
        logger.error("Framework error: %s", e)
"""

from ghanyx.errors.exceptions import (
    # Base
    GhanyxError,

    # Configuration
    ConfigError,

    # Database
    DatabaseError,
    NotFoundError,
    DuplicateError,
    IntegrityError,

    # Logging
    LoggingError,

    # Validation
    ValidationError,

    # Permissions
    PermissionDeniedError,
    AuthenticationError,

    # License
    LicenseError,
    LicenseExpiredError,
    LicenseInvalidError,
    LicenseDeviceMismatchError,
)

__all__ = [
    # Base
    "GhanyxError",

    # Configuration
    "ConfigError",

    # Database
    "DatabaseError",
    "NotFoundError",
    "DuplicateError",
    "IntegrityError",

    # Logging
    "LoggingError",

    # Validation
    "ValidationError",

    # Permissions
    "PermissionDeniedError",
    "AuthenticationError",

    # License
    "LicenseError",
    "LicenseExpiredError",
    "LicenseInvalidError",
    "LicenseDeviceMismatchError",
]