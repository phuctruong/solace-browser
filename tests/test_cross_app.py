"""Tests for cross-app messaging protocol (B7 / original T13).

Test structure:
  - CrossAppMessenger.send() between partner apps (success)
  - CrossAppMessenger.send() to non-partner -> rejected
  - Budget gate B6 blocks when target budget exhausted
  - Message appears in target inbox/requests/
  - CrossAppMessenger.acknowledge() moves to processed/
  - CrossAppMessenger.receive_pending() lists unprocessed messages only
  - Evidence hash computed for each delivery
  - OrchestratorRuntime triggers child apps

Auth: 65537 | Rung: 641
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from budget_gates import BudgetGateChecker
from cross_app.message import CrossAppMessage, CrossAppMessageError, CrossAppMessenger
from cross_app.orchestrator import (
    NotAnOrchestratorError,
    OrchestratorError,
    OrchestratorRuntime,
)
from execution_lifecycle import ExecutionLifecycleManager
from inbox_outbox import InboxOutboxManager


# ---------------------------------------------------------------------------
# Fixed clock for deterministic tests
# ---------------------------------------------------------------------------

FIXED_TIME = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)


def _fixed_now() -> datetime:
    return FIXED_TIME


# ---------------------------------------------------------------------------
# Helpers — build complete app filesystems for testing
# ---------------------------------------------------------------------------


def _make_app(
    apps_root: Path,
    app_id: str = "gmail-inbox-triage",
    *,
    remaining_runs: int = 5,
    include_policy: bool = True,
    allowed_domains: list[str] | None = None,
    evidence_mode: str = "full",
    partners: list[str] | None = None,
    app_type: str | None = None,
    orchestrates: list[str] | None = None,
) -> Path:
    """Create a fully valid app directory under apps_root.

    Returns the app_root path.
    """
    app_root = apps_root / app_id
    inbox_root = app_root / "inbox"
    outbox_root = app_root / "outbox"

    for path in [
        inbox_root / "prompts",
        inbox_root / "templates",
        inbox_root / "assets",
        inbox_root / "policies",
        inbox_root / "datasets",
        inbox_root / "requests",
        inbox_root / "conventions" / "examples",
        outbox_root / "previews",
        outbox_root / "drafts",
        outbox_root / "reports",
        outbox_root / "suggestions",
        outbox_root / "runs",
        app_root / "diagrams",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    # manifest.yaml
    manifest: dict[str, Any] = {
        "id": app_id,
        "name": app_id.replace("-", " ").title(),
        "required_inbox": {
            "prompts": [],
            "templates": [],
            "assets": [],
            "policies": [],
            "datasets": [],
            "requests": [],
            "conventions": {"config": "config.yaml", "defaults": "defaults.yaml"},
        },
    }
    if partners is not None:
        manifest["produces_for"] = partners
    if app_type is not None:
        manifest["type"] = app_type
    if orchestrates is not None:
        manifest["orchestrates"] = orchestrates
    (app_root / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )

    # recipe.json
    (app_root / "recipe.json").write_text(
        json.dumps({"id": app_id, "steps": []}), encoding="utf-8"
    )

    # budget.json
    (app_root / "budget.json").write_text(
        json.dumps({"remaining_runs": remaining_runs}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # diagrams
    for name in ["workflow.md", "data-flow.md", "partner-contracts.md"]:
        (app_root / "diagrams" / name).write_text(
            "```mermaid\nflowchart TD\nA-->B\n```\n", encoding="utf-8"
        )

    # inbox/conventions
    (inbox_root / "conventions" / "config.yaml").write_text(
        "scan_hours: 2\n", encoding="utf-8"
    )
    (inbox_root / "conventions" / "defaults.yaml").write_text(
        "scan_hours: 24\n", encoding="utf-8"
    )

    # budget-policy.yaml
    if include_policy:
        policy: dict[str, Any] = {"evidence_mode": evidence_mode}
        if allowed_domains is not None:
            policy["allowed_domains"] = allowed_domains
        (inbox_root / "policies" / "budget-policy.yaml").write_text(
            yaml.safe_dump(policy, sort_keys=False), encoding="utf-8"
        )

    return app_root


# ---------------------------------------------------------------------------
# CrossAppMessenger.send() — success path
# ---------------------------------------------------------------------------


class TestSendBetweenPartners:
    def test_send_delivers_message_to_target_inbox(self, tmp_path: Path) -> None:
        """Send between partner apps succeeds and writes file to target inbox/requests/."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="source-app", remaining_runs=5, partners=["target-app"])
        _make_app(apps_root, app_id="target-app", remaining_runs=3)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        result = messenger.send(
            source_app="source-app",
            target_app="target-app",
            run_id="run-001",
            message_type="suggestion",
            payload={"summary": "Check your inbox"},
        )

        assert result["delivered"] is True
        assert "evidence_hash" in result
        assert len(result["evidence_hash"]) == 64  # SHA-256 hex

        # Verify file on disk
        delivered_path = Path(result["path"])
        assert delivered_path.exists()
        content = json.loads(delivered_path.read_text(encoding="utf-8"))
        assert content["source_app"] == "source-app"
        assert content["target_app"] == "target-app"
        assert content["run_id"] == "run-001"
        assert content["message_type"] == "suggestion"
        assert content["payload"] == {"summary": "Check your inbox"}
        assert content["evidence_hash"] == result["evidence_hash"]

    def test_send_request_type_succeeds(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="alpha", remaining_runs=5, partners=["beta"])
        _make_app(apps_root, app_id="beta", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        result = messenger.send("alpha", "beta", "r-002", "request", {"action": "process"})

        assert result["delivered"] is True

    def test_send_report_type_succeeds(self, tmp_path: Path) -> None:
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="alpha", remaining_runs=5, partners=["beta"])
        _make_app(apps_root, app_id="beta", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        result = messenger.send("alpha", "beta", "r-003", "report", {"status": "done"})

        assert result["delivered"] is True


# ---------------------------------------------------------------------------
# CrossAppMessenger.send() — non-partner rejected
# ---------------------------------------------------------------------------


class TestSendToNonPartner:
    def test_send_to_non_partner_is_rejected(self, tmp_path: Path) -> None:
        """Sending to an app not in produces_for returns delivered=False."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="source-app", remaining_runs=5, partners=["other-app"])
        _make_app(apps_root, app_id="target-app", remaining_runs=3)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        result = messenger.send(
            source_app="source-app",
            target_app="target-app",
            run_id="run-002",
            message_type="suggestion",
            payload={"summary": "Should be rejected"},
        )

        assert result["delivered"] is False
        assert "produces_for" in result["reason"]

    def test_send_without_produces_for_is_rejected(self, tmp_path: Path) -> None:
        """Source manifest has no produces_for key at all."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="source-app", remaining_runs=5, partners=None)
        _make_app(apps_root, app_id="target-app", remaining_runs=3)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        result = messenger.send(
            source_app="source-app",
            target_app="target-app",
            run_id="run-003",
            message_type="request",
            payload={},
        )

        assert result["delivered"] is False
        assert "produces_for" in result["reason"]


# ---------------------------------------------------------------------------
# Budget gate B6 blocks when target budget exhausted
# ---------------------------------------------------------------------------


class TestBudgetGateBlocks:
    def test_b6_blocks_when_target_budget_zero(self, tmp_path: Path) -> None:
        """B6 gate blocks delivery when target app has zero remaining budget."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="source-app", remaining_runs=5, partners=["target-app"])
        _make_app(apps_root, app_id="target-app", remaining_runs=0)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        result = messenger.send(
            source_app="source-app",
            target_app="target-app",
            run_id="run-004",
            message_type="suggestion",
            payload={"data": "should not arrive"},
        )

        assert result["delivered"] is False
        assert "B6" in result["reason"]
        assert "no remaining budget" in result["reason"]

    def test_b6_blocks_when_source_budget_zero(self, tmp_path: Path) -> None:
        """B6 gate blocks when source app's own budget is exhausted (B2 first)."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="source-app", remaining_runs=0, partners=["target-app"])
        _make_app(apps_root, app_id="target-app", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        result = messenger.send(
            source_app="source-app",
            target_app="target-app",
            run_id="run-005",
            message_type="request",
            payload={},
        )

        assert result["delivered"] is False
        # B2 fires before B6 since source budget is 0
        assert "B2" in result["reason"] or "B6" in result["reason"]


# ---------------------------------------------------------------------------
# Message appears in target inbox/requests/
# ---------------------------------------------------------------------------


class TestMessageInTargetInbox:
    def test_message_file_written_to_correct_location(self, tmp_path: Path) -> None:
        """After send, the file from-{source}-{run_id}.json exists in target inbox/requests/."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="sender", remaining_runs=5, partners=["receiver"])
        _make_app(apps_root, app_id="receiver", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        messenger.send("sender", "receiver", "run-006", "suggestion", {"key": "value"})

        expected_path = apps_root / "receiver" / "inbox" / "requests" / "from-sender-run-006.json"
        assert expected_path.exists()
        content = json.loads(expected_path.read_text(encoding="utf-8"))
        assert content["source_app"] == "sender"
        assert content["payload"] == {"key": "value"}

    def test_multiple_messages_coexist(self, tmp_path: Path) -> None:
        """Multiple messages from the same source create separate files."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="sender", remaining_runs=10, partners=["receiver"])
        _make_app(apps_root, app_id="receiver", remaining_runs=10)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        messenger.send("sender", "receiver", "run-a", "suggestion", {"n": 1})
        messenger.send("sender", "receiver", "run-b", "request", {"n": 2})

        requests_dir = apps_root / "receiver" / "inbox" / "requests"
        files = sorted(f.name for f in requests_dir.iterdir() if f.is_file())
        assert "from-sender-run-a.json" in files
        assert "from-sender-run-b.json" in files


# ---------------------------------------------------------------------------
# Acknowledge moves to processed/
# ---------------------------------------------------------------------------


class TestAcknowledge:
    def test_acknowledge_moves_to_processed(self, tmp_path: Path) -> None:
        """Acknowledge moves message from inbox/requests/ to inbox/requests/processed/."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="sender", remaining_runs=5, partners=["receiver"])
        _make_app(apps_root, app_id="receiver", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        messenger.send("sender", "receiver", "run-007", "suggestion", {"data": "ack me"})

        filename = "from-sender-run-007.json"
        result = messenger.acknowledge("receiver", filename)

        assert result["acknowledged"] is True
        # Original location empty
        original = apps_root / "receiver" / "inbox" / "requests" / filename
        assert not original.exists()
        # Processed location has the file
        processed = apps_root / "receiver" / "inbox" / "requests" / "processed" / filename
        assert processed.exists()

    def test_acknowledge_nonexistent_file_raises(self, tmp_path: Path) -> None:
        """Acknowledging a file that does not exist raises FileNotFoundError."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="receiver", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        with pytest.raises(FileNotFoundError):
            messenger.acknowledge("receiver", "from-ghost-run-999.json")

    def test_acknowledge_rejects_path_traversal(self, tmp_path: Path) -> None:
        """Filename with path separator is rejected."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="receiver", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        with pytest.raises(CrossAppMessageError, match="bare filename"):
            messenger.acknowledge("receiver", "../../../etc/passwd")


# ---------------------------------------------------------------------------
# Receive pending lists unprocessed messages only
# ---------------------------------------------------------------------------


class TestReceivePending:
    def test_receive_pending_lists_unprocessed_only(self, tmp_path: Path) -> None:
        """After acknowledging one of two messages, only the unprocessed one remains."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="sender", remaining_runs=10, partners=["receiver"])
        _make_app(apps_root, app_id="receiver", remaining_runs=10)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        messenger.send("sender", "receiver", "run-a", "suggestion", {"n": 1})
        messenger.send("sender", "receiver", "run-b", "request", {"n": 2})

        # Acknowledge the first message
        messenger.acknowledge("receiver", "from-sender-run-a.json")

        pending = messenger.receive_pending("receiver")
        assert len(pending) == 1
        assert pending[0].run_id == "run-b"
        assert pending[0].message_type == "request"

    def test_receive_pending_empty_when_no_messages(self, tmp_path: Path) -> None:
        """Receive pending returns empty list when no messages exist."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="receiver", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        pending = messenger.receive_pending("receiver")
        assert pending == []

    def test_receive_pending_returns_crossappmessage_objects(self, tmp_path: Path) -> None:
        """Each item in pending list is a CrossAppMessage with correct fields."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="sender", remaining_runs=5, partners=["receiver"])
        _make_app(apps_root, app_id="receiver", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        messenger.send("sender", "receiver", "run-x", "report", {"result": "ok"})

        pending = messenger.receive_pending("receiver")
        assert len(pending) == 1
        msg = pending[0]
        assert isinstance(msg, CrossAppMessage)
        assert msg.source_app == "sender"
        assert msg.target_app == "receiver"
        assert msg.run_id == "run-x"
        assert msg.message_type == "report"
        assert msg.payload == {"result": "ok"}
        assert msg.timestamp == FIXED_TIME.isoformat()
        assert len(msg.evidence_hash) == 64


# ---------------------------------------------------------------------------
# Evidence hash computed for each delivery
# ---------------------------------------------------------------------------


class TestEvidenceHash:
    def test_evidence_hash_is_sha256_of_canonical_json(self, tmp_path: Path) -> None:
        """Evidence hash matches SHA-256 of the canonical message JSON (without hash field)."""
        import hashlib

        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="sender", remaining_runs=5, partners=["receiver"])
        _make_app(apps_root, app_id="receiver", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        result = messenger.send("sender", "receiver", "run-hash", "suggestion", {"v": 42})

        assert result["delivered"] is True

        # Reconstruct canonical form and verify hash
        message_dict = {
            "source_app": "sender",
            "target_app": "receiver",
            "run_id": "run-hash",
            "message_type": "suggestion",
            "payload": {"v": 42},
            "timestamp": FIXED_TIME.isoformat(),
        }
        canonical = json.dumps(message_dict, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        assert result["evidence_hash"] == expected_hash

    def test_different_payloads_produce_different_hashes(self, tmp_path: Path) -> None:
        """Two messages with different payloads have different evidence hashes."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="sender", remaining_runs=10, partners=["receiver"])
        _make_app(apps_root, app_id="receiver", remaining_runs=10)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        r1 = messenger.send("sender", "receiver", "run-h1", "suggestion", {"data": "alpha"})
        r2 = messenger.send("sender", "receiver", "run-h2", "suggestion", {"data": "beta"})

        assert r1["evidence_hash"] != r2["evidence_hash"]


# ---------------------------------------------------------------------------
# Invalid message_type raises
# ---------------------------------------------------------------------------


class TestInvalidMessageType:
    def test_invalid_message_type_raises(self, tmp_path: Path) -> None:
        """Sending with an invalid message_type raises CrossAppMessageError."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="sender", remaining_runs=5, partners=["receiver"])
        _make_app(apps_root, app_id="receiver", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)

        with pytest.raises(CrossAppMessageError, match="Invalid message_type"):
            messenger.send("sender", "receiver", "run-bad", "invalid_type", {})


# ---------------------------------------------------------------------------
# OrchestratorRuntime triggers child apps
# ---------------------------------------------------------------------------


class TestOrchestratorRuntime:
    def test_orchestrator_triggers_all_children(self, tmp_path: Path) -> None:
        """Orchestrator sends messages to all children in orchestrates list."""
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            app_id="orch-app",
            remaining_runs=10,
            partners=["child-a", "child-b"],
            app_type="orchestrator",
            orchestrates=["child-a", "child-b"],
        )
        _make_app(apps_root, app_id="child-a", remaining_runs=5)
        _make_app(apps_root, app_id="child-b", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)
        lifecycle = ExecutionLifecycleManager(
            solace_home=tmp_path / "solace-home-unused",
            sleep_fn=lambda _: None,
        )
        # Override lifecycle's _manager so orchestrator can read manifests from apps_root
        lifecycle._manager = io

        runtime = OrchestratorRuntime(messenger, lifecycle, now_fn=_fixed_now)
        result = runtime.execute_orchestrator("orch-app", "daily-triage")

        assert result["orchestrator"] == "orch-app"
        assert result["trigger"] == "daily-triage"
        assert result["total_children"] == 2
        assert result["delivered_count"] == 2
        assert result["failed_count"] == 0
        assert result["children"]["child-a"]["delivered"] is True
        assert result["children"]["child-b"]["delivered"] is True

        # Verify messages landed in child inboxes
        child_a_requests = apps_root / "child-a" / "inbox" / "requests"
        child_a_files = [f.name for f in child_a_requests.iterdir() if f.is_file()]
        assert any(f.startswith("from-orch-app-") for f in child_a_files)

    def test_orchestrator_partial_failure_records_each_child(self, tmp_path: Path) -> None:
        """If one child has no budget, orchestrator records partial failure."""
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            app_id="orch-app",
            remaining_runs=10,
            partners=["child-ok", "child-broke"],
            app_type="orchestrator",
            orchestrates=["child-ok", "child-broke"],
        )
        _make_app(apps_root, app_id="child-ok", remaining_runs=5)
        _make_app(apps_root, app_id="child-broke", remaining_runs=0)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)
        lifecycle = ExecutionLifecycleManager(
            solace_home=tmp_path / "solace-home-unused",
            sleep_fn=lambda _: None,
        )
        lifecycle._manager = io

        runtime = OrchestratorRuntime(messenger, lifecycle, now_fn=_fixed_now)
        result = runtime.execute_orchestrator("orch-app", "daily-triage")

        assert result["delivered_count"] == 1
        assert result["failed_count"] == 1
        assert result["children"]["child-ok"]["delivered"] is True
        assert result["children"]["child-broke"]["delivered"] is False

    def test_orchestrator_not_orchestrator_type_raises(self, tmp_path: Path) -> None:
        """Calling execute_orchestrator on a non-orchestrator app raises."""
        apps_root = tmp_path / "apps"
        _make_app(apps_root, app_id="regular-app", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)
        lifecycle = ExecutionLifecycleManager(
            solace_home=tmp_path / "solace-home-unused",
            sleep_fn=lambda _: None,
        )
        lifecycle._manager = io

        runtime = OrchestratorRuntime(messenger, lifecycle, now_fn=_fixed_now)

        with pytest.raises(NotAnOrchestratorError, match="type='orchestrator'"):
            runtime.execute_orchestrator("regular-app", "trigger")

    def test_orchestrator_empty_orchestrates_raises(self, tmp_path: Path) -> None:
        """Orchestrator with empty orchestrates list raises OrchestratorError."""
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            app_id="orch-empty",
            remaining_runs=5,
            app_type="orchestrator",
            orchestrates=[],
        )

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)
        lifecycle = ExecutionLifecycleManager(
            solace_home=tmp_path / "solace-home-unused",
            sleep_fn=lambda _: None,
        )
        lifecycle._manager = io

        runtime = OrchestratorRuntime(messenger, lifecycle, now_fn=_fixed_now)

        with pytest.raises(OrchestratorError, match="non-empty list"):
            runtime.execute_orchestrator("orch-empty", "trigger")

    def test_get_orchestrator_status_returns_run_info(self, tmp_path: Path) -> None:
        """After execute_orchestrator, get_orchestrator_status returns the run."""
        apps_root = tmp_path / "apps"
        _make_app(
            apps_root,
            app_id="orch-app",
            remaining_runs=10,
            partners=["child-a"],
            app_type="orchestrator",
            orchestrates=["child-a"],
        )
        _make_app(apps_root, app_id="child-a", remaining_runs=5)

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)
        lifecycle = ExecutionLifecycleManager(
            solace_home=tmp_path / "solace-home-unused",
            sleep_fn=lambda _: None,
        )
        lifecycle._manager = io

        runtime = OrchestratorRuntime(messenger, lifecycle, now_fn=_fixed_now)
        result = runtime.execute_orchestrator("orch-app", "trigger")
        run_id = result["run_id"]

        status = runtime.get_orchestrator_status(run_id)
        assert status["found"] is True
        assert status["orchestrator"] == "orch-app"
        assert status["delivered_count"] == 1

    def test_get_orchestrator_status_unknown_run_id(self, tmp_path: Path) -> None:
        """get_orchestrator_status with unknown run_id returns found=False."""
        apps_root = tmp_path / "apps"

        io = InboxOutboxManager(apps_root=apps_root)
        budget = BudgetGateChecker(apps_root)
        messenger = CrossAppMessenger(io, budget, now_fn=_fixed_now)
        lifecycle = ExecutionLifecycleManager(
            solace_home=tmp_path / "solace-home-unused",
            sleep_fn=lambda _: None,
        )

        runtime = OrchestratorRuntime(messenger, lifecycle, now_fn=_fixed_now)
        status = runtime.get_orchestrator_status("nonexistent-run-id")
        assert status["found"] is False
