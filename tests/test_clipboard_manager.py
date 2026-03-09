"""Tests for Clipboard Manager (Task 106). 10 tests."""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
import json
import hashlib
from io import BytesIO


VALID_TOKEN = hashlib.sha256(b"test-token").hexdigest()


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
    ys._CLIPBOARD_ENTRIES.clear()


def test_clipboard_save():
    """POST saves entry with clp_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/clipboard/entries", {
        "content_type": "text",
        "content_hash": "abc123",
        "source_url_hash": "url_hash",
        "byte_length": 42,
    })
    h._handle_clipboard_save()
    assert h._status == 201
    entry = h._response["entry"]
    assert entry["entry_id"].startswith("clp_")
    assert entry["content_type"] == "text"


def test_clipboard_invalid_content_type():
    """POST with invalid content_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/clipboard/entries", {
        "content_type": "INVALID",
        "content_hash": "abc",
        "source_url_hash": "url",
        "byte_length": 10,
    })
    h._handle_clipboard_save()
    assert h._status == 400


def test_clipboard_list():
    """GET returns entries list newest first."""
    _reset()
    # Save two entries
    for ct in ["text", "url"]:
        h = FakeHandler("POST", "/api/v1/clipboard/entries", {
            "content_type": ct,
            "content_hash": f"hash_{ct}",
            "source_url_hash": "url",
            "byte_length": 10,
        })
        h._handle_clipboard_save()
    h = FakeHandler("GET", "/api/v1/clipboard/entries")
    h._handle_clipboard_list()
    assert h._status == 200
    assert "entries" in h._response
    assert h._response["total"] == 2
    # Newest first: last saved should be first
    assert h._response["entries"][0]["content_type"] == "url"


def test_clipboard_delete():
    """DELETE removes entry and returns 200."""
    _reset()
    h = FakeHandler("POST", "/api/v1/clipboard/entries", {
        "content_type": "code",
        "content_hash": "del_hash",
        "source_url_hash": "src",
        "byte_length": 5,
    })
    h._handle_clipboard_save()
    entry_id = h._response["entry"]["entry_id"]

    dh = FakeHandler("DELETE", f"/api/v1/clipboard/entries/{entry_id}")
    dh._handle_clipboard_delete(entry_id)
    assert dh._status == 200
    assert dh._response["status"] == "deleted"


def test_clipboard_delete_not_found():
    """DELETE unknown entry returns 404."""
    _reset()
    h = FakeHandler("DELETE", "/api/v1/clipboard/entries/clp_nonexistent")
    h._handle_clipboard_delete("clp_nonexistent")
    assert h._status == 404


def test_clipboard_clear():
    """POST /clear deletes all entries."""
    _reset()
    for _ in range(3):
        h = FakeHandler("POST", "/api/v1/clipboard/entries", {
            "content_type": "text",
            "content_hash": "h",
            "source_url_hash": "s",
            "byte_length": 1,
        })
        h._handle_clipboard_save()
    h = FakeHandler("POST", "/api/v1/clipboard/clear")
    h._handle_clipboard_clear()
    assert h._status == 200
    assert h._response["deleted_count"] == 3
    assert len(ys._CLIPBOARD_ENTRIES) == 0


def test_clipboard_content_types():
    """GET /content-types returns 7 types."""
    h = FakeHandler("GET", "/api/v1/clipboard/content-types")
    h._handle_clipboard_content_types()
    assert h._status == 200
    assert len(h._response["content_types"]) == 7


def test_clipboard_unauth():
    """POST without auth returns 401."""
    _reset()
    h = FakeHandler("POST", "/api/v1/clipboard/entries", {
        "content_type": "text",
        "content_hash": "x",
        "source_url_hash": "y",
        "byte_length": 0,
    }, auth=False)
    h._handle_clipboard_save()
    assert h._status == 401


def test_clipboard_invalid_byte_length():
    """POST with negative byte_length returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/clipboard/entries", {
        "content_type": "text",
        "content_hash": "x",
        "source_url_hash": "y",
        "byte_length": -1,
    })
    h._handle_clipboard_save()
    assert h._status == 400


def test_clipboard_list_empty():
    """GET on empty store returns empty list."""
    _reset()
    h = FakeHandler("GET", "/api/v1/clipboard/entries")
    h._handle_clipboard_list()
    assert h._status == 200
    assert h._response["entries"] == []
    assert h._response["total"] == 0
