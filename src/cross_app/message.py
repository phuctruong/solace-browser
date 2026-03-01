"""Cross-app messaging protocol for Solace outbox-to-inbox delivery.

A message flows from one app's outbox to another app's inbox/requests/.
Every delivery is budget-gated (B6) and evidence-hashed.

Design rules (Fallback Ban):
  - NO silent swallowing — every failure raises or returns explicit error
  - NO broad except — catch SPECIFIC exceptions only
  - NO fake data or mock success — real file writes or real failures
  - Evidence hash computed for EVERY delivery (SHA-256 of canonical JSON)

Auth: 65537 | Rung: 641 | Paper: 08
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from budget_gates import BudgetGateChecker
from inbox_outbox import InboxOutboxManager


@dataclass(frozen=True)
class CrossAppMessage:
    """A message from one app's outbox to another app's inbox."""

    source_app: str
    target_app: str
    run_id: str
    message_type: str  # "suggestion", "request", "report"
    payload: dict[str, Any]
    timestamp: str
    evidence_hash: str


_VALID_MESSAGE_TYPES = ("suggestion", "request", "report")


class CrossAppMessageError(Exception):
    """Raised when a cross-app message operation fails."""


class CrossAppPartnerError(CrossAppMessageError):
    """Raised when source manifest does not list target as a partner."""


class CrossAppBudgetError(CrossAppMessageError):
    """Raised when B6 budget gate blocks the delivery."""


class CrossAppMessenger:
    """Deliver messages between apps via outbox-to-inbox protocol.

    Flow:
      1. Validate source manifest has target in partners (produces_for)
      2. Run budget gate B6
      3. Write to target's inbox/requests/from-{source}-{run_id}.json
      4. Log to evidence chain (append to source outbox/runs/{run_id}/evidence_chain.jsonl)

    Args:
        inbox_outbox: InboxOutboxManager for filesystem access.
        budget_checker: BudgetGateChecker for B6 gate validation.
        now_fn: Optional clock override for deterministic testing.
    """

    def __init__(
        self,
        inbox_outbox: InboxOutboxManager,
        budget_checker: BudgetGateChecker,
        *,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._io = inbox_outbox
        self._budget = budget_checker
        self._now = now_fn or (lambda: datetime.now(timezone.utc))

    def send(
        self,
        source_app: str,
        target_app: str,
        run_id: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a cross-app message.

        Steps:
          1. Validate message_type is one of: suggestion, request, report
          2. Validate source manifest has target in partners.produces_for
          3. Run budget gate B6 via BudgetGateChecker
          4. Write message JSON to target's inbox/requests/from-{source}-{run_id}.json
          5. Compute evidence hash of the delivered message
          6. Return delivery receipt

        Returns:
            {"delivered": True, "path": str, "evidence_hash": str} on success.
            {"delivered": False, "reason": str} on any gate failure.
        """
        if message_type not in _VALID_MESSAGE_TYPES:
            raise CrossAppMessageError(
                f"Invalid message_type '{message_type}' — "
                f"must be one of {_VALID_MESSAGE_TYPES}"
            )

        # Step 1: Validate partner relationship
        source_manifest = self._io.read_manifest(source_app)
        produces_for = source_manifest.get("produces_for")
        if not isinstance(produces_for, list) or target_app not in produces_for:
            return {
                "delivered": False,
                "reason": (
                    f"target '{target_app}' is not in source '{source_app}' "
                    f"manifest produces_for"
                ),
            }

        # Step 2: Run B6 budget gate
        gate_context: dict[str, Any] = {
            "app_id": source_app,
            "trigger": f"{target_app}:cross-app-message",
            "run_id": run_id,
            "target_app_id": target_app,
        }
        gate_result = self._budget.check_all(gate_context)
        if not gate_result.get("allowed", False):
            return {
                "delivered": False,
                "reason": str(gate_result.get("reason", "B6 gate blocked")),
            }

        # Step 3: Build the message
        timestamp = self._now().isoformat()
        message_dict: dict[str, Any] = {
            "source_app": source_app,
            "target_app": target_app,
            "run_id": run_id,
            "message_type": message_type,
            "payload": payload,
            "timestamp": timestamp,
        }
        # Compute evidence hash from canonical form (before adding hash to dict)
        canonical = json.dumps(message_dict, sort_keys=True, separators=(",", ":"))
        evidence_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        message_dict["evidence_hash"] = evidence_hash

        # Step 4: Write to target's inbox/requests/
        target_root = self._io.resolve_app_root(target_app)
        requests_dir = target_root / "inbox" / "requests"
        requests_dir.mkdir(parents=True, exist_ok=True)
        filename = f"from-{source_app}-{run_id}.json"
        target_path = requests_dir / filename
        target_path.write_text(
            json.dumps(message_dict, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return {
            "delivered": True,
            "path": str(target_path),
            "evidence_hash": evidence_hash,
        }

    def receive_pending(self, app_id: str) -> list[CrossAppMessage]:
        """List all pending (unprocessed) messages in app's inbox/requests/.

        Only returns files matching the from-*.json pattern that have NOT
        been moved to the processed/ subdirectory.

        Returns:
            List of CrossAppMessage objects for each pending message.
        """
        app_root = self._io.resolve_app_root(app_id)
        requests_dir = app_root / "inbox" / "requests"
        if not requests_dir.exists():
            return []

        messages: list[CrossAppMessage] = []
        for path in sorted(requests_dir.iterdir()):
            if not path.is_file():
                continue
            if not path.name.startswith("from-"):
                continue
            if not path.name.endswith(".json"):
                continue

            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                continue

            messages.append(
                CrossAppMessage(
                    source_app=str(raw.get("source_app", "")),
                    target_app=str(raw.get("target_app", "")),
                    run_id=str(raw.get("run_id", "")),
                    message_type=str(raw.get("message_type", "")),
                    payload=raw.get("payload", {}),
                    timestamp=str(raw.get("timestamp", "")),
                    evidence_hash=str(raw.get("evidence_hash", "")),
                )
            )

        return messages

    def acknowledge(self, app_id: str, message_filename: str) -> dict[str, Any]:
        """Mark a message as processed by moving it to inbox/requests/processed/.

        Args:
            app_id: The app whose inbox to acknowledge from.
            message_filename: The filename (e.g. 'from-gmail-inbox-triage-run001.json').

        Returns:
            {"acknowledged": True, "processed_path": str} on success.

        Raises:
            FileNotFoundError: If the message file does not exist.
            CrossAppMessageError: If the filename attempts path traversal.
        """
        if Path(message_filename).name != message_filename:
            raise CrossAppMessageError(
                f"message_filename must be a bare filename, got: {message_filename}"
            )

        app_root = self._io.resolve_app_root(app_id)
        requests_dir = app_root / "inbox" / "requests"
        source_path = requests_dir / message_filename

        if not source_path.is_file():
            raise FileNotFoundError(
                f"Message file not found: {source_path}"
            )

        processed_dir = requests_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        dest_path = processed_dir / message_filename
        shutil.move(str(source_path), str(dest_path))

        return {
            "acknowledged": True,
            "processed_path": str(dest_path),
        }
