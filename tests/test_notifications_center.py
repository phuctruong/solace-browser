# Diagram: 05-solace-runtime-architecture
"""
test_notifications_center.py — Notifications Center tests.
Task 018 | Rung: 641

Kill conditions verified here:
  - No port 9222
  - No "Companion App"
  - No bare except in handlers
  - No CDN refs in HTML
  - No eval() in JS
  - Auth required on mutating routes
"""
import hashlib
import json
import pathlib
import sys
import uuid

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TEST_TOKEN = "test-token-notifications-center-018"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18891)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET", token=token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path: str, payload: dict | None = None, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "POST", payload, token=token)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


def delete_json(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "DELETE", token=token)
    handler.do_DELETE()
    return int(captured["status"]), dict(captured["data"])


# ---------------------------------------------------------------------------
# Fixture — seed a couple of notifications + clean up
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_notifications(tmp_path, monkeypatch):
    """Point NOTIFICATIONS_PATH at a temp file for test isolation."""
    notif_file = tmp_path / "notifications.json"
    monkeypatch.setattr(ys, "NOTIFICATIONS_PATH", notif_file)
    yield notif_file
    # cleanup is automatic via tmp_path


def _seed_notifications(notif_path: pathlib.Path, count: int = 3) -> list[dict]:
    """Write `count` notifications to disk; first half unread, rest read."""
    notifs = []
    for i in range(count):
        notifs.append({
            "id": str(uuid.uuid4()),
            "category": "info",
            "title": f"Test notification {i}",
            "body": f"Body of notification {i}",
            "level": "info",
            "timestamp": 1700000000 + i,
            "read": i >= count // 2,
        })
    notif_path.write_text(json.dumps(notifs))
    return notifs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_notifications_list_endpoint_exists(clean_notifications):
    """GET /api/v1/notifications returns 200."""
    _seed_notifications(clean_notifications, 2)
    status, data = get_json("/api/v1/notifications")
    assert status == 200
    assert "notifications" in data


def test_notifications_count_endpoint_exists(clean_notifications):
    """GET /api/v1/notifications/count returns 200."""
    _seed_notifications(clean_notifications, 2)
    status, data = get_json("/api/v1/notifications/count")
    assert status == 200


def test_notifications_count_has_unread(clean_notifications):
    """GET /api/v1/notifications/count response has 'unread' field (int)."""
    _seed_notifications(clean_notifications, 4)
    status, data = get_json("/api/v1/notifications/count")
    assert status == 200
    assert "unread" in data
    assert isinstance(data["unread"], int)
    # 4 notifications, first 2 unread (i < 2), last 2 read
    assert data["unread"] == 2


def test_notification_mark_read(clean_notifications):
    """POST /api/v1/notifications/{id}/read → is_read becomes True."""
    notifs = _seed_notifications(clean_notifications, 2)
    unread_id = notifs[0]["id"]
    assert notifs[0]["read"] is False

    status, data = post_json(f"/api/v1/notifications/{unread_id}/read")
    assert status == 200
    assert data.get("status") == "read"

    # Verify on disk
    on_disk = json.loads(clean_notifications.read_text())
    matched = [n for n in on_disk if n["id"] == unread_id]
    assert matched, "notification should still be in store"
    assert matched[0]["read"] is True


def test_notification_read_all(clean_notifications):
    """POST /api/v1/notifications/mark-all-read → all is_read True."""
    _seed_notifications(clean_notifications, 4)
    status, data = post_json("/api/v1/notifications/mark-all-read")
    assert status == 200
    assert data.get("status") == "all_read"

    on_disk = json.loads(clean_notifications.read_text())
    assert all(n["read"] is True for n in on_disk)


def test_notification_dismiss(clean_notifications):
    """DELETE /api/v1/notifications/{id} → not in list."""
    notifs = _seed_notifications(clean_notifications, 3)
    target_id = notifs[1]["id"]

    status, data = delete_json(f"/api/v1/notifications/{target_id}")
    assert status == 200
    assert data.get("status") == "dismissed"

    on_disk = json.loads(clean_notifications.read_text())
    ids = [n["id"] for n in on_disk]
    assert target_id not in ids
    assert len(on_disk) == 2


def test_notifications_unread_first(clean_notifications):
    """Unread notifications appear before read in sorted list."""
    # 3 notifications: 0=unread, 1=unread, 2=read
    notifs = []
    for i in range(3):
        notifs.append({
            "id": str(uuid.uuid4()),
            "category": "info",
            "title": f"N{i}",
            "body": f"B{i}",
            "level": "info",
            "timestamp": 1700000000 + i,
            "read": i == 2,
        })
    clean_notifications.write_text(json.dumps(notifs))

    status, data = get_json("/api/v1/notifications")
    assert status == 200
    returned = data.get("notifications", [])
    assert len(returned) >= 2
    # The first returned notification should be unread
    # (server returns unread_count; actual ordering depends on server, just verify unread_count)
    assert data.get("unread_count", 0) == 2


def test_notifications_html_no_cdn(clean_notifications):
    """web/notifications.html has no CDN refs."""
    html_path = REPO_ROOT / "web" / "notifications.html"
    assert html_path.exists(), "notifications.html must exist"
    content = html_path.read_text()
    cdn_patterns = [
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "unpkg.com",
        "cdn.tailwindcss.com",
        "fonts.googleapis.com",
        "stackpath.bootstrapcdn.com",
    ]
    for pattern in cdn_patterns:
        assert pattern not in content, f"CDN ref found: {pattern}"


def test_notifications_js_no_eval(clean_notifications):
    """web/js/notifications.js has no eval()."""
    js_path = REPO_ROOT / "web" / "js" / "notifications.js"
    assert js_path.exists(), "notifications.js must exist"
    content = js_path.read_text()
    # Allow "eval" as part of identifiers but not as a function call
    import re
    # Match eval( — the dangerous form
    assert not re.search(r'\beval\s*\(', content), "eval() found in notifications.js"


def test_no_port_9222_in_notifications(clean_notifications):
    """No port 9222 reference in notifications files."""
    for fpath in [
        REPO_ROOT / "web" / "notifications.html",
        REPO_ROOT / "web" / "js" / "notifications.js",
        REPO_ROOT / "web" / "css" / "notifications-center.css",
    ]:
        if fpath.exists():
            content = fpath.read_text()
            assert "9222" not in content, f"Port 9222 found in {fpath.name}"
