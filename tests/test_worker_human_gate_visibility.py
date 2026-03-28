from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Tickets 1 & 2: Visible Human Gate surfaces ──


def test_html_has_human_gate_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-human-gate-card" in html
    assert "Human-in-the-Loop Gate" in html


def test_hub_app_js_has_human_gate_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerHumanGate" in js


def test_hub_app_js_has_active_human_gate_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Active Human Gate Context:" in js
    assert "Gate Basis:" in js
    assert "Intervention Basis:" in js
    assert "role-derived visible approval contract" in js
    assert "human review state for current role/run" in js


# ── Ticket 3: Honest Human Gate States ──


def test_hub_app_js_has_honest_states() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "not_yet_at_gate" in js
    assert "awaiting_human" in js
    assert "intervention_required" in js
    assert "approved" in js


def test_hub_app_js_actionable_buttons() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    # The button shouldn't show up for autonomous/approved states
    assert "Review & Approve" in js


# ── Ticket 4: Prime Mermaid Artifact ──


def test_prime_mermaid_human_gate_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-human-gate.prime-mermaid.md").exists()


def test_smoke_worker_human_gate_exists() -> None:
    scripts = REPO_ROOT / "scripts"
    assert (scripts / "smoke-worker-human-gate.sh").exists()
