"""
RTL/LTR helpers for Ghanyx.

Many apps need to switch layout direction at runtime
(e.g., Arabic ↔ English). This module provides safe helpers
that work even if PySide6 isn't available.

Usage:
    from ghanyx.ui.rtl import (
        is_rtl_language, apply_language, current_language,
        language_name, list_languages,
    )

    apply_language("ar")   # → switches app to RTL
    apply_language("en")   # → switches app to LTR
"""

from __future__ import annotations

from typing import Final


# ============================================================
# Known languages
# ============================================================
RTL_LANGUAGES: Final[frozenset[str]] = frozenset({
    "ar", "he", "fa", "ur",  # Arabic, Hebrew, Persian, Urdu
})

LTR_LANGUAGES: Final[frozenset[str]] = frozenset({
    "en", "fr", "es", "de", "it", "pt", "tr", "ru",
})

LANGUAGE_NAMES: Final[dict[str, str]] = {
    "ar": "العربية",
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "de": "Deutsch",
    "tr": "Türkçe",
}


# ============================================================
# State
# ============================================================
_current_language: str = "en"


# ============================================================
# Queries
# ============================================================
def is_rtl_language(code: str) -> bool:
    """Return True if the language code uses RTL layout."""
    return (code or "").lower() in RTL_LANGUAGES


def is_ltr_language(code: str) -> bool:
    """Return True if the language code uses LTR layout."""
    return (code or "").lower() in LTR_LANGUAGES


def list_languages() -> list[str]:
    """Return the list of known language codes."""
    return sorted(RTL_LANGUAGES | LTR_LANGUAGES)


def language_name(code: str) -> str:
    """Return the human-readable name of a language."""
    return LANGUAGE_NAMES.get((code or "").lower(), code)


def current_language() -> str:
    """Return the currently applied language code."""
    return _current_language


# ============================================================
# Apply
# ============================================================
def apply_language(code: str) -> None:
    """
    Apply a language to the running Qt application.

    - Sets layout direction (RTL or LTR).
    - Updates the module's `current_language()` value.
    - Safe to call even without PySide6 (no-op fallback).

    Raises:
        ValueError: if the language code is empty.
    """
    global _current_language

    code = (code or "").strip().lower()
    if not code:
        raise ValueError("language code must not be empty")

    _current_language = code

    # Try to apply to Qt (if available)
    try:
        from PySide6.QtCore import Qt, QLocale
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            direction = Qt.RightToLeft if is_rtl_language(code) else Qt.LeftToRight
            app.setLayoutDirection(direction)

            # Best-effort locale hint (does not always affect Qt text)
            try:
                QLocale.setDefault(QLocale(code))
            except Exception:
                pass
    except ImportError:
        # Headless — nothing to do
        pass