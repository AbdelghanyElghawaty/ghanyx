"""
Tests for ghanyx.ui.

Coverage:
    - Colors: validation, palettes, semantic roles
    - Theme: immutability, with_color, with_font
    - ThemeRegistry: register, get, list
    - ThemeManager: set, subscribe, toggle
    - Styles: build_stylesheet produces valid QSS
    - Icons: emoji map, list_icons
    - RTL: language detection, apply_language

Notes:
    - No PySide6 import required — UI module is headless-safe.
    - QWidget/QApplication are NOT instantiated in these tests.
"""

from __future__ import annotations

import pytest

from ghanyx.ui import (
    # Colors
    PALETTES,
    REQUIRED_ROLES,
    get_palette,
    is_valid_hex,
    list_palettes,
    register_palette,
    # Theme
    Theme,
    ThemeManager,
    ThemeRegistry,
    get_theme,
    get_theme_manager,
    set_theme,
    color,
    is_dark,
    reset_theme_manager,
    # Styles
    build_stylesheet,
    # Icons
    get_emoji,
    list_icons,
    # RTL
    apply_language,
    current_language,
    is_ltr_language,
    is_rtl_language,
    language_name,
    list_languages,
)


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture(autouse=True)
def clean_theme_manager():
    """Reset global theme manager around each test."""
    reset_theme_manager()
    yield
    reset_theme_manager()


# ============================================================
# Colors
# ============================================================
class TestColors:
    def test_valid_hex_6(self):
        assert is_valid_hex("#3b82f6") is True
        assert is_valid_hex("#FFFFFF") is True

    def test_valid_hex_3(self):
        assert is_valid_hex("#abc") is True

    def test_invalid_hex_missing_hash(self):
        assert is_valid_hex("3b82f6") is False

    def test_invalid_hex_wrong_length(self):
        assert is_valid_hex("#12") is False
        assert is_valid_hex("#1234567") is False

    def test_invalid_hex_bad_chars(self):
        assert is_valid_hex("#xyzxyz") is False

    def test_palettes_registered(self):
        names = list_palettes()
        assert "dark_navy" in names
        assert "light_clean" in names
        assert "nord" in names

    def test_every_palette_has_all_roles(self):
        for name, palette in PALETTES.items():
            for role in REQUIRED_ROLES:
                assert role in palette, (
                    f"Palette '{name}' missing role '{role}'"
                )

    def test_every_palette_valid_hex(self):
        for name, palette in PALETTES.items():
            for role, value in palette.items():
                assert is_valid_hex(value), (
                    f"Palette '{name}' has invalid color for '{role}': {value}"
                )

    def test_get_palette_returns_copy(self):
        p1 = get_palette("dark_navy")
        p2 = get_palette("dark_navy")
        p1["primary"] = "#000000"
        assert p2["primary"] != "#000000"

    def test_get_palette_unknown_raises(self):
        with pytest.raises(KeyError):
            get_palette("does_not_exist")

    def test_register_palette_custom(self):
        custom = dict(get_palette("dark_navy"))
        custom["primary"] = "#ff00ff"
        register_palette("my_custom_theme", custom)

        assert "my_custom_theme" in list_palettes()
        assert get_palette("my_custom_theme")["primary"] == "#ff00ff"

    def test_register_palette_missing_role_raises(self):
        broken = {r: "#000000" for r in REQUIRED_ROLES}
        del broken["primary"]
        with pytest.raises(ValueError, match="primary"):
            register_palette("broken", broken)


# ============================================================
# Theme
# ============================================================
class TestTheme:
    def test_theme_basic(self):
        t = Theme(name="test", colors=get_palette("dark_navy"), is_dark=True)
        assert t.name == "test"
        assert t.is_dark is True
        assert t.color("primary") == "#3b82f6"

    def test_theme_color_default(self):
        t = Theme(name="test", colors={}, is_dark=True)
        assert t.color("nonexistent") == "#000000"
        assert t.color("nonexistent", default="#ffffff") == "#ffffff"

    def test_theme_with_color(self):
        t = Theme(name="test", colors=get_palette("dark_navy"))
        t2 = t.with_color("primary", "#ff0000")
        assert t.color("primary") == "#3b82f6"  # original unchanged
        assert t2.color("primary") == "#ff0000"

    def test_theme_with_color_invalid(self):
        t = Theme(name="test", colors=get_palette("dark_navy"))
        with pytest.raises(ValueError):
            t.with_color("primary", "not-a-color")

    def test_theme_with_color_unknown_role(self):
        t = Theme(name="test", colors=get_palette("dark_navy"))
        with pytest.raises(KeyError):
            t.with_color("not_a_role", "#000000")

    def test_theme_with_font(self):
        t = Theme(name="test", colors=get_palette("dark_navy"))
        t2 = t.with_font("Arial", 14)
        assert t.font_family != "Arial"      # original
        assert t2.font_family == "Arial"
        assert t2.font_size == 14

    def test_theme_to_dict(self):
        t = Theme(name="test", colors=get_palette("dark_navy"), is_dark=True)
        d = t.to_dict()
        assert d["name"] == "test"
        assert d["is_dark"] is True
        assert "colors" in d


