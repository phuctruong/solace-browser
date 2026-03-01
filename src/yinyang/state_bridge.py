"""YinyangStateBridge — connects the execution lifecycle FSM to the Yinyang chat interface.

Tracks active runs per FSM state, surfaces preview text + approve/reject actions,
and enforces the Anti-Clippy law: never auto-approves.

Channel [7] — Context + Tools.  Rung: 65537.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from execution_lifecycle import (
    ApprovalDecision,
    ExecutionLifecycleManager,
    ExecutionState,
    LifecycleResult,
)

logger = logging.getLogger("solace-browser.yinyang.state_bridge")


class RiskLevel(str, Enum):
    """Risk levels for execution runs."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# States where the bottom rail should auto-expand
AUTO_EXPAND_STATES = frozenset({
    ExecutionState.PREVIEW_READY,
    ExecutionState.BLOCKED,
    ExecutionState.FAILED,
})

# States where the bottom rail should auto-collapse
AUTO_COLLAPSE_STATES = frozenset({
    ExecutionState.DONE,
    ExecutionState.SEALED_ABORT,
})

# Color mapping for top rail state indicator
STATE_COLOR_MAP: dict[ExecutionState, str] = {
    ExecutionState.TRIGGER: "blue",
    ExecutionState.INTENT: "blue",
    ExecutionState.BUDGET_CHECK: "blue",
    ExecutionState.PREVIEW: "blue",
    ExecutionState.PREVIEW_READY: "yellow",
    ExecutionState.APPROVED: "blue",
    ExecutionState.REJECTED: "red",
    ExecutionState.TIMEOUT: "red",
    ExecutionState.COOLDOWN: "blue",
    ExecutionState.E_SIGN: "blue",
    ExecutionState.SEALED: "blue",
    ExecutionState.EXECUTING: "blue",
    ExecutionState.DONE: "green",
    ExecutionState.FAILED: "red",
    ExecutionState.BLOCKED: "red",
    ExecutionState.SEALED_ABORT: "red",
    ExecutionState.EVIDENCE_SEAL: "green",
}


class RunNotFoundError(Exception):
    """Raised when a run_id is not tracked by the state bridge."""


class RunNotInPreviewError(Exception):
    """Raised when approve/reject is called on a run not in PREVIEW_READY state."""


@dataclass
class ActiveRun:
    """Tracks a single execution run through the FSM."""
    run_id: str
    app_id: str
    trigger: str
    state: ExecutionState
    risk_level: str
    preview_text: str = ""
    block_reason: str = ""
    error_detail: str = ""
    result: LifecycleResult | None = None
    user_decision: ApprovalDecision | None = None
    decision_user_id: str = ""
    decision_meaning: str = ""
    decision_reason: str = ""
    _decision_event: threading.Event = field(default_factory=threading.Event, repr=False)


