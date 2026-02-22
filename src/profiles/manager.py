"""
Multi-Profile Browser Manager — OAuth3-governed browser profile management.

Provides isolated browser profiles where each session is bound to an OAuth3
token, scopes enforced per action, and all activity logged with SHA-256 evidence.

Architecture:
  BrowserProfile   — profile configuration dataclass
  ProfileSession   — session state dataclass
  ProfileManager   — create/delete profiles, start/suspend/resume/terminate sessions

Security contract:
  - Sessions cannot access other profiles data (profile isolation)
  - Each session is bound to an OAuth3 token (token_id stored, not validated inline)
  - Delete profile requires step-up auth (profile.delete.profile is HIGH RISK)
  - All timestamps are ISO 8601 UTC strings
  - All hashes are sha256: prefixed hex strings
  - No float in verification paths (int only)
  - Never store plaintext credentials, reference encrypted vault only

Rung: 274177 (session lifecycle, potentially irreversible operations)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
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
# Constants
# ---------------------------------------------------------------------------

DEFAULT_VIEWPORT: Dict[str, int] = {"width": 1280, "height": 720}
DEFAULT_USER_AGENT: str = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 SolaceBrowser/0.1"
)
DEFAULT_PROFILE_NAME: str = "default"

# OAuth3 scopes referenced by ProfileManager (legacy backward-compat names)
SCOPE_FILE_DELETE: str = "machine.file.delete"
SCOPE_PROCESS_LIST: str = "machine.process.list"

# Max profiles allowed per manager instance
MAX_PROFILES: int = 100


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
    A browser profile with OAuth3 governance.

    Fields:
        profile_id:             UUID4 globally unique profile identifier.
        name:                   Human-readable profile name.
        user_agent:             Browser user-agent string for this profile.
        viewport:               Viewport dict with width (int) and height (int) keys.
        proxy:                  Proxy URL string, or None for direct connection.
        cookies_enabled:        Whether cookies are enabled for this profile.
        oauth3_token_id:        token_id of the AgencyToken that authorized creation.
        created_at:             ISO 8601 UTC timestamp of profile creation.
        platform_credentials:   Dict of credential references (encrypted vault refs only).
    """

    profile_id: str
    name: str
    user_agent: str
    viewport: Dict[str, int]
    proxy: Optional[str]
    cookies_enabled: bool
    oauth3_token_id: str
    created_at: str
    platform_credentials: Dict

    def sha256_hash(self) -> str:
        """Return SHA-256 hex digest of canonical profile fields."""
        canonical = {
            "profile_id": self.profile_id,
            "name": self.name,
            "user_agent": self.user_agent,
            "viewport": self.viewport,
            "created_at": self.created_at,
        }
        return _sha256_hex(canonical)

    def to_dict(self) -> dict:
        """Convert to plain dict. Credential values are masked."""
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "user_agent": self.user_agent,
            "viewport": dict(self.viewport),
            "proxy": self.proxy,
            "cookies_enabled": self.cookies_enabled,
            "oauth3_token_id": self.oauth3_token_id,
            "created_at": self.created_at,
            "platform_credentials": {
                k: "***vault-ref***"
                if any(kw in k.lower() for kw in ("secret", "password", "token", "key"))
                else v
                for k, v in self.platform_credentials.items()
            },
        }

    def __repr__(self) -> str:
        return (
            f"BrowserProfile(id={self.profile_id[:8]}..., "
            f"name={self.name!r}, "
            f"viewport={self.viewport.get('width')}x{self.viewport.get('height')})"
        )


# ---------------------------------------------------------------------------
# ProfileSession dataclass
# ---------------------------------------------------------------------------

@dataclass
class ProfileSession:
    """
    A single browser profile session.

    States: idle -> active -> suspended -> terminated

    Fields:
        session_id:         UUID4 globally unique session identifier.
        profile_id:         ID of the profile this session belongs to.
        status:             Current lifecycle state (idle|active|suspended|terminated).
        started_at:         ISO 8601 UTC timestamp of session start.
        last_activity_at:   ISO 8601 UTC timestamp of last recorded activity.
        pages_visited:      Count of pages visited in this session (int, never float).
        oauth3_scopes_used: List of OAuth3 scope strings exercised in this session.
    """

    session_id: str
    profile_id: str
    status: str
    started_at: str
    last_activity_at: str
    pages_visited: int
    oauth3_scopes_used: List[str]

    def to_dict(self) -> dict:
        """Serialize to plain dict (JSON-serializable)."""
        return {
            "session_id": self.session_id,
            "profile_id": self.profile_id,
            "status": self.status,
            "started_at": self.started_at,
            "last_activity_at": self.last_activity_at,
            "pages_visited": int(self.pages_visited),
            "oauth3_scopes_used": list(self.oauth3_scopes_used),
        }

    def __repr__(self) -> str:
        return (
            f"ProfileSession(id={self.session_id[:8]}..., "
            f"profile={self.profile_id[:8]}..., "
            f"status={self.status!r}, "
            f"pages={self.pages_visited})"
        )


