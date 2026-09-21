"""
Permission system for Ghanyx.

Design:
    - Permissions are named with dot-notation: "feature.action".
    - A `Permission` Enum defines the built-in ones (typo-proof).
    - A `PermissionRegistry` allows apps to register their own.
    - A `PermissionSet` is a set of granted permission keys.
    - Presets (like "admin", "cashier") are pre-baked sets.

Usage:
    from ghanyx.auth import Permission, PermissionSet, PRESETS

    # Enum
    if Permission.EDIT_SERVICES in perms:
        ...

    # Registry (extend with your own)
    from ghanyx.auth.permissions import register_permission
    register_permission("shop.edit", "Edit shop settings")

    # Presets
    perms = PRESETS["admin"]  # a PermissionSet with everything
"""

from __future__ import annotations

from enum import Enum
from typing import Final, Iterable


# ============================================================
# Helper — defined early so it's available during Registry init
# ============================================================
def _pretty_label(key: str) -> str:
    """Convert 'users.edit' to 'Users Edit' (for fallback display)."""
    return key.replace(".", " ").replace("_", " ").title()


# ============================================================
# Permission Enum
# ============================================================
class Permission(str, Enum):
    """
    Built-in permission keys.

    Inheriting from `str` makes them JSON-serializable and directly
    usable as dict keys / set members.

    Naming convention: "feature.action" (e.g., "users.edit").
    """

    # ----- Users & auth -----
    USERS_VIEW = "users.view"
    USERS_CREATE = "users.create"
    USERS_EDIT = "users.edit"
    USERS_DELETE = "users.delete"
    USERS_MANAGE_PERMISSIONS = "users.manage_permissions"

    # ----- Services / products -----
    SERVICES_VIEW = "services.view"
    SERVICES_EDIT = "services.edit"

    # ----- Customers -----
    CUSTOMERS_VIEW = "customers.view"
    CUSTOMERS_EDIT = "customers.edit"
    CUSTOMERS_EDIT_INFO = "customers.edit_info"

    # ----- Bookings / orders -----
    BOOKINGS_VIEW = "bookings.view"
    BOOKINGS_EDIT = "bookings.edit"

    # ----- Shifts -----
    SHIFTS_VIEW = "shifts.view"
    SHIFTS_MANAGE = "shifts.manage"
    SHIFTS_EXPORT = "shifts.export"

    # ----- Reports -----
    REPORTS_VIEW = "reports.view"

    # ----- Employees -----
    EMPLOYEES_VIEW = "employees.view"
    EMPLOYEES_EDIT = "employees.edit"
    ATTENDANCE_MANAGE = "attendance.manage"
    TRANSACTIONS_MANAGE = "transactions.manage"
    SALARIES_MANAGE = "salaries.manage"

    # ----- Inventory -----
    INVENTORY_VIEW = "inventory.view"
    INVENTORY_EDIT = "inventory.edit"
    INVENTORY_STOCK_IN = "inventory.stock_in"
    INVENTORY_STOCK_OUT = "inventory.stock_out"
    INVENTORY_REPORTS = "inventory.reports"

    # ----- Management -----
    MANAGEMENT_VIEW = "management.view"
    DASHBOARD_VIEW = "dashboard.view"
    EXPENSES_MANAGE = "expenses.manage"
    PROFIT_LOSS_VIEW = "profit_loss.view"
    ANALYTICS_VIEW = "analytics.view"

    # ----- Advanced -----
    AUDIT_VIEW = "audit.view"
    SETTINGS_MANAGE = "settings.manage"
    BACKUP_RESTORE = "backup.restore"

    def __str__(self) -> str:
        return self.value


# ============================================================
# Registry
# ============================================================
class PermissionRegistry:
    """
    Registry of known permission keys and their human labels.

    The built-in permissions are pre-registered. Apps can add
    their own with `register()`.
    """

    def __init__(self) -> None:
        self._labels: dict[str, str] = {}
        # Pre-register built-ins (label = pretty version of the value)
        for perm in Permission:
            self._labels[perm.value] = _pretty_label(perm.value)

    def register(self, key: str, label: str = "") -> None:
        """Register a new permission key with an optional label."""
        if not key or not isinstance(key, str):
            raise ValueError("permission key must be a non-empty string")
        self._labels[key] = label or _pretty_label(key)

    def is_registered(self, key: str) -> bool:
        return key in self._labels

    def label(self, key: str) -> str:
        return self._labels.get(key, key)

    def all_keys(self) -> list[str]:
        return sorted(self._labels.keys())

    def all_labels(self) -> dict[str, str]:
        return dict(self._labels)


#: Global registry instance.
REGISTRY: Final[PermissionRegistry] = PermissionRegistry()


def register_permission(key: str, label: str = "") -> None:
    """Convenience function — register a permission in the global registry."""
    REGISTRY.register(key, label)


