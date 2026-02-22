"""
tests/test_approvals.py — Exec Approvals + Elevated Mode Test Suite
SolaceBrowser Phase 2 (OpenClaw Feature #9)

Tests (60+ required):
  TestApprovalRequest   (8 tests)  — dataclass creation, fields, expiry, risk levels
  TestApprovalGate      (12 tests) — request/decide flow, auto-deny on TTL, batch
  TestDualControl       (8 tests)  — critical risk requires 2 approvals, partial approval
  TestElevatedSession   (8 tests)  — dataclass creation, expiry, max actions
  TestElevatedMode      (10 tests) — enter/exit, auto-exit, no nesting, scope constraint
  TestOAuth3Integration (8 tests)  — step-up required for elevated, scope validation
  TestAuditTrail        (6 tests)  — SHA256 hashes, timestamps, completeness

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_approvals.py -v -p no:httpbin

Rung: 274177
"""

import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from approvals.gate import (
    ApprovalRequest,
    ApprovalDecision,
    ApprovalGate,
    ApprovalStatus,
)
from approvals.elevated import (
    ElevatedSession,
    ElevatedMode,
    ElevatedModeError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gate(ttl_seconds: int = 300) -> ApprovalGate:
    """Return a fresh ApprovalGate with given TTL."""
    return ApprovalGate(ttl_seconds=ttl_seconds)


def _make_mode() -> ElevatedMode:
    """Return a fresh ElevatedMode manager."""
    return ElevatedMode()


def _now_iso() -> str:
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _future_iso(seconds: int = 300) -> str:
    """Return ISO8601 string that is `seconds` in the future."""
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _past_iso(seconds: int = 300) -> str:
    """Return ISO8601 string that is `seconds` in the past."""
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def _make_approval_request(
    action: str = "delete_post",
    scope: str = "linkedin.delete.post",
    risk_level: str = "high",
    description: str = "Delete a post on LinkedIn",
    evidence: dict = None,
    requested_by: str = "agent",
    expires_in: int = 300,
) -> ApprovalRequest:
    """Build an ApprovalRequest with sensible defaults."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=expires_in)
    return ApprovalRequest(
        request_id="test-req-id",
        action=action,
        scope=scope,
        risk_level=risk_level,
        description=description,
        evidence=evidence or {},
        requested_by=requested_by,
        requested_at=now.isoformat(),
        expires_at=expires.isoformat(),
    )


def _make_elevated_session(
    user_id: str = "alice@example.com",
    scopes: list = None,
    duration: int = 300,
    max_actions: int = 10,
    actions_performed: int = 0,
) -> ElevatedSession:
    """Build an ElevatedSession with sensible defaults."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=duration)
    return ElevatedSession(
        session_id="test-session-id",
        user_id=user_id,
        granted_scopes=scopes or ["linkedin.delete.post"],
        started_at=now.isoformat(),
        expires_at=expires.isoformat(),
        max_duration_seconds=duration,
        actions_performed=actions_performed,
        max_actions=max_actions,
    )


# ============================================================================
# TestApprovalRequest (8 tests)
# ============================================================================

class TestApprovalRequest:
    """Tests for the ApprovalRequest dataclass."""

    def test_create_has_all_required_fields(self):
        """ApprovalRequest must have all required fields populated."""
        req = _make_approval_request()
        assert req.request_id is not None
        assert req.action == "delete_post"
        assert req.scope == "linkedin.delete.post"
        assert req.risk_level == "high"
        assert req.description == "Delete a post on LinkedIn"
        assert isinstance(req.evidence, dict)
        assert req.requested_by == "agent"
        assert req.requested_at is not None
        assert req.expires_at is not None

    def test_risk_level_low(self):
        """ApprovalRequest accepts 'low' risk level."""
        req = _make_approval_request(risk_level="low")
        assert req.risk_level == "low"

    def test_risk_level_medium(self):
        """ApprovalRequest accepts 'medium' risk level."""
        req = _make_approval_request(risk_level="medium")
        assert req.risk_level == "medium"

    def test_risk_level_high(self):
        """ApprovalRequest accepts 'high' risk level."""
        req = _make_approval_request(risk_level="high")
        assert req.risk_level == "high"

    def test_risk_level_critical(self):
        """ApprovalRequest accepts 'critical' risk level."""
        req = _make_approval_request(risk_level="critical")
        assert req.risk_level == "critical"

    def test_not_expired_by_default(self):
        """ApprovalRequest with future expires_at should not be expired."""
        req = _make_approval_request(expires_in=300)
        assert req.is_expired() is False

    def test_expired_request(self):
        """ApprovalRequest with past expires_at should report expired."""
        req = _make_approval_request(expires_in=0)
        # expires_in=0 sets expires_at to now, which will be expired after construction
        now = datetime.now(timezone.utc)
        past = (now - timedelta(seconds=1)).isoformat()
        expired_req = ApprovalRequest(
            request_id="expired",
            action="delete_post",
            scope="linkedin.delete.post",
            risk_level="high",
            description="test",
            evidence={},
            requested_by="agent",
            requested_at=past,
            expires_at=past,
        )
        assert expired_req.is_expired() is True

    def test_to_dict_is_json_serializable(self):
        """ApprovalRequest.to_dict() must produce a JSON-serializable dict."""
        import json
        req = _make_approval_request(evidence={"post_id": "abc", "count": 1})
        d = req.to_dict()
        # Must not raise
        serialized = json.dumps(d)
        assert "delete_post" in serialized
        assert "linkedin.delete.post" in serialized


# ============================================================================
# TestApprovalGate (12 tests)
# ============================================================================

class TestApprovalGate:
    """Tests for ApprovalGate request/decide/check flow."""

    def test_request_approval_returns_request(self):
        """request_approval() should return an ApprovalRequest."""
        gate = _make_gate()
        req = gate.request_approval(
            action="send_email",
            scope="gmail.send.email",
            risk_level="high",
            evidence={"recipient": "bob@example.com"},
        )
        assert isinstance(req, ApprovalRequest)
        assert req.action == "send_email"
        assert req.scope == "gmail.send.email"

    def test_check_returns_pending_immediately(self):
        """A freshly created request should have status 'pending'."""
        gate = _make_gate()
        req = gate.request_approval(
            action="delete_post",
            scope="linkedin.delete.post",
            risk_level="high",
        )
        assert gate.check(req.request_id) == "pending"

    def test_approve_request(self):
        """Approving a request should set status to 'approved'."""
        gate = _make_gate()
        req = gate.request_approval(
            action="send_email",
            scope="gmail.send.email",
            risk_level="high",
        )
        gate.decide(req.request_id, approved=True, reason="User confirmed")
        assert gate.check(req.request_id) == "approved"

    def test_deny_request(self):
        """Denying a request should set status to 'denied'."""
        gate = _make_gate()
        req = gate.request_approval(
            action="send_email",
            scope="gmail.send.email",
            risk_level="high",
        )
        gate.decide(req.request_id, approved=False, reason="Policy violation")
        assert gate.check(req.request_id) == "denied"

    def test_decide_returns_decision_object(self):
        """decide() should return an ApprovalDecision."""
        gate = _make_gate()
        req = gate.request_approval(
            action="delete_post",
            scope="linkedin.delete.post",
            risk_level="high",
        )
        decision = gate.decide(req.request_id, approved=True, reason="OK")
        assert isinstance(decision, ApprovalDecision)
        assert decision.request_id == req.request_id
        assert decision.approved is True
        assert decision.reason == "OK"

    def test_decision_with_conditions(self):
        """decide() should record conditions on the decision."""
        gate = _make_gate()
        req = gate.request_approval(
            action="merge_pr",
            scope="github.merge.pr",
            risk_level="high",
        )
        conditions = ["CI must pass", "No unresolved comments"]
        decision = gate.decide(
            req.request_id,
            approved=True,
            reason="Reviewed",
            conditions=conditions,
        )
        assert decision.conditions == conditions

    def test_auto_deny_expired_request_on_check(self):
        """Checking a TTL-expired request should auto-deny it."""
        gate = ApprovalGate(ttl_seconds=1)
        req = gate.request_approval(
            action="delete_post",
            scope="linkedin.delete.post",
            risk_level="high",
        )
        # Wait for TTL to expire
        time.sleep(1.1)
        status = gate.check(req.request_id)
        assert status == "expired"

    def test_cannot_decide_already_approved(self):
        """Deciding on an already-approved request should raise ValueError."""
        gate = _make_gate()
        req = gate.request_approval(
            action="send_email",
            scope="gmail.send.email",
            risk_level="high",
        )
        gate.decide(req.request_id, approved=True, reason="OK")
        with pytest.raises(ValueError, match="already approved"):
            gate.decide(req.request_id, approved=False, reason="change mind")

    def test_cannot_decide_already_denied(self):
        """Deciding on an already-denied request should raise ValueError."""
        gate = _make_gate()
        req = gate.request_approval(
            action="send_email",
            scope="gmail.send.email",
            risk_level="high",
        )
        gate.decide(req.request_id, approved=False, reason="no")
        with pytest.raises(ValueError, match="already denied"):
            gate.decide(req.request_id, approved=True, reason="change mind")

    def test_invalid_request_id_raises(self):
        """Checking a non-existent request ID should raise KeyError."""
        gate = _make_gate()
        with pytest.raises(KeyError):
            gate.check("does-not-exist")

    def test_invalid_risk_level_raises(self):
        """Requesting approval with an invalid risk_level should raise ValueError."""
        gate = _make_gate()
        with pytest.raises(ValueError, match="Invalid risk_level"):
            gate.request_approval(
                action="delete_post",
                scope="linkedin.delete.post",
                risk_level="extreme",  # invalid
            )

    def test_batch_approve_multiple_requests(self):
        """batch_approve() should approve all listed requests."""
        gate = _make_gate()
        req1 = gate.request_approval(action="a1", scope="linkedin.read.feed", risk_level="low")
        req2 = gate.request_approval(action="a2", scope="gmail.read.inbox", risk_level="low")
        req3 = gate.request_approval(action="a3", scope="github.read.issues", risk_level="low")

        decisions = gate.batch_approve(
            [req1.request_id, req2.request_id, req3.request_id],
            reason="Batch approved by admin",
            decided_by="admin",
        )
        assert len(decisions) == 3
        assert all(isinstance(d, ApprovalDecision) for d in decisions)
        assert gate.check(req1.request_id) == "approved"
        assert gate.check(req2.request_id) == "approved"
        assert gate.check(req3.request_id) == "approved"


# ============================================================================
# TestDualControl (8 tests)
# ============================================================================

class TestDualControl:
    """Tests for dual-control logic on critical-risk requests."""

    def test_critical_request_stays_pending_after_one_approval(self):
        """Critical risk request must remain pending after only 1 approval."""
        gate = _make_gate()
        req = gate.request_approval(
            action="nuke_db",
            scope="github.delete.branch",
            risk_level="critical",
        )
        gate.decide(req.request_id, approved=True, reason="First approver OK", decided_by="alice")
        # Still pending — needs second approver
        assert gate.check(req.request_id) == "pending"

    def test_critical_request_approved_after_two_distinct_approvers(self):
        """Critical risk request is APPROVED only after 2 distinct approvers."""
        gate = _make_gate()
        req = gate.request_approval(
            action="nuke_db",
            scope="github.delete.branch",
            risk_level="critical",
        )
        gate.decide(req.request_id, approved=True, reason="Approver A", decided_by="alice")
        gate.decide(req.request_id, approved=True, reason="Approver B", decided_by="bob")
        assert gate.check(req.request_id) == "approved"

    def test_same_approver_twice_does_not_satisfy_dual_control(self):
        """A single approver approving twice should NOT satisfy dual-control."""
        gate = _make_gate()
        req = gate.request_approval(
            action="nuke_db",
            scope="github.delete.branch",
            risk_level="critical",
        )
        gate.decide(req.request_id, approved=True, reason="First", decided_by="alice")
        gate.decide(req.request_id, approved=True, reason="Second attempt by same", decided_by="alice")
        # Still pending — alice is only one distinct approver
        assert gate.check(req.request_id) == "pending"

    def test_critical_denied_by_first_approver_ends_immediately(self):
        """If first approver denies a critical request, it is immediately denied."""
        gate = _make_gate()
        req = gate.request_approval(
            action="nuke_db",
            scope="github.delete.branch",
            risk_level="critical",
        )
        gate.decide(req.request_id, approved=False, reason="Risk too high", decided_by="alice")
        assert gate.check(req.request_id) == "denied"

    def test_non_critical_approved_by_single_approver(self):
        """Non-critical requests are approved by a single approver."""
        gate = _make_gate()
        for risk in ("low", "medium", "high"):
            req = gate.request_approval(
                action="test_action",
                scope="linkedin.read.feed",
                risk_level=risk,
            )
            gate.decide(req.request_id, approved=True, reason="OK", decided_by="alice")
            assert gate.check(req.request_id) == "approved", f"Failed for risk={risk}"

    def test_get_decisions_records_all_partial_approvals(self):
        """get_decisions() should return all decisions for a critical request."""
        gate = _make_gate()
        req = gate.request_approval(
            action="nuke_db",
            scope="github.delete.branch",
            risk_level="critical",
        )
        gate.decide(req.request_id, approved=True, reason="OK from Alice", decided_by="alice")
        gate.decide(req.request_id, approved=True, reason="OK from Bob", decided_by="bob")
        decisions = gate.get_decisions(req.request_id)
        assert len(decisions) == 2
        approvers = {d.decided_by for d in decisions}
        assert approvers == {"alice", "bob"}

    def test_critical_three_approvers_still_works(self):
        """3 distinct approvers on a critical request still results in APPROVED."""
        gate = _make_gate()
        req = gate.request_approval(
            action="critical_action",
            scope="github.merge.pr",
            risk_level="critical",
        )
        gate.decide(req.request_id, approved=True, reason="OK", decided_by="alice")
        gate.decide(req.request_id, approved=True, reason="OK", decided_by="bob")
        # Already approved after 2; third should raise (already approved)
        with pytest.raises(ValueError, match="already approved"):
            gate.decide(req.request_id, approved=True, reason="Extra", decided_by="charlie")

    def test_batch_approve_does_not_bypass_dual_control(self):
        """batch_approve() with one decided_by should not satisfy dual-control for critical."""
        gate = _make_gate()
        req = gate.request_approval(
            action="critical_batch",
            scope="github.delete.branch",
            risk_level="critical",
        )
        # batch_approve calls decide() with a single decided_by — cannot satisfy dual-control
        gate.batch_approve([req.request_id], reason="batch", decided_by="alice")
        # Critical request still needs second approver
        assert gate.check(req.request_id) == "pending"


# ============================================================================
# TestElevatedSession (8 tests)
# ============================================================================

class TestElevatedSession:
    """Tests for the ElevatedSession dataclass."""

    def test_create_has_all_required_fields(self):
        """ElevatedSession must have all required fields populated."""
        sess = _make_elevated_session()
        assert sess.session_id == "test-session-id"
        assert sess.user_id == "alice@example.com"
        assert isinstance(sess.granted_scopes, list)
        assert sess.started_at is not None
        assert sess.expires_at is not None
        assert isinstance(sess.max_duration_seconds, int)
        assert isinstance(sess.actions_performed, int)
        assert isinstance(sess.max_actions, int)

    def test_active_session_is_active(self):
        """A newly created session with future expiry should be active."""
        sess = _make_elevated_session(duration=300)
        assert sess.is_active() is True
        assert sess.is_time_expired() is False
        assert sess.is_action_limit_exceeded() is False

    def test_expired_by_time(self):
        """Session with past expires_at should be time-expired."""
        now = datetime.now(timezone.utc)
        past = (now - timedelta(seconds=1)).isoformat()
        sess = ElevatedSession(
            session_id="s1",
            user_id="alice",
            granted_scopes=["linkedin.read.feed"],
            started_at=past,
            expires_at=past,
            max_duration_seconds=0,
            actions_performed=0,
            max_actions=10,
        )
        assert sess.is_time_expired() is True
        assert sess.is_active() is False

    def test_action_limit_exceeded(self):
        """Session with actions_performed >= max_actions should be action-exhausted."""
        sess = _make_elevated_session(actions_performed=10, max_actions=10)
        assert sess.is_action_limit_exceeded() is True
        assert sess.is_active() is False

    def test_remaining_seconds_positive_while_active(self):
        """remaining_seconds() should be positive for an active session."""
        sess = _make_elevated_session(duration=300)
        remaining = sess.remaining_seconds()
        assert remaining > 0
        assert remaining <= 300

    def test_remaining_seconds_zero_when_expired(self):
        """remaining_seconds() returns 0 for an expired session."""
        now = datetime.now(timezone.utc)
        past = (now - timedelta(seconds=60)).isoformat()
        sess = ElevatedSession(
            session_id="s2",
            user_id="bob",
            granted_scopes=["gmail.read.inbox"],
            started_at=past,
            expires_at=past,
            max_duration_seconds=1,
            actions_performed=0,
            max_actions=10,
        )
        assert sess.remaining_seconds() == 0

    def test_remaining_actions_counts_correctly(self):
        """remaining_actions() should return max_actions - actions_performed."""
        sess = _make_elevated_session(actions_performed=3, max_actions=10)
        assert sess.remaining_actions() == 7

    def test_to_dict_is_json_serializable(self):
        """ElevatedSession.to_dict() must produce a JSON-serializable dict."""
        import json
        sess = _make_elevated_session()
        d = sess.to_dict()
        serialized = json.dumps(d)
        assert "test-session-id" in serialized
        assert "alice@example.com" in serialized


# ============================================================================
# TestElevatedMode (10 tests)
# ============================================================================

class TestElevatedMode:
    """Tests for ElevatedMode enter/check/exit/record_action flow."""

    def test_enter_returns_elevated_session(self):
        """enter() should return an ElevatedSession."""
        mode = _make_mode()
        session = mode.enter(
            user_id="alice@example.com",
            scopes=["linkedin.read.feed"],
            duration_seconds=60,
            max_actions=5,
            require_step_up=False,
        )
        assert isinstance(session, ElevatedSession)
        assert session.user_id == "alice@example.com"
        assert "linkedin.read.feed" in session.granted_scopes

    def test_check_active_session_returns_correct_fields(self):
        """check() must return active=True + positive remaining for active sessions."""
        mode = _make_mode()
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=10,
            require_step_up=False,
        )
        status = mode.check(session.session_id)
        assert status["active"] is True
        assert status["remaining_seconds"] > 0
        assert status["remaining_actions"] == 10

    def test_exit_ends_session(self):
        """exit() should set the session to inactive."""
        mode = _make_mode()
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=10,
            require_step_up=False,
        )
        mode.exit(session.session_id)
        status = mode.check(session.session_id)
        assert status["active"] is False
        assert status["remaining_seconds"] == 0
        assert status["remaining_actions"] == 0

    def test_exit_returns_evidence(self):
        """exit() should return an evidence dict with action log."""
        mode = _make_mode()
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=10,
            require_step_up=False,
        )
        mode.record_action(session.session_id, action="read_feed", scope="linkedin.read.feed")
        evidence = mode.exit(session.session_id)
        assert "session_id" in evidence
        assert "user_id" in evidence
        assert "started_at" in evidence
        assert "exited_at" in evidence
        assert "actions_performed" in evidence
        assert "action_log" in evidence
        assert len(evidence["action_log"]) == 1
        assert evidence["action_log"][0]["action"] == "read_feed"

    def test_no_nesting_raises(self):
        """Entering elevated mode while already elevated should raise ElevatedModeError."""
        mode = _make_mode()
        mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=10,
            require_step_up=False,
        )
        with pytest.raises(ElevatedModeError, match="already in elevated mode"):
            mode.enter(
                user_id="alice",
                scopes=["gmail.read.inbox"],
                duration_seconds=120,
                max_actions=5,
                require_step_up=False,
            )

    def test_scope_constraint_enforced(self):
        """Requested scopes must be a subset of user's granted OAuth3 scopes."""
        mode = _make_mode()
        user_granted = ["linkedin.read.feed", "gmail.read.inbox"]
        with pytest.raises(ElevatedModeError, match="Cannot self-grant permissions"):
            mode.enter(
                user_id="alice",
                scopes=["linkedin.delete.post"],  # NOT in user_granted
                duration_seconds=60,
                max_actions=5,
                user_granted_scopes=user_granted,
                require_step_up=False,
            )

    def test_record_action_decrements_remaining_actions(self):
        """record_action() should reduce remaining_actions."""
        mode = _make_mode()
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=5,
            require_step_up=False,
        )
        mode.record_action(session.session_id, action="read_feed", scope="linkedin.read.feed")
        status = mode.check(session.session_id)
        assert status["remaining_actions"] == 4

    def test_auto_exit_on_action_limit(self):
        """Session should auto-exit after reaching max_actions."""
        mode = _make_mode()
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=2,
            require_step_up=False,
        )
        mode.record_action(session.session_id, action="a1", scope="linkedin.read.feed")
        mode.record_action(session.session_id, action="a2", scope="linkedin.read.feed")
        # Session should be auto-exited
        status = mode.check(session.session_id)
        assert status["active"] is False

    def test_is_user_elevated_reflects_state(self):
        """is_user_elevated() should track the active state correctly."""
        mode = _make_mode()
        assert mode.is_user_elevated("alice") is False
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=5,
            require_step_up=False,
        )
        assert mode.is_user_elevated("alice") is True
        mode.exit(session.session_id)
        assert mode.is_user_elevated("alice") is False

    def test_can_reenter_after_exit(self):
        """User can enter elevated mode again after explicitly exiting."""
        mode = _make_mode()
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=5,
            require_step_up=False,
        )
        mode.exit(session.session_id)
        # Should succeed — no longer elevated
        session2 = mode.enter(
            user_id="alice",
            scopes=["gmail.read.inbox"],
            duration_seconds=60,
            max_actions=3,
            require_step_up=False,
        )
        assert session2.session_id != session.session_id
        assert "gmail.read.inbox" in session2.granted_scopes


