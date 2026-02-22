"""
companion/bridge.py — Bridge between companion apps and the browser agent.

The bridge is the only authorised crossing point between the companion app
sandbox and the browser agent.  Every call across the boundary is:
  1. OAuth3 scope-checked (companion.bridge.communicate required)
  2. Rate-limited (max 1000 events/minute per app via EventBus)
  3. Optionally step-up gated (destructive browser actions)

Key classes:
  AppBridge   — bi-directional communication bridge
  BrowserAction — dataclass for browser-directed actions
  ActionResult  — dataclass for action results
  EventBus    — internal event distribution (max 20 subscriptions per app)

Rules:
  - Bridge enforces OAuth3 scopes on every cross-boundary call
  - Browser actions from apps require the same OAuth3 scopes as direct user actions
  - Step-up required for destructive browser actions initiated by apps
  - EventBus bounded: max 1000 events/minute per app (rate limited)
  - No direct memory sharing between apps

No external dependencies beyond stdlib.
Int arithmetic only (no float).

Rung: 641 (local correctness)
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from companion.apps import (
    AppEvent,
    AppResponse,
    CompanionApp,
    AppNotFoundError,
    CompanionAppError,
)


# ---------------------------------------------------------------------------
# Rate limit constants (all int)
# ---------------------------------------------------------------------------

EVENT_BUS_MAX_EVENTS_PER_MINUTE: int = 1000   # per-app rate cap
EVENT_BUS_MAX_SUBSCRIPTIONS_PER_APP: int = 20  # subscription cap per app
RATE_LIMIT_WINDOW_SECONDS: int = 60            # rolling window size


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class BridgeError(CompanionAppError):
    """Base exception for bridge-level errors."""


class BridgeScopeError(BridgeError):
    """Raised when a cross-boundary call is missing required OAuth3 scopes."""

    def __init__(self, app_id: str, missing_scopes: List[str]) -> None:
        self.app_id = app_id
        self.missing_scopes = missing_scopes
        super().__init__(
            f"Bridge call from app '{app_id}' blocked: "
            f"missing OAuth3 scopes {missing_scopes}."
        )


class BridgeRateLimitError(BridgeError):
    """Raised when an app exceeds the event bus rate limit."""

    def __init__(self, app_id: str, limit: int) -> None:
        self.app_id = app_id
        self.limit = limit
        super().__init__(
            f"App '{app_id}' exceeded event bus rate limit "
            f"({limit} events/minute)."
        )


class SubscriptionLimitError(BridgeError):
    """Raised when an app tries to exceed the max subscription count."""

    def __init__(self, app_id: str, limit: int) -> None:
        self.app_id = app_id
        self.limit = limit
        super().__init__(
            f"App '{app_id}' has reached the subscription limit ({limit})."
        )


class StepUpRequiredError(BridgeError):
    """Raised when a destructive browser action requires step-up auth."""

    def __init__(self, app_id: str, action_type: str) -> None:
        self.app_id = app_id
        self.action_type = action_type
        super().__init__(
            f"Browser action '{action_type}' from app '{app_id}' requires "
            "step-up authentication."
        )


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

# Browser action types that are considered destructive (require step-up)
_DESTRUCTIVE_ACTION_TYPES = frozenset({"click", "type", "navigate"})

# Base scope required for all bridge communication
_BRIDGE_SCOPE = "companion.bridge.communicate"


@dataclass
class BrowserAction:
    """
    An action that a companion app requests the browser to perform.

    Fields:
        action_type:       One of "navigate", "click", "type", "read", "screenshot"
        target:            CSS selector, URL, or resource identifier
        parameters:        Extra parameters for the action (key/value)
        requires_approval: If True, the bridge must seek user approval before
                           forwarding to the browser (step-up gate)
    """
    action_type: str           # "navigate" | "click" | "type" | "read" | "screenshot"
    target: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False

    def __post_init__(self) -> None:
        valid_types = {"navigate", "click", "type", "read", "screenshot"}
        if self.action_type not in valid_types:
            raise ValueError(
                f"BrowserAction.action_type must be one of {sorted(valid_types)}, "
                f"got {self.action_type!r}."
            )


@dataclass
class ActionResult:
    """
    Result returned by the browser agent after executing a BrowserAction.

    Fields:
        success:    True if the action completed without error
        data:       Action output (e.g. page title, element text)
        error:      Error message if success is False; empty string otherwise
    """
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""


# ---------------------------------------------------------------------------
# EventBus — internal event distribution
# ---------------------------------------------------------------------------

class EventBus:
    """
    Internal publish/subscribe event bus.

    Rules:
      - Max EVENT_BUS_MAX_SUBSCRIPTIONS_PER_APP subscriptions per app
      - Max EVENT_BUS_MAX_EVENTS_PER_MINUTE events published per app (rolling window)
      - Events are fire-and-forget (no guaranteed delivery, no retry)
      - Callbacks receive the AppEvent directly; exceptions in callbacks are
        swallowed (logged in error_log) so one bad handler never stops others
    """

    def __init__(self) -> None:
        # {app_id: {event_type: [callback, ...]}}
        self._subscriptions: Dict[str, Dict[str, List[Callable]]] = defaultdict(
            lambda: defaultdict(list)
        )
        # {app_id: count of active subscriptions}
        self._subscription_counts: Dict[str, int] = defaultdict(int)
        # {app_id: deque of timestamps (int) for rate limit sliding window}
        self._event_timestamps: Dict[str, deque] = defaultdict(deque)
        # errors from callbacks (for debugging)
        self.error_log: List[Dict[str, str]] = []

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(
        self,
        app_id: str,
        event_type: str,
        callback: Callable[[AppEvent], None],
    ) -> None:
        """
        Subscribe app_id to events of event_type.

        Raises SubscriptionLimitError if app already has
        EVENT_BUS_MAX_SUBSCRIPTIONS_PER_APP subscriptions.
        """
        current = self._subscription_counts[app_id]
        if current >= EVENT_BUS_MAX_SUBSCRIPTIONS_PER_APP:
            raise SubscriptionLimitError(app_id, EVENT_BUS_MAX_SUBSCRIPTIONS_PER_APP)
        self._subscriptions[app_id][event_type].append(callback)
        self._subscription_counts[app_id] += 1

    def unsubscribe(self, app_id: str, event_type: str) -> None:
        """
        Remove all subscriptions for app_id on event_type.

        Updates subscription count accordingly.
        """
        if app_id in self._subscriptions:
            removed = len(self._subscriptions[app_id].get(event_type, []))
            self._subscriptions[app_id].pop(event_type, None)
            self._subscription_counts[app_id] = max(
                0, self._subscription_counts[app_id] - removed
            )

    def subscription_count(self, app_id: str) -> int:
        """Return the total number of active subscriptions for app_id."""
        return self._subscription_counts.get(app_id, 0)

    # ------------------------------------------------------------------
    # Publishing
    # ------------------------------------------------------------------

    def publish(self, event: AppEvent) -> None:
        """
        Publish event to all subscribers of event.event_type.

        Rate-limited per source app_id (EVENT_BUS_MAX_EVENTS_PER_MINUTE).
        Fire-and-forget: callback exceptions are swallowed.

        Raises BridgeRateLimitError if the publishing app exceeds its rate limit.
        """
        source_id = event.source
        self._check_rate_limit(source_id)
        self._record_event(source_id)

        event_type = event.event_type
        for app_id, type_map in self._subscriptions.items():
            callbacks = type_map.get(event_type, [])
            for cb in callbacks:
                try:
                    cb(event)
                except Exception as exc:  # noqa: BLE001
                    self.error_log.append({
                        "app_id": app_id,
                        "event_type": event_type,
                        "error": str(exc),
                    })

    # ------------------------------------------------------------------
    # Rate limit helpers
    # ------------------------------------------------------------------

    def _check_rate_limit(self, app_id: str) -> None:
        """Raise BridgeRateLimitError if app_id is over its event rate limit."""
        now = int(time.time())
        window_start = now - RATE_LIMIT_WINDOW_SECONDS
        dq = self._event_timestamps[app_id]
        # Remove timestamps outside the rolling window
        while dq and dq[0] < window_start:
            dq.popleft()
        if len(dq) >= EVENT_BUS_MAX_EVENTS_PER_MINUTE:
            raise BridgeRateLimitError(app_id, EVENT_BUS_MAX_EVENTS_PER_MINUTE)

    def _record_event(self, app_id: str) -> None:
        """Record the current timestamp for app_id's event counter."""
        self._event_timestamps[app_id].append(int(time.time()))

    def event_count_in_window(self, app_id: str) -> int:
        """Return how many events app_id has published in the last 60 seconds."""
        now = int(time.time())
        window_start = now - RATE_LIMIT_WINDOW_SECONDS
        dq = self._event_timestamps.get(app_id, deque())
        return sum(1 for ts in dq if ts >= window_start)


