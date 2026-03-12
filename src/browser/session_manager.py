"""
Multi-Browser Session Manager — Concurrent Isolated Browser Sessions

Manages multiple simultaneous browser sessions, each with its own:
- Chrome DevTools Protocol (CDP) port (auto-assigned from 9230-9250 range)
- User data directory (~/.solace/sessions/{session_id}/)
- Auth token registered with AuthProxy
- Session manifest (session.json)
- Evidence chain entries

Pre-configured profiles:
- phuc-gmail      -> user@example.com
- phuc-phucnet    -> phuc@phuc.net
- phuc-phuclabs   -> user@work.example.com
- incognito       -> no account, fresh temp dir each time

Design:
- FAIL-CLOSED: Invalid profile or port exhaustion -> raise, never degrade
- NO silent fallback: If ports are exhausted, raise PortExhaustionError
- Evidence: Session create/close logged to evidence chain
- Thread-safe: All session mutations under a lock

Reference: Multi-browser hackathon sprint
Rung: 641
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("session_manager")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PORT_RANGE_START = 9230
PORT_RANGE_END = 9250  # inclusive

SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_CLOSED = "closed"

GENESIS_HASH = "0" * 64

# Pre-configured profiles: profile_name -> (user_email, default_scopes)
PRECONFIGURED_PROFILES: dict[str, tuple[str, list[str]]] = {
    "phuc-gmail": (
        "user@example.com",
        ["browser.read.dom", "browser.write.input", "browser.navigate"],
    ),
    "phuc-phucnet": (
        "phuc@phuc.net",
        ["browser.read.dom", "browser.write.input", "browser.navigate"],
    ),
    "phuc-phuclabs": (
        "user@work.example.com",
        ["browser.read.dom", "browser.write.input", "browser.navigate"],
    ),
    "incognito": (
        "",
        ["browser.read.dom"],
    ),
}


# ---------------------------------------------------------------------------
# Errors — specific, never generic
# ---------------------------------------------------------------------------

class SessionError(Exception):
    """Base error for session operations."""


class PortExhaustionError(SessionError):
    """All ports in the 9230-9250 range are in use."""


class SessionNotFoundError(SessionError):
    """Requested session_id does not exist."""


class DuplicateSessionError(SessionError):
    """A session with this session_id already exists."""


class InvalidProfileError(SessionError):
    """The requested profile name is not recognized."""


# ---------------------------------------------------------------------------
# Evidence chain (session-level, mirrors execution_lifecycle pattern)
# ---------------------------------------------------------------------------

class _SessionEvidenceChain:
    """Append-only hash-chained evidence log for session events."""

    def __init__(self, path: Path, *, now_fn: Callable[[], datetime]) -> None:
        self._path = path
        self._now = now_fn
        self._prev_hash = GENESIS_HASH
        self._index = 0

    def append(self, event: str, detail: dict[str, Any]) -> str:
        """Append an event to the evidence chain. Returns the entry hash."""
        record = {
            "entry_id": self._index,
            "timestamp": self._now().isoformat(),
            "event": event,
            "detail": detail,
            "prev_hash": self._prev_hash,
        }
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
        entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        record["entry_hash"] = entry_hash
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        self._prev_hash = entry_hash
        self._index += 1
        return entry_hash


# ---------------------------------------------------------------------------
# Session dataclass
# ---------------------------------------------------------------------------

@dataclass
class SessionRecord:
    """Internal record for a managed browser session."""
    session_id: str
    profile: str
    user_email: str
    port: int
    status: str
    incognito: bool
    user_data_dir: Path
    created_at: datetime
    closed_at: datetime | None = None
    auth_token: str | None = None
    evidence_chain_path: Path | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        result: dict[str, Any] = {
            "session_id": self.session_id,
            "profile": self.profile,
            "user_email": self.user_email,
            "port": self.port,
            "status": self.status,
            "incognito": self.incognito,
            "user_data_dir": str(self.user_data_dir),
            "created_at": self.created_at.isoformat(),
        }
        if self.closed_at is not None:
            result["closed_at"] = self.closed_at.isoformat()
        if self.evidence_chain_path is not None:
            result["evidence_chain_path"] = str(self.evidence_chain_path)
        result["action_count"] = len(self.actions)
        return result


# ---------------------------------------------------------------------------
# BrowserSessionManager
# ---------------------------------------------------------------------------

class BrowserSessionManager:
    """Manage multiple concurrent browser sessions for multi-account testing.

    Each session gets:
    - Its own CDP port (auto-assigned from 9230-9250 range)
    - Its own user data directory (~/.solace/sessions/{session_id}/)
    - Its own auth token registered with the AuthProxy (if provided)
    - A session manifest written to session.json
    - Evidence chain entries for create/close events

    Usage:
        manager = BrowserSessionManager()
        session = manager.create_session(
            session_id="test-gmail",
            profile="phuc-gmail",
        )
        # ... run browser automation ...
        result = manager.close_session("test-gmail")
    """

    def __init__(
        self,
        solace_home: str | Path | None = None,
        *,
        auth_proxy: Any | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        """Initialize the session manager.

        Args:
            solace_home: Base directory for session data. Defaults to ~/.solace.
            auth_proxy: Optional AuthProxy instance for token registration.
            now_fn: Optional callable returning current UTC datetime (for testing).
        """
        self._solace_home = Path(solace_home or "~/.solace").expanduser().resolve()
        self._sessions_root = self._solace_home / "sessions"
        self._auth_proxy = auth_proxy
        self._now = now_fn or (lambda: datetime.now(timezone.utc))

        # Internal state protected by lock
        self._lock = threading.Lock()
        self._sessions: dict[str, SessionRecord] = {}
        self._allocated_ports: set[int] = set()

        # Temp dirs for incognito sessions (cleaned on close)
        self._temp_dirs: dict[str, str] = {}

    # -----------------------------------------------------------------------
    # Port allocation
    # -----------------------------------------------------------------------

    def _allocate_port(self) -> int:
        """Allocate the next available port from the 9230-9250 range.

        Returns:
            An available port number.

        Raises:
            PortExhaustionError: If all ports in the range are in use.
        """
        for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
            if port not in self._allocated_ports:
                self._allocated_ports.add(port)
                return port
        raise PortExhaustionError(
            f"All ports in range {PORT_RANGE_START}-{PORT_RANGE_END} are in use. "
            f"Close existing sessions before creating new ones. "
            f"Active sessions: {len(self._allocated_ports)}"
        )

    def _release_port(self, port: int) -> None:
        """Release a previously allocated port back to the pool."""
        self._allocated_ports.discard(port)

    # -----------------------------------------------------------------------
    # Profile resolution
    # -----------------------------------------------------------------------

    def _resolve_profile(
        self,
        profile: str,
        user_email: str | None,
        incognito: bool,
    ) -> tuple[str, list[str]]:
        """Resolve profile to (email, scopes).

        Args:
            profile: Profile name (must be in PRECONFIGURED_PROFILES or incognito).
            user_email: Override email (takes precedence over profile default).
            incognito: If True, forces incognito profile behavior.

        Returns:
            Tuple of (resolved_email, scopes).

        Raises:
            InvalidProfileError: If profile is not recognized.
        """
        if incognito:
            profile = "incognito"

        if profile not in PRECONFIGURED_PROFILES:
            raise InvalidProfileError(
                f"Unknown profile: {profile!r}. "
                f"Available profiles: {sorted(PRECONFIGURED_PROFILES.keys())}"
            )

        default_email, scopes = PRECONFIGURED_PROFILES[profile]
        resolved_email = user_email if user_email is not None else default_email
        return resolved_email, list(scopes)

    # -----------------------------------------------------------------------
    # Session CRUD
    # -----------------------------------------------------------------------

    def create_session(
        self,
        session_id: str,
        profile: str,
        user_email: str | None = None,
        incognito: bool = False,
    ) -> dict[str, Any]:
        """Create a new browser session with isolated profile.

        Args:
            session_id: Unique identifier for this session.
            profile: Profile name (e.g., "phuc-gmail", "incognito").
            user_email: Optional email override.
            incognito: If True, uses a temporary directory cleaned up on close.

        Returns:
            Dict with session_id, profile, port, status, created_at, user_email.

        Raises:
            DuplicateSessionError: If session_id already exists.
            InvalidProfileError: If profile is not recognized.
            PortExhaustionError: If all ports are in use.
        """
        resolved_email, scopes = self._resolve_profile(profile, user_email, incognito)

        with self._lock:
            if session_id in self._sessions:
                raise DuplicateSessionError(
                    f"Session {session_id!r} already exists. "
                    f"Close it first or use a different session_id."
                )

            port = self._allocate_port()
            now = self._now()

            # Determine user data directory
            if incognito or profile == "incognito":
                temp_dir = tempfile.mkdtemp(prefix=f"solace-incognito-{session_id}-")
                user_data_dir = Path(temp_dir)
                self._temp_dirs[session_id] = temp_dir
                is_incognito = True
            else:
                user_data_dir = self._sessions_root / session_id
                user_data_dir.mkdir(parents=True, exist_ok=True)
                is_incognito = False

            # Create evidence chain
            evidence_path = (
                user_data_dir / "evidence_chain.jsonl"
                if not is_incognito
                else Path(self._temp_dirs[session_id]) / "evidence_chain.jsonl"
            )
            evidence_chain = _SessionEvidenceChain(evidence_path, now_fn=self._now)

            # Build session record
            record = SessionRecord(
                session_id=session_id,
                profile=profile if not incognito else "incognito",
                user_email=resolved_email,
                port=port,
                status=SESSION_STATUS_ACTIVE,
                incognito=is_incognito,
                user_data_dir=user_data_dir,
                created_at=now,
                evidence_chain_path=evidence_path,
            )

            # Register auth token with proxy if available
            if self._auth_proxy is not None:
                token = f"sw_sk_session_{session_id}_{secrets.token_hex(16)}"
                try:
                    from auth_proxy import TokenInfo
                    token_info = TokenInfo(
                        user_id=resolved_email or f"incognito-{session_id}",
                        scopes=scopes,
                        expires_at=datetime.fromtimestamp(
                            now.timestamp() + 86400,  # 24h TTL
                            tz=timezone.utc,
                        ),
                    )
                    self._auth_proxy.register_token(token, token_info)
                    record.auth_token = token
                except (ImportError, ValueError) as exc:
                    # Release port and raise — no fallback
                    self._release_port(port)
                    raise SessionError(
                        f"Failed to register auth token for session {session_id!r}: {exc}"
                    ) from exc

            self._sessions[session_id] = record

        # Log evidence (outside lock to avoid holding it during I/O)
        evidence_chain.append("session_created", {
            "session_id": session_id,
            "profile": record.profile,
            "user_email": resolved_email,
            "port": port,
            "incognito": is_incognito,
        })

        # Write session manifest
        self._write_manifest(record)

        logger.info(
            "Session created: %s (profile=%s, port=%d, incognito=%s)",
            session_id, record.profile, port, is_incognito,
        )

        return record.to_dict()

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions.

        Returns:
            List of session dicts, sorted by created_at.
        """
        with self._lock:
            sessions = [
                record.to_dict()
                for record in self._sessions.values()
                if record.status == SESSION_STATUS_ACTIVE
            ]
        sessions.sort(key=lambda s: s["created_at"])
        return sessions

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session details by ID.

        Args:
            session_id: The session to look up.

        Returns:
            Session dict if found, None if not found.
        """
        with self._lock:
            record = self._sessions.get(session_id)
        if record is None:
            return None
        return record.to_dict()

    def close_session(self, session_id: str) -> dict[str, Any]:
        """Close a session, seal evidence, clean up resources.

        Args:
            session_id: The session to close.

        Returns:
            Final session dict with closed_at timestamp and status=closed.

        Raises:
            SessionNotFoundError: If session_id does not exist.
        """
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                raise SessionNotFoundError(
                    f"Session {session_id!r} not found. "
                    f"Active sessions: {sorted(self._sessions.keys())}"
                )

            if record.status == SESSION_STATUS_CLOSED:
                return record.to_dict()

            now = self._now()
            record.status = SESSION_STATUS_CLOSED
            record.closed_at = now
            self._release_port(record.port)

        # Log evidence for closure
        if record.evidence_chain_path is not None:
            evidence_chain = _SessionEvidenceChain(
                record.evidence_chain_path, now_fn=self._now,
            )
            # Read existing chain to get correct prev_hash and index
            if record.evidence_chain_path.exists():
                lines = record.evidence_chain_path.read_text(encoding="utf-8").strip().splitlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    evidence_chain._prev_hash = last_entry.get("entry_hash", GENESIS_HASH)
                    evidence_chain._index = last_entry.get("entry_id", 0) + 1
            evidence_chain.append("session_closed", {
                "session_id": session_id,
                "duration_seconds": (now - record.created_at).total_seconds(),
                "action_count": len(record.actions),
            })

        # Update manifest
        self._write_manifest(record)

        # Clean up incognito temp dir
        temp_dir = self._temp_dirs.pop(session_id, None)
        if temp_dir is not None and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
            except OSError as exc:
                logger.warning(
                    "Failed to remove incognito temp dir %s for session %s: %s",
                    temp_dir, session_id, exc,
                )

        # Revoke auth token if proxy is available
        if self._auth_proxy is not None and record.auth_token is not None:
            try:
                from auth_proxy import hash_token
                token_hash = hash_token(record.auth_token)
                self._auth_proxy.revoke_token(token_hash)
            except ImportError:
                logger.warning(
                    "auth_proxy module not available — token for session %s "
                    "could not be revoked (token=%s...)",
                    session_id, record.auth_token[:20],
                )
                # Record the unrevoked token in the session close evidence
                if record.evidence_chain_path is not None and record.evidence_chain_path.exists():
                    unrevoked_chain = _SessionEvidenceChain(
                        record.evidence_chain_path, now_fn=self._now,
                    )
                    lines = record.evidence_chain_path.read_text(encoding="utf-8").strip().splitlines()
                    if lines:
                        last_entry = json.loads(lines[-1])
                        unrevoked_chain._prev_hash = last_entry.get("entry_hash", GENESIS_HASH)
                        unrevoked_chain._index = last_entry.get("entry_id", 0) + 1
                    unrevoked_chain.append("token_revocation_failed", {
                        "session_id": session_id,
                        "reason": "auth_proxy module not available",
                    })

        logger.info("Session closed: %s (duration=%.1fs)", session_id,
                     (now - record.created_at).total_seconds())

        return record.to_dict()

    def close_all(self) -> list[dict[str, Any]]:
        """Close all active sessions.

        Returns:
            List of closed session dicts.
        """
        with self._lock:
            active_ids = [
                sid for sid, rec in self._sessions.items()
                if rec.status == SESSION_STATUS_ACTIVE
            ]

        results = []
        for session_id in active_ids:
            result = self.close_session(session_id)
            results.append(result)
        return results

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------

    @property
    def active_session_count(self) -> int:
        """Number of currently active sessions."""
        with self._lock:
            return sum(
                1 for rec in self._sessions.values()
                if rec.status == SESSION_STATUS_ACTIVE
            )

    @property
    def allocated_ports(self) -> set[int]:
        """Set of currently allocated ports (copy for thread safety)."""
        with self._lock:
            return set(self._allocated_ports)

    @property
    def sessions_root(self) -> Path:
        """Base directory for session data."""
        return self._sessions_root

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _write_manifest(self, record: SessionRecord) -> None:
        """Write session manifest to session.json inside the session directory.

        For incognito sessions whose temp dir has been cleaned up, this is a no-op.
        """
        if not record.user_data_dir.exists():
            return

        manifest_path = record.user_data_dir / "session.json"
        manifest_data = record.to_dict()
        manifest_data["actions"] = record.actions
        manifest_path.write_text(
            json.dumps(manifest_data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
