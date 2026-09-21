"""
Session management for Ghanyx.

Sessions provide a way to remember a user after login without
re-authenticating on every action.

Two levels:
    1. In-memory session (fast, lost on app exit).
    2. Persistent session (saved to a JSON file, survives restarts).

Security notes:
    - Session tokens are 256-bit random (via secrets.token_urlsafe).
    - Tokens have an expiration time (default 8 hours).
    - A token is bound to a device fingerprint (best-effort).
    - Session files are written with restrictive permissions.
    - On load, expired or tampered sessions are rejected.

Usage:
    from ghanyx.auth.session import Session, SessionManager

    mgr = SessionManager()

    # Create + persist
    session = mgr.create(user)
    mgr.save(session, ".session")

    # Restore
    session = mgr.load(".session")
    if session and not session.is_expired:
        user = mgr.restore_user(session, user_lookup)
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import secrets
import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from ghanyx.auth.exceptions import (
    InvalidSessionError,
    SessionExpiredError,
)
from ghanyx.auth.user import User
from ghanyx.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Defaults
# ============================================================
DEFAULT_TTL_HOURS: int = 8
DEFAULT_TTL = timedelta(hours=DEFAULT_TTL_HOURS)


# ============================================================
# Device fingerprint
# ============================================================
def device_fingerprint() -> str:
    """
    Return a best-effort stable fingerprint for the current device.

    Combines several cheap identifiers and hashes them. This is NOT
    a security boundary — just a convenience check to detect obvious
    session theft (e.g., copying a file to another machine).
    """
    parts = [
        platform.node(),
        platform.system(),
        platform.machine(),
        socket.gethostname(),
    ]
    try:
        parts.append(str(os.getuid()))
    except AttributeError:
        # Windows doesn't have os.getuid
        parts.append(os.environ.get("USERNAME", ""))

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ============================================================
# Session
# ============================================================
@dataclass(frozen=True)
class Session:
    """
    An authenticated session.

    Attributes:
        token: Opaque random token (256 bits, base64).
        user_id: The user's DB ID.
        username: The user's username (for convenience).
        role: Cached role at login time.
        created_at: ISO timestamp.
        expires_at: ISO timestamp.
        device: Device fingerprint at login time.
        metadata: Optional free-form dict.
    """

    token: str
    user_id: int | None
    username: str
    role: str
    created_at: str
    expires_at: str
    device: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Time checks
    # ------------------------------------------------------------------
    @property
    def created_at_dt(self) -> datetime:
        return datetime.fromisoformat(self.created_at)

    @property
    def expires_at_dt(self) -> datetime:
        return datetime.fromisoformat(self.expires_at)

    @property
    def is_expired(self) -> bool:
        return datetime.now() >= self.expires_at_dt

    @property
    def time_left(self) -> timedelta:
        remaining = self.expires_at_dt - datetime.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    @property
    def is_valid(self) -> bool:
        """True if not expired and device matches."""
        if self.is_expired:
            return False
        if self.device and self.device != device_fingerprint():
            return False
        return True

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "device": self.device,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        try:
            return cls(
                token=data["token"],
                user_id=data.get("user_id"),
                username=data.get("username", ""),
                role=data.get("role", ""),
                created_at=data["created_at"],
                expires_at=data["expires_at"],
                device=data.get("device", ""),
                metadata=dict(data.get("metadata", {})),
            )
        except KeyError as e:
            raise InvalidSessionError() from e

    def __repr__(self) -> str:
        return (
            f"Session(user={self.username!r}, "
            f"expires_at={self.expires_at!r})"
        )


# ============================================================
# SessionManager
# ============================================================
class SessionManager:
    """
    Creates, validates, saves, and loads sessions.

    Args:
        ttl: Session lifetime (default 8 hours).
        require_device_match: Reject sessions from other devices.
    """

    def __init__(
        self,
        *,
        ttl: timedelta = DEFAULT_TTL,
        require_device_match: bool = True,
    ) -> None:
        self.ttl = ttl
        self.require_device_match = require_device_match

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    def create(self, user: User) -> Session:
        """Create a new session for a user."""
        now = datetime.now()
        expires = now + self.ttl

        session = Session(
            token=secrets.token_urlsafe(32),  # 256 bits
            user_id=user.id,
            username=user.username,
            role=user.role,
            created_at=now.isoformat(timespec="seconds"),
            expires_at=expires.isoformat(timespec="seconds"),
            device=device_fingerprint() if self.require_device_match else "",
            metadata={},
        )
        logger.info(
            "Session created for user='%s' (expires %s)",
            user.username, session.expires_at,
        )
        return session

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------
    def validate(self, session: Session | None) -> Session:
        """
        Validate a session.

        Returns:
            The session if valid.

        Raises:
            InvalidSessionError: if the session is malformed or from
                another device.
            SessionExpiredError: if expired.
        """
        if session is None:
            raise InvalidSessionError()

        if session.is_expired:
            raise SessionExpiredError(session_id=session.token[:8])

        if (
            self.require_device_match
            and session.device
            and session.device != device_fingerprint()
        ):
            raise InvalidSessionError(session_id=session.token[:8])

        return session

    def restore_user(
        self,
        session: Session,
        lookup: Callable[[int], User | None],
    ) -> User | None:
        """
        Validate the session and fetch the corresponding User.

        Args:
            session: The session to restore.
            lookup: A callable that returns a User by ID.

        Returns:
            The User, or None if not found.
        """
        self.validate(session)
        if session.user_id is None:
            return None
        return lookup(session.user_id)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(
        self,
        session: Session,
        path: str | os.PathLike[str],
    ) -> Path:
        """
        Save a session to a JSON file with restrictive permissions.

        Returns the path written.
        """
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "version": 1,
            "session": session.to_dict(),
        }

        # Write atomically (write to .tmp then rename)
        tmp = p.with_suffix(p.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)

        # Restrict permissions (Unix only; no-op on Windows)
        try:
            os.chmod(p, 0o600)
        except (OSError, NotImplementedError):
            pass

        logger.debug("Session saved to %s", p)
        return p

    def load(
        self,
        path: str | os.PathLike[str],
    ) -> Session | None:
        """
        Load a session from a JSON file.

        Returns:
            The Session, or None if the file doesn't exist or is invalid.
        """
        p = Path(path).expanduser()
        if not p.exists():
            return None

        try:
            with p.open("r", encoding="utf-8") as f:
                payload = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read session file %s: %s", p, e)
            return None

        if not isinstance(payload, dict) or "session" not in payload:
            logger.warning("Malformed session file: %s", p)
            return None

        try:
            session = Session.from_dict(payload["session"])
        except (InvalidSessionError, KeyError, TypeError) as e:
            logger.warning("Invalid session data in %s: %s", p, e)
            return None

        return session

    def clear(self, path: str | os.PathLike[str]) -> None:
        """Delete a saved session file, if it exists."""
        p = Path(path).expanduser()
        try:
            if p.exists():
                p.unlink()
                logger.debug("Session cleared: %s", p)
        except OSError as e:
            logger.warning("Failed to clear session %s: %s", p, e)