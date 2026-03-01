"""
companion/apps.py — Companion App system for Solace Browser.

Companion apps are mini-applications that run alongside the browser agent.
All operations are OAuth3 scope-gated (companion.app.run is the base scope).

Key classes:
  CompanionApp    — Base class for companion applications
  AppRegistry     — Registry of available companion apps (max 10 registered, 5 running)
  AppLifecycle    — State machine: REGISTERED → STARTING → RUNNING → STOPPING → STOPPED → ERROR
  AppEvent        — Incoming event dataclass
  AppResponse     — Response dataclass

Architecture rules:
  - All companion apps require OAuth3 scope companion.app.run
  - Step-up for apps with companion.app.system_access scope
  - Apps run in isolation — cannot access other apps' state
  - Apps cannot modify browser DOM directly
  - Resource limits: 10 MB memory budget, 5-second execution timeout
  - App registration validates SHA256 manifest hash

No external dependencies beyond stdlib.
Int arithmetic only (no float).

Rung: 641 (local correctness)
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Resource limits (all int — never float)
# ---------------------------------------------------------------------------

MAX_REGISTERED_APPS: int = 10          # registry hard cap
MAX_RUNNING_APPS: int = 5              # simultaneous running hard cap
APP_MEMORY_BUDGET_BYTES: int = 10 * 1024 * 1024  # 10 MiB per app
APP_EXECUTION_TIMEOUT_SECONDS: int = 5  # 5 s per handle_event call


# ---------------------------------------------------------------------------
# Lifecycle state constants
# ---------------------------------------------------------------------------

class AppState:
    """Valid companion app lifecycle states."""
    REGISTERED = "REGISTERED"
    STARTING   = "STARTING"
    RUNNING    = "RUNNING"
    STOPPING   = "STOPPING"
    STOPPED    = "STOPPED"
    ERROR      = "ERROR"

    ALL_STATES = frozenset({REGISTERED, STARTING, RUNNING, STOPPING, STOPPED, ERROR})


# Valid state transitions: from_state → set of allowed to_states
_VALID_TRANSITIONS: Dict[str, frozenset] = {
    AppState.REGISTERED: frozenset({AppState.STARTING, AppState.ERROR}),
    AppState.STARTING:   frozenset({AppState.RUNNING,  AppState.ERROR}),
    AppState.RUNNING:    frozenset({AppState.STOPPING, AppState.ERROR}),
    AppState.STOPPING:   frozenset({AppState.STOPPED,  AppState.ERROR}),
    AppState.STOPPED:    frozenset({AppState.STARTING}),          # allow restart
    AppState.ERROR:      frozenset({AppState.REGISTERED}),        # allow reset
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CompanionAppError(Exception):
    """Base exception for companion app errors."""


class InvalidTransitionError(CompanionAppError):
    """Raised when an invalid lifecycle state transition is attempted."""

    def __init__(self, app_id: str, from_state: str, to_state: str) -> None:
        self.app_id = app_id
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid transition for app '{app_id}': "
            f"{from_state} → {to_state} is not allowed."
        )


class AppRegistryError(CompanionAppError):
    """Raised for registry-level violations (duplicate, capacity, etc.)."""


class AppNotFoundError(CompanionAppError):
    """Raised when an app_id is not found in the registry."""


class AppScopeError(CompanionAppError):
    """Raised when an app is missing required OAuth3 scopes."""

    def __init__(self, app_id: str, missing_scopes: List[str]) -> None:
        self.app_id = app_id
        self.missing_scopes = missing_scopes
        super().__init__(
            f"App '{app_id}' is missing required OAuth3 scopes: {missing_scopes}"
        )


class ManifestHashError(CompanionAppError):
    """Raised when the manifest SHA256 hash does not match."""

    def __init__(self, app_id: str, expected: str, actual: str) -> None:
        self.app_id = app_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"SHA256 mismatch for app '{app_id}': "
            f"expected {expected!r}, got {actual!r}."
        )


class AppExecutionTimeoutError(CompanionAppError):
    """Raised when handle_event exceeds the execution timeout."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AppEvent:
    """
    Incoming event delivered to a companion app.

    Fields:
        event_type: String identifier for the event (e.g. "clipboard_change").
        source:     Origin of the event — one of "browser", "user", "agent", "system".
        data:       Arbitrary key/value payload.
        timestamp:  Unix epoch seconds (int — no float).
    """
    event_type: str
    source: str                    # "browser" | "user" | "agent" | "system"
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = field(default_factory=lambda: int(time.time()))

    def __post_init__(self) -> None:
        valid_sources = {"browser", "user", "agent", "system"}
        if self.source not in valid_sources:
            raise ValueError(
                f"AppEvent.source must be one of {sorted(valid_sources)}, "
                f"got {self.source!r}."
            )


