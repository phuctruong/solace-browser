from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Ticket 1: Persist selected-run state ──


def test_hub_app_js_has_save_selected_run() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "saveSelectedRun" in hub_app
    assert "sessionStorage" in hub_app
    assert "solace_dev_selected_run" in hub_app


def test_hub_app_js_select_run_persists() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    # __solaceSelectRun must call saveSelectedRun
    assert "saveSelectedRun(appId, runId)" in hub_app


# ── Ticket 2: Rehydrate from stored selection ──


def test_hub_app_js_has_load_selected_run() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "loadSelectedRun" in hub_app


def test_hub_app_js_has_restore_selected_run() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "restoreSelectedRun" in hub_app
    assert "restored:" in hub_app
    assert "storedRow.querySelector('.sat10-select-run')" in hub_app


def test_hub_app_js_finish_hydration_checks_stored() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "var stored = loadSelectedRun()" in hub_app


# ── Ticket 3: Handle invalid stored selection ──


def test_hub_app_js_has_stale_fallback() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "prependStaleFallbackNotice" in hub_app
    assert "fallback:" in hub_app
    assert "no longer in the runs list" in hub_app
    assert "Falling back to <code>" in hub_app


def test_hub_app_js_has_clear_selected_run() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "clearSelectedRun" in hub_app


def test_selected_run_persistence_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-selected-run-persistence.sh").exists()


# ── Ticket 4: Prime Mermaid ──


def test_prime_mermaid_selected_run_persistence_exists() -> None:
    diagrams_root = REPO_ROOT / "specs" / "solace-dev" / "diagrams"

    assert (diagrams_root / "selected-run-persistence.prime-mermaid.md").exists()
