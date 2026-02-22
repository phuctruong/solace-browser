"""
test_workflow.py — Acceptance Tests for Workflow State Machine

55+ tests covering:
  1. TestWorkflowCreation     ( 8) — create, uuid, state=PENDING, transitions
  2. TestWorkflowExecution    (10) — start→RUNNING, step execution, completion, failure
  3. TestApprovalGates        (10) — requires_approval pause, approve/reject paths
  4. TestResumeTokens         (10) — generation, validation, expiry, used, hash
  5. TestWorkflowCancel        (5) — cancel running/paused, evidence preserved
  6. TestTransitionLog         (7) — every change logged, timestamps, reasons
  7. TestWorkflowStatus        (5) — progress pct, step counts, state

Rung: 641

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_workflow.py -v -p no:httpbin
"""

from __future__ import annotations

import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Ensure src/ is on sys.path for local imports
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from workflow import (
    Workflow,
    WorkflowEngine,
    WorkflowState,
    WorkflowStep,
    ResumeToken,
    RESUME_TOKEN_TTL_SECONDS,
    STEP_ID_FORMAT,
    _compute_token_hash,
    _now_iso,
    _parse_iso,
)


# ---------------------------------------------------------------------------
# Shared helpers and fixtures
# ---------------------------------------------------------------------------

SIMPLE_STEPS = [
    {"action": "navigate", "target": "https://example.com", "value": ""},
    {"action": "click",    "target": "#submit-btn",          "value": ""},
    {"action": "type",     "target": "#email-input",         "value": "user@example.com"},
]

APPROVAL_STEPS = [
    {"action": "navigate",  "target": "https://example.com",         "value": ""},
    {"action": "post",      "target": "#publish-btn",                 "value": "", "requires_approval": True},
    {"action": "click",     "target": "#confirm",                     "value": ""},
]

MULTI_APPROVAL_STEPS = [
    {"action": "navigate",  "target": "https://example.com",         "value": ""},
    {"action": "approve",   "target": "#gate1",  "requires_approval": True,  "value": ""},
    {"action": "type",      "target": "#field",  "value": "hello"},
    {"action": "approve",   "target": "#gate2",  "requires_approval": True,  "value": ""},
    {"action": "click",     "target": "#done",   "value": ""},
]


def make_engine(secret: str = "test-secret-abc123") -> WorkflowEngine:
    return WorkflowEngine(secret=secret)


def make_workflow(
    engine: WorkflowEngine,
    steps=None,
    recipe_id: str = "recipe-test-001",
    user_id: str = "user-alice",
    token_id: str = "tok-abc",
) -> Workflow:
    if steps is None:
        steps = SIMPLE_STEPS
    return engine.create(recipe_id, steps, user_id=user_id, token_id=token_id)


# ---------------------------------------------------------------------------
# 1. TestWorkflowCreation
# ---------------------------------------------------------------------------

