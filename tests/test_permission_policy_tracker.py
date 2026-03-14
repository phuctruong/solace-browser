# Diagram: 05-solace-runtime-architecture
import hashlib
import json
import pathlib
import sys
from io import BytesIO

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys


VALID_TOKEN = "b" * 64


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
    with ys._PPE_POLICY_LOCK:
        ys._PPE_POLICY_EVENTS.clear()


def test_event_create():
    h = FakeHandler()
    h._handle_permission_policy_create({
        "policy_type": "camera",
        "action": "allow",
        "url": "https://ex.com",
        "origin": "https://ex.com",
        "is_violation": False,
    })
    assert h._response_code == 201
    assert h._response_body["event_id"].startswith("ppe_")


def test_event_url_hashed():
    url = "https://example.com/camera"
    origin = "https://example.com"
    h = FakeHandler()
    h._handle_permission_policy_create({
        "policy_type": "microphone",
        "action": "deny",
        "url": url,
        "origin": origin,
        "is_violation": False,
    })
    assert h._response_body["url_hash"] == hashlib.sha256(url.encode("utf-8")).hexdigest()
    assert h._response_body["origin_hash"] == hashlib.sha256(origin.encode("utf-8")).hexdigest()
    assert "url" not in h._response_body
    assert "origin" not in h._response_body


def test_event_invalid_type():
    h = FakeHandler()
    h._handle_permission_policy_create({
        "policy_type": "bad",
        "action": "allow",
        "url": "https://ex.com",
        "origin": "https://ex.com",
        "is_violation": False,
    })
    assert h._response_code == 400
    assert "policy_type" in h._response_body["error"]


def test_event_invalid_action():
    h = FakeHandler()
    h._handle_permission_policy_create({
        "policy_type": "camera",
        "action": "bad",
        "url": "https://ex.com",
        "origin": "https://ex.com",
        "is_violation": False,
    })
    assert h._response_code == 400
    assert "action" in h._response_body["error"]


def test_event_violation_flag():
    h = FakeHandler()
    h._handle_permission_policy_create({
        "policy_type": "clipboard-read",
        "action": "violation",
        "url": "https://ex.com",
        "origin": "https://ex.com",
        "is_violation": True,
    })
    assert h._response_code == 201
    assert h._response_body["is_violation"] is True


def test_event_list_route():
    creator = FakeHandler(method="POST", path="/api/v1/permission-policy/events", body={
        "policy_type": "usb",
        "action": "inherit",
        "url": "https://ex.com",
        "origin": "https://ex.com",
        "is_violation": False,
    })
    creator.do_POST()
    reader = FakeHandler(method="GET", path="/api/v1/permission-policy/events")
    reader.do_GET()
    assert reader._response_code == 200
    assert reader._response_body["total"] == 1


def test_event_delete_route():
    creator = FakeHandler()
    creator._handle_permission_policy_create({
        "policy_type": "payment",
        "action": "deny",
        "url": "https://ex.com",
        "origin": "https://ex.com",
        "is_violation": False,
    })
    event_id = creator._response_body["event_id"]
    deleter = FakeHandler(method="DELETE", path=f"/api/v1/permission-policy/events/{event_id}")
    deleter.do_DELETE()
    assert deleter._response_code == 200
    assert deleter._response_body["event_id"] == event_id


def test_event_not_found():
    h = FakeHandler()
    h._handle_permission_policy_delete("ppe_missing")
    assert h._response_code == 404


def test_policy_stats():
    first = FakeHandler()
    first._handle_permission_policy_create({
        "policy_type": "camera",
        "action": "allow",
        "url": "https://one.example",
        "origin": "https://one.example",
        "is_violation": False,
    })
    second = FakeHandler()
    second._handle_permission_policy_create({
        "policy_type": "camera",
        "action": "violation",
        "url": "https://two.example",
        "origin": "https://two.example",
        "is_violation": True,
    })
    stats = FakeHandler(method="GET", path="/api/v1/permission-policy/stats")
    stats.do_GET()
    assert stats._response_code == 200
    assert stats._response_body["violation_rate"] == "0.50"


def test_banned_debug_port_absent_in_policy_files():
    banned = "922" + "2"
    for rel_path in [
        "yinyang_server.py",
        "web/permission-policy-tracker.html",
        "web/css/permission-policy-tracker.css",
        "web/js/permission-policy-tracker.js",
    ]:
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert banned not in content
