# Diagram: 05-solace-runtime-architecture
"""Cloud twin endpoint tests for Yinyang Server."""
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

TEST_PORT = 18890
BASE_URL = f"http://localhost:{TEST_PORT}"
VALID_TOKEN = "b" * 64


@pytest.fixture(scope="module")
def cloud_twin_server(tmp_path_factory):
    """Auth-enabled server with isolated settings and evidence paths."""
    import yinyang_server as ys

    tmp = tmp_path_factory.mktemp("cloud_twin")
    lock_path = tmp / "port.lock"
    settings_path = tmp / "settings.json"
    evidence_path = tmp / "evidence.jsonl"

    original_lock = ys.PORT_LOCK_PATH
    original_settings = ys.SETTINGS_PATH
    original_evidence = ys.EVIDENCE_PATH

    ys.PORT_LOCK_PATH = lock_path
    ys.SETTINGS_PATH = settings_path
    ys.EVIDENCE_PATH = evidence_path

    with ys._SESSIONS_LOCK:
        ys._SESSIONS.clear()

    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            urllib.request.urlopen(f"{BASE_URL}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {"httpd": httpd, "settings_path": settings_path, "evidence_path": evidence_path}

    httpd.shutdown()
    httpd.server_close()
    with ys._SESSIONS_LOCK:
        ys._SESSIONS.clear()
    ys.PORT_LOCK_PATH = original_lock
    ys.SETTINGS_PATH = original_settings
    ys.EVIDENCE_PATH = original_evidence


def _get_auth(path: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _post_auth(path: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {VALID_TOKEN}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def test_cloud_twin_status_not_configured(cloud_twin_server):
    """GET /api/v1/cloud-twin/status → configured=false when no settings exist."""
    status, data = _get_auth("/api/v1/cloud-twin/status")
    assert status == 200
    assert data["configured"] is False
    assert data["url"] == ""
    assert data["reachable"] is False


def test_cloud_twin_set_url(cloud_twin_server):
    """POST /api/v1/cloud-twin/set persists the URL and local-first defaults."""
    status, data = _post_auth(
        "/api/v1/cloud-twin/set",
        {"url": "https://solace-browser-twin.example.run.app"},
    )
    assert status == 200
    assert data == {
        "status": "saved",
        "url": "https://solace-browser-twin.example.run.app",
    }

    saved = json.loads(cloud_twin_server["settings_path"].read_text())
    assert saved["cloud_twin"] == {
        "url": "https://solace-browser-twin.example.run.app",
        "enabled": False,
        "prefer_cloud": False,
        "fallback_to_local": True,
    }


def test_cloud_twin_status_configured(cloud_twin_server):
    """GET /api/v1/cloud-twin/status → configured=true after URL is saved."""
    status, data = _get_auth("/api/v1/cloud-twin/status")
    assert status == 200
    assert data["configured"] is True
    assert data["url"] == "https://solace-browser-twin.example.run.app"
    assert "last_ping_ms" in data


def test_cloud_twin_ping_unreachable(cloud_twin_server):
    """POST /api/v1/cloud-twin/ping → reachable=false for an unreachable URL."""
    status, _ = _post_auth(
        "/api/v1/cloud-twin/set",
        {"url": "https://localhost:1"},
    )
    assert status == 200

    status, data = _post_auth("/api/v1/cloud-twin/ping", {})
    assert status == 200
    assert data["reachable"] is False
    assert data["latency_ms"] is None


def test_session_new_local_target(cloud_twin_server, monkeypatch):
    """POST /api/v1/sessions without target keeps existing local behavior."""
    import os
    import yinyang_server as ys

    class FakeProcess:
        pid = 43210

        def poll(self):
            return None

    monkeypatch.setattr(ys.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setenv("SOLACE_BROWSER", sys.executable)

    status, data = _post_auth(
        "/api/v1/sessions",
        {"url": "http://localhost:8888/start", "profile": "default"},
    )
    assert status == 201
    assert data["pid"] == 43210
    assert "session_id" in data

    with ys._SESSIONS_LOCK:
        ys._SESSIONS.pop(data["session_id"], None)
    os.environ.pop("SOLACE_BROWSER", None)


def test_session_new_cloud_target_no_twin(cloud_twin_server, monkeypatch):
    """POST /api/v1/sessions target=cloud → 503 when no cloud twin is configured."""
    import os
    import yinyang_server as ys

    cloud_twin_server["settings_path"].unlink(missing_ok=True)

    class FakeProcess:
        pid = 54321

        def poll(self):
            return None

    monkeypatch.setattr(ys.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setenv("SOLACE_BROWSER", sys.executable)

    status, data = _post_auth(
        "/api/v1/sessions",
        {"url": "http://localhost:8888/start", "profile": "default", "target": "cloud"},
    )
    assert status == 503
    assert "cloud twin" in data["error"].lower()

    os.environ.pop("SOLACE_BROWSER", None)


def test_deploy_script_exists():
    """scripts/deploy-cloud-twin.sh exists and is executable."""
    script = REPO_ROOT / "scripts" / "deploy-cloud-twin.sh"
    assert script.exists()
    assert script.stat().st_mode & 0o111
