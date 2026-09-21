"""
Theme system for Ghanyx.

A "theme" is a named palette + a dark/light flag + a set of
font overrides. The `ThemeManager` controls the current theme and
notifies listeners when it changes.

Design:
    - One global `ThemeManager` (via `get_theme_manager()`).
    - `Theme` = palette + is_dark + fonts.
    - Listeners can subscribe to theme changes.
    - Convenience `color(role)` for quick lookups.

Usage:
    from ghanyx.ui.theme import (
        get_theme_manager, set_theme, color, is_dark,
    )

    set_theme("dark_purple")
    print(color("primary"))   # → "#a855f7"
    print(is_dark())          # → True

    # Subscribe to changes
    tm = get_theme_manager()
    tm.subscribe(lambda theme: print("Theme changed:", theme.name))
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from threading import RLock
from typing import Callable, Iterable

from ghanyx.logging import get_logger
from ghanyx.ui.colors import (
    PALETTES,
    REQUIRED_ROLES,
    get_palette,
    is_dark as palette_is_dark,
    list_palettes,
    register_palette,
    validate_palette,
)

logger = get_logger(__name__)


# ============================================================
# Defaults
# ============================================================
DEFAULT_THEME_NAME: str = "dark_navy"

DEFAULT_FONT_FAMILY: str = "Segoe UI"
DEFAULT_FONT_SIZE: int = 10
DEFAULT_MONO_FONT_FAMILY: str = "Consolas"


# ============================================================
# Theme
# ============================================================
@dataclass(frozen=True)
class Theme:
    """
    An immutable theme: palette + metadata.

    Attributes:
        name: Human-readable name (e.g., "dark_navy").
        colors: Mapping of role → hex color.
        is_dark: Whether this is a dark theme.
        font_family: Default font family.
        font_size: Default font size in points.
        mono_font_family: Monospace font for code/numbers.
    """

    name: str
    colors: dict[str, str] = field(default_factory=dict)
    is_dark: bool = True
    font_family: str = DEFAULT_FONT_FAMILY
    font_size: int = DEFAULT_FONT_SIZE
    mono_font_family: str = DEFAULT_MONO_FONT_FAMILY

    # ------------------------------------------------------------------
    # Color access
    # ------------------------------------------------------------------
    def color(self, role: str, *, default: str = "#000000") -> str:
        """
        Return the hex color for a semantic role.

        Falls back to `default` if the role is unknown.
        """
        return self.colors.get(role, default)

    def with_color(self, role: str, value: str) -> "Theme":
        """Return a copy of this theme with one color overridden."""
        if role not in self.colors:
            raise KeyError(f"Unknown role: {role!r}")
        new_colors = dict(self.colors)
        new_colors[role] = value
        validate_palette(self.name, new_colors)
        return replace(self, colors=new_colors)

    def with_font(self, family: str, size: int | None = None) -> "Theme":
        """Return a copy with a different font."""
        return replace(
            self,
            font_family=family,
            font_size=size if size is not None else self.font_size,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "colors": dict(self.colors),
            "is_dark": self.is_dark,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "mono_font_family": self.mono_font_family,
        }

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        mode = "dark" if self.is_dark else "light"
        return f"<Theme {self.name!r} ({mode})>"


# ============================================================
# Theme registry
# ============================================================
class ThemeRegistry:
    """
    Registry of available themes.

    Themes are built from palettes. When a new palette is registered,
    a corresponding Theme is created automatically.
    """

    def __init__(self) -> None:
        self._themes: dict[str, Theme] = {}
        self._lock = RLock()
        # Register every built-in palette as a theme
        for name in list_palettes():
            self._register_from_palette(name)

    # ----- Register -----
    def _register_from_palette(self, name: str) -> Theme:
        theme = Theme(
            name=name,
            colors=get_palette(name),
            is_dark=palette_is_dark(name),
        )
        self._themes[name] = theme
        return theme

    def register(
        self,
        name: str,
        palette: dict[str, str] | None = None,
        *,
        overwrite: bool = False,
    ) -> Theme:
        """
        Register a new theme from a palette (or the existing palette).
        """
        with self._lock:
            if name in self._themes and not overwrite:
                raise ValueError(f"Theme '{name}' already exists")
            if palette is not None:
                register_palette(name, palette, overwrite=overwrite)
            return self._register_from_palette(name)

    # ----- Access -----
    def get(self, name: str) -> Theme:
        with self._lock:
            if name not in self._themes:
                raise KeyError(
                    f"Unknown theme: {name!r}. "
                    f"Available: {self.names()}"
                )
            return self._themes[name]

    def has(self, name: str) -> bool:
        return name in self._themes

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._themes.keys())

    def all(self) -> list[Theme]:
        with self._lock:
            return [self._themes[n] for n in sorted(self._themes.keys())]

    # ----- Mutation -----
    def update(self, theme: Theme, *, overwrite: bool = True) -> None:
        """Replace or add a Theme instance directly."""
        with self._lock:
            if theme.name in self._themes and not overwrite:
                raise ValueError(f"Theme '{theme.name}' already exists")
            self._themes[theme.name] = theme


# ============================================================
# ThemeManager
# ============================================================
ListenerFn = Callable[[Theme], None]


class ThemeManager:
    """
    Manages the current theme and notifies listeners on change.

    Thread-safe. One instance is shared globally.
    """

    def __init__(
        self,
        registry: ThemeRegistry | None = None,
        initial: str = DEFAULT_THEME_NAME,
    ) -> None:
        self.registry = registry or ThemeRegistry()
        self._lock = RLock()
        self._listeners: list[ListenerFn] = []
        self._current: Theme = self.registry.get(initial)

    # ----- Current theme -----
    @property
    def current(self) -> Theme:
        return self._current

    @property
    def name(self) -> str:
        return self._current.name

    def set(self, name: str) -> Theme:
        """
        Switch to the named theme and notify listeners.

        Returns the new Theme.

        Raises:
            KeyError: if the theme is not registered.
        """
        theme = self.registry.get(name)
        with self._lock:
            if theme.name == self._current.name:
                return self._current
            self._current = theme
            listeners = list(self._listeners)

        logger.info("Theme changed to '%s'", name)

        # Notify outside the lock to avoid deadlocks
        for fn in listeners:
            try:
                fn(theme)
            except Exception:
                logger.exception("Theme listener raised")

        return theme

    # ----- Listeners -----
    def subscribe(self, fn: ListenerFn) -> Callable[[], None]:
        """
        Register a listener; returns a function to unsubscribe.
        """
        with self._lock:
            self._listeners.append(fn)

        def _unsubscribe() -> None:
            with self._lock:
                if fn in self._listeners:
                    self._listeners.remove(fn)

        return _unsubscribe

    def unsubscribe(self, fn: ListenerFn) -> None:
        with self._lock:
            if fn in self._listeners:
                self._listeners.remove(fn)

    def clear_listeners(self) -> None:
        with self._lock:
            self._listeners.clear()

    # ----- Convenience -----
    def color(self, role: str, *, default: str = "#000000") -> str:
        return self._current.color(role, default=default)

    @property
    def is_dark(self) -> bool:
        return self._current.is_dark

    def list_themes(self) -> list[str]:
        return self.registry.names()

    def toggle_dark_light(self) -> Theme:
        """
        Toggle between the current theme's family (dark ↔ light).

        Picks "light_clean" if currently dark and "dark_navy" if light.
        """
        target = "light_clean" if self._current.is_dark else "dark_navy"
        if not self.registry.has(target):
            raise KeyError(
                f"Cannot toggle: '{target}' is not registered"
            )
        return self.set(target)


# ============================================================
# Global singleton
# ============================================================
_manager: ThemeManager | None = None
_manager_lock = RLock()


def get_theme_manager() -> ThemeManager:
    """Return the global ThemeManager, creating it on first call."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = ThemeManager()
    return _manager


def set_theme(name: str) -> Theme:
    """Switch the global theme."""
    return get_theme_manager().set(name)


def get_theme() -> Theme:
    """Return the current global theme."""
    return get_theme_manager().current


def color(role: str, *, default: str = "#000000") -> str:
    """Shortcut: current theme's color for a role."""
    return get_theme_manager().color(role, default=default)


def is_dark() -> bool:
    """Shortcut: is the current theme dark?"""
    return get_theme_manager().is_dark


def reset_theme_manager() -> None:
    """Clear the global manager (mainly for tests)."""
    global _manager
    with _manager_lock:
        _manager = None