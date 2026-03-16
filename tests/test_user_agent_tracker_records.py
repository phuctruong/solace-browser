# Diagram: 05-solace-runtime-architecture
"""Tests for Task 167v2 — User Agent Tracker /records endpoints."""
import hashlib
import json
import pathlib
import sys
from io import BytesIO

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = "f" * 64


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
    with ys._USER_AGENT_LOCK:
        ys._USER_AGENT_RECORDS.clear()


def test_record_create():
    h = FakeHandler()
    h._handle_uat2_create({
        "user_agent": "Mozilla/5.0 Test",
        "platform": "linux",
        "browser": "firefox",
        "url": "https://ex.com",
        "is_mobile": False,
        "is_bot": False,
    })
    assert h._response_code == 201
    assert h._response_body["record_id"].startswith("uat_")


def test_record_url_hashed():
    url = "https://example.com/page"
    ua = "Mozilla/5.0 (X11; Linux x86_64)"
    h = FakeHandler()
    h._handle_uat2_create({
        "user_agent": ua,
        "platform": "linux",
        "browser": "solace",
        "url": url,
        "is_mobile": False,
        "is_bot": False,
    })
    assert h._response_body["url_hash"] == hashlib.sha256(url.encode("utf-8")).hexdigest()
    assert h._response_body["ua_hash"] == hashlib.sha256(ua.encode("utf-8")).hexdigest()
    assert "url" not in h._response_body
    assert "user_agent" not in h._response_body


def test_record_invalid_platform():
    h = FakeHandler()
    h._handle_uat2_create({
        "user_agent": "Mozilla/5.0 Test",
        "platform": "BeOS",
        "browser": "solace",
        "url": "https://ex.com",
        "is_mobile": False,
        "is_bot": False,
    })
    assert h._response_code == 400
    assert "platform" in h._response_body["error"]


def test_record_invalid_browser():
    h = FakeHandler()
    h._handle_uat2_create({
        "user_agent": "Mozilla/5.0 Test",
        "platform": "windows",
        "browser": "netscape",
        "url": "https://ex.com",
        "is_mobile": False,
        "is_bot": False,
    })
    assert h._response_code == 400
    assert "browser" in h._response_body["error"]


def test_record_bot_flag():
    h = FakeHandler()
    h._handle_uat2_create({
        "user_agent": "Googlebot/2.1",
        "platform": "unknown",
        "browser": "unknown",
        "url": "https://ex.com",
        "is_mobile": False,
        "is_bot": True,
    })
    assert h._response_code == 201
    assert h._response_body["is_bot"] is True


def test_record_mobile_flag():
    h = FakeHandler()
    h._handle_uat2_create({
        "user_agent": "Mobile UA",
        "platform": "android",
        "browser": "solace",
        "url": "https://ex.com",
        "is_mobile": True,
        "is_bot": False,
    })
    assert h._response_code == 201
    assert h._response_body["is_mobile"] is True


def test_record_list():
    creator = FakeHandler(method="POST", path="/api/v1/user-agent/records", body={
        "user_agent": "Mozilla/5.0 Safari",
        "platform": "macos",
        "browser": "safari",
        "url": "https://example.com",
        "is_mobile": False,
        "is_bot": False,
    })
    creator.do_POST()
    reader = FakeHandler(method="GET", path="/api/v1/user-agent/records")
    reader.do_GET()
    assert reader._response_code == 200
    assert reader._response_body["total"] == 1
    assert reader._response_body["records"][0]["record_id"].startswith("uat_")


def test_record_delete():
    creator = FakeHandler()
    creator._handle_uat2_create({
        "user_agent": "Delete UA",
        "platform": "ios",
        "browser": "safari",
        "url": "https://delete.example",
        "is_mobile": True,
        "is_bot": False,
    })
    record_id = creator._response_body["record_id"]
    deleter = FakeHandler(method="DELETE", path=f"/api/v1/user-agent/records/{record_id}")
    deleter.do_DELETE()
    assert deleter._response_code == 200
    assert deleter._response_body["record_id"] == record_id


def test_record_not_found():
    h = FakeHandler()
    h._handle_uat2_delete("uat_missing")
    assert h._response_code == 404


def test_ua_stats():
    first = FakeHandler()
    first._handle_uat2_create({
        "user_agent": "Mozilla/5.0 One",
        "platform": "linux",
        "browser": "firefox",
        "url": "https://one.example",
        "is_mobile": False,
        "is_bot": False,
    })
    second = FakeHandler()
    second._handle_uat2_create({
        "user_agent": "Mozilla/5.0 Two",
        "platform": "android",
        "browser": "solace",
        "url": "https://two.example",
        "is_mobile": True,
        "is_bot": True,
    })
    stats = FakeHandler()
    stats._handle_uat2_stats()
    assert stats._response_code == 200
    body = stats._response_body
    assert body["mobile_count"] == 1
    assert body["bot_count"] == 1
    assert "mobile_rate" in body
    assert "." in body["mobile_rate"]


def test_no_port_9222_in_user_agent():
    banned = "922" + "2"
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert banned not in content
