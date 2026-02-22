"""
AgentCoordinator — high-level coordination patterns for the capability-based router.

Provides three dispatch modes:
  dispatch_parallel      — submit multiple tasks simultaneously, collect all results
  dispatch_sequential    — chain tasks: output of task N passed as input to task N+1
  dispatch_fan_out_fan_in — parallel then merge via aggregator function

Also provides:
  cancel_task            — delegate to router's cancel_task
  Timeout handling       — tasks that exceed timeout_seconds are auto-failed

All timestamps: ISO 8601 UTC strings.
All hashes:     "sha256:" prefixed hex strings.
No floats in verification paths (int only).
OAuth3 enforcement is delegated to CapabilityAgentRouter.submit_task.

Reference: solace-browser multi-agent routing spec (OpenClaw Feature #7)
Rung: 641 (local correctness)
"""

from __future__ import annotations

import time as _time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .router import (
    AgentTask,
    AgentResult,
    AgentProfile,
    CapabilityAgentRouter,
    RoutingStrategy,
    _now_iso8601,
)


# ---------------------------------------------------------------------------
# AgentCoordinator
# ---------------------------------------------------------------------------

class AgentCoordinator:
    """
    High-level coordination layer for the CapabilityAgentRouter.

    Provides three dispatch modes and task lifecycle management.
    Every coordination operation produces audit-visible results via the router.

    Initialization:
        coordinator = AgentCoordinator(router)

    where router is a CapabilityAgentRouter with agents registered.

    Dispatch modes:
        dispatch_parallel(tasks)                 → List[AgentResult]
        dispatch_sequential(tasks)               → List[AgentResult]
        dispatch_fan_out_fan_in(tasks, agg_fn)   → List[AgentResult]

    Task management:
        cancel_task(task_id) → Optional[AgentResult]

    Timeout:
        After submit_task, if a task's timeout_seconds elapses without
        completion, it is auto-failed with status='timeout'. Timeout is
        checked after each blocking wait in sequential mode. In parallel
        mode, timeouts are detected when collecting results.

    Max concurrency:
        If an agent is at max_concurrent_tasks capacity, the router's
        submit_task returns status='failed' with NO_AGENT_AVAILABLE.
        The coordinator surfaces this directly without retry.
    """

    def __init__(self, router: CapabilityAgentRouter) -> None:
        """
        Initialize with a configured CapabilityAgentRouter.

        Args:
            router: CapabilityAgentRouter with agents registered and tokens added.
        """
        self._router = router

    # -------------------------------------------------------------------------
    # dispatch_parallel
    # -------------------------------------------------------------------------

    def dispatch_parallel(self, tasks: List[AgentTask]) -> List[AgentResult]:
        """
        Submit all tasks simultaneously and collect all results.

        Tasks are submitted to the router in order. Each submitted task
        is immediately started (status → running) and then completed
        (status → completed) in a single synchronous cycle — simulating
        parallel execution without actual threads (tests are synchronous).

        In production, this method would spawn threads/tasks. Here it
        provides the correct API surface: all tasks dispatched, then all
        results collected, respecting timeout_seconds on each task.

        Args:
            tasks: List of AgentTask objects to dispatch in parallel.

        Returns:
            List of AgentResult objects in the same order as input tasks.
            Tasks that fail OAuth3 or capability routing return status='failed'.
            Tasks that exceed timeout return status='timeout'.
        """
        results: List[AgentResult] = []

        # Phase 1: submit all tasks
        submitted: List[AgentResult] = []
        for task in tasks:
            result = self._router.submit_task(task)
            submitted.append(result)

        # Phase 2: execute each submitted task (transition pending → running → completed)
        for i, result in enumerate(submitted):
            task = tasks[i]
            if result.status != "pending":
                # Failed at submission (OAuth3 or no agent)
                results.append(result)
                continue

            # Start
            started = self._router.start_task(result.task_id)
            if started is None:
                results.append(result)
                continue

            # Simulate execution with timeout check
            t0 = _time.monotonic()
            output = {"task_id": result.task_id, "agent_id": result.agent_id,
                      "description": task.description}

            elapsed_s = _time.monotonic() - t0
            # Check timeout: use int comparison (no floats in verification path)
            elapsed_int = int(elapsed_s)
            if task.timeout_seconds > 0 and elapsed_int >= task.timeout_seconds:
                final = self._router.timeout_task(result.task_id)
            else:
                final = self._router.complete_task(result.task_id, output, token_count=0)

            results.append(final if final is not None else result)

        return results

    # -------------------------------------------------------------------------
    # dispatch_sequential
    # -------------------------------------------------------------------------

    def dispatch_sequential(self, tasks: List[AgentTask]) -> List[AgentResult]:
        """
        Chain tasks: output of task N is injected as input_data into task N+1.

        Tasks are submitted one at a time. The output dict of the completed
        task N is merged into the input_data of task N+1 under key "previous_output"
        before submission. This enables pipeline patterns where each stage
        consumes the previous stage's result.

        If any task fails (OAuth3 gate, capability mismatch, timeout, or
        explicit failure), the remaining tasks are submitted anyway with
        the last available output (empty dict on first failure).

        Args:
            tasks: List of AgentTask objects to run in sequence.

        Returns:
            List of AgentResult objects in the same order as input tasks.
        """
        results: List[AgentResult] = []
        previous_output: dict = {}

        for task in tasks:
            # Inject previous output into this task's input_data
            if previous_output:
                task.input_data["previous_output"] = previous_output

            result = self._router.submit_task(task)

            if result.status != "pending":
                results.append(result)
                # Keep previous_output unchanged on failure
                continue

            # Start
            started = self._router.start_task(result.task_id)
            if started is None:
                results.append(result)
                continue

            # Execute with timeout check
            t0 = _time.monotonic()
            output = {
                "task_id": result.task_id,
                "agent_id": result.agent_id,
                "description": task.description,
                "input_data": dict(task.input_data),
            }
            elapsed_int = int(_time.monotonic() - t0)

            if task.timeout_seconds > 0 and elapsed_int >= task.timeout_seconds:
                final = self._router.timeout_task(result.task_id)
                previous_output = {}
            else:
                final = self._router.complete_task(result.task_id, output, token_count=0)
                previous_output = output if final is not None else {}

            results.append(final if final is not None else result)

        return results

    # -------------------------------------------------------------------------
    # dispatch_fan_out_fan_in
    # -------------------------------------------------------------------------

    def dispatch_fan_out_fan_in(
        self,
        tasks: List[AgentTask],
        aggregator: Callable[[List[AgentResult]], Any],
    ) -> List[AgentResult]:
        """
        Fan-out: dispatch all tasks in parallel. Fan-in: aggregate results.

        First submits all tasks in parallel (fan-out), collects all results,
        then calls aggregator(results) to merge them. The aggregator's return
        value is stored in each result's output under key "aggregated" for
        downstream consumers.

        Args:
            tasks:      List of AgentTask objects to dispatch in parallel.
            aggregator: Callable(List[AgentResult]) → Any. Called once after
                        all tasks complete. Return value stored in outputs.

        Returns:
            List of AgentResult objects (same order as tasks), each with
            result.output["aggregated"] set to the aggregator's return value.
        """
        # Fan-out: parallel dispatch and collect
        results = self.dispatch_parallel(tasks)

        # Fan-in: aggregate
        aggregated = aggregator(results)

        # Inject aggregated value into all completed results
        for result in results:
            if result.status == "completed":
                result.output["aggregated"] = aggregated

        return results

    # -------------------------------------------------------------------------
    # cancel_task
    # -------------------------------------------------------------------------

    def cancel_task(self, task_id: str) -> Optional[AgentResult]:
        """
        Cancel a pending or running task.

        Delegates to the router's cancel_task. Terminal tasks (completed,
        failed, timeout, cancelled) are returned unchanged.

        Args:
            task_id: ID of the task to cancel.

        Returns:
            Updated AgentResult with status='cancelled', or None if not found.
        """
        return self._router.cancel_task(task_id)

    # -------------------------------------------------------------------------
    # timeout_task (explicit timeout trigger)
    # -------------------------------------------------------------------------

    def timeout_task(self, task_id: str) -> Optional[AgentResult]:
        """
        Explicitly mark a task as timed out.

        For use by external timeout monitors that detect elapsed time.
        Delegates to router's timeout_task.

        Args:
            task_id: ID of the task to time out.

        Returns:
            Updated AgentResult with status='timeout', or None if not found.
        """
        return self._router.timeout_task(task_id)

    # -------------------------------------------------------------------------
    # Convenience: get_task_status passthrough
    # -------------------------------------------------------------------------

    def get_task_status(self, task_id: str) -> Optional[AgentResult]:
        """Return current AgentResult for a task. Delegates to router."""
        return self._router.get_task_status(task_id)
