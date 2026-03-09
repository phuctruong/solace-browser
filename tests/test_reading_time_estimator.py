"""Tests for Reading Time Estimator (Task 130). 10 tests."""
import sys
import pathlib
import hashlib
import json
from decimal import Decimal

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token-130").hexdigest()


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
    ys._ESTIMATES.clear()


def _make_estimate(**kwargs):
    base = {
        "url": "https://example.com/article",
        "content_type": "article",
        "word_count": 476,
    }
    base.update(kwargs)
    return base


def test_estimate_create():
    """POST creates estimate with rte_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reading-time/estimates", _make_estimate())
    h._handle_estimate_create()
    assert h._status == 201
    e = h._response["estimate"]
    assert e["estimate_id"].startswith("rte_")


def test_estimate_url_hashed():
    """POST stores url_hash."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reading-time/estimates", _make_estimate())
    h._handle_estimate_create()
    e = h._response["estimate"]
    assert "url_hash" in e
    assert len(e["url_hash"]) == 64


def test_estimate_invalid_content_type():
    """POST with invalid content_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reading-time/estimates", _make_estimate(content_type="podcast"))
    h._handle_estimate_create()
    assert h._status == 400


def test_estimate_zero_words():
    """POST with word_count=0 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reading-time/estimates", _make_estimate(word_count=0))
    h._handle_estimate_create()
    assert h._status == 400


def test_estimate_computed():
    """POST with word_count=238 returns estimated_minutes='1.00'."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reading-time/estimates", _make_estimate(word_count=238))
    h._handle_estimate_create()
    assert h._status == 201
    e = h._response["estimate"]
    assert e["estimated_minutes"] == "1.00"


def test_estimate_with_actual():
    """POST with actual_minutes provided returns accuracy_pct."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reading-time/estimates", _make_estimate(word_count=238, actual_minutes="1.0"))
    h._handle_estimate_create()
    assert h._status == 201
    e = h._response["estimate"]
    assert e["accuracy_pct"] is not None
    # accuracy should be representable as Decimal
    Decimal(e["accuracy_pct"])


def test_estimate_list():
    """GET returns list of estimates."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/reading-time/estimates", _make_estimate())
    h_create._handle_estimate_create()
    h = FakeHandler("GET", "/api/v1/reading-time/estimates")
    h._handle_estimates_list()
    assert h._status == 200
    assert isinstance(h._response["estimates"], list)
    assert h._response["total"] >= 1


def test_estimate_delete():
    """DELETE removes estimate."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/reading-time/estimates", _make_estimate())
    h_create._handle_estimate_create()
    eid = h_create._response["estimate"]["estimate_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/reading-time/estimates/{eid}")
    h_del._handle_estimate_delete(eid)
    assert h_del._status == 200
    assert not any(e["estimate_id"] == eid for e in ys._ESTIMATES)


def test_estimate_stats():
    """GET /stats returns avg_estimated_minutes as Decimal string."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/reading-time/estimates", _make_estimate(word_count=238))
    h_create._handle_estimate_create()
    h = FakeHandler("GET", "/api/v1/reading-time/stats")
    h._handle_reading_time_stats()
    assert h._status == 200
    assert "avg_estimated_minutes" in h._response
    assert isinstance(h._response["avg_estimated_minutes"], str)
    Decimal(h._response["avg_estimated_minutes"])


def test_no_port_9222_in_reading_time():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