class TestWorkflowCreation:
    """8 tests: create workflow from steps, validate initial state."""

    def test_create_returns_workflow_instance(self):
        engine = make_engine()
        wf = make_workflow(engine)
        assert isinstance(wf, Workflow)

    def test_workflow_id_is_uuid4(self):
        engine = make_engine()
        wf = make_workflow(engine)
        # Should parse as a valid UUID without raising
        parsed = uuid.UUID(wf.workflow_id)
        assert str(parsed) == wf.workflow_id

    def test_initial_state_is_pending(self):
        engine = make_engine()
        wf = make_workflow(engine)
        assert wf.state == WorkflowState.PENDING

    def test_steps_populated_from_dicts(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        assert len(wf.steps) == 3

    def test_step_ids_are_sequential(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        ids = [s.step_id for s in wf.steps]
        assert ids == ["step_001", "step_002", "step_003"]

    def test_step_fields_mapped_correctly(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        first = wf.steps[0]
        assert first.action == "navigate"
        assert first.target == "https://example.com"
        assert first.value == ""
        assert first.requires_approval is False
        assert first.completed is False

    def test_creation_transition_logged(self):
        engine = make_engine()
        wf = make_workflow(engine)
        assert len(wf.transitions) >= 1
        assert wf.transitions[0]["to_state"] == "pending"

    def test_current_step_index_starts_at_zero(self):
        engine = make_engine()
        wf = make_workflow(engine)
        assert wf.current_step_index == 0


# ---------------------------------------------------------------------------
# 2. TestWorkflowExecution
# ---------------------------------------------------------------------------

class TestWorkflowExecution:
    """10 tests: start → RUNNING, step execute, full completion, edge cases."""

    def test_start_transitions_to_running(self):
        engine = make_engine()
        wf = make_workflow(engine)
        engine.start(wf.workflow_id)
        assert wf.state == WorkflowState.RUNNING

    def test_start_sets_started_at(self):
        engine = make_engine()
        wf = make_workflow(engine)
        engine.start(wf.workflow_id)
        assert wf.started_at != ""
        # Must be parseable as ISO8601
        _parse_iso(wf.started_at)

    def test_start_requires_pending_state(self):
        engine = make_engine()
        wf = make_workflow(engine)
        engine.start(wf.workflow_id)
        with pytest.raises(ValueError, match="PENDING"):
            engine.start(wf.workflow_id)

    def test_execute_step_advances_index(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)
        assert wf.current_step_index == 1

    def test_execute_step_marks_step_completed(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        step = engine.execute_step(wf.workflow_id)
        assert step.completed is True
        assert step.completed_at != ""

    def test_execute_all_steps_transitions_to_completed(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        for _ in SIMPLE_STEPS:
            engine.execute_step(wf.workflow_id)
        assert wf.state == WorkflowState.COMPLETED

    def test_completed_workflow_sets_completed_at(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        for _ in SIMPLE_STEPS:
            engine.execute_step(wf.workflow_id)
        assert wf.completed_at != ""
        _parse_iso(wf.completed_at)

    def test_evidence_recorded_per_step(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)
        assert len(wf.evidence) == 1
        ev = wf.evidence[0]
        assert ev["step_id"] == "step_001"
        assert ev["action"] == "navigate"

    def test_execute_step_requires_running_state(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        # PENDING state — not started yet
        with pytest.raises(ValueError):
            engine.execute_step(wf.workflow_id)

    def test_execute_step_raises_when_no_steps_remain(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        for _ in SIMPLE_STEPS:
            engine.execute_step(wf.workflow_id)
        # Workflow is now COMPLETED — cannot execute more steps
        with pytest.raises(ValueError):
            engine.execute_step(wf.workflow_id)


# ---------------------------------------------------------------------------
# 3. TestApprovalGates
# ---------------------------------------------------------------------------

class TestApprovalGates:
    """10 tests: requires_approval pauses workflow, approve/reject paths."""

    def test_approval_step_pauses_workflow(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=APPROVAL_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)   # step_001 — navigate (no approval)
        engine.execute_step(wf.workflow_id)   # step_002 — post (requires_approval)
        assert wf.state in (WorkflowState.PAUSED, WorkflowState.WAITING_APPROVAL)

    def test_approval_step_generates_resume_token(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=APPROVAL_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)   # navigate
        engine.execute_step(wf.workflow_id)   # post (approval gate)
        assert wf.resume_token is not None
        assert isinstance(wf.resume_token, ResumeToken)

    def test_approve_transitions_to_running_or_completed(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=APPROVAL_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)   # navigate
        engine.execute_step(wf.workflow_id)   # post → PAUSED
        engine.approve(wf.workflow_id)
        assert wf.state in (WorkflowState.RUNNING, WorkflowState.COMPLETED)

    def test_approve_marks_step_as_completed(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=APPROVAL_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)   # navigate
        engine.execute_step(wf.workflow_id)   # post → PAUSED
        engine.approve(wf.workflow_id)
        # step_002 should now be completed
        assert wf.steps[1].completed is True

    def test_approve_advances_step_index(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=APPROVAL_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)   # navigate (index → 1)
        engine.execute_step(wf.workflow_id)   # post → PAUSED (index stays at 1)
        engine.approve(wf.workflow_id)        # index → 2
        assert wf.current_step_index == 2

    def test_reject_transitions_to_failed(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=APPROVAL_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)   # navigate
        engine.execute_step(wf.workflow_id)   # post → PAUSED
        engine.reject(wf.workflow_id, reason="user_denied")
        assert wf.state == WorkflowState.FAILED

    def test_reject_records_reason_in_evidence(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=APPROVAL_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)
        engine.execute_step(wf.workflow_id)
        engine.reject(wf.workflow_id, reason="user_denied")
        rejection_events = [e for e in wf.evidence if e.get("event") == "rejected"]
        assert len(rejection_events) == 1
        assert rejection_events[0]["reason"] == "user_denied"

    def test_approve_from_non_paused_state_raises(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        with pytest.raises(ValueError):
            engine.approve(wf.workflow_id)

    def test_reject_from_non_paused_state_raises(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        with pytest.raises(ValueError):
            engine.reject(wf.workflow_id)

    def test_full_workflow_with_approval_completes(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=APPROVAL_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)   # navigate
        engine.execute_step(wf.workflow_id)   # post → PAUSED
        engine.approve(wf.workflow_id)        # approve post
        engine.execute_step(wf.workflow_id)   # click → COMPLETED
        assert wf.state == WorkflowState.COMPLETED


# ---------------------------------------------------------------------------
# 4. TestResumeTokens
# ---------------------------------------------------------------------------

class TestResumeTokens:
    """10 tests: token generation, validation, expiry, used, hash integrity."""

    def _pause_workflow(self, engine: WorkflowEngine, steps=None):
        """Helper: create a workflow paused at an approval step."""
        if steps is None:
            steps = APPROVAL_STEPS
        wf = make_workflow(engine, steps=steps)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)   # navigate (no approval)
        engine.execute_step(wf.workflow_id)   # approval step → PAUSED
        return wf

    def test_resume_token_generated_on_pause(self):
        engine = make_engine()
        wf = self._pause_workflow(engine)
        assert wf.resume_token is not None

    def test_resume_token_has_valid_uuid(self):
        engine = make_engine()
        wf = self._pause_workflow(engine)
        rt = wf.resume_token
        parsed = uuid.UUID(rt.token_id)
        assert str(parsed) == rt.token_id

    def test_resume_token_not_expired(self):
        engine = make_engine()
        wf = self._pause_workflow(engine)
        rt = wf.resume_token
        expires_at = _parse_iso(rt.expires_at)
        now = datetime.now(timezone.utc)
        assert expires_at > now

    def test_resume_token_expires_at_one_hour(self):
        engine = make_engine()
        wf = self._pause_workflow(engine)
        rt = wf.resume_token
        created = _parse_iso(rt.created_at)
        expires = _parse_iso(rt.expires_at)
        delta = expires - created
        # Should be very close to 3600 seconds (within 5 seconds tolerance)
        assert abs(delta.total_seconds() - RESUME_TOKEN_TTL_SECONDS) < 5

    def test_valid_token_allows_resume(self):
        engine = make_engine()
        wf = self._pause_workflow(engine)
        rt = wf.resume_token
        engine.resume(wf.workflow_id, rt.token_id)
        assert wf.state == WorkflowState.RUNNING

    def test_token_marked_used_after_resume(self):
        engine = make_engine()
        wf = self._pause_workflow(engine)
        rt = wf.resume_token
        engine.resume(wf.workflow_id, rt.token_id)
        assert rt.used is True

    def test_used_token_rejected_on_second_resume(self):
        engine = make_engine()
        wf = self._pause_workflow(engine)
        rt = wf.resume_token
        engine.resume(wf.workflow_id, rt.token_id)
        # Pause again to test second use
        engine.execute_step(wf.workflow_id)   # approval step → PAUSED again
        with pytest.raises(ValueError):
            engine.resume(wf.workflow_id, rt.token_id)   # old token is used

    def test_wrong_token_id_rejected(self):
        engine = make_engine()
        wf = self._pause_workflow(engine)
        with pytest.raises(ValueError):
            engine.resume(wf.workflow_id, str(uuid.uuid4()))

    def test_tampered_hash_rejected(self):
        engine = make_engine()
        wf = self._pause_workflow(engine)
        rt = wf.resume_token
        # Tamper with the hash
        rt.token_hash = "hmac-sha256:0000000000000000000000000000000000000000000000000000000000000000"
        with pytest.raises(ValueError):
            engine.resume(wf.workflow_id, rt.token_id)

    def test_expired_token_rejected(self):
        engine = make_engine()
        wf = self._pause_workflow(engine)
        rt = wf.resume_token
        # Force the token to appear expired by back-dating expires_at
        rt.expires_at = (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        ).isoformat()
        with pytest.raises(ValueError):
            engine.resume(wf.workflow_id, rt.token_id)


# ---------------------------------------------------------------------------
# 5. TestWorkflowCancel
# ---------------------------------------------------------------------------

class TestWorkflowCancel:
    """5 tests: cancel running/paused, evidence preserved, terminal state raises."""

    def test_cancel_running_workflow(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        engine.cancel(wf.workflow_id)
        assert wf.state == WorkflowState.CANCELLED

    def test_cancel_paused_workflow(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=APPROVAL_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)   # navigate
        engine.execute_step(wf.workflow_id)   # post → PAUSED
        engine.cancel(wf.workflow_id)
        assert wf.state == WorkflowState.CANCELLED

    def test_cancel_preserves_evidence(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)   # navigate — evidence added
        assert len(wf.evidence) == 1
        engine.cancel(wf.workflow_id)
        assert len(wf.evidence) == 1  # evidence must survive cancellation

    def test_cancel_pending_workflow(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        # PENDING → CANCELLED is valid
        engine.cancel(wf.workflow_id)
        assert wf.state == WorkflowState.CANCELLED

    def test_cancel_completed_workflow_raises(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        for _ in SIMPLE_STEPS:
            engine.execute_step(wf.workflow_id)
        assert wf.state == WorkflowState.COMPLETED
        with pytest.raises(ValueError, match="terminal"):
            engine.cancel(wf.workflow_id)


# ---------------------------------------------------------------------------
# 6. TestTransitionLog
# ---------------------------------------------------------------------------

class TestTransitionLog:
    """7 tests: every state change is logged, timestamps, reasons, append-only."""

    def test_creation_logged_as_pending(self):
        engine = make_engine()
        wf = make_workflow(engine)
        assert any(t["to_state"] == "pending" for t in wf.transitions)

    def test_start_logged_as_running(self):
        engine = make_engine()
        wf = make_workflow(engine)
        engine.start(wf.workflow_id)
        assert any(t["to_state"] == "running" for t in wf.transitions)

    def test_pause_logged_in_transitions(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=APPROVAL_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)
        engine.execute_step(wf.workflow_id)   # triggers pause
        states = [t["to_state"] for t in wf.transitions]
        assert "paused" in states or "waiting_approval" in states

    def test_transitions_have_timestamps(self):
        engine = make_engine()
        wf = make_workflow(engine)
        engine.start(wf.workflow_id)
        for t in wf.transitions:
            assert "timestamp" in t
            assert t["timestamp"] != ""
            # Must parse as ISO8601 without raising
            _parse_iso(t["timestamp"])

    def test_transitions_have_reason_field(self):
        engine = make_engine()
        wf = make_workflow(engine)
        for t in wf.transitions:
            assert "reason" in t

    def test_transitions_have_from_and_to_state(self):
        engine = make_engine()
        wf = make_workflow(engine)
        engine.start(wf.workflow_id)
        for t in wf.transitions:
            assert "from_state" in t
            assert "to_state" in t

    def test_transitions_are_append_only(self):
        """Transitions list only grows — earlier entries are never removed."""
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        first_snapshot = list(wf.transitions)
        engine.start(wf.workflow_id)
        # All original transitions still present at same positions
        for idx, original in enumerate(first_snapshot):
            assert wf.transitions[idx] == original


# ---------------------------------------------------------------------------
# 7. TestWorkflowStatus
# ---------------------------------------------------------------------------

class TestWorkflowStatus:
    """5 tests: progress percentage, step counts, state field."""

    def test_status_returns_dict(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        status = engine.get_status(wf.workflow_id)
        assert isinstance(status, dict)

    def test_progress_zero_before_any_step(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        status = engine.get_status(wf.workflow_id)
        assert status["progress_pct"] == 0

    def test_progress_increases_after_step(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        engine.execute_step(wf.workflow_id)
        status = engine.get_status(wf.workflow_id)
        assert status["progress_pct"] > 0

    def test_progress_100_when_completed(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        engine.start(wf.workflow_id)
        for _ in SIMPLE_STEPS:
            engine.execute_step(wf.workflow_id)
        status = engine.get_status(wf.workflow_id)
        assert status["progress_pct"] == 100

    def test_status_includes_required_fields(self):
        engine = make_engine()
        wf = make_workflow(engine, steps=SIMPLE_STEPS)
        status = engine.get_status(wf.workflow_id)
        required_keys = {
            "workflow_id", "recipe_id", "user_id", "state",
            "progress_pct", "current_step_index", "total_steps",
            "steps_completed", "steps_remaining", "transitions_count",
            "has_resume_token",
        }
        assert required_keys.issubset(status.keys())
