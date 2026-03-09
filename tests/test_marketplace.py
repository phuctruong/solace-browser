"""Marketplace API tests for Yinyang Server."""
import json
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
    import yinyang_server as ys

    calls: list[str] = []

    def fake_urlopen(url, timeout=5):
        calls.append(url)
        if str(url).endswith("/session-rules.yaml"):
            return FakeResponse(200, "name: WhatsApp Web\nurl: https://web.whatsapp.com\n")
        return FakeResponse(200, _catalog_payload([
            {
                "app_id": "whatsapp-web",
                "display_name": "WhatsApp Web",
                "description": "Messaging in the browser",
                "category": "messaging",
                "tier_required": "free",
                "version": "1.0.0",
                "icon_url": "https://solaceagi.com/icons/whatsapp-web.png",
            }
        ]))

    monkeypatch.setattr(ys, "_marketplace_urlopen", fake_urlopen, raising=False)

    status, data = _request_json(
        marketplace_server,
        "/api/v1/marketplace/install",
        method="POST",
        payload={"app_id": "whatsapp-web"},
    )

    installed_path = marketplace_server["apps_root"] / "whatsapp-web" / "session-rules.yaml"
    assert status == 200
    assert data["status"] == "installed"
    assert data["path"] == "data/default/apps/whatsapp-web/"
    assert installed_path.exists()
    assert any(str(call).endswith("/session-rules.yaml") for call in calls)


def test_marketplace_uninstall_removes_file(marketplace_server, monkeypatch):
    import yinyang_server as ys

    def fake_urlopen(url, timeout=5):
        if str(url).endswith("/session-rules.yaml"):
            return FakeResponse(200, "name: Telegram Web\nurl: https://web.telegram.org\n")
        return FakeResponse(200, _catalog_payload([
            {
                "app_id": "telegram-web",
                "display_name": "Telegram Web",
                "description": "Messaging in the browser",
                "category": "messaging",
                "tier_required": "free",
                "version": "1.0.0",
                "icon_url": "https://solaceagi.com/icons/telegram-web.png",
            }
        ]))

    monkeypatch.setattr(ys, "_marketplace_urlopen", fake_urlopen, raising=False)

    app_dir = marketplace_server["apps_root"] / "telegram-web"
    app_dir.mkdir(parents=True, exist_ok=True)
    extra_file = app_dir / "notes.txt"
    extra_file.write_text("keep me")

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
    assert not (app_dir / "session-rules.yaml").exists()
    assert extra_file.exists()


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
