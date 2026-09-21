"""
Tests for ghanyx.config.

Coverage:
    - GhanyxConfig defaults & merging
    - Typed properties
    - Validation (env, log level, theme, etc.)
    - Dot-notation get/set
    - Loader (toml + env + .env priority)
    - Environment-specific overrides
    - Global singleton lifecycle
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from ghanyx.config import (
    GhanyxConfig,
    load_config,
    get_config,
    reload_config,
    set_config,
    reset_config,
    ConfigError,
    ConfigValidationError,
    ConfigMissingKeyError,
    ConfigTypeError,
)


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture(autouse=True)
def clean_global_config():
    """Reset the global config before and after each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def clean_env(monkeypatch):
    """Remove any GHANYX_* env vars before each test."""
    import os
    for key in list(os.environ.keys()):
        if key.startswith("GHANYX_"):
            monkeypatch.delenv(key, raising=False)
    yield monkeypatch


# ============================================================
# GhanyxConfig — defaults
# ============================================================
class TestDefaults:
    def test_empty_config_uses_defaults(self):
        c = GhanyxConfig()
        assert c.app_name == "ghanyx"
        assert c.environment == "development"
        assert c.language == "ar"
        assert c.log_level == "INFO"
        assert c.theme == "dark"
        assert c.window_width == 1400
        assert c.window_height == 850

    def test_default_paths(self):
        c = GhanyxConfig()
        assert c.log_dir == Path("logs")
        assert c.db_dir == Path("data")
        assert c.db_filename == "data.db"
        assert c.db_path == Path("data/data.db")

    def test_user_data_overrides_defaults(self):
        c = GhanyxConfig({"app": {"name": "myapp"}})
        assert c.app_name == "myapp"
        # Other values keep their defaults
        assert c.log_level == "INFO"


# ============================================================
# GhanyxConfig — dot notation
# ============================================================
class TestDotNotation:
    def test_get_simple(self):
        c = GhanyxConfig({"app": {"name": "test"}})
        assert c.get("app.name") == "test"

    def test_get_nested(self):
        c = GhanyxConfig({"a": {"b": {"c": 42}}})
        assert c.get("a.b.c") == 42

    def test_get_missing_returns_default(self):
        c = GhanyxConfig()
        assert c.get("missing.key", default="x") == "x"

    def test_get_missing_required_raises(self):
        c = GhanyxConfig()
        with pytest.raises(ConfigMissingKeyError):
            c.get("missing.key", required=True)

    def test_getitem(self):
        c = GhanyxConfig({"app": {"name": "test"}})
        assert c["app.name"] == "test"

    def test_getitem_missing_raises(self):
        c = GhanyxConfig()
        with pytest.raises(KeyError):
            _ = c["missing.key"]

    def test_contains(self):
        c = GhanyxConfig({"app": {"name": "test"}})
        assert "app.name" in c
        assert "missing.key" not in c

    def test_set(self):
        c = GhanyxConfig()
        c.set("app.name", "new")
        assert c.app_name == "new"


# ============================================================
# GhanyxConfig — typed access
# ============================================================
class TestTypedAccess:
    def test_get_typed_correct(self):
        c = GhanyxConfig({"ui": {"window_width": 1920}})
        assert c.get_typed("ui.window_width", int) == 1920

    def test_get_typed_wrong_type_raises(self):
        c = GhanyxConfig()
        c.set("ui.window_width", "wide")
        with pytest.raises(ConfigTypeError):
            c.get_typed("ui.window_width", int)


# ============================================================
# GhanyxConfig — validation
# ============================================================
class TestValidation:
    def test_invalid_environment_raises(self):
        with pytest.raises(ConfigValidationError):
            GhanyxConfig({"app": {"environment": "banana"}})

    def test_invalid_language_raises(self):
        with pytest.raises(ConfigValidationError):
            GhanyxConfig({"app": {"language": "fr"}})

    def test_invalid_log_level_raises(self):
        with pytest.raises(ConfigValidationError):
            GhanyxConfig({"logging": {"level": "SUPER"}})

    def test_invalid_theme_raises(self):
        with pytest.raises(ConfigValidationError):
            GhanyxConfig({"ui": {"theme": "purple"}})

    def test_invalid_window_width_raises(self):
        with pytest.raises(ConfigError):
            GhanyxConfig({"ui": {"window_width": -1}})

    def test_invalid_log_max_bytes_raises(self):
        with pytest.raises(ConfigError):
            GhanyxConfig({"logging": {"max_bytes": 0}})


