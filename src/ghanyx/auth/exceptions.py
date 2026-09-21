"""
Authentication & authorization exceptions for Ghanyx.

All inherit from AuthError (which inherits from GhanyxError),
so callers can catch at the right level:

    try:
        auth.login("ali", "wrong")
    except InvalidCredentialsError:
        show_error("Wrong password")
    except AuthError:
        show_error("Auth failed")
    except GhanyxError:
        show_error("Framework error")

Design:
    - Every error carries enough context to debug safely.
    - Messages never leak sensitive info (e.g., we say "invalid
      credentials", not "user exists but password is wrong").
"""

from __future__ import annotations

from ghanyx.errors import GhanyxError


# ============================================================
# Base
# ============================================================
class AuthError(GhanyxError):
    """Base exception for all authentication/authorization errors."""


# ============================================================
# Login / registration
# ============================================================
class AuthenticationError(AuthError):
    """
    Base class for authentication failures.

    Note: message is intentionally generic to avoid leaking
    whether a username exists.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        username: str = "",
        details: str = "",
    ) -> None:
        super().__init__(
            message,
            details=details,
            context={"username": username} if username else {},
        )
        self.username = username


class InvalidCredentialsError(AuthenticationError):
    """
    Raised when username/password combination is wrong.

    Message is intentionally generic — we do NOT reveal whether
    the username exists. This prevents user enumeration attacks.
    """

    def __init__(self, *, username: str = "") -> None:
        super().__init__(
            "Invalid username or password",
            username=username,
        )


class AccountLockedError(AuthenticationError):
    """Raised when an account is locked due to too many failed attempts."""

    def __init__(
        self,
        *,
        username: str = "",
        unlock_after_seconds: int = 0,
    ) -> None:
        message = "Account is temporarily locked"
        if unlock_after_seconds > 0:
            minutes = max(1, unlock_after_seconds // 60)
            message += f" — try again in ~{minutes} minute(s)"

        super().__init__(message, username=username)
        self.unlock_after_seconds = unlock_after_seconds


class AccountDisabledError(AuthenticationError):
    """Raised when the account exists but is disabled."""

    def __init__(self, *, username: str = "") -> None:
        super().__init__(
            "Account is disabled",
            username=username,
        )


class UserAlreadyExistsError(AuthError):
    """Raised when registering a username that already exists."""

    def __init__(self, username: str = "") -> None:
        super().__init__(
            f"User '{username}' already exists" if username
            else "User already exists",
            context={"username": username} if username else {},
        )
        self.username = username


class UserNotFoundError(AuthError):
    """Raised when a user is not found."""

    def __init__(self, username: str = "") -> None:
        super().__init__(
            f"User not found: '{username}'" if username
            else "User not found",
            context={"username": username} if username else {},
        )
        self.username = username


# ============================================================
# Validation
# ============================================================
class UsernameValidationError(AuthError):
    """Raised when a username fails validation rules."""

    def __init__(self, reason: str, *, username: str = "") -> None:
        super().__init__(
            f"Invalid username: {reason}",
            context={"username": username} if username else {},
        )
        self.reason = reason
        self.username = username


class PasswordValidationError(AuthError):
    """Raised when a password fails strength requirements."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid password: {reason}")
        self.reason = reason


# ============================================================
# Permissions
# ============================================================
class PermissionDeniedError(AuthError):
    """Raised when a user attempts an action they are not permitted to do."""

    def __init__(
        self,
        permission: str = "",
        *,
        username: str = "",
    ) -> None:
        message = (
            f"Permission denied: '{permission}'"
            if permission else "Permission denied"
        )
        super().__init__(
            message,
            context={
                "permission": permission,
                "username": username,
            },
        )
        self.permission = permission
        self.username = username


# ============================================================
# Sessions
# ============================================================
class SessionError(AuthError):
    """Base class for session-related errors."""


class SessionExpiredError(SessionError):
    """Raised when a session token has expired."""

    def __init__(self, *, session_id: str = "") -> None:
        super().__init__(
            "Session has expired",
            context={"session_id": session_id} if session_id else {},
        )
        self.session_id = session_id


class InvalidSessionError(SessionError):
    """Raised when a session token is malformed or tampered with."""

    def __init__(self, *, session_id: str = "") -> None:
        super().__init__(
            "Invalid session",
            context={"session_id": session_id} if session_id else {},
        )
        self.session_id = session_id