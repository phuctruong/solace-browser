"""Tests for Yinyang rail wiring (B6) — StateBridge + top/bottom rail behavior.

Covers:
- State bridge tracks FSM state correctly
- get_current_state returns proper fields
- approve triggers state transition
- reject triggers state transition
- list_active_runs returns only PREVIEW_READY runs
- Never auto-approves (Anti-Clippy law)
- BLOCKED state includes reason
- Top rail indicator format
- Bottom rail payload behavior
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from execution_lifecycle import (
    ApprovalDecision,
    ExecutionLifecycleManager,
    ExecutionState,
)
from yinyang.state_bridge import (
    AUTO_COLLAPSE_STATES,
    AUTO_EXPAND_STATES,
    STATE_COLOR_MAP,
    ActiveRun,
    RunNotFoundError,
    RunNotInPreviewError,
    YinyangStateBridge,
)
from yinyang.top_rail import _INLINE_TOP_RAIL_JS
from yinyang.bottom_rail import _INLINE_BOTTOM_RAIL_JS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_app(solace_home: Path) -> None:
    """Create a minimal app structure for testing."""
    app_root = solace_home / "apps" / "gmail-inbox-triage"
    for sub in [
        app_root / "diagrams",
        app_root / "inbox" / "prompts",
        app_root / "inbox" / "templates",
        app_root / "inbox" / "assets",
        app_root / "inbox" / "policies",
        app_root / "inbox" / "datasets",
        app_root / "inbox" / "requests",
        app_root / "inbox" / "conventions" / "examples",
        app_root / "outbox" / "previews",
        app_root / "outbox" / "drafts",
        app_root / "outbox" / "reports",
        app_root / "outbox" / "suggestions",
        app_root / "outbox" / "runs",
    ]:
        sub.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": "gmail-inbox-triage",
        "name": "Gmail Inbox Triage",
        "required_inbox": {
            "prompts": [],
            "templates": [],
            "assets": [],
            "policies": [],
            "datasets": [],
            "requests": [],
            "conventions": {"config": "config.yaml", "defaults": "defaults.yaml"},
        },
    }
    (app_root / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )
    (app_root / "recipe.json").write_text(
        json.dumps({"id": "gmail-triage", "steps": []}), encoding="utf-8"
    )
    (app_root / "budget.json").write_text(
        json.dumps({"remaining_runs": 5}), encoding="utf-8"
    )
    for name in ["workflow.md", "data-flow.md", "partner-contracts.md"]:
        (app_root / "diagrams" / name).write_text(
            "```mermaid\nflowchart TD\nA-->B\n```\n", encoding="utf-8"
        )
    (app_root / "inbox" / "conventions" / "config.yaml").write_text(
        "scan_hours: 2\n", encoding="utf-8"
    )
    (app_root / "inbox" / "conventions" / "defaults.yaml").write_text(
        "scan_hours: 24\n", encoding="utf-8"
    )


@pytest.fixture()
def solace_env(tmp_path: Path):
    """Create a solace environment with a test app."""
    solace_home = tmp_path / "solace-home"
    _make_app(solace_home)
    manager = ExecutionLifecycleManager(
        solace_home=solace_home, sleep_fn=lambda _s: None
    )
    bridge = YinyangStateBridge(lifecycle_manager=manager)
    return {"home": solace_home, "manager": manager, "bridge": bridge}


# ---------------------------------------------------------------------------
# Top Rail JS Tests
# ---------------------------------------------------------------------------

class TestTopRailJS:
    """Verify the top rail JavaScript content."""

    def test_top_rail_js_contains_rail_id(self):
        assert "solace-top-rail" in _INLINE_TOP_RAIL_JS

    def test_top_rail_js_handles_state_updates(self):
        assert "yinyang_state" in _INLINE_TOP_RAIL_JS

    def test_top_rail_js_has_color_map(self):
        """Top rail JS should include all ExecutionState color mappings."""
        assert "PREVIEW_READY" in _INLINE_TOP_RAIL_JS
        assert "BLOCKED" in _INLINE_TOP_RAIL_JS
        assert "FAILED" in _INLINE_TOP_RAIL_JS
        assert "DONE" in _INLINE_TOP_RAIL_JS
        assert "EXECUTING" in _INLINE_TOP_RAIL_JS

    def test_top_rail_js_has_app_name_label(self):
        """Top rail should show app_name in the state indicator."""
        assert "solace-app-label" in _INLINE_TOP_RAIL_JS
        assert "app_name" in _INLINE_TOP_RAIL_JS

    def test_top_rail_js_has_pulse_animation(self):
        """Top rail should have pulse animation for processing states."""
        assert "solace-pulse" in _INLINE_TOP_RAIL_JS


# ---------------------------------------------------------------------------
# Bottom Rail JS Tests
# ---------------------------------------------------------------------------

class TestBottomRailJS:
    """Verify the bottom rail JavaScript content."""

    def test_bottom_rail_js_contains_rail_id(self):
        assert "solace-bottom-rail" in _INLINE_BOTTOM_RAIL_JS

    def test_bottom_rail_js_has_ws_placeholder(self):
        assert "__WS_URL__" in _INLINE_BOTTOM_RAIL_JS

    def test_bottom_rail_js_has_auto_expand_states(self):
        """Bottom rail should know which states trigger auto-expand."""
        assert "AUTO_EXPAND" in _INLINE_BOTTOM_RAIL_JS
        assert "PREVIEW_READY" in _INLINE_BOTTOM_RAIL_JS
        assert "BLOCKED" in _INLINE_BOTTOM_RAIL_JS
        assert "FAILED" in _INLINE_BOTTOM_RAIL_JS

    def test_bottom_rail_js_has_auto_collapse_states(self):
        """Bottom rail should know which states trigger auto-collapse."""
        assert "AUTO_COLLAPSE" in _INLINE_BOTTOM_RAIL_JS
        assert "DONE" in _INLINE_BOTTOM_RAIL_JS
        assert "SEALED_ABORT" in _INLINE_BOTTOM_RAIL_JS

    def test_bottom_rail_js_has_approve_reject_buttons(self):
        """Bottom rail should render approve/reject buttons for PREVIEW_READY."""
        assert "solace-approve-btn" in _INLINE_BOTTOM_RAIL_JS
        assert "solace-reject-btn" in _INLINE_BOTTOM_RAIL_JS

    def test_bottom_rail_js_has_fsm_area(self):
        """Bottom rail should have a dedicated FSM action area."""
        assert "solace-fsm-area" in _INLINE_BOTTOM_RAIL_JS

    def test_bottom_rail_js_has_block_reason_display(self):
        """Bottom rail should display block reason."""
        assert "block_reason" in _INLINE_BOTTOM_RAIL_JS

    def test_bottom_rail_js_has_error_detail_display(self):
        """Bottom rail should display error details."""
        assert "error_detail" in _INLINE_BOTTOM_RAIL_JS

    def test_bottom_rail_js_sends_fsm_actions(self):
        """Bottom rail should send fsm_action messages via WebSocket."""
        assert "fsm_action" in _INLINE_BOTTOM_RAIL_JS


# ---------------------------------------------------------------------------
# State Bridge: State Tracking
# ---------------------------------------------------------------------------

class TestStateBridgeTracking:
    """State bridge tracks FSM state correctly."""

    def test_sync_run_approve_tracks_done(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft reply", "actions": ["draft"]},
            execute_callback=lambda _sealed: {"status": "success", "actions_summary": "1 draft"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="looks good",
        )
        info = bridge.get_current_state(run_id)
        assert info["state"] == ExecutionState.DONE.value

    def test_sync_run_reject_tracks_sealed_abort(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft reply"},
            execute_callback=lambda _sealed: {"status": "success"},
            risk_level="low",
            approval_decision=ApprovalDecision.REJECT,
            user_id="phuc",
            meaning="not now",
        )
        info = bridge.get_current_state(run_id)
        assert info["state"] == ExecutionState.SEALED_ABORT.value

    def test_sync_run_with_budget_block_tracks_blocked(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": False, "reason": "B2 daily limit reached"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        info = bridge.get_current_state(run_id)
        assert info["state"] == ExecutionState.BLOCKED.value


# ---------------------------------------------------------------------------
# State Bridge: get_current_state returns proper fields
# ---------------------------------------------------------------------------

class TestGetCurrentState:
    """get_current_state returns all required fields."""

    def test_returns_all_required_keys(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft reply"},
            execute_callback=lambda _sealed: {"status": "success"},
            risk_level="medium",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        info = bridge.get_current_state(run_id)
        required_keys = {
            "state", "preview_text", "can_approve", "can_reject",
            "risk_level", "color", "auto_expand", "auto_collapse",
            "block_reason", "error_detail", "app_id",
        }
        assert required_keys.issubset(info.keys())

    def test_done_state_fields(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft reply"},
            execute_callback=lambda _sealed: {"status": "success"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        info = bridge.get_current_state(run_id)
        assert info["state"] == "DONE"
        assert info["can_approve"] is False
        assert info["can_reject"] is False
        assert info["color"] == "green"
        assert info["auto_collapse"] is True
        assert info["auto_expand"] is False
        assert info["risk_level"] == "low"
        assert info["app_id"] == "gmail-inbox-triage"

    def test_blocked_state_fields(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": False, "reason": "daily limit"},
            risk_level="high",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        info = bridge.get_current_state(run_id)
        assert info["state"] == "BLOCKED"
        assert info["can_approve"] is False
        assert info["can_reject"] is False
        assert info["color"] == "red"
        assert info["auto_expand"] is True
        assert info["risk_level"] == "high"
        assert info["block_reason"] == "daily limit"

    def test_unknown_run_raises(self, solace_env):
        bridge = solace_env["bridge"]
        with pytest.raises(RunNotFoundError):
            bridge.get_current_state("nonexistent-run-id")

    def test_failed_execution_state(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "failed", "error": "network timeout"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        info = bridge.get_current_state(run_id)
        assert info["state"] == "FAILED"
        assert info["color"] == "red"
        assert info["auto_expand"] is True
        assert info["auto_collapse"] is False


# ---------------------------------------------------------------------------
# State Bridge: approve triggers state transition
# ---------------------------------------------------------------------------

class TestApproveTransition:
    """approve() triggers state transition from PREVIEW_READY."""

    def test_approve_from_preview_ready(self, solace_env):
        """Start a run async, wait for PREVIEW_READY, then approve."""
        bridge = solace_env["bridge"]

        preview_reached = threading.Event()
        original_preview = lambda _ctx: {"preview": "Draft reply", "actions": ["draft"]}

        def signaling_preview(ctx):
            result = original_preview(ctx)
            # The bridge will set state to PREVIEW_READY after this returns.
            # We schedule a check after a brief delay.
            return result

        run_id = bridge.start_run(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft reply", "actions": ["draft"]},
            execute_callback=lambda _sealed: {"status": "success", "actions_summary": "1 draft"},
            budget_check=lambda _ctx: {"allowed": True},
            risk_level="low",
        )

        # Wait for PREVIEW_READY state
        for _ in range(100):
            try:
                info = bridge.get_current_state(run_id)
                if info["state"] == "PREVIEW_READY":
                    break
            except RunNotFoundError:
                pass
            time.sleep(0.01)

        info = bridge.get_current_state(run_id)
        assert info["state"] == "PREVIEW_READY"
        assert info["can_approve"] is True
        assert info["preview_text"] == "Draft reply"

        # Approve
        new_state = bridge.approve(run_id, user_id="phuc", meaning="looks good")

        # Wait for execution to complete
        for _ in range(100):
            info = bridge.get_current_state(run_id)
            if info["state"] in ("DONE", "FAILED", "SEALED_ABORT"):
                break
            time.sleep(0.01)

        info = bridge.get_current_state(run_id)
        assert info["state"] == "DONE"
        assert info["can_approve"] is False

    def test_approve_requires_user_id(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": True},
            risk_level="low",
        )

        # Wait for PREVIEW_READY
        for _ in range(100):
            try:
                info = bridge.get_current_state(run_id)
                if info["state"] == "PREVIEW_READY":
                    break
            except RunNotFoundError:
                pass
            time.sleep(0.01)

        with pytest.raises(ValueError, match="user_id is required"):
            bridge.approve(run_id, user_id="", meaning="approve")

        # Clean up: reject to unblock the thread
        bridge.reject(run_id, user_id="test", reason="cleanup")

    def test_approve_requires_meaning(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": True},
            risk_level="low",
        )

        for _ in range(100):
            try:
                info = bridge.get_current_state(run_id)
                if info["state"] == "PREVIEW_READY":
                    break
            except RunNotFoundError:
                pass
            time.sleep(0.01)

        with pytest.raises(ValueError, match="meaning is required"):
            bridge.approve(run_id, user_id="phuc", meaning="")

        bridge.reject(run_id, user_id="test", reason="cleanup")


# ---------------------------------------------------------------------------
# State Bridge: reject triggers state transition
# ---------------------------------------------------------------------------

class TestRejectTransition:
    """reject() triggers state transition from PREVIEW_READY."""

    def test_reject_from_preview_ready(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft reply"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": True},
            risk_level="low",
        )

        for _ in range(100):
            try:
                info = bridge.get_current_state(run_id)
                if info["state"] == "PREVIEW_READY":
                    break
            except RunNotFoundError:
                pass
            time.sleep(0.01)

        info = bridge.get_current_state(run_id)
        assert info["state"] == "PREVIEW_READY"

        bridge.reject(run_id, user_id="phuc", reason="not ready yet")

        for _ in range(100):
            info = bridge.get_current_state(run_id)
            if info["state"] in ("SEALED_ABORT",):
                break
            time.sleep(0.01)

        info = bridge.get_current_state(run_id)
        assert info["state"] == "SEALED_ABORT"
        assert info["can_approve"] is False
        assert info["can_reject"] is False

    def test_reject_requires_user_id(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": True},
            risk_level="low",
        )

        for _ in range(100):
            try:
                info = bridge.get_current_state(run_id)
                if info["state"] == "PREVIEW_READY":
                    break
            except RunNotFoundError:
                pass
            time.sleep(0.01)

        with pytest.raises(ValueError, match="user_id is required"):
            bridge.reject(run_id, user_id="", reason="nope")

        bridge.reject(run_id, user_id="test", reason="cleanup")

    def test_reject_requires_reason(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": True},
            risk_level="low",
        )

        for _ in range(100):
            try:
                info = bridge.get_current_state(run_id)
                if info["state"] == "PREVIEW_READY":
                    break
            except RunNotFoundError:
                pass
            time.sleep(0.01)

        with pytest.raises(ValueError, match="reason is required"):
            bridge.reject(run_id, user_id="phuc", reason="")

        bridge.reject(run_id, user_id="test", reason="cleanup")


# ---------------------------------------------------------------------------
# State Bridge: list_active_runs returns only PREVIEW_READY runs
# ---------------------------------------------------------------------------

class TestListActiveRuns:
    """list_active_runs returns only PREVIEW_READY runs."""

    def test_empty_when_no_runs(self, solace_env):
        bridge = solace_env["bridge"]
        assert bridge.list_active_runs() == []

    def test_returns_preview_ready_run(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft reply"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": True},
            risk_level="medium",
        )

        for _ in range(100):
            try:
                info = bridge.get_current_state(run_id)
                if info["state"] == "PREVIEW_READY":
                    break
            except RunNotFoundError:
                pass
            time.sleep(0.01)

        active = bridge.list_active_runs()
        assert len(active) == 1
        assert active[0]["run_id"] == run_id
        assert active[0]["app_id"] == "gmail-inbox-triage"
        assert active[0]["state"] == "PREVIEW_READY"
        assert active[0]["preview_text"] == "Draft reply"
        assert active[0]["risk_level"] == "medium"

        # Clean up
        bridge.approve(run_id, user_id="test", meaning="cleanup")

    def test_excludes_completed_runs(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )

        active = bridge.list_active_runs()
        assert len(active) == 0

    def test_excludes_blocked_runs(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": False, "reason": "blocked"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )

        active = bridge.list_active_runs()
        assert len(active) == 0


# ---------------------------------------------------------------------------
# Anti-Clippy: Never auto-approves
# ---------------------------------------------------------------------------

class TestAntiClippy:
    """The state bridge NEVER auto-approves. All approvals require explicit user action."""

    def test_no_auto_approve_flag_in_bridge(self, solace_env):
        """Bridge has no auto_approve setting or method."""
        bridge = solace_env["bridge"]
        assert not hasattr(bridge, "auto_approve")
        assert not hasattr(bridge, "set_auto_approve")

    def test_approve_rejects_empty_user_id(self, solace_env):
        """Empty user_id is rejected — no anonymous auto-approval."""
        bridge = solace_env["bridge"]
        run_id = bridge.start_run(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": True},
            risk_level="low",
        )

        for _ in range(100):
            try:
                info = bridge.get_current_state(run_id)
                if info["state"] == "PREVIEW_READY":
                    break
            except RunNotFoundError:
                pass
            time.sleep(0.01)

        with pytest.raises(ValueError):
            bridge.approve(run_id, user_id="", meaning="auto")

        bridge.reject(run_id, user_id="test", reason="cleanup")

    def test_approve_rejects_empty_meaning(self, solace_env):
        """Empty meaning is rejected — approval must have intent."""
        bridge = solace_env["bridge"]
        run_id = bridge.start_run(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": True},
            risk_level="low",
        )

        for _ in range(100):
            try:
                info = bridge.get_current_state(run_id)
                if info["state"] == "PREVIEW_READY":
                    break
            except RunNotFoundError:
                pass
            time.sleep(0.01)

        with pytest.raises(ValueError):
            bridge.approve(run_id, user_id="phuc", meaning="")

        bridge.reject(run_id, user_id="test", reason="cleanup")

    def test_approve_on_non_preview_state_raises(self, solace_env):
        """Cannot approve a run that is not in PREVIEW_READY."""
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )

        with pytest.raises(RunNotInPreviewError):
            bridge.approve(run_id, user_id="phuc", meaning="try again")

    def test_reject_on_non_preview_state_raises(self, solace_env):
        """Cannot reject a run that is not in PREVIEW_READY."""
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )

        with pytest.raises(RunNotInPreviewError):
            bridge.reject(run_id, user_id="phuc", reason="too late")


# ---------------------------------------------------------------------------
# BLOCKED state includes reason
# ---------------------------------------------------------------------------

class TestBlockedReason:
    """BLOCKED state must include the block reason."""

    def test_blocked_includes_reason_in_state(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": False, "reason": "B2 remaining limit exhausted"},
            risk_level="critical",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        info = bridge.get_current_state(run_id)
        assert info["state"] == "BLOCKED"
        assert info["block_reason"] == "B2 remaining limit exhausted"

    def test_blocked_bottom_rail_has_reason(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": False, "reason": "over daily budget"},
            risk_level="medium",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        payload = bridge.bottom_rail_payload(run_id)
        assert payload["state"] == "BLOCKED"
        assert payload["block_reason"] == "over daily budget"
        assert payload["auto_expand"] is True

    def test_blocked_interactive_includes_reason(self, solace_env):
        """When running interactively (start_run), blocked still captures reason."""
        bridge = solace_env["bridge"]
        run_id = bridge.start_run(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": False, "reason": "rate limited"},
            risk_level="high",
        )

        # BLOCKED should be reached quickly since budget fails before preview
        for _ in range(100):
            try:
                info = bridge.get_current_state(run_id)
                if info["state"] == "BLOCKED":
                    break
            except RunNotFoundError:
                pass
            time.sleep(0.01)

        info = bridge.get_current_state(run_id)
        assert info["state"] == "BLOCKED"
        assert info["block_reason"] == "rate limited"


# ---------------------------------------------------------------------------
# Top Rail Indicator
# ---------------------------------------------------------------------------

class TestTopRailIndicator:
    """top_rail_indicator returns the correct format."""

    def test_done_indicator(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        indicator = bridge.top_rail_indicator(run_id)
        assert indicator["app_name"] == "gmail-inbox-triage"
        assert indicator["state"] == "DONE"
        assert indicator["color"] == "green"
        assert indicator["label"] == "gmail-inbox-triage: DONE"

    def test_blocked_indicator(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": False, "reason": "blocked"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        indicator = bridge.top_rail_indicator(run_id)
        assert indicator["state"] == "BLOCKED"
        assert indicator["color"] == "red"
        assert "BLOCKED" in indicator["label"]

    def test_indicator_unknown_run_raises(self, solace_env):
        bridge = solace_env["bridge"]
        with pytest.raises(RunNotFoundError):
            bridge.top_rail_indicator("nonexistent-run")


# ---------------------------------------------------------------------------
# Bottom Rail Payload
# ---------------------------------------------------------------------------

class TestBottomRailPayload:
    """bottom_rail_payload returns correct display data."""

    def test_done_payload_collapses(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        payload = bridge.bottom_rail_payload(run_id)
        assert payload["state"] == "DONE"
        assert payload["auto_collapse"] is True
        assert payload["auto_expand"] is False
        assert payload["show_approve_reject"] is False

    def test_blocked_payload_expands(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": False, "reason": "blocked"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        payload = bridge.bottom_rail_payload(run_id)
        assert payload["state"] == "BLOCKED"
        assert payload["auto_expand"] is True
        assert payload["auto_collapse"] is False
        assert payload["show_approve_reject"] is False
        assert payload["block_reason"] == "blocked"

    def test_preview_ready_payload_shows_buttons(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Email draft for review"},
            execute_callback=lambda _sealed: {"status": "success"},
            budget_check=lambda _ctx: {"allowed": True},
            risk_level="medium",
        )

        for _ in range(100):
            try:
                info = bridge.get_current_state(run_id)
                if info["state"] == "PREVIEW_READY":
                    break
            except RunNotFoundError:
                pass
            time.sleep(0.01)

        payload = bridge.bottom_rail_payload(run_id)
        assert payload["state"] == "PREVIEW_READY"
        assert payload["auto_expand"] is True
        assert payload["show_approve_reject"] is True
        assert payload["preview_text"] == "Email draft for review"

        bridge.reject(run_id, user_id="test", reason="cleanup")

    def test_unknown_run_raises(self, solace_env):
        bridge = solace_env["bridge"]
        with pytest.raises(RunNotFoundError):
            bridge.bottom_rail_payload("nonexistent-run")


# ---------------------------------------------------------------------------
# State Color Map
# ---------------------------------------------------------------------------

class TestStateColorMap:
    """STATE_COLOR_MAP covers all ExecutionState values."""

    def test_all_execution_states_mapped(self):
        """Every ExecutionState should have a color in STATE_COLOR_MAP."""
        for state in ExecutionState:
            assert state in STATE_COLOR_MAP, f"Missing color for {state.value}"

    def test_done_is_green(self):
        assert STATE_COLOR_MAP[ExecutionState.DONE] == "green"

    def test_preview_ready_is_yellow(self):
        assert STATE_COLOR_MAP[ExecutionState.PREVIEW_READY] == "yellow"

    def test_blocked_is_red(self):
        assert STATE_COLOR_MAP[ExecutionState.BLOCKED] == "red"

    def test_failed_is_red(self):
        assert STATE_COLOR_MAP[ExecutionState.FAILED] == "red"

    def test_executing_is_blue(self):
        assert STATE_COLOR_MAP[ExecutionState.EXECUTING] == "blue"


# ---------------------------------------------------------------------------
# Auto-expand/collapse state sets
# ---------------------------------------------------------------------------

class TestAutoExpandCollapseSets:
    """AUTO_EXPAND_STATES and AUTO_COLLAPSE_STATES are correct."""

    def test_auto_expand_contains_preview_ready(self):
        assert ExecutionState.PREVIEW_READY in AUTO_EXPAND_STATES

    def test_auto_expand_contains_blocked(self):
        assert ExecutionState.BLOCKED in AUTO_EXPAND_STATES

    def test_auto_expand_contains_failed(self):
        assert ExecutionState.FAILED in AUTO_EXPAND_STATES

    def test_auto_collapse_contains_done(self):
        assert ExecutionState.DONE in AUTO_COLLAPSE_STATES

    def test_auto_collapse_contains_sealed_abort(self):
        assert ExecutionState.SEALED_ABORT in AUTO_COLLAPSE_STATES

    def test_no_overlap(self):
        """No state should be in both auto-expand and auto-collapse."""
        assert AUTO_EXPAND_STATES.isdisjoint(AUTO_COLLAPSE_STATES)


# ---------------------------------------------------------------------------
# Run Result Access
# ---------------------------------------------------------------------------

class TestRunResult:
    """get_run_result returns the final lifecycle result."""

    def test_completed_run_has_result(self, solace_env):
        bridge = solace_env["bridge"]
        run_id = bridge.start_run_sync(
            app_id="gmail-inbox-triage",
            trigger="manual",
            preview_callback=lambda _ctx: {"preview": "Draft"},
            execute_callback=lambda _sealed: {"status": "success"},
            risk_level="low",
            approval_decision=ApprovalDecision.APPROVE,
            user_id="phuc",
            meaning="approve",
        )
        result = bridge.get_run_result(run_id)
        assert result is not None
        assert result.state == ExecutionState.DONE
        assert result.app_id == "gmail-inbox-triage"

    def test_unknown_run_raises(self, solace_env):
        bridge = solace_env["bridge"]
        with pytest.raises(RunNotFoundError):
            bridge.get_run_result("nonexistent")
