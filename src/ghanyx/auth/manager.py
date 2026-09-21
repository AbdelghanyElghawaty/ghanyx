"""
AuthManager — orchestrates authentication, registration, and sessions.

Responsibilities:
    - Register new users (with password policy enforcement).
    - Authenticate users (with rate limiting + lockout).
    - Rehash passwords transparently when needed.
    - Create/restore sessions.
    - Track failed attempts (persistent via repository).
    - Emit audit-style logs.

Design:
    - Depends only on `UserRepository` (interface), not on SQLite.
    - Thread-safe (locks per username for login/register).
    - Never leaks whether a username exists to callers.
    - Fails fast on invalid input.

Usage:
    from ghanyx.auth import AuthManager, SQLiteUserRepository
    from ghanyx.database import get_db

    repo = SQLiteUserRepository(get_db())
    auth = AuthManager(repo)

    user = auth.register("ali", "Secret123", role="admin")
    user = auth.login("ali", "Secret123")   # returns User or raises

    session = auth.create_session(user)
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Any

from ghanyx.auth.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UsernameValidationError,
)
from ghanyx.auth.passwords import (
    DEFAULT_POLICY,
    PasswordPolicy,
    hash_password,
    needs_rehash,
    validate_password,
    verify_password,
)
from ghanyx.auth.permissions import PRESETS, PermissionSet
from ghanyx.auth.repository import UserRepository
from ghanyx.auth.session import Session, SessionManager
from ghanyx.auth.user import ROLE_ADMIN, ROLE_EMPLOYEE, User
from ghanyx.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Constants
# ============================================================
#: Default lockout policy.
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_LOCKOUT_WINDOW = timedelta(minutes=15)

#: Usernames that are always forbidden.
FORBIDDEN_USERNAMES = frozenset({
    "", "admin ", "root", "system", "guest ",
    "null", "undefined", "none",
})

#: Username regex: 3-32 chars, letters/digits/._- only.
import re
_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")


# ============================================================
# AuthManager
# ============================================================
class AuthManager:
    """
    Central authentication coordinator.

    Args:
        repository: The UserRepository to persist users.
        password_policy: Password strength rules.
        session_manager: For session creation/persistence.
        max_login_attempts: Before lockout.
        lockout_window: How long the failed-attempt window lasts.
    """

    def __init__(
        self,
        repository: UserRepository,
        *,
        password_policy: PasswordPolicy | None = None,
        session_manager: SessionManager | None = None,
        max_login_attempts: int = DEFAULT_MAX_ATTEMPTS,
        lockout_window: timedelta = DEFAULT_LOCKOUT_WINDOW,
    ) -> None:
        self.repo = repository
        self.policy = password_policy or DEFAULT_POLICY
        self.sessions = session_manager or SessionManager()
        self.max_attempts = max_login_attempts
        self.lockout_window = lockout_window

        # username → list[timestamp] (failed attempts)
        self._failed: dict[str, list[float]] = {}
        self._failed_lock = threading.Lock()

        # per-username lock for login/register critical sections
        self._locks: dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _user_lock(self, username: str) -> threading.Lock:
        """Return a per-username lock (creating it lazily)."""
        key = username.lower()
        with self._locks_lock:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock

    @staticmethod
    def _normalize_username(username: str) -> str:
        if not isinstance(username, str):
            raise UsernameValidationError("must be a string")
        return username.strip()

    def _validate_username(self, username: str) -> None:
        if not username:
            raise UsernameValidationError("must not be empty")
        if username.lower() in FORBIDDEN_USERNAMES:
            raise UsernameValidationError(
                "this username is reserved", username=username
            )
        if not _USERNAME_RE.match(username):
            raise UsernameValidationError(
                "must be 3-32 chars (letters, digits, . _ -)",
                username=username,
            )

    # ------------------------------------------------------------------
    # Failed attempts / lockout
    # ------------------------------------------------------------------
    def _record_failure(self, username: str) -> None:
        key = username.lower()
        now = time.time()
        with self._failed_lock:
            attempts = self._failed.setdefault(key, [])
            attempts.append(now)
            # Keep only recent
            cutoff = now - self.lockout_window.total_seconds()
            self._failed[key] = [t for t in attempts if t >= cutoff]

    def _clear_failures(self, username: str) -> None:
        with self._failed_lock:
            self._failed.pop(username.lower(), None)

    def _recent_failures(self, username: str) -> int:
        key = username.lower()
        cutoff = time.time() - self.lockout_window.total_seconds()
        with self._failed_lock:
            attempts = self._failed.get(key, [])
            recent = [t for t in attempts if t >= cutoff]
            if len(recent) != len(attempts):
                self._failed[key] = recent
            return len(recent)

    def is_locked(self, username: str) -> bool:
        """True if the username is currently locked out."""
        return self._recent_failures(username) >= self.max_attempts

    def seconds_until_unlock(self, username: str) -> int:
        """Return seconds remaining until the lock expires (0 if not locked)."""
        key = username.lower()
        with self._failed_lock:
            attempts = self._failed.get(key, [])
        if not attempts:
            return 0
        oldest = min(attempts)
        unlock_at = oldest + self.lockout_window.total_seconds()
        remaining = int(unlock_at - time.time())
        return max(0, remaining)

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------
    def register(
        self,
        username: str,
        password: str,
        *,
        role: str = ROLE_EMPLOYEE,
        permissions: PermissionSet | None = None,
        use_preset: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> User:
        """
        Register a new user.

        Args:
            username: Unique login name (validated).
            password: Plaintext password (validated against policy).
            role: Role name.
            permissions: Explicit permissions. If None and `use_preset`,
                will use PRESETS[role] if available.
            use_preset: If True and permissions is None, use preset.
            metadata: Optional free-form dict (name, email, ...).

        Returns:
            The created User.

        Raises:
            UsernameValidationError, UserAlreadyExistsError,
            PasswordValidationError.
        """
        username = self._normalize_username(username)
        self._validate_username(username)

        with self._user_lock(username):
            # Early existence check (fast path)
            if self.repo.find_by_username(username) is not None:
                raise UserAlreadyExistsError(username)

            # Password policy (uses username as forbidden substring)
            validate_password(password, policy=self.policy, username=username)

            # Permissions
            if permissions is None:
                if use_preset and role in PRESETS:
                    permissions = PermissionSet(PRESETS[role].to_list())
                else:
                    permissions = PermissionSet()

            # Hash
            pw_hash = hash_password(password)

            user = self.repo.create(
                username=username,
                password_hash=pw_hash,
                role=role,
                permissions=permissions,
                metadata=metadata or {},
            )

            logger.info(
                "Registered user '%s' (role=%s, perms=%d)",
                user.username, user.role, len(user.permissions),
            )
            return user

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def login(
        self,
        username: str,
        password: str,
    ) -> User:
        """
        Authenticate a user.

        Returns:
            The authenticated User.

        Raises:
            AccountLockedError: too many recent failures.
            InvalidCredentialsError: wrong username or password.
            AccountDisabledError: account exists but is disabled.
        """
        username = self._normalize_username(username)

        with self._user_lock(username):
            # Lockout check
            if self.is_locked(username):
                raise AccountLockedError(
                    username=username,
                    unlock_after_seconds=self.seconds_until_unlock(username),
                )

            record = self.repo.find_by_username(username)

            # Generic failure (don't reveal user existence)
            if record is None:
                self._record_failure(username)
                logger.info("Login failed (unknown user): '%s'", username)
                raise InvalidCredentialsError(username=username)

            user, stored_hash = record

            if not verify_password(password, stored_hash):
                self._record_failure(username)
                logger.info("Login failed (bad password): '%s'", username)
                raise InvalidCredentialsError(username=username)

            if not user.is_active:
                logger.info("Login rejected (disabled): '%s'", username)
                raise AccountDisabledError(username=username)

            # Success — clear failures
            self._clear_failures(username)

            # Transparent rehash if needed
            if needs_rehash(stored_hash):
                try:
                    new_hash = hash_password(password)
                    self.repo.update_password_hash(user.id, new_hash)
                    logger.info("Rehashed password for '%s'", username)
                except Exception:
                    logger.exception("Password rehash failed for '%s'", username)

            # Update last_login
            try:
                self.repo.update_last_login(user.id)
                user = user.with_last_login()
            except Exception:
                logger.exception("Failed to update last_login for '%s'", username)

            logger.info("Login OK: '%s'", username)
            return user

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------
    def create_session(self, user: User) -> Session:
        """Create a new session for an authenticated user."""
        return self.sessions.create(user)

    def restore_session(
        self,
        session: Session,
    ) -> User | None:
        """
        Validate a session and return the corresponding User (fresh from DB).
        """
        try:
            self.sessions.validate(session)
        except Exception:
            return None

        if session.user_id is None:
            return None

        user = self.repo.find_by_id(session.user_id)
        if user is None or not user.is_active:
            return None
        return user

    def save_session(self, session: Session, path: str) -> None:
        """Persist a session to a file."""
        self.sessions.save(session, path)

    def load_session(self, path: str) -> Session | None:
        """Load a session from a file (no validation)."""
        return self.sessions.load(path)

    def clear_session(self, path: str) -> None:
        """Delete a persisted session."""
        self.sessions.clear(path)

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    def grant_permission(self, user: User, permission: str) -> User:
        """Add a permission to a user and persist."""
        new_perms = PermissionSet(user.permissions.to_list())
        new_perms.add(permission)
        self.repo.update_permissions(user.id, new_perms)  # type: ignore[arg-type]
        return user.with_permission(permission)

    def revoke_permission(self, user: User, permission: str) -> User:
        """Remove a permission from a user and persist."""
        new_perms = PermissionSet(user.permissions.to_list())
        new_perms.remove(permission)
        self.repo.update_permissions(user.id, new_perms)  # type: ignore[arg-type]
        return user.without_permission(permission)

    # ------------------------------------------------------------------
    # Admin helpers
    # ------------------------------------------------------------------
    def set_user_active(self, user_id: int, active: bool) -> None:
        """Enable or disable a user."""
        self.repo.set_active(user_id, active)

    def delete_user(self, user_id: int) -> None:
        """Delete a user."""
        self.repo.delete(user_id)

    def list_users(self) -> list[User]:
        """Return all users (no password hashes)."""
        return self.repo.list_all()

    def ensure_default_admin(self, *, username: str = "admin", password: str = "admin") -> User | None:
        """
        Ensure an admin user exists. Creates one if the repo is empty.

        ⚠️ In production, pass a strong password and force a change.
        """
        if self.repo.count() > 0:
            return None
        logger.warning(
            "Creating default admin '%s' — change the password immediately!",
            username,
        )
        return self.register(
            username=username,
            password=password,
            role=ROLE_ADMIN,
            permissions=PermissionSet(PRESETS["admin"].to_list()),
            metadata={"created_by": "ensure_default_admin"},
        )