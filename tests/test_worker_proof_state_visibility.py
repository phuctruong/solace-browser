from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Tickets 1 & 2: Visible Proof surfaces ──


def test_html_has_proof_state_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-proof-state-card" in html
    assert "Transparency & Proof State" in html


def test_hub_app_js_has_proof_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerProofState" in js


def test_hub_app_js_has_active_proof_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Active Proof Context:" in js
    assert "Proof Basis:" in js
    assert "Transparency Basis:" in js
    assert "role-derived visible evidence contract" in js
    assert "visible proof state for current role/run" in js


# ── Ticket 3: Honest Proof States ──


def test_hub_app_js_has_honest_states() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "proven" in js
    assert "partial" in js
    assert "missing" in js


def test_hub_app_js_has_evidence_logs() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Evidence Present:" in js
    assert "Unproven / Missing Elements:" in js


# ── Ticket 4: Prime Mermaid Artifact ──


def test_prime_mermaid_proof_state_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-proof-state.prime-mermaid.md").exists()


def test_smoke_worker_proof_state_exists() -> None:
    scripts = REPO_ROOT / "scripts"
    assert (scripts / "smoke-worker-proof-state.sh").exists()
