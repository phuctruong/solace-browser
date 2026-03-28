from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Ticket 1: Integrated workspace shell ──


def test_integrated_dev_workspace_shell_exists() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-project-header" in index_html
    assert "Integrated Dev Workspace" in index_html
    assert "solace-browser" in index_html


# ── Ticket 2: Role roster and role detail ──


def test_role_roster_has_all_four_roles() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-role-roster" in index_html
    assert "role-card-manager" in index_html
    assert "role-card-design" in index_html
    assert "role-card-coder" in index_html
    assert "role-card-qa" in index_html


def test_role_detail_panels_exist() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "role-detail-manager" in index_html
    assert "role-detail-design" in index_html
    assert "role-detail-coder" in index_html
    assert "role-detail-qa" in index_html


def test_role_detail_shows_inbox_outbox() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    # Each detail should show inbox and outbox
    assert index_html.count("Inbox / Outbox / Artifacts") >= 4


# ── Ticket 3: Project detail surface ──


def test_project_detail_surface() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-project-header" in index_html
    assert "4 roles active" in index_html
    # Project quick links
    assert "/backoffice/solace-dev-manager/projects" in index_html
    assert "/backoffice/solace-dev-manager/requests" in index_html
    assert "/backoffice/solace-dev-manager/assignments" in index_html


# ── Ticket 4: Worker control ──


def test_worker_control_buttons_exist() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-control" in index_html
    assert "run-worker-manager" in index_html
    assert "run-worker-design" in index_html
    assert "run-worker-coder" in index_html
    assert "run-worker-qa" in index_html
    assert "__solaceRunWorker" in index_html
    assert "/api/v1/apps/run/" in index_html


# ── Ticket 5: Prime Mermaid source ──


def test_prime_mermaid_workspace_diagram_exists() -> None:
    diagrams_root = REPO_ROOT / "specs" / "solace-dev" / "diagrams"

    assert (diagrams_root / "integrated-dev-workspace.prime-mermaid.md").exists()
    assert (diagrams_root / "worker-control-flow.prime-mermaid.md").exists()


def test_inline_role_stack_diagram_in_html() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-role-stack-diagram" in index_html
    assert "Prime Mermaid Source" in index_html


# ── Ticket 6: hub-app.js dev tab side-effect ──


def test_hub_app_js_has_dev_tab_support() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    # The hub-app.js should support tab switching to dev
    assert "set_active_tab" in hub_app or "setActiveTabState" in hub_app


def test_integrated_workspace_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-integrated-workspace.sh").exists()