# ============================================================
# Loader — priority
# ============================================================
class TestLoaderPriority:
    def test_defaults_when_no_sources(self, tmp_path, clean_env, monkeypatch):
        monkeypatch.chdir(tmp_path)
        c = load_config()
        assert c.app_name == "ghanyx"
        assert c.log_level == "INFO"

    def test_toml_overrides_defaults(self, tmp_path, clean_env, monkeypatch):
        toml = tmp_path / "config.toml"
        toml.write_text(
            dedent("""
                [app]
                name = "from_toml"

                [logging]
                level = "WARNING"
            """),
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        c = load_config()
        assert c.app_name == "from_toml"
        assert c.log_level == "WARNING"

    def test_env_file_overrides_toml(self, tmp_path, clean_env, monkeypatch):
        (tmp_path / "config.toml").write_text(
            '[app]\nname = "from_toml"\n', encoding="utf-8"
        )
        (tmp_path / ".env").write_text(
            'GHANYX_APP_NAME=from_env_file\n', encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        c = load_config()
        assert c.app_name == "from_env_file"

    def test_os_environ_overrides_everything(self, tmp_path, clean_env, monkeypatch):
        (tmp_path / "config.toml").write_text(
            '[app]\nname = "from_toml"\n', encoding="utf-8"
        )
        (tmp_path / ".env").write_text(
            'GHANYX_APP_NAME=from_env_file\n', encoding="utf-8"
        )
        monkeypatch.setenv("GHANYX_APP_NAME", "from_os_environ")
        monkeypatch.chdir(tmp_path)
        c = load_config()
        assert c.app_name == "from_os_environ"


# ============================================================
# Loader — type coercion
# ============================================================
class TestLoaderCoercion:
    def test_int_coercion(self, tmp_path, clean_env, monkeypatch):
        (tmp_path / ".env").write_text(
            "GHANYX_WINDOW_WIDTH=1920\n", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        c = load_config()
        assert c.window_width == 1920
        assert isinstance(c.window_width, int)

    def test_bool_coercion_true(self, tmp_path, clean_env, monkeypatch):
        (tmp_path / ".env").write_text(
            "GHANYX_LOG_CONSOLE=true\n", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        c = load_config()
        assert c.log_console is True

    def test_bool_coercion_false(self, tmp_path, clean_env, monkeypatch):
        (tmp_path / ".env").write_text(
            "GHANYX_LOG_COLORS=0\n", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        c = load_config()
        assert c.log_colors is False


# ============================================================
# Environment overrides
# ============================================================
class TestEnvironmentOverrides:
    def test_development_uses_debug(self):
        c = GhanyxConfig({"app": {"environment": "development"}})
        # Overrides are applied at load time, not construction.
        # So a manually-constructed config keeps INFO.
        assert c.log_level == "INFO"

    def test_production_disables_console(self, tmp_path, clean_env, monkeypatch):
        (tmp_path / ".env").write_text(
            "GHANYX_ENV=production\n", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        c = load_config()
        assert c.is_production is True
        assert c.log_console is False

    def test_development_enables_debug(self, tmp_path, clean_env, monkeypatch):
        (tmp_path / ".env").write_text(
            "GHANYX_ENV=development\n", encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        c = load_config()
        assert c.is_development is True
        assert c.log_level == "DEBUG"


# ============================================================
# Environment flag properties
# ============================================================
class TestEnvironmentFlags:
    def test_is_development(self):
        c = GhanyxConfig({"app": {"environment": "development"}})
        assert c.is_development is True
        assert c.is_production is False
        assert c.is_staging is False

    def test_is_production(self):
        c = GhanyxConfig({"app": {"environment": "production"}})
        assert c.is_production is True
        assert c.is_development is False

    def test_is_staging(self):
        c = GhanyxConfig({"app": {"environment": "staging"}})
        assert c.is_staging is True


# ============================================================
# Global singleton
# ============================================================
class TestGlobalSingleton:
    def test_get_config_returns_same_instance(self, tmp_path, clean_env, monkeypatch):
        monkeypatch.chdir(tmp_path)
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_reload_creates_new_instance(self, tmp_path, clean_env, monkeypatch):
        monkeypatch.chdir(tmp_path)
        c1 = get_config()
        c2 = reload_config()
        assert c1 is not c2

    def test_set_config_replaces(self, tmp_path, clean_env, monkeypatch):
        monkeypatch.chdir(tmp_path)
        get_config()
        new = GhanyxConfig({"app": {"name": "custom"}})
        set_config(new)
        assert get_config() is new

    def test_set_config_wrong_type_raises(self):
        with pytest.raises(TypeError):
            set_config("not a config")  # type: ignore

    def test_reset_clears(self, tmp_path, clean_env, monkeypatch):
        monkeypatch.chdir(tmp_path)
        c1 = get_config()
        reset_config()
        c2 = get_config()
        assert c1 is not c2


# ============================================================
# describe / repr
# ============================================================
class TestDescribe:
    def test_repr_contains_key_info(self):
        c = GhanyxConfig()
        text = repr(c)
        assert "GhanyxConfig" in text
        assert "development" in text

    def test_describe_returns_multiline(self):
        c = GhanyxConfig()
        text = c.describe()
        assert "app.name" in text
        assert "logging.level" in text
        assert "\n" in text