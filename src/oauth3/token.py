"""
OAuth3 Agency Token — AgencyToken dataclass + validation

Schema (spec-aligned v0.1 — triple-segment scopes: platform.action.resource):
{
  "token_id": "uuid4",
  "issuer":   "string (URI of issuing platform, e.g. 'https://solaceagi.com')",
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
from typing import List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TTL_SECONDS: int = 3600        # 1 hour
MAX_TTL_SECONDS: int = 86400           # 24 hours (spec §3.2)
STEP_UP_MAX_TTL_SECONDS: int = 300     # 5 minutes (spec §3.4)
SPEC_VERSION: str = "0.1.0"


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
        token_id:       UUID4 globally unique token identifier (revocation key).
        issuer:         URI of the issuing platform (e.g. 'https://solaceagi.com')
                        or 'urn:stillwater:self-issued'.
        subject:        Identifier of the consenting principal (user email or ID).
        scopes:         Granted scopes in platform.action.resource format.
        intent:         Natural-language description of the delegation purpose.
        issued_at:      ISO 8601 UTC timestamp of token issuance.
        expires_at:     ISO 8601 UTC timestamp of expiry.
        revoked:        True if token has been revoked.
        revoked_at:     ISO 8601 UTC timestamp of revocation (None if not revoked).
        signature_stub: SHA-256 hex digest of canonical token fields (audit trail).
    """

    token_id: str
    issuer: str
    subject: str
    scopes: tuple          # Use tuple for immutability (frozen dataclass)
    intent: str
    issued_at: str
    expires_at: str
    revoked: bool = False
    revoked_at: Optional[str] = None
    signature_stub: str = ""

    # -------------------------------------------------------------------------
    # Factory
    # -------------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        issuer: str,
        subject: str,
        scopes: List[str],
        intent: str,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> "AgencyToken":
        """
        Issue a new agency token.

        Validates scopes against the registry at creation time (fail-closed).

        Args:
            issuer:      URI of the issuing platform.
            subject:     Identifier of the consenting principal.
            scopes:      List of action scopes in platform.action.resource format.
            intent:      Natural-language purpose of this delegation.
            ttl_seconds: Token lifetime in seconds (default 3600; max 86400).

        Returns:
            AgencyToken instance (immutable).

        Raises:
            ValueError: If scopes contain unregistered or invalid entries,
                        or if ttl_seconds exceeds MAX_TTL_SECONDS.
        """
        from .scopes import validate_scopes

        if ttl_seconds > MAX_TTL_SECONDS:
            raise ValueError(
                f"ttl_seconds {ttl_seconds} exceeds maximum {MAX_TTL_SECONDS}. "
                "Use a shorter TTL or create multiple tokens."
            )
        if ttl_seconds <= 0:
            raise ValueError(f"ttl_seconds must be positive, got {ttl_seconds}.")

        if not scopes:
            raise ValueError("scopes must not be empty (OAUTH3_EMPTY_SCOPES).")

        # Fail-closed: reject tokens with unregistered scopes at creation time
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

        return cls(
            token_id=token_id,
            issuer=issuer,
            subject=subject,
            scopes=tuple(scopes),
            intent=intent,
            issued_at=issued_at,
            expires_at=expires_at,
            revoked=False,
            revoked_at=None,
            signature_stub=stub,
        )

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
            "issuer": self.issuer,
            "subject": self.subject,
            "scopes": list(self.scopes),
            "intent": self.intent,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
            "revoked_at": self.revoked_at,
            "signature_stub": self.signature_stub,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict) -> "AgencyToken":
        """
        Deserialize from plain dict.

        Enforces null != zero: scopes must be a list, not None.

        Raises:
            ValueError: If required fields are missing or scopes is None.
        """
        scopes = data.get("scopes")
        if scopes is None:
            raise ValueError(
                "scopes must be a list, got null "
                "(null != zero — scopes cannot be None)"
            )

        return cls(
            token_id=data["token_id"],
            issuer=data["issuer"],
            subject=data["subject"],
            scopes=tuple(scopes),
            intent=data.get("intent", ""),
            issued_at=data["issued_at"],
            expires_at=data["expires_at"],
            revoked=data.get("revoked", False),
            revoked_at=data.get("revoked_at", None),
            signature_stub=data.get("signature_stub", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "AgencyToken":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

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
    Create a new AgencyToken (convenience wrapper around AgencyToken.create).

    Args:
        issuer:      URI of the issuing platform.
        subject:     Identifier of the consenting principal.
        scopes:      Granted action scopes (platform.action.resource format).
        intent:      Natural-language purpose of the delegation.
        ttl_seconds: Token lifetime in seconds (default 3600).

    Returns:
        AgencyToken instance.
    """
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
