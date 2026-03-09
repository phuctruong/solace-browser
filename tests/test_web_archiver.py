"""Tests for Web Archiver (Task 110). 10 tests."""
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
    ys._ARCHIVES.clear()


def test_archive_create():
    """POST creates archive with war_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/web-archiver/archives", {
        "url": "https://example.com",
        "title": "Example Page",
        "format": "html",
        "size_bytes": 4096,
        "content": "page content here",
    })
    h._handle_archive_create()
    assert h._status == 201
    archive = h._response["archive"]
    assert archive["archive_id"].startswith("war_")
    assert archive["format"] == "html"


def test_archive_url_hashed():
    """archive stores url_hash, not raw url."""
    _reset()
    h = FakeHandler("POST", "/api/v1/web-archiver/archives", {
        "url": "https://secret.example.com/private",
        "title": "Secret",
        "format": "mhtml",
        "size_bytes": 100,
        "content": "content",
    })
    h._handle_archive_create()
    assert h._status == 201
    archive = h._response["archive"]
    assert "url_hash" in archive
    assert "https://secret.example.com/private" not in str(archive)
    expected_hash = hashlib.sha256(b"https://secret.example.com/private").hexdigest()
    assert archive["url_hash"] == expected_hash


def test_archive_invalid_format():
    """POST with unknown format returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/web-archiver/archives", {
        "url": "https://example.com",
        "title": "Test",
        "format": "INVALID_FORMAT",
        "size_bytes": 0,
        "content": "",
    })
    h._handle_archive_create()
    assert h._status == 400


def test_archive_negative_size():
    """POST with negative size_bytes returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/web-archiver/archives", {
        "url": "https://example.com",
        "title": "Test",
        "format": "html",
        "size_bytes": -1,
        "content": "content",
    })
    h._handle_archive_create()
    assert h._status == 400


def test_archive_list():
    """GET returns list of archives."""
    _reset()
    h = FakeHandler("POST", "/api/v1/web-archiver/archives", {
        "url": "https://example.com",
        "title": "Test",
        "format": "pdf",
        "size_bytes": 512,
        "content": "content",
    })
    h._handle_archive_create()
    h2 = FakeHandler("GET", "/api/v1/web-archiver/archives")
    h2._handle_archive_list()
    assert h2._status == 200
    assert "archives" in h2._response
    assert h2._response["total"] == 1


def test_archive_search():
    """GET /search?q=war_ returns matching results."""
    _reset()
    h = FakeHandler("POST", "/api/v1/web-archiver/archives", {
        "url": "https://example.com",
        "title": "Test",
        "format": "screenshot",
        "size_bytes": 8192,
        "content": "content",
    })
    h._handle_archive_create()

    sh = FakeHandler("GET", "/api/v1/web-archiver/archives/search?q=war_")
    sh._handle_archive_search("")
    assert sh._status == 200
    assert sh._response["total"] >= 1


def test_archive_delete():
    """DELETE removes archive."""
    _reset()
    h = FakeHandler("POST", "/api/v1/web-archiver/archives", {
        "url": "https://example.com",
        "title": "Delete me",
        "format": "warc",
        "size_bytes": 2048,
        "content": "content",
    })
    h._handle_archive_create()
    archive_id = h._response["archive"]["archive_id"]

    dh = FakeHandler("DELETE", f"/api/v1/web-archiver/archives/{archive_id}")
    dh._handle_archive_delete(archive_id)
    assert dh._status == 200
    assert dh._response["status"] == "deleted"

    lh = FakeHandler("GET", "/api/v1/web-archiver/archives")
    lh._handle_archive_list()
    assert lh._response["total"] == 0


def test_archive_not_found():
    """DELETE nonexistent archive returns 404."""
    _reset()
    h = FakeHandler("DELETE", "/api/v1/web-archiver/archives/war_notexist")
    h._handle_archive_delete("war_notexist")
    assert h._status == 404


def test_formats_list():
    """GET /formats returns 6 archive formats."""
    h = FakeHandler("GET", "/api/v1/web-archiver/formats")
    h._handle_archive_formats_list()
    assert h._status == 200
    assert len(h._response["formats"]) == 6
    assert "html" in h._response["formats"]
    assert "warc" in h._response["formats"]


def test_no_legacy_debug_port_in_archiver():
    """Grep check: legacy debug port must not appear in this file."""
    banned_port = "92" + "22"  # split to avoid self-matching
    source = pathlib.Path(__file__).read_text()
    assert banned_port not in source
