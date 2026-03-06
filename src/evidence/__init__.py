"""
evidence/__init__.py — SHA-256 Hash-Chained Evidence System

Provides two public functions for sealing and verifying evidence:
  seal_evidence(data, previous_hash=None) -> dict
  verify_chain(entries) -> bool

Each sealed entry gets:
  - timestamp:     ISO 8601 UTC (contemporaneous)
  - hash:          SHA-256 of (previous_hash + canonical JSON of data)
  - previous_hash: hash of the preceding entry ("genesis" for the first)

Chain verification walks all entries and confirms every hash link
is intact and every content hash is correct.

Rung: 641
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional

# Re-export key classes from audit.chain for unified access.
# These are optional — seal_evidence/verify_chain work standalone.
try:
    from audit.chain import (  # noqa: F401
        AuditChain,
        AuditEntry,
        EvidenceChainManager,
        EvidenceEntry,
    )
except ImportError:
    pass

try:
    from .summary_formatter import (  # noqa: F401
        EvidenceSummaryFormatter,
        format_action_summary,
        format_step_timing,
        link_to_evidence,
    )
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Module-level state for simple sequential sealing
# ---------------------------------------------------------------------------

GENESIS_HASH = "genesis"

_last_hash: str = GENESIS_HASH


def _canonical_json(data: dict) -> str:
    """Return deterministic JSON string for hashing (sorted keys, no spaces)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _compute_hash(previous_hash: str, canonical: str) -> str:
    """SHA-256 of previous_hash concatenated with canonical JSON payload."""
    payload = previous_hash + canonical
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def seal_evidence(data: dict, previous_hash: Optional[str] = None) -> dict:
    """Seal a dict with a SHA-256 hash, timestamp, and chain link.

    Args:
        data:          The evidence payload to seal. Must be a dict.
        previous_hash: Hash of the preceding entry. If None, uses the
                       module-level chain state (auto-chains sequential calls).
                       Pass "genesis" explicitly for the first entry of a new chain.

    Returns:
        A new dict containing all original data fields plus:
          - timestamp:     ISO 8601 UTC string
          - previous_hash: the previous entry's hash (or "genesis")
          - hash:          SHA-256 of (previous_hash + canonical JSON of data)
    """
    global _last_hash

    if not isinstance(data, dict):
        raise TypeError(f"data must be a dict, got {type(data).__name__!r}")

    prev = previous_hash if previous_hash is not None else _last_hash

    # Build the enriched entry
    enriched = dict(data)
    enriched["timestamp"] = datetime.now(timezone.utc).isoformat()
    enriched["previous_hash"] = prev

    # Compute hash over (previous_hash + canonical JSON of original data + timestamp)
    # We hash the enriched dict minus the hash field itself for consistency
    hashable = {k: v for k, v in enriched.items() if k != "hash"}
    canonical = _canonical_json(hashable)
    entry_hash = _compute_hash(prev, canonical)
    enriched["hash"] = entry_hash

    # Update module-level chain state
    _last_hash = entry_hash

    return enriched


def verify_chain(entries: List[dict]) -> bool:
    """Verify the integrity of a list of sealed evidence entries.

    Checks for each entry:
      1. previous_hash matches the hash of the preceding entry
         (or "genesis" for the first entry).
      2. hash field matches the recomputed SHA-256 of
         (previous_hash + canonical JSON of all fields except hash).

    Args:
        entries: Ordered list of sealed evidence dicts (as returned by seal_evidence).

    Returns:
        True if the entire chain is intact, False if any entry is tampered or broken.
    """
    if not isinstance(entries, list):
        raise TypeError(f"entries must be a list, got {type(entries).__name__!r}")

    expected_prev = GENESIS_HASH

    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise TypeError(
                f"Entry {i} must be a dict, got {type(entry).__name__!r}"
            )

        # Check 1: chain link
        actual_prev = entry.get("previous_hash", "")
        if actual_prev != expected_prev:
            return False

        # Check 2: content hash
        stored_hash = entry.get("hash", "")
        hashable = {k: v for k, v in entry.items() if k != "hash"}
        canonical = _canonical_json(hashable)
        computed_hash = _compute_hash(actual_prev, canonical)

        if stored_hash != computed_hash:
            return False

        # Advance expected previous hash
        expected_prev = stored_hash

    return True


def reset_chain() -> None:
    """Reset the module-level chain state to genesis.

    Useful for starting a new independent chain without restarting the process.
    """
    global _last_hash
    _last_hash = GENESIS_HASH
