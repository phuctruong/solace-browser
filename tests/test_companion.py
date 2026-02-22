"""
test_companion.py — Companion App system test suite.

Test classes:
  TestCompanionAppBase       (10) — lifecycle hooks, scopes, manifest hash, repr
  TestAppEvent               ( 6) — creation, valid sources, invalid source, timestamp
  TestAppResponse            ( 5) — creation, valid statuses, invalid status
  TestAppManifest            ( 5) — hash computation, determinism, field coverage
  TestAppLifecycle           (12) — register, transitions, invalid transitions, history, error state
  TestAppRegistry            (18) — register, unregister, get, list, limits, duplicates, scope
  TestAppRegistryLifecycle   ( 8) — start_app, stop_app, limit running, error propagation
  TestCompanionScopes        ( 8) — all scopes registered, step-up scopes, base scope present
  TestAppBridge              (12) — send_to_app, send_to_browser, subscribe, unsubscribe, scope
  TestEventBus               (10) — publish, subscribe, max subscriptions, rate limit, fire-forget
  TestClipboardMonitor       (10) — scope, start/stop, clipboard_change, URL detection, suggestions
  TestSessionRecorder        (12) — scope, start/stop, session lifecycle, export, redaction
  TestTaskTracker            (12) — scope, create, step, complete, cancel, state, auto-complete
  TestOAuth3Integration      ( 8) — token required, scope matching, step-up for system_access/replay
  TestSecurity               (10) — app isolation, no cross-app state, memory budget constant, timeout const
  TestResourceLimits         ( 7) — max apps, max running, max subscriptions, max events

Total: ~153 tests
Rung: 641 (local correctness)

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_companion.py -v -p no:httpbin
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# --- Import companion modules (scopes auto-register on import) ---
from companion.scopes import (
    COMPANION_SCOPES,
    ALL_COMPANION_SCOPES,
    COMPANION_STEP_UP_SCOPES,
    COMPANION_BASE_SCOPE,
)
from companion.apps import (
    CompanionApp,
    AppRegistry,
    AppLifecycle,
    AppEvent,
    AppResponse,
    AppManifest,
    AppState,
    InvalidTransitionError,
    AppRegistryError,
    AppNotFoundError,
    AppScopeError,
    ManifestHashError,
    CompanionAppError,
    MAX_REGISTERED_APPS,
    MAX_RUNNING_APPS,
    APP_MEMORY_BUDGET_BYTES,
    APP_EXECUTION_TIMEOUT_SECONDS,
)
from companion.bridge import (
    AppBridge,
    BrowserAction,
    ActionResult,
    EventBus,
    BridgeScopeError,
    BridgeRateLimitError,
    SubscriptionLimitError,
    StepUpRequiredError,
    EVENT_BUS_MAX_SUBSCRIPTIONS_PER_APP,
    EVENT_BUS_MAX_EVENTS_PER_MINUTE,
)
from companion.builtin import (
    ClipboardMonitor,
    SessionRecorder,
    TaskTracker,
    get_builtin_apps,
)
from oauth3.token import AgencyToken
from oauth3.scopes import SCOPE_REGISTRY


# ===========================================================================
# Helpers / fixtures
# ===========================================================================

class _MinimalApp(CompanionApp):
    """Minimal concrete CompanionApp for testing."""
    app_id = "test.minimal_app"
    name = "Minimal Test App"
    version = "1.0.0"
    required_scopes = ["companion.app.run"]
    description = "Minimal app for unit testing."


class _SystemApp(CompanionApp):
    """App that requires step-up (system_access scope)."""
    app_id = "test.system_app"
    name = "System Test App"
    version = "1.0.0"
    required_scopes = ["companion.app.run", "companion.app.system_access"]
    description = "System-level app for unit testing."


class _CounterApp(CompanionApp):
    """App that increments a counter on each event."""
    app_id = "test.counter_app"
    name = "Counter App"
    version = "2.0.0"
    required_scopes = ["companion.app.run"]

    def __init__(self) -> None:
        super().__init__()
        self._state["count"] = 0

    def handle_event(self, event: AppEvent) -> AppResponse:
        self._state["count"] += 1
        return AppResponse(status="ok", data={"count": self._state["count"]})

    def get_state(self):
        return dict(self._state)


def make_minimal_app() -> _MinimalApp:
    return _MinimalApp()


def make_token(scopes: List[str]) -> AgencyToken:
    """Create a valid AgencyToken with the given companion scopes."""
    return AgencyToken.create(
        issuer="https://solaceagi.com",
        subject="test-user",
        scopes=scopes,
        intent="companion test",
    )


def make_registry() -> AppRegistry:
    return AppRegistry()


def make_bridge(apps=None) -> AppBridge:
    apps = apps or {}
    return AppBridge(apps=apps)


# ===========================================================================
# TestCompanionAppBase
# ===========================================================================

class TestCompanionAppBase:

    def test_minimal_app_creates(self):
        app = make_minimal_app()
        assert app.app_id == "test.minimal_app"

    def test_name_and_version(self):
        app = make_minimal_app()
        assert app.name == "Minimal Test App"
        assert app.version == "1.0.0"

    def test_required_scopes_includes_base(self):
        app = make_minimal_app()
        assert "companion.app.run" in app.required_scopes

    def test_start_sets_running(self):
        app = make_minimal_app()
        app.start()
        assert app.get_state().get("running") is True

    def test_stop_clears_running(self):
        app = make_minimal_app()
        app.start()
        app.stop()
        assert app.get_state().get("running") is False

    def test_handle_event_default_response(self):
        app = make_minimal_app()
        event = AppEvent(event_type="ping", source="system", data={})
        response = app.handle_event(event)
        assert isinstance(response, AppResponse)
        assert response.status == "ok"
        assert response.data.get("echo") == "ping"

    def test_get_state_returns_copy(self):
        app = make_minimal_app()
        s1 = app.get_state()
        s2 = app.get_state()
        assert s1 == s2
        # Mutating returned copy does not affect internal state
        s1["injected"] = True
        assert "injected" not in app.get_state()

    def test_requires_step_up_false_for_base_app(self):
        app = make_minimal_app()
        assert app.requires_step_up() is False

    def test_requires_step_up_true_for_system_app(self):
        app = _SystemApp()
        assert app.requires_step_up() is True

    def test_manifest_hash_format(self):
        app = make_minimal_app()
        h = app.manifest_hash()
        assert h.startswith("sha256:")
        assert len(h) == len("sha256:") + 64

    def test_repr_contains_app_id(self):
        app = make_minimal_app()
        assert "test.minimal_app" in repr(app)

    def test_empty_app_id_raises(self):
        class _BadApp(CompanionApp):
            app_id = ""
            name = "Bad"
            version = "1.0.0"
            required_scopes = ["companion.app.run"]
        with pytest.raises(CompanionAppError):
            _BadApp()

    def test_base_scope_auto_added_if_missing(self):
        """If subclass forgets companion.app.run, __init__ adds it."""
        class _NakedApp(CompanionApp):
            app_id = "test.naked"
            name = "Naked"
            version = "1.0.0"
            required_scopes = []
        app = _NakedApp()
        assert "companion.app.run" in app.required_scopes


# ===========================================================================
# TestAppEvent
# ===========================================================================

class TestAppEvent:

    def test_create_minimal(self):
        ev = AppEvent(event_type="test", source="user")
        assert ev.event_type == "test"
        assert ev.source == "user"
        assert ev.data == {}

    def test_timestamp_is_int(self):
        ev = AppEvent(event_type="test", source="system")
        assert isinstance(ev.timestamp, int)

    def test_all_valid_sources(self):
        for src in ("browser", "user", "agent", "system"):
            ev = AppEvent(event_type="x", source=src)
            assert ev.source == src

    def test_invalid_source_raises(self):
        with pytest.raises(ValueError):
            AppEvent(event_type="x", source="hacker")

    def test_data_payload(self):
        ev = AppEvent(event_type="click", source="browser", data={"target": "#btn"})
        assert ev.data["target"] == "#btn"

    def test_explicit_timestamp(self):
        ev = AppEvent(event_type="x", source="system", timestamp=12345)
        assert ev.timestamp == 12345


# ===========================================================================
# TestAppResponse
# ===========================================================================

class TestAppResponse:

    def test_ok_status(self):
        r = AppResponse(status="ok")
        assert r.status == "ok"

    def test_error_status(self):
        r = AppResponse(status="error", data={"msg": "fail"})
        assert r.status == "error"

    def test_deferred_status(self):
        r = AppResponse(status="deferred")
        assert r.status == "deferred"

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            AppResponse(status="pending")

    def test_actions_list(self):
        r = AppResponse(status="ok", actions=["navigate:http://x.com"])
        assert "navigate:http://x.com" in r.actions


# ===========================================================================
# TestAppManifest
# ===========================================================================

class TestAppManifest:

    def test_compute_hash_format(self):
        h = AppManifest.compute_hash("a.b", "App", "1.0.0", ["companion.app.run"])
        assert h.startswith("sha256:")
        assert len(h) == 71  # "sha256:" + 64 hex chars

    def test_hash_is_deterministic(self):
        h1 = AppManifest.compute_hash("a.b", "App", "1.0.0", ["companion.app.run"])
        h2 = AppManifest.compute_hash("a.b", "App", "1.0.0", ["companion.app.run"])
        assert h1 == h2

    def test_hash_differs_with_different_fields(self):
        h1 = AppManifest.compute_hash("a.b", "App", "1.0.0", ["companion.app.run"])
        h2 = AppManifest.compute_hash("a.b", "App", "2.0.0", ["companion.app.run"])
        assert h1 != h2

    def test_scope_order_does_not_affect_hash(self):
        h1 = AppManifest.compute_hash("a.b", "App", "1.0.0",
                                       ["companion.app.run", "companion.clipboard.monitor"])
        h2 = AppManifest.compute_hash("a.b", "App", "1.0.0",
                                       ["companion.clipboard.monitor", "companion.app.run"])
        assert h1 == h2

    def test_app_manifest_hash_matches_compute(self):
        app = make_minimal_app()
        expected = AppManifest.compute_hash(
            app.app_id, app.name, app.version, list(app.required_scopes)
        )
        assert app.manifest_hash() == expected


# ===========================================================================
# TestAppLifecycle
# ===========================================================================

class TestAppLifecycle:

    def test_register_sets_registered_state(self):
        lc = AppLifecycle()
        lc.register("app1")
        assert lc.get_state("app1") == AppState.REGISTERED

    def test_duplicate_register_raises(self):
        lc = AppLifecycle()
        lc.register("app1")
        with pytest.raises(AppRegistryError):
            lc.register("app1")

    def test_valid_transition_registered_to_starting(self):
        lc = AppLifecycle()
        lc.register("app1")
        result = lc.transition("app1", AppState.STARTING)
        assert result is True
        assert lc.get_state("app1") == AppState.STARTING

    def test_valid_transition_starting_to_running(self):
        lc = AppLifecycle()
        lc.register("app1")
        lc.transition("app1", AppState.STARTING)
        lc.transition("app1", AppState.RUNNING)
        assert lc.get_state("app1") == AppState.RUNNING

    def test_valid_transition_running_to_stopping(self):
        lc = AppLifecycle()
        lc.register("app1")
        lc.transition("app1", AppState.STARTING)
        lc.transition("app1", AppState.RUNNING)
        lc.transition("app1", AppState.STOPPING)
        assert lc.get_state("app1") == AppState.STOPPING

    def test_valid_transition_stopping_to_stopped(self):
        lc = AppLifecycle()
        lc.register("app1")
        lc.transition("app1", AppState.STARTING)
        lc.transition("app1", AppState.RUNNING)
        lc.transition("app1", AppState.STOPPING)
        lc.transition("app1", AppState.STOPPED)
        assert lc.get_state("app1") == AppState.STOPPED

    def test_invalid_transition_raises(self):
        lc = AppLifecycle()
        lc.register("app1")
        with pytest.raises(InvalidTransitionError):
            lc.transition("app1", AppState.RUNNING)  # REGISTERED → RUNNING is invalid

    def test_invalid_transition_registered_to_stopped(self):
        lc = AppLifecycle()
        lc.register("app1")
        with pytest.raises(InvalidTransitionError):
            lc.transition("app1", AppState.STOPPED)

    def test_transition_to_error_always_allowed_from_running(self):
        lc = AppLifecycle()
        lc.register("app1")
        lc.transition("app1", AppState.STARTING)
        lc.transition("app1", AppState.RUNNING)
        lc.transition("app1", AppState.ERROR)
        assert lc.get_state("app1") == AppState.ERROR

    def test_error_can_return_to_registered(self):
        lc = AppLifecycle()
        lc.register("app1")
        lc.transition("app1", AppState.STARTING)
        lc.transition("app1", AppState.ERROR)
        lc.transition("app1", AppState.REGISTERED)
        assert lc.get_state("app1") == AppState.REGISTERED

    def test_history_recorded(self):
        lc = AppLifecycle()
        lc.register("app1")
        lc.transition("app1", AppState.STARTING)
        lc.transition("app1", AppState.RUNNING)
        history = lc.get_history("app1")
        assert len(history) == 2
        assert history[0][0] == AppState.REGISTERED
        assert history[0][1] == AppState.STARTING
        assert history[1][0] == AppState.STARTING
        assert history[1][1] == AppState.RUNNING

    def test_history_timestamps_are_int(self):
        lc = AppLifecycle()
        lc.register("app1")
        lc.transition("app1", AppState.STARTING)
        history = lc.get_history("app1")
        assert isinstance(history[0][2], int)

    def test_is_running(self):
        lc = AppLifecycle()
        lc.register("app1")
        assert not lc.is_running("app1")
        lc.transition("app1", AppState.STARTING)
        lc.transition("app1", AppState.RUNNING)
        assert lc.is_running("app1")

    def test_all_running(self):
        lc = AppLifecycle()
        lc.register("a1")
        lc.register("a2")
        lc.transition("a1", AppState.STARTING)
        lc.transition("a1", AppState.RUNNING)
        running = lc.all_running()
        assert "a1" in running
        assert "a2" not in running

    def test_unregister_removes_app(self):
        lc = AppLifecycle()
        lc.register("app1")
        lc.unregister("app1")
        with pytest.raises(AppNotFoundError):
            lc.get_state("app1")

    def test_get_state_unknown_app_raises(self):
        lc = AppLifecycle()
        with pytest.raises(AppNotFoundError):
            lc.get_state("ghost")

    def test_stopped_can_restart(self):
        lc = AppLifecycle()
        lc.register("app1")
        lc.transition("app1", AppState.STARTING)
        lc.transition("app1", AppState.RUNNING)
        lc.transition("app1", AppState.STOPPING)
        lc.transition("app1", AppState.STOPPED)
        # Restart
        lc.transition("app1", AppState.STARTING)
        assert lc.get_state("app1") == AppState.STARTING


# ===========================================================================
# TestAppRegistry
# ===========================================================================

class TestAppRegistry:

    def test_register_and_get(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        assert reg.get(app.app_id) is app

    def test_get_unknown_returns_none(self):
        reg = make_registry()
        assert reg.get("ghost") is None

    def test_list_apps_empty(self):
        reg = make_registry()
        assert reg.list_apps() == []

    def test_list_apps_after_register(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        lst = reg.list_apps()
        assert len(lst) == 1
        assert lst[0] is app

    def test_duplicate_register_raises(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        with pytest.raises(AppRegistryError):
            reg.register(app)

    def test_max_registered_apps(self):
        """Registry hard cap: MAX_REGISTERED_APPS."""
        reg = make_registry()
        for i in range(MAX_REGISTERED_APPS):
            class _DynApp(CompanionApp):
                app_id = f"test.app_{i}"
                name = f"App {i}"
                version = "1.0.0"
                required_scopes = ["companion.app.run"]
            _DynApp.app_id = f"test.app_cap_{i}"
            reg.register(_DynApp())
        # One more should fail
        class _OverflowApp(CompanionApp):
            app_id = "test.overflow"
            name = "Overflow"
            version = "1.0.0"
            required_scopes = ["companion.app.run"]
        with pytest.raises(AppRegistryError, match="capacity"):
            reg.register(_OverflowApp())

    def test_unregister_removes(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        reg.unregister(app.app_id)
        assert reg.get(app.app_id) is None

    def test_unregister_unknown_raises(self):
        reg = make_registry()
        with pytest.raises(AppNotFoundError):
            reg.unregister("ghost")

    def test_list_running_empty(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        assert reg.list_running() == []

    def test_list_running_after_start(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        reg.start_app(app.app_id)
        running = reg.list_running()
        assert len(running) == 1
        assert running[0] is app

    def test_state_registered_after_register(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        assert reg.get_state(app.app_id) == AppState.REGISTERED

    def test_state_running_after_start(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        reg.start_app(app.app_id)
        assert reg.get_state(app.app_id) == AppState.RUNNING

    def test_state_stopped_after_stop(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        reg.start_app(app.app_id)
        reg.stop_app(app.app_id)
        assert reg.get_state(app.app_id) == AppState.STOPPED

    def test_missing_base_scope_raises(self):
        class _NoScopeApp(CompanionApp):
            app_id = "test.no_scope"
            name = "No Scope"
            version = "1.0.0"
            required_scopes = []

            def __init__(self):
                # Bypass super().__init__ auto-add to test registry validation
                self._state = {}
                self._started_at = None
                self._stopped_at = None
                # Deliberately do NOT add companion.app.run
                self.required_scopes = []

        reg = make_registry()
        app = _NoScopeApp()
        with pytest.raises(AppScopeError):
            reg.register(app)

    def test_cannot_unregister_running_app(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        reg.start_app(app.app_id)
        with pytest.raises(AppRegistryError):
            reg.unregister(app.app_id)

    def test_max_10_registered_constant(self):
        assert MAX_REGISTERED_APPS == 10

    def test_max_5_running_constant(self):
        assert MAX_RUNNING_APPS == 5


# ===========================================================================
# TestAppRegistryLifecycle
# ===========================================================================

class TestAppRegistryLifecycle:

    def test_start_app_not_registered_raises(self):
        reg = make_registry()
        with pytest.raises(AppNotFoundError):
            reg.start_app("ghost")

    def test_stop_app_not_running_raises(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        with pytest.raises(InvalidTransitionError):
            reg.stop_app(app.app_id)  # REGISTERED → STOPPING is invalid

    def test_max_running_apps_limit(self):
        """Cannot start more than MAX_RUNNING_APPS apps simultaneously."""
        reg = make_registry()
        apps = []
        for i in range(MAX_RUNNING_APPS + 1):
            class _Dyn(CompanionApp):
                app_id = f"test.run_{i}"
                name = f"Run {i}"
                version = "1.0.0"
                required_scopes = ["companion.app.run"]
            _Dyn.app_id = f"test.running_{i}"
            a = _Dyn()
            apps.append(a)
            reg.register(a)

        for i in range(MAX_RUNNING_APPS):
            reg.start_app(apps[i].app_id)

        with pytest.raises(AppRegistryError, match="max running"):
            reg.start_app(apps[MAX_RUNNING_APPS].app_id)

    def test_stop_frees_running_slot(self):
        reg = make_registry()
        app1 = make_minimal_app()

        class _App2(CompanionApp):
            app_id = "test.slot_release_2"
            name = "App2"
            version = "1.0.0"
            required_scopes = ["companion.app.run"]

        app2 = _App2()
        reg.register(app1)
        reg.register(app2)
        reg.start_app(app1.app_id)
        reg.stop_app(app1.app_id)
        # Should now be able to start app2 even if we'd filled slots
        reg.start_app(app2.app_id)
        assert reg.get_state(app2.app_id) == AppState.RUNNING

    def test_counter_app_event_handling(self):
        reg = make_registry()
        app = _CounterApp()
        reg.register(app)
        reg.start_app(app.app_id)
        event = AppEvent(event_type="increment", source="user")
        response = app.handle_event(event)
        assert response.status == "ok"
        assert response.data["count"] == 1

    def test_get_state_unknown_raises(self):
        reg = make_registry()
        with pytest.raises(AppNotFoundError):
            reg.get_state("ghost")

    def test_start_calls_app_start(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        reg.start_app(app.app_id)
        # app.start() should have been called
        assert app.get_state().get("running") is True

    def test_stop_calls_app_stop(self):
        reg = make_registry()
        app = make_minimal_app()
        reg.register(app)
        reg.start_app(app.app_id)
        reg.stop_app(app.app_id)
        assert app.get_state().get("running") is False


# ===========================================================================
# TestCompanionScopes
# ===========================================================================

class TestCompanionScopes:

    def test_all_companion_scopes_in_registry(self):
        for scope in COMPANION_SCOPES:
            assert scope in SCOPE_REGISTRY, f"{scope!r} not in SCOPE_REGISTRY"

    def test_base_scope_present(self):
        assert COMPANION_BASE_SCOPE == "companion.app.run"
        assert "companion.app.run" in SCOPE_REGISTRY

    def test_step_up_scopes_are_high_risk(self):
        from oauth3.scopes import HIGH_RISK_SCOPES
        for scope in COMPANION_STEP_UP_SCOPES:
            assert scope in HIGH_RISK_SCOPES, f"{scope!r} should be high-risk"

    def test_system_access_is_step_up(self):
        assert "companion.app.system_access" in COMPANION_STEP_UP_SCOPES

    def test_recorder_replay_is_step_up(self):
        assert "companion.recorder.replay" in COMPANION_STEP_UP_SCOPES

    def test_run_scope_is_not_step_up(self):
        assert "companion.app.run" not in COMPANION_STEP_UP_SCOPES

    def test_all_companion_scopes_frozenset(self):
        assert isinstance(ALL_COMPANION_SCOPES, frozenset)
        assert len(ALL_COMPANION_SCOPES) >= 7

    def test_scope_triple_segment_format(self):
        import re
        pattern = re.compile(r"^[a-z][a-z0-9_-]+\.[a-z][a-z0-9_-]+\.[a-z][a-z0-9_-]+$")
        for scope in COMPANION_SCOPES:
            assert pattern.match(scope), f"{scope!r} fails triple-segment check"


# ===========================================================================
# TestAppBridge
# ===========================================================================

class TestAppBridge:

    def _make_bridge_with_app(self, app=None):
        app = app or make_minimal_app()
        bridge = AppBridge(apps={app.app_id: app})
        bridge.grant_scopes(app.app_id, [
            "companion.bridge.communicate",
            "companion.app.run",
        ])
        return bridge, app

    def test_send_to_app_requires_bridge_scope(self):
        bridge, app = self._make_bridge_with_app()
        bridge.revoke_scopes(app.app_id)
        event = AppEvent(event_type="ping", source="system")
        with pytest.raises(BridgeScopeError):
            bridge.send_to_app(app.app_id, event)

    def test_send_to_app_success(self):
        bridge, app = self._make_bridge_with_app()
        event = AppEvent(event_type="ping", source="system")
        resp = bridge.send_to_app(app.app_id, event)
        assert isinstance(resp, AppResponse)
        assert resp.status == "ok"

    def test_send_to_app_unknown_raises(self):
        bridge = make_bridge()
        event = AppEvent(event_type="ping", source="system")
        with pytest.raises(AppNotFoundError):
            bridge.send_to_app("ghost", event)

    def test_send_to_browser_requires_bridge_scope(self):
        bridge, app = self._make_bridge_with_app()
        bridge.revoke_scopes(app.app_id)
        action = BrowserAction(action_type="read", target="#content")
        with pytest.raises(BridgeScopeError):
            bridge.send_to_browser(app.app_id, action, step_up_confirmed=True)

    def test_send_to_browser_read_no_step_up_needed(self):
        """'read' action is not in destructive list, so no step-up needed."""
        bridge, app = self._make_bridge_with_app()
        action = BrowserAction(action_type="read", target="#content")
        result = bridge.send_to_browser(app.app_id, action, step_up_confirmed=False)
        assert isinstance(result, ActionResult)
        assert result.success is True

    def test_send_to_browser_click_requires_step_up(self):
        bridge, app = self._make_bridge_with_app()
        action = BrowserAction(action_type="click", target="#btn")
        with pytest.raises(StepUpRequiredError):
            bridge.send_to_browser(app.app_id, action, step_up_confirmed=False)

    def test_send_to_browser_click_with_step_up_ok(self):
        bridge, app = self._make_bridge_with_app()
        action = BrowserAction(action_type="click", target="#btn")
        result = bridge.send_to_browser(app.app_id, action, step_up_confirmed=True)
        assert result.success is True

    def test_subscribe_requires_bridge_scope(self):
        bridge = make_bridge()
        with pytest.raises(BridgeScopeError):
            bridge.subscribe("ghost_app", ["click"])

    def test_subscribe_success(self):
        bridge, app = self._make_bridge_with_app()
        bridge.subscribe(app.app_id, ["clipboard_change"])
        eb = bridge.get_event_bus()
        assert eb.subscription_count(app.app_id) >= 1

    def test_unsubscribe_success(self):
        bridge, app = self._make_bridge_with_app()
        bridge.subscribe(app.app_id, ["clipboard_change"])
        before = bridge.get_event_bus().subscription_count(app.app_id)
        bridge.unsubscribe(app.app_id, ["clipboard_change"])
        after = bridge.get_event_bus().subscription_count(app.app_id)
        assert after < before

    def test_publish_event_fire_and_forget(self):
        bridge, app = self._make_bridge_with_app()
        # Grant bridge scope on the source side too
        event = AppEvent(event_type="test_pub", source="system", timestamp=int(time.time()))
        # Should not raise even with no subscribers
        bridge.publish_event(event)

    def test_send_to_browser_navigate_requires_step_up(self):
        bridge, app = self._make_bridge_with_app()
        action = BrowserAction(action_type="navigate", target="https://evil.com")
        with pytest.raises(StepUpRequiredError):
            bridge.send_to_browser(app.app_id, action, step_up_confirmed=False)


# ===========================================================================
# TestEventBus
# ===========================================================================

class TestEventBus:

    def test_subscribe_and_receive(self):
        bus = EventBus()
        received = []
        bus.subscribe("app1", "click", lambda ev: received.append(ev))
        ev = AppEvent(event_type="click", source="browser")
        bus.publish(ev)
        assert len(received) == 1
        assert received[0].event_type == "click"

    def test_publish_only_to_matching_type(self):
        bus = EventBus()
        received = []
        bus.subscribe("app1", "click", lambda ev: received.append(ev))
        bus.publish(AppEvent(event_type="navigate", source="browser"))
        assert len(received) == 0

    def test_multiple_subscribers_same_event(self):
        bus = EventBus()
        results = []
        bus.subscribe("app1", "load", lambda ev: results.append("a1"))
        bus.subscribe("app2", "load", lambda ev: results.append("a2"))
        bus.publish(AppEvent(event_type="load", source="browser"))
        assert "a1" in results
        assert "a2" in results

    def test_unsubscribe_removes_callbacks(self):
        bus = EventBus()
        received = []
        bus.subscribe("app1", "click", lambda ev: received.append(ev))
        bus.unsubscribe("app1", "click")
        bus.publish(AppEvent(event_type="click", source="browser"))
        assert len(received) == 0

    def test_max_subscriptions_enforced(self):
        bus = EventBus()
        for i in range(EVENT_BUS_MAX_SUBSCRIPTIONS_PER_APP):
            bus.subscribe("app1", f"event_{i}", lambda ev: None)
        with pytest.raises(SubscriptionLimitError):
            bus.subscribe("app1", "overflow", lambda ev: None)

    def test_subscription_count(self):
        bus = EventBus()
        assert bus.subscription_count("app1") == 0
        bus.subscribe("app1", "click", lambda ev: None)
        assert bus.subscription_count("app1") == 1

    def test_callback_exception_does_not_stop_others(self):
        bus = EventBus()
        results = []

        def bad_cb(ev):
            raise RuntimeError("boom")

        def good_cb(ev):
            results.append("ok")

        bus.subscribe("app1", "ping", bad_cb)
        bus.subscribe("app2", "ping", good_cb)
        # Should not raise
        bus.publish(AppEvent(event_type="ping", source="system"))
        assert "ok" in results

    def test_exception_logged_to_error_log(self):
        bus = EventBus()

        def bad_cb(ev):
            raise RuntimeError("test error")

        bus.subscribe("app1", "fail", bad_cb)
        bus.publish(AppEvent(event_type="fail", source="system"))
        assert len(bus.error_log) >= 1

    def test_rate_limit_exceeded_raises(self):
        """Pushing EVENT_BUS_MAX_EVENTS_PER_MINUTE+1 events raises BridgeRateLimitError."""
        bus = EventBus()
        # Manually fill the window
        now = int(time.time())
        for _ in range(EVENT_BUS_MAX_EVENTS_PER_MINUTE):
            bus._event_timestamps["system"].append(now)
        with pytest.raises(BridgeRateLimitError):
            bus.publish(AppEvent(event_type="overflow", source="system"))

    def test_event_count_in_window(self):
        bus = EventBus()
        bus.publish(AppEvent(event_type="x", source="agent"))
        count = bus.event_count_in_window("agent")
        assert count == 1


# ===========================================================================
# TestClipboardMonitor
# ===========================================================================

class TestClipboardMonitor:

    def test_app_id(self):
        app = ClipboardMonitor()
        assert app.app_id == "builtin.clipboard_monitor"

    def test_required_scopes_include_base(self):
        app = ClipboardMonitor()
        assert "companion.app.run" in app.required_scopes

    def test_required_scopes_include_clipboard(self):
        app = ClipboardMonitor()
        assert "companion.clipboard.monitor" in app.required_scopes

    def test_does_not_require_step_up(self):
        app = ClipboardMonitor()
        assert app.requires_step_up() is False

    def test_start_stop(self):
        app = ClipboardMonitor()
        app.start()
        assert app.get_state()["running"] is True
        app.stop()
        assert app.get_state()["running"] is False

    def test_clipboard_change_event_with_url(self):
        app = ClipboardMonitor()
        event = AppEvent(
            event_type="clipboard_change",
            source="system",
            data={"content": "Check out https://example.com for details"},
        )
        resp = app.handle_event(event)
        assert resp.status == "ok"
        assert "https://example.com" in resp.data["urls_detected"]

    def test_clipboard_change_suggests_actions(self):
        app = ClipboardMonitor()
        event = AppEvent(
            event_type="clipboard_change",
            source="system",
            data={"content": "Visit https://solaceagi.com"},
        )
        resp = app.handle_event(event)
        assert any("open_url:" in a for a in resp.actions)
        assert any("suggest_recipe:" in a for a in resp.actions)

    def test_clipboard_change_no_url(self):
        app = ClipboardMonitor()
        event = AppEvent(
            event_type="clipboard_change",
            source="system",
            data={"content": "Just plain text, no URL here"},
        )
        resp = app.handle_event(event)
        assert resp.status == "ok"
        assert resp.data["urls_detected"] == []
        assert resp.actions == []

    def test_unknown_event_type_ignored(self):
        app = ClipboardMonitor()
        event = AppEvent(event_type="unknown_event", source="system")
        resp = app.handle_event(event)
        assert resp.status == "ok"

    def test_url_count_accumulates(self):
        app = ClipboardMonitor()
        ev1 = AppEvent(event_type="clipboard_change", source="system",
                       data={"content": "https://a.com"})
        ev2 = AppEvent(event_type="clipboard_change", source="system",
                       data={"content": "https://b.com https://c.com"})
        app.handle_event(ev1)
        app.handle_event(ev2)
        assert app.get_state()["url_count"] == 3

    def test_state_last_content_updated(self):
        app = ClipboardMonitor()
        event = AppEvent(event_type="clipboard_change", source="system",
                         data={"content": "hello world"})
        app.handle_event(event)
        assert app.get_state()["last_content"] == "hello world"


# ===========================================================================
# TestSessionRecorder
# ===========================================================================

class TestSessionRecorder:

    def test_app_id(self):
        app = SessionRecorder()
        assert app.app_id == "builtin.session_recorder"

    def test_required_scopes_include_capture(self):
        app = SessionRecorder()
        assert "companion.recorder.capture" in app.required_scopes

    def test_required_scopes_include_replay(self):
        app = SessionRecorder()
        assert "companion.recorder.replay" in app.required_scopes

    def test_replay_scope_is_step_up(self):
        """companion.recorder.replay is a high-risk (step-up) scope."""
        from oauth3.scopes import HIGH_RISK_SCOPES
        assert "companion.recorder.replay" in HIGH_RISK_SCOPES

    def test_initial_state_not_recording(self):
        app = SessionRecorder()
        assert app.get_state()["recording"] is False

    def test_session_start(self):
        app = SessionRecorder()
        ev = AppEvent(event_type="session_start", source="user",
                      data={"session_id": "sess-001"})
        resp = app.handle_event(ev)
        assert resp.status == "ok"
        assert resp.data["session_id"] == "sess-001"

    def test_session_stop(self):
        app = SessionRecorder()
        app.handle_event(AppEvent(event_type="session_start", source="user",
                                  data={"session_id": "s1"}))
        resp = app.handle_event(AppEvent(event_type="session_stop", source="user", data={}))
        assert resp.status == "ok"
        assert app.get_state()["recording"] is False

    def test_browser_event_recorded(self):
        app = SessionRecorder()
        app.handle_event(AppEvent(event_type="session_start", source="user",
                                  data={"session_id": "s1"}))
        ev = AppEvent(event_type="browser_event", source="browser",
                      data={"action": "click", "target": "#btn"})
        app.handle_event(ev)
        exported = app.export_session()
        assert len(exported["events"]) == 1
        assert exported["events"][0]["event_type"] == "browser_event"

    def test_sensitive_data_redacted(self):
        app = SessionRecorder()
        app.handle_event(AppEvent(event_type="session_start", source="user",
                                  data={"session_id": "s1"}))
        ev = AppEvent(event_type="browser_event", source="browser",
                      data={"action": "type", "value": "mysecretpassword", "sensitive": True})
        app.handle_event(ev)
        exported = app.export_session()
        assert exported["events"][0]["data"]["value"] == "[REDACTED]"

    def test_export_format(self):
        app = SessionRecorder()
        app.handle_event(AppEvent(event_type="session_start", source="user",
                                  data={"session_id": "s-export"}))
        app.handle_event(AppEvent(event_type="session_stop", source="user", data={}))
        exported = app.export_session()
        assert "session_id" in exported
        assert "started_at" in exported
        assert "stopped_at" in exported
        assert "events" in exported
        assert isinstance(exported["events"], list)

    def test_double_start_returns_error(self):
        app = SessionRecorder()
        app.handle_event(AppEvent(event_type="session_start", source="user",
                                  data={"session_id": "s1"}))
        resp = app.handle_event(AppEvent(event_type="session_start", source="user",
                                         data={"session_id": "s2"}))
        assert resp.status == "error"

    def test_stop_without_start_returns_error(self):
        app = SessionRecorder()
        resp = app.handle_event(AppEvent(event_type="session_stop", source="user", data={}))
        assert resp.status == "error"

    def test_browser_event_without_recording_is_deferred(self):
        app = SessionRecorder()
        resp = app.handle_event(AppEvent(event_type="browser_event", source="browser",
                                         data={"action": "click"}))
        assert resp.status == "deferred"

    def test_sessions_completed_counter(self):
        app = SessionRecorder()
        for i in range(3):
            app.handle_event(AppEvent(event_type="session_start", source="user",
                                      data={"session_id": f"s{i}"}))
            app.handle_event(AppEvent(event_type="session_stop", source="user", data={}))
        assert app.get_state()["sessions_completed"] == 3


# ===========================================================================
# TestTaskTracker
# ===========================================================================

class TestTaskTracker:

    def test_app_id(self):
        app = TaskTracker()
        assert app.app_id == "builtin.task_tracker"

    def test_required_scopes_include_manage(self):
        app = TaskTracker()
        assert "companion.tracker.manage" in app.required_scopes

    def test_initial_state(self):
        app = TaskTracker()
        state = app.get_state()
        assert state["active_tasks"] == 0
        assert state["total_tasks"] == 0

    def test_task_create(self):
        app = TaskTracker()
        resp = app.handle_event(AppEvent(
            event_type="task_create", source="user",
            data={"task_id": "t1", "name": "Write report", "steps_total": 5},
        ))
        assert resp.status == "ok"
        assert app.get_state()["active_tasks"] == 1

    def test_task_step_advances(self):
        app = TaskTracker()
        app.handle_event(AppEvent(event_type="task_create", source="user",
                                  data={"task_id": "t1", "name": "Task", "steps_total": 3}))
        resp = app.handle_event(AppEvent(event_type="task_step", source="user",
                                         data={"task_id": "t1"}))
        assert resp.status == "ok"
        assert resp.data["steps_completed"] == 1
        assert resp.data["steps_remaining"] == 2

    def test_task_complete(self):
        app = TaskTracker()
        app.handle_event(AppEvent(event_type="task_create", source="user",
                                  data={"task_id": "t1", "name": "Task", "steps_total": 3}))
        resp = app.handle_event(AppEvent(event_type="task_complete", source="user",
                                         data={"task_id": "t1"}))
        assert resp.status == "ok"
        assert resp.data["done"] is True

    def test_task_cancel(self):
        app = TaskTracker()
        app.handle_event(AppEvent(event_type="task_create", source="user",
                                  data={"task_id": "t1", "name": "Task", "steps_total": 2}))
        resp = app.handle_event(AppEvent(event_type="task_cancel", source="user",
                                         data={"task_id": "t1"}))
        assert resp.status == "ok"
        assert app.get_task("t1") is None

    def test_auto_complete_on_last_step(self):
        app = TaskTracker()
        app.handle_event(AppEvent(event_type="task_create", source="user",
                                  data={"task_id": "t1", "name": "2-step task", "steps_total": 2}))
        app.handle_event(AppEvent(event_type="task_step", source="user", data={"task_id": "t1"}))
        resp = app.handle_event(AppEvent(event_type="task_step", source="user", data={"task_id": "t1"}))
        assert resp.data["done"] is True
        assert app.get_state()["active_tasks"] == 0

    def test_task_step_unknown_task(self):
        app = TaskTracker()
        resp = app.handle_event(AppEvent(event_type="task_step", source="user",
                                         data={"task_id": "ghost"}))
        assert resp.status == "error"

    def test_duplicate_task_id_rejected(self):
        app = TaskTracker()
        app.handle_event(AppEvent(event_type="task_create", source="user",
                                  data={"task_id": "dup", "name": "D", "steps_total": 1}))
        resp = app.handle_event(AppEvent(event_type="task_create", source="user",
                                          data={"task_id": "dup", "name": "D2", "steps_total": 2}))
        assert resp.status == "error"

    def test_get_task_returns_snapshot(self):
        app = TaskTracker()
        app.handle_event(AppEvent(event_type="task_create", source="user",
                                  data={"task_id": "x", "name": "X", "steps_total": 10,
                                        "estimated_seconds": 300}))
        t = app.get_task("x")
        assert t is not None
        assert t["task_id"] == "x"
        assert t["steps_total"] == 10
        assert t["estimated_seconds"] == 300

    def test_get_task_unknown_returns_none(self):
        app = TaskTracker()
        assert app.get_task("ghost") is None

    def test_total_tasks_counter(self):
        app = TaskTracker()
        for i in range(3):
            app.handle_event(AppEvent(event_type="task_create", source="user",
                                      data={"task_id": f"t{i}", "name": f"T{i}", "steps_total": 1}))
        assert app.get_state()["total_tasks"] == 3

    def test_step_on_completed_task_returns_error(self):
        app = TaskTracker()
        app.handle_event(AppEvent(event_type="task_create", source="user",
                                  data={"task_id": "done", "name": "Done", "steps_total": 1}))
        app.handle_event(AppEvent(event_type="task_complete", source="user",
                                  data={"task_id": "done"}))
        resp = app.handle_event(AppEvent(event_type="task_step", source="user",
                                          data={"task_id": "done"}))
        assert resp.status == "error"


# ===========================================================================
# TestOAuth3Integration
# ===========================================================================

class TestOAuth3Integration:

    def test_companion_scopes_accept_in_agency_token(self):
        """AgencyToken.create() accepts companion.* scopes."""
        token = make_token(["companion.app.run"])
        assert "companion.app.run" in token.scopes

    def test_multiple_companion_scopes_in_token(self):
        token = make_token([
            "companion.app.run",
            "companion.bridge.communicate",
            "companion.clipboard.monitor",
        ])
        assert "companion.bridge.communicate" in token.scopes
        assert "companion.clipboard.monitor" in token.scopes

    def test_step_up_scopes_in_token(self):
        """High-risk companion scopes are accepted in token."""
        token = make_token(["companion.app.run", "companion.app.system_access"])
        assert "companion.app.system_access" in token.scopes

    def test_scope_gate_blocks_without_bridge_scope(self):
        """Bridge blocks send_to_app when companion.bridge.communicate is absent."""
        app = make_minimal_app()
        bridge = AppBridge(apps={app.app_id: app})
        # No scopes granted
        event = AppEvent(event_type="ping", source="system")
        with pytest.raises(BridgeScopeError):
            bridge.send_to_app(app.app_id, event)

    def test_scope_gate_passes_with_bridge_scope(self):
        app = make_minimal_app()
        bridge = AppBridge(apps={app.app_id: app})
        bridge.grant_scopes(app.app_id, ["companion.bridge.communicate"])
        event = AppEvent(event_type="ping", source="system")
        resp = bridge.send_to_app(app.app_id, event)
        assert resp.status == "ok"

    def test_system_access_scope_is_high_risk(self):
        from oauth3.scopes import HIGH_RISK_SCOPES
        assert "companion.app.system_access" in HIGH_RISK_SCOPES

    def test_recorder_replay_scope_is_high_risk(self):
        from oauth3.scopes import HIGH_RISK_SCOPES
        assert "companion.recorder.replay" in HIGH_RISK_SCOPES

    def test_run_scope_is_low_risk(self):
        from oauth3.scopes import get_scope_risk_level
        assert get_scope_risk_level("companion.app.run") == "low"


# ===========================================================================
# TestSecurity
# ===========================================================================

class TestSecurity:

    def test_app_state_is_isolated(self):
        """Two apps do not share state."""
        app1 = _CounterApp()
        app2 = ClipboardMonitor()
        app1.handle_event(AppEvent(event_type="increment", source="user"))
        # app2 state should not be affected
        assert app2.get_state().get("count") is None

    def test_get_state_returns_copy_not_reference(self):
        """Mutating the returned state dict does not affect internal state."""
        app = _CounterApp()
        s = app.get_state()
        s["count"] = 9999
        assert app.get_state()["count"] == 0

    def test_memory_budget_constant_is_10mb(self):
        assert APP_MEMORY_BUDGET_BYTES == 10 * 1024 * 1024

    def test_execution_timeout_constant_is_5s(self):
        assert APP_EXECUTION_TIMEOUT_SECONDS == 5

    def test_apps_cannot_access_other_apps_via_registry(self):
        """Registry.get() only returns the specific app, not all apps."""
        reg = make_registry()
        app1 = make_minimal_app()

        class _App2(CompanionApp):
            app_id = "test.other_app"
            name = "Other"
            version = "1.0.0"
            required_scopes = ["companion.app.run"]

        app2 = _App2()
        reg.register(app1)
        reg.register(app2)
        retrieved = reg.get(app1.app_id)
        assert retrieved is not app2

    def test_bridge_does_not_expose_other_apps(self):
        """AppBridge only routes to the addressed app."""
        app1 = make_minimal_app()

        class _App2(CompanionApp):
            app_id = "test.target_app"
            name = "Target"
            version = "1.0.0"
            required_scopes = ["companion.app.run"]

        app2 = _App2()
        bridge = AppBridge(apps={app1.app_id: app1, app2.app_id: app2})
        bridge.grant_scopes(app1.app_id, ["companion.bridge.communicate"])
        # Sending to app2 from app1's context should fail (scope granted to app1 only)
        event = AppEvent(event_type="ping", source="system")
        with pytest.raises(BridgeScopeError):
            bridge.send_to_app(app2.app_id, event)

    def test_browser_action_validate_type(self):
        """Invalid action_type raises ValueError."""
        with pytest.raises(ValueError):
            BrowserAction(action_type="exec", target="shell")

    def test_app_event_invalid_source_raises(self):
        with pytest.raises(ValueError):
            AppEvent(event_type="x", source="root")

    def test_scope_registration_idempotent(self):
        """Calling _register_companion_scopes() twice does not duplicate entries."""
        from companion.scopes import _register_companion_scopes
        before_len = len(SCOPE_REGISTRY)
        _register_companion_scopes()
        after_len = len(SCOPE_REGISTRY)
        assert after_len == before_len

    def test_destructive_browser_actions_gate(self):
        """All destructive action types require step_up_confirmed=True."""
        app = make_minimal_app()
        bridge = AppBridge(apps={app.app_id: app})
        bridge.grant_scopes(app.app_id, ["companion.bridge.communicate"])
        for act in ("click", "type", "navigate"):
            action = BrowserAction(action_type=act, target="x")
            with pytest.raises(StepUpRequiredError):
                bridge.send_to_browser(app.app_id, action, step_up_confirmed=False)


# ===========================================================================
# TestResourceLimits
# ===========================================================================

class TestResourceLimits:

    def test_max_registered_apps_constant(self):
        assert MAX_REGISTERED_APPS == 10

    def test_max_running_apps_constant(self):
        assert MAX_RUNNING_APPS == 5

    def test_max_subscriptions_constant(self):
        assert EVENT_BUS_MAX_SUBSCRIPTIONS_PER_APP == 20

    def test_max_events_per_minute_constant(self):
        assert EVENT_BUS_MAX_EVENTS_PER_MINUTE == 1000

    def test_registry_at_capacity_error_message(self):
        reg = make_registry()
        for i in range(MAX_REGISTERED_APPS):
            class _A(CompanionApp):
                app_id = f"test.cap_{i}"
                name = f"Cap {i}"
                version = "1.0.0"
                required_scopes = ["companion.app.run"]
            _A.app_id = f"test.capacity_{i}"
            reg.register(_A())
        class _Over(CompanionApp):
            app_id = "test.over"
            name = "Over"
            version = "1.0.0"
            required_scopes = ["companion.app.run"]
        with pytest.raises(AppRegistryError) as exc_info:
            reg.register(_Over())
        assert "capacity" in str(exc_info.value).lower()

    def test_subscription_limit_error_message(self):
        bus = EventBus()
        for i in range(EVENT_BUS_MAX_SUBSCRIPTIONS_PER_APP):
            bus.subscribe("app1", f"ev_{i}", lambda ev: None)
        with pytest.raises(SubscriptionLimitError) as exc_info:
            bus.subscribe("app1", "overflow", lambda ev: None)
        assert str(EVENT_BUS_MAX_SUBSCRIPTIONS_PER_APP) in str(exc_info.value)

    def test_get_builtin_apps_returns_three(self):
        apps = get_builtin_apps()
        assert len(apps) == 3
        ids = {a.app_id for a in apps}
        assert "builtin.clipboard_monitor" in ids
        assert "builtin.session_recorder" in ids
        assert "builtin.task_tracker" in ids
