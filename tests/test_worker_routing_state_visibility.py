from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Tickets 1 & 2: Visible Routing surfaces ──


def test_html_has_routing_state_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-routing-state-card" in html
    assert "Hybrid Routing" in html


def test_hub_app_js_has_routing_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerRoutingState" in js


# ── Ticket 3: Honest Routing States ──


def test_hub_app_js_has_honest_routing_states() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Route Selection:" in js
    assert "Cost &amp; Latency Profile:" in js
    assert "replay" in js
    assert "deterministic" in js
    assert "local_model" in js
    assert "external_api" in js


def test_hub_app_js_has_active_routing_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Active Routing Context:" in js
    assert "Routing Basis:" in js
    assert "Cost Basis:" in js


# ── Ticket 4: Prime Mermaid Artifact ──


def test_prime_mermaid_routing_state_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-routing-state.prime-mermaid.md").exists()


def test_smoke_script_exists() -> None:
    scripts = REPO_ROOT / "scripts"
    assert (scripts / "smoke-worker-routing-state.sh").exists()