# ============================================================================
# TestOAuth3Integration (8 tests)
# ============================================================================

class TestOAuth3Integration:
    """Tests integrating approval gate + elevated mode with OAuth3 semantics."""

    def test_step_up_required_by_default(self):
        """enter() without step_up_verified=True should raise ElevatedModeError."""
        mode = _make_mode()
        with pytest.raises(ElevatedModeError, match="Step-up authentication required"):
            mode.enter(
                user_id="alice",
                scopes=["linkedin.read.feed"],
                duration_seconds=60,
                max_actions=5,
                # require_step_up defaults to True, step_up_verified defaults to False
            )

    def test_step_up_verified_allows_entry(self):
        """enter() with step_up_verified=True should succeed."""
        mode = _make_mode()
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=60,
            max_actions=5,
            step_up_verified=True,
        )
        assert session is not None
        assert session.user_id == "alice"

    def test_scope_subset_validation_allows_subset(self):
        """Requesting a proper subset of granted scopes should be allowed."""
        mode = _make_mode()
        user_granted = ["linkedin.read.feed", "linkedin.read.profile", "gmail.read.inbox"]
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],  # subset of user_granted
            duration_seconds=60,
            max_actions=5,
            user_granted_scopes=user_granted,
            require_step_up=False,
        )
        assert "linkedin.read.feed" in session.granted_scopes
        assert "linkedin.read.profile" not in session.granted_scopes

    def test_scope_subset_validation_rejects_superset(self):
        """Requesting scopes outside user's granted set must be rejected."""
        mode = _make_mode()
        user_granted = ["linkedin.read.feed"]
        with pytest.raises(ElevatedModeError, match="Cannot self-grant permissions"):
            mode.enter(
                user_id="alice",
                scopes=["linkedin.read.feed", "github.merge.pr"],  # github not granted
                duration_seconds=60,
                max_actions=5,
                user_granted_scopes=user_granted,
                require_step_up=False,
            )

    def test_approval_gate_linked_to_scope(self):
        """Approval requests should carry their OAuth3 scope."""
        gate = _make_gate()
        req = gate.request_approval(
            action="merge_pr",
            scope="github.merge.pr",
            risk_level="high",
        )
        assert req.scope == "github.merge.pr"

    def test_elevated_session_respects_max_duration_cap(self):
        """Entering elevated mode with duration > MAX should raise ValueError."""
        mode = _make_mode()
        from approvals.elevated import MAX_ELEVATED_DURATION_SECONDS
        with pytest.raises(ValueError, match="exceeds maximum"):
            mode.enter(
                user_id="alice",
                scopes=["linkedin.read.feed"],
                duration_seconds=MAX_ELEVATED_DURATION_SECONDS + 1,
                max_actions=5,
                require_step_up=False,
            )

    def test_elevated_session_respects_max_actions_cap(self):
        """Entering elevated mode with max_actions > MAX should raise ValueError."""
        mode = _make_mode()
        from approvals.elevated import MAX_ELEVATED_ACTIONS
        with pytest.raises(ValueError, match="exceeds maximum"):
            mode.enter(
                user_id="alice",
                scopes=["linkedin.read.feed"],
                duration_seconds=60,
                max_actions=MAX_ELEVATED_ACTIONS + 1,
                require_step_up=False,
            )

    def test_multiple_users_can_be_elevated_independently(self):
        """Multiple different users can each have their own elevated session."""
        mode = _make_mode()
        sess_alice = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=5,
            require_step_up=False,
        )
        sess_bob = mode.enter(
            user_id="bob",
            scopes=["gmail.read.inbox"],
            duration_seconds=120,
            max_actions=3,
            require_step_up=False,
        )
        assert sess_alice.session_id != sess_bob.session_id
        assert mode.is_user_elevated("alice") is True
        assert mode.is_user_elevated("bob") is True
        mode.exit(sess_alice.session_id)
        assert mode.is_user_elevated("alice") is False
        assert mode.is_user_elevated("bob") is True


