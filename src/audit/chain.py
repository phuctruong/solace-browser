"""
audit/chain.py — Hash-Chained Audit Log

FDA 21 CFR Part 11 §11.10(b)(e) compliant:
  - §11.10(b): Audit trail generation, timestamp-ordered, tamper-evident
  - §11.10(e): Operator ID and reason for each record modification

ALCOA+ compliant:
  - Attributable: every entry has user_id + token_id
  - Legible: human_description in plain English
  - Contemporaneous: ISO 8601 timestamp at creation
  - Original: snapshot_id links to HTML snapshot
  - Accurate: SHA-256 hash chain detects any tampering

Tamper evidence mechanism:
  Each entry's entry_hash = SHA-256(all fields except entry_hash itself).
  Each entry's prev_hash   = entry_hash of the preceding entry.
  First entry's prev_hash  = GENESIS_HASH ("0" * 64).

  If any entry is modified → its entry_hash changes → the next entry's
  prev_hash no longer matches → verify_integrity() reports TAMPER DETECTED.

Rung: 641
"""

import json
import hashlib
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# AuditEntry
# ---------------------------------------------------------------------------

@dataclass
class AuditEntry:
    """
    A single immutable audit log entry (21 CFR Part 11 §11.10(e)).

    ALCOA+ fields:
        Attributable  — user_id, token_id
        Legible       — human_description (plain English, no PII)
        Contemporaneous — timestamp (ISO 8601 with milliseconds, UTC)
        Original      — snapshot_id (content-addressed HTML snapshot)
        Accurate      — entry_hash, prev_hash (SHA-256 chain)
    """
    entry_id: str           # Sequential string integer within the session log
    timestamp: str          # ISO 8601 UTC with milliseconds: "2026-02-21T12:34:56.789+00:00"
    user_id: str            # Who performed/authorized the action (ALCOA-A)
    token_id: str           # OAuth3 agency token ID (non-repudiation)
    action: str             # What happened: navigate, click, fill, submit, etc.
    target: str             # What was acted on: URL, CSS selector, field name
    before_value: str       # Value before action (empty for navigate/click)
    after_value: str        # Value after action
    reason: str             # WHY this action was taken (§11.10(e) + EU Annex 11 §9)
    meaning: str            # Signature meaning: "authorized" | "reviewed" | "delegated"
    human_description: str  # Plain English description for audit review (ALCOA-L)
    snapshot_id: str        # SHA-256 content-addressed snapshot ID (ALCOA-O)
    scope_used: str         # OAuth3 scope exercised (e.g. "linkedin.create_post")
    step_up_performed: bool # Whether re-confirmation (step-up) was required
    prev_hash: str          # SHA-256 of previous entry's full hash (chain link)
    entry_hash: str = ""    # SHA-256 of this entry (computed at creation, excluded from own hash)

    def compute_hash(self) -> str:
        """
        Compute SHA-256 of this entry (excluding the entry_hash field itself).

        Canonical form: JSON with sorted keys, no extra whitespace.
        Encoding: UTF-8.

        Returns:
            64-character lowercase hex string.
        """
        d = asdict(self)
        d.pop("entry_hash", None)
        canonical = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# AuditChain
# ---------------------------------------------------------------------------

