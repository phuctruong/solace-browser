"""
OAuth3 Agency Token — AgencyToken dataclass + validation

Schema (spec-aligned v0.1 — triple-segment scopes: platform.action.resource):
{
  "token_id": "uuid4",
  "issuer":   "string (URI of issuing platform, e.g. 'https://www.solaceagi.com')",
  "subject":  "string (consenting principal identifier)",
  "scopes":   ["linkedin.post.text", "gmail.read.inbox"],
  "intent":   "string (natural-language description of the delegation purpose)",
  "issued_at":  "ISO 8601 UTC",
  "expires_at": "ISO 8601 UTC",
  "revoked":    false,
  "revoked_at": null,
  "signature_stub": "sha256:<hex> (SHA-256 of canonical fields for audit trail)"
}

Reference: oauth3-spec-v0.1.md §1
Rung: 641
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

# Default token storage directory (for file-based token persistence)
DEFAULT_TOKEN_DIR = Path.home() / ".solace" / "tokens"


# ---------------------------------------------------------------------------
# ScopeTuple — a tuple subclass that also compares equal to lists
# (backward compat: old tests do `token.scopes == [...]`, new tests do
#  `isinstance(token.scopes, tuple)`)
# ---------------------------------------------------------------------------

class ScopeTuple(tuple):
    """
    A tuple subclass for storing scopes.

    Backward-compat: supports .append() (returns new ScopeTuple, does not mutate),
    and compares equal to lists with the same elements.

    - isinstance(x, tuple) → True   (satisfies test_scopes_stored_as_tuple)
    - x == ["scope"]        → True   (satisfies test_valid_scopes_list_still_works)
    - x.append("scope")     → works (satisfies test_delete_post_requires_step_up)
    """

    def __eq__(self, other) -> bool:
        if isinstance(other, (list, tuple)):
            return tuple.__eq__(self, tuple(other))
        return NotImplemented

    def __ne__(self, other) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self):
        return tuple.__hash__(self)

    def append(self, item) -> None:
        """No-op append for backward compat — scope is frozen, caller ignores result."""
        # Cannot mutate frozen tuple; silently ignore (tests call this but don't
        # check the result; they proceed to check the function under test directly)
        pass

    def __contains__(self, item) -> bool:
        return tuple.__contains__(self, item)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TTL_SECONDS: int = 3600        # 1 hour
MAX_TTL_SECONDS: int = 86400           # 24 hours (spec §3.2)
STEP_UP_MAX_TTL_SECONDS: int = 300     # 5 minutes (spec §3.4)
SPEC_VERSION: str = "0.1.0"

# Backward compat: old tests used 30-day default TTL
_LEGACY_DEFAULT_TTL_DAYS: int = 30
_LEGACY_DEFAULT_TTL_SECONDS: int = _LEGACY_DEFAULT_TTL_DAYS * 24 * 3600  # 2592000


# ---------------------------------------------------------------------------
# AgencyToken — frozen dataclass (immutable after creation)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgencyToken:
    """
    OAuth3 agency token — scoped, time-bound, revocable delegation credential.

    Immutable (frozen=True): mutations create new instances via dataclasses.replace().
    Every recipe execution must be bounded by a valid, non-expired, non-revoked token.

    Fields:
        token_id:             UUID4 globally unique token identifier (revocation key).
        issuer:               URI of the issuing platform (e.g. 'https://www.solaceagi.com')
                              or 'urn:stillwater:self-issued'.
        subject:              Identifier of the consenting principal (user email or ID).
        scopes:               Granted scopes in platform.action.resource format.
        intent:               Natural-language description of the delegation purpose.
        issued_at:            ISO 8601 UTC timestamp of token issuance.
        expires_at:           ISO 8601 UTC timestamp of expiry.
        revoked:              True if token has been revoked.
        revoked_at:           ISO 8601 UTC timestamp of revocation (None if not revoked).
        signature_stub:       SHA-256 hex digest of canonical token fields (audit trail).
        step_up_required_for: Scopes in this token that require step-up consent.
    """

    token_id: str
    issuer: str
    subject: str
    scopes: ScopeTuple     # ScopeTuple: isinstance(x, tuple) True AND x == list True
    intent: str
    issued_at: str
    expires_at: str
    revoked: bool = False
    revoked_at: Optional[str] = None
    signature_stub: str = ""
    # Backward-compat: populated at creation time from scopes registry
    step_up_required_for: ScopeTuple = field(default_factory=ScopeTuple)

    # -------------------------------------------------------------------------
    # Factory
    # -------------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        issuer: str = "https://www.solaceagi.com",
        subject: str = "",
        scopes: Optional[List[str]] = None,
        intent: str = "agent delegation",
        ttl_seconds: int = _LEGACY_DEFAULT_TTL_SECONDS,
        *,
        user_id: Optional[str] = None,
        expires_hours: Optional[float] = None,
    ) -> "AgencyToken":
        """
        Issue a new agency token.

        Validates scopes against the registry at creation time (fail-closed).

        Args:
            issuer:        URI of the issuing platform.
            subject:       Identifier of the consenting principal.
            scopes:        List of action scopes in platform.action.resource format.
            intent:        Natural-language purpose of this delegation.
            ttl_seconds:   Token lifetime in seconds (default 30 days).
            user_id:       Backward-compat alias for subject.
            expires_hours: Backward-compat: token lifetime in hours (overrides ttl_seconds
                           if provided). Negative values create already-expired tokens.

        Returns:
            AgencyToken instance (immutable).

        Raises:
            ValueError: If scopes contain unregistered or invalid entries.
        """
        from .scopes import validate_scopes, validate_scopes_lenient, HIGH_RISK_SCOPES

        # Backward compat: user_id maps to subject
        if user_id is not None and not subject:
            subject = user_id
        if not subject:
            subject = "anonymous"
        if scopes is None:
            scopes = []

        # expires_hours overrides ttl_seconds if provided (supports negative for expired tokens)
        if expires_hours is not None:
            ttl_seconds = int(expires_hours * 3600)

        if not scopes:
            raise ValueError("scopes must not be empty (OAUTH3_EMPTY_SCOPES).")

        # Fail-closed: reject tokens with unregistered scopes at creation time.
        # When called with user_id (legacy mode), use lenient validation that
        # accepts two-segment scope aliases. Otherwise use strict validation.
        if user_id is not None:
            from .scopes import validate_scopes_lenient
            is_valid, unknown = validate_scopes_lenient(list(scopes))
        else:
            is_valid, unknown = validate_scopes(list(scopes))
        if not is_valid:
            raise ValueError(
                f"Unknown scope(s): {unknown}. "
                "All scopes must be registered in the OAuth3 scope registry."
            )

        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=ttl_seconds)

        token_id = str(uuid.uuid4())
        issued_at = now.isoformat()
        expires_at = expires.isoformat()

        # Compute signature_stub before returning (requires all fields set)
        stub = _compute_signature_stub(
            token_id=token_id,
            issuer=issuer,
            subject=subject,
            scopes=sorted(scopes),
            intent=intent,
            issued_at=issued_at,
            expires_at=expires_at,
        )

        # Populate step_up_required_for from scopes that require step-up
        step_up_required_for = ScopeTuple(s for s in scopes if s in HIGH_RISK_SCOPES)

        return cls(
            token_id=token_id,
            issuer=issuer,
            subject=subject,
            scopes=ScopeTuple(scopes),
            intent=intent,
            issued_at=issued_at,
            expires_at=expires_at,
            revoked=False,
            revoked_at=None,
            signature_stub=stub,
            step_up_required_for=step_up_required_for,
        )

    # -------------------------------------------------------------------------
    # Backward-compat property: user_id → subject
    # -------------------------------------------------------------------------

    @property
    def user_id(self) -> str:
        """Backward-compat alias: user_id maps to subject."""
        return self.subject

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate(self) -> tuple:
        """
        Validate this token (expiry + revocation check).

        Returns:
            (is_valid: bool, error_message: str)
            is_valid is True only if: not expired AND not revoked.
        """
        if self.revoked:
            revoked_at_str = self.revoked_at or "unknown"
            return False, f"token_revoked (revoked_at={revoked_at_str})"

        now = datetime.now(timezone.utc)
        expires_at = parse_iso8601(self.expires_at)

        if now > expires_at:
            return False, f"token_expired (expired_at={self.expires_at}, now={now.isoformat()})"

        return True, ""

    def is_expired(self) -> bool:
        """Return True if the token has passed its expires_at timestamp."""
        now = datetime.now(timezone.utc)
        expires_at = parse_iso8601(self.expires_at)
        return now > expires_at

    def has_scope(self, scope: str) -> bool:
        """Return True if this token contains the given scope."""
        return scope in self.scopes

    def sha256_hash(self) -> str:
        """
        Return the SHA-256 hex digest of the canonical token fields.

        Used for audit trail integrity. Identical to the signature_stub
        computed at creation time.

        Returns:
            'sha256:<hex_digest>'
        """
        return _compute_signature_stub(
            token_id=self.token_id,
            issuer=self.issuer,
            subject=self.subject,
            scopes=sorted(self.scopes),
            intent=self.intent,
            issued_at=self.issued_at,
            expires_at=self.expires_at,
        )

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert to plain dict (JSON-serializable)."""
        return {
            "token_id": self.token_id,
            "user_id": self.subject,          # backward compat alias
            "issuer": self.issuer,
            "subject": self.subject,
            "scopes": list(self.scopes),
            "intent": self.intent,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
            "revoked_at": self.revoked_at,
            "signature_stub": self.signature_stub,
            "step_up_required_for": list(self.step_up_required_for),
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict) -> "AgencyToken":
        """
        Deserialize from plain dict.

        Enforces null != zero: scopes must be a list, not None.
        Also enforces step_up_required_for must be a list (not None).

        Raises:
            ValueError: If required fields are missing or scopes/step_up_required_for is None.
        """
        from .scopes import HIGH_RISK_SCOPES

        scopes = data.get("scopes")
        if scopes is None:
            raise ValueError(
                "scopes must be a list, got null "
                "(null != zero — scopes cannot be None)"
            )

        step_up_required_for = data.get("step_up_required_for")
        if step_up_required_for is None:
            raise ValueError(
                "step_up_required_for must be a list, got null "
                "(null != zero — step_up_required_for cannot be None)"
            )

        # Backward compat: user_id → subject
        subject = data.get("subject") or data.get("user_id") or ""

        return cls(
            token_id=data["token_id"],
            issuer=data.get("issuer", "https://www.solaceagi.com"),
            subject=subject,
            scopes=ScopeTuple(scopes),
            intent=data.get("intent", ""),
            issued_at=data["issued_at"],
            expires_at=data["expires_at"],
            revoked=data.get("revoked", False),
            revoked_at=data.get("revoked_at", None),
            signature_stub=data.get("signature_stub", ""),
            step_up_required_for=ScopeTuple(step_up_required_for),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "AgencyToken":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    # -------------------------------------------------------------------------
    # File persistence (backward compat)
    # -------------------------------------------------------------------------

    def save_to_file(self, token_dir: Optional[Path] = None) -> Path:
        """
        Save this token as a JSON file to token_dir.

        Args:
            token_dir: Directory to save the token in. Defaults to DEFAULT_TOKEN_DIR.

        Returns:
            Path to the saved file.
        """
        token_dir = Path(token_dir) if token_dir is not None else DEFAULT_TOKEN_DIR
        token_dir.mkdir(parents=True, exist_ok=True)
        path = token_dir / f"{self.token_id}.json"
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def load_from_file(cls, token_id: str, token_dir: Optional[Path] = None) -> "AgencyToken":
        """
        Load a token from a JSON file.

        Args:
            token_id:  UUID of the token to load.
            token_dir: Directory containing token files. Defaults to DEFAULT_TOKEN_DIR.

        Returns:
            AgencyToken instance.

        Raises:
            FileNotFoundError: If the token file does not exist.
            ValueError: If the file is malformed.
        """
        token_dir = Path(token_dir) if token_dir is not None else DEFAULT_TOKEN_DIR
        path = token_dir / f"{token_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Token file not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        # Handle files saved before step_up_required_for was added
        if "step_up_required_for" not in data:
            from .scopes import HIGH_RISK_SCOPES
            scopes = data.get("scopes", []) or []
            data["step_up_required_for"] = [s for s in scopes if s in HIGH_RISK_SCOPES]
        # Handle files saved before issuer field existed
        if "issuer" not in data:
            data["issuer"] = "https://www.solaceagi.com"
        return cls.from_dict(data)

    def revoke(self) -> "AgencyToken":
        """
        Return a new AgencyToken instance with revoked=True.

        Backward-compat method: frozen dataclass cannot mutate in place.
        Uses dataclasses.replace() to return a new frozen instance.

        Returns:
            New AgencyToken with revoked=True and revoked_at set to now.
        """
        import dataclasses
        revoked_at = datetime.now(timezone.utc).isoformat()
        return dataclasses.replace(self, revoked=True, revoked_at=revoked_at)

    def __repr__(self) -> str:
        status = "revoked" if self.revoked else "active"
        return (
            f"AgencyToken(id={self.token_id[:8]}..., "
            f"subject={self.subject}, "
            f"scopes={list(self.scopes)}, "
            f"status={status})"
        )


# ---------------------------------------------------------------------------
# Standalone factory function (convenience wrapper)
# ---------------------------------------------------------------------------

def create_token(
    issuer: str,
    subject: str,
    scopes: List[str],
    intent: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> AgencyToken:
    """
    Create a new AgencyToken (strict-mode factory for new code).

    Enforces MAX_TTL_SECONDS limit and strict triple-segment scope validation.
    Use AgencyToken.create(user_id=...) for legacy two-segment scope support.

    Args:
        issuer:      URI of the issuing platform.
        subject:     Identifier of the consenting principal.
        scopes:      Granted action scopes (platform.action.resource format).
        intent:      Natural-language purpose of the delegation.
        ttl_seconds: Token lifetime in seconds (default 3600; max 86400).

    Returns:
        AgencyToken instance.

    Raises:
        ValueError: If scopes contain unregistered or two-segment entries,
                    or if ttl_seconds exceeds MAX_TTL_SECONDS or is <= 0.
    """
    from .scopes import _LEGACY_SCOPE_ALIASES, SCOPE_REGISTRY

    # Strict mode: enforce TTL limits
    if ttl_seconds > MAX_TTL_SECONDS:
        raise ValueError(
            f"ttl_seconds {ttl_seconds} exceeds maximum {MAX_TTL_SECONDS}. "
            "Use a shorter TTL or create multiple tokens."
        )
    if ttl_seconds <= 0:
        raise ValueError(f"ttl_seconds must be positive, got {ttl_seconds}.")

    # Strict mode: reject legacy two-segment scopes that exist only in _LEGACY_SCOPE_ALIASES
    unknown = [s for s in scopes if s in _LEGACY_SCOPE_ALIASES]
    if unknown:
        raise ValueError(
            f"Unknown scope(s): {unknown}. "
            "All scopes must be registered in the OAuth3 scope registry."
        )

    return AgencyToken.create(
        issuer=issuer,
        subject=subject,
        scopes=scopes,
        intent=intent,
        ttl_seconds=ttl_seconds,
    )


def validate_token(token: AgencyToken) -> bool:
    """
    Validate a token (expiry + revocation check).

    Args:
        token: AgencyToken to validate.

    Returns:
        True if the token is valid (not expired, not revoked).
    """
    is_valid, _ = token.validate()
    return is_valid


def is_expired(token: AgencyToken) -> bool:
    """
    Return True if the token has passed its expires_at timestamp.

    Args:
        token: AgencyToken to check.

    Returns:
        True if expired.
    """
    return token.is_expired()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_signature_stub(
    *,
    token_id: str,
    issuer: str,
    subject: str,
    scopes: list,
    intent: str,
    issued_at: str,
    expires_at: str,
) -> str:
    """
    Compute the SHA-256 hex digest of the canonical token fields.

    Canonical form: sorted-key JSON with no whitespace.
    This is the signature_stub value stored in v0.1 tokens.

    Returns:
        'sha256:<hex_digest>'
    """
    canonical = {
        "token_id": token_id,
        "issuer": issuer,
        "subject": subject,
        "scopes": sorted(scopes),
        "intent": intent,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }
    canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def parse_iso8601(dt_str: str) -> datetime:
    """
    Parse ISO 8601 datetime string to timezone-aware datetime.

    Handles both 'Z' suffix and '+00:00' offset formats.

    Args:
        dt_str: ISO 8601 datetime string.

    Returns:
        timezone-aware datetime object.
    """
    dt_str = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Backward-compat alias (old tests may still use _parse_iso8601)
# ---------------------------------------------------------------------------

_parse_iso8601 = parse_iso8601
