from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Ticket 1: Last-run inspection surface ──


def test_hub_app_js_has_extract_run_id() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "extractRunId" in hub_app
    assert "YYYYMMDD" in hub_app or r"\d{8}-\d{6}" in hub_app


def test_hub_app_js_has_show_run_inspection() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "showRunInspection" in hub_app
    assert "buildRunInspectionHTML" in hub_app


def test_html_has_run_inspection_container() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-run-inspection" in index_html


# ── Ticket 2: Report/artifact inspection path ──


def test_hub_app_js_has_report_link() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "report.html" in hub_app
    assert "/api/v1/apps/" in hub_app
    assert "/runs/" in hub_app
    assert "/report" in hub_app


def test_hub_app_js_has_artifact_links() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "run detail" in hub_app
    assert "events api" in hub_app
    assert "report html" in hub_app
    assert "payload.json and stillwater.json are not exposed as first-class Hub routes yet" in hub_app


# ── Ticket 3: Event/run-detail visibility ──


def test_hub_app_js_fetches_run_events() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "fetchRunEvents" in hub_app
    assert "/runs/" in hub_app
    assert "/events" in hub_app


def test_hub_app_js_shows_chain_validity() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "chain_valid" in hub_app
    assert "chain ✓" in hub_app or "chain" in hub_app


def test_hub_app_js_shows_event_detail() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "event_type" in hub_app
    assert "show " in hub_app  # "show N events"


# ── Ticket 4: Prime Mermaid ──


def test_prime_mermaid_run_inspection_exists() -> None:
    diagrams_root = REPO_ROOT / "specs" / "solace-dev" / "diagrams"

    assert (diagrams_root / "run-inspection-flow.prime-mermaid.md").exists()


# ── Ticket 5: Routes match reality ──


def test_apps_rs_has_events_endpoint() -> None:
    apps_rs = (
        REPO_ROOT / "solace-runtime" / "src" / "routes" / "apps.rs"
    ).read_text(encoding="utf-8")

    assert "get_run_events" in apps_rs
    assert "runs/:run_id/events" in apps_rs


def test_run_inspection_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-run-inspection.sh").exists()