class AuditChain:
    """
    Append-only, hash-chained audit log for FDA 21 CFR Part 11.

    Storage layout:
        {base_dir}/audit/{session_id}/audit.jsonl

    File format: one JSON object per line (JSONL).
    Each line is the full AuditEntry serialized with json.dumps.

    Tamper detection:
        verify_integrity() walks all loaded entries and checks:
          1. entry.entry_hash == entry.compute_hash()   (content not modified)
          2. entry.prev_hash == previous_entry.entry_hash  (chain not broken)
          3. entry[0].prev_hash == GENESIS_HASH

    This is NOT a blockchain — it is a Merkle-style sequential hash chain
    that proves the log was never reordered, modified, or truncated.

    Design constraints:
        - No delete() method (append-only by design)
        - No modify() method (immutable entries)
        - Entry IDs are sequential integers as strings: "0", "1", "2", ...
        - Genesis entry always has prev_hash = "0" * 64
    """

    GENESIS_HASH = "0" * 64  # All-zero placeholder for the first entry's prev_hash

    def __init__(self, session_id: str, base_dir: Optional[str] = None):
        """
        Args:
            session_id: Unique identifier for this audit session (e.g. recipe run ID).
            base_dir:   Root directory for audit storage.
                        Default: ~/.solace/audit
        """
        self.session_id = session_id
        self._base = Path(base_dir or "~/.solace/audit").expanduser()
        self._entries: List[AuditEntry] = []
        self._entry_count = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def append(
        self,
        user_id: str,
        token_id: str,
        action: str,
        target: str,
        before_value: str = "",
        after_value: str = "",
        reason: str = "",
        meaning: str = "authorized",
        human_description: str = "",
        snapshot_id: str = "",
        scope_used: str = "",
        step_up_performed: bool = False,
    ) -> AuditEntry:
        """
        Append a new, immutable entry to the audit chain.

        The entry_hash is computed automatically (SHA-256 of all other fields).
        The prev_hash is set to the entry_hash of the last appended entry,
        or GENESIS_HASH if this is the first entry.

        Args:
            user_id:            Identifier for the human/agent who acted.
            token_id:           OAuth3 agency token ID authorizing the action.
            action:             Short action verb: navigate, click, fill, submit, etc.
            target:             What was acted on: URL, CSS selector, field name.
            before_value:       Field value before action (empty for non-fill actions).
            after_value:        Field value after action.
            reason:             WHY the action was taken (§11.10(e)).
            meaning:            Signature meaning: "authorized"|"reviewed"|"delegated".
            human_description:  Plain English description (ALCOA-L). No PII.
            snapshot_id:        Content-addressed HTML snapshot ID (ALCOA-O).
            scope_used:         OAuth3 scope exercised.
            step_up_performed:  True if re-confirmation was required and performed.

        Returns:
            The created AuditEntry (already persisted to disk).
        """
        prev_hash = (
            self._entries[-1].entry_hash if self._entries else self.GENESIS_HASH
        )

        entry = AuditEntry(
            entry_id=str(self._entry_count),
            timestamp=self._now_iso(),
            user_id=user_id,
            token_id=token_id,
            action=action,
            target=target,
            before_value=before_value,
            after_value=after_value,
            reason=reason,
            meaning=meaning,
            human_description=human_description,
            snapshot_id=snapshot_id,
            scope_used=scope_used,
            step_up_performed=step_up_performed,
            prev_hash=prev_hash,
        )
        entry.entry_hash = entry.compute_hash()

        self._entries.append(entry)
        self._entry_count += 1
        self._persist_entry(entry)

        return entry

    def verify_integrity(self) -> dict:
        """
        Verify the entire chain is intact.

        Checks (in order for each entry i):
          1. entry.entry_hash == entry.compute_hash()  — content not tampered
          2. If i == 0: entry.prev_hash == GENESIS_HASH
          3. If i > 0:  entry.prev_hash == entries[i-1].entry_hash

        Returns:
            {
                "valid": bool,
                "entries_checked": int,
                "break_at": int | None,   # index of first broken entry, or None
                "error": str | None,      # human-readable error, or None
            }
        """
        for i, entry in enumerate(self._entries):
            # Check 1: content hash is correct
            expected_hash = entry.compute_hash()
            if entry.entry_hash != expected_hash:
                return {
                    "valid": False,
                    "entries_checked": i + 1,
                    "break_at": i,
                    "error": (
                        f"Entry {i}: hash mismatch "
                        f"(stored={entry.entry_hash[:16]}..., "
                        f"computed={expected_hash[:16]}...)"
                    ),
                }

            # Check 2/3: chain link is correct
            if i == 0:
                if entry.prev_hash != self.GENESIS_HASH:
                    return {
                        "valid": False,
                        "entries_checked": 1,
                        "break_at": 0,
                        "error": (
                            f"Genesis entry has wrong prev_hash "
                            f"(expected={self.GENESIS_HASH[:16]}..., "
                            f"got={entry.prev_hash[:16]}...)"
                        ),
                    }
            else:
                expected_prev = self._entries[i - 1].entry_hash
                if entry.prev_hash != expected_prev:
                    return {
                        "valid": False,
                        "entries_checked": i + 1,
                        "break_at": i,
                        "error": (
                            f"Entry {i}: chain broken "
                            f"(expected prev_hash={expected_prev[:16]}..., "
                            f"got={entry.prev_hash[:16]}...)"
                        ),
                    }

        return {
            "valid": True,
            "entries_checked": len(self._entries),
            "break_at": None,
            "error": None,
        }

    def load(self) -> None:
        """
        Load audit chain from disk.

        Reads {base_dir}/audit/{session_id}/audit.jsonl line by line.
        Rebuilds self._entries and self._entry_count from persisted data.

        Raises:
            FileNotFoundError: if the audit.jsonl file does not exist.
        """
        log_path = self._log_path()
        if not log_path.exists():
            raise FileNotFoundError(
                f"Audit log not found: {log_path}"
            )

        loaded: List[AuditEntry] = []
        with log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entry = AuditEntry(**data)
                loaded.append(entry)

        self._entries = loaded
        self._entry_count = len(loaded)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def entries(self) -> List[AuditEntry]:
        """Return a copy of the entries list (immutable view)."""
        return list(self._entries)

    @property
    def chain_hash(self) -> str:
        """
        SHA-256 of the last entry — identity fingerprint of the entire chain.
        Returns GENESIS_HASH when the chain is empty.
        """
        if not self._entries:
            return self.GENESIS_HASH
        return self._entries[-1].entry_hash

    @property
    def count(self) -> int:
        """Number of entries in this chain."""
        return len(self._entries)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_path(self) -> Path:
        """Compute the full path to the audit.jsonl file for this session."""
        return self._base / "audit" / self.session_id / "audit.jsonl"

    def _persist_entry(self, entry: AuditEntry) -> None:
        """
        Append a single entry to audit.jsonl (append-only, never overwrites).

        Creates parent directories on first write.
        Each entry is serialized as a single JSON line terminated by \\n.
        """
        log_path = self._log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        line = json.dumps(asdict(entry), sort_keys=True) + "\n"
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def _now_iso(self) -> str:
        """
        Return the current UTC time as ISO 8601 with milliseconds.

        Format: "2026-02-21T12:34:56.789000+00:00"
        """
        return datetime.now(timezone.utc).isoformat()
