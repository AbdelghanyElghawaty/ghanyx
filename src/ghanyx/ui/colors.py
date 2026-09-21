"""
Color palettes for Ghanyx.

Design:
    - Every theme is a named `Palette` — a mapping of semantic
      role → hex color.
    - Semantic roles are stable: `bg`, `surface`, `text`, `primary`, ...
      so widget code doesn't depend on which theme is active.
    - Palettes can be mixed, overridden, or extended at runtime.
    - All colors are validated to be valid hex strings.

Usage:
    from ghanyx.ui.colors import PALETTES, get_palette

    dark = get_palette("dark_navy")
    print(dark["primary"])   # → "#3b82f6"
"""

from __future__ import annotations

import re
from typing import Final

# ============================================================
# Color validation
# ============================================================
_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def is_valid_hex(color: str) -> bool:
    """Return True if `color` is a valid #RGB or #RRGGBB hex string."""
    return bool(_HEX_RE.match(color))


# ============================================================
# Semantic roles
# ============================================================
#: The set of roles every palette MUST define.
#: Keep this stable — widget code depends on these keys.
REQUIRED_ROLES: Final[tuple[str, ...]] = (
    # Surfaces
    "bg",              # main window background
    "surface",         # cards / panels
    "surface_alt",     # alt cards / hover
    "border",          # subtle borders
    "border_strong",   # emphasized borders

    # Text
    "text",            # primary text
    "text_muted",      # secondary text
    "text_dim",        # very subtle text

    # Brand
    "primary",         # primary brand color
    "primary_hover",
    "primary_dark",

    # Semantic
    "success",
    "success_hover",
    "warning",
    "danger",
    "danger_hover",
    "info",
    "gold",            # highlight / accent

    # UI chrome
    "statusbar",       # status bar background
    "tooltip",         # tooltip background
)


# ============================================================
# Palettes
# ============================================================
PALETTES: Final[dict[str, dict[str, str]]] = {

    # ----- Dark Navy (default) -----
    "dark_navy": {
        "bg":             "#0f172a",
        "surface":        "#1e293b",
        "surface_alt":    "#334155",
        "border":         "#334155",
        "border_strong":  "#475569",

        "text":           "#f1f5f9",
        "text_muted":     "#94a3b8",
        "text_dim":       "#64748b",

        "primary":        "#3b82f6",
        "primary_hover":  "#2563eb",
        "primary_dark":   "#1d4ed8",

        "success":        "#10b981",
        "success_hover":  "#059669",
        "warning":        "#f59e0b",
        "danger":         "#ef4444",
        "danger_hover":   "#dc2626",
        "info":           "#0ea5e9",
        "gold":           "#fbbf24",

        "statusbar":      "#020617",
        "tooltip":        "#1e293b",
    },

    # ----- Dark Purple -----
    "dark_purple": {
        "bg":             "#1a0f2e",
        "surface":        "#2d1b4e",
        "surface_alt":    "#3f2963",
        "border":         "#4c3575",
        "border_strong":  "#6b4ba0",

        "text":           "#f3e8ff",
        "text_muted":     "#c4b5fd",
        "text_dim":       "#9f7aea",

        "primary":        "#a855f7",
        "primary_hover":  "#9333ea",
        "primary_dark":   "#7e22ce",

        "success":        "#10b981",
        "success_hover":  "#059669",
        "warning":        "#f59e0b",
        "danger":         "#ef4444",
        "danger_hover":   "#dc2626",
        "info":           "#38bdf8",
        "gold":           "#fbbf24",

        "statusbar":      "#0f0820",
        "tooltip":        "#2d1b4e",
    },

    # ----- Light Clean -----
    "light_clean": {
        "bg":             "#f8fafc",
        "surface":        "#ffffff",
        "surface_alt":    "#f1f5f9",
        "border":         "#e2e8f0",
        "border_strong":  "#cbd5e1",

        "text":           "#0f172a",
        "text_muted":     "#475569",
        "text_dim":       "#94a3b8",

        "primary":        "#2563eb",
        "primary_hover":  "#1d4ed8",
        "primary_dark":   "#1e40af",

        "success":        "#059669",
        "success_hover":  "#047857",
        "warning":        "#d97706",
        "danger":         "#dc2626",
        "danger_hover":   "#b91c1c",
        "info":           "#0284c7",
        "gold":           "#ca8a04",

        "statusbar":      "#e2e8f0",
        "tooltip":        "#1e293b",
    },

    # ----- Nord (popular palette) -----
    "nord": {
        "bg":             "#2e3440",
        "surface":        "#3b4252",
        "surface_alt":    "#434c5e",
        "border":         "#4c566a",
        "border_strong":  "#616e88",

        "text":           "#eceff4",
        "text_muted":     "#d8dee9",
        "text_dim":       "#7b88a1",

        "primary":        "#88c0d0",
        "primary_hover":  "#8fbcbb",
        "primary_dark":   "#5e81ac",

        "success":        "#a3be8c",
        "success_hover":  "#8faf7d",
        "warning":        "#ebcb8b",
        "danger":         "#bf616a",
        "danger_hover":   "#a54d55",
        "info":           "#81a1c1",
        "gold":           "#ebcb8b",

        "statusbar":      "#242933",
        "tooltip":        "#3b4252",
    },

    # ----- Sunset (warm) -----
    "sunset": {
        "bg":             "#1f1410",
        "surface":        "#2d1e18",
        "surface_alt":    "#3d2a21",
        "border":         "#4d3630",
        "border_strong":  "#6b4a3f",

        "text":           "#fff5ed",
        "text_muted":     "#d4a895",
        "text_dim":       "#a67c6a",

        "primary":        "#f97316",
        "primary_hover":  "#ea580c",
        "primary_dark":   "#c2410c",

        "success":        "#84cc16",
        "success_hover":  "#65a30d",
        "warning":        "#fbbf24",
        "danger":         "#ef4444",
        "danger_hover":   "#dc2626",
        "info":           "#06b6d4",
        "gold":           "#fcd34d",

        "statusbar":      "#140c08",
        "tooltip":        "#2d1e18",
    },

    # ----- Forest (green) -----
    "forest": {
        "bg":             "#0d1a14",
        "surface":        "#14261d",
        "surface_alt":    "#1e3628",
        "border":         "#2a4735",
        "border_strong":  "#3d6249",

        "text":           "#ecfdf5",
        "text_muted":     "#86efac",
        "text_dim":       "#4ade80",

        "primary":        "#22c55e",
        "primary_hover":  "#16a34a",
        "primary_dark":   "#15803d",

        "success":        "#10b981",
        "success_hover":  "#059669",
        "warning":        "#f59e0b",
        "danger":         "#ef4444",
        "danger_hover":   "#dc2626",
        "info":           "#06b6d4",
        "gold":           "#fbbf24",

        "statusbar":      "#07110c",
        "tooltip":        "#14261d",
    },
}


