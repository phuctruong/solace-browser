"""Tests for Task 150 — Media Playback Tracker. 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-150").hexdigest()


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
    with ys._MEDIA_PLAYBACK_LOCK:
        ys._MEDIA_PLAYBACK_SESSIONS.clear()


def _make_session(**kwargs):
    base = {
        "url": "https://example.com/video.mp4",
        "media_type": "video",
        "event_type": "play",
        "duration_seconds": 100,
        "watched_seconds": 50,
        "playback_speed": "1.0",
    }
    base.update(kwargs)
    return base


def test_session_create():
    """POST creates session with mpt_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/media-tracker/sessions", _make_session())
    h._handle_mpt_create()
    assert h._status == 201
    s = h._response["session"]
    assert s["media_session_id"].startswith("mpt_")


def test_session_url_hashed():
    """POST stores url_hash, raw URL never stored."""
    _reset()
    url = "https://private.com/secret-video.mp4"
    h = FakeHandler("POST", "/api/v1/media-tracker/sessions", _make_session(url=url))
    h._handle_mpt_create()
    assert h._status == 201
    s = h._response["session"]
    assert "url_hash" in s
    assert s["url_hash"] == hashlib.sha256(url.encode()).hexdigest()
    assert "url" not in s


def test_session_invalid_media_type():
    """Unknown media_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/media-tracker/sessions", _make_session(media_type="movie"))
    h._handle_mpt_create()
    assert h._status == 400


def test_session_invalid_event():
    """Unknown event_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/media-tracker/sessions", _make_session(event_type="rewind"))
    h._handle_mpt_create()
    assert h._status == 400


def test_session_watched_pct():
    """duration=100, watched=75 yields watched_pct='75.00'."""
    _reset()
    h = FakeHandler("POST", "/api/v1/media-tracker/sessions",
                    _make_session(duration_seconds=100, watched_seconds=75))
    h._handle_mpt_create()
    assert h._status == 201
    assert h._response["session"]["watched_pct"] == "75.00"


def test_session_zero_duration():
    """duration=0 yields watched_pct='0.00'."""
    _reset()
    h = FakeHandler("POST", "/api/v1/media-tracker/sessions",
                    _make_session(duration_seconds=0, watched_seconds=0))
    h._handle_mpt_create()
    assert h._status == 201
    assert h._response["session"]["watched_pct"] == "0.00"


def test_session_invalid_speed():
    """playback_speed='5.0' returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/media-tracker/sessions", _make_session(playback_speed="5.0"))
    h._handle_mpt_create()
    assert h._status == 400


def test_session_list():
    """GET returns list of sessions."""
    _reset()
    FakeHandler("POST", "/api/v1/media-tracker/sessions", _make_session())._handle_mpt_create()
    h = FakeHandler("GET", "/api/v1/media-tracker/sessions")
    h._handle_mpt_list()
    assert h._status == 200
    assert isinstance(h._response["sessions"], list)
    assert h._response["total"] >= 1


def test_session_delete():
    """DELETE removes session."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/media-tracker/sessions", _make_session())
    h_create._handle_mpt_create()
    sid = h_create._response["session"]["media_session_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/media-tracker/sessions/{sid}")
    h_del._handle_mpt_delete(sid)
    assert h_del._status == 200
    with ys._MEDIA_PLAYBACK_LOCK:
        ids = [s["media_session_id"] for s in ys._MEDIA_PLAYBACK_SESSIONS]
    assert sid not in ids


def test_no_port_9222_in_media_tracker():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
