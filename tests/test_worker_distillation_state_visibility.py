from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_html_has_distillation_state_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-distillation-state-card" in html
    assert "Convention Distillation" in html


def test_hub_app_js_has_distillation_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerDistillationState" in js


def test_hub_app_js_has_honest_distillation_states() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Promotion Status:" in js
    assert "Candidate Convention:" in js
    assert "Distillation Basis:" in js
    assert "promoted" in js
    assert "pending_candidate" in js
    assert "blocked" in js


def test_hub_app_js_has_active_distillation_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Active Distillation Context:" in js
    assert "Promotion Basis:" in js
    assert "Evidence Basis:" in js


def test_prime_mermaid_distillation_state_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-distillation-state.prime-mermaid.md").exists()


def test_smoke_script_exists() -> None:
    scripts = REPO_ROOT / "scripts"
    assert (scripts / "smoke-worker-distillation-state.sh").exists()
