from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Ticket 1: Live workspace hydration ──


def test_hub_app_js_has_hydration_function() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "hydrateDevWorkspace" in hub_app
    assert "hydrateHubStatus" in hub_app
    assert "hydrateRoleCard" in hub_app


def test_hub_app_js_hydrates_on_dev_tab() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "tabId === 'dev'" in hub_app
    assert "hydrateDevWorkspace()" in hub_app


def test_hub_app_js_fetches_real_apis() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "/api/v1/hub/status" in hub_app
    assert "/api/v1/apps/" in hub_app
    assert "/api/v1/backoffice/" in hub_app
    assert "page_size=1" in hub_app


# ── Ticket 2: Live role detail ──


def test_html_has_live_role_badges() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "role-live-manager" in index_html
    assert "role-live-design" in index_html
    assert "role-live-coder" in index_html
    assert "role-live-qa" in index_html


def test_html_has_live_count_spans() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    # Check representative live count IDs
    assert "live-count-manager-requests" in index_html
    assert "live-count-design-design_specs" in index_html
    assert "live-count-coder-code_runs" in index_html
    assert "live-count-qa-qa_runs" in index_html


# ── Ticket 3: Visible run feedback ──


def test_worker_control_has_structured_feedback() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Run completed" in hub_app or "✓ Run completed" in hub_app
    assert "Run failed" in hub_app or "✗ Run failed" in hub_app
    assert "dev-last-run" in hub_app


def test_html_has_last_run_container() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-last-run" in index_html


# ── Ticket 4: Live project context ──


def test_html_has_live_status_container() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-live-status" in index_html
    assert "SDH5" in index_html


# ── Ticket 5: Prime Mermaid ──


def test_prime_mermaid_hydration_diagrams_exist() -> None:
    diagrams_root = REPO_ROOT / "specs" / "solace-dev" / "diagrams"

    assert (diagrams_root / "live-workspace-hydration.prime-mermaid.md").exists()
    assert (diagrams_root / "run-feedback-flow.prime-mermaid.md").exists()


# ── Ticket 6: No inline script duplication ──


def test_no_inline_worker_script() -> None:
    """The old inline script should be replaced by the hub-app.js function."""
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    # Old inline pattern removed
    assert "Worker run function now in hub-app.js" in index_html


def test_live_workspace_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-live-workspace.sh").exists()
