from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "src" / "browser" / "inbox_outbox.py"


spec = importlib.util.spec_from_file_location("inbox_outbox", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


# ── Ticket 1: solace-qa worker app ──


def test_qa_app_has_real_inbox_outbox_contract() -> None:
    manager = module.InboxOutboxManager(apps_root=REPO_ROOT / "data" / "apps")

    result = manager.validate_inbox("solace-qa")

    assert result["valid"] is True


def test_qa_app_has_prime_mermaid_source() -> None:
    app_root = REPO_ROOT / "data" / "apps" / "solace-qa"

    assert (app_root / "manifest.prime-mermaid.md").exists()
    assert (app_root / "recipe.prime-mermaid.md").exists()
    assert (app_root / "manifest.yaml").exists()


def test_qa_app_has_budget_and_recipe() -> None:
    app_root = REPO_ROOT / "data" / "apps" / "solace-qa"

    assert (app_root / "budget.json").exists()
    assert (app_root / "recipe.json").exists()


# ── Ticket 2: QA diagrams ──


def test_qa_diagrams_exist() -> None:
    diagrams_root = REPO_ROOT / "specs" / "solace-dev" / "diagrams"

    assert (diagrams_root / "qa-workflow.prime-mermaid.md").exists()
    assert (diagrams_root / "qa-evidence-flow.prime-mermaid.md").exists()
    assert (diagrams_root / "qa-signoff-release-gate.prime-mermaid.md").exists()
    assert (diagrams_root / "qa-regression-routing.prime-mermaid.md").exists()


# ── Ticket 3: Handoff contract ──


def test_qa_handoff_contract_exists() -> None:
    specs_root = REPO_ROOT / "specs" / "solace-dev"

    assert (specs_root / "coder-to-qa-handoff.md").exists()


def test_qa_handoff_contract_has_sample_payload() -> None:
    contract = (
        REPO_ROOT / "specs" / "solace-dev" / "coder-to-qa-handoff.md"
    ).read_text(encoding="utf-8")

    assert "request_id" in contract
    assert "assignment_id" in contract
    assert "code_run_refs" in contract
    assert "design_spec_refs" in contract
    assert "expected_artifacts" in contract
    assert "release_gate_verdict" in contract


# ── Ticket 4: Hub QA workspace ──


def test_hub_index_has_qa_workspace_card() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "qa-workspace-card" in index_html
    assert "QA Workspace" in index_html
    assert "/backoffice/solace-qa/qa_runs" in index_html
    assert "/backoffice/solace-qa/qa_findings" in index_html
    assert "/backoffice/solace-qa/qa_signoffs" in index_html
    assert "/backoffice/solace-dev-manager/qa_handoffs" in index_html


# ── Ticket 5: Durable storage ──


def test_backoffice_registry_knows_about_solace_qa() -> None:
    backoffice_rs = (
        REPO_ROOT / "solace-runtime" / "src" / "routes" / "backoffice.rs"
    ).read_text(encoding="utf-8")

    assert '"solace-qa"' in backoffice_rs


def test_manager_manifest_has_qa_handoffs_table() -> None:
    import yaml

    manifest_path = (
        REPO_ROOT / "data" / "apps" / "solace-dev-manager" / "manifest.yaml"
    )
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    table_names = [t["name"] for t in manifest["backoffice"]["tables"]]
    assert "qa_handoffs" in table_names


# ── Ticket 6: Storage note ──


def test_storage_model_documents_qa_artifacts() -> None:
    storage = (
        REPO_ROOT / "specs" / "solace-dev" / "storage-model.md"
    ).read_text(encoding="utf-8")

    assert "QA Role Artifacts" in storage
    assert "qa_handoffs" in storage
    assert "qa_runs" in storage
    assert "qa_findings" in storage
    assert "qa_signoffs" in storage
    assert "coder-to-qa-handoff.md" in storage


def test_qa_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-qa-role.sh").exists()
