"""
Migration system for Ghanyx.

A migration is a versioned, reversible change to the database schema.

Design:
    - Each migration is a Python class inheriting from `Migration`.
    - Migrations have a `version` (string, e.g., "001") and a `name`.
    - `up()` applies the change; `down()` reverses it.
    - The MigrationManager tracks applied migrations in a
      `_migrations` table inside the database itself.

Usage:
    from ghanyx.database import get_db
    from ghanyx.database.migrations import Migration, MigrationManager

    class CreateUsers(Migration):
        version = "001"
        name = "create_users"

        def up(self, db):
            db.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    created_at TEXT
                )
            ''')

        def down(self, db):
            db.execute("DROP TABLE users")

    db = get_db()
    manager = MigrationManager(db)
    manager.register(CreateUsers)
    manager.migrate()      # applies pending
    # manager.rollback()   # rolls back the last one
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Iterable

from ghanyx.database.exceptions import MigrationError
from ghanyx.logging import get_logger

if TYPE_CHECKING:
    from ghanyx.database.connection import Database

logger = get_logger(__name__)


# ============================================================
# Migration base class
# ============================================================
class Migration(ABC):
    """
    Base class for all migrations.

    Subclasses MUST define:
        - version: str (e.g., "001", "002")
        - name:    str (e.g., "create_users")
        - up(db):   apply the change
        - down(db): reverse the change

    Convention:
        - Versions are zero-padded strings ("001" not "1").
        - Names are snake_case and descriptive.
        - `up()` and `down()` receive the Database instance.
    """

    version: str = ""
    name: str = ""
    description: str = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.version:
            raise ValueError(
                f"Migration '{cls.__name__}' must define a `version`"
            )
        if not cls.name:
            raise ValueError(
                f"Migration '{cls.__name__}' must define a `name`"
            )

    @abstractmethod
    def up(self, db: "Database") -> None:
        """Apply the migration."""

    @abstractmethod
    def down(self, db: "Database") -> None:
        """Reverse the migration."""

    @property
    def identifier(self) -> str:
        """Human-readable identifier: '001_create_users'."""
        return f"{self.version}_{self.name}"

    def __repr__(self) -> str:
        return f"<Migration {self.identifier}>"


# ============================================================
# Applied migration record
# ============================================================
@dataclass(frozen=True)
class AppliedMigration:
    """A record of a migration that has been applied."""

    version: str
    name: str
    applied_at: str

    @property
    def identifier(self) -> str:
        return f"{self.version}_{self.name}"


# ============================================================
# MigrationManager
# ============================================================
class MigrationManager:
    """
    Tracks and applies migrations for a database.

    Usage:
        manager = MigrationManager(db)
        manager.register(CreateUsers)
        manager.register(AddEmailToUsers)

        pending = manager.pending()    # list of migrations not yet applied
        applied = manager.applied()    # list of applied migrations

        manager.migrate()              # apply all pending
        manager.migrate(target="002")  # apply up to version 002

        manager.rollback()             # roll back the last one
        manager.rollback(steps=2)      # roll back two
    """

    _TRACKING_TABLE = "_migrations"

    def __init__(self, db: "Database") -> None:
        self.db = db
        self._migrations: dict[str, Migration] = {}
        self._ensure_tracking_table()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    def register(
        self,
        *migration_classes: type[Migration],
    ) -> "MigrationManager":
        """
        Register one or more migration classes.

        Returns self, so calls can be chained:
            manager.register(A, B, C)
        """
        for cls in migration_classes:
            if not issubclass(cls, Migration):
                raise TypeError(
                    f"{cls.__name__} is not a Migration subclass"
                )
            instance = cls()
            if instance.version in self._migrations:
                raise MigrationError(
                    f"Duplicate migration version: {instance.version}",
                    version=instance.version,
                    name=instance.name,
                )
            self._migrations[instance.version] = instance
            logger.debug("Registered migration: %s", instance.identifier)
        return self

    # ------------------------------------------------------------------
    # Tracking table
    # ------------------------------------------------------------------
    def _ensure_tracking_table(self) -> None:
        """Create the _migrations table if it doesn't exist."""
        self.db.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._TRACKING_TABLE} (
                version TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def applied(self) -> list[AppliedMigration]:
        """Return all applied migrations, ordered by version."""
        rows = self.db.fetch_all(
            f"SELECT version, name, applied_at "
            f"FROM {self._TRACKING_TABLE} ORDER BY version"
        )
        return [
            AppliedMigration(
                version=r["version"],
                name=r["name"],
                applied_at=r["applied_at"],
            )
            for r in rows
        ]

    def applied_versions(self) -> set[str]:
        """Return just the versions of applied migrations."""
        return {m.version for m in self.applied()}

    def pending(self) -> list[Migration]:
        """Return migrations not yet applied, ordered by version."""
        applied = self.applied_versions()
        return [
            self._migrations[v]
            for v in sorted(self._migrations.keys())
            if v not in applied
        ]

    def all_migrations(self) -> list[Migration]:
        """Return all registered migrations, ordered by version."""
        return [self._migrations[v] for v in sorted(self._migrations.keys())]

    def has_pending(self) -> bool:
        """True if there are migrations not yet applied."""
        return bool(self.pending())

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------
    def migrate(self, target: str | None = None) -> int:
        """
        Apply all pending migrations (up to `target` if specified).

        Args:
            target: Optional version to stop at (inclusive).

        Returns:
            Number of migrations applied.

        Raises:
            MigrationError: if any migration fails.
        """
        pending = self.pending()
        if target is not None:
            pending = [m for m in pending if m.version <= target]

        if not pending:
            logger.info("No pending migrations.")
            return 0

        logger.info("Applying %d migration(s)...", len(pending))
        count = 0

        for migration in pending:
            self._apply_one(migration)
            count += 1

        logger.info("Applied %d migration(s).", count)
        return count

    def _apply_one(self, migration: Migration) -> None:
        """Apply a single migration inside a transaction."""
        logger.info("→ Applying %s", migration.identifier)
        try:
            with self.db.transaction():
                migration.up(self.db)
                self.db.execute(
                    f"INSERT INTO {self._TRACKING_TABLE} "
                    f"(version, name, applied_at) VALUES (?, ?, ?)",
                    (
                        migration.version,
                        migration.name,
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )
        except Exception as e:
            logger.exception("Migration failed: %s", migration.identifier)
            raise MigrationError(
                f"Failed to apply migration {migration.identifier}: {e}",
                version=migration.version,
                name=migration.name,
            ) from e

    # ------------------------------------------------------------------
    # Rollback
    # ------------------------------------------------------------------
    def rollback(self, steps: int = 1) -> int:
        """
        Roll back the last `steps` applied migrations.

        Args:
            steps: How many migrations to roll back (default 1).

        Returns:
            Number of migrations rolled back.
        """
        applied = self.applied()
        if not applied:
            logger.info("Nothing to roll back.")
            return 0

        to_rollback = list(reversed(applied))[:steps]
        count = 0

        for record in to_rollback:
            migration = self._migrations.get(record.version)
            if migration is None:
                raise MigrationError(
                    f"Cannot roll back {record.identifier}: "
                    f"migration not registered",
                    version=record.version,
                    name=record.name,
                )
            self._rollback_one(migration)
            count += 1

        logger.info("Rolled back %d migration(s).", count)
        return count

    def _rollback_one(self, migration: Migration) -> None:
        """Roll back a single migration inside a transaction."""
        logger.info("← Rolling back %s", migration.identifier)
        try:
            with self.db.transaction():
                migration.down(self.db)
                self.db.execute(
                    f"DELETE FROM {self._TRACKING_TABLE} WHERE version = ?",
                    (migration.version,),
                )
        except Exception as e:
            logger.exception("Rollback failed: %s", migration.identifier)
            raise MigrationError(
                f"Failed to roll back {migration.identifier}: {e}",
                version=migration.version,
                name=migration.name,
            ) from e

    def rollback_all(self) -> int:
        """Roll back every applied migration."""
        return self.rollback(steps=len(self.applied()))

    # ------------------------------------------------------------------
    # Reset (dev only)
    # ------------------------------------------------------------------
    def reset(self) -> int:
        """
        Roll back all migrations and re-apply them.

        ⚠️ DESTRUCTIVE — only for development.

        Returns:
            Number of migrations re-applied.
        """
        logger.warning("Resetting all migrations (DEV ONLY)")
        self.rollback_all()
        return self.migrate()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    def status(self) -> dict[str, list[str]]:
        """Return a summary of applied and pending migrations."""
        return {
            "applied": [m.identifier for m in self.applied()],
            "pending": [m.identifier for m in self.pending()],
        }