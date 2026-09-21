"""
User model for Ghanyx.

A `User` is a lightweight, immutable-ish representation of an
authenticated identity. It is NOT a database row — it's a domain
object that the rest of the app passes around.

Key properties:
    - id, username, role
    - permissions (PermissionSet)
    - is_active, is_admin
    - metadata (optional free-form dict)

Design principles:
    - Immutable after construction (mutations return copies).
    - JSON-serializable (via to_dict / from_dict).
    - Safe `has_permission()` with admin bypass.
    - Never exposes password hash to the rest of the app.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from ghanyx.auth.permissions import Permission, PermissionSet


# ============================================================
# Roles
# ============================================================
#: Reserved role names.
ROLE_ADMIN: str = "admin"
ROLE_MANAGER: str = "manager"
ROLE_EMPLOYEE: str = "employee"

#: Admin bypasses all permission checks.
ADMIN_ROLES: frozenset[str] = frozenset({ROLE_ADMIN})


# ============================================================
# User
# ============================================================
@dataclass(frozen=True)
class User:
    """
    An authenticated user.

    Attributes:
        id: Database ID (or None for guest users).
        username: Unique login name.
        role: Role name (e.g., "admin", "employee").
        permissions: Set of granted permission keys.
        is_active: Whether the account is enabled.
        created_at: ISO timestamp of account creation.
        last_login: ISO timestamp of last successful login.
        metadata: Optional free-form dict (e.g., full_name, email).
    """

    id: int | None = None
    username: str = ""
    role: str = ROLE_EMPLOYEE
    permissions: PermissionSet = field(default_factory=PermissionSet)
    is_active: bool = True
    created_at: str = ""
    last_login: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Admin / role
    # ------------------------------------------------------------------
    @property
    def is_admin(self) -> bool:
        """True if the user has an admin role (bypasses permissions)."""
        return self.role in ADMIN_ROLES

    def has_role(self, *roles: str) -> bool:
        """True if the user's role is one of the given roles."""
        return self.role in roles

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------
    def has_permission(self, permission: str | Permission) -> bool:
        """
        Check whether the user has a permission.

        Admin role bypasses ALL permission checks.
        """
        if self.is_admin:
            return True
        return self.permissions.has(permission)

    def has_any_permission(self, *permissions: str | Permission) -> bool:
        """True if the user has ANY of the given permissions."""
        if self.is_admin:
            return True
        return self.permissions.has_any(*permissions)

    def has_all_permissions(self, *permissions: str | Permission) -> bool:
        """True if the user has ALL of the given permissions."""
        if self.is_admin:
            return True
        return self.permissions.has_all(*permissions)

    def count_permissions(self) -> int:
        """
        Number of effectively granted permissions.

        For admin, returns the total number of registered permissions.
        """
        if self.is_admin:
            from ghanyx.auth.permissions import REGISTRY
            return len(REGISTRY.all_keys())
        return len(self.permissions)

    # ------------------------------------------------------------------
    # Mutations (return copies — User is frozen)
    # ------------------------------------------------------------------
    def with_permission(self, permission: str | Permission) -> "User":
        """Return a new User with the given permission added."""
        new_perms = PermissionSet(self.permissions.to_list())
        new_perms.add(permission)
        return replace(self, permissions=new_perms)

    def without_permission(self, permission: str | Permission) -> "User":
        """Return a new User with the given permission removed."""
        new_perms = PermissionSet(self.permissions.to_list())
        new_perms.remove(permission)
        return replace(self, permissions=new_perms)

    def with_role(self, role: str) -> "User":
        """Return a new User with a different role."""
        return replace(self, role=role)

    def with_last_login(self, when: datetime | None = None) -> "User":
        """Return a new User with `last_login` set to now (or given time)."""
        when = when or datetime.now()
        return replace(
            self,
            last_login=when.isoformat(timespec="seconds"),
        )

    def deactivated(self) -> "User":
        """Return a new User with is_active=False."""
        return replace(self, is_active=False)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self, *, include_permissions: bool = True) -> dict[str, Any]:
        """
        Return a JSON-serializable dict.

        Note: password hash is NEVER included (User never holds it).
        """
        data: dict[str, Any] = {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "metadata": dict(self.metadata),
        }
        if include_permissions:
            data["permissions"] = self.permissions.to_list()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """Build a User from a dict (inverse of to_dict)."""
        return cls(
            id=data.get("id"),
            username=data.get("username", ""),
            role=data.get("role", ROLE_EMPLOYEE),
            permissions=PermissionSet.from_list(data.get("permissions", [])),
            is_active=bool(data.get("is_active", True)),
            created_at=data.get("created_at", ""),
            last_login=data.get("last_login", ""),
            metadata=dict(data.get("metadata", {})),
        )

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------
    @property
    def display_name(self) -> str:
        """Return a human-friendly name (metadata.full_name or username)."""
        return str(self.metadata.get("full_name") or self.username)

    @property
    def role_display(self) -> str:
        """Arabic-friendly role label (fallback for older code)."""
        mapping = {
            ROLE_ADMIN: "مدير النظام",
            ROLE_MANAGER: "مدير",
            ROLE_EMPLOYEE: "موظف",
        }
        return mapping.get(self.role, self.role)

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"

    def __repr__(self) -> str:
        return (
            f"User(id={self.id!r}, username={self.username!r}, "
            f"role={self.role!r}, active={self.is_active})"
        )


# ============================================================
# Factory helpers
# ============================================================
def make_admin(
    username: str,
    *,
    user_id: int | None = None,
) -> User:
    """Create a full-access admin user (not persisted)."""
    return User(
        id=user_id,
        username=username,
        role=ROLE_ADMIN,
        permissions=PermissionSet(),
        is_active=True,
    )


def make_guest() -> User:
    """
    Create a read-only guest user.

    Useful for demos and previews without an account.
    """
    from ghanyx.auth.permissions import PRESETS
    return User(
        id=None,
        username="guest",
        role="guest",
        permissions=PermissionSet(PRESETS["viewer"].to_list()),
        is_active=True,
        metadata={"guest": True},
    )