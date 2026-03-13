"""Marketplace API tests for Yinyang Server."""
import json
import os
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

VALID_TOKEN = "a" * 64


class FakeResponse:
    def __init__(self, status: int, body: str):
        self.status = status
        self._body = body.encode()

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def marketplace_server(tmp_path, monkeypatch):
    import yinyang_server as ys

    repo_root = tmp_path / "repo"
    apps_root = repo_root / "data" / "default" / "apps"
    apps_root.mkdir(parents=True)

    cache_path = tmp_path / ".solace" / "marketplace-cache.json"
    settings_path = tmp_path / ".solace" / "settings.json"
    evidence_path = tmp_path / ".solace" / "evidence.jsonl"
    port_lock_path = tmp_path / ".solace" / "port.lock"

    monkeypatch.setattr(ys, "MARKETPLACE_CACHE_PATH", cache_path, raising=False)
    monkeypatch.setattr(ys, "SETTINGS_PATH", settings_path)
    monkeypatch.setattr(ys, "EVIDENCE_PATH", evidence_path)
    monkeypatch.setattr(ys, "PORT_LOCK_PATH", port_lock_path)
    monkeypatch.setenv("SOLACE_LOCAL_APPS_ROOT", str(tmp_path / ".solace" / "apps"))
    monkeypatch.setenv("SOLACE_APP_SOURCE_ROOTS", str(apps_root))

    httpd = ys.build_server(0, str(repo_root), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://localhost:{httpd.server_port}"
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1):
                break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {
        "base_url": base_url,
        "repo_root": repo_root,
        "apps_root": apps_root,
        "cache_path": cache_path,
        "settings_path": settings_path,
    }

    httpd.shutdown()
    thread.join(timeout=2)


def _request_json(server: dict, path: str, method: str = "GET", payload: dict | None = None, token: str | None = VALID_TOKEN) -> tuple[int, dict]:
    headers = {}
    data = None
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{server['base_url']}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _catalog_payload(apps: list[dict]) -> str:
    return json.dumps({"apps": apps, "total": len(apps)})


def test_marketplace_apps_requires_auth(marketplace_server):
    status, data = _request_json(marketplace_server, "/api/v1/marketplace/apps", token=None)
    assert status == 401
    assert data["error"] == "unauthorized"


def test_marketplace_apps_returns_list(marketplace_server, monkeypatch):
    import yinyang_server as ys

    def fake_urlopen(url, timeout=5):
        return FakeResponse(200, _catalog_payload([
            {
                "app_id": "gmail",
                "display_name": "Gmail",
                "description": "Access Gmail via browser session",
                "category": "productivity",
                "tier_required": "free",
                "version": "1.0.0",
                "icon_url": "https://solaceagi.com/icons/gmail.png",
            }
        ]))

    monkeypatch.setattr(ys, "_marketplace_urlopen", fake_urlopen, raising=False)

    status, data = _request_json(marketplace_server, "/api/v1/marketplace/apps")

    assert status == 200
    assert isinstance(data["apps"], list)
    assert data["apps"][0]["app_id"] == "gmail"
    assert data["apps"][0]["installed"] is False


def test_marketplace_install_bad_app_id(marketplace_server, monkeypatch):
    import yinyang_server as ys

    def fake_urlopen(url, timeout=5):
        return FakeResponse(200, _catalog_payload([
            {
                "app_id": "gmail",
                "display_name": "Gmail",
                "description": "Access Gmail via browser session",
                "category": "productivity",
                "tier_required": "free",
                "version": "1.0.0",
                "icon_url": "https://solaceagi.com/icons/gmail.png",
            }
        ]))

    monkeypatch.setattr(ys, "_marketplace_urlopen", fake_urlopen, raising=False)

    status, data = _request_json(
        marketplace_server,
        "/api/v1/marketplace/install",
        method="POST",
        payload={"app_id": "nonexistent"},
    )

    assert status == 404
    assert data["error"] == "app not found"


def test_marketplace_install_downloads_session_rules(marketplace_server, monkeypatch):
    source_dir = marketplace_server["apps_root"] / "whatsapp-web"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "manifest.yaml").write_text(
        "id: whatsapp-web\n"
        "name: WhatsApp Web\n"
        "description: Messaging in the browser\n"
        "category: messaging\n"
        "tier_required: free\n"
        "site: web.whatsapp.com\n"
    )
    (source_dir / "session-rules.yaml").write_text("app: whatsapp-web\nsite: web.whatsapp.com\n")

    status, data = _request_json(
        marketplace_server,
        "/api/v1/marketplace/install",
        method="POST",
        payload={"app_id": "whatsapp-web"},
    )

    installed_path = pathlib.Path(data["path"]) / "session-rules.yaml"
    assert status == 200
    assert data["status"] == "installed"
    assert installed_path.exists()


