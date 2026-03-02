"""Tests for apps.runner — local app recipe execution lifecycle."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from apps.runner import AppRunnerError, load_and_compile_recipe, run_app
from execution_lifecycle import ApprovalDecision, ExecutionState
from inbox_outbox import InboxOutboxValidationError
from oauth3.vault import OAuth3Vault
from recipes.recipe_compiler import RecipeIR


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GMAIL_RECIPE = {
    "id": "gmail-inbox-triage",
    "platform": "gmail",
    "version": "1.0.0",
    "oauth3_scopes": ["gmail.read.inbox"],
    "steps": [
        {"step": 1, "action": "load_session", "path": "artifacts/gmail.json", "description": "Load session"},
        {"step": 2, "action": "navigate", "target": "https://mail.google.com/mail/u/0/#inbox", "description": "Open inbox"},
        {"step": 3, "action": "check_auth", "selector": "div[role='main']", "description": "Check auth"},
        {"step": 4, "action": "wait_for_selector", "selector": "[role='row']", "timeout_ms": 8000, "description": "Wait"},
        {"step": 5, "action": "extract_all", "selector": "[role='row']", "fields": {"subject": {}}, "description": "Extract"},
        {"step": 6, "action": "return_result", "description": "Return"},
    ],
}

BUDGET_POLICY = {
    "enabled": True,
    "allowed_domains": ["mail.google.com", "accounts.google.com"],
    "evidence_mode": "full",
    "max_runs_per_day": 24,
    "high_risk_operations": [],
}


def _make_app(solace_home: Path, recipe: dict | None = None) -> Path:
    """Create a valid app directory structure for testing."""
    app_root = solace_home / "apps" / "gmail-inbox-triage"

    # Create directory structure
    for subdir in [
        "diagrams",
        "inbox/prompts",
        "inbox/templates",
        "inbox/assets",
        "inbox/policies",
        "inbox/datasets",
        "inbox/requests",
        "inbox/conventions/examples",
        "outbox/previews",
        "outbox/drafts",
        "outbox/reports",
        "outbox/suggestions",
        "outbox/runs",
    ]:
        (app_root / subdir).mkdir(parents=True, exist_ok=True)

    # Manifest
    manifest = {
        "id": "gmail-inbox-triage",
        "name": "Gmail Inbox Triage",
        "site": "mail.google.com",
        "type": "standard",
        "safety": "B",
        "status": "installed",
        "scopes": ["gmail.read.inbox", "gmail.draft.create", "local.evidence"],
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

    # Recipe
    (app_root / "recipe.json").write_text(
        json.dumps(recipe or GMAIL_RECIPE, indent=2) + "\n", encoding="utf-8"
    )

    # Budget
    (app_root / "budget.json").write_text(
        json.dumps({"remaining_runs": 10, "cooldown_seconds": 5}, indent=2) + "\n", encoding="utf-8"
    )

    # Budget policy
    (app_root / "inbox" / "policies" / "budget-policy.yaml").write_text(
        yaml.safe_dump(BUDGET_POLICY, sort_keys=False), encoding="utf-8"
    )

    # Conventions
    (app_root / "inbox" / "conventions" / "config.yaml").write_text("scan_hours: 2\n", encoding="utf-8")
    (app_root / "inbox" / "conventions" / "defaults.yaml").write_text("scan_hours: 24\n", encoding="utf-8")

    # Diagrams
    for name in ["workflow.md", "data-flow.md", "partner-contracts.md"]:
        (app_root / "diagrams" / name).write_text("```mermaid\nflowchart TD\nA-->B\n```\n", encoding="utf-8")

    return app_root


def _make_vault(tmp_path: Path, scopes: list[str] | None = None) -> tuple:
    """Create an OAuth3Vault and issue a token with needed scopes."""
    vault = OAuth3Vault(
        encryption_key=b"r" * 32,
        evidence_log=tmp_path / "oauth3.jsonl",
        storage_path=tmp_path / "tokens.enc.json",
    )
    if scopes is None:
        scopes = [
            "browser.navigate", "browser.click", "browser.fill",
            "browser.screenshot", "browser.verify", "browser.session",
            "browser.read", "browser.dom", "gmail.read.inbox",
        ]
    token = vault.issue_token(scopes, ttl_seconds=3600)
    return vault, token["token_id"]


FIXED_NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# load_and_compile_recipe tests
# ---------------------------------------------------------------------------

class TestLoadAndCompileRecipe:
    def test_compiles_json_steps_recipe(self, tmp_path):
        app_root = tmp_path / "app"
        app_root.mkdir()
        recipe_path = app_root / "recipe.json"
        recipe_path.write_text(json.dumps(GMAIL_RECIPE), encoding="utf-8")
        ir = load_and_compile_recipe(app_root, recipe_path)
        assert isinstance(ir, RecipeIR)
        assert ir.recipe_id == "gmail-inbox-triage"
        assert len(ir.steps) == 6

    def test_compiles_mermaid_recipe(self, tmp_path):
        app_root = tmp_path / "app"
        app_root.mkdir()
        recipe = {
            "id": "mermaid-app",
            "mermaid_fsm": "stateDiagram-v2\n  [*] --> Navigate\n  Navigate --> Click: action_ok\n  Click --> [*]: done",
            "steps": [{"step": 1, "action": "navigate", "target": "https://example.com"}],
        }
        recipe_path = app_root / "recipe.json"
        recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
        ir = load_and_compile_recipe(app_root, recipe_path)
        assert ir.recipe_id == "mermaid-app"

    def test_deterministic_compilation(self, tmp_path):
        app_root = tmp_path / "app"
        app_root.mkdir()
        recipe_path = app_root / "recipe.json"
        recipe_path.write_text(json.dumps(GMAIL_RECIPE), encoding="utf-8")
        ir1 = load_and_compile_recipe(app_root, recipe_path)
        ir2 = load_and_compile_recipe(app_root, recipe_path)
        assert ir1.ir_hash == ir2.ir_hash


# ---------------------------------------------------------------------------
# run_app tests
# ---------------------------------------------------------------------------

class TestRunAppApproved:
    def test_full_lifecycle_approved_succeeds(self, tmp_path):
        solace_home = tmp_path / "solace"
        _make_app(solace_home)
        vault, token_id = _make_vault(tmp_path)

        result = run_app(
            "gmail-inbox-triage",
            vault=vault,
            token_id=token_id,
            solace_home=solace_home,
            sleep_fn=lambda _: None,
            now_fn=lambda: FIXED_NOW,
        )

        assert result.state == ExecutionState.DONE
        assert result.app_id == "gmail-inbox-triage"
        assert result.run_id.startswith("gmail-inbox-triage-")
        assert result.preview is not None
        assert "6 steps" in result.preview
        assert result.evidence_path.exists()

    def test_creates_evidence_chain(self, tmp_path):
        solace_home = tmp_path / "solace"
        _make_app(solace_home)
        vault, token_id = _make_vault(tmp_path)

        result = run_app(
            "gmail-inbox-triage",
            vault=vault,
            token_id=token_id,
            solace_home=solace_home,
            sleep_fn=lambda _: None,
            now_fn=lambda: FIXED_NOW,
        )

        evidence_lines = result.evidence_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(evidence_lines) >= 5  # TRIGGER, INTENT, BUDGET, PREVIEW, ..., DONE, SEAL
        # Verify hash chain
        prev_hash = "0" * 64
        for line in evidence_lines:
            entry = json.loads(line)
            assert entry["prev_hash"] == prev_hash
            prev_hash = entry["entry_hash"]

    def test_decrements_budget_on_success(self, tmp_path):
        solace_home = tmp_path / "solace"
        _make_app(solace_home)
        vault, token_id = _make_vault(tmp_path)

        result = run_app(
            "gmail-inbox-triage",
            vault=vault,
            token_id=token_id,
            solace_home=solace_home,
            sleep_fn=lambda _: None,
            now_fn=lambda: FIXED_NOW,
        )

        assert result.state == ExecutionState.DONE
        budget = json.loads(
            (solace_home / "apps" / "gmail-inbox-triage" / "budget.json").read_text(encoding="utf-8")
        )
        assert budget["remaining_runs"] == 9  # was 10, decremented by 1

    def test_writes_run_manifest(self, tmp_path):
        solace_home = tmp_path / "solace"
        _make_app(solace_home)
        vault, token_id = _make_vault(tmp_path)

        result = run_app(
            "gmail-inbox-triage",
            vault=vault,
            token_id=token_id,
            solace_home=solace_home,
            sleep_fn=lambda _: None,
            now_fn=lambda: FIXED_NOW,
        )

        run_root = solace_home / "apps" / "gmail-inbox-triage" / "outbox" / "runs" / result.run_id
        run_json = run_root / "run.json"
        assert run_json.exists()
        manifest = json.loads(run_json.read_text(encoding="utf-8"))
        assert manifest["state"] == "DONE"
        assert manifest["run_id"] == result.run_id


class TestRunAppRejected:
    def test_rejected_aborts_cleanly(self, tmp_path):
        solace_home = tmp_path / "solace"
        _make_app(solace_home)
        vault, token_id = _make_vault(tmp_path)

        result = run_app(
            "gmail-inbox-triage",
            approval=ApprovalDecision.REJECT,
            vault=vault,
            token_id=token_id,
            solace_home=solace_home,
            sleep_fn=lambda _: None,
            now_fn=lambda: FIXED_NOW,
        )

        assert result.state == ExecutionState.SEALED_ABORT

    def test_timeout_aborts_cleanly(self, tmp_path):
        solace_home = tmp_path / "solace"
        _make_app(solace_home)
        vault, token_id = _make_vault(tmp_path)

        result = run_app(
            "gmail-inbox-triage",
            approval=ApprovalDecision.TIMEOUT,
            vault=vault,
            token_id=token_id,
            solace_home=solace_home,
            sleep_fn=lambda _: None,
            now_fn=lambda: FIXED_NOW,
        )

        assert result.state == ExecutionState.SEALED_ABORT


class TestRunAppBudgetBlocked:
    def test_zero_budget_blocks_execution(self, tmp_path):
        solace_home = tmp_path / "solace"
        _make_app(solace_home)
        # Set budget to 0
        budget_path = solace_home / "apps" / "gmail-inbox-triage" / "budget.json"
        budget_path.write_text(json.dumps({"remaining_runs": 0}), encoding="utf-8")

        vault, token_id = _make_vault(tmp_path)

        result = run_app(
            "gmail-inbox-triage",
            vault=vault,
            token_id=token_id,
            solace_home=solace_home,
            sleep_fn=lambda _: None,
            now_fn=lambda: FIXED_NOW,
        )

        assert result.state == ExecutionState.BLOCKED
        assert result.block_reason is not None


class TestRunAppErrors:
    def test_missing_recipe_raises(self, tmp_path):
        solace_home = tmp_path / "solace"
        _make_app(solace_home)
        # Delete recipe.json — validate_inbox catches this first
        (solace_home / "apps" / "gmail-inbox-triage" / "recipe.json").unlink()

        vault, token_id = _make_vault(tmp_path)

        with pytest.raises(InboxOutboxValidationError):
            run_app(
                "gmail-inbox-triage",
                vault=vault,
                token_id=token_id,
                solace_home=solace_home,
                sleep_fn=lambda _: None,
                now_fn=lambda: FIXED_NOW,
            )

    def test_nonexistent_app_raises(self, tmp_path):
        solace_home = tmp_path / "solace"
        (solace_home / "apps").mkdir(parents=True)
        vault, token_id = _make_vault(tmp_path)

        with pytest.raises(Exception):  # AppFolderNotFoundError
            run_app(
                "nonexistent-app",
                vault=vault,
                token_id=token_id,
                solace_home=solace_home,
                sleep_fn=lambda _: None,
                now_fn=lambda: FIXED_NOW,
            )


class TestRunAppWithInputs:
    def test_inputs_passed_to_executor(self, tmp_path):
        solace_home = tmp_path / "solace"
        _make_app(solace_home)
        vault, token_id = _make_vault(tmp_path)

        result = run_app(
            "gmail-inbox-triage",
            vault=vault,
            token_id=token_id,
            solace_home=solace_home,
            inputs={"limit": 5},
            sleep_fn=lambda _: None,
            now_fn=lambda: FIXED_NOW,
        )

        assert result.state == ExecutionState.DONE


class TestRunAppUserIdESign:
    def test_user_id_included_in_evidence(self, tmp_path):
        solace_home = tmp_path / "solace"
        _make_app(solace_home)
        vault, token_id = _make_vault(tmp_path)

        result = run_app(
            "gmail-inbox-triage",
            vault=vault,
            token_id=token_id,
            solace_home=solace_home,
            user_id="phuc@phuc.net",
            sleep_fn=lambda _: None,
            now_fn=lambda: FIXED_NOW,
        )

        assert result.state == ExecutionState.DONE
        evidence_text = result.evidence_path.read_text(encoding="utf-8")
        assert "phuc@phuc.net" in evidence_text
