from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from inbox_outbox import InboxOutboxManager, InboxOutboxValidationError


def _make_app(apps_root: Path, *, include_diagrams: bool = True) -> Path:
    app_root = apps_root / "gmail-inbox-triage"
    inbox_root = app_root / "inbox"
    outbox_root = app_root / "outbox"
    for path in [
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
        outbox_root / "runs",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    if include_diagrams:
        diagrams_root = app_root / "diagrams"
        diagrams_root.mkdir(parents=True, exist_ok=True)
        for name in ["workflow.md", "data-flow.md", "partner-contracts.md"]:
            (diagrams_root / name).write_text("```mermaid\nflowchart TD\nA-->B\n```\n", encoding="utf-8")

    manifest = {
        "id": "gmail-inbox-triage",
        "name": "Gmail Inbox Triage",
        "required_inbox": {
            "prompts": ["triage-rules.md"],
            "templates": [],
            "assets": [],
            "policies": ["never-auto-send.yaml"],
            "datasets": [],
            "requests": [],
            "conventions": {"config": "config.yaml", "defaults": "defaults.yaml"},
        },
    }
    (app_root / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    (app_root / "recipe.json").write_text(json.dumps({"steps": []}), encoding="utf-8")
    (app_root / "budget.json").write_text(json.dumps({"remaining_runs": 3}), encoding="utf-8")
    (inbox_root / "prompts" / "triage-rules.md").write_text("Rule 1", encoding="utf-8")
    (inbox_root / "policies" / "never-auto-send.yaml").write_text("send: false\n", encoding="utf-8")
    (inbox_root / "conventions" / "config.yaml").write_text("scan_hours: 2\n", encoding="utf-8")
    (inbox_root / "conventions" / "defaults.yaml").write_text("scan_hours: 24\n", encoding="utf-8")
    (outbox_root / "reports" / "digest.md").write_text("Digest", encoding="utf-8")
    return app_root


def test_list_inbox_groups_files_by_type(tmp_path: Path) -> None:
    apps_root = tmp_path / "apps"
    _make_app(apps_root)
    manager = InboxOutboxManager(apps_root=apps_root)

    listing = manager.list_inbox("gmail-inbox-triage")

    assert listing["prompts"][0]["name"] == "triage-rules.md"
    assert listing["policies"][0]["status"] == "loaded"


def test_list_outbox_groups_files_by_type(tmp_path: Path) -> None:
    apps_root = tmp_path / "apps"
    _make_app(apps_root)
    manager = InboxOutboxManager(apps_root=apps_root)

    listing = manager.list_outbox("gmail-inbox-triage")

    assert listing["reports"][0]["name"] == "digest.md"


def test_read_file_returns_content_and_sha256(tmp_path: Path) -> None:
    apps_root = tmp_path / "apps"
    app_root = _make_app(apps_root)
    manager = InboxOutboxManager(apps_root=apps_root)
    target = app_root / "inbox" / "prompts" / "triage-rules.md"

    payload = manager.read_file("gmail-inbox-triage", "inbox/prompts/triage-rules.md")

    assert payload["content"] == "Rule 1"
    assert payload["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()


def test_write_outbox_updates_outbox_manifest(tmp_path: Path) -> None:
    apps_root = tmp_path / "apps"
    _make_app(apps_root)
    manager = InboxOutboxManager(apps_root=apps_root)

    written = manager.write_outbox("gmail-inbox-triage", "suggestions", "notify-slack.json", '{"target_app":"slack-triage"}')

    assert written["relative_path"] == "outbox/suggestions/notify-slack.json"
    manifest_path = apps_root / "gmail-inbox-triage" / "outbox" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "outbox/suggestions/notify-slack.json" in manifest["entries"]


def test_validate_inbox_requires_diagrams(tmp_path: Path) -> None:
    apps_root = tmp_path / "apps"
    _make_app(apps_root, include_diagrams=False)
    manager = InboxOutboxManager(apps_root=apps_root)

    with pytest.raises(InboxOutboxValidationError):
        manager.validate_inbox("gmail-inbox-triage")


def test_validate_inbox_passes_for_complete_app(tmp_path: Path) -> None:
    apps_root = tmp_path / "apps"
    _make_app(apps_root, include_diagrams=True)
    manager = InboxOutboxManager(apps_root=apps_root)

    result = manager.validate_inbox("gmail-inbox-triage")

    assert result["valid"] is True
