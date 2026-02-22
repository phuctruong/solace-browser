"""
Multi-Profile Browser Manager — OAuth3-isolated browser profiles.

Each BrowserProfile is a complete, isolated browser context:
  - Unique profile_id (UUID v4)
  - Separate cookie jar path (no cross-profile leakage)
  - Separate OAuth3 token namespace (oauth3_token_ids list)
  - Independent viewport, user-agent, proxy, extensions
  - ISO 8601 UTC timestamps for created_at and last_used

ProfileManager enforces:
  - No cross-profile data access (isolation contract)
  - Default profile always exists and cannot be deleted
  - Profile switches are logged with timestamps (evidence trail)
  - delete() requires OAuth3 scope machine.file.delete + step-up

OAuth3 scopes:
  machine.file.delete  — delete a profile (HIGH RISK — step-up required)

Rung: 641
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _sha256_hex(data: dict) -> str:
    """Compute SHA-256 hex digest of a canonical JSON dict."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_VIEWPORT: Dict[str, int] = {"width": 1280, "height": 720}
DEFAULT_USER_AGENT: str = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 SolaceBrowser/0.1"
)
DEFAULT_PROFILE_NAME: str = "default"

# OAuth3 scopes referenced by ProfileManager
SCOPE_FILE_DELETE: str = "machine.file.delete"
SCOPE_PROCESS_LIST: str = "machine.process.list"

# Max profiles allowed per manager instance
MAX_PROFILES: int = 100


# ---------------------------------------------------------------------------
# ProfileSession — session state dataclass (for backward compat with __init__)
# ---------------------------------------------------------------------------

@dataclass
class ProfileSession:
    """
    A single browser profile session (lightweight session state).

    Fields:
        session_id:         UUID v4 unique session identifier.
        profile_id:         ID of the profile this session belongs to.
        status:             Current state: idle|active|suspended|terminated.
        started_at:         ISO 8601 UTC timestamp of session start.
        last_activity_at:   ISO 8601 UTC timestamp of last activity.
        pages_visited:      Integer count of pages visited.
        oauth3_scopes_used: List of OAuth3 scope strings exercised.
    """

    session_id: str
    profile_id: str
    status: str
    started_at: str
    last_activity_at: str
    pages_visited: int
    oauth3_scopes_used: List[str]

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "profile_id": self.profile_id,
            "status": self.status,
            "started_at": self.started_at,
            "last_activity_at": self.last_activity_at,
            "pages_visited": int(self.pages_visited),
            "oauth3_scopes_used": list(self.oauth3_scopes_used),
        }


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ProfileError(Exception):
    """Base class for all ProfileManager errors."""


class ProfileNotFoundError(ProfileError):
    """Raised when a profile_id is not found in the registry."""


class ProfileIsolationError(ProfileError):
    """Raised when a cross-profile access attempt is detected."""


# ---------------------------------------------------------------------------
# BrowserProfile dataclass
# ---------------------------------------------------------------------------

