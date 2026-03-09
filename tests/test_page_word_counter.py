"""Tests for Task 134 — Page Word Counter. 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-134").hexdigest()


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
    with ys._WORD_LOCK:
        ys._WORD_COUNTS.clear()


def _make_count(**kwargs):
    base = {
        "url": "https://example.com/article",
        "content_type": "article",
        "word_count": 500,
        "char_count": 3000,
        "sentence_count": 25,
        "paragraph_count": 5,
    }
    base.update(kwargs)
    return base


def test_count_create():
    """POST creates count with wct_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/word-counter/counts", _make_count())
    h._handle_wct_create()
    assert h._status == 201
    c = h._response["count"]
    assert c["count_id"].startswith("wct_")


def test_count_url_hashed():
    """POST stores url_hash, no raw URL."""
    _reset()
    url = "https://secret.com/article"
    h = FakeHandler("POST", "/api/v1/word-counter/counts", _make_count(url=url))
    h._handle_wct_create()
    assert h._status == 201
    c = h._response["count"]
    assert "url_hash" in c
    assert c["url_hash"] == hashlib.sha256(url.encode()).hexdigest()
    assert "url" not in c


def test_count_invalid_content_type():
    """POST with unknown content_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/word-counter/counts", _make_count(content_type="unknown_type"))
    h._handle_wct_create()
    assert h._status == 400


def test_count_negative_words():
    """POST with word_count=-1 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/word-counter/counts", _make_count(word_count=-1))
    h._handle_wct_create()
    assert h._status == 400


def test_count_reading_time():
    """word_count=238 produces reading_time_mins='1.00'."""
    _reset()
    h = FakeHandler("POST", "/api/v1/word-counter/counts", _make_count(word_count=238))
    h._handle_wct_create()
    assert h._status == 201
    c = h._response["count"]
    assert c["reading_time_mins"] == "1.00"


def test_count_list():
    """GET returns list of counts."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/word-counter/counts", _make_count())
    h_create._handle_wct_create()
    h = FakeHandler("GET", "/api/v1/word-counter/counts")
    h._handle_wct_list()
    assert h._status == 200
    assert isinstance(h._response["counts"], list)
    assert h._response["total"] >= 1


def test_count_delete():
    """DELETE removes count record."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/word-counter/counts", _make_count())
    h_create._handle_wct_create()
    count_id = h_create._response["count"]["count_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/word-counter/counts/{count_id}")
    h_del._handle_wct_delete(count_id)
    assert h_del._status == 200
    with ys._WORD_LOCK:
        ids = [c["count_id"] for c in ys._WORD_COUNTS]
    assert count_id not in ids


def test_count_stats():
    """GET /stats returns avg_word_count as Decimal string."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/word-counter/counts", _make_count(word_count=100))
    h_create._handle_wct_create()
    h = FakeHandler("GET", "/api/v1/word-counter/stats")
    h._handle_wct_stats()
    assert h._status == 200
    assert "avg_word_count" in h._response
    # Should be a Decimal string like "100.00"
    avg = h._response["avg_word_count"]
    assert isinstance(avg, str)
    assert "." in avg


def test_content_types_list():
    """GET /content-types returns 8 types."""
    _reset()
    h = FakeHandler("GET", "/api/v1/word-counter/content-types")
    h._handle_wct_content_types()
    assert h._status == 200
    assert len(h._response["content_types"]) == 8


def test_no_port_9222_in_word():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
