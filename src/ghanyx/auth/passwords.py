"""
Password hashing utilities for Ghanyx.

Design goals:
    - OWASP 2024-compliant by default (PBKDF2-SHA512, 600k iterations).
    - Algorithm-agile: stored hash carries algorithm + iterations + salt,
      so we can upgrade in the future without breaking existing hashes.
    - Constant-time comparison to prevent timing attacks.
    - Optional "pepper": an application-wide secret kept in config/env,
      added to every password before hashing. Protects against DB leaks
      where the attacker doesn't have the app config.
    - Auto-upgrade: when verifying a hash that used fewer iterations
      (or an older algorithm), the caller can rehash transparently.

Storage format:
    pbkdf2_sha512$<iterations>$<salt_hex>$<hash_hex>

Example:
    pbkdf2_sha512$600000$a1b2c3...$9f8e7d...

Public API:
    hash_password(password)          → str
    verify_password(password, hash)  → bool
    needs_rehash(hash)               → bool
    PasswordPolicy                   → validation rules
    validate_password(password)      → raises PasswordValidationError
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass, field
from typing import Final

from ghanyx.auth.exceptions import PasswordValidationError


# ============================================================
# Constants
# ============================================================
#: Default algorithm. SHA512 is preferred over SHA256 in 2024.
DEFAULT_ALGORITHM: Final[str] = "pbkdf2_sha512"

#: OWASP 2024 recommendation for PBKDF2-HMAC-SHA512.
DEFAULT_ITERATIONS: Final[int] = 600_000

#: Minimum acceptable iterations — used by `needs_rehash`.
MIN_ITERATIONS: Final[int] = 200_000

#: Salt size in bytes.
SALT_BYTES: Final[int] = 32

#: Pepper environment variable name.
PEPPER_ENV_VAR: Final[str] = "GHANYX_AUTH_PEPPER"

#: Supported algorithms (for future agility).
SUPPORTED_ALGORITHMS: Final[tuple[str, ...]] = (
    "pbkdf2_sha512",
    "pbkdf2_sha256",
)

#: Number of hex chars in a salt string.
_SALT_HEX_LEN: Final[int] = SALT_BYTES * 2


# ============================================================
# Pepper
# ============================================================
def _get_pepper() -> bytes:
    """
    Return the application-wide pepper as bytes.

    Reads from the GHANYX_AUTH_PEPPER environment variable. If unset,
    returns an empty bytes — no pepper is applied.

    Note: a pepper is optional. When set, it MUST remain stable across
    deployments, otherwise all passwords become invalid.
    """
    raw = os.environ.get(PEPPER_ENV_VAR, "")
    if not raw:
        return b""
    return raw.encode("utf-8")


def _combine(password: str, pepper: bytes) -> bytes:
    """Combine password and pepper deterministically."""
    pwd_bytes = password.encode("utf-8")
    if not pepper:
        return pwd_bytes
    # HMAC ensures pepper isn't just concatenated (better mixing)
    return hmac.new(pepper, pwd_bytes, hashlib.sha256).digest()


# ============================================================
# Hashing
# ============================================================
def hash_password(
    password: str,
    *,
    algorithm: str = DEFAULT_ALGORITHM,
    iterations: int = DEFAULT_ITERATIONS,
) -> str:
    """
    Hash a password using PBKDF2 + salt (+ optional pepper).

    Args:
        password: Plaintext password.
        algorithm: "pbkdf2_sha512" or "pbkdf2_sha256".
        iterations: Number of iterations.

    Returns:
        Encoded hash string:
            pbkdf2_sha512$600000$<salt_hex>$<hash_hex>

    Raises:
        ValueError: if algorithm unsupported or iterations < MIN_ITERATIONS.
        PasswordValidationError: if password is empty.
    """
    if not password:
        raise PasswordValidationError("password must not be empty")

    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    if iterations < MIN_ITERATIONS:
        raise ValueError(
            f"iterations must be >= {MIN_ITERATIONS}, got {iterations}"
        )

    digest = algorithm.replace("pbkdf2_", "")
    salt = secrets.token_bytes(SALT_BYTES)
    pepper = _get_pepper()

    payload = _combine(password, pepper)

    dk = hashlib.pbkdf2_hmac(
        digest,
        payload,
        salt,
        iterations,
        dklen=64,  # 512 bits
    )

    return f"{algorithm}${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a stored hash.

    Uses constant-time comparison (hmac.compare_digest) to prevent
    timing attacks.

    Returns:
        True if the password matches, False otherwise.
    """
    if not password or not stored_hash:
        return False

    try:
        algorithm, iterations_str, salt_hex, expected_hex = stored_hash.split("$")
        iterations = int(iterations_str)
    except (ValueError, AttributeError):
        return False

    if algorithm not in SUPPORTED_ALGORITHMS:
        return False

    if len(salt_hex) != _SALT_HEX_LEN:
        return False

    digest = algorithm.replace("pbkdf2_", "")
    pepper = _get_pepper()
    payload = _combine(password, pepper)

    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False

    try:
        dk = hashlib.pbkdf2_hmac(
            digest,
            payload,
            salt,
            iterations,
            dklen=64,
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(dk.hex(), expected_hex)


def needs_rehash(stored_hash: str) -> bool:
    """
    Return True if the stored hash uses an outdated algorithm or
    too-few iterations and should be rehashed.

    Call this after a successful `verify_password()` and, if True,
    rehash the password and update the stored value.

    Returns:
        True if rehash is recommended.
    """
    if not stored_hash:
        return True

    try:
        algorithm, iterations_str, _, _ = stored_hash.split("$")
        iterations = int(iterations_str)
    except (ValueError, AttributeError):
        return True

    if algorithm != DEFAULT_ALGORITHM:
        return True

    return iterations < DEFAULT_ITERATIONS


# ============================================================
# Password policy
# ============================================================
@dataclass(frozen=True)
class PasswordPolicy:
    """
    Rules that a password must satisfy.

    Attributes:
        min_length: Minimum length (default 8).
        max_length: Maximum length (default 128 — prevents DoS).
        require_uppercase: At least one A-Z (default False).
        require_lowercase: At least one a-z (default True).
        require_digit: At least one 0-9 (default True).
        require_special: At least one symbol (default False).
        forbidden: Set of substrings that must NOT appear
                   (e.g., the username).
    """

    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = False
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = False
    forbidden: frozenset[str] = field(default_factory=frozenset)

    # ---- Validation ----
    def validate(self, password: str, *, username: str = "") -> None:
        """
        Raise PasswordValidationError if password violates the policy.

        Args:
            password: Password to check.
            username: Optional username to forbid in the password.
        """
        if not isinstance(password, str):
            raise PasswordValidationError("password must be a string")

        if len(password) < self.min_length:
            raise PasswordValidationError(
                f"password must be at least {self.min_length} characters"
            )

        if len(password) > self.max_length:
            raise PasswordValidationError(
                f"password must be at most {self.max_length} characters"
            )

        if self.require_uppercase and not re.search(r"[A-Z]", password):
            raise PasswordValidationError(
                "password must contain at least one uppercase letter"
            )

        if self.require_lowercase and not re.search(r"[a-z]", password):
            raise PasswordValidationError(
                "password must contain at least one lowercase letter"
            )

        if self.require_digit and not re.search(r"[0-9]", password):
            raise PasswordValidationError(
                "password must contain at least one digit"
            )

        if self.require_special and not re.search(r"[^A-Za-z0-9]", password):
            raise PasswordValidationError(
                "password must contain at least one special character"
            )

        # Forbidden substrings
        lower_pwd = password.lower()
        for bad in self.forbidden:
            if bad and bad.lower() in lower_pwd:
                raise PasswordValidationError(
                    f"password must not contain '{bad}'"
                )

        if username and username.lower() in lower_pwd:
            raise PasswordValidationError(
                "password must not contain the username"
            )


#: Default, sensible policy for business apps.
DEFAULT_POLICY: Final[PasswordPolicy] = PasswordPolicy()


def validate_password(
    password: str,
    *,
    policy: PasswordPolicy | None = None,
    username: str = "",
) -> None:
    """
    Validate a password against a policy.

    Raises:
        PasswordValidationError: if the password is invalid.
    """
    (policy or DEFAULT_POLICY).validate(password, username=username)


# ============================================================
# Strength meter
# ============================================================
def estimate_strength(password: str) -> tuple[int, str]:
    """
    Estimate the strength of a password.

    Returns:
        (score, label) where score is 0-100 and label is a short
        human-readable description.

    This is a *rough* estimate for UX purposes — not security-critical.
    """
    if not password:
        return 0, "empty"

    score = 0

    # Length
    if len(password) >= 8:
        score += 20
    if len(password) >= 12:
        score += 15
    if len(password) >= 16:
        score += 10

    # Variety
    if re.search(r"[a-z]", password):
        score += 10
    if re.search(r"[A-Z]", password):
        score += 15
    if re.search(r"[0-9]", password):
        score += 15
    if re.search(r"[^A-Za-z0-9]", password):
        score += 15

    # Penalties
    if len(set(password)) < len(password) / 2:
        score -= 20  # lots of repeats
    if re.match(r"^[a-zA-Z]+$", password):
        score -= 10  # letters only

    score = max(0, min(100, score))

    if score < 30:
        label = "weak"
    elif score < 60:
        label = "fair"
    elif score < 80:
        label = "strong"
    else:
        label = "very strong"

    return score, label