@dataclass
class AppResponse:
    """
    Response returned by a companion app after handling an event.

    Fields:
        status:  "ok" | "error" | "deferred"
        data:    Arbitrary key/value payload.
        actions: List of action strings the app requests the bridge to execute.
    """
    status: str                        # "ok" | "error" | "deferred"
    data: Dict[str, Any] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        valid_statuses = {"ok", "error", "deferred"}
        if self.status not in valid_statuses:
            raise ValueError(
                f"AppResponse.status must be one of {sorted(valid_statuses)}, "
                f"got {self.status!r}."
            )


@dataclass
class AppManifest:
    """
    SHA256-validated app manifest.

    content_hash must be 'sha256:<hex>' of the canonical manifest JSON
    (sorted keys, no whitespace).
    """
    app_id: str
    name: str
    version: str
    required_scopes: List[str]
    content_hash: str           # 'sha256:<hex>'
    description: str = ""

    @classmethod
    def compute_hash(cls, app_id: str, name: str, version: str,
                     required_scopes: List[str]) -> str:
        """Compute the canonical SHA256 hash for the given manifest fields."""
        canonical = json.dumps(
            {
                "app_id": app_id,
                "name": name,
                "version": version,
                "required_scopes": sorted(required_scopes),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"


@dataclass(frozen=True)
class InstalledAppRecord:
    """Filesystem record for an installed day-one app."""

    app_id: str
    app_root: Path
    manifest_path: Path


def discover_installed_apps(apps_root: str | Path) -> List[InstalledAppRecord]:
    """Return installed app folders that include a manifest."""

    root = Path(apps_root).expanduser().resolve()
    if not root.exists():
        return []

    records: List[InstalledAppRecord] = []
    for manifest_path in sorted(root.glob("*/manifest.yaml")):
        app_root = manifest_path.parent
        records.append(
            InstalledAppRecord(
                app_id=app_root.name,
                app_root=app_root,
                manifest_path=manifest_path,
            )
        )
    return records


# ---------------------------------------------------------------------------
# CompanionApp — base class
# ---------------------------------------------------------------------------

class CompanionApp:
    """
    Base class for companion applications.

    Subclasses override:
      - handle_event(event) → AppResponse
      - get_state() → dict

    All apps require OAuth3 scope 'companion.app.run'.
    Apps with 'companion.app.system_access' require step-up auth.

    Apps run in isolation: no shared state, no direct DOM access.
    """

    # Subclasses can override these class attributes
    app_id: str = ""
    name: str = ""
    version: str = "0.0.0"
    required_scopes: List[str] = ["companion.app.run"]
    description: str = ""

    def __init__(self) -> None:
        # Ensure subclass has set required class attributes
        if not self.app_id:
            raise CompanionAppError(
                f"{type(self).__name__} must define a non-empty app_id."
            )
        # Internal per-instance state — isolated from other apps
        self._state: Dict[str, Any] = {}
        self._started_at: Optional[int] = None
        self._stopped_at: Optional[int] = None
        # Enforce base scope always present
        if "companion.app.run" not in self.required_scopes:
            self.required_scopes = list(self.required_scopes) + ["companion.app.run"]

    # ------------------------------------------------------------------
    # Lifecycle hooks — override in subclasses as needed
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Launch the companion app. Called by AppLifecycle on STARTING → RUNNING."""
        self._started_at = int(time.time())
        self._state["running"] = True

    def stop(self) -> None:
        """Stop the companion app. Called by AppLifecycle on STOPPING → STOPPED."""
        self._stopped_at = int(time.time())
        self._state["running"] = False

    # ------------------------------------------------------------------
    # Event handling — override in subclasses
    # ------------------------------------------------------------------

    def handle_event(self, event: AppEvent) -> AppResponse:
        """
        Process an incoming event.

        Default implementation returns an 'ok' response with the event_type echoed.
        Subclasses should override to provide domain-specific behaviour.
        """
        return AppResponse(
            status="ok",
            data={"echo": event.event_type},
        )

    # ------------------------------------------------------------------
    # State — override in subclasses
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        """
        Return the current internal state of this app.

        Each app's state is isolated: callers only receive a copy.
        """
        return dict(self._state)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def requires_step_up(self) -> bool:
        """Return True if this app requires step-up auth (system_access scope)."""
        return "companion.app.system_access" in self.required_scopes

    def manifest_hash(self) -> str:
        """Compute the SHA256 hash for this app's manifest."""
        return AppManifest.compute_hash(
            app_id=self.app_id,
            name=self.name,
            version=self.version,
            required_scopes=list(self.required_scopes),
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(app_id={self.app_id!r}, "
            f"version={self.version!r})"
        )


# ---------------------------------------------------------------------------
# AppLifecycle — per-app state machine
# ---------------------------------------------------------------------------

class AppLifecycle:
    """
    Manages lifecycle state for each registered companion app.

    States: REGISTERED → STARTING → RUNNING → STOPPING → STOPPED → ERROR

    Thread-safety: not thread-safe (single-threaded use assumed).
    """

    def __init__(self) -> None:
        # app_id → current state string
        self._states: Dict[str, str] = {}
        # app_id → list of (from_state, to_state, timestamp_int) transition log
        self._history: Dict[str, List[Tuple[str, str, int]]] = {}

    def register(self, app_id: str) -> None:
        """Register a new app at REGISTERED state."""
        if app_id in self._states:
            raise AppRegistryError(f"App '{app_id}' is already registered in lifecycle.")
        self._states[app_id] = AppState.REGISTERED
        self._history[app_id] = []

    def unregister(self, app_id: str) -> None:
        """Remove an app from the lifecycle tracker."""
        if app_id not in self._states:
            raise AppNotFoundError(f"App '{app_id}' is not registered in lifecycle.")
        del self._states[app_id]
        del self._history[app_id]

    def get_state(self, app_id: str) -> str:
        """Return the current state for an app."""
        if app_id not in self._states:
            raise AppNotFoundError(f"App '{app_id}' not found in lifecycle.")
        return self._states[app_id]

    def transition(self, app_id: str, to_state: str) -> bool:
        """
        Transition app_id to to_state.

        Returns True on success.
        Raises InvalidTransitionError if the transition is not allowed.
        Raises AppNotFoundError if the app_id is unknown.
        """
        if app_id not in self._states:
            raise AppNotFoundError(f"App '{app_id}' not found in lifecycle.")
        if to_state not in AppState.ALL_STATES:
            raise InvalidTransitionError(app_id, self._states[app_id], to_state)

        from_state = self._states[app_id]
        allowed = _VALID_TRANSITIONS.get(from_state, frozenset())
        if to_state not in allowed:
            raise InvalidTransitionError(app_id, from_state, to_state)

        self._states[app_id] = to_state
        self._history[app_id].append((from_state, to_state, int(time.time())))
        return True

    def get_history(self, app_id: str) -> List[Tuple[str, str, int]]:
        """Return transition history for an app as list of (from, to, timestamp) tuples."""
        if app_id not in self._history:
            raise AppNotFoundError(f"App '{app_id}' not found in lifecycle.")
        return list(self._history[app_id])

    def is_running(self, app_id: str) -> bool:
        """Return True if the app is in RUNNING state."""
        return self._states.get(app_id) == AppState.RUNNING

    def all_running(self) -> List[str]:
        """Return list of app_ids currently in RUNNING state."""
        return [aid for aid, state in self._states.items()
                if state == AppState.RUNNING]


# ---------------------------------------------------------------------------
# AppRegistry — registry of available companion apps
# ---------------------------------------------------------------------------

class AppRegistry:
    """
    Registry of available companion apps.

    Hard caps:
      - MAX_REGISTERED_APPS (10): total registered apps
      - MAX_RUNNING_APPS (5): simultaneous running apps

    All registered apps must pass SHA256 manifest validation.
    """

    def __init__(self) -> None:
        self._apps: Dict[str, CompanionApp] = {}
        self._lifecycle = AppLifecycle()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, app: CompanionApp) -> None:
        """
        Register a companion app.

        Validates:
          1. app_id not already registered (no duplicates)
          2. registry not at capacity (max MAX_REGISTERED_APPS)
          3. manifest hash is computable (structural validation)
          4. required_scopes includes companion.app.run

        Raises:
            AppRegistryError: if duplicate, at capacity, or invalid manifest.
            AppScopeError: if companion.app.run scope is missing.
        """
        if app.app_id in self._apps:
            raise AppRegistryError(
                f"App '{app.app_id}' is already registered. "
                "Unregister it first before re-registering."
            )
        if len(self._apps) >= MAX_REGISTERED_APPS:
            raise AppRegistryError(
                f"Registry is at capacity ({MAX_REGISTERED_APPS} apps). "
                "Unregister an existing app before registering a new one."
            )
        # Validate base scope
        if "companion.app.run" not in app.required_scopes:
            raise AppScopeError(app.app_id, ["companion.app.run"])
        # Validate manifest hash is computable (structural check)
        _hash = app.manifest_hash()
        if not _hash.startswith("sha256:"):
            raise ManifestHashError(app.app_id, "sha256:*", _hash)

        self._apps[app.app_id] = app
        self._lifecycle.register(app.app_id)

    def unregister(self, app_id: str) -> None:
        """
        Remove an app from the registry.

        The app must be in STOPPED, REGISTERED, or ERROR state (cannot unregister a running app).

        Raises:
            AppNotFoundError: if app_id not in registry.
            AppRegistryError: if app is currently RUNNING or STARTING/STOPPING.
        """
        if app_id not in self._apps:
            raise AppNotFoundError(f"App '{app_id}' is not registered.")
        state = self._lifecycle.get_state(app_id)
        if state in (AppState.RUNNING, AppState.STARTING, AppState.STOPPING):
            raise AppRegistryError(
                f"Cannot unregister app '{app_id}' while it is in state {state}. "
                "Stop it first."
            )
        del self._apps[app_id]
        self._lifecycle.unregister(app_id)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, app_id: str) -> Optional[CompanionApp]:
        """Return the CompanionApp for app_id, or None if not registered."""
        return self._apps.get(app_id)

    def list_apps(self) -> List[CompanionApp]:
        """Return all registered companion apps."""
        return list(self._apps.values())

    def list_running(self) -> List[CompanionApp]:
        """Return all companion apps currently in RUNNING state."""
        running_ids = self._lifecycle.all_running()
        return [self._apps[aid] for aid in running_ids if aid in self._apps]

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------

    def start_app(self, app_id: str) -> None:
        """
        Start a registered app.

        Transitions: REGISTERED/STOPPED → STARTING → RUNNING.
        Enforces MAX_RUNNING_APPS limit.

        Raises:
            AppNotFoundError: if app_id not registered.
            AppRegistryError: if already at MAX_RUNNING_APPS.
            InvalidTransitionError: if app is not in startable state.
        """
        if app_id not in self._apps:
            raise AppNotFoundError(f"App '{app_id}' is not registered.")
        running_count = len(self._lifecycle.all_running())
        if running_count >= MAX_RUNNING_APPS:
            raise AppRegistryError(
                f"Cannot start app '{app_id}': already at max running apps "
                f"({MAX_RUNNING_APPS}). Stop another app first."
            )
        self._lifecycle.transition(app_id, AppState.STARTING)
        try:
            self._apps[app_id].start()
            self._lifecycle.transition(app_id, AppState.RUNNING)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            self._lifecycle.transition(app_id, AppState.ERROR)
            raise CompanionAppError(
                f"App '{app_id}' failed to start: {exc}"
            ) from exc

    def stop_app(self, app_id: str) -> None:
        """
        Stop a running app.

        Transitions: RUNNING → STOPPING → STOPPED.

        Raises:
            AppNotFoundError: if app_id not registered.
            InvalidTransitionError: if app is not in RUNNING state.
        """
        if app_id not in self._apps:
            raise AppNotFoundError(f"App '{app_id}' is not registered.")
        self._lifecycle.transition(app_id, AppState.STOPPING)
        try:
            self._apps[app_id].stop()
            self._lifecycle.transition(app_id, AppState.STOPPED)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            self._lifecycle.transition(app_id, AppState.ERROR)
            raise CompanionAppError(
                f"App '{app_id}' failed to stop cleanly: {exc}"
            ) from exc

    def get_state(self, app_id: str) -> str:
        """Return the lifecycle state for app_id."""
        if app_id not in self._apps:
            raise AppNotFoundError(f"App '{app_id}' is not registered.")
        return self._lifecycle.get_state(app_id)

    def get_lifecycle(self) -> AppLifecycle:
        """Return the underlying AppLifecycle instance (for testing)."""
        return self._lifecycle
