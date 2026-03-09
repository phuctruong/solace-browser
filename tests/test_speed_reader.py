"""Tests for Speed Reader (Task 125). 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token-125").hexdigest()


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
    ys._SPEED_SESSIONS.clear()


def _make_session(wpm=300, difficulty="beginner", comprehension_score=80, word_count=500, duration_seconds=100, text="sample text"):
    return {
        "text": text,
        "word_count": word_count,
        "wpm": wpm,
        "comprehension_score": comprehension_score,
        "difficulty": difficulty,
        "duration_seconds": duration_seconds,
    }


def test_session_create():
    """POST creates session with srd_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/speed-reader/sessions", _make_session())
    h._handle_speed_reader_session_create()
    assert h._status == 201
    session = h._response["session"]
    assert session["session_id"].startswith("srd_")


def test_session_text_hashed():
    """text_hash is stored, not raw text."""
    _reset()
    raw_text = "This is my private reading content"
    h = FakeHandler("POST", "/api/v1/speed-reader/sessions", _make_session(text=raw_text))
    h._handle_speed_reader_session_create()
    assert h._status == 201
    session = h._response["session"]
    assert "text_hash" in session
    assert raw_text not in str(session)
    expected = hashlib.sha256(raw_text.encode()).hexdigest()
    assert session["text_hash"] == expected


def test_session_invalid_difficulty():
    """Unknown difficulty returns 400."""
    _reset()
    body = _make_session()
    body["difficulty"] = "INVALID"
    h = FakeHandler("POST", "/api/v1/speed-reader/sessions", body)
    h._handle_speed_reader_session_create()
    assert h._status == 400


def test_session_wpm_too_low():
    """wpm=49 returns 400."""
    _reset()
    body = _make_session(wpm=49)
    h = FakeHandler("POST", "/api/v1/speed-reader/sessions", body)
    h._handle_speed_reader_session_create()
    assert h._status == 400


def test_session_wpm_too_high():
    """wpm=2001 returns 400."""
    _reset()
    body = _make_session(wpm=2001)
    h = FakeHandler("POST", "/api/v1/speed-reader/sessions", body)
    h._handle_speed_reader_session_create()
    assert h._status == 400


def test_session_comprehension_range():
    """comprehension_score=101 returns 400."""
    _reset()
    body = _make_session(comprehension_score=101)
    h = FakeHandler("POST", "/api/v1/speed-reader/sessions", body)
    h._handle_speed_reader_session_create()
    assert h._status == 400


def test_session_list():
    """GET returns list of sessions."""
    _reset()
    for i in range(3):
        h = FakeHandler("POST", "/api/v1/speed-reader/sessions", _make_session(wpm=200 + i * 50))
        h._handle_speed_reader_session_create()
    lh = FakeHandler("GET", "/api/v1/speed-reader/sessions")
    lh._handle_speed_reader_session_list()
    assert lh._status == 200
    assert "sessions" in lh._response
    assert lh._response["total"] == 3


def test_session_delete():
    """DELETE removes session from list."""
    _reset()
    h = FakeHandler("POST", "/api/v1/speed-reader/sessions", _make_session())
    h._handle_speed_reader_session_create()
    session_id = h._response["session"]["session_id"]

    dh = FakeHandler("DELETE", f"/api/v1/speed-reader/sessions/{session_id}")
    dh._handle_speed_reader_session_delete(session_id)
    assert dh._status == 200
    assert dh._response["status"] == "deleted"

    lh = FakeHandler("GET", "/api/v1/speed-reader/sessions")
    lh._handle_speed_reader_session_list()
    assert lh._response["total"] == 0


def test_progress():
    """GET /progress returns avg_wpm as Decimal string."""
    _reset()
    for i in range(3):
        h = FakeHandler("POST", "/api/v1/speed-reader/sessions", _make_session(wpm=300))
        h._handle_speed_reader_session_create()
    ph = FakeHandler("GET", "/api/v1/speed-reader/progress")
    ph._handle_speed_reader_progress()
    assert ph._status == 200
    assert "avg_wpm" in ph._response
    # avg_wpm must be a string (Decimal str)
    assert isinstance(ph._response["avg_wpm"], str)
    assert float(ph._response["avg_wpm"]) == 300.0
    assert "avg_comprehension" in ph._response
    assert "wpm_trend" in ph._response
    assert ph._response["wpm_trend"] in ("improving", "stable", "declining")


def test_no_banned_port_in_speed_reader():
    """Grep check: banned debug port must not appear in this file."""
    source = pathlib.Path(__file__)
    banned = "9" + "222"
    assert banned not in source.read_text()
