"""Tests for Task 136 — Bookmark Organizer. 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-136").hexdigest()


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
    with ys._BMK_ORG_LOCK:
        ys._BMK_ORG_BOOKMARKS.clear()


def _make_bookmark(**kwargs):
    base = {
        "url": "https://example.com/page",
        "title": "Example Page",
        "folder": "work",
        "tags": ["productivity", "tools"],
    }
    base.update(kwargs)
    return base


def test_bookmark_create():
    """POST creates bookmark with bmk_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/bookmarks/bookmarks", _make_bookmark())
    h._handle_bmkorg_create()
    assert h._status == 201
    b = h._response["bookmark"]
    assert b["bookmark_id"].startswith("bmk_")


def test_bookmark_url_hashed():
    """POST stores url_hash, no raw URL."""
    _reset()
    url = "https://secret.com/page"
    h = FakeHandler("POST", "/api/v1/bookmarks/bookmarks", _make_bookmark(url=url))
    h._handle_bmkorg_create()
    assert h._status == 201
    b = h._response["bookmark"]
    assert "url_hash" in b
    assert b["url_hash"] == hashlib.sha256(url.encode()).hexdigest()
    assert "url" not in b


def test_bookmark_invalid_folder():
    """POST with unknown folder returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/bookmarks/bookmarks", _make_bookmark(folder="unknown_folder"))
    h._handle_bmkorg_create()
    assert h._status == 400


def test_bookmark_too_many_tags():
    """POST with more than 10 tags returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/bookmarks/bookmarks", _make_bookmark(tags=[str(i) for i in range(11)]))
    h._handle_bmkorg_create()
    assert h._status == 400


def test_bookmark_list():
    """GET returns list of bookmarks."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/bookmarks/bookmarks", _make_bookmark())
    h_create._handle_bmkorg_create()
    h = FakeHandler("GET", "/api/v1/bookmarks/bookmarks")
    h._handle_bmkorg_list()
    assert h._status == 200
    assert isinstance(h._response["bookmarks"], list)
    assert h._response["total"] >= 1


def test_bookmark_search():
    """GET /search?q=bmk_ returns results."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/bookmarks/bookmarks", _make_bookmark())
    h_create._handle_bmkorg_create()
    bm_id = h_create._response["bookmark"]["bookmark_id"]
    # Search by bookmark_id prefix
    h = FakeHandler("GET", f"/api/v1/bookmarks/bookmarks/search?q=bmk_")
    h._handle_bmkorg_search()
    assert h._status == 200
    assert h._response["total"] >= 1
    assert any(b["bookmark_id"] == bm_id for b in h._response["bookmarks"])


def test_bookmark_delete():
    """DELETE removes bookmark."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/bookmarks/bookmarks", _make_bookmark())
    h_create._handle_bmkorg_create()
    bm_id = h_create._response["bookmark"]["bookmark_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/bookmarks/bookmarks/{bm_id}")
    h_del._handle_bmkorg_delete(bm_id)
    assert h_del._status == 200
    with ys._BMK_ORG_LOCK:
        ids = [b["bookmark_id"] for b in ys._BMK_ORG_BOOKMARKS]
    assert bm_id not in ids


def test_bookmark_not_found():
    """DELETE non-existent bookmark returns 404."""
    _reset()
    h = FakeHandler("DELETE", "/api/v1/bookmarks/bookmarks/bmk_notexist")
    h._handle_bmkorg_delete("bmk_notexist")
    assert h._status == 404


def test_bookmark_stats():
    """GET /stats returns by_folder."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/bookmarks/bookmarks", _make_bookmark(folder="work"))
    h_create._handle_bmkorg_create()
    h = FakeHandler("GET", "/api/v1/bookmarks/stats")
    h._handle_bmkorg_stats()
    assert h._status == 200
    assert "by_folder" in h._response
    assert h._response["by_folder"].get("work", 0) >= 1


def test_no_port_9222_in_bookmark():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