# ---------------------------------------------------------------------------
# SwitchEvent dataclass (backward compat)
# ---------------------------------------------------------------------------

@dataclass
class SwitchEvent:
    """Evidence record of a profile switch operation."""

    from_profile_id: Optional[str]
    to_profile_id: str
    switched_at: str
    sha256_to: str

    def to_dict(self) -> dict:
        return {
            "from_profile_id": self.from_profile_id,
            "to_profile_id": self.to_profile_id,
            "switched_at": self.switched_at,
            "sha256_to": self.sha256_to,
        }


# ---------------------------------------------------------------------------
# Viewport validation
# ---------------------------------------------------------------------------

def _validate_viewport(viewport: dict) -> Optional[str]:
    """Validate viewport dict. Returns None if valid, error string if invalid."""
    if not isinstance(viewport, dict):
        return "viewport must be a dict"
    width = viewport.get("width")
    height = viewport.get("height")
    if not isinstance(width, int) or isinstance(width, bool):
        return "viewport.width must be an integer"
    if not isinstance(height, int) or isinstance(height, bool):
        return "viewport.height must be an integer"
    if width <= 0:
        return f"viewport.width must be positive, got {width}"
    if height <= 0:
        return f"viewport.height must be positive, got {height}"
    return None


# ---------------------------------------------------------------------------
# ProfileManager
# ---------------------------------------------------------------------------

