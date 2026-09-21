"""
Ghanyx UI — theming, styles, icons, and RTL helpers.

Public API:
    # Colors
    PALETTES            → Built-in palettes.
    REQUIRED_ROLES      → Semantic roles every palette must define.
    get_palette()       → Copy of a palette.
    list_palettes()     → Names of all palettes.
    register_palette()  → Add a custom palette.
    is_valid_hex()      → Color validation helper.

    # Theme
    Theme               → Immutable theme (palette + metadata).
    ThemeRegistry       → Registry of themes.
    ThemeManager        → Current theme + listeners.
    get_theme_manager() → Global singleton.
    get_theme()         → Current Theme.
    set_theme()         → Switch the global theme.
    color()             → Shortcut: current color by role.
    is_dark()           → Shortcut: is the current theme dark?

    # Styles
    build_stylesheet()  → Full QSS string for a Theme.

    # Icons
    get_icon()          → QIcon or None.
    get_emoji()         → Emoji fallback.
    list_icons()        → All known icon names.

    # RTL
    apply_language()    → Switch app layout direction.
    is_rtl_language()   → Check if a language is RTL.
    current_language()  → Currently applied language.

Quick start:
    from ghanyx.ui import set_theme, color, build_stylesheet, apply_language

    set_theme("dark_purple")
    app.setStyleSheet(build_stylesheet(get_theme()))
    apply_language("ar")
"""

# ----- Colors -----
from ghanyx.ui.colors import (
    PALETTES,
    REQUIRED_ROLES,
    get_palette,
    is_valid_hex,
    list_palettes,
    register_palette,
)

# ----- Theme -----
from ghanyx.ui.theme import (
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_MONO_FONT_FAMILY,
    DEFAULT_THEME_NAME,
    Theme,
    ThemeManager,
    ThemeRegistry,
    color,
    get_theme,
    get_theme_manager,
    is_dark,
    reset_theme_manager,
    set_theme,
)

# ----- Styles -----
from ghanyx.ui.styles import build_stylesheet

# ----- Icons -----
from ghanyx.ui.icons import (
    get_emoji,
    get_icon,
    icon_or_emoji,
    list_icons,
)

# ----- RTL -----
from ghanyx.ui.rtl import (
    apply_language,
    current_language,
    is_ltr_language,
    is_rtl_language,
    language_name,
    list_languages,
)

__all__ = [
    # Colors
    "PALETTES",
    "REQUIRED_ROLES",
    "get_palette",
    "is_valid_hex",
    "list_palettes",
    "register_palette",

    # Theme
    "Theme",
    "ThemeRegistry",
    "ThemeManager",
    "get_theme_manager",
    "get_theme",
    "set_theme",
    "color",
    "is_dark",
    "reset_theme_manager",

    # Styles
    "build_stylesheet",

    # Icons
    "get_icon",
    "get_emoji",
    "icon_or_emoji",
    "list_icons",

    # RTL
    "apply_language",
    "is_rtl_language",
    "is_ltr_language",
    "current_language",
    "language_name",
    "list_languages",

    # Constants
    "DEFAULT_THEME_NAME",
    "DEFAULT_FONT_FAMILY",
    "DEFAULT_FONT_SIZE",
    "DEFAULT_MONO_FONT_FAMILY",
]