# Diagram: 05-solace-runtime-architecture
"""Tests for Page Summary AI (Task 129). 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token-129").hexdigest()


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
    ys._SUMMARIES.clear()


def _make_summary(**kwargs):
    base = {
        "url": "https://example.com/article",
        "title": "Test Article",
        "content": "Lorem ipsum dolor sit amet",
        "summary_type": "brief",
        "model": "haiku",
        "word_count": 100,
        "token_cost_usd": "0.001",
    }
    base.update(kwargs)
    return base


def test_summary_create():
    """POST creates summary with psa_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/page-summary/summaries", _make_summary())
    h._handle_summary_create()
    assert h._status == 201
    s = h._response["summary"]
    assert s["summary_id"].startswith("psa_")


def test_summary_url_hashed():
    """POST stores url_hash (not plaintext URL)."""
    _reset()
    h = FakeHandler("POST", "/api/v1/page-summary/summaries", _make_summary())
    h._handle_summary_create()
    s = h._response["summary"]
    assert "url_hash" in s
    assert len(s["url_hash"]) == 64


def test_summary_invalid_type():
    """POST with invalid summary_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/page-summary/summaries", _make_summary(summary_type="invalid"))
    h._handle_summary_create()
    assert h._status == 400


def test_summary_invalid_model():
    """POST with invalid model returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/page-summary/summaries", _make_summary(model="gpt99"))
    h._handle_summary_create()
    assert h._status == 400


def test_summary_zero_words():
    """POST with word_count=0 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/page-summary/summaries", _make_summary(word_count=0))
    h._handle_summary_create()
    assert h._status == 400


def test_summary_invalid_quality():
    """POST with quality_score=6 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/page-summary/summaries", _make_summary(quality_score=6))
    h._handle_summary_create()
    assert h._status == 400


def test_summary_list():
    """GET returns list of summaries."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/page-summary/summaries", _make_summary())
    h_create._handle_summary_create()
    h = FakeHandler("GET", "/api/v1/page-summary/summaries")
    h._handle_summaries_list()
    assert h._status == 200
    assert isinstance(h._response["summaries"], list)
    assert h._response["total"] >= 1


def test_summary_delete():
    """DELETE removes summary from list."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/page-summary/summaries", _make_summary())
    h_create._handle_summary_create()
    summary_id = h_create._response["summary"]["summary_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/page-summary/summaries/{summary_id}")
    h_del._handle_summary_delete(summary_id)
    assert h_del._status == 200
    assert not any(s["summary_id"] == summary_id for s in ys._SUMMARIES)


def test_summary_stats():
    """GET /stats returns total_cost_usd as Decimal string."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/page-summary/summaries", _make_summary(token_cost_usd="0.005"))
    h_create._handle_summary_create()
    h = FakeHandler("GET", "/api/v1/page-summary/stats")
    h._handle_summary_stats()
    assert h._status == 200
    assert "total_cost_usd" in h._response
    # Must be a string (Decimal representation)
    assert isinstance(h._response["total_cost_usd"], str)


def test_no_port_9222_in_summary():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