class ProfileManager:
    """
    OAuth3-governed browser profile manager.

    create_profile / delete_profile / list_profiles
    start_session / suspend_session / resume_session / terminate_session
    get_session_stats

    Rung: 274177
    """

    def __init__(self) -> None:
        self._profiles: Dict[str, BrowserProfile] = {}
        self._sessions: Dict[str, ProfileSession] = {}
        self._audit_log: List[dict] = []
        self._active_profile_id: Optional[str] = None
        self.switch_log: List[SwitchEvent] = []

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _audit(self, event: str, data: dict) -> dict:
        entry = {"event": event, "timestamp": _now_iso(), **data}
        entry["integrity_hash"] = _sha256_hex(entry)
        self._audit_log.append(entry)
        return entry

    # -------------------------------------------------------------------------
    # Profile management
    # -------------------------------------------------------------------------

    def create_profile(
        self,
        name: str,
        config: Optional[dict] = None,
        token_id: str = "",
    ) -> BrowserProfile:
        """
        Create a new browser profile.

        OAuth3 scope required: profile.create.profile (MEDIUM)

        Args:
            name:     Human-readable profile name.
            config:   Profile configuration dict with keys:
                        user_agent, viewport, proxy, cookies_enabled, platform_credentials
            token_id: OAuth3 token_id authorizing this creation (audit trail).

        Returns:
            The new BrowserProfile.

        Raises:
            ValueError: If name is empty, viewport is invalid, or max profiles reached.
        """
        if config is None:
            config = {}

        if not name or not name.strip():
            raise ValueError("Profile name must not be empty.")

        if len(self._profiles) >= MAX_PROFILES:
            raise ValueError(
                f"Maximum profile count ({MAX_PROFILES}) reached."
            )

        user_agent = config.get("user_agent", DEFAULT_USER_AGENT)
        if not isinstance(user_agent, str) or not user_agent.strip():
            user_agent = DEFAULT_USER_AGENT

        viewport = config.get("viewport", dict(DEFAULT_VIEWPORT))
        viewport_error = _validate_viewport(viewport)
        if viewport_error:
            raise ValueError(f"Invalid viewport: {viewport_error}")
        viewport = {
            "width": int(viewport["width"]),
            "height": int(viewport["height"]),
        }

        proxy = config.get("proxy", None)
        if proxy is not None and not isinstance(proxy, str):
            proxy = None

        cookies_enabled = config.get("cookies_enabled", True)
        if not isinstance(cookies_enabled, bool):
            cookies_enabled = bool(cookies_enabled)

        raw_creds = config.get("platform_credentials", {})
        platform_credentials = dict(raw_creds) if isinstance(raw_creds, dict) else {}

        profile_id = str(uuid.uuid4())
        created_at = _now_iso()

        profile = BrowserProfile(
            profile_id=profile_id,
            name=name.strip(),
            user_agent=user_agent,
            viewport=viewport,
            proxy=proxy,
            cookies_enabled=cookies_enabled,
            oauth3_token_id=token_id,
            created_at=created_at,
            platform_credentials=platform_credentials,
        )

        self._profiles[profile_id] = profile

        self._audit("profile_created", {
            "profile_id": profile_id,
            "name": name.strip(),
            "token_id": token_id,
        })

        return profile

    def delete_profile(
        self,
        profile_id: str,
        token_id: str = "",
        step_up_confirmed: bool = False,
    ) -> bool:
        """
        Delete a browser profile and all its sessions.

        OAuth3 scope required: profile.delete.profile (HIGH, step-up required)

        Returns:
            True if deleted, False if profile not found.

        Raises:
            PermissionError: If step_up_confirmed is False.
        """
        if not step_up_confirmed:
            raise PermissionError(
                "profile.delete.profile requires step-up authorization."
            )

        if profile_id not in self._profiles:
            return False

        sessions_to_remove = [
            sid for sid, sess in self._sessions.items()
            if sess.profile_id == profile_id
        ]
        for sid in sessions_to_remove:
            self._sessions.pop(sid)
            self._audit("session_terminated_on_profile_delete", {
                "session_id": sid,
                "profile_id": profile_id,
                "token_id": token_id,
            })

        del self._profiles[profile_id]

        if self._active_profile_id == profile_id:
            self._active_profile_id = None

        self._audit("profile_deleted", {
            "profile_id": profile_id,
            "token_id": token_id,
            "sessions_terminated": len(sessions_to_remove),
        })

        return True

    def list_profiles(self) -> List[BrowserProfile]:
        """
        List all browser profiles.

        OAuth3 scope required: profile.read.list (LOW)
        """
        return list(self._profiles.values())

    def get(self, profile_id: str) -> Optional[BrowserProfile]:
        """Return the profile for the given profile_id, or None."""
        return self._profiles.get(profile_id)

    # -------------------------------------------------------------------------
    # Session lifecycle
    # -------------------------------------------------------------------------

    def start_session(
        self,
        profile_id: str,
        token_id: str,
    ) -> ProfileSession:
        """
        Start a new browsing session for the given profile.

        OAuth3 scope required: profile.session.start (MEDIUM)

        Raises:
            ValueError: If profile_id is not found or token_id is empty.
        """
        if not token_id:
            raise ValueError(
                "token_id is required to start a session. "
                "Each session must be bound to an OAuth3 token."
            )

        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' not found.")

        session_id = str(uuid.uuid4())
        now = _now_iso()

        session = ProfileSession(
            session_id=session_id,
            profile_id=profile_id,
            status="active",
            started_at=now,
            last_activity_at=now,
            pages_visited=0,
            oauth3_scopes_used=["profile.session.start"],
        )

        self._sessions[session_id] = session

        self._audit("session_start", {
            "session_id": session_id,
            "profile_id": profile_id,
            "token_id": token_id,
        })

        return session

    def suspend_session(self, session_id: str) -> bool:
        """
        Suspend an active session.

        OAuth3 scope required: profile.session.suspend (LOW)

        Returns:
            True if suspended/already-suspended, False if not found or terminated.

        Raises:
            ValueError: If session is in invalid state for suspension.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False
        if session.status == "terminated":
            return False
        if session.status == "suspended":
            return True
        if session.status != "active":
            raise ValueError(
                f"Cannot suspend session in state '{session.status}'."
            )
        session.status = "suspended"
        session.last_activity_at = _now_iso()
        self._audit("session_suspend", {
            "session_id": session_id,
            "profile_id": session.profile_id,
            "pages_visited": int(session.pages_visited),
        })
        return True

    def resume_session(self, session_id: str) -> bool:
        """
        Resume a suspended session.

        OAuth3 scope required: profile.session.resume (LOW)

        Returns:
            True if resumed/already-active, False if not found or terminated.

        Raises:
            ValueError: If session is in invalid state for resume.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False
        if session.status == "terminated":
            return False
        if session.status == "active":
            return True
        if session.status != "suspended":
            raise ValueError(
                f"Cannot resume session in state '{session.status}'."
            )
        session.status = "active"
        session.last_activity_at = _now_iso()
        self._audit("session_resume", {
            "session_id": session_id,
            "profile_id": session.profile_id,
            "pages_visited": int(session.pages_visited),
        })
        return True

    def terminate_session(
        self,
        session_id: str,
        token_id: str = "",
        step_up_confirmed: bool = False,
    ) -> bool:
        """
        Terminate a session (irreversible).

        OAuth3 scope required: profile.session.terminate (HIGH, step-up required)

        Returns:
            True if terminated, False if not found.

        Raises:
            PermissionError: If step_up_confirmed is False.
        """
        if not step_up_confirmed:
            raise PermissionError(
                "profile.session.terminate requires step-up authorization."
            )
        session = self._sessions.get(session_id)
        if session is None:
            return False
        if session.status == "terminated":
            return True
        prev_status = session.status
        session.status = "terminated"
        session.last_activity_at = _now_iso()
        self._audit("session_terminate", {
            "session_id": session_id,
            "profile_id": session.profile_id,
            "token_id": token_id,
            "prev_status": prev_status,
            "pages_visited": int(session.pages_visited),
            "scopes_used": list(session.oauth3_scopes_used),
        })
        self._sessions.pop(session_id, None)
        return True

    def get_session_stats(self, session_id: str) -> dict:
        """
        Return statistics for a session.

        OAuth3 scope required: profile.session.read (LOW)

        Returns:
            Dict with session metrics, or {"error": ...} if not found.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return {
                "error": "SESSION_NOT_FOUND",
                "detail": f"Session '{session_id}' not found.",
            }
        return {
            "session_id": session.session_id,
            "profile_id": session.profile_id,
            "status": session.status,
            "started_at": session.started_at,
            "last_activity_at": session.last_activity_at,
            "pages_visited": int(session.pages_visited),
            "oauth3_scopes_used": list(session.oauth3_scopes_used),
            "scope_count": len(session.oauth3_scopes_used),
        }

    # -------------------------------------------------------------------------
    # Session listing (isolation enforcement)
    # -------------------------------------------------------------------------

    def list_sessions_for_profile(self, profile_id: str) -> List[ProfileSession]:
        """List sessions belonging to a specific profile only (isolation)."""
        return [
            sess for sess in self._sessions.values()
            if sess.profile_id == profile_id
        ]

    def list_all_sessions(self) -> List[ProfileSession]:
        """List all active sessions across all profiles."""
        return list(self._sessions.values())

    # -------------------------------------------------------------------------
    # Isolation enforcement
    # -------------------------------------------------------------------------

    def get_tokens_for_profile(
        self,
        requesting_profile_id: str,
        target_profile_id: str,
    ) -> List[str]:
        """
        Return OAuth3 token IDs for target_profile_id.

        Cross-profile access blocked: requesting_profile_id must equal target_profile_id.

        Raises:
            ProfileIsolationError: If cross-profile access is attempted.
            ProfileNotFoundError:  If target_profile_id does not exist.
        """
        if requesting_profile_id != target_profile_id:
            raise ProfileIsolationError(
                f"Cross-profile token access blocked: "
                f"profile {requesting_profile_id!r} attempted to read tokens "
                f"of profile {target_profile_id!r}."
            )
        profile = self._profiles.get(target_profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"Profile not found: {target_profile_id}")
        return [profile.oauth3_token_id] if profile.oauth3_token_id else []

    # -------------------------------------------------------------------------
    # Activity recording
    # -------------------------------------------------------------------------

    def record_page_visit(self, session_id: str, scope_used: str = "") -> bool:
        """Record a page visit (increments counter, updates activity timestamp)."""
        session = self._sessions.get(session_id)
        if session is None or session.status != "active":
            return False
        session.pages_visited = int(session.pages_visited) + 1
        session.last_activity_at = _now_iso()
        if scope_used and scope_used not in session.oauth3_scopes_used:
            session.oauth3_scopes_used.append(scope_used)
        return True

    # -------------------------------------------------------------------------
    # Audit trail access
    # -------------------------------------------------------------------------

    def get_audit_log(self) -> List[dict]:
        """Return a copy of the append-only audit log."""
        return list(self._audit_log)

    # -------------------------------------------------------------------------
    # Legacy switch() for backward compat
    # -------------------------------------------------------------------------

    def switch(self, profile_id: str) -> BrowserProfile:
        """Activate a profile (legacy API). Records a SwitchEvent for evidence."""
        if profile_id not in self._profiles:
            raise ProfileNotFoundError(f"Profile not found: {profile_id}")
        now = _now_iso()
        old_id = self._active_profile_id
        profile = self._profiles[profile_id]
        self._active_profile_id = profile_id
        event = SwitchEvent(
            from_profile_id=old_id,
            to_profile_id=profile_id,
            switched_at=now,
            sha256_to=profile.sha256_hash(),
        )
        self.switch_log.append(event)
        return profile

    @property
    def active_profile(self) -> Optional[BrowserProfile]:
        """Return the currently active BrowserProfile, or None."""
        if self._active_profile_id is None:
            return None
        return self._profiles.get(self._active_profile_id)

    # -------------------------------------------------------------------------
    # Representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"ProfileManager(profiles={len(self._profiles)}, "
            f"active_sessions={len(self._sessions)})"
        )
