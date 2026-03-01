from __future__ import annotations

import importlib.util
import json
import socket
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_PATH = REPO_ROOT / "web" / "server.py"


def _load_server_module() -> Any:
    spec = importlib.util.spec_from_file_location("solace_web_server", SERVER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    body: bytes | None = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()
            return response.status, json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, json.loads(raw.decode("utf-8"))


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def solace_home(tmp_path: Path) -> Path:
    home = tmp_path / "solace-home"
    app_root = home / "apps" / "gmail-inbox-triage"
    inbox_root = app_root / "inbox"
    outbox_root = app_root / "outbox"
    for path in [
        app_root / "diagrams",
        inbox_root / "prompts",
        inbox_root / "templates",
        inbox_root / "assets",
        inbox_root / "policies",
        inbox_root / "datasets",
        inbox_root / "requests",
        inbox_root / "conventions" / "examples",
        outbox_root / "previews",
        outbox_root / "drafts",
        outbox_root / "reports",
        outbox_root / "suggestions",
        outbox_root / "runs" / "run-demo",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "id": "gmail-inbox-triage",
        "name": "Gmail Inbox Triage",
        "description": "Priority sort and drafting",
        "category": "communications",
        "status": "installed",
        "safety": "B",
        "site": "mail.google.com",
        "scopes": ["gmail.read.inbox", "gmail.draft.create"],
        "partners": {
            "produces_for": ["slack-triage", "calendar-brief"],
            "consumes_from": ["morning-brief"],
        },
        "required_inbox": {
            "prompts": ["triage-rules.md"],
            "templates": ["meeting-reply.md"],
            "assets": [],
            "policies": ["never-auto-send.yaml"],
            "datasets": [],
            "requests": [],
            "conventions": {
                "config": "config.yaml",
                "defaults": "defaults.yaml",
            },
        },
    }
    (app_root / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    (app_root / "recipe.json").write_text(json.dumps({"id": "gmail", "steps": []}), encoding="utf-8")
    (app_root / "budget.json").write_text(json.dumps({"remaining_runs": 5, "reads_per_run": 50}), encoding="utf-8")
    (app_root / "diagrams" / "workflow.md").write_text("```mermaid\nflowchart TD\nA-->B\n```\n", encoding="utf-8")
    (app_root / "diagrams" / "data-flow.md").write_text("```mermaid\nflowchart TD\nA-->B\n```\n", encoding="utf-8")
    (app_root / "diagrams" / "partner-contracts.md").write_text("```mermaid\nflowchart TD\nA-->B\n```\n", encoding="utf-8")
    (inbox_root / "prompts" / "triage-rules.md").write_text("Sort by urgency.", encoding="utf-8")
    (inbox_root / "templates" / "meeting-reply.md").write_text("Thanks for the note.", encoding="utf-8")
    (inbox_root / "policies" / "never-auto-send.yaml").write_text("send: false\n", encoding="utf-8")
    (inbox_root / "conventions" / "config.yaml").write_text("scan_hours: 2\n", encoding="utf-8")
    (inbox_root / "conventions" / "defaults.yaml").write_text("scan_hours: 24\n", encoding="utf-8")
    (outbox_root / "previews" / "draft-reply.md").write_text("Preview body", encoding="utf-8")
    (outbox_root / "reports" / "inbox-digest.md").write_text("Digest body", encoding="utf-8")
    (outbox_root / "suggestions" / "notify-slack.json").write_text('{"target_app":"slack-triage"}', encoding="utf-8")
    (outbox_root / "runs" / "run-demo" / "run.json").write_text(
        json.dumps(
            {
                "run_id": "run-demo",
                "trigger": "manual",
                "actions_summary": "12 reads, 2 drafts",
                "cost_usd": 0.003,
                "state": "DONE",
                "created_at": "2026-03-01T14:30:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    (home / "settings.json").write_text(
        json.dumps(
            {
                "account": {"status": "logged_in", "user": "test@solace.local", "tier": "pro"},
                "history": {"enabled": True, "screenshots": False, "pzip_sync": True, "prime_wiki": True, "prime_mermaid": True, "max_gb": 10.0, "exclude_domains": ["localhost"]},
                "llm": {"backend": "claude_code", "model": "claude-sonnet", "endpoint": "http://localhost:8080", "byok_key": ""},
                "tunnel": {"enabled": False, "provider": "cloudflare", "public_url": "Not connected", "approval": "required"},
                "part11": {"enabled": True, "mode": "data", "esigning": True, "chain_entries": 5},
                "privacy": {"history_local_only": True, "vault_encrypted": True, "cloud_sync_optional": True},
                "yinyang": {"top_rail": True, "bottom_rail": True, "max_transcript": 24, "session_ttl_min": 30},
                "about": {"version": "0.5.0-dev", "build": "source", "web_ui_port": 8791},
            }
        ),
        encoding="utf-8",
    )
    return home


@pytest.fixture()
def running_server(solace_home: Path) -> str:
    server_module = _load_server_module()
    port = _find_free_port()
    server = server_module.create_server(
        "127.0.0.1",
        port,
        data_store=server_module.SolaceDataStore(solace_home=solace_home),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_get_apps_reads_installed_manifests(running_server: str) -> None:
    status, payload = _request_json(f"{running_server}/api/apps")
    assert status == 200
    assert payload["apps"][0]["id"] == "gmail-inbox-triage"
    assert payload["apps"][0]["status"] == "installed"


def test_get_app_detail_includes_inbox_outbox_and_runs(running_server: str) -> None:
    status, payload = _request_json(f"{running_server}/api/apps/gmail-inbox-triage")
    assert status == 200
    assert payload["id"] == "gmail-inbox-triage"
    assert payload["inbox"]["prompts"][0]["name"] == "triage-rules.md"
    assert payload["outbox"]["previews"][0]["name"] == "draft-reply.md"
    assert payload["recent_runs"][0]["run_id"] == "run-demo"


def test_get_missing_app_returns_404(running_server: str) -> None:
    status, payload = _request_json(f"{running_server}/api/apps/missing-app")
    assert status == 404
    assert payload["error"] == "App not found"


def test_inbox_and_outbox_endpoints_return_typed_listings(running_server: str) -> None:
    inbox_status, inbox_payload = _request_json(f"{running_server}/api/apps/gmail-inbox-triage/inbox")
    outbox_status, outbox_payload = _request_json(f"{running_server}/api/apps/gmail-inbox-triage/outbox")
    assert inbox_status == 200
    assert outbox_status == 200
    assert "templates" in inbox_payload
    assert "runs" in outbox_payload


def test_settings_round_trip_persists_changes(running_server: str) -> None:
    get_status, original = _request_json(f"{running_server}/api/settings")
    assert get_status == 200
    updated = dict(original)
    updated["history"] = dict(original["history"])
    updated["history"]["screenshots"] = True
    put_status, put_payload = _request_json(
        f"{running_server}/api/settings",
        method="PUT",
        payload=updated,
    )
    assert put_status == 200
    assert put_payload["history"]["screenshots"] is True

    second_status, second = _request_json(f"{running_server}/api/settings")
    assert second_status == 200
    assert second["history"]["screenshots"] is True


def test_yinyang_data_assets_are_served(running_server: str) -> None:
    status, payload = _request_json(f"{running_server}/data/default/yinyang/jokes.json")
    assert status == 200
    assert "jokes" in payload
