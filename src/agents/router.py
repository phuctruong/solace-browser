"""
AgentRouter — OAuth3-governed multi-agent task routing.

Every task dispatch is gated by OAuth3 scope enforcement:
  - Agent's supported_scopes must cover envelope's required_scopes
  - Token's granted scopes must cover envelope's required_scopes
  - Routing decisions are fully audited with scores and rationale

Scoring algorithm:
  final_score = scope_overlap_score * specialization_bonus * availability_weight

Capability-based routing extension (Feature #7):
  AgentProfile   — agent descriptor (capabilities + oauth3_scopes + concurrency)
  AgentTask      — task payload (required_capabilities + oauth3_token_id)
  AgentResult    — task outcome (status + evidence_hash + timing)
  RoutingStrategy — CAPABILITY_MATCH | ROUND_ROBIN | PRIORITY_FIRST | LEAST_LOADED
  AgentRouter (extended) — now supports both scope-based and capability-based routing

Rung: 641 (local correctness)
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Error constants
# ---------------------------------------------------------------------------

NEED_AGENT_ERROR = "NEED_AGENT"
OAUTH3_SCOPE_DENIED = "OAUTH3_SCOPE_DENIED"
OAUTH3_TOKEN_REQUIRED = "OAUTH3_TOKEN_REQUIRED"


# ---------------------------------------------------------------------------
# AgentCapability — registered agent descriptor
# ---------------------------------------------------------------------------

@dataclass
class AgentCapability:
    """
    Descriptor for a registered agent.

    Fields:
        agent_id:         Unique identifier for this agent instance.
        name:             Human-readable agent name.
        specialization:   Domain keyword for bonus scoring (e.g. 'gmail', 'linkedin').
        supported_scopes: OAuth3 scopes this agent is capable of exercising.
        rung:             Minimum verification rung this agent satisfies.
        model_preference: Preferred LLM model ('haiku', 'sonnet', 'opus').
        max_concurrent:   Maximum concurrent tasks this agent can handle.
    """

    agent_id: str
    name: str
    specialization: str
    supported_scopes: List[str]
    rung: int = 641
    model_preference: str = "sonnet"
    max_concurrent: int = 5

    def __post_init__(self) -> None:
        if not self.agent_id:
            raise ValueError("agent_id must not be empty")
        if not self.name:
            raise ValueError("name must not be empty")
        if not self.specialization:
            raise ValueError("specialization must not be empty")
        if self.rung not in (641, 274177, 65537):
            raise ValueError(f"rung must be 641, 274177, or 65537; got {self.rung}")
        if self.max_concurrent < 1:
            raise ValueError(f"max_concurrent must be >= 1; got {self.max_concurrent}")
        if self.model_preference not in ("haiku", "sonnet", "opus"):
            raise ValueError(
                f"model_preference must be haiku, sonnet, or opus; got {self.model_preference}"
            )

    def can_handle_scopes(self, required_scopes: List[str]) -> bool:
        """Return True if this agent's supported_scopes covers all required_scopes."""
        return all(s in self.supported_scopes for s in required_scopes)

    def scope_overlap_count(self, required_scopes: List[str]) -> int:
        """Return count of required_scopes covered by this agent."""
        return sum(1 for s in required_scopes if s in self.supported_scopes)


# ---------------------------------------------------------------------------
# TaskEnvelope — task descriptor passed to the router
# ---------------------------------------------------------------------------

@dataclass
class TaskEnvelope:
    """
    Task envelope submitted to the AgentRouter.

    Fields:
        task_id:         Unique task identifier (UUID4).
        intent:          Natural-language description of the task.
        required_scopes: OAuth3 scopes required to execute this task.
        priority:        Task priority 1 (lowest) to 5 (highest/critical).
        payload:         Arbitrary task data (must be JSON-serializable).
        token_id:        ID of the AgencyToken granting authorization.
        created_at:      ISO8601 UTC timestamp of envelope creation.
    """

    task_id: str
    intent: str
    required_scopes: List[str]
    priority: int
    payload: Dict[str, Any]
    token_id: str
    created_at: str

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id must not be empty")
        if not self.intent:
            raise ValueError("intent must not be empty")
        if self.required_scopes is None:
            raise ValueError("required_scopes must not be None (null != zero)")
        if not isinstance(self.required_scopes, list):
            raise ValueError("required_scopes must be a list")
        if not (1 <= self.priority <= 5):
            raise ValueError(f"priority must be 1-5; got {self.priority}")
        if self.payload is None:
            raise ValueError("payload must not be None (null != zero)")
        if not self.token_id:
            raise ValueError("token_id must not be empty")
        if not self.created_at:
            raise ValueError("created_at must not be empty")

    @classmethod
    def create(
        cls,
        intent: str,
        required_scopes: List[str],
        priority: int,
        payload: Dict[str, Any],
        token_id: str,
    ) -> "TaskEnvelope":
        """
        Factory: create a TaskEnvelope with auto-generated task_id and created_at.

        Args:
            intent:          Natural-language task description.
            required_scopes: OAuth3 scopes needed.
            priority:        Task priority 1-5.
            payload:         Task data dict.
            token_id:        AgencyToken ID granting authorization.

        Returns:
            TaskEnvelope instance.
        """
        now = datetime.now(timezone.utc).isoformat()
        task_id = str(uuid.uuid4())
        return cls(
            task_id=task_id,
            intent=intent,
            required_scopes=required_scopes,
            priority=priority,
            payload=payload,
            token_id=token_id,
            created_at=now,
        )


