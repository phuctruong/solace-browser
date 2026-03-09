"""Tests for Task 071 — Bookmark Manager."""
import sys
import json
import hashlib

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "a" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
        self.headers = {"content-length": "0", "Authorization": f"Bearer {VALID_TOKEN}"}

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass

    def send_response(self, code):
        self._responses.append((code, {}))

    def end_headers(self):
        pass


def make_handler(body=None):
    h = FakeHandler()
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def setup_function():
    with ys._BOOKMARK_LOCK:
        ys._BOOKMARKS.clear()


def test_bookmark_add():
    h = make_handler({"url": "https://example.com", "title": "Example", "tags": ["test"]})
    h._handle_bkm_add()
    assert len(h._responses) == 1
    code, data = h._responses[0]
    assert code == 201
    assert data["bookmark"]["bookmark_id"].startswith("bkm_")


def test_bookmark_list():
    h = make_handler({"url": "https://example.com/list", "title": "List Test"})
    h._handle_bkm_add()
    h2 = FakeHandler()
    h2._handle_bkm_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["bookmarks"], list)
    assert data["total"] >= 1


def test_bookmark_url_hashed():
    url = "https://secret.com"
    h = make_handler({"url": url, "title": "Secret"})
    h._handle_bkm_add()
    code, data = h._responses[0]
    assert code == 201
    bm = data["bookmark"]
    assert "url_hash" in bm
    assert bm["url_hash"] == hashlib.sha256(url.encode()).hexdigest()
    # raw URL must NOT be stored
    assert "url" not in bm


def test_bookmark_title_too_long():
    h = make_handler({"url": "https://x.com", "title": "A" * 129})
    h._handle_bkm_add()
    code, data = h._responses[0]
    assert code == 400
    assert "128" in data["error"]


def test_bookmark_too_many_tags():
    h = make_handler({"url": "https://x.com", "title": "T", "tags": [str(i) for i in range(11)]})
    h._handle_bkm_add()
    code, data = h._responses[0]
    assert code == 400
    assert "10" in data["error"] or "max" in data["error"].lower()


def test_bookmark_delete():
    h = make_handler({"url": "https://del.com", "title": "Del"})
    h._handle_bkm_add()
    bm_id = h._responses[0][1]["bookmark"]["bookmark_id"]
    h2 = make_handler()
    h2._handle_bkm_delete(bm_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["bookmark_id"] == bm_id
    # ensure removed
    with ys._BOOKMARK_LOCK:
        ids = [b["bookmark_id"] for b in ys._BOOKMARKS]
    assert bm_id not in ids


def test_bookmark_delete_not_found():
    h = make_handler()
    h._handle_bkm_delete("bkm_notexist")
    code, data = h._responses[0]
    assert code == 404


def test_bookmark_search():
    h = make_handler({"url": "https://search.com", "title": "SearchTitle", "tags": ["searchable"]})
    h._handle_bkm_add()

    class SearchHandler(FakeHandler):
        def _parse_query(self, q):
            return {"q": "searchable"}

    h2 = SearchHandler()
    h2._handle_bkm_search("")
    code, data = h2._responses[0]
    assert code == 200
    assert any("searchable" in str(b.get("tags", [])) for b in data["bookmarks"])


def test_bookmark_tags_list():
    h = make_handler({"url": "https://tag.com", "title": "Tagged", "tags": ["alpha", "beta"]})
    h._handle_bkm_add()
    h2 = FakeHandler()
    h2._handle_bkm_tags()
    code, data = h2._responses[0]
    assert code == 200
    assert "tags" in data
    assert isinstance(data["tags"], list)


def test_no_port_9222_in_bookmark():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found in yinyang_server.py — BANNED"
