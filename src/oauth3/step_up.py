"""
OAuth3 Step-Up Authorization — One-Time Nonce Manager

For destructive scopes (STEP_UP_REQUIRED_SCOPES), the enforcement layer
blocks execution and returns HTTP 402. The user must visit /step-up, confirm
the action, and receive a one-time nonce. The nonce is then passed back with
the recipe request to allow execution.

Properties:
  - One-use: each nonce is consumed on first validation call
  - Time-bounded: nonces expire after TTL seconds (default 300 = 5 minutes)
  - In-memory: nonces are not persisted to disk (intentional — they are
    ephemeral session artifacts, not durable credentials)

Rung: 641
"""

import uuid
import time
from typing import Optional


# ---------------------------------------------------------------------------
# In-memory nonce store
# {nonce: {"token_id": str, "action": str, "expires_at": float}}
# ---------------------------------------------------------------------------

_NONCE_STORE: dict = {}

# Default TTL in seconds (5 minutes)
DEFAULT_NONCE_TTL = 300


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_step_up_nonce(
    token_id: str,
    action: str,
    ttl: int = DEFAULT_NONCE_TTL,
) -> str:
    """
    Create a one-time step-up nonce for a destructive action.

    Args:
        token_id: The agency token authorising the action.
        action:   The scope string being authorized (e.g. "linkedin.delete_post").
        ttl:      Nonce lifetime in seconds (default 300 = 5 minutes).

    Returns:
        A UUID4 nonce string. Pass this back to /run-recipe as step_up_nonce.
    """
    nonce = str(uuid.uuid4())
    _NONCE_STORE[nonce] = {
        "token_id": token_id,
        "action": action,
        "expires_at": time.monotonic() + ttl,
    }
    return nonce


def validate_and_consume_nonce(nonce: str) -> tuple:
    """
    Validate a step-up nonce and consume it (single-use enforcement).

    The nonce is removed from the store regardless of validity outcome
    (expired nonces are also removed to prevent accumulation).

    Args:
        nonce: The nonce string to validate.

    Returns:
        (valid: bool, action: str)
        When valid is True, action is the authorised scope string.
        When valid is False, action is "" (empty string, never None).
    """
    _sweep_expired()

    entry = _NONCE_STORE.pop(nonce, None)
    if entry is None:
        return False, ""

    # Check expiry (entry may have been inserted before sweep ran)
    if time.monotonic() > entry["expires_at"]:
        return False, ""

    return True, entry["action"]


def peek_nonce(nonce: str) -> Optional[dict]:
    """
    Return nonce metadata without consuming it. For testing only.

    Args:
        nonce: The nonce string to inspect.

    Returns:
        Dict with token_id, action, expires_at keys, or None if not found.
    """
    return _NONCE_STORE.get(nonce)


def clear_all_nonces() -> None:
    """
    Clear the entire nonce store. For testing / server teardown only.
    """
    _NONCE_STORE.clear()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sweep_expired() -> None:
    """Remove all expired nonces from the store (O(n) GC sweep)."""
    now = time.monotonic()
    expired_keys = [k for k, v in _NONCE_STORE.items() if now > v["expires_at"]]
    for k in expired_keys:
        del _NONCE_STORE[k]
