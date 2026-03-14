# Diagram: 05-solace-runtime-architecture
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
    with ys._SQM_STORAGE_LOCK:
        ys._SQM_STORAGE_SNAPSHOTS.clear()


def test_snapshot_create():
    h = FakeHandler(body={
        "storage_type": "localStorage",
        "url": "https://ex.com",
        "used_bytes": 1024,
        "quota_bytes": 10000000,
    })
    h._handle_storage_quota_create({
        "storage_type": "localStorage",
        "url": "https://ex.com",
        "used_bytes": 1024,
        "quota_bytes": 10000000,
    })
    assert h._response_code == 201
    assert h._response_body["snapshot_id"].startswith("sqm_")


def test_snapshot_url_hashed():
    url = "https://example.com/app"
    h = FakeHandler()
    h._handle_storage_quota_create({
        "storage_type": "indexedDB",
        "url": url,
        "used_bytes": 500,
        "quota_bytes": 2000,
    })
    assert h._response_body["url_hash"] == hashlib.sha256(url.encode("utf-8")).hexdigest()
    assert "url" not in h._response_body


def test_snapshot_invalid_type():
    h = FakeHandler()
    h._handle_storage_quota_create({
        "storage_type": "bad-type",
        "url": "https://ex.com",
        "used_bytes": 1,
        "quota_bytes": 10,
    })
    assert h._response_code == 400
    assert "storage_type" in h._response_body["error"]


def test_snapshot_negative_used():
    h = FakeHandler()
    h._handle_storage_quota_create({
        "storage_type": "cacheAPI",
        "url": "https://ex.com",
        "used_bytes": -1,
        "quota_bytes": 10,
    })
    assert h._response_code == 400
    assert "used_bytes" in h._response_body["error"]


def test_snapshot_zero_quota():
    h = FakeHandler()
    h._handle_storage_quota_create({
        "storage_type": "cookies",
        "url": "https://ex.com",
        "used_bytes": 1,
        "quota_bytes": 0,
    })
    assert h._response_code == 400
    assert "quota_bytes" in h._response_body["error"]


def test_snapshot_usage_pct_computed():
    h = FakeHandler()
    h._handle_storage_quota_create({
        "storage_type": "serviceWorker",
        "url": "https://ex.com",
        "used_bytes": 125,
        "quota_bytes": 1000,
    })
    assert h._response_code == 201
    assert h._response_body["usage_pct"] == "12.50"


def test_snapshot_list_route():
    creator = FakeHandler(method="POST", path="/api/v1/storage-quota/snapshots", body={
        "storage_type": "other",
        "url": "https://example.com",
        "used_bytes": 25,
        "quota_bytes": 100,
    })
    creator.do_POST()
    reader = FakeHandler(method="GET", path="/api/v1/storage-quota/snapshots")
    reader.do_GET()
    assert reader._response_code == 200
    assert reader._response_body["total"] == 1
    assert reader._response_body["snapshots"][0]["snapshot_id"].startswith("sqm_")


def test_snapshot_delete_route():
    creator = FakeHandler()
    creator._handle_storage_quota_create({
        "storage_type": "sessionStorage",
        "url": "https://delete.example",
        "used_bytes": 10,
        "quota_bytes": 100,
    })
    snapshot_id = creator._response_body["snapshot_id"]
    deleter = FakeHandler(method="DELETE", path=f"/api/v1/storage-quota/snapshots/{snapshot_id}")
    deleter.do_DELETE()
    assert deleter._response_code == 200
    assert deleter._response_body["snapshot_id"] == snapshot_id


def test_storage_stats():
    first = FakeHandler()
    first._handle_storage_quota_create({
        "storage_type": "localStorage",
        "url": "https://one.example",
        "used_bytes": 25,
        "quota_bytes": 100,
    })
    second = FakeHandler()
    second._handle_storage_quota_create({
        "storage_type": "indexedDB",
        "url": "https://two.example",
        "used_bytes": 50,
        "quota_bytes": 100,
    })
    stats = FakeHandler(method="GET", path="/api/v1/storage-quota/stats")
    stats.do_GET()
    assert stats._response_code == 200
    assert stats._response_body["avg_usage_pct"] == "37.50"
    assert stats._response_body["max_usage_pct"] == "50.00"


def test_banned_debug_port_absent_in_storage_quota_files():
    banned = "922" + "2"
    for rel_path in [
        "yinyang_server.py",
        "web/storage-quota-monitor.html",
        "web/css/storage-quota-monitor.css",
        "web/js/storage-quota-monitor.js",
    ]:
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert banned not in content
