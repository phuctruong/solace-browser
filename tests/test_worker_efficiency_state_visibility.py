from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Tickets 1 & 2: Visible Efficiency surfaces ──


def test_html_has_efficiency_state_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-efficiency-state-card" in html
    assert "Efficiency Metrics" in html


def test_hub_app_js_has_efficiency_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerEfficiencyState" in js


# ── Ticket 3: Honest Efficiency States ──


def test_hub_app_js_has_honest_efficiency_states() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "System Economics Profile:" in js
    assert "Replay Rate:" in js
    assert "Compute Economics:" in js
    assert "Execution Latency:" in js
    assert "Replay Heavy" in js
    assert "Discover Heavy (Ripple)" in js
    assert "Mixed (Local + Replay)" in js


def test_hub_app_js_has_active_efficiency_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Active Efficiency Context:" in js
    assert "Efficiency Basis:" in js
    assert "Latency Basis:" in js


# ── Ticket 4: Prime Mermaid Artifact ──


def test_prime_mermaid_efficiency_state_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-efficiency-state.prime-mermaid.md").exists()


def test_smoke_script_exists() -> None:
    scripts = REPO_ROOT / "scripts"
    assert (scripts / "smoke-worker-efficiency-state.sh").exists()
