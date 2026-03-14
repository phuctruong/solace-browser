# Diagram: 05-solace-runtime-architecture
"""tests/test_spell_checker.py — Task 068: Spell Checker (30 tests per feature → 10 here)"""
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
        self.headers = {"content-length": "0"}

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass


def make_handler(body=None):
    h = FakeHandler()
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {"content-length": str(len(h._body))}
    return h


def setup_function():
    """Clear spell checker state before each test."""
    with ys._SPELLCHECK_LOCK:
        ys._CUSTOM_DICTIONARY.clear()


def test_spellcheck_no_errors():
    """Clean text → 0 errors."""
    h = make_handler({"text": "the quick brown fox", "language": "en-US"})
    h._handle_spellcheck_check()
    assert h._responses
    code, data = h._responses[-1]
    assert code == 200
    assert data["error_count"] == 0
    assert data["word_count"] == 4


def test_spellcheck_finds_errors():
    """'teh word' → at least one error found."""
    h = make_handler({"text": "teh word", "language": "en-US"})
    h._handle_spellcheck_check()
    code, data = h._responses[-1]
    assert code == 200
    assert data["error_count"] >= 1
    assert len(data["errors"]) >= 1


def test_spellcheck_no_raw_words():
    """Response contains word_hash (SHA-256), not raw misspelled word."""
    h = make_handler({"text": "recieve", "language": "en-US"})
    h._handle_spellcheck_check()
    code, data = h._responses[-1]
    assert code == 200
    assert data["error_count"] >= 1
    error = data["errors"][0]
    assert "word_hash" in error
    # word_hash should be 64 hex chars
    assert len(error["word_hash"]) == 64
    # raw word must NOT appear in word_hash field
    assert "recieve" not in error["word_hash"]
    # suggestion should be the correct spelling
    assert error["suggestion"] == "receive"


def test_spellcheck_invalid_language():
    """Unknown language → 400."""
    h = make_handler({"text": "hello", "language": "xx-YY"})
    h._handle_spellcheck_check()
    code, data = h._responses[-1]
    assert code == 400
    assert "error" in data


def test_spellcheck_word_count():
    """Word count is computed correctly."""
    h = make_handler({"text": "one two three four five", "language": "en-US"})
    h._handle_spellcheck_check()
    code, data = h._responses[-1]
    assert code == 200
    assert data["word_count"] == 5


def test_dictionary_empty():
    """GET /api/v1/spellcheck/dictionary → empty list initially."""
    h = make_handler()
    h._handle_spellcheck_dictionary_list()
    code, data = h._responses[-1]
    assert code == 200
    assert data["entries"] == []
    assert data["total"] == 0


def test_dictionary_add():
    """POST → word_hash stored, GET → appears in list."""
    word_hash = hashlib.sha256("myword".encode()).hexdigest()
    h = make_handler({"word_hash": word_hash, "label": "my custom word"})
    h._handle_spellcheck_dictionary_add()
    code, data = h._responses[-1]
    assert code == 201
    assert data["status"] == "added"
    assert data["entry"]["word_hash"] == word_hash

    h2 = make_handler()
    h2._handle_spellcheck_dictionary_list()
    code2, data2 = h2._responses[-1]
    assert code2 == 200
    assert data2["total"] == 1
    assert data2["entries"][0]["word_hash"] == word_hash


def test_dictionary_delete():
    """POST then DELETE → word_hash removed."""
    word_hash = hashlib.sha256("todelete".encode()).hexdigest()
    ha = make_handler({"word_hash": word_hash, "label": "to delete"})
    ha._handle_spellcheck_dictionary_add()

    hd = make_handler()
    hd._handle_spellcheck_dictionary_delete(word_hash)
    code, data = hd._responses[-1]
    assert code == 200
    assert data["status"] == "deleted"
    assert data["word_hash"] == word_hash

    h2 = make_handler()
    h2._handle_spellcheck_dictionary_list()
    _, data2 = h2._responses[-1]
    assert data2["total"] == 0


def test_languages_list():
    """GET /api/v1/spellcheck/languages → list of supported languages."""
    h = make_handler()
    h._handle_spellcheck_languages()
    code, data = h._responses[-1]
    assert code == 200
    assert "languages" in data
    assert "en-US" in data["languages"]
    assert data["total"] == len(ys.SUPPORTED_LANGUAGES)


def test_no_port_9222_in_spellcheck():
    """Port 9222 must not appear anywhere in the spell checker handlers."""
    import inspect
    src = inspect.getsource(ys.YinyangHandler._handle_spellcheck_check)
    src += inspect.getsource(ys.YinyangHandler._handle_spellcheck_dictionary_add)
    src += inspect.getsource(ys.YinyangHandler._handle_spellcheck_dictionary_delete)
    src += inspect.getsource(ys.YinyangHandler._handle_spellcheck_dictionary_list)
    src += inspect.getsource(ys.YinyangHandler._handle_spellcheck_languages)
    assert "9222" not in src
    assert "Companion App" not in src