# ============================================================
# ThemeRegistry
# ============================================================
class TestThemeRegistry:
    def test_registry_prepopulated(self):
        reg = ThemeRegistry()
        assert "dark_navy" in reg.names()
        assert "light_clean" in reg.names()

    def test_registry_get(self):
        reg = ThemeRegistry()
        t = reg.get("dark_navy")
        assert t.name == "dark_navy"
        assert t.is_dark is True

    def test_registry_get_unknown_raises(self):
        reg = ThemeRegistry()
        with pytest.raises(KeyError):
            reg.get("unknown")

    def test_registry_has(self):
        reg = ThemeRegistry()
        assert reg.has("dark_navy") is True
        assert reg.has("unknown") is False

    def test_registry_all(self):
        reg = ThemeRegistry()
        themes = reg.all()
        assert len(themes) >= 6
        assert all(isinstance(t, Theme) for t in themes)


# ============================================================
# ThemeManager
# ============================================================
class TestThemeManager:
    def test_default_theme(self):
        tm = ThemeManager()
        assert tm.name == "dark_navy"

    def test_set_theme(self):
        tm = ThemeManager()
        tm.set("dark_purple")
        assert tm.name == "dark_purple"

    def test_set_unknown_raises(self):
        tm = ThemeManager()
        with pytest.raises(KeyError):
            tm.set("unknown_theme")

    def test_subscribe_called_on_change(self):
        tm = ThemeManager()
        calls = []
        tm.subscribe(lambda theme: calls.append(theme.name))

        tm.set("dark_purple")
        assert "dark_purple" in calls

    def test_subscribe_not_called_on_same(self):
        tm = ThemeManager()
        calls = []
        tm.subscribe(lambda theme: calls.append(theme.name))

        tm.set("dark_navy")  # same as default
        assert calls == []

    def test_unsubscribe(self):
        tm = ThemeManager()
        calls = []
        unsub = tm.subscribe(lambda t: calls.append(t.name))

        tm.set("dark_purple")
        assert len(calls) == 1

        unsub()
        tm.set("light_clean")
        assert len(calls) == 1  # not called again

    def test_color_shortcut(self):
        tm = ThemeManager()
        assert tm.color("primary") == "#3b82f6"

    def test_is_dark(self):
        tm = ThemeManager()
        assert tm.is_dark is True
        tm.set("light_clean")
        assert tm.is_dark is False

    def test_toggle_dark_light(self):
        tm = ThemeManager()
        assert tm.is_dark is True

        tm.toggle_dark_light()
        assert tm.is_dark is False
        assert tm.name == "light_clean"

        tm.toggle_dark_light()
        assert tm.is_dark is True


# ============================================================
# Global singleton
# ============================================================
class TestGlobalSingleton:
    def test_get_manager_same_instance(self):
        m1 = get_theme_manager()
        m2 = get_theme_manager()
        assert m1 is m2

    def test_set_theme_global(self):
        set_theme("dark_purple")
        assert get_theme().name == "dark_purple"

    def test_color_shortcut_global(self):
        set_theme("light_clean")
        assert color("primary") == "#2563eb"

    def test_is_dark_global(self):
        set_theme("light_clean")
        assert is_dark() is False

    def test_reset_clears(self):
        m1 = get_theme_manager()
        reset_theme_manager()
        m2 = get_theme_manager()
        assert m1 is not m2


# ============================================================
# Styles
# ============================================================
class TestStyles:
    def test_stylesheet_is_string(self):
        t = get_theme()
        qss = build_stylesheet(t)
        assert isinstance(qss, str)
        assert len(qss) > 1000

    def test_stylesheet_contains_theme_name(self):
        set_theme("dark_purple")
        qss = build_stylesheet(get_theme())
        assert "dark_purple" in qss

    def test_stylesheet_uses_theme_colors(self):
        set_theme("light_clean")
        qss = build_stylesheet(get_theme())
        # light_clean primary is #2563eb
        assert "#2563eb" in qss

    def test_stylesheet_has_common_selectors(self):
        qss = build_stylesheet(get_theme())
        for selector in ("QPushButton", "QLineEdit", "QTabBar::tab"):
            assert selector in qss


# ============================================================
# Icons
# ============================================================
class TestIcons:
    def test_list_icons_nonempty(self):
        icons = list_icons()
        assert len(icons) >= 30
        assert "save" in icons
        assert "delete" in icons

    def test_get_emoji_known(self):
        assert get_emoji("save") == "💾"
        assert get_emoji("error") == "❌"

    def test_get_emoji_unknown(self):
        assert get_emoji("nonexistent_icon_xyz") == "•"


# ============================================================
# RTL
# ============================================================
class TestRTL:
    def test_is_rtl_arabic(self):
        assert is_rtl_language("ar") is True

    def test_is_rtl_english(self):
        assert is_rtl_language("en") is False

    def test_is_ltr_english(self):
        assert is_ltr_language("en") is True

    def test_is_ltr_arabic(self):
        assert is_ltr_language("ar") is False

    def test_apply_language_arabic(self):
        apply_language("ar")
        assert current_language() == "ar"

    def test_apply_language_english(self):
        apply_language("en")
        assert current_language() == "en"

    def test_apply_language_case_insensitive(self):
        apply_language("AR")
        assert current_language() == "ar"

    def test_apply_language_empty_raises(self):
        with pytest.raises(ValueError):
            apply_language("")

    def test_language_name(self):
        assert language_name("ar") == "العربية"
        assert language_name("en") == "English"
        assert language_name("unknown") == "unknown"

    def test_list_languages(self):
        langs = list_languages()
        assert "ar" in langs
        assert "en" in langs