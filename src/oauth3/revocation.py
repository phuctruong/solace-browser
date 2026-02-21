"""
OAuth3 Token Revocation

Immediate revocation: mark token as revoked in persistent store.
Revocation must propagate within the current request — no async delay.

Per OAUTH3-WHITEPAPER.md §5.2:
  "Immediate revocation must:
   - Kill cloud sessions
   - Burn active agency tokens
   - Wipe vault credentials
   - Disable future execution"

Phase 1 implements: burn active agency tokens.
Cloud session kill and vault wipe are Phase 3 (solaceagi.com).

Rung: 641
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .token import AgencyToken, DEFAULT_TOKEN_DIR


# -------------------------------------------------------------------------
# Single token revocation
# -------------------------------------------------------------------------

def revoke_token(token_id: str, token_dir: Optional[Path] = None) -> bool:
    """
    Revoke a single token by marking it as revoked in its JSON file.

    Args:
        token_id: UUID of the token to revoke.
        token_dir: Directory containing token files.

    Returns:
        True if revocation succeeded, False if token was not found or already revoked.
    """
    token_dir = token_dir or DEFAULT_TOKEN_DIR
    token_path = token_dir / f"{token_id}.json"

    if not token_path.exists():
        return False

    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))

        # Idempotent: if already revoked, return True (revocation is complete)
        if data.get("revoked", False):
            return True

        data["revoked"] = True
        data["revoked_at"] = datetime.now(timezone.utc).isoformat()

        token_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True

    except (json.JSONDecodeError, OSError):
        return False


# -------------------------------------------------------------------------
# Bulk revocation by scope
# -------------------------------------------------------------------------

def revoke_all_tokens_for_scope(
    scope: str,
    token_dir: Optional[Path] = None,
) -> int:
    """
    Find all tokens that include a specific scope and revoke them.

    Useful for emergency revocation when a scope is compromised or abused.

    Args:
        scope: The scope string to search for (e.g. "linkedin.create_post").
        token_dir: Directory containing token files.

    Returns:
        Count of tokens successfully revoked.
    """
    token_dir = token_dir or DEFAULT_TOKEN_DIR

    if not token_dir.exists():
        return 0

    revoked_count = 0

    for token_file in token_dir.glob("*.json"):
        try:
            data = json.loads(token_file.read_text(encoding="utf-8"))

            # Skip already-revoked tokens
            if data.get("revoked", False):
                continue

            # Check if this token has the target scope
            if scope in data.get("scopes", []):
                data["revoked"] = True
                data["revoked_at"] = datetime.now(timezone.utc).isoformat()
                token_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                revoked_count += 1

        except (json.JSONDecodeError, OSError):
            # Skip malformed or inaccessible token files
            continue

    return revoked_count


# -------------------------------------------------------------------------
# Revocation status check
# -------------------------------------------------------------------------

def is_revoked(token_id: str, token_dir: Optional[Path] = None) -> bool:
    """
    Quick check if a specific token is revoked.

    Does not load the full AgencyToken — reads only the "revoked" field.
    Suitable for fast pre-flight checks without full token loading overhead.

    Args:
        token_id: UUID of the token to check.
        token_dir: Directory containing token files.

    Returns:
        True if token is revoked or not found.
        False if token exists and is NOT revoked.

    Note: Returns True (fail-closed) for missing or malformed tokens.
    """
    token_dir = token_dir or DEFAULT_TOKEN_DIR
    token_path = token_dir / f"{token_id}.json"

    if not token_path.exists():
        # Fail-closed: treat missing tokens as revoked
        return True

    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
        return data.get("revoked", False)
    except (json.JSONDecodeError, OSError):
        # Fail-closed: treat malformed tokens as revoked
        return True


# -------------------------------------------------------------------------
# List all tokens (for management UI)
# -------------------------------------------------------------------------

def list_all_tokens(token_dir: Optional[Path] = None) -> list:
    """
    Load all tokens from the token directory.

    Args:
        token_dir: Directory containing token files.

    Returns:
        List of AgencyToken instances (all tokens, including revoked).
    """
    token_dir = token_dir or DEFAULT_TOKEN_DIR

    if not token_dir.exists():
        return []

    tokens = []
    for token_file in sorted(token_dir.glob("*.json")):
        try:
            token = AgencyToken.load_from_file(
                token_file.stem,
                token_dir=token_dir,
            )
            tokens.append(token)
        except Exception:
            continue

    return tokens
