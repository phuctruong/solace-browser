"""
audit/alcoa.py — ALCOA+ Compliance Validation

ALCOA+ is the FDA/regulatory framework for data integrity:

  A — Attributable:     Every record identifies who created/modified it and when.
  L — Legible:          Records are permanently readable (human-readable descriptions).
  C — Contemporaneous:  Records are created at the time of the event.
  O — Original:         The first capture is preserved (snapshot_id links to HTML).
  A — Accurate:         Records reflect actual events (hash chain detects tampering).
  C — Complete:         No gaps in the record sequence (entry_id continuity).
  C — Consistent:       No duplicate entry IDs (uniqueness within session).
  E — Enduring:         Records persist on disk (not only in memory).
  A — Available:        Records can be loaded back from disk.

References:
  FDA Data Integrity Guidance (2018)
  EU GMP Annex 11 — Computerised Systems
  21 CFR Part 11 §11.10

Rung: 641
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chain import AuditChain


# ---------------------------------------------------------------------------
# ALCOAReport
# ---------------------------------------------------------------------------

@dataclass
class ALCOAReport:
    """
    ALCOA+ compliance report for a single AuditChain session.

    Each boolean field represents one ALCOA+ principle.
    overall is True only when all nine principles pass.

    Attributes:
        attributable:     Every entry has non-empty user_id AND non-empty token_id.
        legible:          Every entry has a non-empty human_description.
        contemporaneous:  Timestamps are monotonically non-decreasing (no backward jumps).
        original:         Every entry has a non-empty snapshot_id.
        accurate:         Hash chain verify_integrity() passes.
        complete:         Entry IDs form a contiguous sequence 0, 1, 2, … (no gaps).
        consistent:       No duplicate entry_ids within the session.
        enduring:         The audit.jsonl file exists on disk.
        available:        Entries can be loaded from disk and count matches memory.
        overall:          All nine principles pass.
    """
    attributable: bool = False
    legible: bool = False
    contemporaneous: bool = False
    original: bool = False
    accurate: bool = False
    complete: bool = False
    consistent: bool = False
    enduring: bool = False
    available: bool = False
    overall: bool = False

    @property
    def score(self) -> str:
        """
        Return the ALCOA+ score as a fraction string.

        Example: "8/9" means 8 of 9 principles passed.
        """
        checks = [
            self.attributable,
            self.legible,
            self.contemporaneous,
            self.original,
            self.accurate,
            self.complete,
            self.consistent,
            self.enduring,
            self.available,
        ]
        return f"{sum(checks)}/{len(checks)}"


# ---------------------------------------------------------------------------
# validate_alcoa
# ---------------------------------------------------------------------------

def validate_alcoa(chain: "AuditChain") -> ALCOAReport:
    """
    Run a full ALCOA+ validation pass on an AuditChain.

    Evaluates all nine principles against the chain's current in-memory state
    and its on-disk persistence.

    Args:
        chain: An AuditChain instance (may or may not have entries).

    Returns:
        ALCOAReport with per-principle results and overall pass/fail.
    """
    report = ALCOAReport()
    entries = chain.entries

    # ------------------------------------------------------------------
    # A — Attributable
    # Every entry must have non-empty user_id AND non-empty token_id.
    # ------------------------------------------------------------------
    if entries:
        report.attributable = all(
            bool(e.user_id) and bool(e.token_id)
            for e in entries
        )
    else:
        # An empty chain trivially satisfies attributable
        report.attributable = True

    # ------------------------------------------------------------------
    # L — Legible
    # Every entry must have a non-empty human_description.
    # ------------------------------------------------------------------
    if entries:
        report.legible = all(bool(e.human_description) for e in entries)
    else:
        report.legible = True

    # ------------------------------------------------------------------
    # C — Contemporaneous
    # Timestamps must be monotonically non-decreasing (no backward jumps).
    # Comparison is done lexicographically on ISO 8601 UTC strings,
    # which are naturally sortable when formatted consistently.
    # ------------------------------------------------------------------
    if len(entries) < 2:
        report.contemporaneous = True
    else:
        report.contemporaneous = all(
            entries[i].timestamp <= entries[i + 1].timestamp
            for i in range(len(entries) - 1)
        )

    # ------------------------------------------------------------------
    # O — Original
    # Every entry must have a non-empty snapshot_id that links to the
    # original HTML evidence (content-addressed snapshot store).
    # ------------------------------------------------------------------
    if entries:
        report.original = all(bool(e.snapshot_id) for e in entries)
    else:
        report.original = True

    # ------------------------------------------------------------------
    # A — Accurate
    # The hash chain must be fully intact (no tampering or reordering).
    # ------------------------------------------------------------------
    integrity = chain.verify_integrity()
    report.accurate = integrity["valid"]

    # ------------------------------------------------------------------
    # C — Complete
    # Entry IDs must form a contiguous integer sequence: "0", "1", "2", …
    # No gaps are permitted (ALCOA-C complete).
    # ------------------------------------------------------------------
    if entries:
        expected_ids = [str(i) for i in range(len(entries))]
        actual_ids = [e.entry_id for e in entries]
        report.complete = expected_ids == actual_ids
    else:
        report.complete = True

    # ------------------------------------------------------------------
    # C — Consistent
    # No duplicate entry_ids within the session.
    # ------------------------------------------------------------------
    if entries:
        ids = [e.entry_id for e in entries]
        report.consistent = len(ids) == len(set(ids))
    else:
        report.consistent = True

    # ------------------------------------------------------------------
    # E — Enduring
    # The audit.jsonl file must exist on disk.
    # ------------------------------------------------------------------
    log_path = chain._log_path()
    report.enduring = log_path.exists()

    # ------------------------------------------------------------------
    # A — Available
    # Entries can be loaded from disk and the count matches in-memory count.
    # ------------------------------------------------------------------
    if report.enduring:
        try:
            # Create a temporary chain object and load from the same path
            from .chain import AuditChain as _AuditChain
            temp = _AuditChain(
                session_id=chain.session_id,
                base_dir=str(chain._base),
            )
            temp.load()
            report.available = (temp.count == chain.count)
        except Exception:
            report.available = False
    else:
        # Nothing on disk → not available (unless chain is also empty)
        report.available = (chain.count == 0)

    # ------------------------------------------------------------------
    # Overall
    # ------------------------------------------------------------------
    report.overall = all([
        report.attributable,
        report.legible,
        report.contemporaneous,
        report.original,
        report.accurate,
        report.complete,
        report.consistent,
        report.enduring,
        report.available,
    ])

    return report
