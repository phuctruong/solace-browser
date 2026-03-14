# Diagram: 05-solace-runtime-architecture
"""Tests for Task 086 — Download Manager v2."""
import sys
import json

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "a" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
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


def make_handler(body=None):
    h = FakeHandler()
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def setup_function():
    with ys._DOWNLOAD_LOCK:
        ys._DOWNLOAD_QUEUE.clear()
        ys._DOWNLOAD_HISTORY.clear()


def test_download_add():
    h = make_handler({"url_hash": "abc123", "filename_hash": "def456", "file_type": "pdf", "size_bytes": 1024})
    h._handle_downloads_v2_add()
    code, data = h._responses[0]
    assert code == 200
    assert data["download_id"].startswith("dl_")
    assert data["status"] == "queued"


def test_download_add_invalid_type():
    h = make_handler({"url_hash": "abc", "filename_hash": "def", "file_type": "exe", "size_bytes": 0})
    h._handle_downloads_v2_add()
    code, data = h._responses[0]
    assert code == 400
    assert "file_type" in data["error"]


def test_download_add_missing_url_hash():
    h = make_handler({"filename_hash": "def", "file_type": "pdf"})
    h._handle_downloads_v2_add()
    code, data = h._responses[0]
    assert code == 400
    assert "url_hash" in data["error"]


def test_download_queue_list():
    h = make_handler({"url_hash": "abc", "filename_hash": "def", "file_type": "image", "size_bytes": 512})
    h._handle_downloads_v2_add()
    h2 = FakeHandler()
    h2._handle_downloads_v2_queue_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["queue"], list)
    assert data["total"] >= 1


def test_download_remove():
    h = make_handler({"url_hash": "rm1", "filename_hash": "rm2", "file_type": "video", "size_bytes": 0})
    h._handle_downloads_v2_add()
    dl_id = h._responses[0][1]["download_id"]
    h2 = FakeHandler()
    h2._handle_downloads_v2_remove(dl_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["download_id"] == dl_id
    with ys._DOWNLOAD_LOCK:
        ids = [d["download_id"] for d in ys._DOWNLOAD_QUEUE]
    assert dl_id not in ids


def test_download_remove_not_found():
    h = FakeHandler()
    h._handle_downloads_v2_remove("dl_notexist")
    code, data = h._responses[0]
    assert code == 404


def test_download_complete():
    h = make_handler({"url_hash": "cmp1", "filename_hash": "cmp2", "file_type": "audio", "size_bytes": 2048})
    h._handle_downloads_v2_add()
    dl_id = h._responses[0][1]["download_id"]
    h2 = FakeHandler()
    h2._handle_downloads_v2_complete(dl_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["status"] == "completed"
    with ys._DOWNLOAD_LOCK:
        ids = [d["download_id"] for d in ys._DOWNLOAD_QUEUE]
    assert dl_id not in ids
    with ys._DOWNLOAD_LOCK:
        hist_ids = [d["download_id"] for d in ys._DOWNLOAD_HISTORY]
    assert dl_id in hist_ids


def test_download_complete_not_found():
    h = FakeHandler()
    h._handle_downloads_v2_complete("dl_ghost")
    code, data = h._responses[0]
    assert code == 404


def test_download_history():
    h = make_handler({"url_hash": "hist1", "filename_hash": "hist2", "file_type": "archive", "size_bytes": 0})
    h._handle_downloads_v2_add()
    dl_id = h._responses[0][1]["download_id"]
    h2 = FakeHandler()
    h2._handle_downloads_v2_complete(dl_id)
    h3 = FakeHandler()
    h3._handle_downloads_v2_history()
    code, data = h3._responses[0]
    assert code == 200
    assert isinstance(data["history"], list)
    assert data["total"] >= 1


def test_download_file_types():
    h = FakeHandler()
    h._handle_downloads_v2_file_types()
    code, data = h._responses[0]
    assert code == 200
    assert "pdf" in data["file_types"]
    assert "queued" in data["statuses"]


def test_no_port_9222_in_server():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found — BANNED"
