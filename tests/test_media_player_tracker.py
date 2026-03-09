"""
Tests for Task 100 — Media Player Tracker
Browser: yinyang_server.py routes /api/v1/media-tracker/*
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
    ys._MEDIA_EVENTS.clear()


def test_record_event_ok():
    h = FakeHandler("POST", "/api/v1/media-tracker/events", {
        "event_type": "play",
        "media_type": "video",
        "url_hash": "a" * 64,
        "title_hash": "b" * 64,
        "position_seconds": 30.0,
        "duration_seconds": 120.0,
    })
    h._handle_media_event_record()
    assert h._status == 201
    assert h._response["event"]["event_id"].startswith("mev_")
    assert h._response["event"]["event_type"] == "play"


def test_record_event_invalid_type():
    h = FakeHandler("POST", "/api/v1/media-tracker/events", {
        "event_type": "BADTYPE",
        "media_type": "video",
        "url_hash": "a" * 64,
        "title_hash": "b" * 64,
        "position_seconds": 0,
        "duration_seconds": 0,
    })
    h._handle_media_event_record()
    assert h._status == 400
    assert "event_type" in h._response["error"]


def test_record_event_invalid_media_type():
    h = FakeHandler("POST", "/api/v1/media-tracker/events", {
        "event_type": "play",
        "media_type": "BADMEDIA",
        "url_hash": "a" * 64,
        "title_hash": "b" * 64,
        "position_seconds": 0,
        "duration_seconds": 0,
    })
    h._handle_media_event_record()
    assert h._status == 400
    assert "media_type" in h._response["error"]


def test_record_event_requires_auth():
    h = FakeHandler("POST", "/api/v1/media-tracker/events", {
        "event_type": "play",
        "media_type": "video",
        "url_hash": "a" * 64,
        "title_hash": "b" * 64,
        "position_seconds": 0,
        "duration_seconds": 0,
    }, auth=False)
    h._handle_media_event_record()
    assert h._status == 401


def test_list_events():
    h = FakeHandler("POST", "/api/v1/media-tracker/events", {
        "event_type": "pause",
        "media_type": "audio",
        "url_hash": "c" * 64,
        "title_hash": "d" * 64,
        "position_seconds": 10,
        "duration_seconds": 200,
    })
    h._handle_media_event_record()
    h2 = FakeHandler("GET", "/api/v1/media-tracker/events")
    h2._handle_media_event_list()
    assert h2._status == 200
    assert h2._response["total"] >= 1
    assert any(e["event_type"] == "pause" for e in h2._response["events"])


def test_stats():
    # Record a play event
    h = FakeHandler("POST", "/api/v1/media-tracker/events", {
        "event_type": "play",
        "media_type": "podcast",
        "url_hash": "e" * 64,
        "title_hash": "f" * 64,
        "position_seconds": 50.0,
        "duration_seconds": 300,
    })
    h._handle_media_event_record()
    h2 = FakeHandler("GET", "/api/v1/media-tracker/stats")
    h2._handle_media_tracker_stats()
    assert h2._status == 200
    assert h2._response["total_events"] >= 1
    assert "by_type" in h2._response
    assert "by_media_type" in h2._response
    assert h2._response["total_play_seconds"] >= 50.0


def test_stats_requires_auth():
    h = FakeHandler("GET", "/api/v1/media-tracker/stats", auth=False)
    h._handle_media_tracker_stats()
    assert h._status == 401


def test_clear_events():
    h = FakeHandler("POST", "/api/v1/media-tracker/events", {
        "event_type": "ended",
        "media_type": "live_stream",
        "url_hash": "g" * 64,
        "title_hash": "h" * 64,
        "position_seconds": 0,
        "duration_seconds": 0,
    })
    h._handle_media_event_record()
    h2 = FakeHandler("DELETE", "/api/v1/media-tracker/events")
    h2._handle_media_event_clear()
    assert h2._status == 200
    assert h2._response["status"] == "cleared"
    assert len(ys._MEDIA_EVENTS) == 0


def test_event_types_public():
    h = FakeHandler("GET", "/api/v1/media-tracker/event-types", auth=False)
    h._handle_media_event_types()
    assert h._status == 200
    assert "event_types" in h._response
    assert "play" in h._response["event_types"]


def test_position_seconds_negative_rejected():
    h = FakeHandler("POST", "/api/v1/media-tracker/events", {
        "event_type": "seek",
        "media_type": "video",
        "url_hash": "i" * 64,
        "title_hash": "j" * 64,
        "position_seconds": -5,
        "duration_seconds": 100,
    })
    h._handle_media_event_record()
    assert h._status == 400