# ============================================================
# Helpers
# ============================================================
def validate_palette(name: str, palette: dict[str, str]) -> None:
    """
    Ensure a palette defines all REQUIRED_ROLES and uses valid hex.

    Raises:
        ValueError: if any role is missing or a color is invalid.
    """
    missing = [r for r in REQUIRED_ROLES if r not in palette]
    if missing:
        raise ValueError(
            f"Palette '{name}' is missing required roles: {missing}"
        )

    for role, value in palette.items():
        if not is_valid_hex(value):
            raise ValueError(
                f"Palette '{name}' has invalid color for '{role}': {value!r}"
            )


def get_palette(name: str) -> dict[str, str]:
    """
    Return a copy of the named palette.

    Raises:
        KeyError: if the name is not registered.
    """
    if name not in PALETTES:
        raise KeyError(
            f"Unknown palette: {name!r}. "
            f"Available: {sorted(PALETTES.keys())}"
        )
    return dict(PALETTES[name])


def list_palettes() -> list[str]:
    """Return the names of all registered palettes."""
    return sorted(PALETTES.keys())


def is_dark(name: str) -> bool:
    """Best-effort guess: is the palette dark or light?"""
    if name not in PALETTES:
        return True  # default: dark
    bg = PALETTES[name]["bg"].lstrip("#")
    # Expand #RGB to #RRGGBB
    if len(bg) == 3:
        bg = "".join(c * 2 for c in bg)
    try:
        r, g, b = (int(bg[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return True
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance < 0.5


def register_palette(
    name: str,
    palette: dict[str, str],
    *,
    overwrite: bool = False,
) -> None:
    """
    Register a custom palette.

    Args:
        name: Palette name.
        palette: Mapping of role → hex color.
        overwrite: Whether to replace an existing palette.

    Raises:
        ValueError: if a palette with the same name exists and
            `overwrite` is False.
    """
    if not name:
        raise ValueError("Palette name must not be empty")
    if name in PALETTES and not overwrite:
        raise ValueError(f"Palette '{name}' already exists")
    validate_palette(name, palette)
    PALETTES[name] = dict(palette)


# ============================================================
# Validate all built-in palettes at import time
# ============================================================
for _name, _palette in PALETTES.items():
    validate_palette(_name, _palette)
del _name, _palette