import hashlib
import json
import pathlib
import sys
from io import BytesIO

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys


VALID_TOKEN = "e" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method="GET", path="/", body=None, auth=True):
        self.command = method
        self.path = path
        raw_body = json.dumps(body).encode("utf-8") if body is not None else b""
        self.headers = {
            "Content-Length": str(len(raw_body)),
            "Authorization": f"Bearer {VALID_TOKEN}" if auth else "",
        }
        self.rfile = BytesIO(raw_body)
        self.wfile = BytesIO()
        self.server = type("Server", (), {"session_token_sha256": VALID_TOKEN})()
        self._response_code = None
        self._response_body = None

    def send_response(self, code):
        self._response_code = code

    def send_header(self, *_args):
        pass

    def end_headers(self):
        pass

    def _send_json(self, data, status=200):
        self._response_code = status
        self._response_body = data

    def log_message(self, *_args):
        pass


def setup_function():
    with ys._UAT_LOCK:
        ys._UAT_SNAPSHOTS.clear()


def test_snapshot_create():
    h = FakeHandler()
    h._handle_user_agent_create({
        "user_agent": "Mozilla/5.0 Test",
        "platform": "Linux",
        "browser": "Firefox",
        "is_mobile": False,
        "is_spoofed": False,
    })
    assert h._response_code == 201
    assert h._response_body["snapshot_id"].startswith("uat_")


def test_snapshot_ua_hashed():
    user_agent = "Mozilla/5.0 (X11; Linux x86_64)"
    h = FakeHandler()
    h._handle_user_agent_create({
        "user_agent": user_agent,
        "platform": "Linux",
        "browser": "Chrome",
        "is_mobile": False,
        "is_spoofed": False,
    })
    assert h._response_body["ua_hash"] == hashlib.sha256(user_agent.encode("utf-8")).hexdigest()
    assert "user_agent" not in h._response_body


def test_snapshot_invalid_platform():
    h = FakeHandler()
    h._handle_user_agent_create({
        "user_agent": "Mozilla/5.0 Test",
        "platform": "BeOS",
        "browser": "Chrome",
        "is_mobile": False,
        "is_spoofed": False,
    })
    assert h._response_code == 400
    assert "platform" in h._response_body["error"]


def test_snapshot_invalid_browser():
    h = FakeHandler()
    h._handle_user_agent_create({
        "user_agent": "Mozilla/5.0 Test",
        "platform": "Windows",
        "browser": "Netscape",
        "is_mobile": False,
        "is_spoofed": False,
    })
    assert h._response_code == 400
    assert "browser" in h._response_body["error"]


def test_snapshot_spoofed_flag():
    h = FakeHandler()
    h._handle_user_agent_create({
        "user_agent": "Mozilla/5.0 Test",
        "platform": "Android",
        "browser": "Brave",
        "is_mobile": True,
        "is_spoofed": True,
    })
    assert h._response_code == 201
    assert h._response_body["is_spoofed"] is True


def test_snapshot_list_route():
    creator = FakeHandler(method="POST", path="/api/v1/user-agent/snapshots", body={
        "user_agent": "Mozilla/5.0 Test",
        "platform": "macOS",
        "browser": "Safari",
        "is_mobile": False,
        "is_spoofed": False,
    })
    creator.do_POST()
    reader = FakeHandler(method="GET", path="/api/v1/user-agent/snapshots")
    reader.do_GET()
    assert reader._response_code == 200
    assert reader._response_body["total"] == 1


def test_snapshot_delete_route():
    creator = FakeHandler()
    creator._handle_user_agent_create({
        "user_agent": "Mozilla/5.0 Delete",
        "platform": "iOS",
        "browser": "Safari",
        "is_mobile": True,
        "is_spoofed": False,
    })
    snapshot_id = creator._response_body["snapshot_id"]
    deleter = FakeHandler(method="DELETE", path=f"/api/v1/user-agent/snapshots/{snapshot_id}")
    deleter.do_DELETE()
    assert deleter._response_code == 200
    assert deleter._response_body["snapshot_id"] == snapshot_id


def test_snapshot_not_found():
    h = FakeHandler()
    h._handle_user_agent_delete("uat_missing")
    assert h._response_code == 404


def test_ua_stats():
    first = FakeHandler()
    first._handle_user_agent_create({
        "user_agent": "Mozilla/5.0 One",
        "platform": "Linux",
        "browser": "Firefox",
        "is_mobile": False,
        "is_spoofed": False,
    })
    second = FakeHandler()
    second._handle_user_agent_create({
        "user_agent": "Mozilla/5.0 Two",
        "platform": "Android",
        "browser": "Chrome",
        "is_mobile": True,
        "is_spoofed": True,
    })
    stats = FakeHandler(method="GET", path="/api/v1/user-agent/stats")
    stats.do_GET()
    assert stats._response_code == 200
    assert stats._response_body["spoofed_count"] == 1
    assert stats._response_body["mobile_count"] == 1


def test_banned_debug_port_absent_in_user_agent_files():
    banned = "922" + "2"
    for rel_path in [
        "yinyang_server.py",
        "web/user-agent-tracker.html",
        "web/css/user-agent-tracker.css",
        "web/js/user-agent-tracker.js",
    ]:
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert banned not in content
