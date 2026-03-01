from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from execution_lifecycle import ApprovalDecision, ExecutionLifecycleManager, ExecutionState


def _make_app(solace_home: Path) -> None:
    app_root = solace_home / "apps" / "gmail-inbox-triage"
    for path in [
        app_root / "diagrams",
        app_root / "inbox" / "prompts",
        app_root / "inbox" / "templates",
        app_root / "inbox" / "assets",
        app_root / "inbox" / "policies",
        app_root / "inbox" / "datasets",
        app_root / "inbox" / "requests",
        app_root / "inbox" / "conventions" / "examples",
        app_root / "outbox" / "previews",
        app_root / "outbox" / "drafts",
        app_root / "outbox" / "reports",
        app_root / "outbox" / "suggestions",
        app_root / "outbox" / "runs",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": "gmail-inbox-triage",
        "name": "Gmail Inbox Triage",
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
    (app_root / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    (app_root / "recipe.json").write_text(json.dumps({"id": "gmail-triage", "steps": []}), encoding="utf-8")
    (app_root / "budget.json").write_text(json.dumps({"remaining_runs": 2}), encoding="utf-8")
    for name in ["workflow.md", "data-flow.md", "partner-contracts.md"]:
        (app_root / "diagrams" / name).write_text("```mermaid\nflowchart TD\nA-->B\n```\n", encoding="utf-8")
    (app_root / "inbox" / "conventions" / "config.yaml").write_text("scan_hours: 2\n", encoding="utf-8")
    (app_root / "inbox" / "conventions" / "defaults.yaml").write_text("scan_hours: 24\n", encoding="utf-8")


def test_lifecycle_success_path_seals_output_and_evidence(tmp_path: Path) -> None:
    solace_home = tmp_path / "solace-home"
    _make_app(solace_home)
    preview_calls: list[str] = []
    execute_calls: list[str] = []

    manager = ExecutionLifecycleManager(solace_home=solace_home, sleep_fn=lambda _seconds: None)
    result = manager.run(
        app_id="gmail-inbox-triage",
        trigger="manual",
        approval_decision=ApprovalDecision.APPROVE,
        risk_level="medium",
        preview_callback=lambda context: preview_calls.append(context["app_id"]) or {"preview": "Draft reply", "actions": ["draft"]},
        execute_callback=lambda sealed: execute_calls.append(sealed["run_id"]) or {"status": "success", "actions_summary": "1 draft"},
    )

    assert result.state == ExecutionState.DONE
    assert preview_calls == ["gmail-inbox-triage"]
    assert len(execute_calls) == 1
    assert result.sealed_output_path is not None
    mode = stat.S_IMODE(result.sealed_output_path.stat().st_mode)
    assert mode == 0o444
    evidence_lines = result.evidence_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(evidence_lines) >= 8


def test_lifecycle_timeout_denies_execution(tmp_path: Path) -> None:
    solace_home = tmp_path / "solace-home"
    _make_app(solace_home)
    execute_calls: list[str] = []
    manager = ExecutionLifecycleManager(solace_home=solace_home, sleep_fn=lambda _seconds: None)

    result = manager.run(
        app_id="gmail-inbox-triage",
        trigger="manual",
        approval_decision=ApprovalDecision.TIMEOUT,
        preview_callback=lambda _context: {"preview": "Draft reply", "actions": ["draft"]},
        execute_callback=lambda _sealed: execute_calls.append("called") or {"status": "success"},
    )

    assert result.state == ExecutionState.SEALED_ABORT
    assert execute_calls == []


def test_lifecycle_budget_failure_blocks_closed(tmp_path: Path) -> None:
    solace_home = tmp_path / "solace-home"
    _make_app(solace_home)
    manager = ExecutionLifecycleManager(solace_home=solace_home, sleep_fn=lambda _seconds: None)

    result = manager.run(
        app_id="gmail-inbox-triage",
        trigger="manual",
        approval_decision=ApprovalDecision.APPROVE,
        budget_check=lambda _context: {"allowed": False, "reason": "B2 remaining limit exhausted"},
        preview_callback=lambda _context: {"preview": "Draft reply", "actions": ["draft"]},
        execute_callback=lambda _sealed: {"status": "success"},
    )

    assert result.state == ExecutionState.BLOCKED
    assert result.block_reason == "B2 remaining limit exhausted"


def test_successful_run_decrements_budget(tmp_path: Path) -> None:
    solace_home = tmp_path / "solace-home"
    _make_app(solace_home)
    manager = ExecutionLifecycleManager(solace_home=solace_home, sleep_fn=lambda _seconds: None)

    result = manager.run(
        app_id="gmail-inbox-triage",
        trigger="manual",
        approval_decision=ApprovalDecision.APPROVE,
        preview_callback=lambda _context: {"preview": "Draft reply", "actions": ["draft"]},
        execute_callback=lambda _sealed: {"status": "success"},
    )

    assert result.state == ExecutionState.DONE
    budget = json.loads((solace_home / "apps" / "gmail-inbox-triage" / "budget.json").read_text(encoding="utf-8"))
    assert budget["remaining_runs"] == 1