# ============================================================================
# TestAuditTrail (6 tests)
# ============================================================================

class TestAuditTrail:
    """Tests for SHA256 integrity hash, timestamps, and completeness of audit logs."""

    def test_approval_gate_audit_entries_have_sha256_hash(self):
        """Every audit entry in ApprovalGate should have a sha256-prefixed entry_hash."""
        gate = _make_gate()
        req = gate.request_approval(
            action="delete_post",
            scope="linkedin.delete.post",
            risk_level="high",
        )
        gate.decide(req.request_id, approved=True, reason="OK")
        log = gate.get_audit_log()
        assert len(log) >= 2  # at least: request_created + decision_recorded
        for entry in log:
            assert "entry_hash" in entry
            assert entry["entry_hash"].startswith("sha256:")
            assert len(entry["entry_hash"]) > len("sha256:") + 10

    def test_approval_gate_audit_entries_have_iso8601_timestamps(self):
        """Every audit entry should have a parseable ISO8601 UTC timestamp."""
        gate = _make_gate()
        req = gate.request_approval(
            action="send_email",
            scope="gmail.send.email",
            risk_level="high",
        )
        gate.decide(req.request_id, approved=False, reason="no")
        log = gate.get_audit_log()
        for entry in log:
            assert "timestamp" in entry
            ts_str = entry["timestamp"]
            # Must parse without error
            ts_str_normalized = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(ts_str_normalized)
            # Must be UTC-aware
            assert dt.tzinfo is not None

    def test_elevated_mode_audit_entries_have_sha256_hash(self):
        """Every audit entry in ElevatedMode should have a sha256-prefixed entry_hash."""
        mode = _make_mode()
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=5,
            require_step_up=False,
        )
        mode.record_action(session.session_id, action="read", scope="linkedin.read.feed")
        mode.exit(session.session_id)
        log = mode.get_audit_log()
        assert len(log) >= 3  # started + action + exited
        for entry in log:
            assert "entry_hash" in entry
            assert entry["entry_hash"].startswith("sha256:")

    def test_audit_log_is_complete_for_full_lifecycle(self):
        """Audit log should record: created + decision + (for deny) denial."""
        gate = _make_gate()
        req = gate.request_approval(
            action="delete_post",
            scope="linkedin.delete.post",
            risk_level="high",
        )
        gate.decide(req.request_id, approved=False, reason="denied by policy")
        log = gate.get_audit_log()
        events = [entry["event"] for entry in log]
        assert "request_created" in events
        assert "decision_recorded" in events

    def test_audit_entry_hash_is_deterministic_for_same_input(self):
        """The SHA256 hash of an audit entry must be reproducible from its fields."""
        import hashlib
        import json

        gate = _make_gate()
        req = gate.request_approval(
            action="test_determinism",
            scope="linkedin.read.feed",
            risk_level="low",
        )
        log = gate.get_audit_log()
        # Verify the stored hash matches what we can compute
        entry = log[0]
        event = entry["event"]
        timestamp = entry["timestamp"]
        data = entry["data"]
        stored_hash = entry["entry_hash"]

        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        raw = f"{event}:{timestamp}:{canonical}"
        computed = "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

        assert stored_hash == computed

    def test_audit_log_preserves_order(self):
        """Audit log entries should be in insertion order."""
        gate = _make_gate()
        req = gate.request_approval(
            action="delete_branch",
            scope="github.delete.branch",
            risk_level="high",
        )
        gate.decide(req.request_id, approved=True, reason="reviewed")
        log = gate.get_audit_log()
        # First event must be request creation
        assert log[0]["event"] == "request_created"
        # Last event before approval must be decision
        decision_events = [e for e in log if e["event"] == "decision_recorded"]
        assert len(decision_events) >= 1


