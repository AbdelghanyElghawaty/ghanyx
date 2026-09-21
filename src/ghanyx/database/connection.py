"""
Database connection layer for Ghanyx.

Public API:
    Database           → Abstract base class (for future backends).
    SQLiteDatabase     → SQLite implementation (production-ready).
    get_db()           → Global singleton (reads config).
    set_db(db)         → Replace global (for tests).
    reset_db()         → Clear global (for tests).

Usage:
    from ghanyx.database import get_db

    db = get_db()
    db.execute("INSERT INTO users (name) VALUES (?)", ("Ali",))
    user = db.fetch_one("SELECT * FROM users WHERE name = ?", ("Ali",))

    with db.transaction():
        db.insert("users", {"name": "A"})
        db.insert("users", {"name": "B"})
"""

from __future__ import annotations

import sqlite3
import threading
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

from ghanyx.database.exceptions import (
    ConnectionError,
    DuplicateError,
    IntegrityError,
    QueryError,
)


# ============================================================
# Abstract base
# ============================================================
class Database(ABC):
    """
    Abstract database interface.

    Future backends (PostgreSQL, MySQL) should inherit from this
    and implement every abstract method. Consumers should only
    depend on this interface, never on a concrete backend.
    """

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def execute(self, sql: str, params: Sequence[Any] = ()) -> int: ...

    @abstractmethod
    def fetch_one(
        self, sql: str, params: Sequence[Any] = ()
    ) -> dict[str, Any] | None: ...

    @abstractmethod
    def fetch_all(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    def fetch_scalar(
        self, sql: str, params: Sequence[Any] = (), default: Any = None
    ) -> Any: ...


# ============================================================
# SQLite implementation
# ============================================================
class SQLiteDatabase(Database):
    """
    SQLite implementation of the Database interface.

    Features:
        - WAL mode for better concurrency.
        - Foreign keys enforcement.
        - Row factory returning dicts (not tuples).
        - Thread-local connections.
        - Context-manager transactions with automatic rollback.
        - Nested transactions via SAVEPOINTs.
        - Convenience helpers: insert/update/delete/exists/count.

    Args:
        path: Path to the database file, or ":memory:" for an
              in-memory database.
        timeout: Connection timeout (seconds).
        foreign_keys: Whether to enforce FK constraints.
        wal_mode: Whether to enable WAL journal mode.
    """

    def __init__(
        self,
        path: str | Path = "data.db",
        *,
        timeout: float = 10.0,
        foreign_keys: bool = True,
        wal_mode: bool = True,
    ) -> None:
        self._path = str(path)
        self._timeout = timeout
        self._foreign_keys = foreign_keys
        self._wal_mode = wal_mode

        # Thread-local connections
        self._local = threading.local()
        self._local.transaction_depth = 0
        self._local_connections: list[sqlite3.Connection] = []
        self._lock = threading.Lock()

        # Eagerly connect once to fail fast on bad paths
        self.connect()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def path(self) -> str:
        return self._path

    @property
    def is_memory(self) -> bool:
        return self._path == ":memory:"

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def connect(self) -> None:
        """Open the connection for the current thread (idempotent)."""
        if getattr(self._local, "conn", None) is not None:
            return

        try:
            if self.is_memory:
                conn = sqlite3.connect(
                    ":memory:",
                    timeout=self._timeout,
                    check_same_thread=False,
                )
            else:
                # Ensure parent dir exists
                db_path = Path(self._path)
                if db_path.parent and str(db_path.parent) != ".":
                    db_path.parent.mkdir(parents=True, exist_ok=True)

                conn = sqlite3.connect(
                    self._path,
                    timeout=self._timeout,
                    check_same_thread=False,
                )
        except sqlite3.Error as e:
            raise ConnectionError(
                f"Failed to connect to database: {e}",
                path=self._path,
            ) from e

        # Row factory → dict
        conn.row_factory = sqlite3.Row

        # PRAGMAs
        try:
            if self._foreign_keys:
                conn.execute("PRAGMA foreign_keys = ON")
            if self._wal_mode and not self.is_memory:
                conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 10000")
        except sqlite3.Error:
            pass  # PRAGMA failures are non-fatal

        self._local.conn = conn
        with self._lock:
            self._local_connections.append(conn)

    def _conn(self) -> sqlite3.Connection:
        """Get the current thread's connection, opening if needed."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            self.connect()
            conn = self._local.conn
        return conn

    def close(self) -> None:
        """Close the current thread's connection."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            return
        try:
            conn.close()
        except sqlite3.Error:
            pass
        finally:
            self._local.conn = None

    def close_all(self) -> None:
        """Close every connection opened by this instance."""
        with self._lock:
            for conn in list(self._local_connections):
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
            self._local_connections.clear()
        self._local.conn = None

    def __enter__(self) -> "SQLiteDatabase":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Commit / rollback helpers (transaction-aware)
    # ------------------------------------------------------------------
    def _commit(self) -> None:
        """
        Commit only if we're NOT inside a transaction.

        If we ARE inside a transaction (depth > 0), skip — the
        transaction's context manager will commit at the end.
        """
        if getattr(self._local, "transaction_depth", 0) == 0:
            self._conn().commit()

    def _rollback(self) -> None:
        """Rollback only if NOT inside a transaction."""
        if getattr(self._local, "transaction_depth", 0) == 0:
            try:
                self._conn().rollback()
            except sqlite3.Error:
                pass

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------
    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        """
        Execute a write query (INSERT/UPDATE/DELETE).

        Returns:
            Number of affected rows.

        Raises:
            QueryError, DuplicateError, IntegrityError.
        """
        try:
            cur = self._conn().execute(sql, tuple(params))
            self._commit()
            return cur.rowcount
        except sqlite3.IntegrityError as e:
            self._rollback()
            raise self._translate_integrity_error(e, sql) from e
        except sqlite3.Error as e:
            self._rollback()
            raise QueryError(str(e), sql=sql, params=tuple(params)) from e

    def execute_many(
        self, sql: str, seq_of_params: Sequence[Sequence[Any]]
    ) -> int:
        """Execute the same query many times with different params."""
        try:
            cur = self._conn().executemany(sql, seq_of_params)
            self._commit()
            return cur.rowcount
        except sqlite3.IntegrityError as e:
            self._rollback()
            raise self._translate_integrity_error(e, sql) from e
        except sqlite3.Error as e:
            self._rollback()
            raise QueryError(str(e), sql=sql) from e

    def fetch_one(
        self, sql: str, params: Sequence[Any] = ()
    ) -> dict[str, Any] | None:
        """Fetch a single row as a dict, or None."""
        try:
            cur = self._conn().execute(sql, tuple(params))
            row = cur.fetchone()
            return dict(row) if row is not None else None
        except sqlite3.Error as e:
            raise QueryError(str(e), sql=sql, params=tuple(params)) from e

    def fetch_all(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[dict[str, Any]]:
        """Fetch all rows as dicts."""
        try:
            cur = self._conn().execute(sql, tuple(params))
            return [dict(row) for row in cur.fetchall()]
        except sqlite3.Error as e:
            raise QueryError(str(e), sql=sql, params=tuple(params)) from e

    def fetch_scalar(
        self,
        sql: str,
        params: Sequence[Any] = (),
        default: Any = None,
    ) -> Any:
        """Fetch the first column of the first row (e.g., COUNT(*))."""
        try:
            cur = self._conn().execute(sql, tuple(params))
            row = cur.fetchone()
            if row is None:
                return default
            return row[0]
        except sqlite3.Error as e:
            raise QueryError(str(e), sql=sql, params=tuple(params)) from e

    # ------------------------------------------------------------------
    # High-level helpers
    # ------------------------------------------------------------------
    def insert(
        self,
        table: str,
        data: dict[str, Any],
        *,
        returning: str | None = None,
    ) -> int | None:
        """
        Insert a row and return the new primary key.

        Args:
            table: Table name.
            data: Column → value dict.
            returning: Optional column to return (e.g., "id").

        Returns:
            The last inserted row ID (default), or the value of
            `returning` if specified.
        """
        if not data:
            raise QueryError("insert() requires a non-empty data dict")

        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        try:
            cur = self._conn().execute(sql, tuple(data.values()))
            self._commit()
            last_id = cur.lastrowid

            if returning:
                row = self.fetch_one(
                    f"SELECT {returning} FROM {table} WHERE rowid = ?",
                    (last_id,),
                )
                return row[returning] if row else None
            return last_id
        except sqlite3.IntegrityError as e:
            self._rollback()
            raise self._translate_integrity_error(e, sql) from e
        except sqlite3.Error as e:
            self._rollback()
            raise QueryError(str(e), sql=sql) from e

    def update(
        self,
        table: str,
        record_id: Any,
        data: dict[str, Any],
        *,
        id_column: str = "id",
    ) -> int:
        """
        Update a row by primary key.

        Returns:
            Number of affected rows (0 or 1).
        """
        if not data:
            raise QueryError("update() requires a non-empty data dict")

        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE {id_column} = ?"
        params = tuple(data.values()) + (record_id,)

        try:
            cur = self._conn().execute(sql, params)
            self._commit()
            return cur.rowcount
        except sqlite3.IntegrityError as e:
            self._rollback()
            raise self._translate_integrity_error(e, sql) from e
        except sqlite3.Error as e:
            self._rollback()
            raise QueryError(str(e), sql=sql, params=params) from e

    def delete(
        self,
        table: str,
        record_id: Any,
        *,
        id_column: str = "id",
    ) -> int:
        """Delete a row by primary key. Returns number of affected rows."""
        sql = f"DELETE FROM {table} WHERE {id_column} = ?"
        try:
            cur = self._conn().execute(sql, (record_id,))
            self._commit()
            return cur.rowcount
        except sqlite3.Error as e:
            self._rollback()
            raise QueryError(str(e), sql=sql, params=(record_id,)) from e

    def exists(
        self,
        table: str,
        column: str,
        value: Any,
    ) -> bool:
        """Check whether any row has the given column value."""
        sql = f"SELECT 1 FROM {table} WHERE {column} = ? LIMIT 1"
        try:
            cur = self._conn().execute(sql, (value,))
            return cur.fetchone() is not None
        except sqlite3.Error as e:
            raise QueryError(str(e), sql=sql, params=(value,)) from e

    def count(self, table: str, where: str = "", params: Sequence[Any] = ()) -> int:
        """Count rows in a table, optionally filtered."""
        sql = f"SELECT COUNT(*) FROM {table}"
        if where:
            sql += f" WHERE {where}"
        return int(self.fetch_scalar(sql, params, default=0))

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------
    @contextmanager
    def transaction(self) -> Iterator["SQLiteDatabase"]:
        """
        Context manager for atomic transactions.

        Supports nesting via SAVEPOINTs. If nested, uses SAVEPOINT;
        if top-level, uses BEGIN/COMMIT/ROLLBACK.

        Usage:
            with db.transaction():
                db.insert("users", {"name": "A"})
                db.insert("users", {"name": "B"})
                # raises → all rolled back
        """
        conn = self._conn()
        depth = getattr(self._local, "transaction_depth", 0)
        self._local.transaction_depth = depth + 1

        savepoint_name = f"ghanyx_sp_{depth}"

        try:
            if depth == 0:
                # Top-level: real transaction
                conn.execute("BEGIN")
            else:
                # Nested: savepoint
                conn.execute(f"SAVEPOINT {savepoint_name}")

            yield self

            if depth == 0:
                conn.commit()
            else:
                conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")

        except Exception:
            try:
                if depth == 0:
                    conn.rollback()
                else:
                    conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                    conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            except sqlite3.Error:
                pass
            raise
        finally:
            self._local.transaction_depth = depth

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def table_exists(self, table: str) -> bool:
        """Check if a table exists."""
        sql = (
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name = ? LIMIT 1"
        )
        return self.fetch_one(sql, (table,)) is not None

    def list_tables(self) -> list[str]:
        """Return all table names."""
        rows = self.fetch_all(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        return [r["name"] for r in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _translate_integrity_error(
        e: sqlite3.IntegrityError, sql: str
    ) -> Exception:
        """Map raw SQLite integrity errors to our domain errors."""
        msg = str(e).lower()
        if "unique" in msg or "duplicate" in msg:
            return DuplicateError(details=f"SQL: {sql[:200]}")
        return IntegrityError(details=f"SQL: {sql[:200]}")

    def __repr__(self) -> str:
        return f"SQLiteDatabase(path={self._path!r})"


# ============================================================
# Global singleton
# ============================================================
_global_db: Database | None = None
_global_lock = threading.Lock()


def get_db() -> Database:
    """
    Return the global database instance, creating it on first call.

    Reads `database.dir` and `database.filename` from the global
    config. Falls back to "data.db" if config is unavailable.
    """
    global _global_db
    if _global_db is not None:
        return _global_db

    with _global_lock:
        if _global_db is not None:
            return _global_db

        try:
            from ghanyx.config import get_config
            config = get_config()
            db_path = config.db_path
        except Exception:
            db_path = Path("data.db")

        _global_db = SQLiteDatabase(db_path)
        return _global_db


def set_db(db: Database) -> None:
    """Replace the global database (mainly for tests)."""
    global _global_db
    if not isinstance(db, Database):
        raise TypeError(
            f"set_db expects a Database instance, got {type(db).__name__}"
        )
    with _global_lock:
        _global_db = db


def reset_db() -> None:
    """Clear the global database (mainly for tests)."""
    global _global_db
    with _global_lock:
        if _global_db is not None:
            try:
                close_all = getattr(_global_db, "close_all", None)
                if callable(close_all):
                    close_all()
            except Exception:
                pass
        _global_db = None