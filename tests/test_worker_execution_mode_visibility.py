from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Tickets 1 & 2: Visible Execution Mode and Convention surfaces ──


def test_html_has_execution_mode_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-execution-mode-card" in html
    assert "Execution Mode & Convention" in html


def test_hub_app_js_has_execution_mode_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerExecutionMode" in js
    assert "Execution Mode:" in js
    assert "Governing Convention / Prime Reuse" in js


def test_hub_app_js_has_active_execution_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Active Execution Context:" in js
    assert "Mode Basis:" in js
    assert "Convention Basis:" in js
    assert "role-derived visible contract" in js
    assert "visible reusable artifact for current role" in js


def test_hub_app_js_has_discover_and_replay_modes() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "DISCOVER" in js
    assert "REPLAY" in js


# ── Ticket 3: Tied to active context ──


def test_hub_app_js_execution_mode_hooked_in() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    # Hooked from updateWorkerDetail
    assert "updateWorkerExecutionMode(appId, runId);" in js


def test_hub_app_js_all_roles_defined() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "roleName === 'manager'" in js
    assert "roleName === 'design'" in js
    assert "roleName === 'coder'" in js
    assert "roleName === 'qa'" in js


# ── Ticket 4: Prime Mermaid Artifact ──


def test_prime_mermaid_execution_mode_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-execution-mode.prime-mermaid.md").exists()


def test_smoke_worker_execution_mode_exists() -> None:
    scripts = REPO_ROOT / "scripts"
    assert (scripts / "smoke-worker-execution-mode.sh").exists()
