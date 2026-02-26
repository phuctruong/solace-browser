"""
test_action_lifecycle.py
=========================
Derived from: data/default/diagrams/browser-action-lifecycle.md

Tests the complete browser action lifecycle FSM:
  Phase 1: INTENT — normalize → compute cache key
  Phase 2: OAUTH3 — G1 → G2 → G3 → G4 → AUTHORIZED | BLOCKED_AUTH
  Phase 3: RECIPE — CACHE_HIT | CACHE_MISS → BUILD_RECIPE
  Phase 4: EXECUTE — BEFORE_SNAPSHOT → STEP_EXECUTE → CHECKPOINT
                    → AFTER_SNAPSHOT
  Phase 5: EVIDENCE — DIFF → PZIP → CHAIN → SIGN → STORE
  Phase 6: REPLAY — bundle is replay-ready (capability check)

Required artifacts per lifecycle run (from diagram manifest):
  classified_intent.json    — Phase 1
  gate_audit.json           — Phase 2 (all 4 gates)
  recipe.json               — Phase 3
  execution_trace.json      — Phase 4
  before_snapshot.pzip      — Phase 4/5 boundary
  after_snapshot.pzip       — Phase 4/5 boundary
  evidence_bundle.json      — Phase 5

Run:
    python -m pytest tests/test_data/default/diagrams/test_action_lifecycle.py -v
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch, call

import pytest

try:
    from action_lifecycle import (
        ActionLifecycle,
        LifecycleResult,
        LifecycleArtifacts,
        LifecyclePhase,
        PhaseResult,
    )
    _LIFECYCLE_AVAILABLE = True
except ImportError:
    _LIFECYCLE_AVAILABLE = False

_NEEDS_LIFECYCLE = pytest.mark.xfail(
    not _LIFECYCLE_AVAILABLE,
    reason="action_lifecycle module not yet implemented",
    strict=False,
)

REQUIRED_ARTIFACTS = [
    "classified_intent",
    "gate_audit",
    "recipe",
    "execution_trace",
    "before_snapshot_pzip",
    "after_snapshot_pzip",
    "evidence_bundle",
]


# ---------------------------------------------------------------------------
# Phase 1: INTENT
# ---------------------------------------------------------------------------


class TestPhase1Intent:
    """
    Diagram Phase 1: INTENT CLASSIFICATION
    States: INTENT → NORMALIZE → CACHE_KEY
    Output: classified_intent.json
    """

    @_NEEDS_LIFECYCLE
    def test_phase1_produces_classified_intent_artifact(self, minimal_recipe):
        """
        Phase 1 must emit classified_intent.json.
        Missing this artifact = incomplete lifecycle.
        """
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=MagicMock(),
        )
        phase_result = lifecycle.run_phase1(intent="post to LinkedIn")
        assert phase_result.artifact is not None
        artifact = phase_result.artifact
        assert "platform" in artifact
        assert "action_type" in artifact
        assert "cache_key" in artifact

    @_NEEDS_LIFECYCLE
    def test_phase1_cache_key_is_sha256(self):
        """
        Diagram: CACHE_KEY = SHA256(normalized intent + platform).
        Cache key must be a 64-char hex string.
        """
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=MagicMock(),
        )
        phase_result = lifecycle.run_phase1(intent="post to LinkedIn")
        cache_key = phase_result.artifact["cache_key"]
        assert len(cache_key) == 64
        assert all(c in "0123456789abcdef" for c in cache_key)


# ---------------------------------------------------------------------------
# Phase 2: OAUTH3
# ---------------------------------------------------------------------------


class TestPhase2OAuth3:
    """
    Diagram Phase 2: OAUTH3 AUTHORIZATION
    States: G1 → G2 → G3 → G4 → AUTHORIZED | BLOCKED_AUTH
    Output: gate_audit.json (all 4 gates)
    """

    @_NEEDS_LIFECYCLE
    def test_phase2_produces_gate_audit_artifact(self, valid_oauth3_token):
        """
        Phase 2 must emit gate_audit.json with all 4 gate results.
        """
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=MagicMock(),
        )
        phase_result = lifecycle.run_phase2(
            token=valid_oauth3_token,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        artifact = phase_result.artifact
        assert "g1_token_exists" in artifact
        assert "g2_not_expired" in artifact
        assert "g3_scope_present" in artifact
        assert "g4_step_up_satisfied" in artifact or "g4_result" in artifact

    @_NEEDS_LIFECYCLE
    def test_phase2_blocked_auth_stops_lifecycle(self, expired_oauth3_token):
        """
        Diagram: any gate failure → BLOCKED_AUTH → [*] (exit).
        An expired token must produce BLOCKED_AUTH, not continue to Phase 3.
        """
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=MagicMock(),
        )
        phase_result = lifecycle.run_phase2(
            token=expired_oauth3_token,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        assert phase_result.status == "BLOCKED_AUTH"
        assert not phase_result.can_continue

    @_NEEDS_LIFECYCLE
    def test_phase2_gate_audit_includes_timestamp(self, valid_oauth3_token):
        """
        gate_audit.json must carry a timestamp (ALCOA+ audit requirement).
        """
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=MagicMock(),
        )
        phase_result = lifecycle.run_phase2(
            token=valid_oauth3_token,
            required_scope="linkedin.read.feed",
            is_destructive=False,
        )
        artifact = phase_result.artifact
        assert "timestamp_iso8601" in artifact or "timestamp" in artifact


# ---------------------------------------------------------------------------
# Phase 3: RECIPE
# ---------------------------------------------------------------------------


class TestPhase3Recipe:
    """
    Diagram Phase 3: RECIPE MATCH
    States: AUTHORIZED → CACHE_HIT | CACHE_MISS → BUILD_RECIPE
    Output: recipe.json (hit or built)
    """

    @_NEEDS_LIFECYCLE
    def test_phase3_cache_hit_produces_recipe_artifact(
        self, recipe_store, recipe_cache_key, minimal_recipe
    ):
        """
        Cache hit path must produce recipe.json from the cache.
        """
        lifecycle = ActionLifecycle(
            recipe_cache=recipe_store, llm=MagicMock(), browser=MagicMock(),
        )
        phase_result = lifecycle.run_phase3(cache_key=recipe_cache_key)
        assert phase_result.cache_hit is True
        assert phase_result.artifact is not None
        assert phase_result.artifact["recipe_id"] == minimal_recipe["recipe_id"]

    @_NEEDS_LIFECYCLE
    def test_phase3_cache_miss_builds_recipe(self):
        """
        Cache miss must trigger BUILD_RECIPE (dispatch recipe-builder).
        """
        mock_llm = MagicMock(return_value=_recipe_json())
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=mock_llm, browser=MagicMock(),
        )
        phase_result = lifecycle.run_phase3(
            cache_key="unknown-key",
            intent="post to LinkedIn",
            platform="linkedin",
            action_type="create_post",
        )
        assert phase_result.cache_hit is False
        mock_llm.assert_called()
        assert phase_result.artifact is not None


# ---------------------------------------------------------------------------
# Phase 4: EXECUTE
# ---------------------------------------------------------------------------


class TestPhase4Execute:
    """
    Diagram Phase 4: EXECUTION
    States: BEFORE_SNAPSHOT → STEP_EXECUTE → CHECKPOINT
            → AFTER_SNAPSHOT (all complete)
            | ROLLBACK → BLOCKED_EXEC (checkpoint fail)
    Output: execution_trace.json, before_snapshot.pzip, after_snapshot.pzip
    """

    @_NEEDS_LIFECYCLE
    def test_phase4_captures_before_and_after_snapshots(
        self, minimal_recipe, mock_browser, mock_pzip
    ):
        """
        Phase 4 must capture DOM snapshots before and after execution.
        Both must be non-empty bytes (PZip-compressed).
        """
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=mock_browser, pzip=mock_pzip,
        )
        phase_result = lifecycle.run_phase4(recipe=minimal_recipe)
        assert phase_result.before_snapshot_pzip is not None
        assert phase_result.after_snapshot_pzip is not None
        assert len(phase_result.before_snapshot_pzip) > 0
        assert len(phase_result.after_snapshot_pzip) > 0

    @_NEEDS_LIFECYCLE
    def test_phase4_produces_execution_trace_artifact(
        self, minimal_recipe, mock_browser, mock_pzip
    ):
        """
        Phase 4 must produce execution_trace.json with step-by-step results.
        """
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=mock_browser, pzip=mock_pzip,
        )
        phase_result = lifecycle.run_phase4(recipe=minimal_recipe)
        trace = phase_result.artifact
        assert trace is not None
        assert "trace_id" in trace
        assert "steps_executed" in trace
        assert "status" in trace

    @_NEEDS_LIFECYCLE
    def test_phase4_rollback_on_checkpoint_failure(self, mock_browser, mock_pzip):
        """
        Diagram: CHECKPOINT failed → ROLLBACK → BLOCKED_EXEC.
        A failing checkpoint must stop and rollback, not continue.
        """
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=mock_browser, pzip=mock_pzip,
        )
        bad_recipe = {
            "recipe_id": "checkpoint-fail-test",
            "version": "1.0.0",
            "intent": "test",
            "platform": "linkedin",
            "action_type": "create_post",
            "oauth3_scopes_required": [],
            "max_steps": 5,
            "timeout_ms": 10000,
            "portals": ["https://www.linkedin.com/"],
            "steps": [
                {
                    "step_number": 1,
                    "action": "click",
                    "selector": "#nonexistent",
                    "checkpoint": True,
                    "rollback": "navigate_back",
                    "max_retry": 1,
                    "timeout_ms": 1000,
                }
            ],
            "output_schema": "test",
        }
        mock_browser.click.side_effect = RuntimeError("Element not found")
        phase_result = lifecycle.run_phase4(recipe=bad_recipe)
        assert phase_result.status == "BLOCKED_EXEC"


# ---------------------------------------------------------------------------
# Phase 5: EVIDENCE
# ---------------------------------------------------------------------------


class TestPhase5Evidence:
    """
    Diagram Phase 5: EVIDENCE
    States: AFTER_SNAPSHOT → DIFF → PZIP → CHAIN → SIGN → STORE
    Output: evidence_bundle.json (ALCOA+ signed)
    """

    @_NEEDS_LIFECYCLE
    def test_phase5_produces_evidence_bundle(
        self, mock_pzip, valid_oauth3_token, genesis_bundle
    ):
        """
        Phase 5 must produce a complete evidence_bundle.json.
        """
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=MagicMock(), pzip=mock_pzip,
        )
        phase_result = lifecycle.run_phase5(
            before_snapshot=b"<!DOCTYPE html><html><body>before</body></html>",
            after_snapshot=b"<!DOCTYPE html><html><body>after</body></html>",
            action_id="test-action",
            platform="linkedin",
            action_type="create_post",
            oauth3_token_id=valid_oauth3_token["token_id"],
            prev_bundle_id=genesis_bundle["bundle_id"],
        )
        bundle = phase_result.artifact
        assert bundle is not None
        assert "bundle_id" in bundle
        assert "sha256_chain_link" in bundle
        assert bundle["sha256_chain_link"] == genesis_bundle["bundle_id"]

    @_NEEDS_LIFECYCLE
    def test_phase5_bundle_has_all_alcoa_fields(
        self, mock_pzip, valid_oauth3_token, genesis_bundle
    ):
        """
        Evidence bundle must contain all 9 ALCOA+ dimensions.
        """
        from tests.test_diagrams.conftest import ALCOA_DIMENSIONS
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=MagicMock(), pzip=mock_pzip,
        )
        phase_result = lifecycle.run_phase5(
            before_snapshot=b"<!DOCTYPE html><html><body>before</body></html>",
            after_snapshot=b"<!DOCTYPE html><html><body>after</body></html>",
            action_id="test-action",
            platform="linkedin",
            action_type="create_post",
            oauth3_token_id=valid_oauth3_token["token_id"],
            prev_bundle_id=genesis_bundle["bundle_id"],
        )
        bundle = phase_result.artifact
        alcoa = bundle.get("alcoa_fields", {})
        for dim in ALCOA_DIMENSIONS:
            assert dim in alcoa, f"ALCOA+ dimension '{dim}' missing"


# ---------------------------------------------------------------------------
# Phase 6: REPLAY capability
# ---------------------------------------------------------------------------


class TestPhase6ReplayCapability:
    """
    Diagram Phase 6: REPLAY (future capability)
    States: STORE → REPLAY_CAPABLE : bundle is replay-ready
    The replay capability is built from Phase 5 artifacts.
    This phase tests the presence of replay metadata — not actual re-execution.
    """

    @_NEEDS_LIFECYCLE
    def test_evidence_bundle_is_replay_capable(self, evidence_bundle):
        """
        A stored evidence_bundle.json must be replay-ready.
        Replay-ready = before_snapshot_pzip_hash + after_snapshot_pzip_hash
        + diff_hash + recipe_id all present.
        """
        replay_fields = [
            "before_snapshot_pzip_hash",
            "after_snapshot_pzip_hash",
            "diff_hash",
            "action_type",
            "platform",
            "oauth3_token_id",
        ]
        for field in replay_fields:
            assert field in evidence_bundle, (
                f"evidence_bundle missing replay field '{field}'"
            )

    @_NEEDS_LIFECYCLE
    def test_replay_produces_deterministic_output_for_same_seed(
        self, mock_pzip, minimal_recipe, mock_browser
    ):
        """
        Diagram: replay execution → identical output for same seed.
        Running the same recipe twice on identical DOM must produce
        the same execution_trace (same steps, same selectors).
        """
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=mock_browser, pzip=mock_pzip,
        )
        # Set deterministic mock returns
        mock_browser.content.return_value = "<!DOCTYPE html><html><body>same</body></html>"

        trace1 = lifecycle.replay_bundle(
            recipe=minimal_recipe, seed="deterministic-seed-123"
        )
        trace2 = lifecycle.replay_bundle(
            recipe=minimal_recipe, seed="deterministic-seed-123"
        )
        assert trace1.steps_executed == trace2.steps_executed
        assert trace1.status == trace2.status


# ---------------------------------------------------------------------------
# Full lifecycle artifact manifest
# ---------------------------------------------------------------------------


class TestLifecycleArtifactManifest:
    """
    Diagram: Lifecycle Artifact Manifest
    Every lifecycle execution MUST produce all 7 required artifacts.
    Missing any = incomplete lifecycle = rung target NOT achieved.
    """

    @_NEEDS_LIFECYCLE
    def test_full_lifecycle_produces_all_required_artifacts(
        self, recipe_store, recipe_cache_key, valid_oauth3_token,
        mock_browser, mock_pzip
    ):
        """
        Running the full 6-phase lifecycle must produce all 7 required artifacts.
        """
        lifecycle = ActionLifecycle(
            recipe_cache=recipe_store,
            llm=MagicMock(),
            browser=mock_browser,
            pzip=mock_pzip,
        )
        result = lifecycle.run(
            intent="post to LinkedIn",
            token=valid_oauth3_token,
            required_scope="linkedin.create_post",
        )
        assert isinstance(result, LifecycleResult)
        artifacts = result.artifacts

        for artifact_name in REQUIRED_ARTIFACTS:
            assert getattr(artifacts, artifact_name, None) is not None, (
                f"Required artifact '{artifact_name}' missing from lifecycle result"
            )

    @_NEEDS_LIFECYCLE
    def test_lifecycle_blocked_auth_has_no_execution_trace(
        self, expired_oauth3_token, mock_browser, mock_pzip
    ):
        """
        When Phase 2 produces BLOCKED_AUTH, Phases 3-5 must NOT run.
        execution_trace must be absent (None) in the result.
        """
        lifecycle = ActionLifecycle(
            recipe_cache={}, llm=MagicMock(), browser=mock_browser, pzip=mock_pzip,
        )
        result = lifecycle.run(
            intent="post to LinkedIn",
            token=expired_oauth3_token,
            required_scope="linkedin.create_post",
        )
        assert result.status == "BLOCKED_AUTH"
        assert result.artifacts.execution_trace is None

    @_NEEDS_LIFECYCLE
    def test_lifecycle_timing_cache_hit_under_7s(
        self, recipe_store, recipe_cache_key, valid_oauth3_token,
        mock_browser, mock_pzip
    ):
        """
        Diagram timing: cache hit total < 7s.
        This test uses a mock browser (no real network) to verify
        the lifecycle doesn't add unnecessary overhead.
        """
        import time
        lifecycle = ActionLifecycle(
            recipe_cache=recipe_store,
            llm=MagicMock(),
            browser=mock_browser,
            pzip=mock_pzip,
        )
        start = time.monotonic()
        result = lifecycle.run(
            intent="post to LinkedIn",
            token=valid_oauth3_token,
            required_scope="linkedin.create_post",
        )
        elapsed_s = time.monotonic() - start
        # With mocks, should complete in well under 7s
        assert elapsed_s < 7.0, (
            f"Cache-hit lifecycle took {elapsed_s:.2f}s, must be < 7s"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _recipe_json() -> str:
    import json
    return json.dumps({
        "recipe_id": str(uuid.uuid4()),
        "version": "1.0.0",
        "intent": "post to LinkedIn",
        "platform": "linkedin",
        "action_type": "create_post",
        "oauth3_scopes_required": ["linkedin.create_post"],
        "max_steps": 10,
        "timeout_ms": 30000,
        "portals": ["https://www.linkedin.com/feed/"],
        "steps": [],
        "output_schema": "post_created",
    })
