"""
Icon helpers for Ghanyx.

Design:
    - Prefers Qt's built-in theme icons (works on any OS).
    - Falls back to emoji strings when Qt icons are unavailable.
    - Never crashes if PySide6 is missing (headless tests).

Usage:
    from ghanyx.ui.icons import icon_names, get_icon, get_emoji

    icon = get_icon("save")     # → QIcon (or None)
    text = get_emoji("save")    # → "💾"
"""

from __future__ import annotations

from typing import Final


# ============================================================
# Semantic icon names → emoji fallback
# ============================================================
EMOJI_MAP: Final[dict[str, str]] = {
    # File / actions
    "save":     "💾",
    "open":     "📂",
    "new":      "🆕",
    "delete":   "🗑️",
    "edit":     "✏️",
    "copy":     "📋",
    "paste":    "📋",
    "cut":      "✂️",
    "refresh":  "🔄",
    "search":   "🔍",
    "filter":   "🔽",
    "export":   "📤",
    "import":   "📥",
    "print":    "🖨️",
    "backup":   "📦",
    "restore":  "♻️",

    # Navigation
    "home":     "🏠",
    "back":     "⬅️",
    "forward":  "➡️",
    "up":       "⬆️",
    "down":     "⬇️",
    "menu":     "☰",
    "settings": "⚙️",

    # Status
    "ok":       "✅",
    "error":    "❌",
    "warning":  "⚠️",
    "info":     "ℹ️",
    "help":     "❓",
    "loading":  "⏳",

    # People
    "user":     "👤",
    "users":    "👥",
    "admin":    "👑",
    "guest":    "🎭",

    # Business
    "money":    "💰",
    "cart":     "🛒",
    "receipt":  "🧾",
    "chart":    "📊",
    "calendar": "📅",
    "clock":    "🕐",
    "inventory": "📦",
    "lock":     "🔒",
    "key":      "🔑",
    "shield":   "🛡️",

    # Files
    "database": "🗄️",
    "file":     "📄",
    "folder":   "📁",
    "log":      "📜",
    "config":   "⚙️",
}


# ============================================================
# Public API
# ============================================================
def list_icons() -> list[str]:
    """Return the names of all known icons."""
    return sorted(EMOJI_MAP.keys())


def get_emoji(name: str) -> str:
    """Return the emoji for a semantic icon name."""
    return EMOJI_MAP.get(name, "•")


def get_icon(name: str):
    """
    Return a QIcon for a semantic name, or None.

    - On Qt, tries the system theme first (works on Linux/KDE/GNOME).
    - Falls back to a small set of standard Qt icons.
    - Returns None if Qt is not available (headless mode).
    """
    try:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication
    except ImportError:
        return None

    # 1) System theme icon
    try:
        if QApplication.instance() is not None:
            icon = QIcon.fromTheme(name)
            if not icon.isNull():
                return icon
    except Exception:
        pass

    # 2) Standard Qt icons (a few common ones)
    qt_map = {
        "save":    "SP_DialogSaveButton",
        "open":    "SP_DialogOpenButton",
        "delete":  "SP_TrashIcon",
        "refresh": "SP_BrowserReload",
        "ok":      "SP_DialogApplyButton",
        "error":   "SP_MessageBoxCritical",
        "warning": "SP_MessageBoxWarning",
        "info":    "SP_MessageBoxInformation",
        "help":    "SP_DialogHelpButton",
        "home":    "SP_DirHomeIcon",
        "file":    "SP_FileIcon",
        "folder":  "SP_DirIcon",
    }
    qt_name = qt_map.get(name)
    if qt_name:
        try:
            from PySide6.QtWidgets import QStyle
            app = QApplication.instance()
            if app is not None:
                style = app.style()
                sp = getattr(QStyle.StandardPixmap, qt_name, None)
                if sp is not None:
                    return style.standardIcon(sp)
        except Exception:
            pass

    return None


def icon_or_emoji(name: str) -> str:
    """
    Convenience: return a QIcon if available, else the emoji string.
    Useful when you want graceful degradation in UI.
    """
    icon = get_icon(name)
    return icon if icon is not None else get_emoji(name)  # type: ignore[return-value]