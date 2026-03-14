# Diagram: 05-solace-runtime-architecture
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
    with ys._RTE_LOCK:
        ys._RTE_RESOURCE_ENTRIES.clear()


def test_entry_create():
    h = FakeHandler()
    h._handle_resource_timing_create({
        "resource_type": "script",
        "url": "https://ex.com/app.js",
        "page_url": "https://ex.com",
        "duration_ms": "12.5",
        "transfer_size_bytes": 2048,
        "cache_hit": False,
    })
    assert h._response_code == 201
    assert h._response_body["entry_id"].startswith("rte_")


def test_entry_url_hashed():
    url = "https://example.com/app.js"
    page_url = "https://example.com"
    h = FakeHandler()
    h._handle_resource_timing_create({
        "resource_type": "fetch",
        "url": url,
        "page_url": page_url,
        "duration_ms": "10",
        "transfer_size_bytes": 1,
        "cache_hit": False,
    })
    assert h._response_body["url_hash"] == hashlib.sha256(url.encode("utf-8")).hexdigest()
    assert h._response_body["page_url_hash"] == hashlib.sha256(page_url.encode("utf-8")).hexdigest()
    assert "url" not in h._response_body


def test_entry_invalid_type():
    h = FakeHandler()
    h._handle_resource_timing_create({
        "resource_type": "bad",
        "url": "https://ex.com",
        "page_url": "https://ex.com",
        "duration_ms": "1",
        "transfer_size_bytes": 1,
        "cache_hit": False,
    })
    assert h._response_code == 400
    assert "resource_type" in h._response_body["error"]


def test_entry_negative_duration():
    h = FakeHandler()
    h._handle_resource_timing_create({
        "resource_type": "image",
        "url": "https://ex.com/img.png",
        "page_url": "https://ex.com",
        "duration_ms": "-1",
        "transfer_size_bytes": 1,
        "cache_hit": False,
    })
    assert h._response_code == 400
    assert "duration_ms" in h._response_body["error"]


def test_entry_negative_transfer():
    h = FakeHandler()
    h._handle_resource_timing_create({
        "resource_type": "font",
        "url": "https://ex.com/font.woff2",
        "page_url": "https://ex.com",
        "duration_ms": "1",
        "transfer_size_bytes": -1,
        "cache_hit": False,
    })
    assert h._response_code == 400
    assert "transfer_size_bytes" in h._response_body["error"]


def test_entry_list_route():
    creator = FakeHandler(method="POST", path="/api/v1/resource-timing/entries", body={
        "resource_type": "stylesheet",
        "url": "https://ex.com/app.css",
        "page_url": "https://ex.com",
        "duration_ms": "4.25",
        "transfer_size_bytes": 512,
        "cache_hit": False,
    })
    creator.do_POST()
    reader = FakeHandler(method="GET", path="/api/v1/resource-timing/entries")
    reader.do_GET()
    assert reader._response_code == 200
    assert reader._response_body["total"] == 1


def test_entry_delete_route():
    creator = FakeHandler()
    creator._handle_resource_timing_create({
        "resource_type": "iframe",
        "url": "https://delete.example/frame",
        "page_url": "https://delete.example",
        "duration_ms": "2",
        "transfer_size_bytes": 0,
        "cache_hit": True,
    })
    entry_id = creator._response_body["entry_id"]
    deleter = FakeHandler(method="DELETE", path=f"/api/v1/resource-timing/entries/{entry_id}")
    deleter.do_DELETE()
    assert deleter._response_code == 200
    assert deleter._response_body["entry_id"] == entry_id


def test_entry_not_found():
    h = FakeHandler()
    h._handle_resource_timing_delete("rte_missing")
    assert h._response_code == 404


def test_resource_stats():
    first = FakeHandler()
    first._handle_resource_timing_create({
        "resource_type": "script",
        "url": "https://one.example/app.js",
        "page_url": "https://one.example",
        "duration_ms": "10",
        "transfer_size_bytes": 100,
        "cache_hit": False,
    })
    second = FakeHandler()
    second._handle_resource_timing_create({
        "resource_type": "script",
        "url": "https://two.example/app.js",
        "page_url": "https://two.example",
        "duration_ms": "20",
        "transfer_size_bytes": 0,
        "cache_hit": True,
    })
    stats = FakeHandler(method="GET", path="/api/v1/resource-timing/stats")
    stats.do_GET()
    assert stats._response_code == 200
    assert stats._response_body["cache_hit_rate"] == "0.50"
    assert stats._response_body["avg_duration_ms"] == "15.00"


def test_banned_debug_port_absent_in_resource_timing_files():
    banned = "922" + "2"
    for rel_path in [
        "yinyang_server.py",
        "web/resource-timing-tracker.html",
        "web/css/resource-timing-tracker.css",
        "web/js/resource-timing-tracker.js",
    ]:
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert banned not in content
