"""
test_multi_layer_architecture.py
=================================
Derived from: diagrams/browser-multi-layer-architecture.md

Tests the 5-layer architecture contracts:
  Layer 1: Heartbeat — CPU, < 100ms budget
  Layer 2: Intent    — haiku LLM, < 500ms, produces classified_intent.json
  Layer 3: Recipe    — cache lookup + OAuth3 4-gate, < 1s
  Layer 4: Execute   — haiku (hit) or sonnet (miss), DOM snapshot
  Layer 5: Evidence  — PZip + SHA256 + ALCOA+, < 500ms

Each test class corresponds to one layer in the flowchart.
Tests are SKELETAL: they assert interface contracts, not implementation details.
First run MUST be RED (fail) — implementation not yet wired to this interface.

Run:
    python -m pytest tests/test_diagrams/test_multi_layer_architecture.py -v
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Attempt imports — tests that require missing modules are marked xfail
# so the file is always importable and the red gate is explicit.
# ---------------------------------------------------------------------------

try:
    from browser_layers import (
        heartbeat_check,
        HeartbeatResult,
    )
    _HEARTBEAT_AVAILABLE = True
except ImportError:
    _HEARTBEAT_AVAILABLE = False

try:
    from browser_layers import (
        classify_intent,
        ClassifiedIntent,
        compute_cache_key,
    )
    _INTENT_AVAILABLE = True
except ImportError:
    _INTENT_AVAILABLE = False

try:
    from browser_layers import (
        recipe_match,
        RecipeMatchResult,
    )
    _RECIPE_AVAILABLE = True
except ImportError:
    _RECIPE_AVAILABLE = False

try:
    from browser_layers import (
        execute_layer,
        ExecutionResult,
    )
    _EXECUTE_AVAILABLE = True
except ImportError:
    _EXECUTE_AVAILABLE = False

try:
    from browser_layers import (
        evidence_layer,
        EvidenceResult,
    )
    _EVIDENCE_AVAILABLE = True
except ImportError:
    _EVIDENCE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Layer 1: Heartbeat
# ---------------------------------------------------------------------------


class TestLayer1Heartbeat:
    """
    Layer 1: Heartbeat (CPU, < 100ms)
    Diagram states: browser_alive? → session_active? → recipe_store_ready?
    All three checks must pass before Layer 2 is entered.
    """

    @pytest.mark.xfail(not _HEARTBEAT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_heartbeat_returns_structured_result(self):
        """heartbeat_check() must return a HeartbeatResult (not raw bool)."""
        result = heartbeat_check()
        assert hasattr(result, "browser_alive")
        assert hasattr(result, "session_active")
        assert hasattr(result, "recipe_store_ready")

    @pytest.mark.xfail(not _HEARTBEAT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_heartbeat_completes_under_100ms(self):
        """
        Diagram contract: Layer 1 budget is < 100ms (CPU only).
        Heartbeat must not block on network or LLM.
        """
        start = time.monotonic()
        heartbeat_check()
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 100, f"Heartbeat took {elapsed_ms:.1f}ms, must be < 100ms"

    @pytest.mark.xfail(not _HEARTBEAT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_heartbeat_all_pass_allows_layer2(self):
        """
        When all three checks pass, the result must have an overall PASS status
        so Layer 2 can proceed.
        """
        result = heartbeat_check()
        # When browser, session, and store are all healthy, overall must be PASS
        if result.browser_alive and result.session_active and result.recipe_store_ready:
            assert result.overall == "PASS"

    @pytest.mark.xfail(not _HEARTBEAT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_heartbeat_dead_browser_blocks_layer2(self, mock_browser):
        """
        Diagram flow: if browser_alive? → NO, pipeline is blocked.
        Layer 2 must NOT be entered when browser is dead.
        """
        mock_browser.is_connected.return_value = False
        with patch("browser_layers.get_browser_page", return_value=mock_browser):
            result = heartbeat_check()
        assert result.browser_alive is False
        assert result.overall != "PASS"

    @pytest.mark.xfail(not _HEARTBEAT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_heartbeat_produces_heartbeat_json_artifact(self):
        """
        Diagram: Layer 1 output is heartbeat.json.
        The result must be serialisable to dict with expected keys.
        """
        result = heartbeat_check()
        d = result.__dict__ if hasattr(result, "__dict__") else dict(result)
        assert "browser_alive" in d
        assert "session_active" in d
        assert "recipe_store_ready" in d


# ---------------------------------------------------------------------------
# Layer 2: Intent Classification
# ---------------------------------------------------------------------------


class TestLayer2IntentClassification:
    """
    Layer 2: Intent Classification (haiku, < 500ms)
    Diagram states: Classify platform → Classify action_type → Normalize intent
                    → Compute cache key SHA256(intent+platform)
    Output: classified_intent.json
    """

    VALID_TASK_TYPES = {
        "create_post", "read_feed", "send_email", "read_inbox",
        "create_tweet", "delete_post", "execute_command", "write_file",
        "read_file", "create_issue", "search", "navigate",
    }

    VALID_PLATFORMS = {
        "linkedin", "gmail", "twitter", "reddit", "hackernews",
        "github", "notion", "substack", "machine", "tunnel",
    }

    @pytest.mark.xfail(not _INTENT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_classify_intent_returns_classified_intent(self):
        """classify_intent() must return a ClassifiedIntent object."""
        result = classify_intent("post something to LinkedIn")
        assert isinstance(result, ClassifiedIntent)

    @pytest.mark.xfail(not _INTENT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_classified_intent_has_valid_platform(self):
        """
        Layer 2 diagram: 'Classify platform' step.
        Platform must be a known, well-formed string (not empty, not wildcard).
        """
        result = classify_intent("post something to LinkedIn")
        assert result.platform in self.VALID_PLATFORMS, (
            f"Platform '{result.platform}' not in known platform list"
        )

    @pytest.mark.xfail(not _INTENT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_classified_intent_has_valid_action_type(self):
        """
        Layer 2 diagram: 'Classify action_type' step.
        action_type must be a known verb-based type (not empty string).
        """
        result = classify_intent("send an email via Gmail")
        assert result.action_type in self.VALID_TASK_TYPES, (
            f"action_type '{result.action_type}' not recognised"
        )

    @pytest.mark.xfail(not _INTENT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_cache_key_is_sha256_hex(self):
        """
        Layer 2 diagram: 'Compute cache key SHA256(intent+platform)'.
        Cache key must be a 64-character hex string (SHA256 output).
        """
        result = classify_intent("post something to LinkedIn")
        key = compute_cache_key(result)
        assert isinstance(key, str)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    @pytest.mark.xfail(not _INTENT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_cache_key_deterministic(self):
        """
        Same intent must always produce the same cache key.
        Determinism is required for cache correctness.
        """
        r1 = classify_intent("post something to LinkedIn")
        r2 = classify_intent("post something to LinkedIn")
        assert compute_cache_key(r1) == compute_cache_key(r2)

    @pytest.mark.xfail(not _INTENT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_different_platforms_produce_different_keys(self):
        """
        Diagram note: 'search for jobs' on LinkedIn ≠ 'search for jobs' on indeed.
        Platform must be part of the cache key computation.
        """
        r_linkedin = classify_intent("search for python jobs on LinkedIn")
        r_github = classify_intent("search for python jobs on GitHub")
        key_linkedin = compute_cache_key(r_linkedin)
        key_github = compute_cache_key(r_github)
        assert key_linkedin != key_github

    @pytest.mark.xfail(not _INTENT_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_ambiguous_intent_returns_need_info(self):
        """
        Diagram: INTENT_CLASSIFY → EXIT_NEED_INFO if classification fails (ambiguous).
        Ambiguous inputs must not produce a confident wrong answer.
        """
        result = classify_intent("")
        # Either raises or returns a need_info status — must NOT return a valid platform
        if hasattr(result, "status"):
            assert result.status == "NEED_INFO"
        else:
            pytest.fail("Empty intent must not silently produce a ClassifiedIntent")


# ---------------------------------------------------------------------------
# Layer 3: Recipe Match
# ---------------------------------------------------------------------------


class TestLayer3RecipeMatch:
    """
    Layer 3: Recipe Match (haiku, < 1s)
    Diagram states: Cache lookup → Hit? → Load recipe.json | OAuth3 4-gate check
    Output: recipe.json (hit) or cold_miss signal (miss)
    """

    @pytest.mark.xfail(not _RECIPE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_cache_hit_returns_recipe(self, recipe_store, recipe_cache_key, minimal_recipe):
        """
        Diagram: Cache lookup → Hit → Load recipe.json.
        A hit must return the stored recipe, not None.
        """
        result = recipe_match(recipe_cache_key, cache=recipe_store)
        assert result.hit is True
        assert result.recipe is not None
        assert result.recipe["recipe_id"] == minimal_recipe["recipe_id"]

    @pytest.mark.xfail(not _RECIPE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_cache_miss_returns_miss_signal(self):
        """
        Diagram: Cache lookup → Miss.
        Unknown key must return a miss result, not raise an exception.
        """
        result = recipe_match("unknown-sha256-key", cache={})
        assert result.hit is False
        assert result.recipe is None

    @pytest.mark.xfail(not _RECIPE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_cache_hit_includes_cache_key(self, recipe_store, recipe_cache_key):
        """
        The result must carry the cache_key that produced the hit
        for downstream traceability.
        """
        result = recipe_match(recipe_cache_key, cache=recipe_store)
        assert result.cache_key == recipe_cache_key

    @pytest.mark.xfail(not _RECIPE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_recipe_has_required_closure_fields(self, recipe_store, recipe_cache_key):
        """
        Diagram note: recipe must have max_steps and timeout_ms (CLOSURE fields).
        A recipe without these is a SCOPELESS_RECIPE (forbidden state).
        """
        result = recipe_match(recipe_cache_key, cache=recipe_store)
        assert result.hit is True
        recipe = result.recipe
        assert "max_steps" in recipe, "max_steps required for CLOSURE"
        assert "timeout_ms" in recipe, "timeout_ms required for CLOSURE"
        assert recipe["max_steps"] > 0
        assert recipe["timeout_ms"] > 0


# ---------------------------------------------------------------------------
# Layer 4: Execution
# ---------------------------------------------------------------------------


class TestLayer4Execution:
    """
    Layer 4: Execution (haiku for hit, sonnet for miss)
    Diagram: Load recipe → DOM snapshot before + after
             Dispatches haiku (cache hit) or sonnet (cold miss)
    """

    @pytest.mark.xfail(not _EXECUTE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_execution_produces_execution_trace(self, minimal_recipe, mock_browser):
        """
        Layer 4 must produce execution_trace.json after all steps complete.
        ExecutionResult must carry trace_id, recipe_id, and status.
        """
        result = execute_layer(recipe=minimal_recipe, browser=mock_browser)
        assert hasattr(result, "trace_id")
        assert hasattr(result, "recipe_id")
        assert hasattr(result, "status")
        assert result.recipe_id == minimal_recipe["recipe_id"]

    @pytest.mark.xfail(not _EXECUTE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_execution_captures_before_and_after_snapshots(self, minimal_recipe, mock_browser):
        """
        Diagram: DOM snapshot before + after execution.
        Both snapshots must be captured and non-empty.
        """
        result = execute_layer(recipe=minimal_recipe, browser=mock_browser)
        assert result.before_snapshot is not None
        assert result.after_snapshot is not None
        assert len(result.before_snapshot) > 0
        assert len(result.after_snapshot) > 0

    @pytest.mark.xfail(not _EXECUTE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_execution_respects_max_steps(self, mock_browser):
        """
        CLOSURE axiom: max_steps is a hard limit.
        Execution that exceeds max_steps must produce EXIT_BLOCKED, not run forever.
        """
        recipe_with_one_step = {
            "recipe_id": "test-closure",
            "version": "1.0.0",
            "intent": "test closure",
            "platform": "linkedin",
            "action_type": "create_post",
            "oauth3_scopes_required": [],
            "max_steps": 1,
            "timeout_ms": 5000,
            "portals": ["https://www.linkedin.com/"],
            "steps": [
                {"step_number": 1, "action": "click", "selector": "#btn", "checkpoint": False, "rollback": None, "max_retry": 1, "timeout_ms": 1000},
                {"step_number": 2, "action": "click", "selector": "#btn2", "checkpoint": False, "rollback": None, "max_retry": 1, "timeout_ms": 1000},
            ],
            "output_schema": "test",
        }
        result = execute_layer(recipe=recipe_with_one_step, browser=mock_browser)
        assert result.status in ("EXIT_BLOCKED", "BLOCKED"), (
            f"Expected EXIT_BLOCKED when max_steps exceeded, got {result.status}"
        )

    @pytest.mark.xfail(not _EXECUTE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_execution_cache_hit_uses_haiku_model(self, minimal_recipe, mock_browser):
        """
        Diagram: cache hit path uses haiku model (cheaper).
        ExecutionResult for a hit must record the model used.
        """
        result = execute_layer(recipe=minimal_recipe, browser=mock_browser, cache_hit=True)
        assert hasattr(result, "model_used")
        assert "haiku" in result.model_used.lower()


# ---------------------------------------------------------------------------
# Layer 5: Evidence
# ---------------------------------------------------------------------------


class TestLayer5Evidence:
    """
    Layer 5: Evidence (CPU + haiku, < 500ms)
    Diagram: PZip snapshot → SHA256 diff → ALCOA+ fields → Chain linked + Signed
    Output: evidence_bundle.json
    """

    @pytest.mark.xfail(not _EVIDENCE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_evidence_bundle_has_all_required_fields(self, evidence_bundle):
        """
        Layer 5 must populate all 14 required ALCOA+ fields.
        Missing any field = EVIDENCE_INCOMPLETE (forbidden state).
        """
        from tests.test_diagrams.conftest import ALCOA_REQUIRED_FIELDS
        for field in ALCOA_REQUIRED_FIELDS:
            assert field in evidence_bundle, f"Required field '{field}' missing from evidence bundle"

    @pytest.mark.xfail(not _EVIDENCE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_evidence_pipeline_produces_bundle_from_snapshots(self, mock_pzip):
        """
        Layer 5 input: before_snapshot + after_snapshot (from Layer 4).
        Output must be a valid evidence_bundle.json dict.
        """
        before_html = b"<!DOCTYPE html><html><body>before</body></html>"
        after_html = b"<!DOCTYPE html><html><body>after</body></html>"
        result = evidence_layer(
            before_snapshot=before_html,
            after_snapshot=after_html,
            action_id="test-action",
            platform="linkedin",
            action_type="create_post",
            oauth3_token_id="test-token-id",
            pzip=mock_pzip,
        )
        assert isinstance(result, dict)
        assert "bundle_id" in result
        assert "sha256_chain_link" in result

    @pytest.mark.xfail(not _EVIDENCE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_evidence_pzip_hashes_are_sha256_hex(self, evidence_bundle):
        """
        Hashes stored in the bundle must be 64-character hex strings (SHA256).
        """
        for field in ("before_snapshot_pzip_hash", "after_snapshot_pzip_hash", "diff_hash"):
            value = evidence_bundle[field]
            assert isinstance(value, str), f"{field} must be a string"
            assert len(value) == 64, f"{field} must be 64 hex chars"

    @pytest.mark.xfail(not _EVIDENCE_AVAILABLE, reason="browser_layers not implemented", strict=False)
    def test_evidence_timestamp_is_contemporaneous(self, evidence_bundle):
        """
        Diagram: ALCOA+ C — Contemporaneous.
        Timestamp must be within 30 seconds of current time.
        """
        from datetime import datetime, timezone
        ts = datetime.fromisoformat(evidence_bundle["timestamp_iso8601"])
        now = datetime.now(timezone.utc)
        delta_seconds = abs((now - ts).total_seconds())
        assert delta_seconds < 30, (
            f"Timestamp delta {delta_seconds:.1f}s exceeds 30s ALCOA+ contemporaneous limit"
        )
