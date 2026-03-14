# Diagram: 05-solace-runtime-architecture
"""Tests for Task 095 — Code Snippet Saver."""
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
        self.path = ""
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


def make_handler(body=None, path=""):
    h = FakeHandler()
    h.path = path
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def setup_function():
    with ys._SNIPPET_LOCK:
        ys._SNIPPETS.clear()


def test_snippet_save():
    code_hash = hashlib.sha256(b"print('hello')").hexdigest()
    desc_hash = hashlib.sha256(b"Hello world").hexdigest()
    h = make_handler({
        "language": "python",
        "code_hash": code_hash,
        "description_hash": desc_hash,
        "tags": ["python", "basic"],
    })
    h._handle_snippet_save()
    assert len(h._responses) == 1
    code, data = h._responses[0]
    assert code == 201
    assert data["snippet"]["snippet_id"].startswith("snp_")
    assert data["snippet"]["language"] == "python"


def test_snippet_code_hashed():
    code_hash = hashlib.sha256(b"secret code").hexdigest()
    h = make_handler({
        "language": "bash",
        "code_hash": code_hash,
        "description_hash": hashlib.sha256(b"desc").hexdigest(),
    })
    h._handle_snippet_save()
    code, data = h._responses[0]
    assert code == 201
    snippet = data["snippet"]
    assert "code_hash" in snippet
    assert snippet["code_hash"] == code_hash
    # raw code must NOT be stored
    assert "code" not in snippet


def test_snippet_invalid_language():
    h = make_handler({
        "language": "cobol",
        "code_hash": hashlib.sha256(b"x").hexdigest(),
        "description_hash": hashlib.sha256(b"d").hexdigest(),
    })
    h._handle_snippet_save()
    code, data = h._responses[0]
    assert code == 400
    assert "language" in data["error"]


def test_snippet_list():
    code_hash = hashlib.sha256(b"list code").hexdigest()
    desc_hash = hashlib.sha256(b"list desc").hexdigest()
    h = make_handler({"language": "go", "code_hash": code_hash, "description_hash": desc_hash})
    h._handle_snippet_save()

    h2 = FakeHandler()
    h2._handle_snippet_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["snippets"], list)
    assert data["total"] >= 1


def test_snippet_by_language():
    code_hash = hashlib.sha256(b"rust code").hexdigest()
    desc_hash = hashlib.sha256(b"rust desc").hexdigest()
    h = make_handler({"language": "rust", "code_hash": code_hash, "description_hash": desc_hash})
    h._handle_snippet_save()

    h2 = FakeHandler()
    h2.path = "/api/v1/snippets/by-language?language=rust"
    h2._handle_snippet_by_language()
    code, data = h2._responses[0]
    assert code == 200
    assert all(s["language"] == "rust" for s in data["snippets"])
    assert data["total"] >= 1


def test_snippet_delete():
    code_hash = hashlib.sha256(b"del code").hexdigest()
    desc_hash = hashlib.sha256(b"del desc").hexdigest()
    h = make_handler({"language": "sql", "code_hash": code_hash, "description_hash": desc_hash})
    h._handle_snippet_save()
    snippet_id = h._responses[0][1]["snippet"]["snippet_id"]

    h2 = make_handler()
    h2._handle_snippet_delete(snippet_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["snippet_id"] == snippet_id

    with ys._SNIPPET_LOCK:
        ids = [s["snippet_id"] for s in ys._SNIPPETS]
    assert snippet_id not in ids


def test_snippet_not_found():
    h = make_handler()
    h._handle_snippet_delete("snp_notexist")
    code, data = h._responses[0]
    assert code == 404


def test_snippet_tags_limit():
    tags = [str(i) for i in range(11)]  # 11 tags — over limit
    h = make_handler({
        "language": "python",
        "code_hash": hashlib.sha256(b"x").hexdigest(),
        "description_hash": hashlib.sha256(b"d").hexdigest(),
        "tags": tags,
    })
    h._handle_snippet_save()
    code, data = h._responses[0]
    assert code == 400
    assert "10" in data["error"] or "max" in data["error"].lower()


def test_snippet_languages():
    h = FakeHandler()
    h._handle_snippet_languages()
    code, data = h._responses[0]
    assert code == 200
    assert len(data["languages"]) == 16
    assert "python" in data["languages"]
    assert "rust" in data["languages"]
    assert "other" in data["languages"]


def test_no_port_9222_in_snippets():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found in yinyang_server.py — BANNED"