# ============================================================
# PermissionSet
# ============================================================
class PermissionSet:
    """
    An immutable-ish set of granted permission keys.

    Backed by a `set[str]`, so membership tests are O(1).
    Accepts `Permission` enum members or plain strings.

    Usage:
        perms = PermissionSet({"users.view", Permission.USERS_EDIT})
        Permission.USERS_VIEW in perms        # True
        "users.edit" in perms                 # True
        "users.delete" in perms               # False

        perms.add("users.delete")
        perms.remove("users.delete")
    """

    def __init__(self, initial: Iterable[str | Permission] | None = None) -> None:
        self._keys: set[str] = set()
        if initial:
            for item in initial:
                self.add(item)

    # ----- Core -----
    def add(self, permission: str | Permission) -> None:
        self._keys.add(_key(permission))

    def remove(self, permission: str | Permission) -> None:
        self._keys.discard(_key(permission))

    def has(self, permission: str | Permission) -> bool:
        return _key(permission) in self._keys

    def has_all(self, *permissions: str | Permission) -> bool:
        """True if ALL of the given permissions are present."""
        return all(self.has(p) for p in permissions)

    def has_any(self, *permissions: str | Permission) -> bool:
        """True if ANY of the given permissions is present."""
        return any(self.has(p) for p in permissions)

    def clear(self) -> None:
        self._keys.clear()

    # ----- Iteration -----
    def __iter__(self):
        return iter(sorted(self._keys))

    def __len__(self) -> int:
        return len(self._keys)

    def __contains__(self, permission: object) -> bool:
        try:
            return self.has(permission)  # type: ignore[arg-type]
        except (TypeError, AttributeError):
            return False

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PermissionSet):
            return self._keys == other._keys
        if isinstance(other, (set, frozenset)):
            return self._keys == {_key(p) for p in other}
        return NotImplemented

    def __repr__(self) -> str:
        return f"PermissionSet({sorted(self._keys)!r})"

    # ----- Serialization -----
    def to_list(self) -> list[str]:
        """Return a sorted list of keys (JSON-friendly)."""
        return sorted(self._keys)

    @classmethod
    def from_list(cls, keys: Iterable[str] | None) -> "PermissionSet":
        """Build from a list of strings."""
        return cls(keys or [])

    # ----- Special -----
    def expand_wildcard(self) -> "PermissionSet":
        """
        Return a new set where a "*" entry is replaced by all
        registered permissions.
        """
        if "*" not in self._keys:
            return PermissionSet(self._keys)
        return PermissionSet(REGISTRY.all_keys())


# ============================================================
# Helpers
# ============================================================
def _key(permission: str | Permission | object) -> str:
    """Normalize a permission to its string key."""
    if isinstance(permission, Permission):
        return permission.value
    if isinstance(permission, str):
        return permission
    raise TypeError(f"Invalid permission: {permission!r}")


# ============================================================
# Presets
# ============================================================
def _all_permissions() -> PermissionSet:
    """All built-in permissions."""
    return PermissionSet({p.value for p in Permission})


def _admin() -> PermissionSet:
    """Admin: full access."""
    return _all_permissions()


def _manager() -> PermissionSet:
    """Branch manager — almost everything except user management."""
    return PermissionSet({
        Permission.SERVICES_VIEW, Permission.SERVICES_EDIT,
        Permission.CUSTOMERS_VIEW, Permission.CUSTOMERS_EDIT,
        Permission.CUSTOMERS_EDIT_INFO,
        Permission.BOOKINGS_VIEW, Permission.BOOKINGS_EDIT,
        Permission.SHIFTS_VIEW, Permission.SHIFTS_MANAGE, Permission.SHIFTS_EXPORT,
        Permission.REPORTS_VIEW,
        Permission.EMPLOYEES_VIEW, Permission.EMPLOYEES_EDIT,
        Permission.ATTENDANCE_MANAGE, Permission.TRANSACTIONS_MANAGE,
        Permission.SALARIES_MANAGE,
        Permission.INVENTORY_VIEW, Permission.INVENTORY_EDIT,
        Permission.INVENTORY_STOCK_IN, Permission.INVENTORY_STOCK_OUT,
        Permission.INVENTORY_REPORTS,
        Permission.MANAGEMENT_VIEW, Permission.DASHBOARD_VIEW,
        Permission.EXPENSES_MANAGE, Permission.PROFIT_LOSS_VIEW,
        Permission.ANALYTICS_VIEW,
    })


def _cashier() -> PermissionSet:
    """Cashier — sales, bookings, shifts."""
    return PermissionSet({
        Permission.SERVICES_VIEW,
        Permission.CUSTOMERS_VIEW, Permission.CUSTOMERS_EDIT,
        Permission.CUSTOMERS_EDIT_INFO,
        Permission.BOOKINGS_VIEW, Permission.BOOKINGS_EDIT,
        Permission.SHIFTS_VIEW, Permission.SHIFTS_MANAGE,
        Permission.INVENTORY_VIEW, Permission.INVENTORY_STOCK_OUT,
    })


def _employee() -> PermissionSet:
    """Base employee — view bookings and customers."""
    return PermissionSet({
        Permission.SERVICES_VIEW,
        Permission.CUSTOMERS_VIEW,
        Permission.BOOKINGS_VIEW,
    })


def _viewer() -> PermissionSet:
    """Read-only — view everything, edit nothing."""
    return PermissionSet({
        Permission.SERVICES_VIEW,
        Permission.CUSTOMERS_VIEW,
        Permission.BOOKINGS_VIEW,
        Permission.SHIFTS_VIEW,
        Permission.REPORTS_VIEW,
        Permission.EMPLOYEES_VIEW,
        Permission.INVENTORY_VIEW,
        Permission.MANAGEMENT_VIEW, Permission.DASHBOARD_VIEW,
        Permission.PROFIT_LOSS_VIEW, Permission.ANALYTICS_VIEW,
    })


#: Built-in presets. Keys: role → PermissionSet.
PRESETS: Final[dict[str, PermissionSet]] = {
    "admin": _admin(),
    "manager": _manager(),
    "cashier": _cashier(),
    "employee": _employee(),
    "viewer": _viewer(),
}


def get_preset(name: str) -> PermissionSet:
    """Return a copy of a preset by name."""
    if name not in PRESETS:
        raise KeyError(f"Unknown preset: {name!r}")
    return PermissionSet(PRESETS[name].to_list())