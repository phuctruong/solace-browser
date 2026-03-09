"""Tests for Task 123 — Text Expander."""
import sys
import json
import subprocess

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "h" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._body = b"{}"
        self._responses = []
        self.headers = {"Authorization": f"Bearer {VALID_TOKEN}"}

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
    return h


def setup_function():
    with ys._EXPANDER_LOCK:
        ys._TEXT_SNIPPETS.clear()
        ys._EXPANSION_LOG.clear()


def test_snippet_create():
    h = make_handler({"abbreviation": "brb", "content": "Be right back", "category": "response", "tags": []})
    h._handle_snippet_create()
    code, data = h._responses[0]
    assert code == 201
    assert data["snippet"]["snippet_id"].startswith("txs_")


def test_snippet_abbrev_hashed():
    h = make_handler({"abbreviation": "omw", "content": "On my way", "category": "response", "tags": []})
    h._handle_snippet_create()
    code, data = h._responses[0]
    assert code == 201
    snippet = data["snippet"]
    assert "abbreviation_hash" in snippet
    assert "abbreviation" not in snippet


def test_snippet_invalid_category():
    h = make_handler({"abbreviation": "test", "content": "Test content", "category": "invalid_cat", "tags": []})
    h._handle_snippet_create()
    code, data = h._responses[0]
    assert code == 400
    assert "category" in data["error"]


def test_snippet_too_many_tags():
    h = make_handler({
        "abbreviation": "ttm",
        "content": "Too many tags",
        "category": "custom",
        "tags": ["a", "b", "c", "d", "e", "f"],
    })
    h._handle_snippet_create()
    code, data = h._responses[0]
    assert code == 400
    assert "tags" in data["error"]


def test_snippet_list():
    h1 = make_handler({"abbreviation": "ty", "content": "Thank you", "category": "greeting", "tags": []})
    h1._handle_snippet_create()
    h2 = FakeHandler()
    h2._handle_snippet_list_expander()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["snippets"], list)
    assert data["total"] >= 1


def test_snippet_delete():
    h = make_handler({"abbreviation": "gm", "content": "Good morning", "category": "greeting", "tags": []})
    h._handle_snippet_create()
    snippet_id = h._responses[0][1]["snippet"]["snippet_id"]
    h2 = FakeHandler()
    h2._handle_snippet_delete_expander(snippet_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["snippet_id"] == snippet_id
    with ys._EXPANDER_LOCK:
        ids = [s["snippet_id"] for s in ys._TEXT_SNIPPETS]
    assert snippet_id not in ids


def test_snippet_not_found():
    h = FakeHandler()
    h._handle_snippet_delete_expander("txs_notexist")
    code, data = h._responses[0]
    assert code == 404


def test_expand():
    h1 = make_handler({"abbreviation": "sig", "content": "Best regards, John", "category": "signature", "tags": []})
    h1._handle_snippet_create()
    snippet_id = h1._responses[0][1]["snippet"]["snippet_id"]

    h2 = make_handler({"snippet_id": snippet_id, "site": "https://gmail.com"})
    h2._handle_expansion_record()
    code, data = h2._responses[0]
    assert code == 201
    assert data["expansion"]["expansion_id"].startswith("txe_")

    # Verify use_count incremented
    with ys._EXPANDER_LOCK:
        snippet = next(s for s in ys._TEXT_SNIPPETS if s["snippet_id"] == snippet_id)
    assert snippet["use_count"] == 1


def test_expand_invalid_snippet():
    h = make_handler({"snippet_id": "txs_notexist", "site": "https://example.com"})
    h._handle_expansion_record()
    code, data = h._responses[0]
    assert code == 404


def test_no_port_9222_in_expander():
    # Verify no banned port appears in the server implementation
    result = subprocess.run(
        ["grep", "-n", "9" + "222", "/home/phuc/projects/solace-browser/yinyang_server.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, f"Banned port found in server: {result.stdout}"
