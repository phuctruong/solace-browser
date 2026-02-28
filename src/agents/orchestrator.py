"""
AgentOrchestrator — multi-step, parallel workflow execution.

Features:
  - plan(intent, scopes) → WorkflowPlan (decompose into ordered steps)
  - execute(plan) → results with partial completion support
  - Parallel execution: independent steps run concurrently (threading)
  - Dependency tracking: step waits until all blockers complete
  - Rollback: compensating actions attempted on completed steps when critical step fails
  - Evidence: each step produces a full evidence bundle

Rung: 641 (local correctness)
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# StepEvidence — per-step execution evidence bundle
# ---------------------------------------------------------------------------

@dataclass
class StepEvidence:
    """
    Evidence bundle produced by executing a single workflow step.

    Fields:
        step_id:       Step identifier (e.g. 'step_001').
        task_id:       TaskEnvelope.task_id that was dispatched for this step.
        agent_id:      Agent that handled this step (or None if not dispatched).
        status:        'success', 'failed', 'skipped', or 'rolled_back'.
        input_summary: String summary of the step's input payload.
        output:        Execution output (may be None on failure).
        scope_used:    Scopes exercised by this step.
        latency_ms:    Execution latency in integer milliseconds.
        error_code:    Error code if status != 'success'.
        error_detail:  Human-readable error description.
        executed_at:   ISO8601 UTC timestamp when execution started.
    """

    step_id: str
    task_id: str
    agent_id: Optional[str]
    status: str
    input_summary: str
    output: Optional[Any]
    scope_used: List[str]
    latency_ms: int
    error_code: Optional[str]
    error_detail: Optional[str]
    executed_at: str


# ---------------------------------------------------------------------------
# WorkflowPlan — decomposed multi-step plan
# ---------------------------------------------------------------------------

@dataclass
class WorkflowPlan:
    """
    A multi-step execution plan produced by AgentOrchestrator.plan().

    Fields:
        plan_id:      Unique plan identifier (UUID4).
        intent:       Natural-language description of the overall goal.
        scopes:       OAuth3 scopes required across all steps.
        steps:        Ordered list of TaskEnvelope objects (one per step).
        dependencies: Mapping of step_id → list of step_ids that must complete first.
        created_at:   ISO8601 UTC timestamp of plan creation.
        metadata:     Arbitrary plan-level metadata.
    """

    plan_id: str
    intent: str
    scopes: List[str]
    steps: List[Any]            # List[TaskEnvelope]
    dependencies: Dict[str, List[str]]
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.plan_id:
            raise ValueError("plan_id must not be empty")
        if not self.intent:
            raise ValueError("intent must not be empty")
        if self.steps is None:
            raise ValueError("steps must not be None (null != zero)")
        if self.dependencies is None:
            raise ValueError("dependencies must not be None (null != zero)")

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def get_step_by_id(self, step_id: str) -> Optional[Any]:
        """Return the TaskEnvelope with matching task_id, or None."""
        for step in self.steps:
            if step.task_id == step_id:
                return step
        return None

    def execution_order(self) -> List[List[str]]:
        """
        Topological sort of steps respecting dependencies.

        Returns list of batches (each batch can run in parallel).
        Each batch is a list of step task_ids whose dependencies are all satisfied
        by previous batches.
        """
        # Build in-degree map
        step_ids = [s.task_id for s in self.steps]
        in_degree: Dict[str, int] = {sid: 0 for sid in step_ids}
        dependents: Dict[str, List[str]] = {sid: [] for sid in step_ids}

        for sid, blockers in self.dependencies.items():
            for blocker in blockers:
                in_degree[sid] = in_degree.get(sid, 0) + 1
                if blocker in dependents:
                    dependents[blocker].append(sid)

        batches: List[List[str]] = []
        ready: Set[str] = {sid for sid, deg in in_degree.items() if deg == 0}

        while ready:
            batch = sorted(ready)  # deterministic ordering within a batch
            batches.append(batch)
            next_ready: Set[str] = set()
            for sid in batch:
                for dep in dependents.get(sid, []):
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        next_ready.add(dep)
            ready = next_ready

        return batches


# ---------------------------------------------------------------------------
# ExecutionResult — result of plan execution
# ---------------------------------------------------------------------------

@dataclass
class ExecutionResult:
    """
    Result of AgentOrchestrator.execute().

    Fields:
        plan_id:          Plan identifier.
        status:           'completed', 'partial', or 'failed'.
        step_evidence:    List of StepEvidence, one per executed step.
        completed_steps:  step_ids that succeeded.
        failed_steps:     step_ids that failed.
        rolled_back_steps: step_ids that were rolled back.
        total_latency_ms: Total wall-clock execution latency in integer milliseconds.
        executed_at:      ISO8601 UTC timestamp of execution start.
    """

    plan_id: str
    status: str
    step_evidence: List[StepEvidence]
    completed_steps: List[str]
    failed_steps: List[str]
    rolled_back_steps: List[str]
    total_latency_ms: int
    executed_at: str

    @property
    def success(self) -> bool:
        return self.status == "completed"

    @property
    def partial(self) -> bool:
        return self.status == "partial"


# ---------------------------------------------------------------------------
# AgentOrchestrator
# ---------------------------------------------------------------------------

class AgentOrchestrator:
    """
    Multi-step, parallel workflow orchestrator.

    Uses AgentRouter internally for per-step dispatching.
    Steps with no mutual dependencies execute concurrently (threading).
    Steps blocked by incomplete dependencies wait synchronously.

    Rollback:
        When a critical step fails, compensating actions are attempted
        on all previously completed steps (in reverse order).
        'Critical' means the step has no fallback and failure must abort the plan.

    Usage:
        router = AgentRouter()
        # ... register agents ...
        orchestrator = AgentOrchestrator(router)
        plan = orchestrator.plan("send linkedin post then email summary",
                                 ["linkedin.post.text", "gmail.send.email"])
        result = orchestrator.execute(plan, token=my_token)
    """

    def __init__(self, router: Any) -> None:
        """
        Initialize with an AgentRouter instance.

        Args:
            router: AgentRouter used for per-step dispatch.
        """
        self._router = router

    # -------------------------------------------------------------------------
    # Plan
    # -------------------------------------------------------------------------

    def plan(
        self,
        intent: str,
        scopes: List[str],
        token_id: str = "plan-token",
        step_payloads: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[Dict[str, List[str]]] = None,
    ) -> WorkflowPlan:
        """
        Decompose a high-level intent into a WorkflowPlan.

        Each unique platform in scopes becomes one step.
        If step_payloads is provided, it overrides the auto-generated payloads.
        If dependencies is provided, it is used directly; otherwise no deps.

        Args:
            intent:        Natural-language description of the overall goal.
            scopes:        All OAuth3 scopes required across the full workflow.
            token_id:      AgencyToken ID to bind to each step envelope.
            step_payloads: Optional list of per-step payload dicts.
            dependencies:  Optional dict of step_task_id → [blocker_task_ids].

        Returns:
            WorkflowPlan with one TaskEnvelope per platform group.
        """
        from .router import TaskEnvelope

        from collections import defaultdict

        # Group scopes by platform
        platform_scopes: Dict[str, List[str]] = defaultdict(list)
        for scope in scopes:
            platform = scope.split(".")[0] if "." in scope else "general"
            platform_scopes[platform].append(scope)

        steps: List[TaskEnvelope] = []
        now = datetime.now(timezone.utc).isoformat()

        for i, (platform, platform_s) in enumerate(sorted(platform_scopes.items())):
            payload = {}
            if step_payloads and i < len(step_payloads):
                payload = step_payloads[i]
            else:
                payload = {"platform": platform, "intent": intent}

            envelope = TaskEnvelope(
                task_id=str(uuid.uuid4()),
                intent=f"{intent} [{platform}]",
                required_scopes=platform_s,
                priority=3,
                payload=payload,
                token_id=token_id,
                created_at=now,
            )
            steps.append(envelope)

        plan_id = str(uuid.uuid4())
        deps = dependencies or {}

        return WorkflowPlan(
            plan_id=plan_id,
            intent=intent,
            scopes=list(scopes),
            steps=steps,
            dependencies=deps,
            created_at=now,
        )

    # -------------------------------------------------------------------------
    # Execute
    # -------------------------------------------------------------------------

    def execute(
        self,
        plan: WorkflowPlan,
        token: Any = None,
        executor: Any = None,
        critical_steps: Optional[Set[str]] = None,
        rollback_fn: Optional[Callable[[str, StepEvidence], None]] = None,
    ) -> ExecutionResult:
        """
        Execute a WorkflowPlan with parallel independent steps.

        Args:
            plan:          WorkflowPlan to execute.
            token:         AgencyToken for OAuth3 enforcement (passed to router.dispatch).
            executor:      Optional callable(envelope, agent) → dict for custom execution.
            critical_steps: Set of step task_ids where failure aborts plan + triggers rollback.
                           If None, all steps are treated as critical.
            rollback_fn:   Optional callable(step_id, evidence) for custom rollback logic.

        Returns:
            ExecutionResult with per-step evidence and aggregate status.
        """
        import time as _time

        executed_at = datetime.now(timezone.utc).isoformat()
        t_wall_start = _time.monotonic()

        if critical_steps is None:
            # Default: all steps are critical
            critical_steps = {s.task_id for s in plan.steps}

        # Per-step results (populated by worker threads)
        step_evidence_map: Dict[str, StepEvidence] = {}
        step_status_map: Dict[str, str] = {}  # task_id → 'success'|'failed'
        lock = threading.Lock()
        abort_flag = threading.Event()

        completed_steps: List[str] = []
        failed_steps: List[str] = []
        rolled_back_steps: List[str] = []

        def execute_step(envelope: Any) -> None:
            """Worker: dispatch one step and record evidence."""
            if abort_flag.is_set():
                # Plan already aborted — skip this step
                ev = StepEvidence(
                    step_id=envelope.task_id,
                    task_id=envelope.task_id,
                    agent_id=None,
                    status="skipped",
                    input_summary=str(envelope.payload)[:200],
                    output=None,
                    scope_used=list(envelope.required_scopes),
                    latency_ms=0,
                    error_code="PLAN_ABORTED",
                    error_detail="Plan aborted by earlier critical failure",
                    executed_at=datetime.now(timezone.utc).isoformat(),
                )
                with lock:
                    step_evidence_map[envelope.task_id] = ev
                    step_status_map[envelope.task_id] = "skipped"
                return

            t0 = _time.monotonic()
            dispatch_result = self._router.dispatch(
                envelope, token=token, executor=executor
            )
            latency = int((_time.monotonic() - t0) * 1000)

            ev = StepEvidence(
                step_id=envelope.task_id,
                task_id=envelope.task_id,
                agent_id=dispatch_result.agent_id,
                status=dispatch_result.status,
                input_summary=str(envelope.payload)[:200],
                output=dispatch_result.output,
                scope_used=list(envelope.required_scopes),
                latency_ms=latency,
                error_code=dispatch_result.error_code,
                error_detail=dispatch_result.error_detail,
                executed_at=datetime.now(timezone.utc).isoformat(),
            )

            with lock:
                step_evidence_map[envelope.task_id] = ev
                step_status_map[envelope.task_id] = dispatch_result.status

                if dispatch_result.status == "success":
                    completed_steps.append(envelope.task_id)
                else:
                    failed_steps.append(envelope.task_id)
                    if envelope.task_id in critical_steps:
                        abort_flag.set()

        # Execute in topological batches
        batches = plan.execution_order()

        for batch in batches:
            if abort_flag.is_set():
                break

            batch_envelopes = [plan.get_step_by_id(sid) for sid in batch]
            batch_envelopes = [e for e in batch_envelopes if e is not None]

            if len(batch_envelopes) == 1:
                # Single step: run inline (no thread overhead)
                execute_step(batch_envelopes[0])
            else:
                # Multiple independent steps: run in parallel threads
                threads = []
                for envelope in batch_envelopes:
                    t = threading.Thread(
                        target=execute_step,
                        args=(envelope,),
                        daemon=True,
                    )
                    threads.append(t)
                    t.start()
                for t in threads:
                    t.join()

        # Rollback: if plan aborted, attempt compensating actions on completed steps
        if abort_flag.is_set() and completed_steps:
            for step_id in reversed(list(completed_steps)):
                ev = step_evidence_map.get(step_id)
                if ev is not None:
                    if rollback_fn is not None:
                        try:
                            rollback_fn(step_id, ev)
                        except (RuntimeError, TypeError, ValueError) as exc:
                            logger.warning("Rollback handler failed for %s: %s", step_id, exc)
                    rolled_back_steps.append(step_id)
                    # Update evidence status
                    rolled_ev = StepEvidence(
                        step_id=ev.step_id,
                        task_id=ev.task_id,
                        agent_id=ev.agent_id,
                        status="rolled_back",
                        input_summary=ev.input_summary,
                        output=ev.output,
                        scope_used=ev.scope_used,
                        latency_ms=ev.latency_ms,
                        error_code="ROLLED_BACK",
                        error_detail="Compensating rollback due to critical step failure",
                        executed_at=ev.executed_at,
                    )
                    step_evidence_map[step_id] = rolled_ev

        # Determine aggregate status
        if failed_steps and abort_flag.is_set():
            agg_status = "failed"
        elif failed_steps:
            agg_status = "partial"
        else:
            agg_status = "completed"

        total_latency_ms = int((_time.monotonic() - t_wall_start) * 1000)

        # Collect evidence in plan step order
        ordered_evidence = []
        for step in plan.steps:
            ev = step_evidence_map.get(step.task_id)
            if ev is not None:
                ordered_evidence.append(ev)

        return ExecutionResult(
            plan_id=plan.plan_id,
            status=agg_status,
            step_evidence=ordered_evidence,
            completed_steps=list(completed_steps),
            failed_steps=list(failed_steps),
            rolled_back_steps=list(rolled_back_steps),
            total_latency_ms=total_latency_ms,
            executed_at=executed_at,
        )
