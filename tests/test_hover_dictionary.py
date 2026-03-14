# Diagram: 05-solace-runtime-architecture
"""Tests for Hover Dictionary (Task 138). 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token-138").hexdigest()


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
    ys._DICT_LOOKUPS.clear()


def _make_lookup(**kwargs):
    base = {
        "word": "serendipity",
        "source_language": "en",
        "target_language": "es",
        "definition": "the occurrence of events by chance",
        "page_url": "https://example.com/article",
    }
    base.update(kwargs)
    return base


def test_lookup_create():
    """POST creates lookup with dkl_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/hover-dict/lookups", _make_lookup())
    h._handle_dict_lookup_create()
    assert h._status == 201
    lk = h._response["lookup"]
    assert lk["lookup_id"].startswith("dkl_")


def test_lookup_word_hashed():
    """POST stores word_hash, no raw word stored."""
    _reset()
    h = FakeHandler("POST", "/api/v1/hover-dict/lookups", _make_lookup())
    h._handle_dict_lookup_create()
    lk = h._response["lookup"]
    assert "word_hash" in lk
    assert len(lk["word_hash"]) == 64
    assert "word" not in lk


def test_lookup_invalid_source():
    """POST with unknown source_language returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/hover-dict/lookups", _make_lookup(source_language="xx"))
    h._handle_dict_lookup_create()
    assert h._status == 400


def test_lookup_same_language():
    """POST with source == target returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/hover-dict/lookups", _make_lookup(source_language="en", target_language="en"))
    h._handle_dict_lookup_create()
    assert h._status == 400


def test_lookup_list():
    """GET returns list of lookups."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/hover-dict/lookups", _make_lookup())
    h_c._handle_dict_lookup_create()
    h = FakeHandler("GET", "/api/v1/hover-dict/lookups")
    h._handle_dict_lookups_list()
    assert h._status == 200
    assert isinstance(h._response["lookups"], list)
    assert h._response["total"] >= 1


def test_lookup_delete():
    """DELETE removes lookup from list."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/hover-dict/lookups", _make_lookup())
    h_c._handle_dict_lookup_create()
    lid = h_c._response["lookup"]["lookup_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/hover-dict/lookups/{lid}")
    h_del._handle_dict_lookup_delete(lid)
    assert h_del._status == 200
    assert not any(lk["lookup_id"] == lid for lk in ys._DICT_LOOKUPS)


def test_lookup_not_found():
    """DELETE on nonexistent id returns 404."""
    _reset()
    h = FakeHandler("DELETE", "/api/v1/hover-dict/lookups/dkl_notexist")
    h._handle_dict_lookup_delete("dkl_notexist")
    assert h._status == 404


def test_lookup_stats():
    """GET /stats returns unique_words count."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/hover-dict/lookups", _make_lookup())
    h_c._handle_dict_lookup_create()
    h = FakeHandler("GET", "/api/v1/hover-dict/stats")
    h._handle_dict_stats()
    assert h._status == 200
    assert "unique_words" in h._response
    assert h._response["unique_words"] >= 1


def test_languages_list():
    """GET /languages returns 15 languages."""
    _reset()
    h = FakeHandler("GET", "/api/v1/hover-dict/languages")
    h._handle_dict_languages()
    assert h._status == 200
    assert len(h._response["languages"]) == 15


def test_no_port_9222_in_dict():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
