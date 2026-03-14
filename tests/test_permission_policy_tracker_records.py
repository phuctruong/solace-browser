# Diagram: 05-solace-runtime-architecture
"""Tests for Task 164v2 — Permission Policy Tracker /records endpoints."""
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
    with ys._PERMISSION_POLICY_LOCK:
        ys._PERMISSION_POLICY_RECORDS.clear()


def test_record_create():
    h = FakeHandler()
    h._handle_ppt2_create({
        "feature": "camera",
        "url": "https://ex.com",
        "policy_value": "allowed",
        "is_blocked_by_header": False,
    })
    assert h._response_code == 201
    assert h._response_body["record_id"].startswith("ppt_")


def test_record_url_hashed():
    url = "https://example.com/camera"
    h = FakeHandler()
    h._handle_ppt2_create({
        "feature": "microphone",
        "url": url,
        "policy_value": "blocked",
        "is_blocked_by_header": True,
    })
    assert h._response_body["url_hash"] == hashlib.sha256(url.encode("utf-8")).hexdigest()
    assert "url" not in h._response_body


def test_record_invalid_feature():
    h = FakeHandler()
    h._handle_ppt2_create({
        "feature": "laser",
        "url": "https://ex.com",
        "policy_value": "allowed",
        "is_blocked_by_header": False,
    })
    assert h._response_code == 400
    assert "feature" in h._response_body["error"]


def test_record_invalid_policy_value():
    h = FakeHandler()
    h._handle_ppt2_create({
        "feature": "geolocation",
        "url": "https://ex.com",
        "policy_value": "maybe",
        "is_blocked_by_header": False,
    })
    assert h._response_code == 400
    assert "policy_value" in h._response_body["error"]


def test_record_blocked_flag():
    h = FakeHandler()
    h._handle_ppt2_create({
        "feature": "notifications",
        "url": "https://ex.com",
        "policy_value": "blocked",
        "is_blocked_by_header": True,
    })
    assert h._response_code == 201
    assert h._response_body["is_blocked_by_header"] is True


def test_record_list():
    creator = FakeHandler(method="POST", path="/api/v1/permission-policy/records", body={
        "feature": "payment",
        "url": "https://example.com",
        "policy_value": "ask",
        "is_blocked_by_header": False,
    })
    creator.do_POST()
    reader = FakeHandler(method="GET", path="/api/v1/permission-policy/records")
    reader.do_GET()
    assert reader._response_code == 200
    assert reader._response_body["total"] == 1
    assert reader._response_body["records"][0]["record_id"].startswith("ppt_")


def test_record_delete():
    creator = FakeHandler()
    creator._handle_ppt2_create({
        "feature": "usb",
        "url": "https://delete.example",
        "policy_value": "allowed",
        "is_blocked_by_header": False,
    })
    record_id = creator._response_body["record_id"]
    deleter = FakeHandler(method="DELETE", path=f"/api/v1/permission-policy/records/{record_id}")
    deleter.do_DELETE()
    assert deleter._response_code == 200
    assert deleter._response_body["record_id"] == record_id


def test_record_not_found():
    h = FakeHandler()
    h._handle_ppt2_delete("ppt_missing")
    assert h._response_code == 404


def test_policy_stats():
    first = FakeHandler()
    first._handle_ppt2_create({
        "feature": "bluetooth",
        "url": "https://one.example",
        "policy_value": "blocked",
        "is_blocked_by_header": True,
    })
    second = FakeHandler()
    second._handle_ppt2_create({
        "feature": "accelerometer",
        "url": "https://two.example",
        "policy_value": "allowed",
        "is_blocked_by_header": False,
    })
    stats = FakeHandler()
    stats._handle_ppt2_stats()
    assert stats._response_code == 200
    body = stats._response_body
    assert body["blocked_count"] == 1
    assert "block_rate" in body
    assert "." in body["block_rate"]


def test_no_port_9222_in_policy():
    banned = "922" + "2"
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert banned not in content
