"""
Tests for ghanyx.auth.

Coverage:
    - Passwords: hash, verify, rehash, policy, strength
    - Permissions: enum, set, registry, presets
    - User: immutability, permissions, admin bypass, serialization
    - Repository: CRUD, permissions, disable, delete
    - Session: creation, expiry, device fingerprint, persistence
    - AuthManager: register, login, lockout, rehash, sessions
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ghanyx.auth import (
    AuthManager,
    SQLiteUserRepository,
    UserRepository,
    User,
    Permission,
    PermissionSet,
    PermissionRegistry,
    PRESETS,
    get_preset,
    hash_password,
    verify_password,
    needs_rehash,
    PasswordPolicy,
    validate_password,
    estimate_strength,
    Session,
    SessionManager,
    device_fingerprint,
    make_admin,
    make_guest,
    AuthError,
    InvalidCredentialsError,
    AccountLockedError,
    AccountDisabledError,
    UserAlreadyExistsError,
    UserNotFoundError,
    UsernameValidationError,
    PasswordValidationError,
)
from ghanyx.database import SQLiteDatabase


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture
def db():
    d = SQLiteDatabase(":memory:")
    yield d
    d.close()


@pytest.fixture
def repo(db):
    return SQLiteUserRepository(db)


@pytest.fixture
def auth(repo):
    return AuthManager(repo)


# ============================================================
# Passwords
# ============================================================
class TestPasswords:
    def test_hash_returns_formatted_string(self):
        h = hash_password("Secret123")
        parts = h.split("$")
        assert len(parts) == 4
        assert parts[0].startswith("pbkdf2_")
        assert parts[1].isdigit()

    def test_hash_is_not_deterministic(self):
        """Two hashes of the same password must differ (salt)."""
        h1 = hash_password("Secret123")
        h2 = hash_password("Secret123")
        assert h1 != h2

    def test_verify_correct(self):
        h = hash_password("Secret123")
        assert verify_password("Secret123", h) is True

    def test_verify_wrong(self):
        h = hash_password("Secret123")
        assert verify_password("Wrong", h) is False

    def test_verify_empty(self):
        h = hash_password("Secret123")
        assert verify_password("", h) is False

    def test_verify_malformed_hash(self):
        assert verify_password("Secret123", "not-a-valid-hash") is False

    def test_hash_empty_raises(self):
        with pytest.raises(PasswordValidationError):
            hash_password("")

    def test_needs_rehash_old_format(self):
        import hashlib, secrets
        salt = secrets.token_bytes(32)
        dk = hashlib.pbkdf2_hmac("sha512", b"pw", salt, 1000)
        weak = f"pbkdf2_sha512$1000${salt.hex()}${dk.hex()}"
        assert needs_rehash(weak) is True

    def test_needs_rehash_fresh(self):
        h = hash_password("Secret123")
        assert needs_rehash(h) is False

    def test_policy_min_length(self):
        policy = PasswordPolicy(min_length=12)
        with pytest.raises(PasswordValidationError):
            policy.validate("short")

    def test_policy_requires_digit(self):
        policy = PasswordPolicy(require_digit=True)
        with pytest.raises(PasswordValidationError):
            policy.validate("NoDigitsHere")

    def test_policy_forbids_username(self):
        policy = PasswordPolicy()
        with pytest.raises(PasswordValidationError):
            policy.validate("ali12345", username="ali")

    def test_validate_password_default(self):
        validate_password("secret123")

    def test_strength_weak(self):
        score, label = estimate_strength("abc")
        assert label in ("weak", "empty")

    def test_strength_strong(self):
        score, label = estimate_strength("MyS3cur3-P@ssw0rd!")
        assert score >= 60


# ============================================================
# Permissions
# ============================================================
class TestPermissions:
    def test_enum_values(self):
        assert Permission.USERS_VIEW.value == "users.view"
        assert str(Permission.USERS_VIEW) == "users.view"

    def test_permission_set_add(self):
        ps = PermissionSet()
        ps.add(Permission.USERS_VIEW)
        assert Permission.USERS_VIEW in ps

    def test_permission_set_from_string(self):
        ps = PermissionSet({"users.view", "users.edit"})
        assert ps.has("users.view") is True
        assert ps.has("users.delete") is False

    def test_permission_set_has_all(self):
        ps = PermissionSet({"a", "b", "c"})
        assert ps.has_all("a", "b") is True
        assert ps.has_all("a", "x") is False

    def test_permission_set_has_any(self):
        ps = PermissionSet({"a", "b"})
        assert ps.has_any("a", "x") is True
        assert ps.has_any("x", "y") is False

    def test_permission_set_to_list(self):
        ps = PermissionSet({"b", "a", "c"})
        assert ps.to_list() == ["a", "b", "c"]

    def test_permission_set_from_list(self):
        ps = PermissionSet.from_list(["a", "b"])
        assert ps.to_list() == ["a", "b"]

    def test_permission_set_eq(self):
        ps1 = PermissionSet({"a", "b"})
        ps2 = PermissionSet({"a", "b"})
        assert ps1 == ps2

    def test_registry_has_built_ins(self):
        r = PermissionRegistry()
        assert r.is_registered("users.view")
        assert "users.view" in r.all_keys()

    def test_registry_register_custom(self):
        r = PermissionRegistry()
        r.register("custom.action", "Custom Action")
        assert r.is_registered("custom.action")
        assert r.label("custom.action") == "Custom Action"

    def test_presets_exist(self):
        for name in ("admin", "manager", "cashier", "employee", "viewer"):
            assert name in PRESETS

    def test_admin_preset_has_all(self):
        admin = PRESETS["admin"]
        assert admin.has(Permission.USERS_VIEW)
        assert admin.has(Permission.USERS_DELETE)
        assert admin.has(Permission.SETTINGS_MANAGE)

    def test_cashier_preset_limited(self):
        cashier = PRESETS["cashier"]
        assert cashier.has(Permission.BOOKINGS_EDIT)
        assert not cashier.has(Permission.USERS_DELETE)

    def test_get_preset_returns_copy(self):
        p1 = get_preset("admin")
        p2 = get_preset("admin")
        p1.add("hacked")
        assert "hacked" not in p2


# ============================================================
# User
# ============================================================
class TestUser:
    def test_admin_bypasses_permissions(self):
        admin = User(username="root_user", role="admin")
        assert admin.has_permission("anything") is True
        assert admin.has_permission("not.a.real.permission") is True

    def test_employee_respects_permissions(self):
        u = User(username="bob", role="employee", permissions=PermissionSet())
        assert u.has_permission("users.view") is False

    def test_employee_with_permission(self):
        u = User(
            username="bob",
            role="employee",
            permissions=PermissionSet({"users.view"}),
        )
        assert u.has_permission("users.view") is True

    def test_has_any_permission(self):
        u = User(permissions=PermissionSet({"a"}))
        assert u.has_any_permission("a", "b") is True
        assert u.has_any_permission("b", "c") is False

    def test_has_all_permissions(self):
        u = User(permissions=PermissionSet({"a", "b"}))
        assert u.has_all_permissions("a", "b") is True
        assert u.has_all_permissions("a", "c") is False

    def test_with_permission_returns_new(self):
        u = User(permissions=PermissionSet())
        u2 = u.with_permission("x")
        # Original unchanged
        assert u.has_permission("x") is False
        # New user has it
        assert u2.has_permission("x") is True

    def test_without_permission(self):
        u = User(permissions=PermissionSet({"a", "b"}))
        u2 = u.without_permission("a")
        assert u.has_permission("a") is True  # original
        assert u2.has_permission("a") is False

    def test_to_dict_from_dict_roundtrip(self):
        u = User(
            id=1,
            username="ali",
            role="admin",
            permissions=PermissionSet({"a", "b"}),
            metadata={"full_name": "Ali"},
        )
        d = u.to_dict()
        u2 = User.from_dict(d)
        assert u2.id == u.id
        assert u2.username == u.username
        assert u2.permissions == u.permissions
        assert u2.metadata == u.metadata

    def test_display_name_uses_metadata(self):
        u = User(username="ali", metadata={"full_name": "Ali Ahmed"})
        assert u.display_name == "Ali Ahmed"

    def test_make_admin(self):
        u = make_admin("admin_user")
        assert u.is_admin is True
        assert u.role == "admin"

    def test_make_guest(self):
        u = make_guest()
        assert u.username == "guest"
        assert u.is_admin is False
        assert u.has_permission("bookings.view") is True
        assert u.has_permission("users.delete") is False


# ============================================================
# Repository
# ============================================================
class TestRepository:
    def test_empty_repo(self, repo):
        assert repo.count() == 0
        assert repo.list_all() == []

    def test_create_and_find(self, repo):
        u = repo.create(
            username="ali",
            password_hash="hash",
            role="admin",
            permissions=PermissionSet({"a"}),
        )
        assert u.id is not None

        found = repo.find_by_id(u.id)
        assert found is not None
        assert found.username == "ali"

    def test_find_by_username(self, repo):
        repo.create(
            username="ali",
            password_hash="hash",
            role="employee",
            permissions=PermissionSet(),
        )
        result = repo.find_by_username("ali")
        assert result is not None
        user, hash_ = result
        assert user.username == "ali"
        assert hash_ == "hash"

    def test_find_by_username_missing(self, repo):
        assert repo.find_by_username("nobody") is None

    def test_duplicate_username_raises(self, repo):
        repo.create(
            username="ali", password_hash="h", role="e",
            permissions=PermissionSet(),
        )
        with pytest.raises(UserAlreadyExistsError):
            repo.create(
                username="ali", password_hash="h", role="e",
                permissions=PermissionSet(),
            )

    def test_update_password_hash(self, repo):
        u = repo.create(
            username="ali", password_hash="old", role="e",
            permissions=PermissionSet(),
        )
        repo.update_password_hash(u.id, "new")
        _, h = repo.find_by_username("ali")
        assert h == "new"

    def test_update_permissions(self, repo):
        u = repo.create(
            username="ali", password_hash="h", role="e",
            permissions=PermissionSet({"a"}),
        )
        repo.update_permissions(u.id, PermissionSet({"x", "y"}))
        u2 = repo.find_by_id(u.id)
        assert u2.has_permission("x")
        assert not u2.has_permission("a")

    def test_set_active(self, repo):
        u = repo.create(
            username="ali", password_hash="h", role="e",
            permissions=PermissionSet(),
        )
        repo.set_active(u.id, False)
        u2 = repo.find_by_id(u.id)
        assert u2.is_active is False

    def test_delete(self, repo):
        u = repo.create(
            username="ali", password_hash="h", role="e",
            permissions=PermissionSet(),
        )
        repo.delete(u.id)
        assert repo.find_by_id(u.id) is None

    def test_delete_missing_raises(self, repo):
        with pytest.raises(UserNotFoundError):
            repo.delete(9999)


# ============================================================
# Session
# ============================================================
class TestSession:
    def test_create_session(self):
        mgr = SessionManager()
        u = User(id=1, username="ali", role="admin")
        s = mgr.create(u)
        assert s.username == "ali"
        assert s.user_id == 1
        assert s.token
        assert not s.is_expired

    def test_session_expires(self):
        mgr = SessionManager(ttl=timedelta(seconds=-1))
        u = User(id=1, username="ali")
        s = mgr.create(u)
        assert s.is_expired is True

    def test_validate_expired_raises(self):
        from ghanyx.auth import SessionExpiredError
        mgr = SessionManager(ttl=timedelta(seconds=-1))
        s = mgr.create(User(id=1, username="ali"))
        with pytest.raises(SessionExpiredError):
            mgr.validate(s)

    def test_validate_ok(self):
        mgr = SessionManager()
        s = mgr.create(User(id=1, username="ali"))
        assert mgr.validate(s) is s

    def test_device_mismatch_raises(self):
        from ghanyx.auth import InvalidSessionError
        mgr = SessionManager(require_device_match=True)
        s = mgr.create(User(id=1, username="ali"))
        s2 = Session(
            token=s.token, user_id=s.user_id, username=s.username,
            role=s.role, created_at=s.created_at,
            expires_at=s.expires_at, device="other-device",
        )
        with pytest.raises(InvalidSessionError):
            mgr.validate(s2)

    def test_save_load_session(self, tmp_path):
        mgr = SessionManager()
        s = mgr.create(User(id=1, username="ali", role="admin"))
        path = tmp_path / ".session"
        mgr.save(s, path)
        assert path.exists()

        loaded = mgr.load(path)
        assert loaded is not None
        assert loaded.token == s.token
        assert loaded.username == "ali"

    def test_load_missing_returns_none(self, tmp_path):
        mgr = SessionManager()
        assert mgr.load(tmp_path / "nope") is None

    def test_load_corrupt_returns_none(self, tmp_path):
        path = tmp_path / ".session"
        path.write_text("not json", encoding="utf-8")
        mgr = SessionManager()
        assert mgr.load(path) is None

    def test_clear_session(self, tmp_path):
        mgr = SessionManager()
        s = mgr.create(User(id=1, username="ali"))
        path = tmp_path / ".session"
        mgr.save(s, path)
        mgr.clear(path)
        assert not path.exists()

    def test_device_fingerprint_stable(self):
        f1 = device_fingerprint()
        f2 = device_fingerprint()
        assert f1 == f2


# ============================================================
# AuthManager
# ============================================================
class TestAuthManagerRegister:
    def test_register_creates_user(self, auth):
        u = auth.register("ali", "Secret123")
        assert u.username == "ali"
        assert u.role == "employee"
        assert u.id is not None

    def test_register_with_preset(self, auth):
        u = auth.register("ali", "Secret123", role="cashier")
        assert u.has_permission("bookings.edit")
        assert not u.has_permission("users.delete")

    def test_register_admin_has_all(self, auth):
        # Use "admin_user" — "root" is a reserved/forbidden username
        u = auth.register("admin_user", "Secret123", role="admin")
        assert u.is_admin is True

    def test_register_duplicate_raises(self, auth):
        auth.register("ali", "Secret123")
        with pytest.raises(UserAlreadyExistsError):
            auth.register("ali", "Other123")

    def test_register_invalid_username(self, auth):
        with pytest.raises(UsernameValidationError):
            auth.register("a", "Secret123")

    def test_register_forbidden_username(self, auth):
        with pytest.raises(UsernameValidationError):
            auth.register("root", "Secret123")

    def test_register_weak_password(self, auth):
        with pytest.raises(PasswordValidationError):
            auth.register("ali", "weak")

    def test_register_password_containing_username(self, auth):
        with pytest.raises(PasswordValidationError):
            auth.register("ali", "ali12345")


class TestAuthManagerLogin:
    def test_login_success(self, auth):
        auth.register("ali", "Secret123")
        u = auth.login("ali", "Secret123")
        assert u.username == "ali"

    def test_login_wrong_password(self, auth):
        auth.register("ali", "Secret123")
        with pytest.raises(InvalidCredentialsError):
            auth.login("ali", "Wrong123")

    def test_login_unknown_user(self, auth):
        with pytest.raises(InvalidCredentialsError):
            auth.login("nobody", "Secret123")

    def test_login_disabled_account(self, auth):
        u = auth.register("ali", "Secret123")
        auth.set_user_active(u.id, False)
        with pytest.raises(AccountDisabledError):
            auth.login("ali", "Secret123")

    def test_login_lockout_after_max_attempts(self, auth):
        auth.register("ali", "Secret123")
        for _ in range(5):
            with pytest.raises(InvalidCredentialsError):
                auth.login("ali", "Wrong123")
        with pytest.raises(AccountLockedError):
            auth.login("ali", "Secret123")

    def test_lockout_clears_on_success(self, auth):
        auth.register("ali", "Secret123")
        for _ in range(3):
            with pytest.raises(InvalidCredentialsError):
                auth.login("ali", "Wrong123")
        auth.login("ali", "Secret123")
        assert auth.is_locked("ali") is False

    def test_login_updates_last_login(self, auth):
        auth.register("ali", "Secret123")
        u1 = auth.login("ali", "Secret123")
        time.sleep(1.1)
        u2 = auth.login("ali", "Secret123")
        assert u2.last_login >= u1.last_login

    def test_login_rehashes_old_password(self, auth):
        import hashlib, secrets
        salt = secrets.token_bytes(32)
        dk = hashlib.pbkdf2_hmac("sha512", b"Secret123", salt, 1000)
        weak_hash = f"pbkdf2_sha512$1000${salt.hex()}${dk.hex()}"

        auth.repo.create(
            username="ali",
            password_hash=weak_hash,
            role="employee",
            permissions=PermissionSet(),
        )

        auth.login("ali", "Secret123")
        _, new_hash = auth.repo.find_by_username("ali")
        # Should have been upgraded to the current iteration count
        iterations = int(new_hash.split("$")[1])
        assert iterations >= 200_000


class TestAuthManagerPermissions:
    def test_grant_permission(self, auth):
        u = auth.register("ali", "Secret123", role="employee")
        u2 = auth.grant_permission(u, "users.view")
        assert u2.has_permission("users.view")

        fresh = auth.repo.find_by_id(u.id)
        assert fresh.has_permission("users.view")

    def test_revoke_permission(self, auth):
        u = auth.register("ali", "Secret123", role="cashier")
        u2 = auth.revoke_permission(u, "bookings.edit")
        assert not u2.has_permission("bookings.edit")


class TestAuthManagerSessions:
    def test_create_and_restore_session(self, auth):
        u = auth.register("ali", "Secret123", role="admin")
        s = auth.create_session(u)
        restored = auth.restore_session(s)
        assert restored is not None
        assert restored.username == "ali"

    def test_restore_expired_returns_none(self, auth):
        u = auth.register("ali", "Secret123")
        from ghanyx.auth import SessionManager
        mgr = SessionManager(ttl=timedelta(seconds=-1))
        s = mgr.create(u)
        assert auth.restore_session(s) is None

    def test_save_and_load_session_file(self, auth, tmp_path):
        u = auth.register("ali", "Secret123")
        s = auth.create_session(u)
        path = tmp_path / ".session"
        auth.save_session(s, path)

        loaded = auth.load_session(path)
        assert loaded is not None
        assert loaded.username == "ali"

        restored = auth.restore_session(loaded)
        assert restored is not None

    def test_clear_session_file(self, auth, tmp_path):
        u = auth.register("ali", "Secret123")
        s = auth.create_session(u)
        path = tmp_path / ".session"
        auth.save_session(s, path)
        auth.clear_session(path)
        assert not path.exists()


class TestAuthManagerAdmin:
    def test_ensure_default_admin_creates_when_empty(self, auth):
        # Password must not contain the username, so we pick
        # a strong, unrelated one.
        u = auth.ensure_default_admin(
            username="admin",
            password="Str0ng@Pass!",
        )
        assert u is not None
        assert u.is_admin is True

    def test_ensure_default_admin_skips_when_users_exist(self, auth):
        auth.register("ali", "Secret123")
        result = auth.ensure_default_admin()
        assert result is None

    def test_list_users(self, auth):
        auth.register("a_user1", "Secret123")
        auth.register("b_user2", "Secret123")
        users = auth.list_users()
        assert len(users) == 2

    def test_delete_user(self, auth):
        u = auth.register("ali", "Secret123")
        auth.delete_user(u.id)
        assert auth.repo.find_by_id(u.id) is None