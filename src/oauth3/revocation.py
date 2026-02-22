"""
OAuth3 Token Revocation + Session Management

Revocation must be synchronous and immediate per spec §4.1:
  "Revocation MUST take effect immediately and synchronously."

Two storage backends:
  TokenStore  — in-memory store (for testing + ephemeral sessions)

Per spec §4.4 the revocation registry must support O(1) lookups.
TokenStore uses dict keyed by token_id for O(1) lookup.

Reference: oauth3-spec-v0.1.md §4
Rung: 641
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from .token import AgencyToken, parse_iso8601


# ---------------------------------------------------------------------------
# TokenStore — in-memory token store with CRUD + revocation
# ---------------------------------------------------------------------------

class TokenStore:
    """
    In-memory token store.

    Provides O(1) lookup, insert, revocation, and cleanup.
    Thread-safety: not guaranteed (single-threaded use only in Phase 1).

    Usage:
        store = TokenStore()
        store.add(token)
        store.revoke(token.token_id)
        active = store.get_active_tokens(subject="user:alice@example.com")
    """

    def __init__(self) -> None:
        # _tokens: {token_id: AgencyToken}
        self._tokens: Dict[str, AgencyToken] = {}

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    def add(self, token: AgencyToken) -> None:
        """
        Add a token to the store. Overwrites any existing token with the same id.

        Args:
            token: AgencyToken to store.
        """
        self._tokens[token.token_id] = token

    def get(self, token_id: str) -> Optional[AgencyToken]:
        """
        Retrieve a token by id.

        Args:
            token_id: UUID of the token.

        Returns:
            AgencyToken if found, None otherwise.
        """
        return self._tokens.get(token_id)

    def remove(self, token_id: str) -> bool:
        """
        Remove a token from the store entirely.

        Args:
            token_id: UUID of the token.

        Returns:
            True if token existed and was removed, False otherwise.
        """
        if token_id in self._tokens:
            del self._tokens[token_id]
            return True
        return False

    def all_tokens(self) -> List[AgencyToken]:
        """Return all tokens in the store (including revoked and expired)."""
        return list(self._tokens.values())

    # -------------------------------------------------------------------------
    # Revocation
    # -------------------------------------------------------------------------

    def revoke(self, token_id: str) -> bool:
        """
        Revoke a single token by id.

        Revocation is immediate and synchronous (spec §4.1).
        Revocation is permanent: a revoked token cannot be re-activated.

        Args:
            token_id: UUID of the token to revoke.

        Returns:
            True if revocation succeeded or token was already revoked.
            False if token not found.
        """
        token = self._tokens.get(token_id)
        if token is None:
            return False

        if token.revoked:
            # Idempotent: already revoked → True (revocation is complete)
            return True

        # Frozen dataclass: create a new instance with revoked=True
        import dataclasses
        revoked_at = datetime.now(timezone.utc).isoformat()
        revoked_token = dataclasses.replace(
            token,
            revoked=True,
            revoked_at=revoked_at,
        )
        self._tokens[token_id] = revoked_token
        return True

    def revoke_all_for_subject(self, subject: str) -> int:
        """
        Revoke ALL active tokens for a given subject.

        Used when an account is compromised or a session is terminated (spec §4.3).

        Args:
            subject: Principal identifier whose tokens should be revoked.

        Returns:
            Count of tokens revoked (excludes already-revoked tokens).
        """
        import dataclasses
        revoked_count = 0
        revoked_at = datetime.now(timezone.utc).isoformat()

        for token_id, token in list(self._tokens.items()):
            if token.subject == subject and not token.revoked:
                revoked_token = dataclasses.replace(
                    token,
                    revoked=True,
                    revoked_at=revoked_at,
                )
                self._tokens[token_id] = revoked_token
                revoked_count += 1

        return revoked_count

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_active_tokens(self, subject: str) -> List[AgencyToken]:
        """
        Return all active (non-revoked, non-expired) tokens for a subject.

        Args:
            subject: Principal identifier.

        Returns:
            List of active AgencyToken instances.
        """
        now = datetime.now(timezone.utc)
        result = []
        for token in self._tokens.values():
            if token.subject != subject:
                continue
            if token.revoked:
                continue
            try:
                expires_at = parse_iso8601(token.expires_at)
                if now > expires_at:
                    continue
            except (ValueError, AttributeError):
                continue
            result.append(token)
        return result

    def is_revoked(self, token_id: str) -> bool:
        """
        Quickly check if a token is revoked.

        Fail-closed: returns True for unknown/missing tokens.

        Args:
            token_id: UUID to check.

        Returns:
            True if revoked or not found.
            False if found and NOT revoked.
        """
        token = self._tokens.get(token_id)
        if token is None:
            return True  # fail-closed: unknown → treat as revoked
        return token.revoked

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def cleanup_expired(self) -> int:
        """
        Remove tokens that have been expired for > 0 seconds.

        Per spec §4.4: expired tokens MAY be pruned from the registry.
        They are implicitly invalid via G2 (TTL gate) regardless.

        Returns:
            Count of tokens removed.
        """
        now = datetime.now(timezone.utc)
        to_remove = []

        for token_id, token in self._tokens.items():
            try:
                expires_at = parse_iso8601(token.expires_at)
                if now > expires_at:
                    to_remove.append(token_id)
            except (ValueError, AttributeError):
                to_remove.append(token_id)  # malformed → remove

        for token_id in to_remove:
            del self._tokens[token_id]

        return len(to_remove)

    def __len__(self) -> int:
        return len(self._tokens)

    def __repr__(self) -> str:
        return f"TokenStore(count={len(self._tokens)})"


# ---------------------------------------------------------------------------
# Standalone revocation functions (legacy API + convenience wrappers)
# ---------------------------------------------------------------------------

def revoke_token(
    token_id: str,
    store: Optional[TokenStore] = None,
    *,
    token_dir=None,
) -> bool:
    """
    Revoke a single token by id.

    Supports both in-memory (store=) and file-based (token_dir=) backends.

    Args:
        token_id:  UUID of the token to revoke.
        store:     TokenStore to revoke from (for in-memory backend).
        token_dir: Directory containing token files (for file-based backend).

    Returns:
        True if revocation succeeded or token was already revoked.
        False if token not found.
    """
    # File-based backend takes priority if token_dir is provided
    if token_dir is not None:
        return revoke_token_file(token_id, token_dir=token_dir)
    if store is not None:
        return store.revoke(token_id)
    return False


def revoke_all_for_subject(subject: str, store: TokenStore) -> int:
    """
    Revoke all active tokens for a subject.

    Args:
        subject: Principal identifier.
        store:   TokenStore to revoke from.

    Returns:
        Count of tokens revoked.
    """
    return store.revoke_all_for_subject(subject)


def get_active_tokens(subject: str, store: TokenStore) -> List[AgencyToken]:
    """
    Return all active tokens for a subject from the given store.

    Args:
        subject: Principal identifier.
        store:   TokenStore to query.

    Returns:
        List of active AgencyToken instances.
    """
    return store.get_active_tokens(subject)


def cleanup_expired(store: TokenStore) -> int:
    """
    Remove expired tokens from the store.

    Args:
        store: TokenStore to clean.

    Returns:
        Count of tokens removed.
    """
    return store.cleanup_expired()


# ---------------------------------------------------------------------------
# File-based revocation (backward compat with file-based storage)
# ---------------------------------------------------------------------------

def revoke_token_file(token_id: str, token_dir=None) -> bool:
    """
    Revoke a single token by marking it in its JSON file.

    Legacy function for file-based storage. New code should use TokenStore.

    Args:
        token_id:  UUID of the token to revoke.
        token_dir: Directory containing token files.

    Returns:
        True if revocation succeeded, False if not found or already revoked.
    """
    import json
    from pathlib import Path

    if token_dir is None:
        return False

    token_path = Path(token_dir) / f"{token_id}.json"
    if not token_path.exists():
        return False

    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
        if data.get("revoked", False):
            return True  # idempotent

        data["revoked"] = True
        data["revoked_at"] = datetime.now(timezone.utc).isoformat()
        token_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True

    except (json.JSONDecodeError, OSError):
        return False


def is_revoked_file(token_id: str, token_dir=None) -> bool:
    """
    Quick revocation check for file-based storage.

    Fail-closed: returns True for missing/malformed tokens.

    Args:
        token_id:  UUID to check.
        token_dir: Directory containing token files.

    Returns:
        True if token is revoked or not found.
    """
    import json
    from pathlib import Path

    if token_dir is None:
        return True

    token_path = Path(token_dir) / f"{token_id}.json"
    if not token_path.exists():
        return True  # fail-closed

    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
        return data.get("revoked", False)
    except (json.JSONDecodeError, OSError):
        return True  # fail-closed


def list_all_tokens(token_dir=None) -> List[AgencyToken]:
    """
    List all tokens from file-based storage as AgencyToken objects.

    Args:
        token_dir: Directory containing token JSON files.

    Returns:
        List of AgencyToken instances loaded from files.
    """
    import json
    from pathlib import Path

    if token_dir is None:
        return []

    token_path = Path(token_dir)
    if not token_path.exists():
        return []

    tokens = []
    for f in sorted(token_path.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            # Handle files saved before step_up_required_for field existed
            if "step_up_required_for" not in data:
                from .scopes import HIGH_RISK_SCOPES
                scopes = data.get("scopes", [])
                data["step_up_required_for"] = [s for s in scopes if s in HIGH_RISK_SCOPES]
            # Handle files saved before issuer field existed (legacy)
            if "issuer" not in data:
                data["issuer"] = "https://www.solaceagi.com"
            token = AgencyToken.from_dict(data)
            tokens.append(token)
        except (json.JSONDecodeError, OSError, ValueError, KeyError):
            continue
    return tokens


def is_revoked(token_id: str, token_dir=None) -> bool:
    """
    Backward-compat alias for is_revoked_file.

    Fail-closed: missing/malformed → True.
    """
    return is_revoked_file(token_id, token_dir=token_dir)


def revoke_all_tokens_for_scope(scope: str, token_dir=None) -> int:
    """
    Revoke all tokens that contain a given scope (file-based).

    Backward-compatibility function for old tests.

    Args:
        scope:     Scope string to match.
        token_dir: Directory containing token JSON files.

    Returns:
        Number of tokens revoked.
    """
    import json
    from pathlib import Path

    if token_dir is None:
        return 0

    token_path = Path(token_dir)
    if not token_path.exists():
        return 0

    count = 0
    for f in sorted(token_path.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            scopes = data.get("scopes", [])
            if scope in scopes and not data.get("revoked", False):
                data["revoked"] = True
                f.write_text(json.dumps(data), encoding="utf-8")
                count += 1
        except (json.JSONDecodeError, OSError):
            continue
    return count
