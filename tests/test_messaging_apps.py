import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest
import yaml


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18888
BASE_URL = f"http://localhost:{TEST_PORT}"
AUTH_HASH = "a" * 64
APP_IDS = [
    "whatsapp-web",
    "whatsapp-unread",
    "slack-web",
    "slack-dm",
    "discord-web",
    "discord-notifications",
    "facebook-messenger",
    "messenger-unread",
    "telegram-web",
    "telegram-unread",
]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("messaging-apps")
    lock_path = tmp / "port.lock"

    import yinyang_server as ys

    original_lock = ys.PORT_LOCK_PATH
    ys.PORT_LOCK_PATH = lock_path
    ys.write_port_lock(TEST_PORT, AUTH_HASH, 99999)

    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256=AUTH_HASH)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            urllib.request.urlopen(f"{BASE_URL}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {"httpd": httpd, "lock_path": lock_path}

    httpd.shutdown()
    ys.PORT_LOCK_PATH = original_lock


def _get_json(path: str, include_auth: bool = True) -> tuple[int, dict]:
    headers = {}
    if include_auth:
        headers["Authorization"] = f"Bearer {AUTH_HASH}"
    request = urllib.request.Request(f"{BASE_URL}{path}", headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode())


def test_all_10_session_rules_load():
    for app_id in APP_IDS:
        session_rules_path = REPO_ROOT / "data" / "default" / "apps" / app_id / "session-rules.yaml"
        assert session_rules_path.exists(), f"missing session rules for {app_id}"
        data = yaml.safe_load(session_rules_path.read_text())
        assert data["app"] == app_id
        assert data["site"]


def test_all_10_manifest_exist():
    for app_id in APP_IDS:
        manifest_path = REPO_ROOT / "data" / "default" / "apps" / app_id / "manifest.yaml"
        assert manifest_path.exists(), f"missing manifest for {app_id}"


def test_domain_lookup_whatsapp(server):
    status, data = _get_json("/api/v1/apps/by-domain?domain=web.whatsapp.com")
    assert status == 200
    assert data["domain"] == "web.whatsapp.com"
    assert data["total"] == 2
    assert [app["app_id"] for app in data["apps"]] == ["whatsapp-unread", "whatsapp-web"]


def test_domain_lookup_slack(server):
    status, data = _get_json("/api/v1/apps/by-domain?domain=app.slack.com")
    assert status == 200
    assert data["domain"] == "app.slack.com"
    assert data["total"] == 3
    assert [app["app_id"] for app in data["apps"]] == ["slack-dm", "slack-triage", "slack-web"]


def test_domain_lookup_discord(server):
    status, data = _get_json("/api/v1/apps/by-domain?domain=discord.com")
    assert status == 200
    assert data["domain"] == "discord.com"
    assert data["total"] == 2
    assert [app["app_id"] for app in data["apps"]] == ["discord-notifications", "discord-web"]


def test_domain_lookup_no_match(server):
    status, data = _get_json("/api/v1/apps/by-domain?domain=github.com")
    assert status == 200
    assert data["domain"] == "github.com"
    assert data["total"] == 0
    assert data["apps"] == []


def test_domain_lookup_requires_auth(server):
    request = urllib.request.Request(
        f"{BASE_URL}/api/v1/apps/by-domain?domain=web.whatsapp.com",
        method="GET",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(request, timeout=5)
    assert exc_info.value.code == 401


def test_official_store_includes_messaging_apps():
    store_path = REPO_ROOT / "data" / "default" / "app-store" / "official-store.json"
    store = json.loads(store_path.read_text())
    app_ids = {entry["id"] for entry in store["apps"]}
    assert set(APP_IDS).issubset(app_ids)

