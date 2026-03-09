"""Tests for Task 149 — Scroll Tracker. 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-149").hexdigest()


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
    with ys._SCROLL_TRACKER_LOCK:
        ys._SCROLL_TRACKER_SESSIONS.clear()


def _make_session(**kwargs):
    base = {
        "url": "https://example.com/article",
        "max_depth_pct": 50,
        "scroll_events": 10,
        "time_on_page_ms": 30000,
    }
    base.update(kwargs)
    return base


def test_session_create():
    """POST creates scroll session with sct_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/scroll-tracker/sessions", _make_session())
    h._handle_sct_create()
    assert h._status == 201
    s = h._response["session"]
    assert s["scroll_session_id"].startswith("sct_")


def test_session_url_hashed():
    """POST stores url_hash, raw URL never stored."""
    _reset()
    url = "https://private.com/article"
    h = FakeHandler("POST", "/api/v1/scroll-tracker/sessions", _make_session(url=url))
    h._handle_sct_create()
    assert h._status == 201
    s = h._response["session"]
    assert "url_hash" in s
    assert s["url_hash"] == hashlib.sha256(url.encode()).hexdigest()
    assert "url" not in s


def test_session_depth_level():
    """max_depth_pct=80 maps to depth_level='75-100%'."""
    _reset()
    h = FakeHandler("POST", "/api/v1/scroll-tracker/sessions", _make_session(max_depth_pct=80))
    h._handle_sct_create()
    assert h._status == 201
    assert h._response["session"]["depth_level"] == "75-100%"


def test_session_invalid_depth():
    """max_depth_pct=101 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/scroll-tracker/sessions", _make_session(max_depth_pct=101))
    h._handle_sct_create()
    assert h._status == 400


def test_session_negative_events():
    """scroll_events=-1 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/scroll-tracker/sessions", _make_session(scroll_events=-1))
    h._handle_sct_create()
    assert h._status == 400


def test_session_list():
    """GET returns list of sessions."""
    _reset()
    FakeHandler("POST", "/api/v1/scroll-tracker/sessions", _make_session())._handle_sct_create()
    h = FakeHandler("GET", "/api/v1/scroll-tracker/sessions")
    h._handle_sct_list()
    assert h._status == 200
    assert isinstance(h._response["sessions"], list)
    assert h._response["total"] >= 1


def test_session_delete():
    """DELETE removes session."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/scroll-tracker/sessions", _make_session())
    h_create._handle_sct_create()
    sid = h_create._response["session"]["scroll_session_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/scroll-tracker/sessions/{sid}")
    h_del._handle_sct_delete(sid)
    assert h_del._status == 200
    with ys._SCROLL_TRACKER_LOCK:
        ids = [s["scroll_session_id"] for s in ys._SCROLL_TRACKER_SESSIONS]
    assert sid not in ids


def test_session_not_found():
    """DELETE non-existent session returns 404."""
    _reset()
    h = FakeHandler("DELETE", "/api/v1/scroll-tracker/sessions/sct_notexist")
    h._handle_sct_delete("sct_notexist")
    assert h._status == 404


def test_scroll_stats():
    """GET /stats returns avg_depth_pct as Decimal string."""
    _reset()
    FakeHandler("POST", "/api/v1/scroll-tracker/sessions", _make_session(max_depth_pct=100))._handle_sct_create()
    FakeHandler("POST", "/api/v1/scroll-tracker/sessions", _make_session(max_depth_pct=50))._handle_sct_create()
    h = FakeHandler("GET", "/api/v1/scroll-tracker/stats")
    h._handle_sct_stats()
    assert h._status == 200
    r = h._response
    assert "avg_depth_pct" in r
    assert "." in r["avg_depth_pct"]  # Decimal format
    assert r["total_sessions"] == 2
    assert r["full_read_count"] == 1  # one 100% session


def test_no_port_9222_in_scroll():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
