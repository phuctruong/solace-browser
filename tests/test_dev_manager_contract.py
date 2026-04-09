from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "src" / "browser" / "inbox_outbox.py"


spec = importlib.util.spec_from_file_location("inbox_outbox", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_manager_app_has_real_inbox_outbox_contract() -> None:
    manager = module.InboxOutboxManager(apps_root=REPO_ROOT / "data" / "apps")

    result = manager.validate_inbox("solace-dev-manager")

    assert result["valid"] is True


def test_manager_app_has_prime_mermaid_source() -> None:
    app_root = REPO_ROOT / "data" / "apps" / "solace-dev-manager"

    assert (app_root / "manifest.prime-mermaid.md").exists()
    assert (app_root / "recipe.prime-mermaid.md").exists()
    assert (app_root / "manifest.yaml").exists()


def test_manager_specs_exist() -> None:
    specs_root = REPO_ROOT / "specs" / "solace-dev"

    assert (specs_root / "manager-source-map.md").exists()
    assert (specs_root / "storage-model.md").exists()
    assert (specs_root / "diagrams" / "dev-role-map.prime-mermaid.md").exists()
    assert (
        specs_root / "project-mappings" / "solace-browser.prime-mermaid.md"
    ).exists()


def test_manager_manifest_exposes_runtime_backed_workflow_objects() -> None:
    manifest = (
        REPO_ROOT / "data" / "apps" / "solace-dev-manager" / "manifest.yaml"
    ).read_text(encoding="utf-8")

    assert "- name: worker_inboxes" in manifest
    assert "- name: runs" in manifest
    assert "- name: memory_entries" in manifest
    assert "- name: conventions" in manifest
    assert "- name: source_assignment_id" in manifest
    assert 'values: ["ready", "shipped", "canceled"]' in manifest
