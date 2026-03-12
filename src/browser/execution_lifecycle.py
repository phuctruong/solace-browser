"""Preview -> approve -> execute lifecycle for Solace day-one apps."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from inbox_outbox import InboxOutboxManager


GENESIS_HASH = "0" * 64
COOLDOWN_SECONDS: dict[str, int] = {
    "low": 0,
    "medium": 5,
    "high": 15,
    "critical": 30,
}


class ApprovalDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    TIMEOUT = "timeout"


class ExecutionState(str, Enum):
    TRIGGER = "TRIGGER"
    INTENT = "INTENT"
    BUDGET_CHECK = "BUDGET_CHECK"
    PREVIEW = "PREVIEW"
    PREVIEW_READY = "PREVIEW_READY"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"
    COOLDOWN = "COOLDOWN"
    E_SIGN = "E_SIGN"
    SEALED = "SEALED"
    EXECUTING = "EXECUTING"
    DONE = "DONE"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SEALED_ABORT = "SEALED_ABORT"
    EVIDENCE_SEAL = "EVIDENCE_SEAL"


@dataclass(frozen=True)
class LifecycleResult:
    run_id: str
    app_id: str
    state: ExecutionState
    preview: str | None
    sealed_output_path: Path | None
    evidence_path: Path
    block_reason: str | None = None


class ExecutionLifecycleManager:
    """Run the diagram-14 lifecycle using file-backed evidence."""

    def __init__(
        self,
        *,
        solace_home: str | Path | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._manager = InboxOutboxManager(solace_home=solace_home)
        self._sleep = sleep_fn or time.sleep
        self._now = now_fn or (lambda: datetime.now(timezone.utc))

    def run(
        self,
        *,
        app_id: str,
        trigger: str,
        approval_decision: ApprovalDecision,
        preview_callback: Callable[[dict[str, Any]], dict[str, Any]],
        execute_callback: Callable[[dict[str, Any]], dict[str, Any]],
        budget_check: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        risk_level: str = "low",
        user_id: str = "guest",
        meaning: str = "approved",
    ) -> LifecycleResult:
        self._manager.validate_inbox(app_id)
        run_id = self._build_run_id(app_id)
        app_root = self._manager.resolve_app_root(app_id)
        run_root = app_root / "outbox" / "runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)
        evidence_path = run_root / "evidence_chain.jsonl"
        chain = _EvidenceChain(evidence_path, now_fn=self._now)
        preview_path: Path | None = None
        preview_text: str | None = None
        context = {"app_id": app_id, "trigger": trigger, "run_id": run_id}

        chain.append(ExecutionState.TRIGGER, {"trigger": trigger})
        chain.append(ExecutionState.INTENT, {"intent": f"{app_id}:{trigger}"})
        chain.append(ExecutionState.BUDGET_CHECK, {"gate": "B1-B5"})

        if budget_check is not None:
            gate_result = budget_check(context)
        else:
            gate_result = {"allowed": True}
        if not gate_result.get("allowed", False):
            reason = str(gate_result.get("reason", "blocked"))
            chain.append(ExecutionState.BLOCKED, {"reason": reason})
            chain.append(ExecutionState.EVIDENCE_SEAL, {"final_state": ExecutionState.BLOCKED.value})
            return LifecycleResult(
                run_id=run_id,
                app_id=app_id,
                state=ExecutionState.BLOCKED,
                preview=None,
                sealed_output_path=None,
                evidence_path=evidence_path,
                block_reason=reason,
            )

        chain.append(ExecutionState.PREVIEW, {"mode": "llm_once"})
        preview_payload = preview_callback(context)
        preview_text = str(preview_payload.get("preview", ""))
        sealed_preview = {
            "run_id": run_id,
            "app_id": app_id,
            "trigger": trigger,
            "preview": preview_text,
            "actions": preview_payload.get("actions", []),
        }
        written = self._manager.write_outbox(
            app_id,
            "previews",
            f"{run_id}.json",
            json.dumps(sealed_preview, indent=2, sort_keys=True) + "\n",
        )
        preview_path = Path(written["path"])
        chain.append(ExecutionState.PREVIEW_READY, {"preview_path": written["relative_path"]})

        if approval_decision == ApprovalDecision.REJECT:
            chain.append(ExecutionState.REJECTED, {"reason": "user_rejected"})
            chain.append(ExecutionState.SEALED_ABORT, {"reason": "user_rejected"})
            chain.append(ExecutionState.EVIDENCE_SEAL, {"final_state": ExecutionState.SEALED_ABORT.value})
            return LifecycleResult(run_id, app_id, ExecutionState.SEALED_ABORT, preview_text, preview_path, evidence_path)

        if approval_decision == ApprovalDecision.TIMEOUT:
            chain.append(ExecutionState.TIMEOUT, {"reason": "timeout_deny"})
            chain.append(ExecutionState.SEALED_ABORT, {"reason": "timeout_deny"})
            chain.append(ExecutionState.EVIDENCE_SEAL, {"final_state": ExecutionState.SEALED_ABORT.value})
            return LifecycleResult(run_id, app_id, ExecutionState.SEALED_ABORT, preview_text, preview_path, evidence_path)

        chain.append(ExecutionState.APPROVED, {"meaning": meaning})
        cooldown_seconds = COOLDOWN_SECONDS.get(risk_level, COOLDOWN_SECONDS["low"])
        chain.append(ExecutionState.COOLDOWN, {"seconds": cooldown_seconds})
        if cooldown_seconds > 0:
            self._sleep(cooldown_seconds)
        if user_id != "guest":
            chain.append(ExecutionState.E_SIGN, {"user_id": user_id, "meaning": meaning})

        preview_path.chmod(0o444)
        chain.append(ExecutionState.SEALED, {"path": str(preview_path.relative_to(app_root))})
        chain.append(ExecutionState.EXECUTING, {"mode": "cpu_replay"})
        execution_result = execute_callback(sealed_preview)
        status = str(execution_result.get("status", "success")).lower()
        if status == "success":
            final_state = ExecutionState.DONE
            chain.append(ExecutionState.DONE, {"actions_summary": execution_result.get("actions_summary", "")})
            self._write_run_manifest(run_root, run_id, trigger, execution_result)
            self._decrement_budget(app_id)
        else:
            final_state = ExecutionState.FAILED
            chain.append(ExecutionState.FAILED, {"error": execution_result.get("error", "execution failed")})
            self._write_run_manifest(run_root, run_id, trigger, execution_result)

        chain.append(ExecutionState.EVIDENCE_SEAL, {"final_state": final_state.value})
        return LifecycleResult(run_id, app_id, final_state, preview_text, preview_path, evidence_path)

    def _build_run_id(self, app_id: str) -> str:
        stamp = self._now().strftime("%Y%m%d%H%M%S%f")
        return f"{app_id}-{stamp}"

    def _decrement_budget(self, app_id: str) -> None:
        budget = self._manager.read_budget(app_id)
        remaining = budget.get("remaining_runs")
        if isinstance(remaining, int) and remaining > 0:
            budget["remaining_runs"] = remaining - 1
            self._manager.write_budget(app_id, budget)

    def _write_run_manifest(
        self,
        run_root: Path,
        run_id: str,
        trigger: str,
        execution_result: dict[str, Any],
    ) -> None:
        payload = {
            "run_id": run_id,
            "trigger": trigger,
            "actions_summary": execution_result.get("actions_summary", ""),
            "cost_usd": execution_result.get("cost_usd", 0.0),
            "state": "DONE" if str(execution_result.get("status", "success")).lower() == "success" else "FAILED",
            "created_at": self._now().isoformat(),
        }
        (run_root / "run.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class _EvidenceChain:
    def __init__(self, path: Path, *, now_fn: Callable[[], datetime]) -> None:
        self._path = path
        self._now = now_fn
        self._prev_hash = GENESIS_HASH
        self._index = 0

    def append(self, state: ExecutionState, detail: dict[str, Any]) -> None:
        record = {
            "entry_id": self._index,
            "timestamp": self._now().isoformat(),
            "state": state.value,
            "detail": detail,
            "prev_hash": self._prev_hash,
        }
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
        entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        record["entry_hash"] = entry_hash
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        self._prev_hash = entry_hash
        self._index += 1
