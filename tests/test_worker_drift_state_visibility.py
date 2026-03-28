from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Tickets 1 & 2: Visible Drift surfaces ──


def test_html_has_drift_state_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-drift-state-card" in html
    assert "Drift & Adaptive Replay" in html


def test_hub_app_js_has_drift_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerDriftState" in js


def test_hub_app_js_has_active_drift_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Active Drift Context:" in js
    assert "Replay Basis:" in js
    assert "Drift Basis:" in js
    assert "role-derived visible replay-safety contract" in js
    assert "visible environment deviation for current role/run" in js


# ── Ticket 3: Honest Drift States ──


def test_hub_app_js_has_honest_drift_states() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Replay Safety Evaluation:" in js
    assert "safe_replay" in js
    assert "drift_detected" in js
    assert "fallback_to_discover" in js
    assert "unknown_state" in js


# ── Ticket 4: Prime Mermaid Artifact ──


def test_prime_mermaid_drift_state_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-drift-state.prime-mermaid.md").exists()


def test_smoke_worker_drift_state_exists() -> None:
    scripts = REPO_ROOT / "scripts"
    assert (scripts / "smoke-worker-drift-state.sh").exists()
