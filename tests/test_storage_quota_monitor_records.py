"""Tests for Task 163v2 — Storage Quota Monitor /records endpoints."""
import hashlib
import json
import pathlib
import sys
from io import BytesIO

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = "a" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method="GET", path="/", body=None, auth=True):
        self.command = method
        self.path = path
        raw_body = json.dumps(body).encode("utf-8") if body is not None else b""
        self.headers = {
            "Content-Length": str(len(raw_body)),
            "Authorization": f"Bearer {VALID_TOKEN}" if auth else "",
        }
        self.rfile = BytesIO(raw_body)
        self.wfile = BytesIO()
        self.server = type("Server", (), {"session_token_sha256": VALID_TOKEN})()
        self._response_code = None
        self._response_body = None

    def send_response(self, code):
        self._response_code = code

    def send_header(self, *_args):
        pass

    def end_headers(self):
        pass

    def _send_json(self, data, status=200):
        self._response_code = status
        self._response_body = data

    def log_message(self, *_args):
        pass


def setup_function():
    with ys._STORAGE_QUOTA_LOCK:
        ys._STORAGE_QUOTA_RECORDS.clear()


def test_record_create():
    h = FakeHandler()
    h._handle_sqm2_create({
        "storage_type": "indexeddb",
        "url": "https://ex.com",
        "used_bytes": 1024,
        "quota_bytes": 10000000,
    })
    assert h._response_code == 201
    assert h._response_body["record_id"].startswith("sqm_")


def test_record_url_hashed():
    url = "https://example.com/app"
    h = FakeHandler()
    h._handle_sqm2_create({
        "storage_type": "localstorage",
        "url": url,
        "used_bytes": 500,
        "quota_bytes": 2000,
    })
    assert h._response_body["url_hash"] == hashlib.sha256(url.encode("utf-8")).hexdigest()
    assert "url" not in h._response_body


def test_record_invalid_type():
    h = FakeHandler()
    h._handle_sqm2_create({
        "storage_type": "bad-type",
        "url": "https://ex.com",
        "used_bytes": 1,
        "quota_bytes": 10,
    })
    assert h._response_code == 400
    assert "storage_type" in h._response_body["error"]


def test_record_negative_used():
    h = FakeHandler()
    h._handle_sqm2_create({
        "storage_type": "cookies",
        "url": "https://ex.com",
        "used_bytes": -1,
        "quota_bytes": 10,
    })
    assert h._response_code == 400
    assert "used_bytes" in h._response_body["error"]


def test_record_zero_quota():
    h = FakeHandler()
    h._handle_sqm2_create({
        "storage_type": "cache_api",
        "url": "https://ex.com",
        "used_bytes": 1,
        "quota_bytes": 0,
    })
    assert h._response_code == 400
    assert "quota_bytes" in h._response_body["error"]


def test_record_near_limit():
    h = FakeHandler()
    h._handle_sqm2_create({
        "storage_type": "opfs",
        "url": "https://ex.com",
        "used_bytes": 900,
        "quota_bytes": 1000,
    })
    assert h._response_code == 201
    assert h._response_body["is_near_limit"] is True


def test_record_list():
    creator = FakeHandler(method="POST", path="/api/v1/storage-quota/records", body={
        "storage_type": "sessionstorage",
        "url": "https://example.com",
        "used_bytes": 25,
        "quota_bytes": 100,
    })
    creator.do_POST()
    reader = FakeHandler(method="GET", path="/api/v1/storage-quota/records")
    reader.do_GET()
    assert reader._response_code == 200
    assert reader._response_body["total"] == 1
    assert reader._response_body["records"][0]["record_id"].startswith("sqm_")


def test_record_delete():
    creator = FakeHandler()
    creator._handle_sqm2_create({
        "storage_type": "websql",
        "url": "https://delete.example",
        "used_bytes": 10,
        "quota_bytes": 100,
    })
    record_id = creator._response_body["record_id"]
    deleter = FakeHandler(method="DELETE", path=f"/api/v1/storage-quota/records/{record_id}")
    deleter.do_DELETE()
    assert deleter._response_code == 200
    assert deleter._response_body["record_id"] == record_id


def test_quota_stats():
    first = FakeHandler()
    first._handle_sqm2_create({
        "storage_type": "localstorage",
        "url": "https://one.example",
        "used_bytes": 25,
        "quota_bytes": 100,
    })
    second = FakeHandler()
    second._handle_sqm2_create({
        "storage_type": "indexeddb",
        "url": "https://two.example",
        "used_bytes": 50,
        "quota_bytes": 100,
    })
    stats = FakeHandler()
    stats._handle_sqm2_stats()
    assert stats._response_code == 200
    body = stats._response_body
    assert "avg_usage_pct" in body
    assert "." in body["avg_usage_pct"]
    assert body["total_records"] == 2


def test_no_port_9222_in_quota():
    banned = "922" + "2"
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert banned not in content
