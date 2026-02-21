"""
OAuth3 Agency Token — AgencyToken dataclass + validation

Schema (stored as JSON in ~/.solace/tokens/{token_id}.json):
{
  "token_id": "uuid4",
  "user_id": "string",
  "issued_at": "ISO8601",
  "expires_at": "ISO8601 (default: 30 days)",
  "scopes": ["linkedin.read_messages", "gmail.send_email"],
  "revoked": false,
  "revoked_at": null,
  "step_up_required_for": ["linkedin.delete_post", "gmail.delete_email"]
}

Rung: 641
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional


# Default token store directory
DEFAULT_TOKEN_DIR = Path.home() / ".solace" / "tokens"
DEFAULT_EXPIRY_DAYS = 30


@dataclass
class AgencyToken:
    """
    OAuth3 agency token — scoped, time-bound, revocable delegation credential.

    Every recipe execution must be bounded by a valid AgencyToken.
    No execution without a valid, non-expired, non-revoked token.
    """

    token_id: str
    user_id: str
    issued_at: str
    expires_at: str
    scopes: List[str]
    revoked: bool = False
    revoked_at: Optional[str] = None
    step_up_required_for: List[str] = field(default_factory=list)

    # -------------------------------------------------------------------------
    # Factory
    # -------------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        user_id: str,
        scopes: List[str],
        expires_hours: int = DEFAULT_EXPIRY_DAYS * 24,
        step_up_required_for: Optional[List[str]] = None,
    ) -> "AgencyToken":
        """
        Issue a new agency token.

        Args:
            user_id: Identifier for the user granting delegation.
            scopes: List of action scopes being delegated.
            expires_hours: Token lifetime in hours (default 720 = 30 days).
            step_up_required_for: Scopes that require step-up re-consent.

        Returns:
            AgencyToken instance (not yet persisted — call save_to_file()).
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=expires_hours)

        from .scopes import STEP_UP_REQUIRED_SCOPES, validate_scopes

        # Fail-closed: reject tokens with unregistered scopes at creation time
        is_valid, unknown = validate_scopes(scopes)
        if not is_valid:
            raise ValueError(
                f"Unknown scope(s): {unknown}. "
                "All scopes must be registered in the OAuth3 scope registry."
            )

        # Auto-populate step_up_required_for from the canonical list
        # if caller doesn't specify
        if step_up_required_for is None:
            step_up_required_for = [s for s in scopes if s in STEP_UP_REQUIRED_SCOPES]

        return cls(
            token_id=str(uuid.uuid4()),
            user_id=user_id,
            issued_at=now.isoformat(),
            expires_at=expires.isoformat(),
            scopes=scopes,
            revoked=False,
            revoked_at=None,
            step_up_required_for=step_up_required_for,
        )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate(self) -> tuple:
        """
        Validate this token.

        Returns:
            (is_valid: bool, error_message: str)
            is_valid is True only if: not expired AND not revoked.
        """
        if self.revoked:
            revoked_at_str = self.revoked_at or "unknown"
            return False, f"token_revoked (revoked_at={revoked_at_str})"

        now = datetime.now(timezone.utc)
        expires_at = _parse_iso8601(self.expires_at)

        if now > expires_at:
            return False, f"token_expired (expired_at={self.expires_at}, now={now.isoformat()})"

        return True, ""

    def has_scope(self, scope: str) -> bool:
        """Return True if this token contains the given scope."""
        return scope in self.scopes

    def requires_step_up(self, scope: str) -> bool:
        """Return True if the given scope requires step-up re-consent."""
        return scope in self.step_up_required_for

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert to plain dict (JSON-serializable)."""
        return {
            "token_id": self.token_id,
            "user_id": self.user_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "scopes": self.scopes,
            "revoked": self.revoked,
            "revoked_at": self.revoked_at,
            "step_up_required_for": self.step_up_required_for,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "AgencyToken":
        """Deserialize from plain dict."""
        scopes = data.get("scopes")
        if scopes is None:
            raise ValueError(
                "scopes must be a list, got null (null != zero — scopes cannot be None)"
            )

        step_up_required_for = data.get("step_up_required_for")
        if step_up_required_for is None:
            raise ValueError(
                "step_up_required_for must be a list, got null "
                "(null != zero — step_up_required_for cannot be None)"
            )

        return cls(
            token_id=data["token_id"],
            user_id=data["user_id"],
            issued_at=data["issued_at"],
            expires_at=data["expires_at"],
            scopes=scopes,
            revoked=data.get("revoked", False),
            revoked_at=data.get("revoked_at", None),
            step_up_required_for=step_up_required_for,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "AgencyToken":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def save_to_file(self, token_dir: Optional[Path] = None) -> Path:
        """
        Persist token to ~/.solace/tokens/{token_id}.json.

        Args:
            token_dir: Directory to save token files (default: ~/.solace/tokens/).

        Returns:
            Path to the saved token file.
        """
        token_dir = token_dir or DEFAULT_TOKEN_DIR
        token_dir.mkdir(parents=True, exist_ok=True)

        token_path = token_dir / f"{self.token_id}.json"
        token_path.write_text(self.to_json(), encoding="utf-8")
        return token_path

    @classmethod
    def load_from_file(cls, token_id: str, token_dir: Optional[Path] = None) -> "AgencyToken":
        """
        Load token from ~/.solace/tokens/{token_id}.json.

        Args:
            token_id: UUID of the token to load.
            token_dir: Directory containing token files.

        Returns:
            AgencyToken instance.

        Raises:
            FileNotFoundError: If token file does not exist.
            json.JSONDecodeError: If token file is malformed.
        """
        token_dir = token_dir or DEFAULT_TOKEN_DIR
        token_path = token_dir / f"{token_id}.json"

        if not token_path.exists():
            raise FileNotFoundError(f"Token not found: {token_id}")

        data = json.loads(token_path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def _persist_updates(self, token_dir: Optional[Path] = None) -> None:
        """
        Write current state back to disk (used after mutation like revocation).
        Internal method — callers should use revocation.revoke_token() instead.
        """
        self.save_to_file(token_dir)

    def __repr__(self) -> str:
        status = "revoked" if self.revoked else "active"
        return (
            f"AgencyToken(id={self.token_id[:8]}..., "
            f"user={self.user_id}, "
            f"scopes={self.scopes}, "
            f"status={status})"
        )


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _parse_iso8601(dt_str: str) -> datetime:
    """
    Parse ISO8601 datetime string to timezone-aware datetime.

    Handles both 'Z' suffix and '+00:00' offset formats.
    """
    # Python 3.10 fromisoformat handles 'Z', earlier versions do not
    dt_str = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
