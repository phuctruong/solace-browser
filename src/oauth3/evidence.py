"""
OAuth3 Evidence Chain

Hash-chained JSONL audit log for OAuth3 events.
Each event includes `prev_hash` so tampering is detectable.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

GENESIS_HASH = "0" * 64


class EvidenceChain:
    """Append-only hash chain for OAuth3 audit events."""

    def __init__(self, logfile: Path | str) -> None:
        self.logfile = Path(logfile)
        self.logfile.parent.mkdir(parents=True, exist_ok=True)
        self.prev_hash = self._load_tail_hash()

    def log_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Append one event and return the new event hash."""
        event: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "prev_hash": self.prev_hash,
            "data": data,
        }
        event_hash = self._event_hash(event)
        event["event_hash"] = event_hash

        with self.logfile.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

        self.prev_hash = event_hash
        return event_hash

    def load_events(self) -> List[Dict[str, Any]]:
        """Load all events from the JSONL file."""
        if not self.logfile.exists():
            return []

        events: List[Dict[str, Any]] = []
        with self.logfile.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))
        return events

    def verify_chain(self) -> Tuple[bool, Optional[str]]:
        """Verify hash links from genesis to tail."""
        events = self.load_events()
        expected_prev = GENESIS_HASH

        for idx, event in enumerate(events):
            if event.get("prev_hash") != expected_prev:
                return False, f"broken_prev_hash_at_index_{idx}"

            payload = {
                "timestamp": event.get("timestamp"),
                "event_type": event.get("event_type"),
                "prev_hash": event.get("prev_hash"),
                "data": event.get("data"),
            }
            expected_hash = self._event_hash(payload)
            if event.get("event_hash") != expected_hash:
                return False, f"broken_event_hash_at_index_{idx}"

            expected_prev = expected_hash

        return True, None

    def _load_tail_hash(self) -> str:
        if not self.logfile.exists():
            return GENESIS_HASH

        last_nonempty = ""
        with self.logfile.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last_nonempty = line

        if not last_nonempty:
            return GENESIS_HASH

        try:
            event = json.loads(last_nonempty)
            return str(event.get("event_hash") or GENESIS_HASH)
        except json.JSONDecodeError:
            return GENESIS_HASH

    @staticmethod
    def _event_hash(event: Dict[str, Any]) -> str:
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
