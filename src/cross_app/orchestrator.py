"""Orchestrator runtime for apps that coordinate multiple child apps.

An orchestrator-type app reads its manifest (type=orchestrator, orchestrates=[app_ids]),
triggers each child app through the cross-app messenger, and collects results.

Design rules (Fallback Ban):
  - NO silent failures — if a child fails, it is recorded in the result
  - NO broad except — catch SPECIFIC exceptions only
  - NO fake orchestration — real message sends, real budget gates
  - Every child trigger is budget-gated independently

Auth: 65537 | Rung: 641 | Paper: 08
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from cross_app.message import CrossAppMessenger
from execution_lifecycle import ExecutionLifecycleManager
from inbox_outbox import InboxOutboxManager


class OrchestratorError(Exception):
    """Raised when an orchestrator operation fails."""


class NotAnOrchestratorError(OrchestratorError):
    """Raised when the app manifest type is not 'orchestrator'."""


class OrchestratorRuntime:
    """Execute orchestrator-type apps that coordinate multiple child apps.

    An orchestrator app's manifest must declare:
      - type: orchestrator
      - orchestrates: [list of child app_ids]
      - produces_for: [list of child app_ids] (for B6 partner validation)

    The runtime:
      1. Reads manifest and validates type=orchestrator
      2. Triggers each child app via CrossAppMessenger (budget-gated per child)
      3. Collects delivery receipts from each child
      4. Returns combined results with per-child status

    Args:
        messenger: CrossAppMessenger for sending messages to child apps.
        lifecycle: ExecutionLifecycleManager for reading app manifests.
        now_fn: Optional clock override for deterministic testing.
    """

    def __init__(
        self,
        messenger: CrossAppMessenger,
        lifecycle: ExecutionLifecycleManager,
        *,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._messenger = messenger
        self._lifecycle = lifecycle
        self._now = now_fn or (lambda: datetime.now(timezone.utc))
        self._runs: dict[str, dict[str, Any]] = {}

    def execute_orchestrator(
        self,
        orchestrator_app_id: str,
        trigger: str,
    ) -> dict[str, Any]:
        """Run an orchestrator app.

        Steps:
          1. Read manifest, validate type=orchestrator and orchestrates list
          2. Generate a unique orchestrator run_id
          3. For each child in orchestrates:
             a. Send a cross-app message (budget-gated via B6)
             b. Record delivery receipt or failure
          4. Return combined results

        Args:
            orchestrator_app_id: The app_id of the orchestrator app.
            trigger: The trigger string that initiated this orchestration.

        Returns:
            {
                "run_id": str,
                "orchestrator": str,
                "trigger": str,
                "children": {app_id: {delivered: bool, ...}, ...},
                "total_children": int,
                "delivered_count": int,
                "failed_count": int,
                "timestamp": str,
            }

        Raises:
            NotAnOrchestratorError: If manifest type is not 'orchestrator'.
            OrchestratorError: If orchestrates list is missing or empty.
        """
        io_manager = self._lifecycle._manager
        manifest = io_manager.read_manifest(orchestrator_app_id)

        manifest_type = manifest.get("type")
        if manifest_type != "orchestrator":
            raise NotAnOrchestratorError(
                f"App '{orchestrator_app_id}' has type='{manifest_type}', "
                f"expected type='orchestrator'"
            )

        orchestrates = manifest.get("orchestrates")
        if not isinstance(orchestrates, list) or len(orchestrates) == 0:
            raise OrchestratorError(
                f"App '{orchestrator_app_id}' manifest 'orchestrates' must be "
                f"a non-empty list of child app_ids"
            )

        run_id = f"orch-{orchestrator_app_id}-{uuid.uuid4().hex[:12]}"
        timestamp = self._now().isoformat()
        children_results: dict[str, dict[str, Any]] = {}
        delivered_count = 0
        failed_count = 0

        for child_app_id in orchestrates:
            result = self._messenger.send(
                source_app=orchestrator_app_id,
                target_app=child_app_id,
                run_id=run_id,
                message_type="request",
                payload={"trigger": trigger, "orchestrator_run_id": run_id},
            )
            children_results[child_app_id] = result
            if result.get("delivered", False):
                delivered_count += 1
            else:
                failed_count += 1

        run_status = {
            "run_id": run_id,
            "orchestrator": orchestrator_app_id,
            "trigger": trigger,
            "children": children_results,
            "total_children": len(orchestrates),
            "delivered_count": delivered_count,
            "failed_count": failed_count,
            "timestamp": timestamp,
        }

        self._runs[run_id] = run_status
        return run_status

    def get_orchestrator_status(self, run_id: str) -> dict[str, Any]:
        """Get status of an orchestrator run including child statuses.

        Args:
            run_id: The orchestrator run_id returned by execute_orchestrator.

        Returns:
            The full run status dict, or {"found": False} if run_id is unknown.
        """
        if run_id not in self._runs:
            return {"found": False, "run_id": run_id}

        status = dict(self._runs[run_id])
        status["found"] = True
        return status