@dataclass
class BrowserProfile:
    """
    A browser profile — a fully isolated execution context.

    Fields:
        profile_id:       UUID v4 unique identifier.
        name:             Human-readable profile name.
        user_agent:       Browser User-Agent header string.
        viewport:         {"width": int, "height": int} in pixels.
        cookies_path:     Path to this profile's cookie jar (isolated).
        proxy:            Optional proxy URL (e.g. "socks5://localhost:1080").
        extensions:       Installed browser extension IDs.
        oauth3_token_ids: OAuth3 token IDs bound to this profile (isolated).
        created_at:       ISO 8601 UTC creation timestamp.
        last_used:        ISO 8601 UTC last activation timestamp.
    """

    profile_id: str
    name: str
    user_agent: str
    viewport: Dict[str, int]
    cookies_path: str
    proxy: Optional[str]
    extensions: List[str]
    oauth3_token_ids: List[str]
    created_at: str
    last_used: str

    # ------------------------------------------------------------------
    # Evidence / integrity
    # ------------------------------------------------------------------

    def sha256_hash(self) -> str:
        """
        Return SHA-256 hex digest of canonical profile fields.

        Used for audit trail integrity.
        """
        canonical = {
            "profile_id": self.profile_id,
            "name": self.name,
            "user_agent": self.user_agent,
            "viewport": self.viewport,
            "cookies_path": self.cookies_path,
            "created_at": self.created_at,
        }
        return _sha256_hex(canonical)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Convert to plain dict (JSON-serializable)."""
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "user_agent": self.user_agent,
            "viewport": dict(self.viewport),
            "cookies_path": self.cookies_path,
            "proxy": self.proxy,
            "extensions": list(self.extensions),
            "oauth3_token_ids": list(self.oauth3_token_ids),
            "created_at": self.created_at,
            "last_used": self.last_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BrowserProfile":
        """Deserialize from plain dict."""
        if data.get("oauth3_token_ids") is None:
            raise ValueError("oauth3_token_ids must be a list, not null.")
        if data.get("extensions") is None:
            raise ValueError("extensions must be a list, not null.")
        return cls(
            profile_id=data["profile_id"],
            name=data["name"],
            user_agent=data.get("user_agent", DEFAULT_USER_AGENT),
            viewport=dict(data.get("viewport", DEFAULT_VIEWPORT)),
            cookies_path=data["cookies_path"],
            proxy=data.get("proxy", None),
            extensions=list(data.get("extensions", [])),
            oauth3_token_ids=list(data.get("oauth3_token_ids", [])),
            created_at=data["created_at"],
            last_used=data["last_used"],
        )

    def __repr__(self) -> str:
        return (
            f"BrowserProfile(id={self.profile_id[:8]}..., "
            f"name={self.name!r}, "
            f"viewport={self.viewport['width']}x{self.viewport['height']})"
        )


# ---------------------------------------------------------------------------
# SwitchEvent — evidence log entry for profile switches
# ---------------------------------------------------------------------------

@dataclass
class SwitchEvent:
    """
    Evidence record of a profile switch operation.

    Every call to ProfileManager.switch() appends one of these to the
    switch_log. Used to prove that isolation was maintained across
    profile transitions.
    """

    from_profile_id: Optional[str]   # None if no profile was active
    to_profile_id: str
    switched_at: str                  # ISO 8601 UTC
    sha256_to: str                    # SHA-256 of the target profile at switch time

    def to_dict(self) -> dict:
        return {
            "from_profile_id": self.from_profile_id,
            "to_profile_id": self.to_profile_id,
            "switched_at": self.switched_at,
            "sha256_to": self.sha256_to,
        }


# ---------------------------------------------------------------------------
# ProfileManager
# ---------------------------------------------------------------------------

class ProfileManager:
    """
    Manage multiple isolated browser profiles.

    Guarantees:
      1. No cross-profile data leakage: each profile has its own cookie jar
         and OAuth3 token set. Accessing another profile's tokens raises
         ProfileIsolationError.
      2. Default profile always exists: it is created at init time and
         cannot be deleted (raises ProfileError).
      3. Profile switches are logged with timestamps (evidence trail).
      4. delete() enforces OAuth3 scope machine.file.delete + step-up
         semantics (raises ProfileError without confirmation).

    Usage:
        pm = ProfileManager()
        p = pm.create("Work", user_agent="...", viewport={"width": 1920, "height": 1080})
        pm.switch(p.profile_id)
        pm.delete(p.profile_id, oauth3_confirmed=True, step_up_confirmed=True)
    """

    def __init__(self) -> None:
        self._profiles: Dict[str, BrowserProfile] = {}
        self._active_profile_id: Optional[str] = None
        self.switch_log: List[SwitchEvent] = []

        # Always create the default profile at init time
        self._default_profile_id: str = self._create_default_profile()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cookies_path_for(self, profile_id: str) -> str:
        """Derive an isolated cookie jar path for a profile."""
        return f"~/.solace/profiles/{profile_id}/cookies.db"

    def _create_default_profile(self) -> str:
        """Create the immutable default profile and return its ID."""
        profile_id = str(uuid.uuid4())
        now = _now_iso()
        profile = BrowserProfile(
            profile_id=profile_id,
            name=DEFAULT_PROFILE_NAME,
            user_agent=DEFAULT_USER_AGENT,
            viewport=dict(DEFAULT_VIEWPORT),
            cookies_path=self._cookies_path_for(profile_id),
            proxy=None,
            extensions=[],
            oauth3_token_ids=[],
            created_at=now,
            last_used=now,
        )
        self._profiles[profile_id] = profile
        return profile_id

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        user_agent: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None,
        proxy: Optional[str] = None,
        extensions: Optional[List[str]] = None,
    ) -> BrowserProfile:
        """
        Create a new isolated browser profile.

        Args:
            name:       Human-readable profile name.
            user_agent: Browser user-agent string (defaults to DEFAULT_USER_AGENT).
            viewport:   {"width": int, "height": int} (defaults to DEFAULT_VIEWPORT).
            proxy:      Optional proxy URL.
            extensions: Optional list of extension IDs.

        Returns:
            New BrowserProfile instance.
        """
        profile_id = str(uuid.uuid4())
        now = _now_iso()

        profile = BrowserProfile(
            profile_id=profile_id,
            name=name,
            user_agent=user_agent or DEFAULT_USER_AGENT,
            viewport=dict(viewport) if viewport else dict(DEFAULT_VIEWPORT),
            cookies_path=self._cookies_path_for(profile_id),
            proxy=proxy,
            extensions=list(extensions) if extensions else [],
            oauth3_token_ids=[],
            created_at=now,
            last_used=now,
        )
        self._profiles[profile_id] = profile
        return profile

    def get(self, profile_id: str) -> Optional[BrowserProfile]:
        """
        Return the profile for the given profile_id, or None if not found.

        Args:
            profile_id: UUID v4 profile identifier.

        Returns:
            BrowserProfile or None.
        """
        return self._profiles.get(profile_id)

    def list_profiles(self) -> List[BrowserProfile]:
        """
        Return all profiles (including the default profile).

        Returns:
            List of BrowserProfile instances, ordered by creation time.
        """
        return sorted(
            self._profiles.values(),
            key=lambda p: p.created_at,
        )

    def delete(
        self,
        profile_id: str,
        oauth3_confirmed: bool = False,
        step_up_confirmed: bool = False,
    ) -> bool:
        """
        Delete a browser profile.

        Requires oauth3_confirmed=True (OAuth3 scope machine.file.delete)
        AND step_up_confirmed=True (step-up re-consent for destructive action).

        The default profile cannot be deleted.

        Args:
            profile_id:        UUID v4 of the profile to delete.
            oauth3_confirmed:  True if machine.file.delete scope is granted.
            step_up_confirmed: True if step-up consent was obtained.

        Returns:
            True on success.

        Raises:
            ProfileError:         If trying to delete the default profile, or
                                  missing OAuth3 scope / step-up.
            ProfileNotFoundError: If profile_id does not exist.
        """
        # Gate 1: default profile is immutable
        if profile_id == self._default_profile_id:
            raise ProfileError(
                "Cannot delete the default profile. "
                "The default profile is permanent and always available."
            )

        # Gate 2: profile must exist
        if profile_id not in self._profiles:
            raise ProfileNotFoundError(
                f"Profile not found: {profile_id}"
            )

        # Gate 3: OAuth3 scope check
        if not oauth3_confirmed:
            raise ProfileError(
                f"OAuth3 scope required: {SCOPE_FILE_DELETE}. "
                "Set oauth3_confirmed=True after verifying the token grants this scope."
            )

        # Gate 4: step-up required (machine.file.delete is a destructive scope)
        if not step_up_confirmed:
            raise ProfileError(
                "Step-up re-consent required for profile deletion (destructive action). "
                "Set step_up_confirmed=True after the user confirms via the step-up flow."
            )

        # All gates passed — delete the profile
        del self._profiles[profile_id]

        # If the deleted profile was active, fall back to default
        if self._active_profile_id == profile_id:
            self._active_profile_id = self._default_profile_id

        return True

    # ------------------------------------------------------------------
    # Switch
    # ------------------------------------------------------------------

    def switch(self, profile_id: str) -> BrowserProfile:
        """
        Activate a profile and suspend the currently active one.

        Records a SwitchEvent in the switch_log for evidence.

        Args:
            profile_id: UUID v4 of the profile to activate.

        Returns:
            The newly activated BrowserProfile.

        Raises:
            ProfileNotFoundError: If profile_id does not exist.
        """
        if profile_id not in self._profiles:
            raise ProfileNotFoundError(
                f"Profile not found: {profile_id}"
            )

        now = _now_iso()
        old_id = self._active_profile_id
        new_profile = self._profiles[profile_id]

        # Update last_used timestamp on the target profile
        updated = BrowserProfile(
            profile_id=new_profile.profile_id,
            name=new_profile.name,
            user_agent=new_profile.user_agent,
            viewport=dict(new_profile.viewport),
            cookies_path=new_profile.cookies_path,
            proxy=new_profile.proxy,
            extensions=list(new_profile.extensions),
            oauth3_token_ids=list(new_profile.oauth3_token_ids),
            created_at=new_profile.created_at,
            last_used=now,
        )
        self._profiles[profile_id] = updated
        self._active_profile_id = profile_id

        # Log evidence
        event = SwitchEvent(
            from_profile_id=old_id,
            to_profile_id=profile_id,
            switched_at=now,
            sha256_to=updated.sha256_hash(),
        )
        self.switch_log.append(event)

        return updated

    # ------------------------------------------------------------------
    # Active profile access
    # ------------------------------------------------------------------

    @property
    def active_profile(self) -> Optional[BrowserProfile]:
        """Return the currently active BrowserProfile, or None."""
        if self._active_profile_id is None:
            return None
        return self._profiles.get(self._active_profile_id)

    @property
    def default_profile(self) -> BrowserProfile:
        """Return the default (immutable) profile."""
        return self._profiles[self._default_profile_id]

    # ------------------------------------------------------------------
    # Isolation enforcement
    # ------------------------------------------------------------------

    def get_tokens_for_profile(
        self,
        requesting_profile_id: str,
        target_profile_id: str,
    ) -> List[str]:
        """
        Return the OAuth3 token IDs for target_profile_id.

        Cross-profile access is blocked: requesting_profile_id must equal
        target_profile_id, or a ProfileIsolationError is raised.

        Args:
            requesting_profile_id: Profile making the request.
            target_profile_id:     Profile whose tokens are requested.

        Returns:
            List of OAuth3 token ID strings.

        Raises:
            ProfileIsolationError: If cross-profile access is attempted.
            ProfileNotFoundError:  If target_profile_id does not exist.
        """
        if requesting_profile_id != target_profile_id:
            raise ProfileIsolationError(
                f"Cross-profile token access blocked: "
                f"profile {requesting_profile_id!r} attempted to read tokens "
                f"of profile {target_profile_id!r}. "
                "Each profile's OAuth3 tokens are isolated."
            )

        profile = self._profiles.get(target_profile_id)
        if profile is None:
            raise ProfileNotFoundError(
                f"Profile not found: {target_profile_id}"
            )

        return list(profile.oauth3_token_ids)

    def add_token_to_profile(self, profile_id: str, token_id: str) -> bool:
        """
        Associate an OAuth3 token ID with a profile.

        Args:
            profile_id: UUID v4 of the target profile.
            token_id:   OAuth3 token_id to bind.

        Returns:
            True on success.

        Raises:
            ProfileNotFoundError: If profile_id does not exist.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"Profile not found: {profile_id}")

        if token_id not in profile.oauth3_token_ids:
            updated_tokens = list(profile.oauth3_token_ids) + [token_id]
            updated = BrowserProfile(
                profile_id=profile.profile_id,
                name=profile.name,
                user_agent=profile.user_agent,
                viewport=dict(profile.viewport),
                cookies_path=profile.cookies_path,
                proxy=profile.proxy,
                extensions=list(profile.extensions),
                oauth3_token_ids=updated_tokens,
                created_at=profile.created_at,
                last_used=profile.last_used,
            )
            self._profiles[profile_id] = updated
        return True

    def cookies_path_for(self, profile_id: str) -> str:
        """
        Return the isolated cookie jar path for a profile.

        Args:
            profile_id: UUID v4 of the profile.

        Returns:
            Cookie jar path string.

        Raises:
            ProfileNotFoundError: If profile_id does not exist.
        """
        profile = self._profiles.get(profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"Profile not found: {profile_id}")
        return profile.cookies_path

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        n = len(self._profiles)
        active = self._active_profile_id
        return (
            f"ProfileManager(profiles={n}, "
            f"active={active[:8] + '...' if active else 'None'})"
        )
