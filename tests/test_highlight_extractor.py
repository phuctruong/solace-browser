# Diagram: 05-solace-runtime-architecture
"""Tests for Task 135 — Highlight Extractor. 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-135").hexdigest()


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
    with ys._HIGHLIGHT_LOCK:
        ys._HIGHLIGHTS.clear()


def _make_highlight(**kwargs):
    base = {
        "page_url": "https://example.com/article",
        "text": "This is highlighted text",
        "color": "yellow",
        "note": "My annotation",
        "position": "100-150",
    }
    base.update(kwargs)
    return base


def test_highlight_create():
    """POST creates highlight with hlt_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/highlights/highlights", _make_highlight())
    h._handle_hlt_create()
    assert h._status == 201
    hl = h._response["highlight"]
    assert hl["highlight_id"].startswith("hlt_")


def test_highlight_text_hashed():
    """POST stores text_hash, no raw text."""
    _reset()
    text = "Some important highlighted text"
    h = FakeHandler("POST", "/api/v1/highlights/highlights", _make_highlight(text=text))
    h._handle_hlt_create()
    assert h._status == 201
    hl = h._response["highlight"]
    assert "text_hash" in hl
    assert hl["text_hash"] == hashlib.sha256(text.encode()).hexdigest()
    assert "text" not in hl


def test_highlight_invalid_color():
    """POST with unknown color returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/highlights/highlights", _make_highlight(color="rainbow"))
    h._handle_hlt_create()
    assert h._status == 400


def test_highlight_list():
    """GET returns list of highlights."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/highlights/highlights", _make_highlight())
    h_create._handle_hlt_create()
    h = FakeHandler("GET", "/api/v1/highlights/highlights")
    h._handle_hlt_list()
    assert h._status == 200
    assert isinstance(h._response["highlights"], list)
    assert h._response["total"] >= 1


def test_highlight_by_page():
    """GET /by-page?page_hash=xxx returns filtered highlights."""
    _reset()
    page_url = "https://filtered.com/page"
    page_hash = hashlib.sha256(page_url.encode()).hexdigest()
    h_create = FakeHandler("POST", "/api/v1/highlights/highlights", _make_highlight(page_url=page_url))
    h_create._handle_hlt_create()
    # Create one on a different page
    h_other = FakeHandler("POST", "/api/v1/highlights/highlights", _make_highlight(page_url="https://other.com"))
    h_other._handle_hlt_create()

    h = FakeHandler("GET", f"/api/v1/highlights/highlights/by-page?page_hash={page_hash}")
    h._handle_hlt_by_page()
    assert h._status == 200
    result = h._response["highlights"]
    assert len(result) >= 1
    assert all(hl["page_hash"] == page_hash for hl in result)


def test_highlight_delete():
    """DELETE removes highlight."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/highlights/highlights", _make_highlight())
    h_create._handle_hlt_create()
    hl_id = h_create._response["highlight"]["highlight_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/highlights/highlights/{hl_id}")
    h_del._handle_hlt_delete(hl_id)
    assert h_del._status == 200
    with ys._HIGHLIGHT_LOCK:
        ids = [h["highlight_id"] for h in ys._HIGHLIGHTS]
    assert hl_id not in ids


def test_highlight_not_found():
    """DELETE non-existent highlight returns 404."""
    _reset()
    h = FakeHandler("DELETE", "/api/v1/highlights/highlights/hlt_notexist")
    h._handle_hlt_delete("hlt_notexist")
    assert h._status == 404


def test_highlight_stats():
    """GET /stats returns total_pages."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/highlights/highlights", _make_highlight())
    h_create._handle_hlt_create()
    h = FakeHandler("GET", "/api/v1/highlights/stats")
    h._handle_hlt_stats()
    assert h._status == 200
    assert "total_pages" in h._response
    assert h._response["total_pages"] >= 1


def test_colors_list():
    """GET /colors returns 8 colors."""
    _reset()
    h = FakeHandler("GET", "/api/v1/highlights/colors")
    h._handle_hlt_colors()
    assert h._status == 200
    assert len(h._response["colors"]) == 8


def test_no_port_9222_in_highlight():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
