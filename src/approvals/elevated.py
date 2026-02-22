"""
approvals/elevated.py — OAuth3 Elevated Mode (Time-Bounded Privilege Escalation)

Provides short-lived, scope-constrained elevated privilege sessions for
agents or users that have passed step-up authentication.

Design constraints:
  - All timestamps ISO8601 UTC (no naive datetimes)
  - All durations int seconds
  - Scope constraint: elevated scopes must be a strict subset of the caller's
    granted OAuth3 scopes — cannot self-grant new permissions.
  - No nesting: cannot enter elevated mode while already elevated.
  - Auto-exit: session terminates when duration OR max_actions is exceeded.
  - Evidence on exit: full action log with timestamps is preserved.
  - Fail-closed: any ambiguity → deny.

Rung: 274177
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ELEVATED_DURATION_SECONDS: int = 3600   # 1 hour hard cap
MAX_ELEVATED_ACTIONS: int = 1000            # Hard cap on actions per session
DEFAULT_ELEVATED_DURATION_SECONDS: int = 300  # 5 minutes default


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ElevatedModeError(Exception):
    """Raised when elevated mode constraints are violated."""
    pass


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ElevatedSession:
    """
    An active elevated-privilege session.

    Fields:
        session_id:          UUID4 globally unique session identifier.
        user_id:             Identifier of the principal who entered elevated mode.
        granted_scopes:      OAuth3 scopes active in this elevated session.
        started_at:          ISO8601 UTC timestamp of session start.
        expires_at:          ISO8601 UTC timestamp of session expiry.
        max_duration_seconds: Maximum session lifetime in seconds.
        actions_performed:   Count of actions taken in this session so far.
        max_actions:         Maximum number of actions allowed in this session.
    """
    session_id:           str
    user_id:              str
    granted_scopes:       List[str]
    started_at:           str   # ISO8601 UTC
    expires_at:           str   # ISO8601 UTC
    max_duration_seconds: int
    actions_performed:    int
    max_actions:          int

    def is_time_expired(self) -> bool:
        """Return True if the session has exceeded its time limit."""
        now = datetime.now(timezone.utc)
        expires = _parse_iso8601(self.expires_at)
        return now > expires

    def is_action_limit_exceeded(self) -> bool:
        """Return True if the session has reached its action limit."""
        return self.actions_performed >= self.max_actions

    def is_active(self) -> bool:
        """Return True if the session is still valid (time and actions within limits)."""
        return not self.is_time_expired() and not self.is_action_limit_exceeded()

    def remaining_seconds(self) -> int:
        """
        Return seconds remaining in the session (0 if expired).

        Returns:
            Non-negative integer count of remaining seconds.
        """
        now = datetime.now(timezone.utc)
        expires = _parse_iso8601(self.expires_at)
        delta = (expires - now).total_seconds()
        return max(0, int(delta))

    def remaining_actions(self) -> int:
        """
        Return actions remaining before the limit is reached (0 if exhausted).

        Returns:
            Non-negative integer count of remaining actions.
        """
        return max(0, self.max_actions - self.actions_performed)

    def to_dict(self) -> dict:
        """Convert to plain dict (JSON-serializable)."""
        return {
            "session_id":           self.session_id,
            "user_id":              self.user_id,
            "granted_scopes":       self.granted_scopes,
            "started_at":           self.started_at,
            "expires_at":           self.expires_at,
            "max_duration_seconds": self.max_duration_seconds,
            "actions_performed":    self.actions_performed,
            "max_actions":          self.max_actions,
        }


# ---------------------------------------------------------------------------
# Internal session state
# ---------------------------------------------------------------------------

@dataclass
class _SessionState:
    """Internal mutable state for a session."""
    session: ElevatedSession
    active: bool = True
    # Timestamped action log: list of {"action": str, "timestamp": ISO8601, "scope": str}
    action_log: List[dict] = field(default_factory=list)
    # Exit evidence (populated on session end)
    exit_evidence: Optional[dict] = None


# ---------------------------------------------------------------------------
# ElevatedMode
# ---------------------------------------------------------------------------

class ElevatedMode:
    """
    OAuth3-governed elevated privilege session manager.

    Allows agents or users who have completed step-up authentication to
    operate under time-bounded, scope-constrained elevated privileges.

    Usage::

        mode = ElevatedMode()

        # Simulate OAuth3 token granting these scopes to the user:
        user_base_scopes = ["linkedin.delete.post", "gmail.send.email"]

        session = mode.enter(
            user_id="alice@example.com",
            scopes=["linkedin.delete.post"],   # must be subset of base_scopes
            duration_seconds=120,
            max_actions=5,
            user_granted_scopes=user_base_scopes,
        )

        status = mode.check(session.session_id)
        # {"active": True, "remaining_seconds": 119, "remaining_actions": 5}

        mode.record_action(session.session_id, action="delete_post", scope="linkedin.delete.post")

        mode.exit(session.session_id)
    """

    def __init__(self, *, system_id: str = "elevated-mode") -> None:
        """
        Initialise the elevated mode manager.

        Args:
            system_id: Identifier used for system-generated audit entries.
        """
        self._system_id: str = system_id
        # {session_id: _SessionState}
        self._sessions: Dict[str, _SessionState] = {}
        # {user_id: session_id}  — tracks which users are currently elevated
        self._active_user_sessions: Dict[str, str] = {}
        # Ordered audit log with SHA256 hashes
        self._audit_log: List[dict] = []

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def enter(
        self,
        user_id: str,
        scopes: List[str],
        duration_seconds: int,
        max_actions: int,
        *,
        user_granted_scopes: Optional[List[str]] = None,
        require_step_up: bool = True,
        step_up_verified: bool = False,
    ) -> ElevatedSession:
        """
        Enter elevated mode for a user.

        Requires step-up authentication (caller must pass step_up_verified=True
        to signal that step-up has been completed). Validates:
          - No active elevated session for this user (no nesting).
          - Requested scopes are a subset of user's granted OAuth3 scopes.
          - Duration does not exceed MAX_ELEVATED_DURATION_SECONDS.
          - max_actions does not exceed MAX_ELEVATED_ACTIONS.

        Args:
            user_id:              Identifier of the principal.
            scopes:               OAuth3 scopes to activate in elevated session.
            duration_seconds:     Session lifetime in seconds.
            max_actions:          Maximum number of actions allowed.
            user_granted_scopes:  The OAuth3 scopes granted to this user. Required
                                  when require_step_up=True or scopes are provided.
                                  If None, scope checking is skipped (testing only).
            require_step_up:      If True (default), step_up_verified must be True.
            step_up_verified:     Set True to signal step-up auth has been completed.

        Returns:
            ElevatedSession (registered in internal state).

        Raises:
            ElevatedModeError: If any constraint is violated.
            ValueError:        If duration or max_actions exceed hard limits.
        """
        # Step-up gate (fail-closed)
        if require_step_up and not step_up_verified:
            raise ElevatedModeError(
                "Step-up authentication required to enter elevated mode. "
                "Pass step_up_verified=True after completing step-up flow."
            )

        # No nesting: check if user already has an active session
        if user_id in self._active_user_sessions:
            existing_sid = self._active_user_sessions[user_id]
            existing_state = self._sessions.get(existing_sid)
            if existing_state and existing_state.active:
                existing_session = existing_state.session
                # Allow entry if existing session has expired or hit action limit
                if existing_session.is_active():
                    raise ElevatedModeError(
                        f"User '{user_id}' is already in elevated mode "
                        f"(session {existing_sid}). "
                        "Exit the current session before entering a new one."
                    )
                else:
                    # Auto-expire the old stale session
                    self._auto_exit(existing_sid)

        # Duration cap
        if duration_seconds > MAX_ELEVATED_DURATION_SECONDS:
            raise ValueError(
                f"duration_seconds {duration_seconds} exceeds maximum "
                f"{MAX_ELEVATED_DURATION_SECONDS}."
            )
        if duration_seconds <= 0:
            raise ValueError(f"duration_seconds must be positive, got {duration_seconds}.")

        # Actions cap
        if max_actions > MAX_ELEVATED_ACTIONS:
            raise ValueError(
                f"max_actions {max_actions} exceeds maximum {MAX_ELEVATED_ACTIONS}."
            )
        if max_actions <= 0:
            raise ValueError(f"max_actions must be positive, got {max_actions}.")

        # Scope constraint: elevated scopes must be subset of user's granted scopes
        if user_granted_scopes is not None:
            granted_set = set(user_granted_scopes)
            requested_set = set(scopes)
            unauthorized = requested_set - granted_set
            if unauthorized:
                raise ElevatedModeError(
                    f"Elevated scopes {sorted(unauthorized)} are not in user's "
                    f"granted OAuth3 scopes. Cannot self-grant permissions."
                )

        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=duration_seconds)
        session_id = str(uuid.uuid4())

        session = ElevatedSession(
            session_id=session_id,
            user_id=user_id,
            granted_scopes=list(scopes),
            started_at=now.isoformat(),
            expires_at=expires.isoformat(),
            max_duration_seconds=duration_seconds,
            actions_performed=0,
            max_actions=max_actions,
        )

        self._sessions[session_id] = _SessionState(session=session)
        self._active_user_sessions[user_id] = session_id
        self._append_audit(
            event="elevated_session_started",
            data={
                "session_id":           session_id,
                "user_id":              user_id,
                "granted_scopes":       list(scopes),
                "duration_seconds":     duration_seconds,
                "max_actions":          max_actions,
                "started_at":           now.isoformat(),
                "expires_at":           expires.isoformat(),
                "step_up_verified":     step_up_verified,
            },
        )

        return session

    def check(self, session_id: str) -> dict:
        """
        Check the status of an elevated session.

        Auto-exits sessions that have timed out or exhausted their action limit.

        Args:
            session_id: UUID of the session to check.

        Returns:
            Dict with keys:
                "active"            — bool
                "remaining_seconds" — int (0 if expired or inactive)
                "remaining_actions" — int (0 if exhausted or inactive)

        Raises:
            KeyError: If session_id is not found.
        """
        state = self._get_state(session_id)

        # Check if session should be auto-exited
        if state.active:
            session = state.session
            if not session.is_active():
                self._auto_exit(session_id)
                state = self._sessions[session_id]  # re-fetch after exit

        if not state.active:
            return {
                "active":            False,
                "remaining_seconds": 0,
                "remaining_actions": 0,
            }

        session = state.session
        return {
            "active":            True,
            "remaining_seconds": session.remaining_seconds(),
            "remaining_actions": session.remaining_actions(),
        }

    def exit(self, session_id: str) -> dict:
        """
        End an elevated session early, logging evidence.

        Safe to call on already-exited sessions (idempotent).

        Args:
            session_id: UUID of the session to exit.

        Returns:
            Evidence dict containing:
                "session_id"       — str
                "user_id"          — str
                "started_at"       — ISO8601 UTC
                "exited_at"        — ISO8601 UTC
                "actions_performed"— int
                "action_log"       — list of action records
                "exit_reason"      — str

        Raises:
            KeyError: If session_id is not found.
        """
        state = self._get_state(session_id)
        if not state.active:
            # Already exited: return existing evidence
            return state.exit_evidence or {}

        return self._do_exit(session_id, reason="user_requested")

    def record_action(
        self,
        session_id: str,
        action: str,
        scope: str = "",
        *,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Record an action performed under elevated mode.

        Increments the action counter. Auto-exits if the action limit is reached.

        Args:
            session_id: UUID of the elevated session.
            action:     Short name of the action performed.
            scope:      OAuth3 scope exercised (optional).
            metadata:   Additional context dict (optional).

        Raises:
            KeyError:          If session_id is not found.
            ElevatedModeError: If the session is not active.
        """
        state = self._get_state(session_id)

        if not state.active:
            raise ElevatedModeError(
                f"Session {session_id} is not active. Cannot record action."
            )

        session = state.session
        if not session.is_active():
            self._auto_exit(session_id)
            raise ElevatedModeError(
                f"Session {session_id} expired or exhausted before action '{action}' "
                "could be recorded. Session has been auto-exited."
            )

        now = datetime.now(timezone.utc).isoformat()
        action_record = {
            "action":    action,
            "scope":     scope,
            "timestamp": now,
            "metadata":  metadata or {},
        }
        state.action_log.append(action_record)

        # Increment counter on the session object (replace immutable-friendly)
        state.session = ElevatedSession(
            session_id=session.session_id,
            user_id=session.user_id,
            granted_scopes=session.granted_scopes,
            started_at=session.started_at,
            expires_at=session.expires_at,
            max_duration_seconds=session.max_duration_seconds,
            actions_performed=session.actions_performed + 1,
            max_actions=session.max_actions,
        )

        self._append_audit(
            event="elevated_action_recorded",
            data={
                "session_id": session_id,
                "action":     action,
                "scope":      scope,
                "timestamp":  now,
            },
        )

        # Auto-exit if action limit just reached
        if state.session.is_action_limit_exceeded():
            self._auto_exit(session_id)

    def get_audit_log(self) -> List[dict]:
        """
        Return a copy of the full audit log.

        Each entry has: event, timestamp, data, entry_hash (SHA256).

        Returns:
            List of audit entries (ordered by insertion time).
        """
        return list(self._audit_log)

    def is_user_elevated(self, user_id: str) -> bool:
        """
        Return True if the user currently has an active elevated session.

        Args:
            user_id: Identifier of the user to check.

        Returns:
            True if the user is in an active elevated session.
        """
        session_id = self._active_user_sessions.get(user_id)
        if session_id is None:
            return False
        state = self._sessions.get(session_id)
        if state is None:
            return False
        if not state.active:
            return False
        # Check if session has auto-expired
        if not state.session.is_active():
            self._auto_exit(session_id)
            return False
        return True

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _get_state(self, session_id: str) -> _SessionState:
        """Retrieve state or raise KeyError with a clear message."""
        try:
            return self._sessions[session_id]
        except KeyError:
            raise KeyError(f"Elevated session not found: {session_id}")

    def _auto_exit(self, session_id: str) -> None:
        """Auto-exit a session that has expired or hit its action limit."""
        state = self._sessions.get(session_id)
        if state is None or not state.active:
            return

        session = state.session
        if session.is_time_expired():
            reason = "auto_exit:time_expired"
        elif session.is_action_limit_exceeded():
            reason = "auto_exit:action_limit_reached"
        else:
            reason = "auto_exit:unknown"

        self._do_exit(session_id, reason=reason)

    def _do_exit(self, session_id: str, reason: str) -> dict:
        """
        Perform session exit and record evidence.

        Returns the evidence dict.
        """
        state = self._sessions[session_id]
        session = state.session
        now = datetime.now(timezone.utc).isoformat()

        evidence = {
            "session_id":        session_id,
            "user_id":           session.user_id,
            "started_at":        session.started_at,
            "exited_at":         now,
            "actions_performed": session.actions_performed,
            "action_log":        list(state.action_log),
            "exit_reason":       reason,
        }

        state.active = False
        state.exit_evidence = evidence

        # Remove from active user index
        self._active_user_sessions.pop(session.user_id, None)

        self._append_audit(
            event="elevated_session_exited",
            data={
                "session_id":        session_id,
                "user_id":           session.user_id,
                "exited_at":         now,
                "actions_performed": session.actions_performed,
                "exit_reason":       reason,
            },
        )

        return evidence

    def _append_audit(self, event: str, data: dict) -> None:
        """
        Append a hashed entry to the audit log.

        Hash = SHA256(event + ":" + timestamp + ":" + canonical_json(data))
        Prefixed "sha256:" for clarity.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        raw = f"{event}:{timestamp}:{canonical}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        entry_hash = f"sha256:{digest}"

        self._audit_log.append({
            "event":      event,
            "timestamp":  timestamp,
            "data":       data,
            "entry_hash": entry_hash,
        })


# ---------------------------------------------------------------------------
# Internal utility
# ---------------------------------------------------------------------------

def _parse_iso8601(dt_str: str) -> datetime:
    """Parse ISO 8601 datetime string to timezone-aware datetime."""
    dt_str = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
