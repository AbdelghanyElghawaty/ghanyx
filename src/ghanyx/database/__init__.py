"""
Ghanyx database — unified database layer with migrations.

Public API:
    # Connection
    Database            → Abstract base class (for future backends).
    SQLiteDatabase      → SQLite implementation.
    get_db()            → Global singleton (reads config).
    set_db(db)          → Replace global (for tests).
    reset_db()          → Clear global (for tests).

    # Migrations
    Migration           → Base class for migrations.
    MigrationManager    → Tracks and applies migrations.
    AppliedMigration    → Record of an applied migration.

    # Exceptions
    DatabaseError       → Base.
    ConnectionError     → Failed to connect.
    QueryError          → SQL failed.
    NotFoundError       → Record not found.
    DuplicateError      → UNIQUE constraint violation.
    IntegrityError      → FK / CHECK violation.
    MigrationError      → Migration failed.
    TransactionError    → Transaction failed.

Quick start:
    from ghanyx.database import get_db

    db = get_db()
    db.execute("INSERT INTO users (name) VALUES (?)", ("Ali",))
    user = db.fetch_one("SELECT * FROM users WHERE name = ?", ("Ali",))

    with db.transaction():
        db.insert("users", {"name": "A"})
        db.insert("users", {"name": "B"})

Migrations:
    from ghanyx.database import Migration, MigrationManager

    class CreateUsers(Migration):
        version = "001"
        name = "create_users"

        def up(self, db):
            db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")

        def down(self, db):
            db.execute("DROP TABLE users")

    manager = MigrationManager(db)
    manager.register(CreateUsers)
    manager.migrate()
"""

from ghanyx.database.connection import (
    Database,
    SQLiteDatabase,
    get_db,
    set_db,
    reset_db,
)
from ghanyx.database.migrations import (
    Migration,
    MigrationManager,
    AppliedMigration,
)
from ghanyx.database.exceptions import (
    DatabaseError,
    ConnectionError,
    QueryError,
    NotFoundError,
    DuplicateError,
    IntegrityError,
    MigrationError,
    TransactionError,
)

__all__ = [
    # Connection
    "Database",
    "SQLiteDatabase",
    "get_db",
    "set_db",
    "reset_db",

    # Migrations
    "Migration",
    "MigrationManager",
    "AppliedMigration",

    # Exceptions
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "NotFoundError",
    "DuplicateError",
    "IntegrityError",
    "MigrationError",
    "TransactionError",
]