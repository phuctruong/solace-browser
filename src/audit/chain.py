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

EvidenceChainManager (B9 / T11):
  Two-stream evidence system for cross-app hash-chained audit trails.
  - execution_chain.jsonl: execution lifecycle events
  - oauth3_audit.jsonl: auth/token events
  Both streams share a run_id. Both are independently hash-chained.
  seal() freezes both chains. merge_cross_app() combines chains from
  multiple applications into a unified view.

Rung: 641
"""

from __future__ import annotations

import json
import hashlib
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List, Optional


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


# ---------------------------------------------------------------------------
# Constants for EvidenceChainManager
# ---------------------------------------------------------------------------

GENESIS_HASH = "0" * 64

_VALID_REALMS = frozenset({"local", "cloud", "browser"})


# ---------------------------------------------------------------------------
# Errors — specific, never generic (Fallback Ban)
# ---------------------------------------------------------------------------

class ChainBreakError(Exception):
    """Raised when a hash chain break is detected during validation."""


class ChainSealedError(Exception):
    """Raised when trying to append to a chain that has been sealed."""


# ---------------------------------------------------------------------------
# EvidenceEntry — single entry in an evidence chain
# ---------------------------------------------------------------------------

@dataclass
class EvidenceEntry:
    """Single entry in a two-stream evidence chain.

    Fields:
        entry_id:       Sequential integer index within the chain.
        timestamp:      ISO 8601 UTC timestamp at creation.
        event:          Event name (e.g. "TRIGGER", "token_issued").
        detail:         Arbitrary dict of event-specific data.
        realm_origin:   Where this event originated: "local", "cloud", "browser".
        prev_hash:      SHA-256 hash of the previous entry (genesis = "0" * 64).
        entry_hash:     SHA-256 hash of this entry (computed from all other fields).
        run_id:         Shared run identifier linking execution + auth streams.
    """
    entry_id: int
    timestamp: str
    event: str
    detail: dict
    realm_origin: str
    prev_hash: str
    entry_hash: str
    run_id: str


# ---------------------------------------------------------------------------
# _SingleChain — internal append-only hash chain for one JSONL file
# ---------------------------------------------------------------------------

class _SingleChain:
    """Append-only hash-chained JSONL file for a single evidence stream.

    Each entry's hash is computed from a canonical JSON representation
    that excludes the entry_hash field. The prev_hash links to the
    previous entry, forming a tamper-evident sequential chain.

    This class is internal to EvidenceChainManager. External callers
    should use EvidenceChainManager.log_execution() / log_auth().
    """

    def __init__(
        self,
        path: Path,
        run_id: str,
        *,
        now_fn: Callable[[], datetime],
    ) -> None:
        self._path = path
        self._run_id = run_id
        self._now = now_fn
        self._prev_hash = GENESIS_HASH
        self._index = 0
        self._sealed = False

    @property
    def sealed(self) -> bool:
        """True if this chain has been sealed (no further writes allowed)."""
        return self._sealed

    @property
    def path(self) -> Path:
        """Filesystem path to the JSONL file."""
        return self._path

    @property
    def entry_count(self) -> int:
        """Number of entries written so far."""
        return self._index

    def append(self, event: str, detail: dict, *, realm: str = "local") -> str:
        """Append an event to this chain. Returns the entry_hash.

        Args:
            event:  Event name string.
            detail: Event-specific data dict.
            realm:  Origin realm ("local", "cloud", "browser").

        Returns:
            The SHA-256 entry_hash of the appended entry.

        Raises:
            ChainSealedError: If the chain has been sealed.
            ValueError: If realm is not one of the valid realm values.
        """
        if self._sealed:
            raise ChainSealedError(
                f"Chain {self._path.name} is sealed. "
                f"No further entries can be appended after seal."
            )

        if realm not in _VALID_REALMS:
            raise ValueError(
                f"Invalid realm_origin: {realm!r}. "
                f"Must be one of: {sorted(_VALID_REALMS)}"
            )

        record: dict[str, Any] = {
            "entry_id": self._index,
            "timestamp": self._now().isoformat(),
            "event": event,
            "detail": detail,
            "realm_origin": realm,
            "prev_hash": self._prev_hash,
            "run_id": self._run_id,
        }

        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
        entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        record["entry_hash"] = entry_hash

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

        self._prev_hash = entry_hash
        self._index += 1
        return entry_hash

    def write_seal(self) -> str:
        """Write a SEAL entry and mark this chain as closed.

        Returns:
            The entry_hash of the SEAL entry.

        Raises:
            ChainSealedError: If already sealed.
        """
        seal_hash = self.append(
            "SEAL",
            {"sealed_at": self._now().isoformat(), "total_entries": self._index},
            realm="local",
        )
        self._sealed = True
        return seal_hash


# ---------------------------------------------------------------------------
# EvidenceChainManager — two parallel streams sharing a run_id
# ---------------------------------------------------------------------------

class EvidenceChainManager:
    """Manages two parallel evidence streams sharing a run_id.

    Streams:
        1. evidence_chain.jsonl — execution lifecycle events
        2. oauth3_audit.jsonl   — auth/token events

    Both streams are independently hash-chained with SHA-256.
    Both share the same run_id so they can be correlated.

    Design rules (Fallback Ban):
        - Append-only (no modification after write)
        - Chain sealed before any upload
        - Broken chain surfaced immediately to user (not hidden)
        - No bare except blocks
    """

    def __init__(
        self,
        evidence_dir: Path,
        run_id: str,
        *,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        """Create two JSONL chain files under evidence_dir.

        Args:
            evidence_dir: Directory where JSONL files will be created.
            run_id:       Shared run identifier for both streams.
            now_fn:       Optional callable returning current UTC datetime (for testing).
        """
        self._evidence_dir = Path(evidence_dir)
        self._run_id = run_id
        self._now = now_fn or (lambda: datetime.now(timezone.utc))

        self._execution_chain = _SingleChain(
            self._evidence_dir / "evidence_chain.jsonl",
            run_id,
            now_fn=self._now,
        )
        self._auth_chain = _SingleChain(
            self._evidence_dir / "oauth3_audit.jsonl",
            run_id,
            now_fn=self._now,
        )

    # ------------------------------------------------------------------
    # Public logging interface
    # ------------------------------------------------------------------

    def log_execution(
        self, event: str, detail: dict, *, realm: str = "local"
    ) -> str:
        """Log an event to the execution chain.

        Args:
            event:  Event name (e.g. "TRIGGER", "PREVIEW", "DONE").
            detail: Event-specific data dict.
            realm:  Origin realm ("local", "cloud", "browser").

        Returns:
            The SHA-256 entry_hash of the appended entry.
        """
        return self._execution_chain.append(event, detail, realm=realm)

    def log_auth(
        self, event: str, detail: dict, *, realm: str = "local"
    ) -> str:
        """Log an event to the oauth3 audit chain.

        Args:
            event:  Event name (e.g. "token_issued", "token_revoked").
            detail: Event-specific data dict.
            realm:  Origin realm ("local", "cloud", "browser").

        Returns:
            The SHA-256 entry_hash of the appended entry.
        """
        return self._auth_chain.append(event, detail, realm=realm)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_chain(self, chain_path: Path) -> dict:
        """Validate a single chain file by reading its JSONL and verifying every hash link.

        Args:
            chain_path: Path to a JSONL chain file.

        Returns:
            {
                "valid": bool,
                "entries": int,
                "first_hash": str,   # entry_hash of first entry, or ""
                "last_hash": str,    # entry_hash of last entry, or ""
                "breaks": list,      # list of break-point dicts
            }
        """
        if not chain_path.exists():
            return {
                "valid": True,
                "entries": 0,
                "first_hash": "",
                "last_hash": "",
                "breaks": [],
            }

        entries: list[dict] = []
        with chain_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                entries.append(json.loads(stripped))

        if not entries:
            return {
                "valid": True,
                "entries": 0,
                "first_hash": "",
                "last_hash": "",
                "breaks": [],
            }

        breaks: list[dict] = []

        for i, entry in enumerate(entries):
            # Recompute hash from canonical form (excluding entry_hash)
            stored_hash = entry.get("entry_hash", "")
            record_without_hash = {
                k: v for k, v in entry.items() if k != "entry_hash"
            }
            canonical = json.dumps(
                record_without_hash, sort_keys=True, separators=(",", ":")
            )
            computed_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

            if stored_hash != computed_hash:
                breaks.append({
                    "entry_id": entry.get("entry_id", i),
                    "type": "hash_mismatch",
                    "expected": computed_hash[:16] + "...",
                    "got": stored_hash[:16] + "...",
                })

            # Check chain link
            expected_prev = (
                GENESIS_HASH if i == 0
                else entries[i - 1].get("entry_hash", "")
            )
            actual_prev = entry.get("prev_hash", "")
            if actual_prev != expected_prev:
                breaks.append({
                    "entry_id": entry.get("entry_id", i),
                    "type": "chain_break",
                    "expected_prev": expected_prev[:16] + "...",
                    "got_prev": actual_prev[:16] + "...",
                })

        return {
            "valid": len(breaks) == 0,
            "entries": len(entries),
            "first_hash": entries[0].get("entry_hash", ""),
            "last_hash": entries[-1].get("entry_hash", ""),
            "breaks": breaks,
        }

    def validate_all(self) -> dict:
        """Validate both evidence chains.

        Returns:
            {
                "execution": {"valid": bool, "entries": int},
                "auth": {"valid": bool, "entries": int},
                "run_id": str,
            }
        """
        exec_result = self.validate_chain(self._execution_chain.path)
        auth_result = self.validate_chain(self._auth_chain.path)
        return {
            "execution": {
                "valid": exec_result["valid"],
                "entries": exec_result["entries"],
            },
            "auth": {
                "valid": auth_result["valid"],
                "entries": auth_result["entries"],
            },
            "run_id": self._run_id,
        }

    # ------------------------------------------------------------------
    # Seal
    # ------------------------------------------------------------------

    def seal(self) -> dict:
        """Seal both chains. No more entries allowed after this call.

        Returns:
            {
                "execution_hash": str,  # final entry_hash of execution chain
                "auth_hash": str,       # final entry_hash of auth chain
                "sealed_at": str,       # ISO 8601 timestamp
            }
        """
        exec_hash = self._execution_chain.write_seal()
        auth_hash = self._auth_chain.write_seal()
        return {
            "execution_hash": exec_hash,
            "auth_hash": auth_hash,
            "sealed_at": self._now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Cross-app merge
    # ------------------------------------------------------------------

    def merge_cross_app(self, other_chain: Path) -> dict:
        """Merge another application's evidence chain into a cross-app view.

        Reads the other chain's JSONL entries and writes them into a
        merged file at {evidence_dir}/cross_app_merged.jsonl. The merged
        file is sorted by timestamp. Source app_ids are extracted from
        run_id prefixes.

        Args:
            other_chain: Path to another app's JSONL chain file.

        Returns:
            {
                "merged_entries": int,  # total entries in merged file
                "sources": [str],       # list of distinct source app_ids
            }

        Raises:
            FileNotFoundError: If other_chain does not exist.
        """
        if not other_chain.exists():
            raise FileNotFoundError(
                f"Cross-app chain not found: {other_chain}"
            )

        # Collect entries from both our execution chain and the other chain
        all_entries: list[dict] = []
        source_ids: set[str] = set()

        # Read our execution chain
        exec_path = self._execution_chain.path
        if exec_path.exists():
            with exec_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    entry = json.loads(stripped)
                    entry["_source_chain"] = str(exec_path)
                    all_entries.append(entry)
                    run_id = entry.get("run_id", "")
                    if run_id:
                        source_ids.add(run_id.split("-")[0] if "-" in run_id else run_id)

        # Read the other chain
        with other_chain.open("r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                entry = json.loads(stripped)
                entry["_source_chain"] = str(other_chain)
                all_entries.append(entry)
                run_id = entry.get("run_id", "")
                if run_id:
                    source_ids.add(run_id.split("-")[0] if "-" in run_id else run_id)

        # Sort by timestamp for chronological ordering
        all_entries.sort(key=lambda e: e.get("timestamp", ""))

        # Write merged file
        merged_path = self._evidence_dir / "cross_app_merged.jsonl"
        merged_path.parent.mkdir(parents=True, exist_ok=True)
        with merged_path.open("w", encoding="utf-8") as fh:
            for entry in all_entries:
                # Remove internal _source_chain before writing
                entry_clean = {k: v for k, v in entry.items() if k != "_source_chain"}
                fh.write(json.dumps(entry_clean, sort_keys=True) + "\n")

        return {
            "merged_entries": len(all_entries),
            "sources": sorted(source_ids),
        }

    # ------------------------------------------------------------------
    # E-signing
    # ------------------------------------------------------------------

    @staticmethod
    def e_sign(
        user_id: str,
        timestamp: str,
        meaning: str,
        record_hash: str,
    ) -> str:
        """Compute an e-signature hash for an approval entry.

        Formula: sha256(user_id + timestamp + meaning + record_hash)

        Args:
            user_id:      Identifier of the signing user.
            timestamp:    ISO 8601 timestamp of the signing event.
            meaning:      Signature meaning (e.g. "approved", "reviewed").
            record_hash:  SHA-256 hash of the record being signed.

        Returns:
            64-character lowercase hex SHA-256 digest.
        """
        payload = user_id + timestamp + meaning + record_hash
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def run_id(self) -> str:
        """The shared run_id for both evidence streams."""
        return self._run_id

    @property
    def execution_chain_path(self) -> Path:
        """Path to the execution evidence chain JSONL file."""
        return self._execution_chain.path

    @property
    def auth_chain_path(self) -> Path:
        """Path to the oauth3 audit chain JSONL file."""
        return self._auth_chain.path

    @property
    def is_sealed(self) -> bool:
        """True if both chains have been sealed."""
        return self._execution_chain.sealed and self._auth_chain.sealed
