"""Tests for Task 166v2 — Resource Timing Tracker /records endpoints."""
import hashlib
import json
import pathlib
import sys
from io import BytesIO

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = "d" * 64


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
    with ys._RESOURCE_TIMING_LOCK:
        ys._RESOURCE_TIMING_RECORDS.clear()


def test_record_create():
    h = FakeHandler()
    h._handle_rtt2_create({
        "resource_type": "script",
        "page_url": "https://ex.com",
        "resource_url": "https://cdn.ex.com/app.js",
        "duration_ms": 150,
        "transfer_size_bytes": 45000,
        "is_cached": False,
    })
    assert h._response_code == 201
    assert h._response_body["record_id"].startswith("rtt_")


def test_record_url_hashed():
    page_url = "https://example.com/page"
    resource_url = "https://cdn.example.com/main.js"
    h = FakeHandler()
    h._handle_rtt2_create({
        "resource_type": "script",
        "page_url": page_url,
        "resource_url": resource_url,
        "duration_ms": 100,
        "transfer_size_bytes": 20000,
        "is_cached": False,
    })
    assert h._response_body["page_url_hash"] == hashlib.sha256(page_url.encode("utf-8")).hexdigest()
    assert h._response_body["resource_url_hash"] == hashlib.sha256(resource_url.encode("utf-8")).hexdigest()
    assert "page_url" not in h._response_body
    assert "resource_url" not in h._response_body


def test_record_invalid_type():
    h = FakeHandler()
    h._handle_rtt2_create({
        "resource_type": "video",
        "page_url": "https://ex.com",
        "resource_url": "https://ex.com/vid.mp4",
        "duration_ms": 200,
        "transfer_size_bytes": 1000,
        "is_cached": False,
    })
    assert h._response_code == 400
    assert "resource_type" in h._response_body["error"]


def test_record_negative_duration():
    h = FakeHandler()
    h._handle_rtt2_create({
        "resource_type": "image",
        "page_url": "https://ex.com",
        "resource_url": "https://ex.com/img.png",
        "duration_ms": -1,
        "transfer_size_bytes": 1000,
        "is_cached": False,
    })
    assert h._response_code == 400
    assert "duration_ms" in h._response_body["error"]


def test_record_negative_transfer():
    h = FakeHandler()
    h._handle_rtt2_create({
        "resource_type": "font",
        "page_url": "https://ex.com",
        "resource_url": "https://ex.com/font.woff2",
        "duration_ms": 50,
        "transfer_size_bytes": -1,
        "is_cached": False,
    })
    assert h._response_code == 400
    assert "transfer_size_bytes" in h._response_body["error"]


def test_record_cached_flag():
    h = FakeHandler()
    h._handle_rtt2_create({
        "resource_type": "stylesheet",
        "page_url": "https://ex.com",
        "resource_url": "https://ex.com/style.css",
        "duration_ms": 5,
        "transfer_size_bytes": 0,
        "is_cached": True,
    })
    assert h._response_code == 201
    assert h._response_body["is_cached"] is True


def test_record_list():
    creator = FakeHandler(method="POST", path="/api/v1/resource-timing/records", body={
        "resource_type": "fetch",
        "page_url": "https://example.com",
        "resource_url": "https://api.example.com/data",
        "duration_ms": 300,
        "transfer_size_bytes": 5000,
        "is_cached": False,
    })
    creator.do_POST()
    reader = FakeHandler(method="GET", path="/api/v1/resource-timing/records")
    reader.do_GET()
    assert reader._response_code == 200
    assert reader._response_body["total"] == 1
    assert reader._response_body["records"][0]["record_id"].startswith("rtt_")


def test_record_delete():
    creator = FakeHandler()
    creator._handle_rtt2_create({
        "resource_type": "xhr",
        "page_url": "https://delete.example",
        "resource_url": "https://api.delete.example/data",
        "duration_ms": 100,
        "transfer_size_bytes": 2000,
        "is_cached": False,
    })
    record_id = creator._response_body["record_id"]
    deleter = FakeHandler(method="DELETE", path=f"/api/v1/resource-timing/records/{record_id}")
    deleter.do_DELETE()
    assert deleter._response_code == 200
    assert deleter._response_body["record_id"] == record_id


def test_record_not_found():
    h = FakeHandler()
    h._handle_rtt2_delete("rtt_missing")
    assert h._response_code == 404


def test_resource_stats():
    first = FakeHandler()
    first._handle_rtt2_create({
        "resource_type": "document",
        "page_url": "https://one.example",
        "resource_url": "https://one.example/",
        "duration_ms": 500,
        "transfer_size_bytes": 15000,
        "is_cached": False,
    })
    second = FakeHandler()
    second._handle_rtt2_create({
        "resource_type": "other",
        "page_url": "https://two.example",
        "resource_url": "https://two.example/data",
        "duration_ms": 100,
        "transfer_size_bytes": 0,
        "is_cached": True,
    })
    stats = FakeHandler()
    stats._handle_rtt2_stats()
    assert stats._response_code == 200
    body = stats._response_body
    assert body["cached_count"] == 1
    assert "cache_rate" in body
    assert "avg_duration_ms" in body


def test_no_port_9222_in_resource_timing():
    banned = "922" + "2"
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert banned not in content
