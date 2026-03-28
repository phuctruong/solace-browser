from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Ticket 1: URL-backed selected-run context ──


def test_hub_app_js_has_parse_inspection_hash() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "parseInspectionHash" in hub_app
    assert "#inspect=" in hub_app


def test_hub_app_js_has_set_inspection_hash() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "setInspectionHash" in hub_app
    assert "history.replaceState" in hub_app


def test_hub_app_js_select_run_sets_hash() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "setInspectionHash(appId, runId)" in hub_app


# ── Ticket 2: Restore from hash ──


def test_hub_app_js_hash_has_precedence() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "var hashContext = parseInspectionHash()" in hub_app
    assert "hashContext || loadSelectedRun()" in hub_app


def test_hub_app_js_restore_has_source_param() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "deep-link" in hub_app
    assert "function restoreSelectedRun(appId, runId, storedRow, source)" in hub_app


# ── Ticket 3: Invalid deep-link fallback ──


def test_hub_app_js_has_invalid_deep_link_fallback() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "showInvalidDeepLinkFallback" in hub_app
    assert "prependInvalidDeepLinkNotice" in hub_app
    assert "deep link invalid" in hub_app
    assert "was not found" in hub_app
    assert "Falling back to <code>" in hub_app


def test_hub_app_js_has_clear_inspection_hash() -> None:
    hub_app = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "clearInspectionHash" in hub_app


# ── Ticket 4: Prime Mermaid ──


def test_prime_mermaid_deep_link_exists() -> None:
    diagrams_root = REPO_ROOT / "specs" / "solace-dev" / "diagrams"

    assert (diagrams_root / "deep-link-inspection.prime-mermaid.md").exists()


def test_deep_link_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-deep-link-inspection.sh").exists()
