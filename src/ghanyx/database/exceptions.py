"""
Database-specific exceptions for Ghanyx.

All inherit from DatabaseError (which inherits from GhanyxError),
so callers can catch at the right level of granularity:

    try:
        db.execute(...)
    except NotFoundError:
        # specific handling
    except DatabaseError:
        # general database handling
    except GhanyxError:
        # any framework error

Design notes:
    - Every error carries enough context to debug the issue.
    - The original SQLite exception is chained via `from e`.
"""

from __future__ import annotations

from typing import Any

from ghanyx.errors import DatabaseError


# ============================================================
# Base (re-export for clarity)
# ============================================================
# DatabaseError itself lives in ghanyx.errors, but we re-export
# it here so users can import from either place:
#
#     from ghanyx.errors import DatabaseError
#     from ghanyx.database.exceptions import DatabaseError
#
__all__ = [
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "NotFoundError",
    "DuplicateError",
    "IntegrityError",
    "MigrationError",
    "TransactionError",
]


# ============================================================
# Connection
# ============================================================
class ConnectionError(DatabaseError):
    """Raised when a database connection cannot be opened or lost."""

    def __init__(
        self,
        message: str = "Database connection failed",
        *,
        path: str | None = None,
        details: str = "",
    ) -> None:
        super().__init__(
            message,
            details=details,
            context={"path": path} if path else {},
        )
        self.path = path


# ============================================================
# Query
# ============================================================
class QueryError(DatabaseError):
    """Raised when an SQL query fails (syntax, constraint, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        sql: str = "",
        params: tuple[Any, ...] | None = None,
        details: str = "",
    ) -> None:
        super().__init__(
            message,
            details=details,
            context={
                "sql": sql,
                "params": params,
            } if sql else {},
        )
        self.sql = sql
        self.params = params


# ============================================================
# Not found / duplicates
# ============================================================
class NotFoundError(DatabaseError):
    """Raised when a requested record does not exist."""

    def __init__(
        self,
        table: str = "",
        record_id: Any = None,
        *,
        details: str = "",
    ) -> None:
        message = "Record not found"
        if table and record_id is not None:
            message = f"Record not found in '{table}' with id={record_id}"
        elif table:
            message = f"No matching record in '{table}'"

        super().__init__(
            message,
            details=details,
            context={"table": table, "record_id": record_id},
        )
        self.table = table
        self.record_id = record_id


class DuplicateError(DatabaseError):
    """Raised when an insert violates a UNIQUE constraint."""

    def __init__(
        self,
        table: str = "",
        column: str = "",
        value: Any = None,
        *,
        details: str = "",
    ) -> None:
        message = "Duplicate value"
        if table and column:
            message = f"Duplicate value in '{table}.{column}'"
        if value is not None:
            message += f": {value!r}"

        super().__init__(
            message,
            details=details,
            context={"table": table, "column": column, "value": value},
        )
        self.table = table
        self.column = column
        self.value = value


class IntegrityError(DatabaseError):
    """Raised when a foreign key or CHECK constraint is violated."""

    def __init__(
        self,
        message: str = "Integrity constraint violated",
        *,
        table: str = "",
        details: str = "",
    ) -> None:
        super().__init__(
            message,
            details=details,
            context={"table": table} if table else {},
        )
        self.table = table


# ============================================================
# Migrations
# ============================================================
class MigrationError(DatabaseError):
    """Raised when a migration fails to apply or roll back."""

    def __init__(
        self,
        message: str,
        *,
        version: str = "",
        name: str = "",
        details: str = "",
    ) -> None:
        super().__init__(
            message,
            details=details,
            context={"version": version, "name": name},
        )
        self.version = version
        self.name = name


# ============================================================
# Transactions
# ============================================================
class TransactionError(DatabaseError):
    """Raised when a transaction cannot be started, committed, or rolled back."""

    def __init__(
        self,
        message: str = "Transaction failed",
        *,
        details: str = "",
    ) -> None:
        super().__init__(message, details=details)