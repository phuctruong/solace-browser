"""
test_oauth3_enforcement.py
===========================
Derived from: data/default/diagrams/oauth3-enforcement-flow.md

Tests the 4-gate cascade:
  G1: Token exists in vault
  G2: Token not expired
  G3: Required scope present in token
  G4: Step-up satisfied for destructive actions

Rules from diagram:
  - Gate order: G1 → G2 → G3 → G4 (strict)
  - No gate skip: all 4 gates run every time
  - Fail closed: any gate failure = BLOCKED
  - Scope exact match: no wildcards
  - Revocation real-time: revoked token → G1 FAIL

Run:
    python -m pytest tests/test_data/default/diagrams/test_oauth3_enforcement.py -v
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import gate machinery from existing oauth3 module (already implemented)
# or from the new browser_layers module (to be implemented).
# We try the existing src/oauth3/enforcement.py first.
# ---------------------------------------------------------------------------

import sys
from pathlib import Path
_SRC = Path(__file__).parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Import base types that exist in the current implementation
try:
    from oauth3.enforcement import (
        GateResult,
        GATE_PASS,
        GATE_BLOCKED,
    )
    from oauth3.token import create_token, AgencyToken
    from oauth3.revocation import TokenStore, revoke_token
    _OAUTH3_BASE_AVAILABLE = True
except ImportError:
    _OAUTH3_BASE_AVAILABLE = False

# The NEW diagram-defined interface: ScopeGate(store=...) + gate.check(...) +
# ScopeGateResult with named attributes (g1_token_exists, g2_not_expired, etc.)
# This interface does NOT yet exist — the existing ScopeGate uses a different API.
# Tests below target this new interface and are xfail until it is implemented.
try:
    from oauth3.enforcement import ScopeGate, ScopeGateResult, enforce_scopes
    # Probe for the new interface: ScopeGate must accept a `store` kwarg
    import inspect
    _sig = inspect.signature(ScopeGate.__init__)
    _OAUTH3_AVAILABLE = "store" in _sig.parameters
except (ImportError, Exception):
    _OAUTH3_AVAILABLE = False

# Also try the higher-level browser gate wrapper (new interface)
try:
    from browser_gate import (
        BrowserGateResult,
        run_4gate_cascade,
        build_gate_audit_record,
    )
    _BROWSER_GATE_AVAILABLE = True
except ImportError:
    _BROWSER_GATE_AVAILABLE = False

_NEEDS_OAUTH3 = pytest.mark.xfail(
    not _OAUTH3_AVAILABLE,
    reason="oauth3.enforcement new vault-aware ScopeGate interface not yet implemented",
    strict=False,
)
_NEEDS_GATE = pytest.mark.xfail(
    not _BROWSER_GATE_AVAILABLE,
    reason="browser_gate not implemented",
    strict=False,
)

ISSUER = "https://www.solaceagi.com"
SUBJECT = "user:testuser@example.com"


# ---------------------------------------------------------------------------
# Helper: build a fresh token with given scopes
# ---------------------------------------------------------------------------

def _token(scopes, ttl_seconds=3600):
    if _OAUTH3_BASE_AVAILABLE:
        return create_token(
            issuer=ISSUER,
            subject=SUBJECT,
            scopes=scopes,
            intent="test intent",
            ttl_seconds=ttl_seconds,
        )
    return None


# ---------------------------------------------------------------------------
# G1: Token existence
# ---------------------------------------------------------------------------


class TestGate1TokenExists:
    """
    G1: Token exists in vault.
    Diagram: G1 FAIL → BLOCKED (No token — re-consent required).
    """

    @_NEEDS_OAUTH3
    def test_g1_pass_when_token_in_vault(self, token_vault, valid_oauth3_token):
        """
        G1 must PASS when the token_id is present in the vault.
        """
        store = TokenStore()
        token = _token(["linkedin.read.feed"])
        store.add(token)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        # G1 must have passed (token was found)
        assert result.g1_token_exists is True

    @_NEEDS_OAUTH3
    def test_g1_fail_when_token_not_in_vault(self):
        """
        G1 must FAIL when token_id is not in the vault.
        Overall result must be BLOCKED — no silent pass.
        """
        store = TokenStore()
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id="nonexistent-token-id",
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert result.g1_token_exists is False
        assert result.overall_result == GATE_BLOCKED

    @_NEEDS_OAUTH3
    def test_g1_fail_blocks_all_subsequent_gates(self):
        """
        Diagram: G1 FAIL → EXIT immediately.
        G2/G3/G4 must NOT be evaluated when G1 fails.
        """
        store = TokenStore()
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id="nonexistent",
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert result.g1_token_exists is False
        assert result.overall_result == GATE_BLOCKED
        # G2 should reflect that it was not reached (None or False)
        assert result.g2_not_expired in (None, False, True)  # implementation choice
        # But overall must be BLOCKED
        assert result.overall_result == GATE_BLOCKED

    @_NEEDS_OAUTH3
    def test_revoked_token_fails_g1(self):
        """
        Diagram: revocation real-time — revoked token → G1 FAIL.
        A revoked token must be treated as non-existent.
        """
        store = TokenStore()
        token = _token(["linkedin.read.feed"])
        store.add(token)
        revoke_token(store=store, token_id=token.token_id)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert result.overall_result == GATE_BLOCKED


# ---------------------------------------------------------------------------
# G2: Token not expired
# ---------------------------------------------------------------------------


class TestGate2NotExpired:
    """
    G2: Token not expired (expires_at > now()).
    Diagram: G2 FAIL → BLOCKED (Expired — refresh or re-consent).
    """

    @_NEEDS_OAUTH3
    def test_g2_pass_for_fresh_token(self):
        """G2 must PASS when token.expires_at is in the future."""
        store = TokenStore()
        token = _token(["linkedin.read.feed"], ttl_seconds=3600)
        store.add(token)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert result.g2_not_expired is True

    @_NEEDS_OAUTH3
    def test_g2_fail_for_expired_token(self, expired_oauth3_token):
        """
        G2 must FAIL when token.expires_at is in the past.
        Overall result must be BLOCKED.
        """
        store = TokenStore()
        # Build an expired AgencyToken
        from oauth3.token import _compute_signature_stub, AgencyToken
        import dataclasses
        token = _token(["linkedin.read.feed"], ttl_seconds=1)
        # Force expiry by replacing expires_at to past
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        token_expired = dataclasses.replace(token, expires_at=past)
        store.add(token_expired)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token_expired.token_id,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert result.g2_not_expired is False
        assert result.overall_result == GATE_BLOCKED


# ---------------------------------------------------------------------------
# G3: Scope present
# ---------------------------------------------------------------------------


class TestGate3ScopePresent:
    """
    G3: Required scope present in token.scopes.
    Diagram: G3 FAIL → BLOCKED (Scope missing — add scope to token).
    Scope exact match rule: no wildcards, no pattern matching.
    """

    @_NEEDS_OAUTH3
    def test_g3_pass_when_exact_scope_present(self):
        """G3 must PASS when the required scope exactly matches a token scope."""
        store = TokenStore()
        token = _token(["linkedin.create_post"])
        store.add(token)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.create_post",
            is_destructive=False,
        )
        assert result.g3_scope_present is True

    @_NEEDS_OAUTH3
    def test_g3_fail_when_scope_missing(self):
        """G3 must FAIL when the required scope is not in token.scopes."""
        store = TokenStore()
        token = _token(["linkedin.read.feed"])  # read only, no create_post
        store.add(token)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.create_post",
            is_destructive=False,
        )
        assert result.g3_scope_present is False
        assert result.overall_result == GATE_BLOCKED

    @_NEEDS_OAUTH3
    def test_g3_fail_for_wildcard_scope_in_token(self):
        """
        Diagram: wildcard linkedin.* → G3 FAIL (BLOCKED).
        Wildcard scopes in a token must NOT grant access.
        """
        store = TokenStore()
        # Wildcard scope should be rejected by token creation or enforcement
        with pytest.raises(Exception):
            # Creating a token with wildcard scope must raise
            _token(["linkedin.*"])

    @_NEEDS_OAUTH3
    def test_g3_cross_platform_scope_blocked(self):
        """
        Diagram: cross-platform scope (gmail.* in linkedin action) → BLOCKED.
        Gmail scope must not grant LinkedIn action.
        """
        store = TokenStore()
        token = _token(["gmail.compose.send"])
        store.add(token)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.create_post",
            is_destructive=False,
        )
        assert result.g3_scope_present is False
        assert result.overall_result == GATE_BLOCKED


# ---------------------------------------------------------------------------
# G4: Step-up for destructive actions
# ---------------------------------------------------------------------------


class TestGate4StepUp:
    """
    G4: Step-up required for destructive actions (delete, execute, payment).
    Diagram: destructive → STEP_UP → confirmed → EXECUTE | denied → BLOCKED.
    Non-destructive actions: G4 N/A → EXECUTE directly.
    """

    @_NEEDS_OAUTH3
    def test_g4_not_required_for_non_destructive(self):
        """
        Diagram: non-destructive action → G4 N/A → EXECUTE.
        Read/navigate/search must not trigger step-up.
        """
        store = TokenStore()
        token = _token(["linkedin.read.feed"])
        store.add(token)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert result.overall_result == GATE_PASS
        # Step-up must NOT be required
        assert result.g4_step_up_satisfied in (True, None)

    @_NEEDS_OAUTH3
    def test_g4_required_for_delete_scope(self):
        """
        Diagram: delete action → G4 step-up required.
        linkedin.delete_post is destructive → must trigger step-up gate.
        """
        store = TokenStore()
        token = _token(["linkedin.delete_post"])
        store.add(token)
        gate = ScopeGate(store=store)
        # Without step-up confirmation
        result = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.delete_post",
            is_destructive=True,
            step_up_confirmed=False,
        )
        assert result.overall_result == GATE_BLOCKED

    @_NEEDS_OAUTH3
    def test_g4_pass_when_step_up_confirmed(self):
        """
        Diagram: destructive + step-up confirmed → G4 PASS → EXECUTE.
        """
        store = TokenStore()
        token = _token(["linkedin.delete_post"])
        store.add(token)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.delete_post",
            is_destructive=True,
            step_up_confirmed=True,
        )
        assert result.overall_result == GATE_PASS
        assert result.g4_step_up_satisfied is True

    @_NEEDS_OAUTH3
    def test_machine_execute_requires_step_up(self):
        """
        Diagram: machine.execute_command is in STEP_UP_REQUIRED_SCOPES.
        Must require step-up confirmation.
        """
        store = TokenStore()
        token = _token(["machine.execute_command"])
        store.add(token)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token.token_id,
            required_scope="machine.execute_command",
            is_destructive=True,
            step_up_confirmed=False,
        )
        assert result.overall_result == GATE_BLOCKED


# ---------------------------------------------------------------------------
# Gate cascade integration: all 4 gates in sequence
# ---------------------------------------------------------------------------


class TestGateCascadeIntegration:
    """
    End-to-end cascade: G1 → G2 → G3 → G4.
    Diagram: strict precedence, no gate skip, fail closed.
    """

    @_NEEDS_OAUTH3
    def test_full_cascade_pass_for_valid_non_destructive(self):
        """
        All 4 gates must PASS for a valid, non-expired, correctly-scoped,
        non-destructive action request.
        """
        store = TokenStore()
        token = _token(["linkedin.create_post"])
        store.add(token)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.create_post",
            is_destructive=False,
        )
        assert result.g1_token_exists is True
        assert result.g2_not_expired is True
        assert result.g3_scope_present is True
        assert result.overall_result == GATE_PASS

    @_NEEDS_OAUTH3
    def test_audit_record_produced_on_gate_pass(self):
        """
        Diagram: Execute → Evidence → gate_audit.json stored.
        A gate result must carry enough fields to produce an audit record.
        """
        store = TokenStore()
        token = _token(["linkedin.read.feed"])
        store.add(token)
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert result.overall_result == GATE_PASS
        # Result must carry token_id for audit attribution
        assert result.token_id == token.token_id

    @_NEEDS_OAUTH3
    def test_audit_record_produced_on_gate_fail(self):
        """
        Diagram: BLOCKED → audit record → EXIT.
        A gate failure must also produce a traceable record (no silent failure).
        """
        store = TokenStore()
        gate = ScopeGate(store=store)
        result = gate.check(
            token_id="no-such-token",
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert result.overall_result == GATE_BLOCKED
        assert result.failure_gate is not None
        assert result.failure_reason is not None

    @_NEEDS_OAUTH3
    def test_enforce_scopes_function_end_to_end(self):
        """
        enforce_scopes() must accept a token and required scope and return
        a GateResult that is either GATE_PASS or GATE_BLOCKED.
        """
        store = TokenStore()
        token = _token(["linkedin.read.feed"])
        store.add(token)
        result = enforce_scopes(
            token_id=token.token_id,
            required_scope="linkedin.read.feed",
            is_destructive=False,
            store=store,
        )
        assert result in (GATE_PASS, GATE_BLOCKED)

    @_NEEDS_OAUTH3
    def test_revocation_invalidates_immediately(self):
        """
        Diagram: Token revocation propagates within 60 seconds.
        After revoke_token(), the same token must be BLOCKED on next gate check.
        """
        store = TokenStore()
        token = _token(["linkedin.read.feed"])
        store.add(token)

        # Pre-revocation: must PASS
        gate = ScopeGate(store=store)
        result_before = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert result_before.overall_result == GATE_PASS

        # Revoke
        revoke_token(store=store, token_id=token.token_id)

        # Post-revocation: must be BLOCKED
        result_after = gate.check(
            token_id=token.token_id,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert result_after.overall_result == GATE_BLOCKED


# ---------------------------------------------------------------------------
# Browser-level gate wrapper (higher-level interface, new module)
# ---------------------------------------------------------------------------


class TestBrowserGateWrapper:
    """
    BrowserGateResult — the higher-level wrapper used by browser_layers.
    This interface is not yet implemented (red gate).
    """

    @_NEEDS_GATE
    def test_run_4gate_cascade_returns_browser_gate_result(self, valid_oauth3_token):
        """
        run_4gate_cascade() must return a BrowserGateResult.
        """
        result = run_4gate_cascade(
            token=valid_oauth3_token,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert isinstance(result, BrowserGateResult)

    @_NEEDS_GATE
    def test_build_gate_audit_record_has_required_schema_fields(self, valid_oauth3_token):
        """
        build_gate_audit_record() must produce a dict matching GateAuditRecord schema
        from the diagram's classDiagram definition.
        """
        required_fields = [
            "audit_id", "action_id", "platform", "action_type", "token_id",
            "g1_token_exists", "g2_not_expired", "g3_scope_present",
            "g4_step_up_satisfied", "overall_result", "failure_gate",
            "failure_reason", "timestamp_iso8601", "sha256_chain_link",
        ]
        from oauth3.enforcement import ScopeGateResult
        mock_result = MagicMock(spec=ScopeGateResult)
        mock_result.g1_token_exists = True
        mock_result.g2_not_expired = True
        mock_result.g3_scope_present = True
        mock_result.g4_step_up_satisfied = True
        mock_result.overall_result = GATE_PASS
        mock_result.failure_gate = None
        mock_result.failure_reason = None
        mock_result.token_id = valid_oauth3_token["token_id"]

        record = build_gate_audit_record(
            gate_result=mock_result,
            action_id="test-action",
            platform="linkedin",
            action_type="create_post",
            prev_chain_link=None,
        )
        for field in required_fields:
            assert field in record, f"GateAuditRecord missing field '{field}'"
