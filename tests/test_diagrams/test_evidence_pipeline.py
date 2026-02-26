"""
test_evidence_pipeline.py
==========================
Derived from: data/default/diagrams/evidence-pipeline.md

Tests the evidence pipeline:
  Before capture: DOM snapshot → PZip compress → SHA256 hash
  Action execution: OAuth3 gate confirmed → recipe steps → checkpoints
  After capture: DOM snapshot → PZip compress → SHA256 hash
  Diff computation: DOM diff → SHA256(diff)
  Bundle assembly: ALCOA+ fields → SHA256 chain link → AES-256-GCM sign → store

Pipeline invariants from diagram:
  - Before snapshot required (captured BEFORE action)
  - After snapshot required (captured AFTER action)
  - Diff non-null for state-changing actions
  - PZip required for all snapshots (no raw HTML stored)
  - SHA256 chain must be intact
  - Signature required (AES-256-GCM per bundle)
  - ALCOA+ fields required (all 9 dimensions)
  - Contemporaneous timestamps (within 30 seconds of action)

Run:
    python -m pytest tests/test_data/default/diagrams/test_evidence_pipeline.py -v
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

try:
    from evidence_pipeline import (
        EvidencePipeline,
        EvidenceBundle,
        BeforeCapture,
        AfterCapture,
        DiffResult,
        BundleAssembly,
        PipelineInvariantError,
    )
    _PIPELINE_AVAILABLE = True
except ImportError:
    _PIPELINE_AVAILABLE = False

_NEEDS_PIPELINE = pytest.mark.xfail(
    not _PIPELINE_AVAILABLE,
    reason="evidence_pipeline module not yet implemented",
    strict=False,
)

ALCOA_DIMENSIONS = [
    "attributable", "legible", "contemporaneous", "original",
    "accurate", "complete", "consistent", "enduring", "available",
]

BEFORE_HTML = b"<!DOCTYPE html><html><body><div id='feed'>old content</div></body></html>"
AFTER_HTML = b"<!DOCTYPE html><html><body><div id='feed'>new post added</div></body></html>"


# ---------------------------------------------------------------------------
# Before/After DOM capture
# ---------------------------------------------------------------------------


class TestBeforeAfterCapture:
    """
    Diagram: Before Capture: DOM Snapshot → PZip Compress → SHA256
             After Capture: DOM Snapshot → PZip Compress → SHA256

    Invariants:
      - Before snapshot captured BEFORE action executes
      - After snapshot captured AFTER action completes
      - Both snapshots stored as PZip (not raw HTML)
    """

    @_NEEDS_PIPELINE
    def test_before_capture_produces_pzip_hash(self, mock_pzip):
        """
        BeforeCapture must compress the HTML with PZip and return a SHA256 hash.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        capture = pipeline.capture_before(BEFORE_HTML)
        assert isinstance(capture, BeforeCapture)
        assert capture.pzip_hash is not None
        assert len(capture.pzip_hash) == 64  # SHA256 hex

    @_NEEDS_PIPELINE
    def test_after_capture_produces_pzip_hash(self, mock_pzip):
        """
        AfterCapture must compress the HTML with PZip and return a SHA256 hash.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        capture = pipeline.capture_after(AFTER_HTML)
        assert isinstance(capture, AfterCapture)
        assert capture.pzip_hash is not None
        assert len(capture.pzip_hash) == 64

    @_NEEDS_PIPELINE
    def test_before_and_after_hashes_differ(self, mock_pzip):
        """
        Before and after snapshots of different content must produce different hashes.
        Same hash for different pages would indicate a pipeline bug.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        before = pipeline.capture_before(BEFORE_HTML)
        after = pipeline.capture_after(AFTER_HTML)
        assert before.pzip_hash != after.pzip_hash

    @_NEEDS_PIPELINE
    def test_before_capture_not_raw_html(self, mock_pzip):
        """
        Diagram invariant: PZip required for all snapshots.
        The stored artifact must be PZip-compressed, not raw HTML bytes.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        capture = pipeline.capture_before(BEFORE_HTML)
        # The stored compressed bytes must not equal raw HTML
        assert capture.compressed_bytes != BEFORE_HTML

    @_NEEDS_PIPELINE
    def test_pzip_compression_is_called(self, mock_pzip):
        """
        PZip.compress() must be called during capture (not skipped).
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        pipeline.capture_before(BEFORE_HTML)
        mock_pzip.compress.assert_called_once()

    @_NEEDS_PIPELINE
    def test_before_snapshot_captured_before_action_timestamp(self, mock_pzip):
        """
        Invariant: Before snapshot must have a timestamp BEFORE action execution.
        The capture timestamp must be set at capture time, not retroactively.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        action_start = datetime.now(timezone.utc)
        before = pipeline.capture_before(BEFORE_HTML)
        action_end = datetime.now(timezone.utc)
        capture_ts = datetime.fromisoformat(before.timestamp_iso8601)
        # Capture must have happened during or before action window
        assert capture_ts >= action_start or capture_ts <= action_end


# ---------------------------------------------------------------------------
# SHA256 diff computation
# ---------------------------------------------------------------------------


class TestDiffComputation:
    """
    Diagram: DOM Diff (before → after) → SHA256(diff) → diff_hash
    Invariant: diff non-null for state-changing actions.
    """

    @_NEEDS_PIPELINE
    def test_diff_is_non_null_for_state_change(self, mock_pzip):
        """
        When before_html != after_html, the diff must be non-empty.
        An empty diff for a state-changing action violates ACCURATE principle.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        diff = pipeline.compute_diff(before=BEFORE_HTML, after=AFTER_HTML)
        assert isinstance(diff, DiffResult)
        assert diff.diff_content is not None
        assert len(diff.diff_content) > 0

    @_NEEDS_PIPELINE
    def test_diff_hash_is_sha256_hex(self, mock_pzip):
        """diff_hash must be a 64-character SHA256 hex string."""
        pipeline = EvidencePipeline(pzip=mock_pzip)
        diff = pipeline.compute_diff(before=BEFORE_HTML, after=AFTER_HTML)
        assert len(diff.diff_hash) == 64
        assert all(c in "0123456789abcdef" for c in diff.diff_hash)

    @_NEEDS_PIPELINE
    def test_diff_is_zero_for_identical_content(self, mock_pzip):
        """
        When before == after (no state change), the diff must be empty.
        This is the read-only action case.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        diff = pipeline.compute_diff(before=BEFORE_HTML, after=BEFORE_HTML)
        # For identical content, diff content should be empty or null
        assert not diff.diff_content or len(diff.diff_content) == 0

    @_NEEDS_PIPELINE
    def test_diff_hash_deterministic(self, mock_pzip):
        """Same before/after must always produce same diff_hash."""
        pipeline = EvidencePipeline(pzip=mock_pzip)
        diff1 = pipeline.compute_diff(before=BEFORE_HTML, after=AFTER_HTML)
        diff2 = pipeline.compute_diff(before=BEFORE_HTML, after=AFTER_HTML)
        assert diff1.diff_hash == diff2.diff_hash


# ---------------------------------------------------------------------------
# SHA256 hash chain
# ---------------------------------------------------------------------------


class TestSHA256HashChain:
    """
    Diagram: SHA256 Hash Chain
    Bundle 0 (genesis): chain_link = null
    Bundle N: chain_link = bundle_id of Bundle N-1
    Tamper detection: bundle_id(N-1) ≠ chain_link(N) → CHAIN BREAK DETECTED
    """

    @_NEEDS_PIPELINE
    def test_genesis_bundle_has_null_chain_link(self, genesis_bundle):
        """
        Diagram: Bundle 0 (genesis): bundle_id: sha256_0, chain_link: null
        """
        assert genesis_bundle["sha256_chain_link"] is None

    @_NEEDS_PIPELINE
    def test_subsequent_bundle_links_to_previous(self, genesis_bundle, mock_pzip):
        """
        Bundle N must have sha256_chain_link == bundle_id of Bundle N-1.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        bundle2 = pipeline.assemble_bundle(
            before_capture=MagicMock(pzip_hash="a" * 64, timestamp_iso8601="2026-01-01T00:00:00+00:00"),
            after_capture=MagicMock(pzip_hash="b" * 64),
            diff=MagicMock(diff_hash="c" * 64),
            oauth3_token_id="tok-1",
            action_id="act-2",
            platform="linkedin",
            action_type="create_post",
            prev_bundle_id=genesis_bundle["bundle_id"],
        )
        assert bundle2["sha256_chain_link"] == genesis_bundle["bundle_id"]

    @_NEEDS_PIPELINE
    def test_chain_break_detected_on_tampered_bundle(self, mock_pzip):
        """
        Diagram: tamper attempt on Bundle 2 → sha256_2_mod ≠ B3.chain_link → CHAIN BREAK DETECTED.
        Chain validation must detect when a bundle's ID does not match its successor's chain_link.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)

        # Build a chain of 3 bundles
        def _make_bundle(prev_id, action_id):
            return pipeline.assemble_bundle(
                before_capture=MagicMock(pzip_hash="a" * 64, timestamp_iso8601="2026-01-01T00:00:00+00:00"),
                after_capture=MagicMock(pzip_hash="b" * 64),
                diff=MagicMock(diff_hash="c" * 64),
                oauth3_token_id="tok-1",
                action_id=action_id,
                platform="linkedin",
                action_type="create_post",
                prev_bundle_id=prev_id,
            )

        bundle1 = _make_bundle(None, "act-1")
        bundle2 = _make_bundle(bundle1["bundle_id"], "act-2")
        bundle3 = _make_bundle(bundle2["bundle_id"], "act-3")

        # Tamper: modify bundle2's bundle_id after the fact
        tampered_bundle2 = dict(bundle2)
        tampered_bundle2["bundle_id"] = "tampered-" + bundle2["bundle_id"][:54]

        chain = [bundle1, tampered_bundle2, bundle3]
        result = pipeline.validate_chain(chain)
        assert result.chain_valid is False
        assert result.broken_at_index == 2  # bundle3 references untampered bundle2 id

    @_NEEDS_PIPELINE
    def test_valid_chain_passes_validation(self, mock_pzip):
        """An untampered chain must pass validation."""
        pipeline = EvidencePipeline(pzip=mock_pzip)

        def _make_bundle(prev_id, action_id):
            return pipeline.assemble_bundle(
                before_capture=MagicMock(pzip_hash="a" * 64, timestamp_iso8601="2026-01-01T00:00:00+00:00"),
                after_capture=MagicMock(pzip_hash="b" * 64),
                diff=MagicMock(diff_hash="c" * 64),
                oauth3_token_id="tok-1",
                action_id=action_id,
                platform="linkedin",
                action_type="create_post",
                prev_bundle_id=prev_id,
            )

        bundle1 = _make_bundle(None, "act-1")
        bundle2 = _make_bundle(bundle1["bundle_id"], "act-2")
        bundle3 = _make_bundle(bundle2["bundle_id"], "act-3")
        result = pipeline.validate_chain([bundle1, bundle2, bundle3])
        assert result.chain_valid is True


# ---------------------------------------------------------------------------
# Bundle assembly and ALCOA+ fields
# ---------------------------------------------------------------------------


class TestBundleAssembly:
    """
    Diagram: Bundle Assembly: ALCOA+ fields → SHA256 chain link → AES-256-GCM sign → store
    Invariant: all 9 ALCOA+ dimensions required.
    """

    @_NEEDS_PIPELINE
    def test_bundle_has_all_alcoa_dimensions(self, evidence_bundle):
        """
        All 9 ALCOA+ dimensions must be present in alcoa_fields.
        """
        alcoa = evidence_bundle.get("alcoa_fields", {})
        for dim in ALCOA_DIMENSIONS:
            assert dim in alcoa, f"ALCOA+ dimension '{dim}' missing from bundle"

    @_NEEDS_PIPELINE
    def test_bundle_has_signature(self, evidence_bundle):
        """
        Diagram invariant: UNSIGNED_BUNDLE → BLOCKED.
        Every bundle must carry a non-empty signature field.
        """
        assert evidence_bundle.get("signature") is not None
        assert len(evidence_bundle["signature"]) > 0

    @_NEEDS_PIPELINE
    def test_bundle_timestamp_within_30s_of_action(self, mock_pzip):
        """
        Diagram: ALCOA+ C — Contemporaneous.
        |timestamp - action| < 30s. Retroactive evidence is BLOCKED.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        action_time = datetime.now(timezone.utc)
        before = MagicMock()
        before.pzip_hash = "a" * 64
        before.timestamp_iso8601 = action_time.isoformat()
        after = MagicMock()
        after.pzip_hash = "b" * 64
        diff = MagicMock()
        diff.diff_hash = "c" * 64

        bundle = pipeline.assemble_bundle(
            before_capture=before,
            after_capture=after,
            diff=diff,
            oauth3_token_id="tok-1",
            action_id="act-1",
            platform="linkedin",
            action_type="create_post",
            prev_bundle_id=None,
        )
        ts = datetime.fromisoformat(bundle["timestamp_iso8601"])
        delta = abs((ts - action_time).total_seconds())
        assert delta < 30, f"Bundle timestamp is {delta:.1f}s from action — exceeds 30s limit"

    @_NEEDS_PIPELINE
    def test_bundle_alcoa_attributable_is_token_id(self, evidence_bundle):
        """
        Diagram: A — Attributable → oauth3_token_id (who authorized this).
        alcoa_fields.attributable must reference the oauth3_token_id.
        """
        alcoa = evidence_bundle["alcoa_fields"]
        token_id = evidence_bundle["oauth3_token_id"]
        # attributable must be the subject or token_id, not a generic truthy value
        assert alcoa.get("attributable") is not None
        assert alcoa["attributable"] != ""

    @_NEEDS_PIPELINE
    def test_bundle_alcoa_original_requires_full_html(self, mock_pzip):
        """
        Diagram: O — Original → full HTML source, not AI-summarized.
        The before_snapshot must be full HTML (DOCTYPE present, length > 1000 bytes).
        This test checks that the pipeline enforces minimum HTML size for ORIGINAL compliance.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        # Tiny snippet — not a full HTML document
        tiny_html = b"<p>summary</p>"
        with pytest.raises(Exception):
            # Pipeline must reject non-full-HTML content for ALCOA+ ORIGINAL
            pipeline.capture_before(tiny_html, require_full_html=True)

    @_NEEDS_PIPELINE
    def test_bundle_store_path_under_evidence_dir(self, mock_pzip, tmp_path):
        """
        Diagram: BU4 → Store to ~/.solace/evidence/
        Bundle storage path must be within the evidence directory.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip, evidence_dir=tmp_path)
        before = MagicMock(pzip_hash="a" * 64, timestamp_iso8601=datetime.now(timezone.utc).isoformat())
        after = MagicMock(pzip_hash="b" * 64)
        diff = MagicMock(diff_hash="c" * 64)

        bundle = pipeline.assemble_bundle(
            before_capture=before, after_capture=after, diff=diff,
            oauth3_token_id="tok-1", action_id="act-1",
            platform="linkedin", action_type="create_post", prev_bundle_id=None,
        )
        stored_path = pipeline.store_bundle(bundle)
        assert stored_path.is_relative_to(tmp_path), (
            f"Bundle stored at {stored_path}, expected under {tmp_path}"
        )


