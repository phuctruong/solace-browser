from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Tickets 1 & 2: Visible Assignment Packet surfaces ──


def test_html_has_assignment_packet_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-assignment-packet-card" in html
    assert "Worker Assignment Packet" in html


def test_hub_app_js_has_assignment_packet_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerAssignmentPacket" in js
    assert "Task Statement / Objective" in js
    assert "Scope Change Policy" in js
    assert "Evidence Contract (Required Output)" in js
    assert "Active Assignment Context:" in js
    assert "Packet Basis:" in js
    assert "Outbox Root:" in js


def test_hub_app_js_has_scope_lock() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "FAIL_AND_NEW_TASK" in js


# ── Ticket 3: Tied to active context ──


def test_hub_app_js_assignment_hooked_in() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    # Hooked from updateWorkerDetail
    assert "updateWorkerAssignmentPacket(appId, runId);" in js


def test_hub_app_js_all_roles_defined() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "roleName === 'manager'" in js
    assert "roleName === 'design'" in js
    assert "roleName === 'coder'" in js
    assert "roleName === 'qa'" in js


# ── Ticket 4: Prime Mermaid Artifact ──


def test_prime_mermaid_assignment_packet_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-assignment-packet.prime-mermaid.md").exists()


def test_worker_assignment_packet_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-worker-assignment-packet.sh").exists()