def test_marketplace_uninstall_removes_file(marketplace_server, monkeypatch):
    source_dir = marketplace_server["apps_root"] / "telegram-web"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "manifest.yaml").write_text(
        "id: telegram-web\n"
        "name: Telegram Web\n"
        "description: Messaging in the browser\n"
        "category: messaging\n"
        "tier_required: free\n"
        "site: web.telegram.org\n"
    )
    (source_dir / "session-rules.yaml").write_text("app: telegram-web\nsite: web.telegram.org\n")

    install_status, _ = _request_json(
        marketplace_server,
        "/api/v1/marketplace/install",
        method="POST",
        payload={"app_id": "telegram-web"},
    )
    assert install_status == 200

    status, data = _request_json(
        marketplace_server,
        "/api/v1/marketplace/uninstall",
        method="POST",
        payload={"app_id": "telegram-web"},
    )

    assert status == 200
    assert data["status"] == "uninstalled"
    local_root = pathlib.Path(os.environ["SOLACE_LOCAL_APPS_ROOT"])
    assert not any(local_root.glob("**/telegram-web/session-rules.yaml"))


def test_marketplace_categories(marketplace_server):
    status, data = _request_json(marketplace_server, "/api/v1/marketplace/categories")
    assert status == 200
    assert isinstance(data["categories"], list)
    assert all(isinstance(item, str) for item in data["categories"])


def test_marketplace_serves_cache_when_offline(marketplace_server, monkeypatch):
    import yinyang_server as ys

    marketplace_server["cache_path"].parent.mkdir(parents=True, exist_ok=True)
    marketplace_server["cache_path"].write_text(_catalog_payload([
        {
            "app_id": "slack-dm",
            "display_name": "Slack DM",
            "description": "Check Slack direct messages",
            "category": "messaging",
            "tier_required": "free",
            "version": "1.0.0",
            "icon_url": "https://solaceagi.com/icons/slack-dm.png",
        }
    ]))

    def offline_urlopen(url, timeout=5):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(ys, "_marketplace_urlopen", offline_urlopen, raising=False)

    status, data = _request_json(marketplace_server, "/api/v1/marketplace/apps")

    assert status == 200
    assert data["source"] == "cache"
    assert data["apps"][0]["app_id"] == "slack-dm"


def test_marketplace_serves_local_bundle_when_remote_unavailable(marketplace_server, monkeypatch):
    import yinyang_server as ys

    app_dir = marketplace_server["apps_root"] / "solace-yinyang"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "manifest.yaml").write_text(
        "id: solace-yinyang\n"
        "name: Solace Yinyang\n"
        "description: Local-first assistant\n"
        "category: solace\n"
        "tier_required: free\n"
        "site: solaceagi.com\n"
    )

    def offline_urlopen(url, timeout=5):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(ys, "_marketplace_urlopen", offline_urlopen, raising=False)

    status, data = _request_json(marketplace_server, "/api/v1/marketplace/apps")

    assert status == 200
    assert data["source"] == "local_bundle"
    assert data["apps"][0]["app_id"] == "solace-yinyang"


def test_app_install_route_by_id_updates_install_state(marketplace_server):
    app_dir = marketplace_server["repo_root"] / "data" / "default" / "apps" / "solace-yinyang"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "manifest.yaml").write_text(
        "id: solace-yinyang\n"
        "name: Solace Yinyang\n"
        "description: Local-first assistant\n"
        "site: solaceagi.com\n"
    )

    status, data = _request_json(
        marketplace_server,
        "/api/v1/apps/solace-yinyang/install",
        method="POST",
        payload={},
    )
    assert status == 200
    assert data["status"] == "installed"

    _request_json(
        marketplace_server,
        "/onboarding/complete",
        method="POST",
        payload={"auth_state": "logged_in", "membership_tier": "free", "model_sources": ["byok"]},
    )

    status, data = _request_json(
        marketplace_server,
        "/api/v1/apps/by-domain?domain=solaceagi.com",
    )
    assert status == 200
    assert any(app["id"] == "solace-yinyang" for app in data["installed_apps"])

    status, data = _request_json(
        marketplace_server,
        "/api/v1/apps/solace-yinyang/install",
        method="DELETE",
        payload={},
    )
    assert status == 200
    assert data["status"] == "uninstalled"