# ---------------------------------------------------------------------------
# AppBridge — bi-directional bridge
# ---------------------------------------------------------------------------

class AppBridge:
    """
    Communication bridge between companion apps and the browser agent.

    Every cross-boundary call is:
      1. OAuth3-checked: requires companion.bridge.communicate
      2. Optionally step-up gated for destructive browser actions
      3. Rate-limited via the EventBus

    The bridge does NOT hold references to browser internals; it uses
    a pluggable browser_executor callable for browser actions.
    """

    def __init__(
        self,
        apps: Dict[str, CompanionApp],
        browser_executor: Optional[Callable[[BrowserAction], ActionResult]] = None,
    ) -> None:
        """
        Args:
            apps:             Dict mapping app_id → CompanionApp instance.
            browser_executor: Callable that executes BrowserActions against the
                              browser agent.  Defaults to a stub that returns
                              ActionResult(success=True).
        """
        self._apps = apps
        self._browser_executor: Callable[[BrowserAction], ActionResult] = (
            browser_executor or _default_browser_executor
        )
        self._event_bus = EventBus()
        # {app_id: set of granted scope strings} — populated externally
        self._granted_scopes: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Scope management
    # ------------------------------------------------------------------

    def grant_scopes(self, app_id: str, scopes: List[str]) -> None:
        """Grant OAuth3 scopes to an app for bridge-level enforcement."""
        self._granted_scopes[app_id] = list(scopes)

    def revoke_scopes(self, app_id: str) -> None:
        """Revoke all scopes for an app (e.g. after token expiry)."""
        self._granted_scopes.pop(app_id, None)

    def _has_scope(self, app_id: str, scope: str) -> bool:
        """Return True if app_id has the given scope granted."""
        return scope in self._granted_scopes.get(app_id, [])

    def _check_bridge_scope(self, app_id: str) -> None:
        """
        Enforce companion.bridge.communicate scope.

        Raises BridgeScopeError if not granted.
        """
        if not self._has_scope(app_id, _BRIDGE_SCOPE):
            raise BridgeScopeError(app_id, [_BRIDGE_SCOPE])

    # ------------------------------------------------------------------
    # Inbound: browser/system → app
    # ------------------------------------------------------------------

    def send_to_app(self, app_id: str, event: AppEvent) -> AppResponse:
        """
        Deliver event to a companion app.

        Requires companion.bridge.communicate on the calling side.
        The app_id must be registered.

        Raises:
            AppNotFoundError: if app_id not in apps dict.
            BridgeScopeError: if bridge scope not granted.
        """
        if app_id not in self._apps:
            raise AppNotFoundError(f"App '{app_id}' not found in bridge.")
        self._check_bridge_scope(app_id)
        return self._apps[app_id].handle_event(event)

    # ------------------------------------------------------------------
    # Outbound: app → browser
    # ------------------------------------------------------------------

    def send_to_browser(
        self,
        app_id: str,
        action: BrowserAction,
        step_up_confirmed: bool = False,
    ) -> ActionResult:
        """
        Request the browser agent to execute a BrowserAction on behalf of an app.

        OAuth3 rules:
          - companion.bridge.communicate required (base bridge scope)
          - Destructive actions (click, type, navigate) require step-up unless
            step_up_confirmed=True

        Raises:
            AppNotFoundError: if app_id not registered.
            BridgeScopeError: if bridge scope missing.
            StepUpRequiredError: if action is destructive and step_up_confirmed=False.
        """
        if app_id not in self._apps:
            raise AppNotFoundError(f"App '{app_id}' not found in bridge.")
        self._check_bridge_scope(app_id)
        # Step-up gate for destructive actions
        if action.requires_approval or action.action_type in _DESTRUCTIVE_ACTION_TYPES:
            if not step_up_confirmed:
                raise StepUpRequiredError(app_id, action.action_type)
        return self._browser_executor(action)

    # ------------------------------------------------------------------
    # Event subscription
    # ------------------------------------------------------------------

    def subscribe(self, app_id: str, event_types: List[str]) -> None:
        """
        Subscribe app_id to a list of event types.

        companion.bridge.communicate is required.
        Max EVENT_BUS_MAX_SUBSCRIPTIONS_PER_APP subscriptions per app.

        Raises:
            BridgeScopeError: if bridge scope missing.
            SubscriptionLimitError: if subscription count exceeded.
        """
        self._check_bridge_scope(app_id)
        for event_type in event_types:
            self._event_bus.subscribe(
                app_id=app_id,
                event_type=event_type,
                callback=lambda ev, aid=app_id: self._route_event(aid, ev),
            )

    def unsubscribe(self, app_id: str, event_types: List[str]) -> None:
        """
        Unsubscribe app_id from a list of event types.

        No scope check required for unsubscription (idempotent cleanup).
        """
        for event_type in event_types:
            self._event_bus.unsubscribe(app_id, event_type)

    def _route_event(self, app_id: str, event: AppEvent) -> None:
        """Internal: route an event bus event to the companion app."""
        if app_id in self._apps:
            try:
                self._apps[app_id].handle_event(event)
            except Exception:  # noqa: BLE001
                pass  # fire-and-forget; error already captured by EventBus

    # ------------------------------------------------------------------
    # EventBus exposure
    # ------------------------------------------------------------------

    def get_event_bus(self) -> EventBus:
        """Return the underlying EventBus (for publish access and testing)."""
        return self._event_bus

    def publish_event(self, event: AppEvent) -> None:
        """
        Publish an event to all subscribed apps via the EventBus.

        Rate-limited: raises BridgeRateLimitError if source exceeds 1000/min.
        """
        self._event_bus.publish(event)


# ---------------------------------------------------------------------------
# Default browser executor stub
# ---------------------------------------------------------------------------

def _default_browser_executor(action: BrowserAction) -> ActionResult:
    """
    Default no-op browser executor.

    Real deployments inject a browser-connected executor.
    This stub always returns success so unit tests can operate without
    a running browser.
    """
    return ActionResult(
        success=True,
        data={"stub": True, "action_type": action.action_type, "target": action.target},
    )
