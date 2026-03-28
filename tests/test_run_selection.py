from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Ticket 1: Run selection drives the workspace ──


def test_hub_app_js_has_select_run() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "__solaceSelectRun" in hub_app
    assert "sat10-select-run" in hub_app
    assert "▸ select" in hub_app
    assert "data-report-exists" in hub_app
    assert "data-events-exists" in hub_app


def test_hub_app_js_has_highlight() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "highlightSelectedRun" in hub_app
    assert "● viewing" in hub_app
    assert "sat10-run-row" in hub_app


def test_hub_app_js_select_triggers_inspection_and_preview() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    # __solaceSelectRun must call showRunInspection
    assert "showRunInspection(appId, runId" in hub_app
    # showRunInspection must call hydrateArtifactPreviews
    assert "hydrateArtifactPreviews(appId, runId)" in hub_app
    assert "clickedEl.dataset.reportExists" in hub_app


# ── Ticket 2: Artifact switching across runs ──


def test_hub_app_js_artifact_preview_takes_parameters() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    # hydrateArtifactPreviews takes appId, runId — not hardcoded
    assert "function hydrateArtifactPreviews(appId, runId)" in hub_app


# ── Ticket 3: Missing artifacts still honest ──


def test_hub_app_js_still_has_missing_state() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "buildMissingState" in hub_app
    assert "not found in outbox" in hub_app


# ── Ticket 4: Prime Mermaid ──


def test_prime_mermaid_run_selection_exists() -> None:
    diagrams_root = REPO_ROOT / "specs" / "solace-dev" / "diagrams"

    assert (diagrams_root / "run-selection-flow.prime-mermaid.md").exists()


# ── Ticket 5: No stale /report path ──


def test_hub_app_js_no_stale_report_path() -> None:
    """History report links should use /artifact/report.html, not /report."""
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "/reports/" not in hub_app


def test_hub_app_js_backward_compat_alias() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "__solaceInspectRun = window.__solaceSelectRun" in hub_app


def test_run_selection_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-run-selection.sh").exists()
