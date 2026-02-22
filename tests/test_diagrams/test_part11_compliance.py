"""
test_part11_compliance.py
==========================
Derived from: diagrams/part11-alcoa-mapping.md

Tests 21 CFR Part 11 / ALCOA+ compliance:
  Each ALCOA+ dimension has at least one assertion
  Evidence bundle passes all 9 ALCOA+ checks
  Chain integrity verified (no missing links)
  21 CFR Part 11 section mapping validated

ALCOA+ Dimensions (9):
  A — Attributable    (oauth3_token_id identifies agent + user + consent)
  L — Legible         (PZip HTML, machine-readable, not screenshot)
  C — Contemporaneous (timestamp within 30s of action execution)
  O — Original        (full HTML, not AI-summarized)
  A — Accurate        (diff computed before → after)
  + Complete          (all 14 required fields, no null required fields)
  + Consistent        (sha256_chain_link intact)
  + Enduring          (PZip deterministic, forever replay)
  + Available         (indexed, retrievable by bundle_id < 5s)

21 CFR Part 11 Sections:
  §11.10(a) — Validation: rung-gated evidence schema
  §11.10(b) — Accurate copies: PZip decompression → HTML, bit-perfect
  §11.10(c) — Record protection: AES-256-GCM encryption
  §11.10(e) — Audit trails: execution_trace + oauth3_token_id + timestamp
  §11.50   — Electronic signatures: AES-256-GCM per bundle, chain-linked

Run:
    python -m pytest tests/test_diagrams/test_part11_compliance.py -v
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

try:
    from compliance_checker import (
        ALCOAChecker,
        ALCOACheckResult,
        Part11Checker,
        Part11CheckResult,
        ComplianceScore,
        ComplianceStatus,
        ChainValidator,
        ChainValidationResult,
    )
    _COMPLIANCE_AVAILABLE = True
except ImportError:
    _COMPLIANCE_AVAILABLE = False

_NEEDS_COMPLIANCE = pytest.mark.xfail(
    not _COMPLIANCE_AVAILABLE,
    reason="compliance_checker module not yet implemented",
    strict=False,
)

ALCOA_DIMENSIONS = [
    "attributable", "legible", "contemporaneous", "original",
    "accurate", "complete", "consistent", "enduring", "available",
]


# ---------------------------------------------------------------------------
# A — Attributable
# ---------------------------------------------------------------------------


class TestAlcoaAttributable:
    """
    A — Attributable: 'Who did what, and when?'
    Implementation: oauth3_token_id identifies agent + user + consent event.
    Gap if absent: HIGH — no audit trail.
    """

    @_NEEDS_COMPLIANCE
    def test_attributable_passes_with_token_id(self, evidence_bundle):
        """
        A bundle with a valid oauth3_token_id must pass ATTRIBUTABLE check.
        """
        checker = ALCOAChecker()
        result = checker.check_attributable(evidence_bundle)
        assert result.passed is True

    @_NEEDS_COMPLIANCE
    def test_attributable_fails_when_token_id_missing(self, evidence_bundle):
        """
        A bundle without oauth3_token_id must FAIL ATTRIBUTABLE.
        No token_id = no audit trail = CRITICAL gap.
        """
        bundle = dict(evidence_bundle)
        bundle["oauth3_token_id"] = None
        checker = ALCOAChecker()
        result = checker.check_attributable(bundle)
        assert result.passed is False
        assert "attributable" in result.failure_reason.lower()

    @_NEEDS_COMPLIANCE
    def test_attributable_token_id_must_resolve_to_consent_record(
        self, evidence_bundle
    ):
        """
        token_id must be resolvable to a consent record (not a random string).
        A dangling token_id means attribution cannot be verified.
        """
        checker = ALCOAChecker()
        # Real token_id that exists in vault
        result = checker.check_attributable(
            evidence_bundle,
            token_vault={evidence_bundle["oauth3_token_id"]: {"subject": "user:test"}},
        )
        assert result.resolvable is True


# ---------------------------------------------------------------------------
# L — Legible
# ---------------------------------------------------------------------------


class TestAlcoaLegible:
    """
    L — Legible: 'Is the record readable and permanent?'
    Implementation: PZip HTML snapshot — full page, machine-readable, deterministic.
    Gap if absent: HIGH — not legible.
    """

    @_NEEDS_COMPLIANCE
    def test_legible_passes_for_pzip_html_snapshot(self, evidence_bundle, mock_pzip):
        """
        A bundle with a valid PZip HTML before_snapshot must pass LEGIBLE.
        """
        # Simulate decompression returns full HTML
        mock_pzip.decompress.return_value = (
            b"<!DOCTYPE html><html><body>full page content</body></html>"
        )
        checker = ALCOAChecker(pzip=mock_pzip)
        result = checker.check_legible(evidence_bundle)
        assert result.passed is True

    @_NEEDS_COMPLIANCE
    def test_legible_fails_for_screenshot_type(self, evidence_bundle):
        """
        Diagram: screenshots fail LEGIBLE (pixel image, not machine-readable).
        A bundle with snapshot_type='screenshot' must FAIL LEGIBLE.
        """
        bundle = dict(evidence_bundle)
        bundle["snapshot_type"] = "screenshot"
        checker = ALCOAChecker()
        result = checker.check_legible(bundle)
        assert result.passed is False

    @_NEEDS_COMPLIANCE
    def test_legible_html_must_be_parseable(self, evidence_bundle, mock_pzip):
        """
        The decompressed HTML must be parseable (DOCTYPE present).
        A binary blob or AI summary is not legible under Part 11.
        """
        mock_pzip.decompress.return_value = b"not HTML content"
        checker = ALCOAChecker(pzip=mock_pzip)
        result = checker.check_legible(evidence_bundle)
        assert result.passed is False


# ---------------------------------------------------------------------------
# C — Contemporaneous
# ---------------------------------------------------------------------------


class TestAlcoaContemporaneous:
    """
    C — Contemporaneous: 'Was the record created at the time of action?'
    Implementation: timestamp_iso8601 captured at execution, not reconstructed.
    Verification: |timestamp - action| < 30s.
    Gap if absent: HIGH — backdated record.
    """

    @_NEEDS_COMPLIANCE
    def test_contemporaneous_passes_within_30s(self, evidence_bundle):
        """
        Bundle with timestamp within 30s of now must pass CONTEMPORANEOUS.
        """
        checker = ALCOAChecker()
        result = checker.check_contemporaneous(evidence_bundle)
        assert result.passed is True

    @_NEEDS_COMPLIANCE
    def test_contemporaneous_fails_for_backdated_timestamp(self, evidence_bundle):
        """
        Bundle with timestamp > 30s in the past must FAIL CONTEMPORANEOUS.
        RETROACTIVE_EVIDENCE → BLOCKED.
        """
        bundle = dict(evidence_bundle)
        bundle["timestamp_iso8601"] = (
            datetime.now(timezone.utc) - timedelta(minutes=5)
        ).isoformat()
        checker = ALCOAChecker()
        result = checker.check_contemporaneous(bundle)
        assert result.passed is False
        assert "contemporaneous" in result.failure_reason.lower()

    @_NEEDS_COMPLIANCE
    def test_contemporaneous_fails_for_future_timestamp(self, evidence_bundle):
        """
        A future timestamp (clock skew or fraud) must also FAIL.
        The timestamp must not be more than 60s in the future.
        """
        bundle = dict(evidence_bundle)
        bundle["timestamp_iso8601"] = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat()
        checker = ALCOAChecker()
        result = checker.check_contemporaneous(bundle)
        assert result.passed is False


# ---------------------------------------------------------------------------
# O — Original
# ---------------------------------------------------------------------------


class TestAlcoaOriginal:
    """
    O — Original: 'Is this the original record, not a copy or summary?'
    Implementation: before_snapshot (full HTML, not screenshot, not AI summary).
    Verification: HTML length > 1000 bytes, DOCTYPE present.
    Gap if absent: CRITICAL — not original.
    """

    @_NEEDS_COMPLIANCE
    def test_original_passes_for_full_html(self, evidence_bundle, mock_pzip):
        """
        Full HTML before_snapshot must pass ORIGINAL check.
        """
        full_html = b"<!DOCTYPE html><html><head><title>T</title></head><body>" + b"x" * 2000 + b"</body></html>"
        mock_pzip.decompress.return_value = full_html
        checker = ALCOAChecker(pzip=mock_pzip)
        result = checker.check_original(evidence_bundle)
        assert result.passed is True

    @_NEEDS_COMPLIANCE
    def test_original_fails_for_short_content(self, evidence_bundle, mock_pzip):
        """
        A tiny HTML snippet (< 1000 bytes) must FAIL ORIGINAL.
        Part 11 Original requires the complete record, not a fragment.
        """
        mock_pzip.decompress.return_value = b"<p>summary</p>"  # < 1000 bytes
        checker = ALCOAChecker(pzip=mock_pzip)
        result = checker.check_original(evidence_bundle)
        assert result.passed is False

    @_NEEDS_COMPLIANCE
    def test_original_fails_for_missing_doctype(self, evidence_bundle, mock_pzip):
        """
        HTML without DOCTYPE is not a full original HTML document.
        """
        mock_pzip.decompress.return_value = b"<html><body>" + b"x" * 2000 + b"</body></html>"
        checker = ALCOAChecker(pzip=mock_pzip)
        result = checker.check_original(evidence_bundle)
        assert result.passed is False


# ---------------------------------------------------------------------------
# A — Accurate
# ---------------------------------------------------------------------------


class TestAlcoaAccurate:
    """
    A — Accurate: 'Does the record reflect what actually happened?'
    Implementation: diff computed from actual before → after state change.
    Gap if absent: HIGH — accuracy unverifiable.
    """

    @_NEEDS_COMPLIANCE
    def test_accurate_passes_with_non_null_diff(self, evidence_bundle):
        """
        A bundle with a non-null diff_hash must pass ACCURATE.
        """
        checker = ALCOAChecker()
        result = checker.check_accurate(evidence_bundle)
        assert result.passed is True

    @_NEEDS_COMPLIANCE
    def test_accurate_fails_when_diff_missing_for_state_change(self, evidence_bundle):
        """
        A state-changing action (create_post) with no diff must FAIL ACCURATE.
        DIFF_SKIPPED → BLOCKED.
        """
        bundle = dict(evidence_bundle)
        bundle["diff_hash"] = None  # no diff
        bundle["action_type"] = "create_post"  # state-changing
        checker = ALCOAChecker()
        result = checker.check_accurate(bundle)
        assert result.passed is False

    @_NEEDS_COMPLIANCE
    def test_accurate_passes_null_diff_for_read_only(self, evidence_bundle):
        """
        A read-only action with null diff is acceptable (no state change).
        """
        bundle = dict(evidence_bundle)
        bundle["diff_hash"] = None
        bundle["action_type"] = "read_feed"  # read-only
        checker = ALCOAChecker()
        result = checker.check_accurate(bundle)
        # Read-only with no diff is OK
        assert result.passed is True


# ---------------------------------------------------------------------------
# + Complete
# ---------------------------------------------------------------------------


class TestAlcoaComplete:
    """
    + Complete: 'Is the entire record there?'
    Implementation: 14-field schema validation, all fields required, no null defaults.
    Gap if absent: HIGH — incomplete record.
    """

    @_NEEDS_COMPLIANCE
    def test_complete_passes_with_all_14_fields(self, evidence_bundle):
        """
        A bundle with all 14 required fields must pass COMPLETE.
        """
        checker = ALCOAChecker()
        result = checker.check_complete(evidence_bundle)
        assert result.passed is True

    @_NEEDS_COMPLIANCE
    def test_complete_fails_with_missing_required_field(self, evidence_bundle):
        """
        A bundle with any required field set to None must FAIL COMPLETE.
        No null defaults allowed.
        """
        from tests.test_diagrams.conftest import ALCOA_REQUIRED_FIELDS
        for field in ALCOA_REQUIRED_FIELDS:
            bundle = dict(evidence_bundle)
            bundle[field] = None
            checker = ALCOAChecker()
            result = checker.check_complete(bundle)
            assert result.passed is False, (
                f"Expected FAIL for null field '{field}', but COMPLETE passed"
            )

    @_NEEDS_COMPLIANCE
    def test_complete_field_count_is_14(self, evidence_bundle):
        """
        Schema must have exactly 14 required fields (as specified in diagram).
        """
        from tests.test_diagrams.conftest import ALCOA_REQUIRED_FIELDS
        assert len(ALCOA_REQUIRED_FIELDS) == 14


# ---------------------------------------------------------------------------
# + Consistent
# ---------------------------------------------------------------------------


class TestAlcoaConsistent:
    """
    + Consistent: 'Is the record consistent across time?'
    Implementation: sha256_chain_link — hash chain links all bundles.
    Gap if absent: CRITICAL — chain break.
    """

    @_NEEDS_COMPLIANCE
    def test_consistent_passes_with_intact_chain(
        self, genesis_bundle, evidence_bundle
    ):
        """
        A bundle that correctly references its predecessor must pass CONSISTENT.
        """
        # Set chain_link to genesis bundle_id
        bundle = dict(evidence_bundle)
        bundle["sha256_chain_link"] = genesis_bundle["bundle_id"]

        checker = ALCOAChecker()
        result = checker.check_consistent(
            bundle=bundle,
            prev_bundle=genesis_bundle,
        )
        assert result.passed is True

    @_NEEDS_COMPLIANCE
    def test_consistent_fails_with_broken_chain(
        self, genesis_bundle, evidence_bundle
    ):
        """
        A bundle with a wrong chain_link must FAIL CONSISTENT.
        CHAIN_BROKEN → BLOCKED.
        """
        bundle = dict(evidence_bundle)
        bundle["sha256_chain_link"] = "wrong-hash-" + "a" * 52  # incorrect

        checker = ALCOAChecker()
        result = checker.check_consistent(
            bundle=bundle,
            prev_bundle=genesis_bundle,
        )
        assert result.passed is False
        assert "chain" in result.failure_reason.lower()

    @_NEEDS_COMPLIANCE
    def test_chain_validator_detects_tampered_bundle(self, genesis_bundle, mock_pzip):
        """
        Full chain validation must detect a tampered intermediate bundle.
        """
        def _sha256(s: str) -> str:
            return hashlib.sha256(s.encode()).hexdigest()

        b1 = {
            "bundle_id": _sha256("act-1"),
            "sha256_chain_link": None,
            "action_id": "act-1",
        }
        b2 = {
            "bundle_id": _sha256("act-2"),
            "sha256_chain_link": b1["bundle_id"],
            "action_id": "act-2",
        }
        b3 = {
            "bundle_id": _sha256("act-3"),
            "sha256_chain_link": b2["bundle_id"],
            "action_id": "act-3",
        }
        # Tamper b2
        b2_tampered = dict(b2)
        b2_tampered["bundle_id"] = "tampered-" + _sha256("act-2")[:54]

        validator = ChainValidator()
        result = validator.validate([b1, b2_tampered, b3])
        assert result.chain_valid is False

    @_NEEDS_COMPLIANCE
    def test_chain_validator_passes_valid_chain(self):
        """
        An untampered chain must pass validation.
        """
        def _sha256(s: str) -> str:
            return hashlib.sha256(s.encode()).hexdigest()

        b1 = {"bundle_id": _sha256("act-1"), "sha256_chain_link": None}
        b2 = {"bundle_id": _sha256("act-2"), "sha256_chain_link": b1["bundle_id"]}
        b3 = {"bundle_id": _sha256("act-3"), "sha256_chain_link": b2["bundle_id"]}

        validator = ChainValidator()
        result = validator.validate([b1, b2, b3])
        assert result.chain_valid is True


# ---------------------------------------------------------------------------
# + Enduring
# ---------------------------------------------------------------------------


class TestAlcoaEnduring:
    """
    + Enduring: 'Can this record be retrieved forever?'
    Implementation: PZip deterministic compression — forever replay.
    pzip_hash is reproducible and verifiable.
    Gap if absent: CRITICAL — not reproducible.
    """

    @_NEEDS_COMPLIANCE
    def test_enduring_pzip_hash_is_deterministic(self, evidence_bundle, mock_pzip):
        """
        PZip hash must be deterministic: same input → same hash, always.
        This is the +Enduring ALCOA+ property.
        """
        source_html = b"<!DOCTYPE html><html><body>test</body></html>"
        hash1 = mock_pzip.hash(source_html)
        hash2 = mock_pzip.hash(source_html)
        assert hash1 == hash2, (
            "PZip hash must be deterministic — same input must produce same hash"
        )

    @_NEEDS_COMPLIANCE
    def test_enduring_pzip_hash_matches_bundle_field(
        self, evidence_bundle, mock_pzip
    ):
        """
        The before_snapshot_pzip_hash in the bundle must match
        the PZip hash computed from the stored snapshot.
        """
        checker = ALCOAChecker(pzip=mock_pzip)
        # Mock pzip to return a hash matching the bundle's field
        mock_pzip.hash.return_value = evidence_bundle["before_snapshot_pzip_hash"]
        result = checker.check_enduring(evidence_bundle)
        assert result.passed is True

    @_NEEDS_COMPLIANCE
    def test_enduring_fails_when_pzip_hash_mismatches(
        self, evidence_bundle, mock_pzip
    ):
        """
        If recomputing pzip_hash from source produces a different value,
        the record is NOT enduring (data corruption or tampering).
        """
        mock_pzip.hash.return_value = "different-hash-" + "a" * 49
        checker = ALCOAChecker(pzip=mock_pzip)
        result = checker.check_enduring(evidence_bundle)
        assert result.passed is False


# ---------------------------------------------------------------------------
# + Available
# ---------------------------------------------------------------------------


class TestAlcoaAvailable:
    """
    + Available: 'Is the record accessible when needed?'
    Implementation: Indexed evidence store — bundle_id lookup < 5 seconds.
    """

    @_NEEDS_COMPLIANCE
    def test_available_passes_for_indexed_bundle(self, evidence_bundle):
        """
        A bundle indexed in the store must pass AVAILABLE (lookup < 5s).
        """
        mock_store = MagicMock()
        mock_store.lookup.return_value = evidence_bundle
        mock_store.lookup_latency_ms.return_value = 50  # 50ms

        checker = ALCOAChecker(evidence_store=mock_store)
        result = checker.check_available(evidence_bundle)
        assert result.passed is True

    @_NEEDS_COMPLIANCE
    def test_available_fails_when_not_indexed(self, evidence_bundle):
        """
        A bundle not in the store index must FAIL AVAILABLE.
        """
        mock_store = MagicMock()
        mock_store.lookup.return_value = None

        checker = ALCOAChecker(evidence_store=mock_store)
        result = checker.check_available(evidence_bundle)
        assert result.passed is False


# ---------------------------------------------------------------------------
# Full ALCOA+ bundle check (all 9 dimensions in one pass)
# ---------------------------------------------------------------------------


class TestFullALCOABundleCheck:
    """
    Tests that check the entire evidence bundle against all 9 ALCOA+ dimensions.
    This mirrors the evidence-reviewer agent's primary function.
    """

    @_NEEDS_COMPLIANCE
    def test_full_bundle_passes_all_9_dimensions(
        self, evidence_bundle, mock_pzip, alcoa_fields
    ):
        """
        A well-formed evidence bundle must pass all 9 ALCOA+ dimensions.
        ComplianceStatus must be COMPLIANT (all dimensions >= 7).
        """
        mock_pzip.decompress.return_value = (
            b"<!DOCTYPE html><html><body>" + b"x" * 2000 + b"</body></html>"
        )
        mock_pzip.hash.return_value = evidence_bundle["before_snapshot_pzip_hash"]

        checker = ALCOAChecker(pzip=mock_pzip, evidence_store=MagicMock())
        checker.evidence_store.lookup.return_value = evidence_bundle
        checker.evidence_store.lookup_latency_ms.return_value = 50

        result = checker.check_all(evidence_bundle)
        assert result.overall_status in ("COMPLIANT", "MOSTLY_COMPLIANT")

    @_NEEDS_COMPLIANCE
    def test_each_alcoa_dimension_has_individual_result(
        self, evidence_bundle, mock_pzip
    ):
        """
        The ALCOACheckResult must contain one individual result per dimension.
        """
        mock_pzip.decompress.return_value = (
            b"<!DOCTYPE html><html><body>" + b"x" * 2000 + b"</body></html>"
        )
        checker = ALCOAChecker(pzip=mock_pzip, evidence_store=MagicMock())
        result = checker.check_all(evidence_bundle)
        for dim in ALCOA_DIMENSIONS:
            assert hasattr(result, dim) or dim in result.dimension_results, (
                f"ALCOACheckResult missing dimension result for '{dim}'"
            )

    @_NEEDS_COMPLIANCE
    def test_non_compliant_bundle_returns_non_compliant_status(self, mock_pzip):
        """
        A bundle with critical gaps (null oauth3_token_id, null chain_link)
        must return NON_COMPLIANT status.
        """
        bad_bundle = {
            "schema_version": "1.0.0",
            "bundle_id": "bad-bundle",
            "action_id": None,
            "action_type": None,
            "platform": None,
            "before_snapshot_pzip_hash": None,
            "after_snapshot_pzip_hash": None,
            "diff_hash": None,
            "oauth3_token_id": None,      # CRITICAL gap
            "timestamp_iso8601": None,
            "sha256_chain_link": None,    # CRITICAL gap
            "signature": None,
            "alcoa_fields": {},
            "rung_achieved": 0,
        }
        checker = ALCOAChecker(pzip=mock_pzip, evidence_store=MagicMock())
        result = checker.check_all(bad_bundle)
        assert result.overall_status == "NON_COMPLIANT"


# ---------------------------------------------------------------------------
# 21 CFR Part 11 section mapping
# ---------------------------------------------------------------------------


class TestPart11SectionMapping:
    """
    Diagram: 21 CFR Part 11 Section Mapping
    §11.10(a) — Validation: rung-gated evidence schema
    §11.10(b) — Accurate copies: PZip decompression → HTML, bit-perfect
    §11.10(c) — Record protection: AES-256-GCM encryption
    §11.10(e) — Audit trails: execution_trace + oauth3_token_id + timestamp
    §11.50   — Electronic signatures: AES-256-GCM per bundle, chain-linked
    """

    @_NEEDS_COMPLIANCE
    def test_11_10a_schema_validation_requires_rung_641(self, evidence_bundle):
        """
        §11.10(a): Validation of systems — accuracy + reliability.
        Evidence bundle schema validation must require rung >= 641.
        """
        checker = Part11Checker()
        result = checker.check_section_11_10a(evidence_bundle)
        assert result.passed is True
        assert result.rung_verified >= 641

    @_NEEDS_COMPLIANCE
    def test_11_10b_pzip_decompression_is_bit_perfect(self, evidence_bundle, mock_pzip):
        """
        §11.10(b): Generate accurate copies of records.
        PZip decompression must be lossless (bit-perfect reconstruction).
        """
        original = b"<!DOCTYPE html><html><body>exact content</body></html>"
        compressed = mock_pzip.compress(original)
        mock_pzip.decompress.return_value = original

        checker = Part11Checker(pzip=mock_pzip)
        result = checker.check_section_11_10b(
            evidence_bundle, source_html=original
        )
        assert result.passed is True
        assert result.copy_fidelity == "BIT_PERFECT"

    @_NEEDS_COMPLIANCE
    def test_11_10c_evidence_encrypted_at_rest(self, evidence_bundle):
        """
        §11.10(c): Protect records throughout retention period.
        Evidence files must be AES-256-GCM encrypted at rest.
        """
        checker = Part11Checker()
        result = checker.check_section_11_10c(evidence_bundle)
        assert result.passed is True
        assert result.encryption == "AES-256-GCM"

    @_NEEDS_COMPLIANCE
    def test_11_10e_audit_trail_has_operator_id_and_timestamp(self, evidence_bundle):
        """
        §11.10(e): Audit trails — date/time + operator ID per action.
        execution_trace must carry oauth3_token_id (operator) and timestamp.
        """
        mock_trace = {
            "trace_id": str(uuid.uuid4()),
            "recipe_id": "test-recipe",
            "oauth3_token_id": evidence_bundle["oauth3_token_id"],
            "timestamp_iso8601": evidence_bundle["timestamp_iso8601"],
            "steps_executed": 1,
            "status": "PASS",
        }
        checker = Part11Checker()
        result = checker.check_section_11_10e(mock_trace)
        assert result.passed is True
        assert result.operator_id_present is True
        assert result.timestamp_present is True

    @_NEEDS_COMPLIANCE
    def test_11_50_electronic_signature_present(self, evidence_bundle):
        """
        §11.50: Electronic signatures — legally binding per bundle.
        Every bundle must carry a non-null signature field (AES-256-GCM).
        """
        checker = Part11Checker()
        result = checker.check_section_11_50(evidence_bundle)
        assert result.passed is True
        assert result.signature_algorithm == "AES-256-GCM"

    @_NEEDS_COMPLIANCE
    def test_11_50_signature_fails_for_unsigned_bundle(self, evidence_bundle):
        """
        §11.50: UNSIGNED_BUNDLE → BLOCKED.
        A bundle with null signature must FAIL §11.50.
        """
        bundle = dict(evidence_bundle)
        bundle["signature"] = None
        checker = Part11Checker()
        result = checker.check_section_11_50(bundle)
        assert result.passed is False

    @_NEEDS_COMPLIANCE
    def test_full_part11_check_passes_compliant_bundle(
        self, evidence_bundle, mock_pzip
    ):
        """
        A fully-compliant bundle must pass all 5 Part 11 sections.
        Overall status must be COMPLIANT.
        """
        mock_pzip.decompress.return_value = (
            b"<!DOCTYPE html><html><body>" + b"x" * 2000 + b"</body></html>"
        )
        mock_trace = {
            "trace_id": str(uuid.uuid4()),
            "oauth3_token_id": evidence_bundle["oauth3_token_id"],
            "timestamp_iso8601": evidence_bundle["timestamp_iso8601"],
            "steps_executed": 1,
            "status": "PASS",
        }
        checker = Part11Checker(pzip=mock_pzip)
        result = checker.check_all(evidence_bundle, execution_trace=mock_trace)
        assert result.overall_status == "COMPLIANT"
        assert result.sections_passed == 5


# ---------------------------------------------------------------------------
# Compliance score interpretation (from diagram scoring flowchart)
# ---------------------------------------------------------------------------


class TestComplianceScoreInterpretation:
    """
    Diagram: ALCOA+ Score Interpretation
    9-10: Fully compliant
    6-8:  Mostly compliant
    3-5:  Partially compliant (remediation required)
    0-2:  Non-compliant (cannot proceed to audit)

    Overall: COMPLIANT if all 9 dimensions >= 7
             PARTIALLY_COMPLIANT if all >= 3, some < 7
             NON_COMPLIANT if any < 3 OR chain break OR PZip mismatch
    """

    @_NEEDS_COMPLIANCE
    def test_all_dimensions_9_produces_compliant(self):
        """All 9 dimensions at score 9+ must produce COMPLIANT."""
        scores = {dim: 9 for dim in ALCOA_DIMENSIONS}
        status = ComplianceScore.interpret(scores)
        assert status == ComplianceStatus.COMPLIANT

    @_NEEDS_COMPLIANCE
    def test_all_dimensions_7_produces_compliant(self):
        """All 9 dimensions at exactly 7 must produce COMPLIANT (threshold is >= 7)."""
        scores = {dim: 7 for dim in ALCOA_DIMENSIONS}
        status = ComplianceScore.interpret(scores)
        assert status == ComplianceStatus.COMPLIANT

    @_NEEDS_COMPLIANCE
    def test_one_dimension_below_3_produces_non_compliant(self):
        """Any dimension below 3 must produce NON_COMPLIANT (cannot proceed to audit)."""
        scores = {dim: 9 for dim in ALCOA_DIMENSIONS}
        scores["attributable"] = 2  # critical gap
        status = ComplianceScore.interpret(scores)
        assert status == ComplianceStatus.NON_COMPLIANT

    @_NEEDS_COMPLIANCE
    def test_all_dimensions_5_produces_partially_compliant(self):
        """All dimensions at 5 (below 7 threshold, above 3 floor) → PARTIALLY_COMPLIANT."""
        scores = {dim: 5 for dim in ALCOA_DIMENSIONS}
        status = ComplianceScore.interpret(scores)
        assert status == ComplianceStatus.PARTIALLY_COMPLIANT

    @_NEEDS_COMPLIANCE
    def test_chain_break_produces_non_compliant_regardless_of_scores(self):
        """
        Diagram: NON_COMPLIANT if chain break — even if other scores are high.
        A broken chain is an absolute disqualifier.
        """
        scores = {dim: 9 for dim in ALCOA_DIMENSIONS}
        status = ComplianceScore.interpret(scores, chain_break=True)
        assert status == ComplianceStatus.NON_COMPLIANT

    @_NEEDS_COMPLIANCE
    def test_pzip_mismatch_produces_non_compliant(self):
        """
        Diagram: NON_COMPLIANT if PZip mismatch — pzip_hash cannot be recomputed.
        """
        scores = {dim: 9 for dim in ALCOA_DIMENSIONS}
        status = ComplianceScore.interpret(scores, pzip_mismatch=True)
        assert status == ComplianceStatus.NON_COMPLIANT
