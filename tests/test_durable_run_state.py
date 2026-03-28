from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Ticket 1: Runtime endpoint for listing runs ──


def test_apps_rs_has_list_runs_route() -> None:
    apps_rs = (
        REPO_ROOT / "solace-runtime" / "src" / "routes" / "apps.rs"
    ).read_text(encoding="utf-8")

    assert "list_runs" in apps_rs
    assert "/api/v1/apps/:app_id/runs" in apps_rs


def test_apps_rs_list_runs_scans_outbox() -> None:
    apps_rs = (
        REPO_ROOT / "solace-runtime" / "src" / "routes" / "apps.rs"
    ).read_text(encoding="utf-8")

    assert "outbox" in apps_rs
    assert "report_exists" in apps_rs
    assert "events_exist" in apps_rs


# ── Ticket 2: Hydration on tab load ──


def test_hub_app_js_has_hydrate_run_history() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "hydrateRunHistory" in hub_app
    assert "/api/v1/apps/" in hub_app
    assert "/runs" in hub_app


def test_hub_app_js_hydrates_latest_known_run() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "latestRun" in hub_app
    assert "latestRunAppId" in hub_app
    assert "finishHydration" in hub_app


# ── Ticket 3: Run history panel ──


def test_html_has_run_history_card() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-run-history-card" in index_html
    assert "dev-run-history" in index_html
    assert "Run History" in index_html


def test_hub_app_js_has_inspect_run() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "__solaceInspectRun" in hub_app
    assert "/apps/" in hub_app
    assert "/report" in hub_app
    assert "/reports/" not in hub_app


# ── Ticket 4: Prime Mermaid ──


def test_prime_mermaid_durable_run_state_exists() -> None:
    diagrams_root = REPO_ROOT / "specs" / "solace-dev" / "diagrams"

    assert (diagrams_root / "durable-run-state.prime-mermaid.md").exists()


# ── Ticket 5: Structural ──


def test_hub_app_js_calls_hydrate_on_dev_tab() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "hydrateRunHistory()" in hub_app


def test_durable_run_state_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-durable-run-state.sh").exists()