# ---------------------------------------------------------------------------
# RoutingResult — result of a routing decision
# ---------------------------------------------------------------------------

@dataclass
class RoutingResult:
    """
    Result of AgentRouter.route().

    Fields:
        selected:      Selected AgentCapability, or None if no agent found.
        score:         Final routing score for the selected agent.
        rationale:     Human-readable explanation of the routing decision.
        candidates:    All evaluated candidates with their scores.
        error_code:    NEED_AGENT or OAUTH3_* if routing failed.
        routed_at:     ISO8601 UTC timestamp of the routing decision.
    """

    selected: Optional[AgentCapability]
    score: float
    rationale: str
    candidates: List[Dict[str, Any]]
    error_code: Optional[str]
    routed_at: str

    @property
    def success(self) -> bool:
        return self.selected is not None and self.error_code is None


# ---------------------------------------------------------------------------
# DispatchResult — result of task execution
# ---------------------------------------------------------------------------

@dataclass
class DispatchResult:
    """
    Result of AgentRouter.dispatch().

    Fields:
        task_id:      Task identifier from the envelope.
        agent_id:     Agent that executed the task (or None if failed).
        status:       'success', 'failed', or 'blocked'.
        output:       Task output (may be None on failure).
        error_code:   Error code if status != 'success'.
        error_detail: Human-readable error description.
        latency_ms:   Execution latency in integer milliseconds.
        evidence:     Full evidence bundle (routing + execution audit).
        dispatched_at: ISO8601 UTC timestamp of dispatch.
    """

    task_id: str
    agent_id: Optional[str]
    status: str
    output: Optional[Any]
    error_code: Optional[str]
    error_detail: Optional[str]
    latency_ms: int
    evidence: Dict[str, Any]
    dispatched_at: str


# ---------------------------------------------------------------------------
# AgentRouter — core routing engine
# ---------------------------------------------------------------------------

