"""
Tests for ghanyx.database.

Coverage:
    - SQLiteDatabase: connect, execute, fetch_one, fetch_all, fetch_scalar
    - Helpers: insert, update, delete, exists, count
    - Transactions: commit, rollback, nested
    - Introspection: table_exists, list_tables
    - Error translation: DuplicateError, IntegrityError
    - MigrationManager: register, migrate, rollback, pending, applied
    - Migration validation: version/name required
    - Global singleton: get_db, set_db, reset_db
"""

from __future__ import annotations

import pytest

from ghanyx.database import (
    SQLiteDatabase,
    Database,
    Migration,
    MigrationManager,
    AppliedMigration,
    DuplicateError,
    QueryError,
    get_db,
    set_db,
    reset_db,
)


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture
def db():
    """A fresh in-memory database for each test."""
    d = SQLiteDatabase(":memory:")
    yield d
    d.close()


@pytest.fixture
def db_with_users(db):
    """Database with a `users` table ready for tests."""
    db.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            role TEXT DEFAULT 'employee',
            is_active INTEGER DEFAULT 1
        )
    """)
    return db


@pytest.fixture(autouse=True)
def clean_global():
    """Reset the global database around each test."""
    reset_db()
    yield
    reset_db()


# ============================================================
# Connection
# ============================================================
class TestConnection:
    def test_connect_memory(self):
        d = SQLiteDatabase(":memory:")
        assert d.is_memory is True
        assert d.path == ":memory:"
        d.close()

    def test_connect_file(self, tmp_path):
        path = tmp_path / "test.db"
        d = SQLiteDatabase(path)
        assert d.is_memory is False
        assert path.exists()
        d.close()

    def test_creates_parent_dir(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "test.db"
        d = SQLiteDatabase(path)
        assert path.exists()
        d.close()

    def test_context_manager(self):
        with SQLiteDatabase(":memory:") as d:
            d.execute("CREATE TABLE t (id INTEGER)")
            assert d.table_exists("t")

    def test_repr(self):
        d = SQLiteDatabase(":memory:")
        assert "SQLiteDatabase" in repr(d)
        d.close()


# ============================================================
# Core execution
# ============================================================
class TestExecution:
    def test_execute_creates_table(self, db):
        affected = db.execute("CREATE TABLE t (id INTEGER, name TEXT)")
        assert db.table_exists("t")

    def test_execute_insert(self, db_with_users):
        count = db_with_users.execute(
            "INSERT INTO users (username) VALUES (?)", ("ali",)
        )
        assert count == 1

    def test_execute_update(self, db_with_users):
        db_with_users.insert("users", {"username": "ali"})
        count = db_with_users.execute(
            "UPDATE users SET role = ? WHERE username = ?",
            ("admin", "ali"),
        )
        assert count == 1

    def test_execute_many(self, db_with_users):
        count = db_with_users.execute_many(
            "INSERT INTO users (username) VALUES (?)",
            [("a",), ("b",), ("c",)],
        )
        assert count == 3
        assert db_with_users.count("users") == 3


# ============================================================
# Fetching
# ============================================================
class TestFetching:
    def test_fetch_one_returns_dict(self, db_with_users):
        db_with_users.insert("users", {"username": "ali", "role": "admin"})
        row = db_with_users.fetch_one(
            "SELECT * FROM users WHERE username = ?", ("ali",)
        )
        assert isinstance(row, dict)
        assert row["username"] == "ali"
        assert row["role"] == "admin"

    def test_fetch_one_missing_returns_none(self, db_with_users):
        row = db_with_users.fetch_one(
            "SELECT * FROM users WHERE username = ?", ("nobody",)
        )
        assert row is None

    def test_fetch_all_returns_list_of_dicts(self, db_with_users):
        db_with_users.insert("users", {"username": "a"})
        db_with_users.insert("users", {"username": "b"})
        rows = db_with_users.fetch_all("SELECT * FROM users ORDER BY username")
        assert len(rows) == 2
        assert all(isinstance(r, dict) for r in rows)
        assert [r["username"] for r in rows] == ["a", "b"]

    def test_fetch_all_empty(self, db_with_users):
        assert db_with_users.fetch_all("SELECT * FROM users") == []

    def test_fetch_scalar(self, db_with_users):
        db_with_users.insert("users", {"username": "a"})
        db_with_users.insert("users", {"username": "b"})
        count = db_with_users.fetch_scalar("SELECT COUNT(*) FROM users")
        assert count == 2

    def test_fetch_scalar_default(self, db_with_users):
        val = db_with_users.fetch_scalar(
            "SELECT COUNT(*) FROM users WHERE username = ?",
            ("nobody",),
            default=999,
        )
        assert val == 0  # COUNT returns 0, not default

    def test_fetch_scalar_no_rows(self, db):
        db.execute("CREATE TABLE t (id INTEGER)")
        val = db.fetch_scalar("SELECT id FROM t LIMIT 1", default="empty")
        assert val == "empty"


# ============================================================
# Helpers
# ============================================================
class TestHelpers:
    def test_insert_returns_id(self, db_with_users):
        new_id = db_with_users.insert("users", {"username": "ali"})
        assert new_id == 1

        new_id2 = db_with_users.insert("users", {"username": "bob"})
        assert new_id2 == 2

    def test_insert_empty_raises(self, db_with_users):
        with pytest.raises(QueryError):
            db_with_users.insert("users", {})

    def test_insert_duplicate_raises_duplicate_error(self, db_with_users):
        db_with_users.insert("users", {"username": "ali"})
        with pytest.raises(DuplicateError):
            db_with_users.insert("users", {"username": "ali"})

    def test_insert_returning(self, db_with_users):
        username = db_with_users.insert(
            "users", {"username": "ali"}, returning="username"
        )
        assert username == "ali"

    def test_update(self, db_with_users):
        uid = db_with_users.insert("users", {"username": "ali"})
        affected = db_with_users.update("users", uid, {"role": "admin"})
        assert affected == 1

        row = db_with_users.fetch_one("SELECT * FROM users WHERE id = ?", (uid,))
        assert row["role"] == "admin"

    def test_update_nonexistent_returns_zero(self, db_with_users):
        affected = db_with_users.update("users", 9999, {"role": "admin"})
        assert affected == 0

    def test_update_empty_raises(self, db_with_users):
        with pytest.raises(QueryError):
            db_with_users.update("users", 1, {})

    def test_delete(self, db_with_users):
        uid = db_with_users.insert("users", {"username": "ali"})
        affected = db_with_users.delete("users", uid)
        assert affected == 1
        assert db_with_users.count("users") == 0

    def test_delete_nonexistent_returns_zero(self, db_with_users):
        assert db_with_users.delete("users", 9999) == 0

    def test_exists_true(self, db_with_users):
        db_with_users.insert("users", {"username": "ali"})
        assert db_with_users.exists("users", "username", "ali") is True

    def test_exists_false(self, db_with_users):
        assert db_with_users.exists("users", "username", "nobody") is False

    def test_count(self, db_with_users):
        assert db_with_users.count("users") == 0
        db_with_users.insert("users", {"username": "a"})
        db_with_users.insert("users", {"username": "b"})
        assert db_with_users.count("users") == 2

    def test_count_with_where(self, db_with_users):
        db_with_users.insert("users", {"username": "a", "role": "admin"})
        db_with_users.insert("users", {"username": "b", "role": "employee"})
        assert db_with_users.count("users", "role = ?", ("admin",)) == 1


# ============================================================
# Transactions
# ============================================================
class TestTransactions:
    def test_transaction_commit(self, db_with_users):
        with db_with_users.transaction():
            db_with_users.insert("users", {"username": "a"})
            db_with_users.insert("users", {"username": "b"})

        assert db_with_users.count("users") == 2

    def test_transaction_rollback_on_error(self, db_with_users):
        with pytest.raises(Exception):
            with db_with_users.transaction():
                db_with_users.insert("users", {"username": "a"})
                raise ValueError("boom")

        assert db_with_users.count("users") == 0

    def test_transaction_rollback_on_duplicate(self, db_with_users):
        db_with_users.insert("users", {"username": "a"})

        with pytest.raises(DuplicateError):
            with db_with_users.transaction():
                db_with_users.insert("users", {"username": "b"})
                db_with_users.insert("users", {"username": "a"})  # duplicate

        # Only the first 'a' should remain
        assert db_with_users.count("users") == 1


# ============================================================
# Introspection
# ============================================================
class TestIntrospection:
    def test_table_exists(self, db):
        assert db.table_exists("nope") is False
        db.execute("CREATE TABLE t (id INTEGER)")
        assert db.table_exists("t") is True

    def test_list_tables(self, db):
        assert db.list_tables() == []
        db.execute("CREATE TABLE a (id INTEGER)")
        db.execute("CREATE TABLE b (id INTEGER)")
        assert sorted(db.list_tables()) == ["a", "b"]

    def test_list_tables_excludes_internal(self, db):
        db.execute("CREATE TABLE t (id INTEGER)")
        db.execute("CREATE TABLE _migrations (version TEXT)")
        tables = db.list_tables()
        assert "_migrations" in tables  # user-created, not sqlite internal


# ============================================================
# Migrations
# ============================================================
class CreateUsers(Migration):
    version = "001"
    name = "create_users"

    def up(self, db):
        db.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL
            )
        """)

    def down(self, db):
        db.execute("DROP TABLE users")


