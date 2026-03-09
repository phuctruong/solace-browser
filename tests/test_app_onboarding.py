"""tests/test_app_onboarding.py — App Onboarding 4-State Lifecycle acceptance gate."""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
VALID_TOKEN = "a" * 64


def _req(base, path, method="GET", payload=None):
    url = base + path
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {VALID_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


@pytest.fixture
def onboard_server(tmp_path, monkeypatch):
    import yinyang_server as ys

    for attr in ["EVIDENCE_PATH", "PORT_LOCK_PATH", "SETTINGS_PATH"]:
        monkeypatch.setattr(ys, attr, tmp_path / f"{attr.lower()}.json", raising=False)
    httpd = ys.build_server(0, str(tmp_path), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://localhost:{httpd.server_port}"
    for _ in range(30):
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)
    yield base
    httpd.shutdown()


def test_lifecycle_returns_state_for_all_apps(onboard_server):
    status, data = _req(onboard_server, "/api/v1/apps/lifecycle")
    assert status == 200
    assert "apps" in data
    for app in data["apps"]:
        assert "app_id" in app
        assert "state" in app
        assert app["state"] in ("installed", "setup", "activated", "running")


def test_activate_requires_auth(onboard_server):
    req = urllib.request.Request(
        onboard_server + "/api/v1/apps/gmail/activate",
        data=b"{}",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        assert False, "Expected 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401


def test_activate_returns_activated_state(onboard_server, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pathlib.Path.home", lambda: tmp_path, raising=False
    )
    status, data = _req(
        onboard_server,
        "/api/v1/apps/gmail/activate",
        method="POST",
        payload={"config": {}},
    )
    assert status == 200
    assert data.get("activated") is True
    assert data.get("state") == "activated"


def test_deactivate_resets_to_installed(onboard_server, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pathlib.Path.home", lambda: tmp_path, raising=False
    )
    # First activate
    _req(
        onboard_server,
        "/api/v1/apps/gmail-test/activate",
        method="POST",
        payload={"config": {}},
    )
    # Then deactivate
    status, data = _req(
        onboard_server, "/api/v1/apps/gmail-test/activate", method="DELETE"
    )
    assert status == 200
    assert data.get("deactivated") is True
    assert data.get("state") == "installed"


def test_setup_requirements_has_config_fields(onboard_server):
    status, data = _req(onboard_server, "/api/v1/apps/gmail/setup-requirements")
    assert status == 200
    assert "app_id" in data
    assert "fields" in data
    assert isinstance(data["fields"], list)


def test_apps_css_no_hardcoded_hex():
    css = (PROJECT_ROOT / "web" / "css" / "apps.css").read_text()
    assert "var(--hub-" in css


def test_apps_html_no_cdn():
    html = (PROJECT_ROOT / "web" / "apps.html").read_text()
    assert "cdn.jsdelivr" not in html
    assert "bootstrap" not in html.lower()


def test_state_classes_are_4_valid_values():
    js = (PROJECT_ROOT / "web" / "js" / "apps.js").read_text()
    for state in ["installed", "setup", "activated", "running"]:
        assert f"app-state--{state}" in js


def test_setup_banner_shows_when_apps_not_activated():
    html = (PROJECT_ROOT / "web" / "apps.html").read_text()
    assert "setup-banner" in html
    assert "setup-count" in html


def test_lifecycle_requires_auth(onboard_server):
    req = urllib.request.Request(onboard_server + "/api/v1/apps/lifecycle")
    try:
        urllib.request.urlopen(req, timeout=5)
        assert False, "Expected 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401
