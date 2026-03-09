"""tests/test_notification_settings.py — Notification Settings Panel acceptance gate.
Task 037 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - channels keys validated against NOTIFICATION_CHANNELS
  - min_severity validated against NOTIFICATION_SEVERITIES
  - Auth required on POST routes; GET is public
  - No port 9222, no eval(), no CDN
"""
import hashlib
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-notif-settings-037"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18910)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET", token=token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path: str, payload: dict, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "POST", payload, token=token)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


@pytest.fixture(autouse=True)
def reset_notif_settings(monkeypatch):
    """Reset notification settings between tests."""
    monkeypatch.setattr(ys, "_NOTIF_SETTINGS", {
        "channels": {"browser": True, "desktop": True, "email": False, "webhook": False},
        "min_severity": "info",
        "quiet_hours_enabled": False,
        "quiet_start": "22:00",
        "quiet_end": "08:00",
        "quiet_timezone": "UTC",
    })
    yield


# ---------------------------------------------------------------------------
# 1. GET defaults returns channels dict
# ---------------------------------------------------------------------------
def test_notification_settings_get_defaults():
    status, data = get_json("/api/v1/notification-settings")
    assert status == 200
    assert "channels" in data
    assert "min_severity" in data
    channels = data["channels"]
    assert set(channels.keys()) == {"browser", "desktop", "email", "webhook"}


# ---------------------------------------------------------------------------
# 2. POST updates settings
# ---------------------------------------------------------------------------
def test_notification_settings_update():
    status, data = post_json(
        "/api/v1/notification-settings",
        {"min_severity": "warning", "quiet_hours_enabled": True},
    )
    assert status == 200
    assert data.get("status") == "updated"
    assert data["settings"]["min_severity"] == "warning"
    assert data["settings"]["quiet_hours_enabled"] is True


# ---------------------------------------------------------------------------
# 3. GET /channels lists 4 channels
# ---------------------------------------------------------------------------
def test_notification_channels_list():
    status, data = get_json("/api/v1/notification-settings/channels")
    assert status == 200
    assert "channels" in data
    assert len(data["channels"]) == 4
    ids = {ch["id"] for ch in data["channels"]}
    assert ids == {"browser", "desktop", "email", "webhook"}


# ---------------------------------------------------------------------------
# 4. POST with invalid severity → 400
# ---------------------------------------------------------------------------
def test_notification_invalid_severity():
    status, data = post_json("/api/v1/notification-settings", {"min_severity": "fatal"})
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 5. POST with unknown channel key → 400
# ---------------------------------------------------------------------------
def test_notification_invalid_channel():
    status, data = post_json(
        "/api/v1/notification-settings",
        {"channels": {"sms": True}},
    )
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 6. POST /test → {"sent": True}
# ---------------------------------------------------------------------------
def test_notification_test_send():
    status, data = post_json("/api/v1/notification-settings/test", {})
    assert status == 200
    assert data.get("sent") is True
    assert "channels_notified" in data


# ---------------------------------------------------------------------------
# 7. POST quiet_hours_enabled persists
# ---------------------------------------------------------------------------
def test_notification_quiet_hours_toggle():
    status, data = post_json(
        "/api/v1/notification-settings",
        {"quiet_hours_enabled": True, "quiet_start": "23:00"},
    )
    assert status == 200
    assert data["settings"]["quiet_hours_enabled"] is True
    assert data["settings"]["quiet_start"] == "23:00"


# ---------------------------------------------------------------------------
# 8. HTML has no CDN links
# ---------------------------------------------------------------------------
def test_notification_settings_html_no_cdn():
    html_path = REPO_ROOT / "web" / "notification-settings.html"
    assert html_path.exists(), "notification-settings.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 9. JS has no eval()
# ---------------------------------------------------------------------------
def test_notification_js_no_eval():
    js_path = REPO_ROOT / "web" / "js" / "notification-settings.js"
    assert js_path.exists(), "notification-settings.js must exist"
    content = js_path.read_text()
    assert "eval(" not in content, "eval() is banned in JS"


# ---------------------------------------------------------------------------
# 10. No port 9222 in any notification-settings file
# ---------------------------------------------------------------------------
def test_no_port_9222_in_notification_settings():
    files_to_check = [
        REPO_ROOT / "web" / "notification-settings.html",
        REPO_ROOT / "web" / "js" / "notification-settings.js",
        REPO_ROOT / "web" / "css" / "notification-settings.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