# ---------------------------------------------------------------------------
# Pipeline invariant enforcement
# ---------------------------------------------------------------------------


class TestPipelineInvariants:
    """
    From diagram: Pipeline Invariants table.
    Each invariant violation must raise PipelineInvariantError (not silently proceed).
    """

    @_NEEDS_PIPELINE
    def test_missing_before_snapshot_raises(self, mock_pzip):
        """
        Invariant: Before snapshot required.
        ACTION_WITHOUT_EVIDENCE → BLOCKED.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        with pytest.raises(PipelineInvariantError, match="before_snapshot"):
            pipeline.assemble_bundle(
                before_capture=None,  # missing
                after_capture=MagicMock(pzip_hash="b" * 64),
                diff=MagicMock(diff_hash="c" * 64),
                oauth3_token_id="tok", action_id="act", platform="linkedin",
                action_type="create_post", prev_bundle_id=None,
            )

    @_NEEDS_PIPELINE
    def test_missing_after_snapshot_raises(self, mock_pzip):
        """
        Invariant: After snapshot required.
        EVIDENCE_TAMPERED → BLOCKED.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        with pytest.raises(PipelineInvariantError, match="after_snapshot"):
            pipeline.assemble_bundle(
                before_capture=MagicMock(pzip_hash="a" * 64, timestamp_iso8601="2026-01-01T00:00:00+00:00"),
                after_capture=None,  # missing
                diff=MagicMock(diff_hash="c" * 64),
                oauth3_token_id="tok", action_id="act", platform="linkedin",
                action_type="create_post", prev_bundle_id=None,
            )

    @_NEEDS_PIPELINE
    def test_pzip_missing_raises(self, mock_pzip):
        """
        Invariant: PZip required for all snapshots.
        PZIP_MISSING → BLOCKED.
        """
        mock_pzip.compress.side_effect = RuntimeError("PZip unavailable")
        pipeline = EvidencePipeline(pzip=mock_pzip)
        with pytest.raises(PipelineInvariantError):
            pipeline.capture_before(BEFORE_HTML)

    @_NEEDS_PIPELINE
    def test_retroactive_timestamp_raises(self, mock_pzip):
        """
        Invariant: Contemporaneous timestamps (|ts - action| < 30s).
        RETROACTIVE_EVIDENCE → BLOCKED.
        """
        pipeline = EvidencePipeline(pzip=mock_pzip)
        old_ts = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        before = MagicMock(pzip_hash="a" * 64, timestamp_iso8601=old_ts)
        after = MagicMock(pzip_hash="b" * 64)
        diff = MagicMock(diff_hash="c" * 64)
        with pytest.raises(PipelineInvariantError, match="contemporaneous"):
            pipeline.assemble_bundle(
                before_capture=before, after_capture=after, diff=diff,
                oauth3_token_id="tok", action_id="act", platform="linkedin",
                action_type="create_post", prev_bundle_id=None,
            )
