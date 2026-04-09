from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_html_has_department_memory_queue_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-department-memory-queue-card" in html
    assert "Department Memory Queue" in html


def test_hub_app_js_has_department_memory_queue_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateDepartmentMemoryQueue" in js
    assert "real Back Office memory_entries and conventions tables" in js


def test_hub_app_js_has_honest_department_memory_states() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "PROMOTED" in js
    assert "PENDING REVIEW" in js
    assert "BLOCKED" in js
    assert "Candidate:" in js
    assert "Review Basis:" in js


def test_hub_app_js_has_active_department_memory_context() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "Active Queue Context:" in js
    assert "Viewer Role:" in js
    assert "Queue Basis:" in js
    assert "Promotion Basis:" in js


def test_prime_mermaid_department_memory_queue_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "department-memory-queue.prime-mermaid.md").exists()


def test_smoke_script_exists() -> None:
    scripts = REPO_ROOT / "scripts"
    assert (scripts / "smoke-department-memory-queue.sh").exists()
