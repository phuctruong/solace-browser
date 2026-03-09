"""Agent notification SSE tests for Yinyang Server."""

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

TEST_PORT = 18895  # unique port — 18888 is used by test_messaging_apps, test_cloud_twin_docker, test_hub_tunnel_client
BASE_URL = f"http://localhost:{TEST_PORT}"
VALID_TOKEN = "c" * 64


@pytest.fixture()
def yinyang_sse_server():
    import yinyang_server as ys

    ys._YINYANG_NOTIFICATIONS = []
    ys._YINYANG_SSE_CLIENTS = []
    ys._YINYANG_NOTIF_COUNTER = 0

    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            urllib.request.urlopen(f"{BASE_URL}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {"httpd": httpd, "module": ys}

    httpd.shutdown()
    httpd.server_close()
    ys._YINYANG_NOTIFICATIONS = []
    ys._YINYANG_SSE_CLIENTS = []
    ys._YINYANG_NOTIF_COUNTER = 0


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {VALID_TOKEN}",
        "Content-Type": "application/json",
    }


def _post_json(path: str, payload: dict, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    request_headers = headers or {"Content-Type": "application/json"}
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode(),
        headers=request_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _get_json(path: str, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def test_notify_post_queues_notification(yinyang_sse_server):
    status, data = _post_json(
        "/api/yinyang/notify",
        {"type": "task_complete", "message": "Done"},
        headers=_auth_headers(),
    )

    assert status == 200
    assert data["status"] == "queued"
    assert data["notification_id"].startswith("notif_")
    assert data["queued_at"].endswith("Z")


def test_notify_requires_auth(yinyang_sse_server):
    status, data = _post_json("/api/yinyang/notify", {"type": "task_complete", "message": "Done"})
    assert status == 401
    assert data["error"] == "unauthorized"


def test_notify_requires_type(yinyang_sse_server):
    status, data = _post_json("/api/yinyang/notify", {"message": "Done"}, headers=_auth_headers())
    assert status == 400
    assert data["error"] == "type required"


def test_notify_requires_message(yinyang_sse_server):
    status, data = _post_json("/api/yinyang/notify", {"type": "task_complete"}, headers=_auth_headers())
    assert status == 400
    assert data["error"] == "message required"


def test_yinyang_status_shows_queue(yinyang_sse_server):
    post_status, _ = _post_json(
        "/api/yinyang/notify",
        {"type": "task_complete", "message": "Ready"},
        headers=_auth_headers(),
    )
    assert post_status == 200

    status, data = _get_json("/api/yinyang/status", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert status == 200
    assert data["queue_depth"] == 1
    assert data["unread_count"] == 1
    assert len(data["notifications"]) == 1
    assert data["notifications"][0]["message"] == "Ready"
    assert data["last_checked"].endswith("Z")


def test_yinyang_status_requires_auth(yinyang_sse_server):
    status, data = _get_json("/api/yinyang/status")
    assert status == 401
    assert data["error"] == "unauthorized"


def test_mark_read_updates_read_flag(yinyang_sse_server):
    status, created = _post_json(
        "/api/yinyang/notify",
        {"type": "task_complete", "message": "Review this"},
        headers=_auth_headers(),
    )
    assert status == 200

    status, marked = _post_json(
        f"/api/yinyang/notifications/{created['notification_id']}/read",
        {},
        headers=_auth_headers(),
    )
    assert status == 200
    assert marked == {"status": "marked_read", "id": created["notification_id"]}

    status, data = _get_json("/api/yinyang/status", headers={"Authorization": f"Bearer {VALID_TOKEN}"})
    assert status == 200
    assert data["unread_count"] == 0
    assert data["notifications"][0]["read"] is True


def test_mark_nonexistent_read_404(yinyang_sse_server):
    status, data = _post_json(
        "/api/yinyang/notifications/notif_zzz/read",
        {},
        headers=_auth_headers(),
    )
    assert status == 404
    assert data["error"] == "notification not found"


def test_sse_endpoint_returns_event_stream(yinyang_sse_server):
    status, _ = _post_json(
        "/api/yinyang/notify",
        {"type": "task_complete", "message": "SSE ready"},
        headers=_auth_headers(),
    )
    assert status == 200

    req = urllib.request.Request(f"{BASE_URL}/api/yinyang/events?token={VALID_TOKEN}", method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        assert resp.headers.get_content_type() == "text/event-stream"
        line_one = resp.readline().decode().strip()
        line_two = resp.readline().decode().strip()
        assert line_one.startswith("id: notif_")
        assert line_two.startswith("data: ")


def test_sse_requires_token_param(yinyang_sse_server):
    req = urllib.request.Request(f"{BASE_URL}/api/yinyang/events", method="GET")
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=5)
    assert exc_info.value.code == 401
    assert json.loads(exc_info.value.read().decode()) == {"error": "unauthorized"}


def test_js_file_exists():
    path = REPO_ROOT / "web" / "js" / "notifications-sse.js"
    assert path.exists()


def test_css_file_exists():
    path = REPO_ROOT / "web" / "css" / "notifications.css"
    assert path.exists()


def test_js_no_cdn():
    path = REPO_ROOT / "web" / "js" / "notifications-sse.js"
    assert "cdn.jsdelivr.net" not in path.read_text()
