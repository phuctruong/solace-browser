"""
SolaceBrowser Agents — OAuth3-governed multi-agent routing system.

Modules:
  router.py       — AgentCapability, TaskEnvelope, AgentRouter (scope-based dispatch)
                    AgentProfile, AgentTask, AgentResult, RoutingStrategy,
                    CapabilityAgentRouter (capability-based dispatch, Feature #7)
  orchestrator.py — WorkflowPlan, AgentOrchestrator (multi-step, parallel execution)
  coordinator.py  — AgentCoordinator (parallel, sequential, fan-out/fan-in patterns)

Architecture:
  Every task dispatch is bounded by OAuth3 scope enforcement.
  Routing decisions are logged with full audit trails.
  Capability-based routing uses score-weighted round-robin with availability checks.

Rung: 641 (local correctness)
"""

from .router import (
    AgentCapability,
    TaskEnvelope,
    AgentRouter,
    RoutingResult,
    DispatchResult,
    NEED_AGENT_ERROR,
    # Feature #7: capability-based routing
    AgentProfile,
    AgentTask,
    AgentResult,
    RoutingStrategy,
    CapabilityAgentRouter,
)

from .orchestrator import (
    WorkflowPlan,
    StepEvidence,
    AgentOrchestrator,
    ExecutionResult,
)

from .coordinator import AgentCoordinator

__all__ = [
    # Original scope-based router
    "AgentCapability",
    "TaskEnvelope",
    "AgentRouter",
    "RoutingResult",
    "DispatchResult",
    "NEED_AGENT_ERROR",
    # Feature #7: capability-based routing
    "AgentProfile",
    "AgentTask",
    "AgentResult",
    "RoutingStrategy",
    "CapabilityAgentRouter",
    # Orchestrator
    "WorkflowPlan",
    "StepEvidence",
    "AgentOrchestrator",
    "ExecutionResult",
    # Coordinator
    "AgentCoordinator",
]

__version__ = "0.2.0"
__rung__ = 641
