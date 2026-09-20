"""
Filesystem path helpers for Ghanyx.

Design goals:
    - No external dependencies (only stdlib).
    - Cross-platform (Windows / macOS / Linux).
    - Safe by default: never crash on missing dirs or bad input.
    - UTF-8 safe for Arabic and other non-ASCII names.

Typical usage:
    from ghanyx.utils.paths import ensure_dir, get_app_data_dir

    data_dir = get_app_data_dir("myapp")
    logs_dir = ensure_dir(data_dir / "logs")
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# ============================================================
# Constants
# ============================================================
_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


# ============================================================
# Public API
# ============================================================
def ensure_dir(path: str | os.PathLike[str]) -> Path:
    """
    Ensure a directory exists, creating it (and parents) if needed.

    Args:
        path: Directory path.

    Returns:
        The path as a Path object.

    Example:
        logs = ensure_dir("logs")
        db_dir = ensure_dir(Path("data") / "db")
    """
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_app_data_dir(app_name: str) -> Path:
    """
    Return the standard per-user data directory for an app,
    creating it if it doesn't exist.

    Locations:
        Windows : %APPDATA%\\<app_name>
        macOS   : ~/Library/Application Support/<app_name>
        Linux   : ~/.local/share/<app_name>

    Args:
        app_name: Name of the application (e.g., "myapp").

    Returns:
        Path to the app data directory (guaranteed to exist).
    """
    if not app_name or not app_name.strip():
        raise ValueError("app_name must be a non-empty string")

    app_name = app_name.strip()

    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        root = Path(base)
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
        root = Path(base)

    return ensure_dir(root / app_name)


def get_project_root() -> Path:
    """
    Return the project root directory.

    Uses the location of this file (`.../src/ghanyx/utils/paths.py`)
    and walks up 4 levels to reach the project root.

    Note: This is a best-effort guess. For installed packages, prefer
    explicit configuration over relying on this.

    Returns:
        Path to the project root.
    """
    return Path(__file__).resolve().parents[3]


def safe_filename(name: str, fallback: str = "file") -> str:
    """
    Convert an arbitrary string into a safe filename.

    - Removes characters that are illegal on Windows.
    - Strips leading/trailing spaces and dots.
    - Handles Windows reserved names (CON, PRN, ...).
    - Truncates to 200 characters.
    - Falls back to `fallback` if the result is empty.

    Args:
        name: Desired filename (without directory).
        fallback: Value to use if sanitization yields an empty string.

    Returns:
        A safe filename.

    Example:
        safe_filename("تقرير: 2026/09")  →  "تقرير 202609"
        safe_filename("CON")             →  "_CON"
        safe_filename("")                →  "file"
    """
    if not isinstance(name, str):
        return fallback

    cleaned = _UNSAFE_CHARS.sub("", name)
    cleaned = cleaned.strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)

    if not cleaned:
        return fallback

    stem = cleaned.split(".")[0].upper()
    if stem in _RESERVED_NAMES:
        cleaned = "_" + cleaned

    if len(cleaned) > 200:
        cleaned = cleaned[:200]

    return cleaned