class YinyangStateBridge:
    """Connects the execution lifecycle FSM to the Yinyang chat interface.

    Tracks current FSM state per active run. Provides methods to get current
    state for display, handle approve/reject actions from the UI, and list
    runs awaiting user action.

    Anti-Clippy law: NEVER auto-approves. All approvals require explicit
    user action with a user_id and meaning.
    """

    def __init__(self, lifecycle_manager: ExecutionLifecycleManager) -> None:
        self._lifecycle = lifecycle_manager
        self._runs: dict[str, ActiveRun] = {}
        self._lock = threading.Lock()

    def get_current_state(self, run_id: str) -> dict[str, Any]:
        """Return current state info for a run.

        Returns dict with keys:
            state: str — current ExecutionState value
            preview_text: str — preview content (if available)
            can_approve: bool — True only when PREVIEW_READY
            can_reject: bool — True only when PREVIEW_READY
            risk_level: str — risk level of this run
            color: str — top rail color for this state
            auto_expand: bool — whether bottom rail should auto-expand
            auto_collapse: bool — whether bottom rail should auto-collapse
            block_reason: str — reason for BLOCKED state (if applicable)
            error_detail: str — error details for FAILED state (if applicable)
            app_id: str — the app this run belongs to
        """
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFoundError(f"Run not found: {run_id}")

            state = run.state
            return {
                "state": state.value,
                "preview_text": run.preview_text,
                "can_approve": state == ExecutionState.PREVIEW_READY,
                "can_reject": state == ExecutionState.PREVIEW_READY,
                "risk_level": run.risk_level,
                "color": STATE_COLOR_MAP.get(state, "blue"),
                "auto_expand": state in AUTO_EXPAND_STATES,
                "auto_collapse": state in AUTO_COLLAPSE_STATES,
                "block_reason": run.block_reason,
                "error_detail": run.error_detail,
                "app_id": run.app_id,
            }

    def approve(self, run_id: str, user_id: str, meaning: str) -> dict[str, Any]:
        """User approves the preview. Returns new state dict.

        Anti-Clippy: user_id and meaning are required. Empty values are rejected.
        """
        if not user_id:
            raise ValueError("user_id is required for approval (Anti-Clippy law)")
        if not meaning:
            raise ValueError("meaning is required for approval (Anti-Clippy law)")

        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFoundError(f"Run not found: {run_id}")
            if run.state != ExecutionState.PREVIEW_READY:
                raise RunNotInPreviewError(
                    f"Run {run_id} is in state {run.state.value}, not PREVIEW_READY"
                )
            run.user_decision = ApprovalDecision.APPROVE
            run.decision_user_id = user_id
            run.decision_meaning = meaning
            run._decision_event.set()

        # Wait briefly for the lifecycle thread to pick up the decision
        # and advance state. We do NOT block indefinitely — the caller
        # can poll get_current_state for the final result.
        run._decision_event.wait(timeout=0.1)

        return self.get_current_state(run_id)

    def reject(self, run_id: str, user_id: str, reason: str) -> dict[str, Any]:
        """User rejects the preview. Returns new state dict.

        Anti-Clippy: user_id and reason are required. Empty values are rejected.
        """
        if not user_id:
            raise ValueError("user_id is required for rejection (Anti-Clippy law)")
        if not reason:
            raise ValueError("reason is required for rejection (Anti-Clippy law)")

        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFoundError(f"Run not found: {run_id}")
            if run.state != ExecutionState.PREVIEW_READY:
                raise RunNotInPreviewError(
                    f"Run {run_id} is in state {run.state.value}, not PREVIEW_READY"
                )
            run.user_decision = ApprovalDecision.REJECT
            run.decision_user_id = user_id
            run.decision_reason = reason
            run._decision_event.set()

        run._decision_event.wait(timeout=0.1)

        return self.get_current_state(run_id)

    def list_active_runs(self) -> list[dict[str, Any]]:
        """Return all runs in PREVIEW_READY state (awaiting user action)."""
        with self._lock:
            result = []
            for run_id, run in self._runs.items():
                if run.state == ExecutionState.PREVIEW_READY:
                    result.append({
                        "run_id": run_id,
                        "app_id": run.app_id,
                        "state": run.state.value,
                        "preview_text": run.preview_text,
                        "risk_level": run.risk_level,
                    })
            return result

    def start_run(
        self,
        *,
        app_id: str,
        trigger: str,
        preview_callback: Callable[[dict[str, Any]], dict[str, Any]],
        execute_callback: Callable[[dict[str, Any]], dict[str, Any]],
        budget_check: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        risk_level: str = "low",
    ) -> str:
        """Start an execution run asynchronously.

        The run proceeds through the lifecycle FSM. When PREVIEW_READY is
        reached, it pauses and waits for approve() or reject() from the UI.

        Returns the run_id for tracking. Use get_current_state(run_id) to
        poll state, or list_active_runs() to find runs awaiting action.
        """
        # Generate a run_id using the lifecycle manager's internal method
        run_id = self._lifecycle._build_run_id(app_id)

        run = ActiveRun(
            run_id=run_id,
            app_id=app_id,
            trigger=trigger,
            state=ExecutionState.TRIGGER,
            risk_level=risk_level,
        )

        with self._lock:
            self._runs[run_id] = run

        thread = threading.Thread(
            target=self._run_lifecycle,
            args=(run, preview_callback, execute_callback, budget_check, risk_level),
            daemon=True,
            name=f"yy-run-{run_id}",
        )
        thread.start()

        return run_id

    def start_run_sync(
        self,
        *,
        app_id: str,
        trigger: str,
        preview_callback: Callable[[dict[str, Any]], dict[str, Any]],
        execute_callback: Callable[[dict[str, Any]], dict[str, Any]],
        budget_check: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        risk_level: str = "low",
        approval_decision: ApprovalDecision | None = None,
        user_id: str = "guest",
        meaning: str = "approved",
    ) -> str:
        """Start an execution run synchronously (for testing or scripted flows).

        If approval_decision is provided, it is used directly without waiting
        for UI interaction. If None, the run pauses at PREVIEW_READY.
        """
        run_id = self._lifecycle._build_run_id(app_id)

        run = ActiveRun(
            run_id=run_id,
            app_id=app_id,
            trigger=trigger,
            state=ExecutionState.TRIGGER,
            risk_level=risk_level,
        )

        with self._lock:
            self._runs[run_id] = run

        if approval_decision is not None:
            # Direct execution — no UI wait
            result = self._lifecycle.run(
                app_id=app_id,
                trigger=trigger,
                approval_decision=approval_decision,
                preview_callback=self._wrapping_preview_callback(run, preview_callback),
                execute_callback=self._wrapping_execute_callback(run, execute_callback),
                budget_check=self._wrapping_budget_check(run, budget_check),
                risk_level=risk_level,
                user_id=user_id,
                meaning=meaning,
            )
            self._finalize_run(run, result)
        else:
            # Pause at PREVIEW_READY — caller must use approve/reject
            self._run_lifecycle(run, preview_callback, execute_callback, budget_check, risk_level)

        return run_id

    def get_run_result(self, run_id: str) -> LifecycleResult | None:
        """Get the final LifecycleResult for a completed run, or None if still active."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFoundError(f"Run not found: {run_id}")
            return run.result

    def _run_lifecycle(
        self,
        run: ActiveRun,
        preview_callback: Callable[[dict[str, Any]], dict[str, Any]],
        execute_callback: Callable[[dict[str, Any]], dict[str, Any]],
        budget_check: Callable[[dict[str, Any]], dict[str, Any]] | None,
        risk_level: str,
    ) -> None:
        """Run the execution lifecycle, pausing at PREVIEW_READY for user decision.

        Delegates to _run_lifecycle_interactive which replicates the
        lifecycle logic with proper pause/resume for UI interaction.
        """
        self._run_lifecycle_interactive(
            run, preview_callback, execute_callback, budget_check, risk_level
        )

    def _run_lifecycle_interactive(
        self,
        run: ActiveRun,
        preview_callback: Callable[[dict[str, Any]], dict[str, Any]],
        execute_callback: Callable[[dict[str, Any]], dict[str, Any]],
        budget_check: Callable[[dict[str, Any]], dict[str, Any]] | None,
        risk_level: str,
    ) -> None:
        """Interactive lifecycle: runs FSM steps with a pause at PREVIEW_READY.

        Replicates ExecutionLifecycleManager.run() but splits it into
        pre-preview and post-decision phases so the UI can approve/reject.
        """
        context = {
            "app_id": run.app_id,
            "trigger": run.trigger,
            "run_id": run.run_id,
        }

        # Phase 1: Budget check
        with self._lock:
            run.state = ExecutionState.BUDGET_CHECK

        if budget_check is not None:
            gate_result = budget_check(context)
        else:
            gate_result = {"allowed": False, "reason": "No budget checker configured"}

        if not gate_result.get("allowed", False):
            reason = str(gate_result.get("reason", "blocked"))
            with self._lock:
                run.state = ExecutionState.BLOCKED
                run.block_reason = reason
            logger.info(f"[StateBridge] Run {run.run_id} → BLOCKED: {reason}")
            return

        # Phase 2: Generate preview
        with self._lock:
            run.state = ExecutionState.PREVIEW

        preview_payload = preview_callback(context)
        preview_text = str(preview_payload.get("preview", ""))

        with self._lock:
            run.preview_text = preview_text
            run.state = ExecutionState.PREVIEW_READY

        logger.info(f"[StateBridge] Run {run.run_id} → PREVIEW_READY")

        # Phase 3: Wait for user decision (Anti-Clippy: NEVER auto-approve)
        run._decision_event.wait()

        decision = run.user_decision
        if decision == ApprovalDecision.REJECT:
            with self._lock:
                run.state = ExecutionState.SEALED_ABORT
            logger.info(f"[StateBridge] Run {run.run_id} → SEALED_ABORT (rejected)")

            # Now run the full lifecycle with REJECT to get proper evidence chain
            result = self._lifecycle.run(
                app_id=run.app_id,
                trigger=run.trigger,
                approval_decision=ApprovalDecision.REJECT,
                preview_callback=lambda _ctx: preview_payload,
                execute_callback=execute_callback,
                budget_check=lambda _ctx: {"allowed": True},
                risk_level=risk_level,
                user_id=run.decision_user_id or "guest",
                meaning=run.decision_reason or "rejected",
            )
            self._finalize_run(run, result)
            return

        if decision == ApprovalDecision.APPROVE:
            with self._lock:
                run.state = ExecutionState.APPROVED

            # Run the full lifecycle with APPROVE to get proper evidence chain
            result = self._lifecycle.run(
                app_id=run.app_id,
                trigger=run.trigger,
                approval_decision=ApprovalDecision.APPROVE,
                preview_callback=lambda _ctx: preview_payload,
                execute_callback=execute_callback,
                budget_check=lambda _ctx: {"allowed": True},
                risk_level=risk_level,
                user_id=run.decision_user_id or "guest",
                meaning=run.decision_meaning or "approved",
            )
            self._finalize_run(run, result)
            return

        # Timeout or unknown
        with self._lock:
            run.state = ExecutionState.SEALED_ABORT
        logger.info(f"[StateBridge] Run {run.run_id} → SEALED_ABORT (timeout)")

    def _wrapping_preview_callback(
        self,
        run: ActiveRun,
        original: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> Callable[[dict[str, Any]], dict[str, Any]]:
        """Wrap a preview callback to capture state transitions."""
        def wrapper(context: dict[str, Any]) -> dict[str, Any]:
            with self._lock:
                run.state = ExecutionState.PREVIEW
            result = original(context)
            with self._lock:
                run.preview_text = str(result.get("preview", ""))
            return result
        return wrapper

    def _wrapping_execute_callback(
        self,
        run: ActiveRun,
        original: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> Callable[[dict[str, Any]], dict[str, Any]]:
        """Wrap an execute callback to capture state transitions."""
        def wrapper(sealed: dict[str, Any]) -> dict[str, Any]:
            with self._lock:
                run.state = ExecutionState.EXECUTING
            result = original(sealed)
            status = str(result.get("status", "success")).lower()
            with self._lock:
                if status == "success":
                    run.state = ExecutionState.DONE
                else:
                    run.state = ExecutionState.FAILED
                    run.error_detail = str(result.get("error", "execution failed"))
            return result
        return wrapper

    def _wrapping_budget_check(
        self,
        run: ActiveRun,
        original: Callable[[dict[str, Any]], dict[str, Any]] | None,
    ) -> Callable[[dict[str, Any]], dict[str, Any]] | None:
        """Wrap a budget check to capture BLOCKED state."""
        if original is None:
            return None

        def wrapper(context: dict[str, Any]) -> dict[str, Any]:
            with self._lock:
                run.state = ExecutionState.BUDGET_CHECK
            result = original(context)
            if not result.get("allowed", False):
                with self._lock:
                    run.state = ExecutionState.BLOCKED
                    run.block_reason = str(result.get("reason", "blocked"))
            return result
        return wrapper

    def _finalize_run(self, run: ActiveRun, result: LifecycleResult) -> None:
        """Update run with final lifecycle result."""
        with self._lock:
            run.result = result
            run.state = result.state
            if result.block_reason:
                run.block_reason = result.block_reason
            if result.state == ExecutionState.FAILED:
                run.error_detail = run.error_detail or "execution failed"

    def top_rail_indicator(self, run_id: str) -> dict[str, str]:
        """Return compact state indicator for the top rail.

        Returns:
            app_name: str — the app_id for this run
            state: str — current FSM state value
            color: str — green/yellow/red/blue
            label: str — "{app_id}: {state}" display string
        """
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFoundError(f"Run not found: {run_id}")
            state = run.state
            color = STATE_COLOR_MAP.get(state, "blue")
            return {
                "app_name": run.app_id,
                "state": state.value,
                "color": color,
                "label": f"{run.app_id}: {state.value}",
            }

    def bottom_rail_payload(self, run_id: str) -> dict[str, Any]:
        """Return the bottom rail display payload for a run.

        The bottom rail:
        - Auto-expands when state is PREVIEW_READY, BLOCKED, or FAILED
        - Shows preview text + approve/reject buttons for PREVIEW_READY
        - Shows block reason for BLOCKED
        - Shows error details for FAILED
        - Collapses automatically on DONE or SEALED_ABORT
        """
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFoundError(f"Run not found: {run_id}")

            state = run.state
            payload: dict[str, Any] = {
                "run_id": run_id,
                "state": state.value,
                "auto_expand": state in AUTO_EXPAND_STATES,
                "auto_collapse": state in AUTO_COLLAPSE_STATES,
                "show_approve_reject": state == ExecutionState.PREVIEW_READY,
                "preview_text": "",
                "block_reason": "",
                "error_detail": "",
            }

            if state == ExecutionState.PREVIEW_READY:
                payload["preview_text"] = run.preview_text
            elif state == ExecutionState.BLOCKED:
                payload["block_reason"] = run.block_reason
            elif state == ExecutionState.FAILED:
                payload["error_detail"] = run.error_detail

            return payload