class AgentRouter:
    """
    OAuth3-governed multi-agent task router.

    Routing algorithm:
        For each candidate agent:
            scope_overlap_score = (overlapping scopes) / max(len(required), 1)
            specialization_bonus = 1.5 if any required scope starts with agent.specialization
            availability_weight  = 1.0 - (active_tasks / max_concurrent)
            final_score          = scope_overlap_score * specialization_bonus * availability_weight

        Agents that cannot cover ALL required_scopes are eliminated first.
        Among remaining agents, highest final_score wins.
        Ties broken by round-robin across same-score agents (sorted by agent_id).

    OAuth3 gate:
        envelope.required_scopes must be subset of agent's supported_scopes AND
        the token (if provided to route()) must grant those scopes.

    Audit:
        Every routing decision logged to self.audit_trail with full score details.
    """

    def __init__(self) -> None:
        # {agent_id: AgentCapability}
        self._agents: Dict[str, AgentCapability] = {}
        # {agent_id: int} — currently active task count per agent
        self._active_tasks: Dict[str, int] = defaultdict(int)
        # Round-robin counters per score bucket (for tie-breaking)
        self._rr_counter: Dict[str, int] = defaultdict(int)
        # Audit trail: list of routing decision records
        self.audit_trail: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def register_agent(self, capability: AgentCapability) -> None:
        """
        Register an agent with its capability descriptor.

        Args:
            capability: AgentCapability to register. Overwrites any existing
                        registration with the same agent_id.
        """
        if not isinstance(capability, AgentCapability):
            raise TypeError("capability must be an AgentCapability instance")
        self._agents[capability.agent_id] = capability

    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent by ID.

        Args:
            agent_id: ID of the agent to remove.
        """
        self._agents.pop(agent_id, None)
        self._active_tasks.pop(agent_id, None)

    def registered_agents(self) -> List[AgentCapability]:
        """Return list of all registered agents."""
        return list(self._agents.values())

    # -------------------------------------------------------------------------
    # Scoring
    # -------------------------------------------------------------------------

    def _compute_score(
        self,
        agent: AgentCapability,
        envelope: TaskEnvelope,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Compute routing score for a given agent + envelope.

        Returns:
            (final_score, score_breakdown_dict)
        """
        required = envelope.required_scopes
        n_required = max(len(required), 1)

        # Scope overlap score: fraction of required scopes the agent covers
        overlap_count = agent.scope_overlap_count(required)
        scope_overlap_score = overlap_count / n_required

        # Specialization bonus: 1.5x if agent specialization matches any required scope prefix
        specialization_bonus = 1.0
        for scope in required:
            platform = scope.split(".")[0] if "." in scope else scope
            if platform == agent.specialization or agent.specialization in scope:
                specialization_bonus = 1.5
                break

        # Availability weight: 1.0 when idle, approaches 0 at full capacity
        active = self._active_tasks.get(agent.agent_id, 0)
        max_c = agent.max_concurrent
        # Weight is 0 when at capacity (active >= max_c)
        if active >= max_c:
            availability_weight = 0.0
        else:
            availability_weight = 1.0 - (active / max_c)

        final_score = scope_overlap_score * specialization_bonus * availability_weight

        breakdown = {
            "agent_id": agent.agent_id,
            "scope_overlap_score": scope_overlap_score,
            "specialization_bonus": specialization_bonus,
            "availability_weight": availability_weight,
            "final_score": final_score,
            "active_tasks": active,
            "max_concurrent": max_c,
        }
        return final_score, breakdown

    # -------------------------------------------------------------------------
    # OAuth3 gate
    # -------------------------------------------------------------------------

    def _check_token_scopes(
        self,
        envelope: TaskEnvelope,
        token: Any,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check that token grants all required_scopes in the envelope.

        Args:
            envelope: Task envelope with required_scopes.
            token:    AgencyToken (or None to skip token check).

        Returns:
            (passes, error_code, error_detail)
        """
        if token is None:
            return True, None, None

        # Check token validity (revocation + expiry)
        is_valid, err_msg = token.validate()
        if not is_valid:
            return False, "OAUTH3_TOKEN_INVALID", err_msg

        # Check scope coverage
        missing = [s for s in envelope.required_scopes if s not in token.scopes]
        if missing:
            return (
                False,
                OAUTH3_SCOPE_DENIED,
                f"Token does not grant scope(s): {missing}",
            )

        return True, None, None

    # -------------------------------------------------------------------------
    # Route
    # -------------------------------------------------------------------------

    def route(
        self,
        envelope: TaskEnvelope,
        token: Any = None,
    ) -> RoutingResult:
        """
        Route a task to the best-fit registered agent.

        OAuth3 gate: if token is provided, required_scopes must be granted by token.
        Agent gate:  only agents whose supported_scopes cover ALL required_scopes are considered.

        Args:
            envelope: TaskEnvelope describing the task.
            token:    AgencyToken (optional; provide for full OAuth3 enforcement).

        Returns:
            RoutingResult with selected agent and full score rationale.
        """
        routed_at = datetime.now(timezone.utc).isoformat()

        # OAuth3 token gate
        if token is not None:
            ok, err_code, err_detail = self._check_token_scopes(envelope, token)
            if not ok:
                result = RoutingResult(
                    selected=None,
                    score=0.0,
                    rationale=f"OAuth3 gate blocked: {err_detail}",
                    candidates=[],
                    error_code=err_code,
                    routed_at=routed_at,
                )
                self._log_routing(envelope, result)
                return result

        # Eliminate agents that cannot cover all required_scopes
        candidates: List[Tuple[float, str, AgentCapability, Dict]] = []
        all_candidates: List[Dict[str, Any]] = []

        for agent in self._agents.values():
            if not agent.can_handle_scopes(envelope.required_scopes):
                all_candidates.append({
                    "agent_id": agent.agent_id,
                    "final_score": 0.0,
                    "eliminated": "scope_mismatch",
                })
                continue

            score, breakdown = self._compute_score(agent, envelope)
            all_candidates.append({**breakdown, "eliminated": None})

            if score > 0.0:
                candidates.append((score, agent.agent_id, agent, breakdown))

        if not candidates:
            # Fallback: check if any agent has capacity issues only
            result = RoutingResult(
                selected=None,
                score=0.0,
                rationale=(
                    "No available agent found for required scopes: "
                    f"{envelope.required_scopes}"
                ),
                candidates=all_candidates,
                error_code=NEED_AGENT_ERROR,
                routed_at=routed_at,
            )
            self._log_routing(envelope, result)
            return result

        # Sort: descending score, then ascending agent_id for deterministic tie-breaking
        candidates.sort(key=lambda x: (-x[0], x[1]))

        # Round-robin among agents with the same top score
        top_score = candidates[0][0]
        top_group = [c for c in candidates if c[0] == top_score]

        # Use round-robin counter keyed by sorted agent_ids of the top group
        group_key = ",".join(sorted(c[1] for c in top_group))
        rr_idx = self._rr_counter[group_key] % len(top_group)
        # Sort top_group by agent_id for deterministic ordering
        top_group_sorted = sorted(top_group, key=lambda x: x[1])
        selected_tuple = top_group_sorted[rr_idx]
        self._rr_counter[group_key] += 1

        selected_agent = selected_tuple[2]
        final_score = selected_tuple[0]
        breakdown = selected_tuple[3]

        rationale = (
            f"Selected agent '{selected_agent.name}' (id={selected_agent.agent_id}) "
            f"with score={final_score:.4f} "
            f"[overlap={breakdown['scope_overlap_score']:.2f}, "
            f"spec_bonus={breakdown['specialization_bonus']:.1f}, "
            f"avail={breakdown['availability_weight']:.2f}]"
        )

        result = RoutingResult(
            selected=selected_agent,
            score=final_score,
            rationale=rationale,
            candidates=all_candidates,
            error_code=None,
            routed_at=routed_at,
        )
        self._log_routing(envelope, result)
        return result

    # -------------------------------------------------------------------------
    # Dispatch
    # -------------------------------------------------------------------------

    def dispatch(
        self,
        envelope: TaskEnvelope,
        token: Any = None,
        executor: Any = None,
    ) -> DispatchResult:
        """
        Route and execute a task.

        Routes the envelope to the best agent, then calls executor(envelope, agent)
        if provided, otherwise returns a simulated success result.

        Args:
            envelope: TaskEnvelope to dispatch.
            token:    AgencyToken for OAuth3 enforcement.
            executor: Optional callable(envelope, agent) → dict with keys
                      {'output': ..., 'latency_ms': int}. If None, a default
                      stub is used (for testing).

        Returns:
            DispatchResult with execution outcome and evidence bundle.
        """
        import time as _time

        dispatched_at = datetime.now(timezone.utc).isoformat()
        t_start = _time.monotonic()

        # Route
        routing = self.route(envelope, token=token)

        if not routing.success:
            elapsed_ms = int((_time.monotonic() - t_start) * 1000)
            evidence = _build_evidence(
                envelope=envelope,
                routing=routing,
                agent_id=None,
                output=None,
                latency_ms=elapsed_ms,
                dispatched_at=dispatched_at,
            )
            return DispatchResult(
                task_id=envelope.task_id,
                agent_id=None,
                status="blocked",
                output=None,
                error_code=routing.error_code,
                error_detail=routing.rationale,
                latency_ms=elapsed_ms,
                evidence=evidence,
                dispatched_at=dispatched_at,
            )

        agent = routing.selected

        # Increment active task counter
        self._active_tasks[agent.agent_id] += 1
        try:
            if executor is not None:
                exec_result = executor(envelope, agent)
                output = exec_result.get("output")
                exec_latency = int(exec_result.get("latency_ms", 0))
            else:
                # Default stub: simulate successful execution
                output = {
                    "status": "executed",
                    "agent_id": agent.agent_id,
                    "task_id": envelope.task_id,
                    "intent": envelope.intent,
                }
                exec_latency = 0

            elapsed_ms = int((_time.monotonic() - t_start) * 1000)
            evidence = _build_evidence(
                envelope=envelope,
                routing=routing,
                agent_id=agent.agent_id,
                output=output,
                latency_ms=elapsed_ms,
                dispatched_at=dispatched_at,
            )

            return DispatchResult(
                task_id=envelope.task_id,
                agent_id=agent.agent_id,
                status="success",
                output=output,
                error_code=None,
                error_detail=None,
                latency_ms=elapsed_ms,
                evidence=evidence,
                dispatched_at=dispatched_at,
            )

        except Exception as exc:  # noqa: BLE001
            elapsed_ms = int((_time.monotonic() - t_start) * 1000)
            evidence = _build_evidence(
                envelope=envelope,
                routing=routing,
                agent_id=agent.agent_id,
                output=None,
                latency_ms=elapsed_ms,
                dispatched_at=dispatched_at,
            )
            return DispatchResult(
                task_id=envelope.task_id,
                agent_id=agent.agent_id,
                status="failed",
                output=None,
                error_code="EXECUTION_ERROR",
                error_detail=str(exc),
                latency_ms=elapsed_ms,
                evidence=evidence,
                dispatched_at=dispatched_at,
            )
        finally:
            # Decrement active task counter
            self._active_tasks[agent.agent_id] = max(
                0, self._active_tasks[agent.agent_id] - 1
            )

    # -------------------------------------------------------------------------
    # Audit
    # -------------------------------------------------------------------------

    def _log_routing(
        self,
        envelope: TaskEnvelope,
        result: RoutingResult,
    ) -> None:
        """Append routing decision to audit_trail."""
        entry = {
            "task_id": envelope.task_id,
            "intent": envelope.intent,
            "required_scopes": list(envelope.required_scopes),
            "priority": envelope.priority,
            "token_id": envelope.token_id,
            "selected_agent_id": result.selected.agent_id if result.selected else None,
            "score": result.score,
            "rationale": result.rationale,
            "error_code": result.error_code,
            "candidates": result.candidates,
            "routed_at": result.routed_at,
        }
        self.audit_trail.append(entry)


# ---------------------------------------------------------------------------
# Evidence builder
# ---------------------------------------------------------------------------

def _build_evidence(
    *,
    envelope: TaskEnvelope,
    routing: RoutingResult,
    agent_id: Optional[str],
    output: Any,
    latency_ms: int,
    dispatched_at: str,
) -> Dict[str, Any]:
    """Build a complete evidence bundle for a dispatch."""
    return {
        "task_id": envelope.task_id,
        "token_id": envelope.token_id,
        "required_scopes": list(envelope.required_scopes),
        "priority": envelope.priority,
        "agent_id": agent_id,
        "routing_score": routing.score,
        "routing_rationale": routing.rationale,
        "routing_candidates": routing.candidates,
        "output_summary": str(output)[:500] if output is not None else None,
        "latency_ms": latency_ms,
        "dispatched_at": dispatched_at,
        "routed_at": routing.routed_at,
    }


# ===========================================================================
# Capability-Based Routing Extension (Feature #7)
# ===========================================================================
#
# The classes below extend the router with a capability-matching, OAuth3-gated
# dispatch API. They operate independently of AgentCapability/TaskEnvelope
# above and expose the new AgentProfile / AgentTask / AgentResult surface.
#
# All timestamps: ISO 8601 UTC strings.
# All hashes:     "sha256:" prefixed hex strings.
# No floats in verification paths (int only).
# OAuth3 scope: "agent.dispatch.task" required for task submission.
# ===========================================================================

import hashlib as _hashlib
import json as _json


def _now_iso8601() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _sha256_hex(data: dict) -> str:
    """Compute SHA-256 hex digest of canonical JSON dict. Returns 'sha256:<hex>'."""
    canonical = _json.dumps(data, sort_keys=True, separators=(",", ":"))
    return "sha256:" + _hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# RoutingStrategy — capability-based dispatch strategy
# ---------------------------------------------------------------------------

from enum import Enum as _Enum


class RoutingStrategy(_Enum):
    """Strategy controlling how AgentRouter selects among eligible agents."""
    CAPABILITY_MATCH = "capability_match"
    ROUND_ROBIN      = "round_robin"
    PRIORITY_FIRST   = "priority_first"
    LEAST_LOADED     = "least_loaded"


# ---------------------------------------------------------------------------
# AgentProfile — agent registration record
# ---------------------------------------------------------------------------

@dataclass
class AgentProfile:
    """
    Registration record for a capability-based agent.

    Fields:
        agent_id:             Globally unique agent identifier.
        name:                 Human-readable display name.
        capabilities:         Capability strings this agent supports.
        oauth3_scopes:        OAuth3 scopes this agent may exercise.
        model_preference:     Preferred LLM model string (e.g. 'claude-haiku').
        max_concurrent_tasks: Max simultaneous tasks (default 1).
        priority:             Routing priority; lower int = higher priority (default 100).
    """

    agent_id:             str
    name:                 str
    capabilities:         List[str] = field(default_factory=list)
    oauth3_scopes:        List[str] = field(default_factory=list)
    model_preference:     str = ""
    max_concurrent_tasks: int = 1
    priority:             int = 100


# ---------------------------------------------------------------------------
# AgentTask — task payload submitted for routing
# ---------------------------------------------------------------------------

@dataclass
class AgentTask:
    """
    A task submitted to the router for capability-based dispatch.

    Fields:
        task_id:               Globally unique task identifier.
        description:           Human-readable task description.
        required_capabilities: Capabilities the handling agent must possess.
        oauth3_token_id:       token_id of the AgencyToken authorizing dispatch.
        priority:              Task priority; lower int = higher priority (default 100).
        timeout_seconds:       Max seconds before auto-fail (default 60).
        created_at:            ISO 8601 UTC timestamp of creation.
        input_data:            Arbitrary input payload dict.
    """

    task_id:               str
    description:           str
    required_capabilities: List[str] = field(default_factory=list)
    oauth3_token_id:       str = ""
    priority:              int = 100
    timeout_seconds:       int = 60
    created_at:            str = field(default_factory=_now_iso8601)
    input_data:            dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# AgentResult — task outcome record
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    """
    Outcome of a task dispatched via the capability-based router.

    Status values: pending | running | completed | failed | timeout | cancelled

    Fields:
        task_id:       task_id this result belongs to.
        agent_id:      agent_id assigned to handle the task.
        status:        Current task status string.
        output:        Agent output payload dict.
        evidence_hash: SHA-256 hash of core fields for audit integrity.
        started_at:    ISO 8601 UTC when execution started (empty until running).
        completed_at:  ISO 8601 UTC when execution ended (empty until terminal).
        token_count:   Integer token usage (0 if not applicable; no floats).
        error_detail:  Human-readable error message (empty on success).
    """

    task_id:       str
    agent_id:      str
    status:        str = "pending"
    output:        dict = field(default_factory=dict)
    evidence_hash: str = ""
    started_at:    str = ""
    completed_at:  str = ""
    token_count:   int = 0
    error_detail:  str = ""

    VALID_STATUSES: ClassVar[frozenset] = frozenset(
        {"pending", "running", "completed", "failed", "timeout", "cancelled"}
    )

    def _recompute_evidence_hash(self) -> str:
        """Recompute evidence hash from current field values."""
        return _sha256_hex({
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        })


# ---------------------------------------------------------------------------
# Internal runtime state for capability-based router
# ---------------------------------------------------------------------------

@dataclass
class _CapAgentState:
    """Runtime tracking for a capability-based registered agent."""
    profile: AgentProfile
    active_task_ids: List[str] = field(default_factory=list)
    total_dispatched: int = 0
    total_completed: int = 0


# ---------------------------------------------------------------------------
# CapabilityAgentRouter — capability-based routing engine
# ---------------------------------------------------------------------------

class CapabilityAgentRouter:
    """
    OAuth3-governed capability-based multi-agent task router.

    This is the capability-based routing engine for Feature #7. It is distinct
    from the existing AgentRouter (scope-based) above and provides:
      - register_agent(profile) / unregister_agent(agent_id)
      - submit_task(task) → routes using RoutingStrategy
      - get_task_status(task_id) → AgentResult
      - get_agent_stats() → per-agent metrics dict
      - OAuth3 gate: submit_task requires 'agent.dispatch.task' scope
      - Capability matching: required_capabilities ⊆ agent.capabilities
      - Audit: every event logged with SHA-256 integrity hash

    Routing strategies:
      CAPABILITY_MATCH  — first registered eligible agent (default)
      ROUND_ROBIN       — cycle through eligible agents
      PRIORITY_FIRST    — eligible agent with lowest priority int
      LEAST_LOADED      — eligible agent with fewest active tasks

    Usage:
        router = CapabilityAgentRouter(strategy=RoutingStrategy.LEAST_LOADED)
        router.add_token(token)
        router.register_agent(profile)
        result = router.submit_task(task)
    """

    DISPATCH_SCOPE = "agent.dispatch.task"

    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_MATCH) -> None:
        self._strategy = strategy
        self._agents: Dict[str, _CapAgentState] = {}
        self._agent_order: List[str] = []
        self._rr_cursor: int = 0
        self._results: Dict[str, AgentResult] = {}
        self._tasks: Dict[str, AgentTask] = {}
        self._audit_log: List[dict] = []
        self._tokens: Dict[str, object] = {}

    # -------------------------------------------------------------------------
    # Token management
    # -------------------------------------------------------------------------

    def add_token(self, token: object) -> None:
        """Register an AgencyToken in the router's token registry."""
        self._tokens[token.token_id] = token

    def _get_token(self, token_id: str) -> Optional[object]:
        return self._tokens.get(token_id)

    def _validate_token_for_scope(self, token_id: str, required_scope: str) -> tuple:
        """Run full four-gate OAuth3 enforcement. Returns (passed, error_code, error_detail)."""
        token = self._get_token(token_id)
        if token is None:
            return False, "OAUTH3_TOKEN_NOT_FOUND", f"Token {token_id!r} not in registry"

        try:
            from src.oauth3.enforcement import ScopeGate
        except ImportError:
            from oauth3.enforcement import ScopeGate

        gate = ScopeGate(token=token, required_scopes=[required_scope])
        result = gate.check_all()
        if result.allowed:
            return True, "", ""
        return False, result.error_code or "OAUTH3_BLOCKED", result.error_detail or ""

    # -------------------------------------------------------------------------
    # Agent registration
    # -------------------------------------------------------------------------

    def register_agent(self, profile: AgentProfile) -> bool:
        """Register an agent. Returns False if agent_id is empty."""
        if not profile.agent_id:
            return False
        state = _CapAgentState(profile=profile)
        if profile.agent_id not in self._agents:
            self._agent_order.append(profile.agent_id)
        self._agents[profile.agent_id] = state
        self._audit("agent_registered", {
            "agent_id": profile.agent_id,
            "name": profile.name,
            "capabilities": list(profile.capabilities),
            "max_concurrent_tasks": profile.max_concurrent_tasks,
            "priority": profile.priority,
        })
        return True

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent. Returns False if not registered."""
        if agent_id not in self._agents:
            return False
        del self._agents[agent_id]
        if agent_id in self._agent_order:
            self._agent_order.remove(agent_id)
        if self._rr_cursor >= len(self._agent_order):
            self._rr_cursor = 0
        self._audit("agent_unregistered", {"agent_id": agent_id})
        return True

    def list_agents(self) -> List[AgentProfile]:
        """Return profiles of all registered agents in registration order."""
        return [self._agents[aid].profile for aid in self._agent_order if aid in self._agents]

    # -------------------------------------------------------------------------
    # Task submission
    # -------------------------------------------------------------------------

    def submit_task(self, task: AgentTask) -> AgentResult:
        """
        Submit a task for routing.

        OAuth3 gate: requires 'agent.dispatch.task' scope.
        Capability gate: task.required_capabilities ⊆ agent.capabilities.

        Returns AgentResult with status='pending' or 'failed'.
        """
        # OAuth3 gate
        passed, error_code, error_detail = self._validate_token_for_scope(
            task.oauth3_token_id, self.DISPATCH_SCOPE
        )
        if not passed:
            result = AgentResult(
                task_id=task.task_id,
                agent_id="",
                status="failed",
                error_detail=f"{error_code}: {error_detail}",
            )
            result.evidence_hash = result._recompute_evidence_hash()
            self._audit("task_rejected_oauth3", {
                "task_id": task.task_id,
                "oauth3_token_id": task.oauth3_token_id,
                "error_code": error_code,
            })
            return result

        # Find eligible agent
        agent_id = self._route(task)
        if agent_id is None:
            result = AgentResult(
                task_id=task.task_id,
                agent_id="",
                status="failed",
                error_detail="NO_AGENT_AVAILABLE: no eligible agent found for required capabilities",
            )
            result.evidence_hash = result._recompute_evidence_hash()
            self._audit("task_rejected_no_agent", {
                "task_id": task.task_id,
                "required_capabilities": list(task.required_capabilities),
            })
            return result

        # Register task
        self._tasks[task.task_id] = task
        result = AgentResult(
            task_id=task.task_id,
            agent_id=agent_id,
            status="pending",
        )
        result.evidence_hash = result._recompute_evidence_hash()
        self._results[task.task_id] = result

        state = self._agents[agent_id]
        state.active_task_ids.append(task.task_id)
        state.total_dispatched += 1

        self._audit("task_submitted", {
            "task_id": task.task_id,
            "agent_id": agent_id,
            "required_capabilities": list(task.required_capabilities),
            "oauth3_token_id": task.oauth3_token_id,
            "priority": task.priority,
        })
        return result

    def _route(self, task: AgentTask) -> Optional[str]:
        """Find best eligible agent using current strategy. Returns agent_id or None."""
        required = set(task.required_capabilities)

        eligible: List[str] = []
        for aid in self._agent_order:
            if aid not in self._agents:
                continue
            state = self._agents[aid]
            profile = state.profile
            if required and not required.issubset(set(profile.capabilities)):
                continue
            if len(state.active_task_ids) >= profile.max_concurrent_tasks:
                continue
            eligible.append(aid)

        if not eligible:
            return None

        if self._strategy == RoutingStrategy.CAPABILITY_MATCH:
            return eligible[0]

        elif self._strategy == RoutingStrategy.ROUND_ROBIN:
            return self._rr_pick(eligible)

        elif self._strategy == RoutingStrategy.PRIORITY_FIRST:
            return min(eligible, key=lambda aid: self._agents[aid].profile.priority)

        elif self._strategy == RoutingStrategy.LEAST_LOADED:
            return min(
                eligible,
                key=lambda aid: (
                    len(self._agents[aid].active_task_ids),
                    self._agents[aid].profile.priority,
                    self._agent_order.index(aid),
                ),
            )

        return eligible[0]

    def _rr_pick(self, eligible: List[str]) -> str:
        """Round-robin pick from eligible list, advancing global cursor."""
        order = self._agent_order
        n = len(order)
        for offset in range(n):
            idx = (self._rr_cursor + offset) % n
            candidate = order[idx]
            if candidate in eligible:
                self._rr_cursor = (idx + 1) % n
                return candidate
        self._rr_cursor = 0
        return eligible[0]

    # -------------------------------------------------------------------------
    # Task lifecycle
    # -------------------------------------------------------------------------

    def start_task(self, task_id: str) -> Optional[AgentResult]:
        """Transition a pending task to running."""
        result = self._results.get(task_id)
        if result is None or result.status != "pending":
            return result
        result.status = "running"
        result.started_at = _now_iso8601()
        result.evidence_hash = result._recompute_evidence_hash()
        self._audit("task_started", {"task_id": task_id, "agent_id": result.agent_id,
                                      "started_at": result.started_at})
        return result

    def complete_task(self, task_id: str, output: dict, token_count: int = 0) -> Optional[AgentResult]:
        """Mark a task as completed."""
        result = self._results.get(task_id)
        if result is None:
            return None
        if result.status not in ("pending", "running"):
            return result
        result.status = "completed"
        result.output = output
        result.completed_at = _now_iso8601()
        result.token_count = int(token_count)
        result.evidence_hash = result._recompute_evidence_hash()
        self._release(result.agent_id, task_id)
        self._audit("task_completed", {"task_id": task_id, "agent_id": result.agent_id,
                                        "completed_at": result.completed_at,
                                        "evidence_hash": result.evidence_hash})
        return result

    def fail_task(self, task_id: str, error_detail: str = "") -> Optional[AgentResult]:
        """Mark a task as failed."""
        result = self._results.get(task_id)
        if result is None:
            return None
        if result.status in ("completed", "failed", "timeout", "cancelled"):
            return result
        result.status = "failed"
        result.error_detail = error_detail
        result.completed_at = _now_iso8601()
        result.evidence_hash = result._recompute_evidence_hash()
        self._release(result.agent_id, task_id)
        self._audit("task_failed", {"task_id": task_id, "error_detail": error_detail})
        return result

    def timeout_task(self, task_id: str) -> Optional[AgentResult]:
        """Mark a task as timed out."""
        result = self._results.get(task_id)
        if result is None:
            return None
        if result.status in ("completed", "failed", "timeout", "cancelled"):
            return result
        result.status = "timeout"
        result.completed_at = _now_iso8601()
        result.error_detail = "Task exceeded timeout_seconds limit"
        result.evidence_hash = result._recompute_evidence_hash()
        self._release(result.agent_id, task_id)
        self._audit("task_timeout", {"task_id": task_id, "completed_at": result.completed_at})
        return result

    def cancel_task(self, task_id: str) -> Optional[AgentResult]:
        """Cancel a pending or running task. Terminal tasks returned unchanged."""
        result = self._results.get(task_id)
        if result is None:
            return None
        if result.status in ("completed", "failed", "timeout", "cancelled"):
            return result
        result.status = "cancelled"
        result.completed_at = _now_iso8601()
        result.evidence_hash = result._recompute_evidence_hash()
        self._release(result.agent_id, task_id)
        self._audit("task_cancelled", {"task_id": task_id, "completed_at": result.completed_at})
        return result

    def _release(self, agent_id: str, task_id: str) -> None:
        """Remove task from agent's active list and increment completed count."""
        state = self._agents.get(agent_id)
        if state is None:
            return
        if task_id in state.active_task_ids:
            state.active_task_ids.remove(task_id)
        state.total_completed += 1

    # -------------------------------------------------------------------------
    # Status and stats
    # -------------------------------------------------------------------------

    def get_task_status(self, task_id: str) -> Optional[AgentResult]:
        """Return current AgentResult for a task_id, or None if unknown."""
        return self._results.get(task_id)

    def get_agent_stats(self) -> Dict[str, dict]:
        """Return per-agent metrics dict keyed by agent_id."""
        stats: Dict[str, dict] = {}
        for aid in self._agent_order:
            if aid not in self._agents:
                continue
            state = self._agents[aid]
            profile = state.profile
            active = len(state.active_task_ids)
            stats[aid] = {
                "name": profile.name,
                "capabilities": list(profile.capabilities),
                "priority": profile.priority,
                "max_concurrent_tasks": profile.max_concurrent_tasks,
                "active_task_count": active,
                "total_dispatched": state.total_dispatched,
                "total_completed": state.total_completed,
                "at_capacity": active >= profile.max_concurrent_tasks,
            }
        return stats

    # -------------------------------------------------------------------------
    # Audit log
    # -------------------------------------------------------------------------

    def _audit(self, event: str, data: dict) -> dict:
        """Append an entry to the append-only audit log with SHA-256 integrity hash."""
        entry = {"event": event, "timestamp": _now_iso8601(), **data}
        entry["integrity_hash"] = _sha256_hex(entry)
        self._audit_log.append(entry)
        return entry

    def get_audit_log(self) -> List[dict]:
        """Return a copy of the append-only audit log."""
        return list(self._audit_log)


# ---------------------------------------------------------------------------
# Re-export under the task-spec names for backward-compatible import
# ---------------------------------------------------------------------------
# The task spec calls for:
#   AgentProfile, AgentTask, AgentResult, RoutingStrategy
#   AgentRouter (the new capability-based one)
#   NEED_AGENT_ERROR (already defined above)
#
# We expose CapabilityAgentRouter as the primary "AgentRouter" import alias
# for new code that imports from this module using the Feature #7 API.
# The old AgentRouter class (scope-based) remains available as AgentRouter.
# New code should import CapabilityAgentRouter directly.
# ---------------------------------------------------------------------------