class AddEmail(Migration):
    version = "002"
    name = "add_email"

    def up(self, db):
        db.execute("ALTER TABLE users ADD COLUMN email TEXT")

    def down(self, db):
        db.execute("ALTER TABLE users DROP COLUMN email")


class TestMigrationBase:
    def test_subclass_requires_version(self):
        with pytest.raises(ValueError, match="version"):
            class Bad(Migration):
                name = "bad"
                def up(self, db): pass
                def down(self, db): pass

    def test_subclass_requires_name(self):
        with pytest.raises(ValueError, match="name"):
            class Bad(Migration):
                version = "999"
                def up(self, db): pass
                def down(self, db): pass

    def test_identifier(self):
        m = CreateUsers()
        assert m.identifier == "001_create_users"

    def test_repr(self):
        m = CreateUsers()
        assert "001_create_users" in repr(m)


class TestMigrationManager:
    def test_creates_tracking_table(self, db):
        MigrationManager(db)
        assert db.table_exists("_migrations")

    def test_register_single(self, db):
        mgr = MigrationManager(db)
        mgr.register(CreateUsers)
        assert len(mgr.all_migrations()) == 1

    def test_register_multiple(self, db):
        mgr = MigrationManager(db)
        mgr.register(CreateUsers, AddEmail)
        assert len(mgr.all_migrations()) == 2

    def test_register_duplicate_raises(self, db):
        from ghanyx.database import MigrationError
        mgr = MigrationManager(db)
        mgr.register(CreateUsers)
        with pytest.raises(MigrationError):
            mgr.register(CreateUsers)

    def test_register_wrong_type_raises(self, db):
        mgr = MigrationManager(db)
        with pytest.raises(TypeError):
            mgr.register(str)

    def test_pending_initially_all(self, db):
        mgr = MigrationManager(db)
        mgr.register(CreateUsers, AddEmail)
        assert len(mgr.pending()) == 2

    def test_migrate_applies_all(self, db):
        mgr = MigrationManager(db)
        mgr.register(CreateUsers, AddEmail)
        applied = mgr.migrate()
        assert applied == 2
        assert db.table_exists("users")
        assert len(mgr.pending()) == 0

    def test_migrate_no_pending(self, db):
        mgr = MigrationManager(db)
        mgr.register(CreateUsers)
        mgr.migrate()
        assert mgr.migrate() == 0

    def test_applied_returns_records(self, db):
        mgr = MigrationManager(db)
        mgr.register(CreateUsers)
        mgr.migrate()

        applied = mgr.applied()
        assert len(applied) == 1
        assert isinstance(applied[0], AppliedMigration)
        assert applied[0].version == "001"
        assert applied[0].identifier == "001_create_users"

    def test_rollback_one(self, db):
        mgr = MigrationManager(db)
        mgr.register(CreateUsers, AddEmail)
        mgr.migrate()

        rolled = mgr.rollback(steps=1)
        assert rolled == 1
        assert len(mgr.applied()) == 1

    def test_rollback_all(self, db):
        mgr = MigrationManager(db)
        mgr.register(CreateUsers, AddEmail)
        mgr.migrate()

        mgr.rollback_all()
        assert len(mgr.applied()) == 0
        assert not db.table_exists("users")

    def test_rollback_nothing(self, db):
        mgr = MigrationManager(db)
        mgr.register(CreateUsers)
        assert mgr.rollback() == 0

    def test_migration_failure_rolls_back(self, db):
        from ghanyx.database import MigrationError

        class BrokenMigration(Migration):
            version = "003"
            name = "broken"
            def up(self, d):
                d.execute("CREATE TABLE ok (id INTEGER)")
                d.execute("THIS IS NOT VALID SQL")
            def down(self, d):
                d.execute("DROP TABLE ok")

        mgr = MigrationManager(db)
        mgr.register(BrokenMigration)

        with pytest.raises(MigrationError):
            mgr.migrate()

        # The table 'ok' should NOT exist because the transaction rolled back
        assert not db.table_exists("ok")
        assert len(mgr.applied()) == 0

    def test_has_pending(self, db):
        mgr = MigrationManager(db)
        mgr.register(CreateUsers)
        assert mgr.has_pending() is True
        mgr.migrate()
        assert mgr.has_pending() is False

    def test_status(self, db):
        mgr = MigrationManager(db)
        mgr.register(CreateUsers, AddEmail)
        mgr.migrate(target="001")

        status = mgr.status()
        assert status["applied"] == ["001_create_users"]
        assert status["pending"] == ["002_add_email"]


# ============================================================
# Global singleton
# ============================================================
class TestGlobalSingleton:
    def test_get_db_returns_same_instance(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        d1 = get_db()
        d2 = get_db()
        assert d1 is d2

    def test_set_db_replaces(self, db):
        set_db(db)
        assert get_db() is db

    def test_set_db_wrong_type_raises(self):
        with pytest.raises(TypeError):
            set_db("not a db")

    def test_reset_db(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        d1 = get_db()
        reset_db()
        d2 = get_db()
        assert d1 is not d2


# ============================================================
# Abstract base
# ============================================================
class TestAbstractBase:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            Database()

    def test_sqlite_is_subclass(self):
        assert issubclass(SQLiteDatabase, Database)