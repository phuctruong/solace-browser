"""
Tests for Task 105 — Scroll Tracker
Browser: yinyang_server.py routes /api/v1/scroll-tracker/*
"""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
import json
import hashlib
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token").hexdigest()


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

    def _send_json(self, data, status=200):
        self._status = status
        self._response = data

    def _check_auth(self):
        if not self._auth:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}


def setup_function():
    ys._SCROLL_EVENTS.clear()


def test_record_event_ok():
    h = FakeHandler("POST", "/api/v1/scroll-tracker/events", {
        "page_hash": "a" * 64,
        "direction": "down",
        "depth_pct": 75,
        "position_px": 1500,
    })
    h._handle_scroll_event_record()
    assert h._status == 201
    assert h._response["event"]["event_id"].startswith("scv_")
    assert h._response["event"]["direction"] == "down"
    assert h._response["event"]["depth_pct"] == 75


def test_record_invalid_direction():
    h = FakeHandler("POST", "/api/v1/scroll-tracker/events", {
        "page_hash": "b" * 64,
        "direction": "BADDIR",
        "depth_pct": 50,
        "position_px": 100,
    })
    h._handle_scroll_event_record()
    assert h._status == 400
    assert "direction" in h._response["error"]


def test_record_depth_out_of_range():
    h = FakeHandler("POST", "/api/v1/scroll-tracker/events", {
        "page_hash": "c" * 64,
        "direction": "up",
        "depth_pct": 150,
        "position_px": 100,
    })
    h._handle_scroll_event_record()
    assert h._status == 400
    assert "depth_pct" in h._response["error"]


def test_record_position_negative():
    h = FakeHandler("POST", "/api/v1/scroll-tracker/events", {
        "page_hash": "d" * 64,
        "direction": "down",
        "depth_pct": 50,
        "position_px": -10,
    })
    h._handle_scroll_event_record()
    assert h._status == 400
    assert "position_px" in h._response["error"]


def test_record_requires_auth():
    h = FakeHandler("POST", "/api/v1/scroll-tracker/events", {
        "page_hash": "e" * 64,
        "direction": "left",
        "depth_pct": 30,
        "position_px": 0,
    }, auth=False)
    h._handle_scroll_event_record()
    assert h._status == 401


def test_list_events():
    h = FakeHandler("POST", "/api/v1/scroll-tracker/events", {
        "page_hash": "f" * 64,
        "direction": "right",
        "depth_pct": 20,
        "position_px": 200,
    })
    h._handle_scroll_event_record()

    h2 = FakeHandler("GET", "/api/v1/scroll-tracker/events")
    h2._handle_scroll_event_list()
    assert h2._status == 200
    assert h2._response["total"] >= 1


def test_stats():
    page_hash = "g" * 64
    h1 = FakeHandler("POST", "/api/v1/scroll-tracker/events", {
        "page_hash": page_hash,
        "direction": "down",
        "depth_pct": 40,
        "position_px": 400,
    })
    h1._handle_scroll_event_record()
    h2 = FakeHandler("POST", "/api/v1/scroll-tracker/events", {
        "page_hash": page_hash,
        "direction": "down",
        "depth_pct": 80,
        "position_px": 800,
    })
    h2._handle_scroll_event_record()

    h3 = FakeHandler("GET", "/api/v1/scroll-tracker/stats")
    h3._handle_scroll_stats()
    assert h3._status == 200
    assert h3._response["total_events"] >= 2
    assert page_hash in h3._response["by_page"]
    assert h3._response["by_page"][page_hash]["max_depth_pct"] == 80
    assert "avg_depth_pct" in h3._response


def test_stats_empty():
    h = FakeHandler("GET", "/api/v1/scroll-tracker/stats")
    h._handle_scroll_stats()
    assert h._status == 200
    assert h._response["avg_depth_pct"] == "0.00"


def test_clear_events():
    h = FakeHandler("POST", "/api/v1/scroll-tracker/events", {
        "page_hash": "h" * 64,
        "direction": "up",
        "depth_pct": 10,
        "position_px": 100,
    })
    h._handle_scroll_event_record()

    h2 = FakeHandler("DELETE", "/api/v1/scroll-tracker/events")
    h2._handle_scroll_event_clear()
    assert h2._status == 200
    assert h2._response["status"] == "cleared"
    assert len(ys._SCROLL_EVENTS) == 0


def test_directions_public():
    h = FakeHandler("GET", "/api/v1/scroll-tracker/directions", auth=False)
    h._handle_scroll_directions()
    assert h._status == 200
    assert "directions" in h._response
    assert "down" in h._response["directions"]
