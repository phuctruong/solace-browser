from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Tickets 1 & 2: Visible Store surfaces ──


def test_html_has_convention_store_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-convention-store-card" in html
    assert "Convention Store Binding" in html


def test_hub_app_js_has_convention_store_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerConventionStore" in js


def test_hub_app_js_has_active_convention_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Active Convention Context:" in js
    assert "Convention Basis:" in js
    assert "Replay Basis:" in js
    assert "role-derived visible convention binding" in js
    assert "visible convention maturity for current role/run" in js


# ── Ticket 3: Honest Convention Store States ──


def test_hub_app_js_has_honest_store_states() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Active Convention:" in js
    assert "Store Ring:" in js
    assert "replayable" in js
    assert "discover_only" in js
    assert "partial" in js
    assert "GLOBAL" in js
    assert "LOCAL" in js
    assert "SHARED" in js


# ── Ticket 4: Prime Mermaid Artifact ──


def test_prime_mermaid_convention_store_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-convention-store.prime-mermaid.md").exists()


def test_smoke_worker_convention_store_exists() -> None:
    scripts = REPO_ROOT / "scripts"
    assert (scripts / "smoke-worker-convention-store.sh").exists()
