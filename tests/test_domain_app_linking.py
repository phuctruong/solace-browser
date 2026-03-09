import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys


def _copy_app(repo_root: Path, app_id: str) -> None:
    source = REPO_ROOT / "data" / "default" / "apps" / app_id
    destination = repo_root / "data" / "default" / "apps" / app_id
    shutil.copytree(source, destination)


def _write_store(repo_root: Path) -> None:
    store_root = repo_root / "data" / "default" / "app-store"
    store_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "data" / "default" / "app-store" / "official-store.json", store_root / "official-store.json")


def _repo_with_apps(tmp_path: Path, *app_ids: str) -> Path:
    repo_root = tmp_path / "repo"
    (repo_root / "data" / "default" / "apps").mkdir(parents=True, exist_ok=True)
    (repo_root / "data" / "custom" / "apps").mkdir(parents=True, exist_ok=True)
    _write_store(repo_root)
    for app_id in app_ids:
        _copy_app(repo_root, app_id)
    return repo_root


def test_by_domain_gmail_returns_gmail_apps(tmp_path):
    repo_root = _repo_with_apps(tmp_path, "gmail-inbox-triage", "gmail-spam-cleaner")

    ys._rebuild_domain_index(str(repo_root))
    data = ys._apps_for_domain(str(repo_root), "mail.google.com", "/mail/u/0/#inbox", "free")

    assert data["domain"] == "mail.google.com"
    assert [app["id"] for app in data["installed_apps"]] == ["gmail-inbox-triage"]
    assert data["installed_apps"][0]["quick_action"] == "Run Triage"
    assert any(app["id"] == "gmail-spam-cleaner" for app in data["store_apps"])


def test_by_domain_free_user_hides_pro_apps(tmp_path):
    repo_root = _repo_with_apps(tmp_path, "slack-web", "slack-dm")

    ys._rebuild_domain_index(str(repo_root))
    data = ys._apps_for_domain(str(repo_root), "app.slack.com", "/client/T123", "free")

    assert [app["id"] for app in data["installed_apps"]] == ["slack-web"]
    locked = next(app for app in data["store_apps"] if app["id"] == "slack-dm")
    assert locked["tier_required"] == "pro"
    assert locked["status"] == "upgrade_required"
    assert locked["install_url"] == ys.MARKETPLACE_UPGRADE_URL


def test_by_domain_unknown_domain_returns_empty(tmp_path):
    repo_root = _repo_with_apps(tmp_path, "gmail-inbox-triage")

    ys._rebuild_domain_index(str(repo_root))
    data = ys._apps_for_domain(str(repo_root), "unknown.example", "/", "free")

    assert data["installed_apps"] == []
    assert data["store_apps"] == []
    assert data["can_create_custom"] is True
    assert data["create_url"].endswith("domain=unknown.example")


def test_rebuild_domain_index_updates_file(tmp_path):
    repo_root = _repo_with_apps(tmp_path, "gmail-inbox-triage", "slack-web")

    result = ys._rebuild_domain_index(str(repo_root))
    index_path = repo_root / "data" / "default" / "apps" / ".domain-index.json"
    payload = json.loads(index_path.read_text())

    assert result["rebuilt"] is True
    assert result["apps_indexed"] == 2
    assert "mail.google.com" in payload["patterns"]
    assert payload["patterns"]["mail.google.com"] == ["gmail-inbox-triage"]


def test_wildcard_domain_matches_subdomain(tmp_path):
    repo_root = _repo_with_apps(tmp_path)
    app_root = repo_root / "data" / "default" / "apps" / "wildcard-helper"
    app_root.mkdir(parents=True, exist_ok=True)
    (app_root / "manifest.yaml").write_text(
        "\n".join([
            "id: wildcard-helper",
            'name: "Wildcard Helper"',
            'description: "Wildcard matcher"',
            'tier: "free"',
            "domains:",
            '  - "*.example.com/app/*"',
            'site: "foo.example.com"',
        ])
    )
    (app_root / "session-rules.yaml").write_text(
        "\n".join([
            "app: wildcard-helper",
            'display_name: "Wildcard Helper"',
            'site: "foo.example.com"',
            'check_url: "https://foo.example.com/app/home"',
            'tier_required: "free"',
        ])
    )

    ys._rebuild_domain_index(str(repo_root))
    data = ys._apps_for_domain(str(repo_root), "team.example.com", "/app/home", "free")

    assert [app["id"] for app in data["installed_apps"]] == ["wildcard-helper"]


def test_custom_app_create_scaffolds_manifest(tmp_path):
    repo_root = _repo_with_apps(tmp_path)

    payload = ys._create_custom_app_scaffold(
        str(repo_root),
        "portal.example.com",
        "Portal Co-Pilot",
        "Custom helper for portal.example.com",
    )

    manifest_path = repo_root / payload["manifest_path"]
    session_rules_path = repo_root / payload["session_rules_path"]
    manifest = yaml.safe_load(manifest_path.read_text())

    assert payload["app_id"] == "portal-co-pilot"
    assert manifest_path.exists()
    assert session_rules_path.exists()
    assert manifest["domains"] == ["portal.example.com"]
    assert "portal.example.com" in session_rules_path.read_text()


def test_by_domain_requires_auth():
    class FakeHandler:
        def __init__(self):
            self.headers = {}
            self.server = type("Server", (), {"session_token_sha256": "a" * 64})()
            self.sent = None

        def _send_json(self, data, status=200):
            self.sent = (status, data)

    handler = FakeHandler()

    assert ys.YinyangHandler._check_auth(handler) is False
    assert handler.sent == (401, {"error": "unauthorized"})


def test_by_domain_includes_store_apps(tmp_path):
    repo_root = _repo_with_apps(tmp_path, "gmail-inbox-triage", "gmail-spam-cleaner")

    ys._rebuild_domain_index(str(repo_root))
    data = ys._apps_for_domain(str(repo_root), "mail.google.com", "/mail/u/0/#inbox", "free")
    store_app = next(app for app in data["store_apps"] if app["id"] == "gmail-spam-cleaner")

    assert store_app["status"] == "upgrade_required"
    assert store_app["tier_required"] == "starter"

