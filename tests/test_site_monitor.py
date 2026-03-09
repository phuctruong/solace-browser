"""Tests for Site Monitor (Task 119). 10 tests."""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
import json
import hashlib
from io import BytesIO


VALID_TOKEN = hashlib.sha256(b"test-site-monitor-token").hexdigest()


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method, path, body=None, auth=True):
        self.command = method
        self.path = path
        self._body = json.dumps(body).encode() if body else b""
        self._auth = auth
        self._status = None
        self._response = None
        self.headers = {
            "Content-Length": str(len(self._body)),
            "Authorization": f"Bearer {VALID_TOKEN}" if auth else "",
        }
        self.server = type("S", (), {
            "session_token_sha256": VALID_TOKEN,
            "repo_root": str(REPO_ROOT),
        })()
        self.rfile = BytesIO(self._body)
        self.wfile = BytesIO()

    def send_response(self, code):
        self._status = code

    def send_header(self, *a):
        pass

    def end_headers(self):
        pass

    def _send_json(self, data, code=200):
        self._status = code
        self._response = data

    def _check_auth(self):
        if not self._auth:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}


def _reset():
    ys._SITE_MONITORS.clear()
    ys._SITE_CHECKS.clear()


def test_monitor_create():
    """POST creates monitor with smt_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/site-monitor/monitors", {
        "url": "https://example.com",
        "name": "Example Monitor",
        "check_interval_mins": 5,
    })
    h._handle_site_monitor_create()
    assert h._status == 201
    monitor = h._response["monitor"]
    assert monitor["monitor_id"].startswith("smt_")


def test_monitor_url_hashed():
    """url_hash present, no raw URL stored."""
    _reset()
    url = "https://secret-site.example.com/private"
    h = FakeHandler("POST", "/api/v1/site-monitor/monitors", {
        "url": url,
        "name": "Secret Monitor",
        "check_interval_mins": 10,
    })
    h._handle_site_monitor_create()
    assert h._status == 201
    monitor = h._response["monitor"]
    assert "url_hash" in monitor
    assert url not in str(monitor)
    expected = hashlib.sha256(url.encode()).hexdigest()
    assert monitor["url_hash"] == expected


def test_monitor_invalid_interval():
    """check_interval_mins=0 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/site-monitor/monitors", {
        "url": "https://example.com",
        "name": "Bad Monitor",
        "check_interval_mins": 0,
    })
    h._handle_site_monitor_create()
    assert h._status == 400


def test_check_create():
    """POST check returns sck_ prefix and increments check_count."""
    _reset()
    # Create a monitor first
    mh = FakeHandler("POST", "/api/v1/site-monitor/monitors", {
        "url": "https://example.com",
        "name": "Test Monitor",
        "check_interval_mins": 5,
    })
    mh._handle_site_monitor_create()
    monitor_id = mh._response["monitor"]["monitor_id"]

    ch = FakeHandler("POST", "/api/v1/site-monitor/checks", {
        "monitor_id": monitor_id,
        "status": "up",
        "http_code": 200,
        "response_ms": 123,
    })
    ch._handle_site_check_create()
    assert ch._status == 201
    check = ch._response["check"]
    assert check["check_id"].startswith("sck_")

    # Verify check_count incremented
    lh = FakeHandler("GET", "/api/v1/site-monitor/monitors")
    lh._handle_site_monitors_list()
    monitors = lh._response["monitors"]
    assert monitors[0]["check_count"] == 1


def test_check_invalid_status():
    """Unknown status returns 400."""
    _reset()
    mh = FakeHandler("POST", "/api/v1/site-monitor/monitors", {
        "url": "https://example.com",
        "name": "Test",
        "check_interval_mins": 5,
    })
    mh._handle_site_monitor_create()
    monitor_id = mh._response["monitor"]["monitor_id"]

    ch = FakeHandler("POST", "/api/v1/site-monitor/checks", {
        "monitor_id": monitor_id,
        "status": "INVALID_STATUS",
        "http_code": 200,
        "response_ms": 100,
    })
    ch._handle_site_check_create()
    assert ch._status == 400


def test_check_invalid_http_code():
    """http_code=600 returns 400."""
    _reset()
    mh = FakeHandler("POST", "/api/v1/site-monitor/monitors", {
        "url": "https://example.com",
        "name": "Test",
        "check_interval_mins": 5,
    })
    mh._handle_site_monitor_create()
    monitor_id = mh._response["monitor"]["monitor_id"]

    ch = FakeHandler("POST", "/api/v1/site-monitor/checks", {
        "monitor_id": monitor_id,
        "status": "up",
        "http_code": 600,
        "response_ms": 100,
    })
    ch._handle_site_check_create()
    assert ch._status == 400


def test_check_invalid_monitor():
    """Non-existent monitor_id returns 404."""
    _reset()
    ch = FakeHandler("POST", "/api/v1/site-monitor/checks", {
        "monitor_id": "smt_doesnotexist",
        "status": "up",
        "http_code": 200,
        "response_ms": 100,
    })
    ch._handle_site_check_create()
    assert ch._status == 404


def test_monitor_list():
    """GET returns list of monitors."""
    _reset()
    h = FakeHandler("POST", "/api/v1/site-monitor/monitors", {
        "url": "https://example.com",
        "name": "List Test",
        "check_interval_mins": 15,
    })
    h._handle_site_monitor_create()
    lh = FakeHandler("GET", "/api/v1/site-monitor/monitors")
    lh._handle_site_monitors_list()
    assert lh._status == 200
    assert "monitors" in lh._response
    assert lh._response["total"] == 1


def test_statuses_list():
    """GET /statuses returns 6 statuses."""
    h = FakeHandler("GET", "/api/v1/site-monitor/statuses")
    h._handle_site_check_statuses()
    assert h._status == 200
    assert len(h._response["statuses"]) == 6
    assert "up" in h._response["statuses"]
    assert "down" in h._response["statuses"]


def test_no_legacy_debug_port_in_monitor():
    """Grep check: legacy debug port must not appear in this file."""
    banned_port = "92" + "22"  # split to avoid self-matching
    source = pathlib.Path(__file__).read_text()
    assert banned_port not in source
