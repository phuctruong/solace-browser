#!/usr/bin/env python3
"""
Solace Browser Per-Tab State Machine (A1)

Implements deterministic per-tab state management with atomic transitions,
command validation, and audit logging. This is the source of truth for all
tab state across the Solace browser control system.

Architecture:
  - TabState: dataclass for per-tab state
  - TabStateManager: thread-safe state manager with locking
  - VALID_TRANSITIONS: state transition matrix
  - COMMAND_STATE_MAP: command-to-state validation mapping
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, FrozenSet
from datetime import datetime
import threading
import json

# Valid states for browser tabs
VALID_STATES: FrozenSet[str] = frozenset({
    "IDLE", "CONNECTED", "NAVIGATING", "CLICKING",
    "TYPING", "RECORDING", "ERROR"
})

# Transition matrix: from_state -> list of valid target states
VALID_TRANSITIONS: Dict[str, List[str]] = {
    "IDLE":       ["CONNECTED"],
    "CONNECTED":  ["NAVIGATING", "CLICKING", "TYPING", "RECORDING", "ERROR"],
    "NAVIGATING": ["CONNECTED", "ERROR"],
    "CLICKING":   ["CONNECTED", "ERROR"],
    "TYPING":     ["CONNECTED", "ERROR"],
    "RECORDING":  ["RECORDING", "CONNECTED", "ERROR"],
    "ERROR":      ["IDLE"],
}

# Maps command types to allowed source states and in-progress target state
# For read-only commands (snapshot, extract_page), target is None (no state change)
COMMAND_STATE_MAP: Dict[str, Dict] = {
    "NAVIGATE":        {"required": {"CONNECTED"},            "target": "NAVIGATING"},
    "CLICK":           {"required": {"CONNECTED"},            "target": "CLICKING"},
    "TYPE":            {"required": {"CONNECTED"},            "target": "TYPING"},
    "START_RECORDING": {"required": {"CONNECTED"},            "target": "RECORDING"},
    "STOP_RECORDING":  {"required": {"RECORDING"},            "target": "CONNECTED"},
    "SNAPSHOT":        {"required": {"CONNECTED", "RECORDING"}, "target": None},
    "EXTRACT_PAGE":    {"required": {"CONNECTED", "RECORDING"}, "target": None},
    "EXECUTE_SCRIPT":  {"required": {"CONNECTED"},            "target": None},
    "PING":            {"required": None,                     "target": None},
}


@dataclass
class AuditEntry:
    """Log entry for a state transition."""
    tab_id: int
    from_state: str
    to_state: str
    reason: str
    timestamp: str


@dataclass
class TabState:
    """Per-tab state representation."""
    tab_id: int
    state: str = "IDLE"
    current_action: Optional[Dict] = None
    recording_session: Optional[str] = None
    last_error: Optional[str] = None
    timestamp: str = ""
    metadata: Dict = field(default_factory=dict)


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""
    def __init__(self, from_state: str, to_state: str, reason: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        msg = f"Invalid transition: {from_state} -> {to_state}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class InvalidCommandError(Exception):
    """Raised when a command is not allowed in the current state."""
    def __init__(self, command: str, current_state: str):
        self.command = command
        self.current_state = current_state
        super().__init__(
            f"Command '{command}' not allowed in state '{current_state}'"
        )


class TabStateManager:
    """
    Thread-safe per-tab state manager.

    Maintains per-tab state with atomic transitions, command validation,
    and audit logging. Uses threading.Lock for atomicity across async/sync
    code paths.
    """

    def __init__(self):
        self._tabs: Dict[int, TabState] = {}
        self._audit_log: Dict[int, List[AuditEntry]] = {}
        self._lock = threading.Lock()

    def create_tab(self, tab_id: int) -> TabState:
        """
        Create new tab state (IDLE -> CONNECTED).

        Called when extension attaches to a tab.
        Raises InvalidTransitionError if tab already exists.

        Args:
            tab_id: Chrome tab ID

        Returns:
            TabState: newly created tab state in CONNECTED state

        Raises:
            InvalidTransitionError: if tab already exists
        """
        with self._lock:
            if tab_id in self._tabs:
                raise InvalidTransitionError(
                    "CONNECTED", "CONNECTED",
                    f"tab {tab_id} already attached"
                )
            tab = TabState(
                tab_id=tab_id,
                state="CONNECTED",
                timestamp=datetime.utcnow().isoformat(),
            )
            self._tabs[tab_id] = tab
            self._append_audit(tab_id, "IDLE", "CONNECTED", "extension attached")
            return tab

    def get_tab(self, tab_id: int) -> Optional[TabState]:
        """
        Query current state for a tab.

        Args:
            tab_id: Chrome tab ID

        Returns:
            TabState if tab exists, None otherwise
        """
        with self._lock:
            return self._tabs.get(tab_id)

    def get_all_tabs(self) -> Dict[int, TabState]:
        """
        Snapshot of all tab states.

        Returns:
            Dict[tab_id, TabState] of all tracked tabs
        """
        with self._lock:
            return dict(self._tabs)

    def transition(
        self, tab_id: int, new_state: str, reason: str = ""
    ) -> TabState:
        """
        Atomic validated transition.

        Validates the transition is allowed, updates state, and logs to audit.
        Clears current_action for terminal/connection states.

        Args:
            tab_id: Chrome tab ID
            new_state: target state string
            reason: explanation for transition (logged in audit)

        Returns:
            TabState: updated tab state

        Raises:
            InvalidTransitionError: if transition is not allowed
        """
        with self._lock:
            tab = self._tabs.get(tab_id)
            if tab is None:
                raise InvalidTransitionError(
                    "NO_TAB", new_state, f"tab {tab_id} not found"
                )

            allowed = VALID_TRANSITIONS.get(tab.state, [])
            if new_state not in allowed:
                raise InvalidTransitionError(tab.state, new_state, reason)

            old_state = tab.state
            tab.state = new_state
            tab.timestamp = datetime.utcnow().isoformat()

            # Clear current_action for terminal/connection states
            if new_state in ("CONNECTED", "ERROR", "IDLE"):
                tab.current_action = None

            # Store error message in ERROR state
            if new_state == "ERROR":
                tab.last_error = reason

            self._append_audit(tab_id, old_state, new_state, reason)
            return tab

    def validate_command(self, tab_id: int, command_type: str) -> None:
        """
        Check if command is allowed in current tab state.

        Uses COMMAND_STATE_MAP to validate command preconditions.
        Raises InvalidCommandError if command is not allowed.

        Args:
            tab_id: Chrome tab ID
            command_type: command type string (e.g., "NAVIGATE", "CLICK")

        Raises:
            InvalidCommandError: if command not allowed in current state
        """
        mapping = COMMAND_STATE_MAP.get(command_type)
        if mapping is None:
            return  # unknown commands pass through

        required = mapping["required"]
        if required is None:
            return  # always allowed (e.g., PING)

        with self._lock:
            tab = self._tabs.get(tab_id)
            if tab is None:
                raise InvalidCommandError(command_type, "NO_TAB")
            if tab.state not in required:
                raise InvalidCommandError(command_type, tab.state)

    def remove_tab(self, tab_id: int) -> Optional[TabState]:
        """
        Remove tab state on tab close.

        Cleans up all tracking for a closed tab and logs the closure
        to the audit trail.

        Args:
            tab_id: Chrome tab ID

        Returns:
            TabState: removed tab state or None if not found
        """
        with self._lock:
            tab = self._tabs.pop(tab_id, None)
            if tab:
                self._append_audit(tab_id, tab.state, "CLOSED", "tab closed")
            return tab

    def get_audit_log(self, tab_id: int) -> List[AuditEntry]:
        """
        Return audit trail for a tab.

        Args:
            tab_id: Chrome tab ID

        Returns:
            List[AuditEntry]: transition history for the tab
        """
        with self._lock:
            return list(self._audit_log.get(tab_id, []))

    def reset(self) -> None:
        """
        Clear all state.

        Used for testing only. Wipes all tabs and audit logs.
        """
        with self._lock:
            self._tabs.clear()
            self._audit_log.clear()

    def _append_audit(
        self,
        tab_id: int,
        from_state: str,
        to_state: str,
        reason: str
    ) -> None:
        """Internal: append to audit log."""
        if tab_id not in self._audit_log:
            self._audit_log[tab_id] = []
        self._audit_log[tab_id].append(AuditEntry(
            tab_id=tab_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            timestamp=datetime.utcnow().isoformat(),
        ))

    def audit_log_to_dict(self, tab_id: int) -> List[Dict]:
        """Convert audit log to JSON-serializable dicts."""
        return [
            {
                "tab_id": entry.tab_id,
                "from_state": entry.from_state,
                "to_state": entry.to_state,
                "reason": entry.reason,
                "timestamp": entry.timestamp,
            }
            for entry in self.get_audit_log(tab_id)
        ]
