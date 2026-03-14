# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 101 — Link Preview Cache
Browser: yinyang_server.py routes /api/v1/link-preview/*
"""
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

    def _send_json(self, data, status=200):
        self._status = status
        self._response = data

    def _check_auth(self):
        if not self._auth:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}


def setup_function():
    ys._PREVIEW_CACHE.clear()


def test_store_preview_ok():
    url_hash = "a" * 64
    h = FakeHandler("POST", "/api/v1/link-preview/cache", {
        "url_hash": url_hash,
        "title_hash": "b" * 64,
        "description_hash": "c" * 64,
        "domain_hash": "d" * 64,
    })
    h._handle_preview_cache_store()
    assert h._status == 201
    assert h._response["preview"]["preview_id"].startswith("prv_")
    assert h._response["preview"]["url_hash"] == url_hash
    assert h._response["preview"]["hit_count"] == 0


def test_store_preview_invalid_url_hash():
    h = FakeHandler("POST", "/api/v1/link-preview/cache", {
        "url_hash": "short",
        "title_hash": "b" * 64,
        "description_hash": "c" * 64,
        "domain_hash": "d" * 64,
    })
    h._handle_preview_cache_store()
    assert h._status == 400
    assert "url_hash" in h._response["error"]


def test_store_requires_auth():
    h = FakeHandler("POST", "/api/v1/link-preview/cache", {
        "url_hash": "a" * 64,
        "title_hash": "b" * 64,
        "description_hash": "c" * 64,
        "domain_hash": "d" * 64,
    }, auth=False)
    h._handle_preview_cache_store()
    assert h._status == 401


def test_get_preview_increments_hit_count():
    url_hash = "e" * 64
    h = FakeHandler("POST", "/api/v1/link-preview/cache", {
        "url_hash": url_hash,
        "title_hash": "f" * 64,
        "description_hash": "g" * 64,
        "domain_hash": "h" * 64,
    })
    h._handle_preview_cache_store()

    h2 = FakeHandler("GET", f"/api/v1/link-preview/cache?url_hash={url_hash}")
    h2._handle_preview_cache_get()
    assert h2._status == 200
    assert h2._response["preview"]["hit_count"] == 1

    h3 = FakeHandler("GET", f"/api/v1/link-preview/cache?url_hash={url_hash}")
    h3._handle_preview_cache_get()
    assert h3._response["preview"]["hit_count"] == 2


def test_get_preview_not_found():
    h = FakeHandler("GET", "/api/v1/link-preview/cache?url_hash=" + "z" * 64)
    h._handle_preview_cache_get()
    assert h._status == 404


def test_delete_preview():
    url_hash = "k" * 64
    h = FakeHandler("POST", "/api/v1/link-preview/cache", {
        "url_hash": url_hash,
        "title_hash": "l" * 64,
        "description_hash": "m" * 64,
        "domain_hash": "n" * 64,
    })
    h._handle_preview_cache_store()

    h2 = FakeHandler("DELETE", f"/api/v1/link-preview/cache?url_hash={url_hash}")
    h2._handle_preview_cache_delete()
    assert h2._status == 200
    assert h2._response["status"] == "deleted"


def test_delete_preview_not_found():
    h = FakeHandler("DELETE", "/api/v1/link-preview/cache?url_hash=" + "x" * 64)
    h._handle_preview_cache_delete()
    assert h._status == 404


def test_list_previews():
    url_hash = "o" * 64
    h = FakeHandler("POST", "/api/v1/link-preview/cache", {
        "url_hash": url_hash,
        "title_hash": "p" * 64,
        "description_hash": "q" * 64,
        "domain_hash": "r" * 64,
    })
    h._handle_preview_cache_store()

    h2 = FakeHandler("GET", "/api/v1/link-preview/list")
    h2._handle_preview_list()
    assert h2._status == 200
    assert h2._response["total"] >= 1


def test_flush():
    url_hash = "s" * 64
    h = FakeHandler("POST", "/api/v1/link-preview/cache", {
        "url_hash": url_hash,
        "title_hash": "t" * 64,
        "description_hash": "u" * 64,
        "domain_hash": "v" * 64,
    })
    h._handle_preview_cache_store()

    h2 = FakeHandler("POST", "/api/v1/link-preview/flush")
    h2._handle_preview_flush()
    assert h2._status == 200
    assert h2._response["status"] == "flushed"
    assert len(ys._PREVIEW_CACHE) == 0


def test_stats():
    url_hash = "w" * 64
    h = FakeHandler("POST", "/api/v1/link-preview/cache", {
        "url_hash": url_hash,
        "title_hash": "x" * 64,
        "description_hash": "y" * 64,
        "domain_hash": "0" * 64,
    })
    h._handle_preview_cache_store()

    # Fetch it once to increment hit count
    h2 = FakeHandler("GET", f"/api/v1/link-preview/cache?url_hash={url_hash}")
    h2._handle_preview_cache_get()

    h3 = FakeHandler("GET", "/api/v1/link-preview/stats")
    h3._handle_preview_stats()
    assert h3._status == 200
    assert h3._response["total_entries"] >= 1
    assert h3._response["total_hits"] >= 1
    assert "avg_hits" in h3._response
