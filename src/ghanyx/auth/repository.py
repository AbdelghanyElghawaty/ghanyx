"""
User repository — abstracts persistence of users.

Design:
    - `UserRepository` is an abstract base class (interface).
    - `SQLiteUserRepository` is the default concrete implementation.
    - Apps can provide their own (e.g., for a REST API backend).

Storage schema (SQLite):
    users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'employee',
        permissions TEXT NOT NULL DEFAULT '[]',   -- JSON array
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        last_login TEXT,
        metadata TEXT NOT NULL DEFAULT '{}'       -- JSON object
    )

Security note:
    The `password_hash` NEVER leaves the repository. The public API
    returns `User` objects (which have no hash field).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from ghanyx.auth.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
)
from ghanyx.auth.permissions import PermissionSet
from ghanyx.auth.user import User
from ghanyx.database.connection import Database
from ghanyx.database.exceptions import DuplicateError
from ghanyx.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Abstract interface
# ============================================================
class UserRepository(ABC):
    """
    Abstract user persistence interface.

    Implementations must provide these methods. Consumers should
    only depend on this interface, never on a concrete class.
    """

    @abstractmethod
    def find_by_username(self, username: str) -> tuple[User, str] | None:
        """
        Return (user, password_hash) for a given username, or None.

        ⚠️ This is the ONLY method that exposes the password hash.
        It is intended for the AuthManager only.
        """

    @abstractmethod
    def find_by_id(self, user_id: int) -> User | None:
        """Return a User by ID, or None."""

    @abstractmethod
    def create(
        self,
        *,
        username: str,
        password_hash: str,
        role: str,
        permissions: PermissionSet,
        metadata: dict[str, Any] | None = None,
    ) -> User:
        """Create a new user and return it."""

    @abstractmethod
    def update_password_hash(self, user_id: int, password_hash: str) -> None:
        """Update the password hash for a user (used after rehash)."""

    @abstractmethod
    def update_last_login(self, user_id: int) -> None:
        """Mark a login event."""

    @abstractmethod
    def update_permissions(
        self, user_id: int, permissions: PermissionSet
    ) -> None:
        """Replace the permissions set for a user."""

    @abstractmethod
    def set_active(self, user_id: int, active: bool) -> None:
        """Enable or disable a user."""

    @abstractmethod
    def delete(self, user_id: int) -> None:
        """Permanently delete a user."""

    @abstractmethod
    def list_all(self) -> list[User]:
        """Return all users (without password hashes)."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of users."""


# ============================================================
# SQLite implementation
# ============================================================
class SQLiteUserRepository(UserRepository):
    """
    SQLite-backed implementation of UserRepository.

    The `users` table is created automatically on first use.
    """

    TABLE = "users"

    def __init__(self, db: Database) -> None:
        self.db = db
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def _ensure_schema(self) -> None:
        """Create the users table if it doesn't exist."""
        self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'employee',
                permissions TEXT NOT NULL DEFAULT '[]',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT,
                metadata TEXT NOT NULL DEFAULT '{{}}'
            )
        """)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def find_by_username(self, username: str) -> tuple[User, str] | None:
        row = self.db.fetch_one(
            f"SELECT * FROM {self.TABLE} WHERE username = ?",
            (username,),
        )
        if row is None:
            return None
        return self._row_to_user(row), row["password_hash"]

    def find_by_id(self, user_id: int) -> User | None:
        row = self.db.fetch_one(
            f"SELECT * FROM {self.TABLE} WHERE id = ?",
            (user_id,),
        )
        return self._row_to_user(row) if row else None

    def list_all(self) -> list[User]:
        rows = self.db.fetch_all(
            f"SELECT * FROM {self.TABLE} ORDER BY username"
        )
        return [self._row_to_user(r) for r in rows]

    def count(self) -> int:
        return int(
            self.db.fetch_scalar(f"SELECT COUNT(*) FROM {self.TABLE}") or 0
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def create(
        self,
        *,
        username: str,
        password_hash: str,
        role: str,
        permissions: PermissionSet,
        metadata: dict[str, Any] | None = None,
    ) -> User:
        now = datetime.now().isoformat(timespec="seconds")
        data = {
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "permissions": json.dumps(permissions.to_list(), ensure_ascii=False),
            "is_active": 1,
            "created_at": now,
            "last_login": None,
            "metadata": json.dumps(metadata or {}, ensure_ascii=False),
        }
        try:
            new_id = self.db.insert(self.TABLE, data)
        except DuplicateError as e:
            raise UserAlreadyExistsError(username) from e

        logger.info("Created user '%s' (role=%s)", username, role)

        return User(
            id=int(new_id) if new_id is not None else None,
            username=username,
            role=role,
            permissions=PermissionSet(permissions.to_list()),
            is_active=True,
            created_at=now,
            last_login="",
            metadata=dict(metadata or {}),
        )

    def update_password_hash(self, user_id: int, password_hash: str) -> None:
        affected = self.db.update(
            self.TABLE, user_id, {"password_hash": password_hash}
        )
        if affected == 0:
            raise UserNotFoundError(str(user_id))

    def update_last_login(self, user_id: int) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self.db.update(self.TABLE, user_id, {"last_login": now})

    def update_permissions(
        self, user_id: int, permissions: PermissionSet
    ) -> None:
        affected = self.db.update(
            self.TABLE,
            user_id,
            {"permissions": json.dumps(permissions.to_list(), ensure_ascii=False)},
        )
        if affected == 0:
            raise UserNotFoundError(str(user_id))

    def set_active(self, user_id: int, active: bool) -> None:
        affected = self.db.update(
            self.TABLE, user_id, {"is_active": 1 if active else 0}
        )
        if affected == 0:
            raise UserNotFoundError(str(user_id))

    def delete(self, user_id: int) -> None:
        affected = self.db.delete(self.TABLE, user_id)
        if affected == 0:
            raise UserNotFoundError(str(user_id))
        logger.info("Deleted user id=%s", user_id)

    # ------------------------------------------------------------------
    # Row → User
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_user(row: dict[str, Any]) -> User:
        """Convert a DB row to a User (hiding password_hash)."""
        permissions_raw = row.get("permissions") or "[]"
        try:
            permissions_list = json.loads(permissions_raw)
        except (json.JSONDecodeError, TypeError):
            permissions_list = []

        metadata_raw = row.get("metadata") or "{}"
        try:
            metadata = json.loads(metadata_raw)
            if not isinstance(metadata, dict):
                metadata = {}
        except (json.JSONDecodeError, TypeError):
            metadata = {}

        return User(
            id=row.get("id"),
            username=row.get("username", ""),
            role=row.get("role", "employee"),
            permissions=PermissionSet.from_list(permissions_list),
            is_active=bool(row.get("is_active", 1)),
            created_at=row.get("created_at") or "",
            last_login=row.get("last_login") or "",
            metadata=metadata,
        )