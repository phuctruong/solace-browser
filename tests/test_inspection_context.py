from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Ticket 1: Visible inspection-context panel ──


def test_html_has_context_panel() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-inspection-context-card" in html
    assert "dev-inspection-context" in html
    assert "Inspection Context" in html
    assert "dev-context-source-pill" in html


def test_hub_app_js_has_update_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateInspectionContext" in js
    assert "dev-inspection-context" in js
    assert "dev-context-source-pill" in js


# ── Ticket 2: Copy-link affordance ──


def test_hub_app_js_has_copy_link() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "__solaceCopyInspectionLink" in js
    assert "dev-copy-link-btn" in js
    assert "dev-context-link" in js
    assert "copy link" in js


def test_hub_app_js_has_clipboard_and_fallback() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "navigator.clipboard" in js
    assert "execCommand" in js
    assert "copied" in js


# ── Ticket 3: Source indicator ──


def test_hub_app_js_has_all_source_types() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    for source in ["deep-link", "restored", "selected", "fallback", "invalid"]:
        assert source in js, f"source type missing: {source}"


def test_hub_app_js_labels_invalid_fallback_honestly() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "invalidDeepLink ? 'invalid' : (staleSelection ? 'fallback' : 'selected')" in js
    assert "Requested deep link was invalid" in js


def test_hub_app_js_context_called_from_select() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateInspectionContext(appId, runId, 'selected')" in js


def test_hub_app_js_context_called_from_restore() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateInspectionContext(appId, runId, label)" in js


# ── Ticket 4: Prime Mermaid ──


def test_prime_mermaid_inspection_context_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "inspection-context-panel.prime-mermaid.md").exists()


def test_inspection_context_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-inspection-context.sh").exists()
