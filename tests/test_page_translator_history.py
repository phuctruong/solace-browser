"""Tests for Page Translator History (Task 140). 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token-140").hexdigest()


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
    ys._TRANSLATOR_HISTORY.clear()


def _make_translation(**kwargs):
    base = {
        "url": "https://example.com/article",
        "source_lang": "en",
        "target_lang": "es",
        "word_count": 500,
    }
    base.update(kwargs)
    return base


def test_translation_create():
    """POST creates translation with ptr_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/page-translator/translations", _make_translation())
    h._handle_translator_create()
    assert h._status == 201
    tr = h._response["translation"]
    assert tr["translation_id"].startswith("ptr_")


def test_translation_url_hashed():
    """POST stores url_hash, no raw URL stored."""
    _reset()
    h = FakeHandler("POST", "/api/v1/page-translator/translations", _make_translation())
    h._handle_translator_create()
    tr = h._response["translation"]
    assert "url_hash" in tr
    assert len(tr["url_hash"]) == 64
    assert "url" not in tr


def test_translation_invalid_source():
    """POST with unknown source_lang returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/page-translator/translations", _make_translation(source_lang="xx"))
    h._handle_translator_create()
    assert h._status == 400


def test_translation_invalid_target():
    """POST with unknown target_lang returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/page-translator/translations", _make_translation(target_lang="zz"))
    h._handle_translator_create()
    assert h._status == 400


def test_translation_same_lang():
    """POST with source == target returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/page-translator/translations", _make_translation(source_lang="fr", target_lang="fr"))
    h._handle_translator_create()
    assert h._status == 400


def test_translation_list():
    """GET returns list of translations."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/page-translator/translations", _make_translation())
    h_c._handle_translator_create()
    h = FakeHandler("GET", "/api/v1/page-translator/translations")
    h._handle_translator_list()
    assert h._status == 200
    assert isinstance(h._response["translations"], list)
    assert h._response["total"] >= 1


def test_translation_delete():
    """DELETE removes translation."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/page-translator/translations", _make_translation())
    h_c._handle_translator_create()
    tid = h_c._response["translation"]["translation_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/page-translator/translations/{tid}")
    h_del._handle_translator_delete(tid)
    assert h_del._status == 200
    assert not any(t["translation_id"] == tid for t in ys._TRANSLATOR_HISTORY)


def test_translation_not_found():
    """DELETE on nonexistent id returns 404."""
    _reset()
    h = FakeHandler("DELETE", "/api/v1/page-translator/translations/ptr_notexist")
    h._handle_translator_delete("ptr_notexist")
    assert h._status == 404


def test_translation_stats():
    """GET /stats returns most_translated_language."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/page-translator/translations", _make_translation())
    h_c._handle_translator_create()
    h = FakeHandler("GET", "/api/v1/page-translator/stats")
    h._handle_translator_stats()
    assert h._status == 200
    assert "most_translated_language" in h._response
    assert h._response["most_translated_language"] == "es"


def test_no_port_9222_in_translator():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
