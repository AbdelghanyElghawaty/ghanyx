"""
Ghanyx auth — authentication, permissions, and sessions.

Public API:
    # User & Permissions
    User                → Authenticated user domain object.
    Permission          → Enum of built-in permissions.
    PermissionSet       → Set of granted permissions.
    PermissionRegistry  → Registry of known permissions.
    PRESETS             → Built-in role presets.
    get_preset()        → Copy of a preset by name.

    # Passwords
    hash_password()     → Hash a password.
    verify_password()   → Verify a password.
    needs_rehash()      → True if a stored hash should be upgraded.
    PasswordPolicy      → Validation rules.
    validate_password() → Enforce a policy.
    estimate_strength() → Rough strength score (for UX).

    # Repositories
    UserRepository          → Abstract persistence interface.
    SQLiteUserRepository    → Default SQLite implementation.

    # Sessions
    Session             → Session value object.
    SessionManager      → Create, validate, persist sessions.

    # Auth Manager
    AuthManager         → Register, login, sessions, permissions.

    # Exceptions
    AuthError, AuthenticationError,
    InvalidCredentialsError, AccountLockedError, AccountDisabledError,
    UserAlreadyExistsError, UserNotFoundError,
    UsernameValidationError, PasswordValidationError,
    PermissionDeniedError,
    SessionError, SessionExpiredError, InvalidSessionError.

Quick start:
    from ghanyx.auth import AuthManager, SQLiteUserRepository
    from ghanyx.database import get_db

    repo = SQLiteUserRepository(get_db())
    auth = AuthManager(repo)

    # First time only: create an admin
    auth.ensure_default_admin()

    # Register + login
    user = auth.register("ali", "Secret123", role="cashier")
    user = auth.login("ali", "Secret123")
    if user.has_permission("bookings.edit"):
        ...
"""

# ----- User & Permissions -----
from ghanyx.auth.permissions import (
    Permission,
    PermissionRegistry,
    PermissionSet,
    PRESETS,
    REGISTRY,
    get_preset,
    register_permission,
)
from ghanyx.auth.user import (
    User,
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_EMPLOYEE,
    ADMIN_ROLES,
    make_admin,
    make_guest,
)

# ----- Passwords -----
from ghanyx.auth.passwords import (
    DEFAULT_ALGORITHM,
    DEFAULT_ITERATIONS,
    DEFAULT_POLICY,
    PasswordPolicy,
    estimate_strength,
    hash_password,
    needs_rehash,
    validate_password,
    verify_password,
)

# ----- Repositories -----
from ghanyx.auth.repository import (
    UserRepository,
    SQLiteUserRepository,
)

# ----- Sessions -----
from ghanyx.auth.session import (
    Session,
    SessionManager,
    device_fingerprint,
)

# ----- Manager -----
from ghanyx.auth.manager import AuthManager

# ----- Exceptions -----
from ghanyx.auth.exceptions import (
    AuthError,
    AuthenticationError,
    InvalidCredentialsError,
    AccountLockedError,
    AccountDisabledError,
    UserAlreadyExistsError,
    UserNotFoundError,
    UsernameValidationError,
    PasswordValidationError,
    PermissionDeniedError,
    SessionError,
    SessionExpiredError,
    InvalidSessionError,
)


__all__ = [
    # User & Permissions
    "User",
    "Permission",
    "PermissionSet",
    "PermissionRegistry",
    "PRESETS",
    "REGISTRY",
    "get_preset",
    "register_permission",
    "ROLE_ADMIN",
    "ROLE_MANAGER",
    "ROLE_EMPLOYEE",
    "ADMIN_ROLES",
    "make_admin",
    "make_guest",

    # Passwords
    "hash_password",
    "verify_password",
    "needs_rehash",
    "PasswordPolicy",
    "validate_password",
    "estimate_strength",
    "DEFAULT_ALGORITHM",
    "DEFAULT_ITERATIONS",
    "DEFAULT_POLICY",

    # Repositories
    "UserRepository",
    "SQLiteUserRepository",

    # Sessions
    "Session",
    "SessionManager",
    "device_fingerprint",

    # Manager
    "AuthManager",

    # Exceptions
    "AuthError",
    "AuthenticationError",
    "InvalidCredentialsError",
    "AccountLockedError",
    "AccountDisabledError",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "UsernameValidationError",
    "PasswordValidationError",
    "PermissionDeniedError",
    "SessionError",
    "SessionExpiredError",
    "InvalidSessionError",
]