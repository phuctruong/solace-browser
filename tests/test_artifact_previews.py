from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Ticket 1: Native artifact preview panel ──


def test_html_has_artifact_preview_card() -> None:
    index_html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-artifact-preview-card" in index_html
    assert "dev-artifact-previews" in index_html
    assert "Artifact Previews" in index_html


def test_hub_app_js_has_hydrate_previews() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "hydrateArtifactPreviews" in hub_app
    assert "fetchArtifactText" in hub_app


# ── Ticket 2: Inline preview for at least 2 artifacts ──


def test_hub_app_js_has_payload_preview() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "buildPayloadPreview" in hub_app
    assert "preview-payload" in hub_app


def test_hub_app_js_has_events_preview() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "buildEventsPreview" in hub_app
    assert "preview-events" in hub_app


def test_hub_app_js_has_report_preview() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "buildReportPreview" in hub_app
    assert "preview-report" in hub_app
    assert "srcdoc" in hub_app  # sandboxed iframe


# ── Ticket 3: Missing-state treatment ──


def test_hub_app_js_has_missing_state() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "buildMissingState" in hub_app
    assert "missing" in hub_app
    assert "not found in outbox" in hub_app


def test_hub_app_js_handles_all_error_codes() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "r.status === 404" in hub_app
    assert "r.status === 403" in hub_app
    assert "fetch error" in hub_app


# ── Ticket 4: Prime Mermaid ──


def test_prime_mermaid_artifact_preview_exists() -> None:
    diagrams_root = REPO_ROOT / "specs" / "solace-dev" / "diagrams"

    assert (diagrams_root / "artifact-preview-flow.prime-mermaid.md").exists()


# ── Ticket 5: Structural ──


def test_artifact_preview_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-artifact-preview.sh").exists()


def test_show_run_inspection_triggers_previews() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "hydrateArtifactPreviews(appId, runId)" in hub_app
