# Diagram: 05-solace-runtime-architecture
"""Tests for Task 092 — Translation Overlay."""
import sys
import pathlib
REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import json
import hashlib
import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token").hexdigest()


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method="GET", path="/", body=None, auth=True):
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

    def log_message(self, *a):
        pass


def setup_function():
    with ys._TRANSLATION_LOCK:
        ys._TRANSLATION_HISTORY.clear()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _make_translate_body(source="en", target="fr", chars=100):
    return {
        "source_lang": source,
        "target_lang": target,
        "text_hash": _sha256("some source text"),
        "result_hash": _sha256("some result text"),
        "char_count": chars,
    }


def test_translate_valid():
    """POST /api/v1/translation/translate records a translation."""
    body = _make_translate_body("en", "fr", 250)
    h = FakeHandler("POST", "/api/v1/translation/translate", body=body, auth=True)
    h._handle_translation_translate()
    assert h._status == 201
    assert h._response["translation"]["translation_id"].startswith("trn_")
    assert h._response["translation"]["source_lang"] == "en"
    assert h._response["translation"]["target_lang"] == "fr"


def test_translate_same_language():
    """source_lang == target_lang returns 400."""
    body = _make_translate_body("en", "en")
    h = FakeHandler("POST", "/api/v1/translation/translate", body=body, auth=True)
    h._handle_translation_translate()
    assert h._status == 400
    assert "differ" in h._response["error"]


def test_translate_invalid_source_lang():
    """Unknown source_lang returns 400."""
    body = {
        "source_lang": "zz",
        "target_lang": "fr",
        "text_hash": _sha256("x"),
        "result_hash": _sha256("y"),
        "char_count": 10,
    }
    h = FakeHandler("POST", "/api/v1/translation/translate", body=body, auth=True)
    h._handle_translation_translate()
    assert h._status == 400


def test_translate_char_count_exceeded():
    """char_count > 5000 returns 400."""
    body = _make_translate_body("en", "de", 5001)
    h = FakeHandler("POST", "/api/v1/translation/translate", body=body, auth=True)
    h._handle_translation_translate()
    assert h._status == 400
    assert "5000" in h._response["error"]


def test_history_list():
    """GET /api/v1/translation/history returns list."""
    body = _make_translate_body("en", "es", 100)
    FakeHandler("POST", "/", body=body, auth=True)._handle_translation_translate()

    h = FakeHandler("GET", "/api/v1/translation/history", auth=True)
    h._handle_translation_history()
    assert h._status == 200
    assert isinstance(h._response["history"], list)
    assert h._response["total"] >= 1


def test_history_clear():
    """DELETE /api/v1/translation/history clears history."""
    body = _make_translate_body("en", "ja")
    FakeHandler("POST", "/", body=body, auth=True)._handle_translation_translate()

    h = FakeHandler("DELETE", "/api/v1/translation/history", auth=True)
    h._handle_translation_history_clear()
    assert h._status == 200
    assert h._response["status"] == "cleared"
    with ys._TRANSLATION_LOCK:
        assert len(ys._TRANSLATION_HISTORY) == 0


def test_stats_by_lang():
    """GET /api/v1/translation/stats returns counts by language."""
    FakeHandler("POST", "/", body=_make_translate_body("en", "fr"), auth=True)._handle_translation_translate()
    FakeHandler("POST", "/", body=_make_translate_body("en", "de"), auth=True)._handle_translation_translate()

    h = FakeHandler("GET", "/api/v1/translation/stats", auth=True)
    h._handle_translation_stats()
    assert h._status == 200
    assert h._response["total"] >= 2
    assert "by_source_lang" in h._response
    assert "by_target_lang" in h._response
    assert h._response["by_source_lang"]["en"] >= 2


def test_languages_public():
    """GET /api/v1/translation/languages is public."""
    h = FakeHandler("GET", "/api/v1/translation/languages", auth=False)
    h._handle_translation_languages()
    assert h._status == 200
    assert "languages" in h._response
    assert "en" in h._response["languages"]
    assert h._response["languages"]["en"] == "English"


def test_history_requires_auth():
    """GET /api/v1/translation/history requires auth."""
    h = FakeHandler("GET", "/api/v1/translation/history", auth=False)
    h._handle_translation_history()
    assert h._status == 401


def test_translate_requires_auth():
    """POST /api/v1/translation/translate requires auth."""
    body = _make_translate_body("en", "fr")
    h = FakeHandler("POST", "/api/v1/translation/translate", body=body, auth=False)
    h._handle_translation_translate()
    assert h._status == 401
