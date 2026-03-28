from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Ticket 1: Rust artifact-serving route ──


def test_apps_rs_has_artifact_route() -> None:
    apps_rs = (
        REPO_ROOT / "solace-runtime" / "src" / "routes" / "apps.rs"
    ).read_text(encoding="utf-8")

    assert "serve_run_artifact" in apps_rs
    assert "/artifact/:filename" in apps_rs


def test_apps_rs_has_whitelist() -> None:
    apps_rs = (
        REPO_ROOT / "solace-runtime" / "src" / "routes" / "apps.rs"
    ).read_text(encoding="utf-8")

    assert "ALLOWED_ARTIFACTS" in apps_rs
    assert "report.html" in apps_rs
    assert "payload.json" in apps_rs
    assert "stillwater.json" in apps_rs
    assert "events.jsonl" in apps_rs


def test_apps_rs_serves_correct_content_types() -> None:
    apps_rs = (
        REPO_ROOT / "solace-runtime" / "src" / "routes" / "apps.rs"
    ).read_text(encoding="utf-8")

    assert "text/html" in apps_rs
    assert "application/json" in apps_rs
    assert "application/x-ndjson" in apps_rs


# ── Ticket 2: JS uses real artifact routes ──


def test_hub_app_js_uses_artifact_route() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "/artifact/" in hub_app
    assert "artifactBase" in hub_app


def test_hub_app_js_no_reports_path() -> None:
    """Old /reports/ path should be gone — replaced by /api/v1/.../artifact/."""
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "/reports/" not in hub_app


def test_hub_app_js_no_fake_disclaimer() -> None:
    """The 'not exposed yet' disclaimer should be gone."""
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "not exposed as first-class" not in hub_app


def test_hub_app_js_links_five_artifacts() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    for artifact in ["report.html", "payload.json", "stillwater.json", "events.jsonl"]:
        assert artifact in hub_app, f"artifact link missing: {artifact}"


# ── Ticket 3: Prime Mermaid ──


def test_prime_mermaid_artifact_access_exists() -> None:
    diagrams_root = REPO_ROOT / "specs" / "solace-dev" / "diagrams"

    assert (diagrams_root / "artifact-access-flow.prime-mermaid.md").exists()


def test_artifact_access_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-artifact-access.sh").exists()