# ============================================================================
# Additional edge-case tests (to exceed 60 total)
# ============================================================================

class TestEdgeCases:
    """Additional edge-case and boundary tests."""

    def test_approval_request_evidence_stored_correctly(self):
        """Evidence dict is stored without modification."""
        gate = _make_gate()
        ev = {"post_id": "abc123", "platform": "linkedin", "count": 42}
        req = gate.request_approval(
            action="delete_post",
            scope="linkedin.delete.post",
            risk_level="high",
            evidence=ev,
        )
        assert req.evidence == ev

    def test_request_approval_default_requested_by(self):
        """request_approval() default requested_by is 'agent'."""
        gate = _make_gate()
        req = gate.request_approval(
            action="test",
            scope="linkedin.read.feed",
            risk_level="low",
        )
        assert req.requested_by == "agent"

    def test_request_approval_custom_requested_by(self):
        """request_approval() records custom requested_by value."""
        gate = _make_gate()
        req = gate.request_approval(
            action="test",
            scope="linkedin.read.feed",
            risk_level="low",
            requested_by="orchestrator-v2",
        )
        assert req.requested_by == "orchestrator-v2"

    def test_batch_approve_handles_invalid_id_gracefully(self):
        """batch_approve() with non-existent ID should not crash; returns failure decision."""
        gate = _make_gate()
        req = gate.request_approval(
            action="test",
            scope="linkedin.read.feed",
            risk_level="low",
        )
        decisions = gate.batch_approve(
            [req.request_id, "does-not-exist"],
            reason="Batch",
            decided_by="admin",
        )
        assert len(decisions) == 2
        # First should succeed
        assert decisions[0].approved is True
        # Second should be a failure decision
        assert decisions[1].approved is False

    def test_elevated_mode_session_id_is_uuid(self):
        """ElevatedSession session_id should be a UUID4 string."""
        import uuid
        mode = _make_mode()
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=60,
            max_actions=5,
            require_step_up=False,
        )
        # Must parse as UUID without raising
        parsed = uuid.UUID(session.session_id)
        assert str(parsed) == session.session_id

    def test_approval_request_request_id_unique(self):
        """Each approval request should get a unique UUID request_id."""
        gate = _make_gate()
        ids = set()
        for _ in range(10):
            req = gate.request_approval(
                action="test",
                scope="linkedin.read.feed",
                risk_level="low",
            )
            ids.add(req.request_id)
        assert len(ids) == 10

    def test_exit_is_idempotent(self):
        """Calling exit() twice on the same session should not raise."""
        mode = _make_mode()
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=5,
            require_step_up=False,
        )
        ev1 = mode.exit(session.session_id)
        ev2 = mode.exit(session.session_id)
        assert ev1 is not None
        assert ev2 is not None

    def test_approval_gate_auto_deny_sets_expired_not_denied(self):
        """Auto-deny on TTL expiry should set status to 'expired', not 'denied'."""
        gate = ApprovalGate(ttl_seconds=1)
        req = gate.request_approval(
            action="test",
            scope="linkedin.read.feed",
            risk_level="low",
        )
        time.sleep(1.1)
        status = gate.check(req.request_id)
        assert status == "expired"

    def test_elevated_mode_invalid_session_raises(self):
        """check() on a non-existent session should raise KeyError."""
        mode = _make_mode()
        with pytest.raises(KeyError):
            mode.check("does-not-exist")

    def test_record_action_on_inactive_session_raises(self):
        """record_action() on an exited session should raise ElevatedModeError."""
        mode = _make_mode()
        session = mode.enter(
            user_id="alice",
            scopes=["linkedin.read.feed"],
            duration_seconds=300,
            max_actions=5,
            require_step_up=False,
        )
        mode.exit(session.session_id)
        with pytest.raises(ElevatedModeError):
            mode.record_action(session.session_id, action="after_exit", scope="linkedin.read.feed")
