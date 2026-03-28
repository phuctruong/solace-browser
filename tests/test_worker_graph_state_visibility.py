from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Tickets 1 & 2: Visible Graph surfaces ──


def test_html_has_graph_state_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-graph-state-card" in html
    assert "Execution Graph Trace" in html


def test_hub_app_js_has_graph_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerGraphState" in js


def test_hub_app_js_has_active_graph_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Active Graph Context:" in js
    assert "Graph Basis:" in js
    assert "Path Basis:" in js
    assert "role-derived visible execution graph" in js
    assert "visible active stage for current role/run" in js


# ── Ticket 3: Honest Graph States ──


def test_hub_app_js_has_honest_node_states() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "PLANNER &rarr; ROUTER" in js
    assert "Active Node Context" in js
    assert "UNKNOWN_GRAPH" in js


# ── Ticket 4: Prime Mermaid Artifact ──


def test_prime_mermaid_graph_state_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-graph-state.prime-mermaid.md").exists()


def test_smoke_worker_graph_state_exists() -> None:
    scripts = REPO_ROOT / "scripts"
    assert (scripts / "smoke-worker-graph-state.sh").exists()
