from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


# ── Tickets 1 & 2: Visible Inbox/Outbox surfaces ──


def test_html_has_inbox_outbox_card() -> None:
    html = (
        REPO_ROOT / "solace-hub" / "src" / "index.html"
    ).read_text(encoding="utf-8")

    assert "dev-worker-inbox-outbox-card" in html
    assert "Worker Inbox / Outbox Contract" in html


def test_hub_app_js_has_inbox_outbox_logic() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "updateWorkerInboxOutbox" in js
    assert "Inbox Inputs (read-only context)" in js
    assert "Outbox Outputs (result surface)" in js
    assert "Active Contract Context:" in js
    assert "Outbox Root:" in js


# ── Ticket 3: Tied to active context ──


def test_hub_app_js_inbox_outbox_hooked_in() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    # Hooked from updateWorkerDetail
    assert "updateWorkerInboxOutbox(appId, runId);" in js


def test_hub_app_js_all_roles_defined() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "roleName === 'manager'" in js
    assert "roleName === 'design'" in js
    assert "roleName === 'coder'" in js
    assert "roleName === 'qa'" in js


def test_hub_app_js_handoff_docs_present() -> None:
    js = (
        REPO_ROOT / "solace-hub" / "src" / "hub-app.js"
    ).read_text(encoding="utf-8")

    assert "manager-to-design-handoff.md" in js
    assert "design-to-coder-handoff.md" in js
    assert "coder-to-qa-handoff.md" in js
    assert "qa-signoffs" in js
    assert "solace-worker-inbox-contract.md" in js


# ── Ticket 4: Prime Mermaid Artifact ──


def test_prime_mermaid_inbox_outbox_exists() -> None:
    diagrams = REPO_ROOT / "specs" / "solace-dev" / "diagrams"
    assert (diagrams / "worker-inbox-outbox.prime-mermaid.md").exists()


def test_worker_inbox_outbox_smoke_script_exists() -> None:
    assert (REPO_ROOT / "scripts" / "smoke-worker-inbox-outbox.sh").exists()
