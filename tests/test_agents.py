"""
Multi-Agent Routing — Test Suite (Feature #7)

~60 tests across 7 test classes:
  TestAgentProfile     (8)  — creation, capabilities, validation
  TestAgentTask        (8)  — creation, required capabilities, priority
  TestAgentRouter      (15) — register, route, capability match, round robin,
                              priority, least loaded, stats
  TestAgentCoordinator (12) — parallel, sequential, fan-out/fan-in, cancel, timeout
  TestOAuth3Gate       (8)  — valid token dispatches, expired rejects, scope mismatch
  TestEvidence         (5)  — submission logging, completion logging, hash integrity
  TestEdgeCases        (4)  — no agents, all at capacity, unknown capability

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_agents.py -v

Rung: 641 (local correctness)
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agents.router import (
    AgentProfile,
    AgentTask,
    AgentResult,
    RoutingStrategy,
    CapabilityAgentRouter,
    _now_iso8601,
    _sha256_hex,
)
from agents.coordinator import AgentCoordinator
from oauth3.token import AgencyToken


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_token(
    scopes: List[str] = None,
    expired: bool = False,
    revoked: bool = False,
) -> AgencyToken:
    """Create an AgencyToken for testing."""
    if scopes is None:
        scopes = ["agent.dispatch.task"]
    kwargs: dict = dict(
        issuer="https://test.example.com",
        subject="test-user",
        scopes=scopes,
        intent="test agent delegation",
    )
    if expired:
        kwargs["expires_hours"] = -1
    else:
        kwargs["ttl_seconds"] = 3600
    token = AgencyToken.create(**kwargs)
    if revoked:
        token = token.revoke()
    return token


def _make_profile(
    agent_id: str = None,
    name: str = "TestAgent",
    capabilities: List[str] = None,
    oauth3_scopes: List[str] = None,
    max_concurrent_tasks: int = 5,
    priority: int = 100,
    model_preference: str = "sonnet",
) -> AgentProfile:
    """Create a test AgentProfile."""
    return AgentProfile(
        agent_id=agent_id or str(uuid.uuid4()),
        name=name,
        capabilities=capabilities or ["web.scrape", "text.summarize"],
        oauth3_scopes=oauth3_scopes or ["agent.dispatch.task"],
        max_concurrent_tasks=max_concurrent_tasks,
        priority=priority,
        model_preference=model_preference,
    )


def _make_task(
    task_id: str = None,
    description: str = "Test task",
    required_capabilities: List[str] = None,
    oauth3_token_id: str = "",
    priority: int = 100,
    timeout_seconds: int = 60,
) -> AgentTask:
    """Create a test AgentTask."""
    return AgentTask(
        task_id=task_id or str(uuid.uuid4()),
        description=description,
        required_capabilities=required_capabilities or [],
        oauth3_token_id=oauth3_token_id,
        priority=priority,
        timeout_seconds=timeout_seconds,
    )


def _make_router_with_token(
    strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_MATCH,
) -> tuple:
    """Return (router, token) with a valid dispatch token registered."""
    router = CapabilityAgentRouter(strategy=strategy)
    token = _make_token(["agent.dispatch.task"])
    router.add_token(token)
    return router, token


# ---------------------------------------------------------------------------
# TestAgentProfile (8 tests)
# ---------------------------------------------------------------------------

class TestAgentProfile:

    def test_agent_id_is_stored(self):
        aid = str(uuid.uuid4())
        p = AgentProfile(agent_id=aid, name="Alpha")
        assert p.agent_id == aid

    def test_name_is_stored(self):
        p = AgentProfile(agent_id="a1", name="Beta Agent")
        assert p.name == "Beta Agent"

    def test_capabilities_default_empty_list(self):
        p = AgentProfile(agent_id="a1", name="X")
        assert p.capabilities == []

    def test_capabilities_stored_correctly(self):
        caps = ["web.scrape", "text.summarize", "image.classify"]
        p = AgentProfile(agent_id="a1", name="X", capabilities=caps)
        assert p.capabilities == caps

    def test_oauth3_scopes_stored(self):
        scopes = ["agent.dispatch.task", "agent.monitor.stats"]
        p = AgentProfile(agent_id="a1", name="X", oauth3_scopes=scopes)
        assert p.oauth3_scopes == scopes

    def test_max_concurrent_tasks_default_is_one(self):
        p = AgentProfile(agent_id="a1", name="X")
        assert p.max_concurrent_tasks == 1

    def test_priority_default_is_100(self):
        p = AgentProfile(agent_id="a1", name="X")
        assert p.priority == 100

    def test_model_preference_stored(self):
        p = AgentProfile(agent_id="a1", name="X", model_preference="claude-haiku")
        assert p.model_preference == "claude-haiku"


# ---------------------------------------------------------------------------
# TestAgentTask (8 tests)
# ---------------------------------------------------------------------------

class TestAgentTask:

    def test_task_id_is_stored(self):
        tid = str(uuid.uuid4())
        t = AgentTask(task_id=tid, description="do X")
        assert t.task_id == tid

    def test_description_is_stored(self):
        t = AgentTask(task_id="t1", description="scrape linkedin feed")
        assert t.description == "scrape linkedin feed"

    def test_required_capabilities_default_empty(self):
        t = AgentTask(task_id="t1", description="do Y")
        assert t.required_capabilities == []

    def test_required_capabilities_stored(self):
        caps = ["web.scrape", "ocr.extract"]
        t = AgentTask(task_id="t1", description="d", required_capabilities=caps)
        assert t.required_capabilities == caps

    def test_oauth3_token_id_stored(self):
        t = AgentTask(task_id="t1", description="d", oauth3_token_id="tok-xyz")
        assert t.oauth3_token_id == "tok-xyz"

    def test_priority_default_is_100(self):
        t = AgentTask(task_id="t1", description="d")
        assert t.priority == 100

    def test_timeout_seconds_default_is_60(self):
        t = AgentTask(task_id="t1", description="d")
        assert t.timeout_seconds == 60

    def test_created_at_is_iso8601_string(self):
        t = AgentTask(task_id="t1", description="d")
        # Should be parseable as ISO 8601
        dt = datetime.fromisoformat(t.created_at.replace("Z", "+00:00"))
        assert dt.tzinfo is not None


# ---------------------------------------------------------------------------
# TestAgentRouter (15 tests)
# ---------------------------------------------------------------------------

class TestAgentRouter:

    def test_register_agent_returns_true(self):
        router = CapabilityAgentRouter()
        p = _make_profile()
        assert router.register_agent(p) is True

    def test_register_empty_agent_id_returns_false(self):
        router = CapabilityAgentRouter()
        p = AgentProfile(agent_id="", name="Bad")
        assert router.register_agent(p) is False

    def test_unregister_existing_agent_returns_true(self):
        router = CapabilityAgentRouter()
        p = _make_profile(agent_id="a1")
        router.register_agent(p)
        assert router.unregister_agent("a1") is True

    def test_unregister_unknown_agent_returns_false(self):
        router = CapabilityAgentRouter()
        assert router.unregister_agent("nonexistent") is False

    def test_list_agents_returns_registered_profiles(self):
        router = CapabilityAgentRouter()
        p1 = _make_profile(agent_id="a1", name="A1")
        p2 = _make_profile(agent_id="a2", name="A2")
        router.register_agent(p1)
        router.register_agent(p2)
        profiles = router.list_agents()
        ids = [p.agent_id for p in profiles]
        assert "a1" in ids
        assert "a2" in ids

    def test_capability_match_routes_to_first_eligible(self):
        router, token = _make_router_with_token(RoutingStrategy.CAPABILITY_MATCH)
        p1 = _make_profile(agent_id="a1", capabilities=["web.scrape"])
        p2 = _make_profile(agent_id="a2", capabilities=["web.scrape", "nlp"])
        router.register_agent(p1)
        router.register_agent(p2)
        task = _make_task(required_capabilities=["web.scrape"],
                          oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.status == "pending"
        assert result.agent_id == "a1"  # first registered eligible agent

    def test_capability_match_skips_ineligible_agent(self):
        router, token = _make_router_with_token(RoutingStrategy.CAPABILITY_MATCH)
        p1 = _make_profile(agent_id="a1", capabilities=["nlp.classify"])
        p2 = _make_profile(agent_id="a2", capabilities=["web.scrape"])
        router.register_agent(p1)
        router.register_agent(p2)
        task = _make_task(required_capabilities=["web.scrape"],
                          oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.agent_id == "a2"

    def test_round_robin_distributes_across_agents(self):
        router, token = _make_router_with_token(RoutingStrategy.ROUND_ROBIN)
        p1 = _make_profile(agent_id="a1", capabilities=["web"], max_concurrent_tasks=10)
        p2 = _make_profile(agent_id="a2", capabilities=["web"], max_concurrent_tasks=10)
        router.register_agent(p1)
        router.register_agent(p2)

        assigned = []
        for i in range(4):
            task = _make_task(required_capabilities=["web"],
                              oauth3_token_id=token.token_id)
            result = router.submit_task(task)
            assigned.append(result.agent_id)

        # Both agents should receive at least one task
        assert "a1" in assigned
        assert "a2" in assigned

    def test_priority_first_picks_lowest_priority_int(self):
        router, token = _make_router_with_token(RoutingStrategy.PRIORITY_FIRST)
        # priority=10 is higher priority than priority=50
        p_low_prio = _make_profile(agent_id="a_hi", capabilities=["task"], priority=10)
        p_hi_prio = _make_profile(agent_id="a_lo", capabilities=["task"], priority=50)
        router.register_agent(p_hi_prio)  # registered first but lower priority
        router.register_agent(p_low_prio)
        task = _make_task(required_capabilities=["task"],
                          oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.agent_id == "a_hi"  # lower int = higher routing priority

    def test_least_loaded_picks_agent_with_fewer_tasks(self):
        router, token = _make_router_with_token(RoutingStrategy.LEAST_LOADED)
        p1 = _make_profile(agent_id="a1", capabilities=["task"], max_concurrent_tasks=10)
        p2 = _make_profile(agent_id="a2", capabilities=["task"], max_concurrent_tasks=10)
        router.register_agent(p1)
        router.register_agent(p2)

        # Give a1 one active task
        task_a1 = _make_task(required_capabilities=["task"], oauth3_token_id=token.token_id)
        router.submit_task(task_a1)  # routes to a1 (first eligible)

        # Next task should go to a2 (least loaded)
        task_new = _make_task(required_capabilities=["task"], oauth3_token_id=token.token_id)
        result = router.submit_task(task_new)
        assert result.agent_id == "a2"

    def test_submit_task_returns_pending_on_success(self):
        router, token = _make_router_with_token()
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.status == "pending"

    def test_get_task_status_returns_result(self):
        router, token = _make_router_with_token()
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        submitted = router.submit_task(task)
        status = router.get_task_status(task.task_id)
        assert status is not None
        assert status.task_id == task.task_id
        assert status.status == submitted.status

    def test_get_agent_stats_returns_dict_per_agent(self):
        router, token = _make_router_with_token()
        p = _make_profile(agent_id="a1")
        router.register_agent(p)
        stats = router.get_agent_stats()
        assert "a1" in stats
        assert "name" in stats["a1"]
        assert "capabilities" in stats["a1"]
        assert "total_dispatched" in stats["a1"]

    def test_agent_at_capacity_not_selected(self):
        router, token = _make_router_with_token()
        # max_concurrent_tasks=1
        p = _make_profile(agent_id="solo", capabilities=["task"], max_concurrent_tasks=1)
        router.register_agent(p)

        # Submit first task (takes the slot)
        t1 = _make_task(required_capabilities=["task"], oauth3_token_id=token.token_id)
        r1 = router.submit_task(t1)
        assert r1.status == "pending"

        # Second task should fail — agent at capacity
        t2 = _make_task(required_capabilities=["task"], oauth3_token_id=token.token_id)
        r2 = router.submit_task(t2)
        assert r2.status == "failed"
        assert "NO_AGENT_AVAILABLE" in r2.error_detail

    def test_complete_task_frees_agent_capacity(self):
        router, token = _make_router_with_token()
        p = _make_profile(agent_id="solo", capabilities=["task"], max_concurrent_tasks=1)
        router.register_agent(p)

        t1 = _make_task(required_capabilities=["task"], oauth3_token_id=token.token_id)
        router.submit_task(t1)
        router.start_task(t1.task_id)
        router.complete_task(t1.task_id, output={"result": "done"})

        # Now capacity is freed — second task should succeed
        t2 = _make_task(required_capabilities=["task"], oauth3_token_id=token.token_id)
        r2 = router.submit_task(t2)
        assert r2.status == "pending"


# ---------------------------------------------------------------------------
# TestAgentCoordinator (12 tests)
# ---------------------------------------------------------------------------

class TestAgentCoordinator:

    def _make_coordinator(self, n_agents: int = 2, capabilities: list = None,
                          max_concurrent: int = 10) -> tuple:
        """Return (coordinator, router, token) with n_agents registered."""
        router, token = _make_router_with_token()
        caps = capabilities or ["web"]
        for i in range(n_agents):
            p = _make_profile(
                agent_id=f"agent_{i}",
                capabilities=caps,
                max_concurrent_tasks=max_concurrent,
            )
            router.register_agent(p)
        coord = AgentCoordinator(router)
        return coord, router, token

    def test_dispatch_parallel_returns_list_of_results(self):
        coord, _, token = self._make_coordinator()
        tasks = [_make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
                 for _ in range(3)]
        results = coord.dispatch_parallel(tasks)
        assert len(results) == 3

    def test_dispatch_parallel_all_results_have_task_ids(self):
        coord, _, token = self._make_coordinator()
        tasks = [_make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
                 for _ in range(2)]
        results = coord.dispatch_parallel(tasks)
        task_ids = {t.task_id for t in tasks}
        result_ids = {r.task_id for r in results}
        assert result_ids == task_ids

    def test_dispatch_parallel_results_in_same_order_as_tasks(self):
        coord, _, token = self._make_coordinator()
        tasks = [_make_task(task_id=f"task_{i}", required_capabilities=["web"],
                            oauth3_token_id=token.token_id)
                 for i in range(3)]
        results = coord.dispatch_parallel(tasks)
        for i, (task, result) in enumerate(zip(tasks, results)):
            assert result.task_id == task.task_id

    def test_dispatch_parallel_completes_tasks(self):
        coord, _, token = self._make_coordinator()
        tasks = [_make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
                 for _ in range(2)]
        results = coord.dispatch_parallel(tasks)
        for r in results:
            assert r.status == "completed"

    def test_dispatch_sequential_returns_list_of_results(self):
        coord, _, token = self._make_coordinator()
        tasks = [_make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
                 for _ in range(3)]
        results = coord.dispatch_sequential(tasks)
        assert len(results) == 3

    def test_dispatch_sequential_passes_output_to_next_task(self):
        coord, _, token = self._make_coordinator()
        t1 = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        t2 = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        results = coord.dispatch_sequential([t1, t2])
        # t2's input_data should contain "previous_output" from t1
        assert "previous_output" in t2.input_data

    def test_dispatch_sequential_preserves_task_order(self):
        coord, _, token = self._make_coordinator()
        tasks = [_make_task(task_id=f"seq_{i}", required_capabilities=["web"],
                            oauth3_token_id=token.token_id)
                 for i in range(3)]
        results = coord.dispatch_sequential(tasks)
        for i, (task, result) in enumerate(zip(tasks, results)):
            assert result.task_id == task.task_id

    def test_dispatch_fan_out_fan_in_returns_results_for_all_tasks(self):
        coord, _, token = self._make_coordinator(n_agents=3, max_concurrent=10)
        tasks = [_make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
                 for _ in range(3)]
        results = coord.dispatch_fan_out_fan_in(tasks, aggregator=lambda rs: len(rs))
        assert len(results) == 3

    def test_dispatch_fan_out_fan_in_calls_aggregator(self):
        coord, _, token = self._make_coordinator(n_agents=2, max_concurrent=10)
        tasks = [_make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
                 for _ in range(2)]
        aggregator_called = []
        def agg(results):
            aggregator_called.append(True)
            return "merged"
        coord.dispatch_fan_out_fan_in(tasks, aggregator=agg)
        assert aggregator_called

    def test_dispatch_fan_out_fan_in_stores_aggregated_in_output(self):
        coord, _, token = self._make_coordinator(n_agents=2, max_concurrent=10)
        tasks = [_make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
                 for _ in range(2)]
        results = coord.dispatch_fan_out_fan_in(tasks, aggregator=lambda rs: "merged_value")
        completed = [r for r in results if r.status == "completed"]
        assert all(r.output.get("aggregated") == "merged_value" for r in completed)

    def test_cancel_task_transitions_to_cancelled(self):
        router, token = _make_router_with_token()
        p = _make_profile(capabilities=["task"])
        router.register_agent(p)
        coord = AgentCoordinator(router)

        task = _make_task(required_capabilities=["task"], oauth3_token_id=token.token_id)
        router.submit_task(task)  # now pending

        result = coord.cancel_task(task.task_id)
        assert result is not None
        assert result.status == "cancelled"

    def test_timeout_task_transitions_to_timeout(self):
        router, token = _make_router_with_token()
        p = _make_profile(capabilities=["task"])
        router.register_agent(p)
        coord = AgentCoordinator(router)

        task = _make_task(required_capabilities=["task"], oauth3_token_id=token.token_id)
        router.submit_task(task)
        router.start_task(task.task_id)

        result = coord.timeout_task(task.task_id)
        assert result is not None
        assert result.status == "timeout"


# ---------------------------------------------------------------------------
# TestOAuth3Gate (8 tests)
# ---------------------------------------------------------------------------

class TestOAuth3Gate:

    def test_valid_token_with_dispatch_scope_allows_task(self):
        router, token = _make_router_with_token()
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.status == "pending"

    def test_unknown_token_id_blocks_task(self):
        router = CapabilityAgentRouter()
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id="nonexistent-token")
        result = router.submit_task(task)
        assert result.status == "failed"
        assert "OAUTH3_TOKEN_NOT_FOUND" in result.error_detail

    def test_expired_token_blocks_task(self):
        router = CapabilityAgentRouter()
        token = _make_token(expired=True)
        router.add_token(token)
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.status == "failed"
        assert "OAUTH3" in result.error_detail

    def test_revoked_token_blocks_task(self):
        router = CapabilityAgentRouter()
        token = _make_token(revoked=True)
        router.add_token(token)
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.status == "failed"
        assert "OAUTH3" in result.error_detail

    def test_token_missing_dispatch_scope_blocks_task(self):
        router = CapabilityAgentRouter()
        # Token with only monitor scope — missing agent.dispatch.task
        token = _make_token(scopes=["agent.monitor.stats"])
        router.add_token(token)
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.status == "failed"
        assert "OAUTH3" in result.error_detail

    def test_empty_token_id_blocks_task(self):
        router = CapabilityAgentRouter()
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        # oauth3_token_id is empty string by default in _make_task
        task = _make_task(required_capabilities=["web"], oauth3_token_id="")
        result = router.submit_task(task)
        assert result.status == "failed"

    def test_valid_token_with_multiple_scopes_allows_dispatch(self):
        router = CapabilityAgentRouter()
        token = _make_token(scopes=["agent.dispatch.task", "agent.monitor.stats"])
        router.add_token(token)
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.status == "pending"

    def test_blocked_task_has_error_detail(self):
        router = CapabilityAgentRouter()
        task = _make_task(oauth3_token_id="ghost-token")
        result = router.submit_task(task)
        assert result.status == "failed"
        assert len(result.error_detail) > 0


# ---------------------------------------------------------------------------
# TestEvidence (5 tests)
# ---------------------------------------------------------------------------

class TestEvidence:

    def test_task_submission_logged_in_audit(self):
        router, token = _make_router_with_token()
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        router.submit_task(task)
        log = router.get_audit_log()
        events = [e["event"] for e in log]
        assert "task_submitted" in events

    def test_task_completion_logged_in_audit(self):
        router, token = _make_router_with_token()
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        router.submit_task(task)
        router.start_task(task.task_id)
        router.complete_task(task.task_id, output={"x": 1})
        log = router.get_audit_log()
        events = [e["event"] for e in log]
        assert "task_completed" in events

    def test_evidence_hash_has_sha256_prefix(self):
        router, token = _make_router_with_token()
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.evidence_hash.startswith("sha256:")

    def test_evidence_hash_is_64_hex_chars_after_prefix(self):
        router, token = _make_router_with_token()
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        hex_part = result.evidence_hash[len("sha256:"):]
        assert len(hex_part) == 64
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_audit_log_entries_have_integrity_hash(self):
        router, token = _make_router_with_token()
        p = _make_profile(capabilities=["web"])
        router.register_agent(p)
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        router.submit_task(task)
        log = router.get_audit_log()
        for entry in log:
            if "integrity_hash" in entry:
                assert entry["integrity_hash"].startswith("sha256:")


# ---------------------------------------------------------------------------
# TestEdgeCases (4 tests)
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_no_agents_registered_returns_failed(self):
        router, token = _make_router_with_token()
        task = _make_task(required_capabilities=["web"], oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.status == "failed"
        assert "NO_AGENT_AVAILABLE" in result.error_detail

    def test_all_agents_at_capacity_returns_failed(self):
        router, token = _make_router_with_token()
        # Register one agent with max_concurrent_tasks=1
        p = _make_profile(agent_id="solo", capabilities=["task"], max_concurrent_tasks=1)
        router.register_agent(p)

        # Fill the slot
        t1 = _make_task(required_capabilities=["task"], oauth3_token_id=token.token_id)
        r1 = router.submit_task(t1)
        assert r1.status == "pending"

        # Second task should fail — agent at capacity
        t2 = _make_task(required_capabilities=["task"], oauth3_token_id=token.token_id)
        r2 = router.submit_task(t2)
        assert r2.status == "failed"
        assert "NO_AGENT_AVAILABLE" in r2.error_detail

    def test_unknown_capability_returns_failed(self):
        router, token = _make_router_with_token()
        p = _make_profile(capabilities=["web.scrape"])
        router.register_agent(p)

        # Request capability that no agent has
        task = _make_task(required_capabilities=["quantum.compute"],
                          oauth3_token_id=token.token_id)
        result = router.submit_task(task)
        assert result.status == "failed"
        assert "NO_AGENT_AVAILABLE" in result.error_detail

    def test_get_task_status_unknown_id_returns_none(self):
        router = CapabilityAgentRouter()
        result = router.get_task_status("nonexistent-task-id")
        assert result is None
