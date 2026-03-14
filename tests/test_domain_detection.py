# Diagram: 05-solace-runtime-architecture
import json
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18888
BASE_URL = f"http://localhost:{TEST_PORT}"
VALID_TOKEN = "a" * 64
UPGRADE_URL = "https://solaceagi.com/upgrade"


@pytest.fixture(scope="module")
def domain_server(tmp_path_factory):
    tmp_root = tmp_path_factory.mktemp("domain-detection")
    repo_root = tmp_root / "repo"
    apps_root = repo_root / "data" / "default" / "apps"
    apps_root.mkdir(parents=True, exist_ok=True)

    for app_id in ("whatsapp-web", "whatsapp-unread", "whatsapp-responder"):
        shutil.copytree(REPO_ROOT / "data" / "default" / "apps" / app_id, apps_root / app_id)

    settings_path = tmp_root / "settings.json"

    import yinyang_server as ys

    original_settings_path = ys.SETTINGS_PATH
    ys.SETTINGS_PATH = settings_path

    httpd = ys.build_server(TEST_PORT, str(repo_root), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    for _ in range(40):
        try:
            urllib.request.urlopen(f"{BASE_URL}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {
        "httpd": httpd,
        "repo_root": repo_root,
        "settings_path": settings_path,
    }

    httpd.shutdown()
    httpd.server_close()
    ys.SETTINGS_PATH = original_settings_path


def _request(method: str, path: str, payload: dict | None = None, with_auth: bool = True) -> tuple[int, dict]:
    headers = {}
    if with_auth:
        headers["Authorization"] = f"Bearer {VALID_TOKEN}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode())


def test_domain_apps_whatsapp(domain_server):
    status, data = _request("GET", "/api/v1/apps/by-domain?domain=web.whatsapp.com")
    assert status == 200
    assert data["domain"] == "web.whatsapp.com"
    # store_apps contains tier-gated apps; all whatsapp apps require pro/enterprise
    store_ids = {app["id"] for app in data["store_apps"]}
    assert len(store_ids) >= 2
    assert "whatsapp-web" in store_ids
    assert "whatsapp-unread" in store_ids


def test_domain_apps_requires_auth(domain_server):
    status, data = _request("GET", "/api/v1/apps/by-domain?domain=web.whatsapp.com", with_auth=False)
    assert status == 401
    assert data["error"] == "unauthorized"


def test_user_tier_default_free(domain_server):
    settings_path = domain_server["settings_path"]
    if settings_path.exists():
        settings_path.unlink()
    status, data = _request("GET", "/api/v1/user/tier")
    assert status == 200
    assert data["tier"] == "free"
    assert data["can_sync"] is False
    assert data["can_submit"] is False


def test_user_tier_reads_settings(domain_server):
    domain_server["settings_path"].write_text(json.dumps({"user": {"tier": "pro"}}))
    status, data = _request("GET", "/api/v1/user/tier")
    assert status == 200
    assert data["tier"] == "pro"
    assert data["can_sync"] is True
    assert data["can_submit"] is True


def test_custom_app_create(domain_server):
    status, data = _request(
        "POST",
        "/api/v1/apps/custom/create",
        {
            "domain": "web.whatsapp.com",
            "name": "My WhatsApp Monitor",
            "description": "Custom monitor",
        },
    )
    assert status == 201
    assert data["app_id"] == "my-whatsapp-monitor"
    session_rules_path = domain_server["repo_root"] / data["session_rules_path"]
    assert session_rules_path.exists()
    contents = session_rules_path.read_text()
    assert "web.whatsapp.com" in contents
    assert "my-whatsapp-monitor" in contents

    status, payload = _request("GET", "/api/v1/apps/by-domain?domain=web.whatsapp.com")
    assert status == 200
    installed_ids = {app["id"] for app in payload["installed_apps"]}
    assert "my-whatsapp-monitor" in installed_ids

    status, payload = _request("DELETE", "/api/v1/apps/my-whatsapp-monitor/install")
    assert status == 200
    assert payload["state"] == "available"

    status, payload = _request("GET", "/api/v1/apps/by-domain?domain=web.whatsapp.com")
    assert status == 200
    installed_ids = {app["id"] for app in payload["installed_apps"]}
    store_ids = {app["id"] for app in payload["store_apps"]}
    assert "my-whatsapp-monitor" not in installed_ids
    assert "my-whatsapp-monitor" in store_ids


def test_custom_app_delete_removes_all_local_state(domain_server):
    app_name = f"Transient Custom App {uuid.uuid4().hex[:8]}"
    status, data = _request(
        "POST",
        "/api/v1/apps/custom/create",
        {
            "domain": "web.whatsapp.com",
            "name": app_name,
            "description": "Delete me completely",
        },
    )
    assert status == 201
    app_id = data["app_id"]

    status, payload = _request(
        "POST",
        f"/api/v1/apps/{app_id}/config",
        {
            "objective": "Track messages",
            "target_url": "https://web.whatsapp.com/",
            "cron": "0 7 * * *",
            "keepalive_minutes": 15,
        },
    )
    assert status == 200
    assert payload["status"] == "saved"
    assert payload["config"]["objective"] == "Track messages"

    status, payload = _request(
        "POST",
        "/api/v1/browser/schedules",
        {
            "app_id": app_id,
            "cron": "0 7 * * *",
            "url": "https://web.whatsapp.com/",
        },
    )
    assert status == 201
    schedule_id = payload["id"]

    status, payload = _request("DELETE", f"/api/v1/apps/{app_id}")
    assert status == 200
    assert payload["status"] == "deleted"
    assert payload["app_id"] == app_id
    assert payload["removed_schedules"] == 1

    status, payload = _request("GET", "/api/v1/apps/by-domain?domain=web.whatsapp.com")
    assert status == 200
    installed_ids = {app["id"] for app in payload["installed_apps"]}
    store_ids = {app["id"] for app in payload["store_apps"]}
    assert app_id not in installed_ids
    assert app_id not in store_ids

    status, payload = _request("GET", f"/api/v1/apps/{app_id}/config")
    assert status == 404
    assert payload["error"] == "app not found"

    status, payload = _request("GET", "/api/v1/browser/schedules")
    assert status == 200
    schedule_ids = {schedule["id"] for schedule in payload["schedules"]}
    assert schedule_id not in schedule_ids


def test_custom_app_name_sanitized(domain_server):
    status, data = _request(
        "POST",
        "/api/v1/apps/custom/create",
        {
            "domain": "web.whatsapp.com",
            "name": "../bad-app",
            "description": "No traversal",
        },
    )
    assert status == 400
    assert data["error"] == "invalid app name"


def test_sync_free_user_blocked(domain_server):
    domain_server["settings_path"].write_text(json.dumps({"user": {"tier": "free"}}))
    status, data = _request("POST", "/api/v1/apps/sync", {})
    assert status == 403
    assert data["status"] == "sync_disabled"
    assert data["upgrade_url"] == UPGRADE_URL


def test_sidebar_html_has_domain_panel():
    sidepanel_html = (REPO_ROOT / "solace-hub" / "src" / "sidepanel.html").read_text()
    assert 'id="domain-apps-panel"' in sidepanel_html
    assert 'id="create-custom-app-btn"' in sidepanel_html
    assert 'id="submit-to-store-btn"' in sidepanel_html
