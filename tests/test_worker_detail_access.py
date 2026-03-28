from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Ticket 1 & 2: Visible worker-detail panel tied to active context ──


def test_html_has_worker_detail() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-detail-card" in html
    assert "Worker Detail" in html
    assert "dev-worker-role-pill" in html
    assert "dev-worker-diagram-preview" in html


def test_hub_app_js_has_update_worker_detail() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerDetail" in js
    assert "dev-worker-detail" in js
    assert "dev-worker-role-pill" in js
    assert "dev-worker-diagram-preview" in js


def test_hub_app_js_worker_detail_called_from_update_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    # updateWorkerDetail must be hooked into updateInspectionContext
    assert "updateWorkerDetail(appId, runId);" in js


def test_hub_app_js_worker_detail_shows_identity() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Worker Identity:" in js
    assert "App ID:" in js
    assert "Artifacts Outbox:" in js


# ── Ticket 3: Native Prime Mermaid diagram access ──


def test_hub_app_js_has_prime_mermaid_links() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Governing Prime Mermaid Diagrams:" in js
    assert "__solaceShowWorkerDiagram" in js
    assert "renderWorkerDiagramPreview" in js
    assert "role-stack.prime-mermaid.md" in js
    assert "browser-page-map.prime-mermaid.md" in js
    assert "scrollIntoView" in js
    assert "vscode://file" not in js


def test_hub_app_js_has_dynamic_handoff_docs() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "manager-to-design-handoff.md" in js
    assert "design-to-coder-handoff.md" in js
    assert "coder-to-qa-handoff.md" in js


# ── Ticket 4: Prime Mermaid Artifact ──


def test_prime_mermaid_worker_detail_access_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-detail-access.prime-mermaid.md").exists()


def test_worker_detail_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-worker-detail-access.sh").exists()
