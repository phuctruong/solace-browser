"""
Tests for Task 098 — Page Diff Tracker
Browser: yinyang_server.py routes /api/v1/page-diff
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


def setup_function():
    ys._PAGE_SNAPSHOTS.clear()


def _make_snapshot(page_hash="a" * 64, content_hash="b" * 64, title_hash="c" * 64, word_count=100):
    h = FakeHandler("POST", "/api/v1/page-diff/snapshots", {
        "page_hash": page_hash,
        "content_hash": content_hash,
        "title_hash": title_hash,
        "word_count": word_count,
    })
    h._handle_diff_snapshot_create()
    return h


def test_snapshot_create():
    h = _make_snapshot()
    assert h._status == 201
    assert h._response["snapshot"]["snapshot_id"].startswith("pss_")
    assert h._response["status"] == "created"


def test_snapshot_url_hashed():
    h = _make_snapshot(page_hash="d" * 64)
    assert h._status == 201
    assert "page_hash" in h._response["snapshot"]
    assert h._response["snapshot"]["page_hash"] == "d" * 64


def test_snapshot_list():
    _make_snapshot(page_hash="e" * 64)
    h = FakeHandler("GET", "/api/v1/page-diff/snapshots")
    h._handle_diff_snapshot_list()
    assert h._status == 200
    assert isinstance(h._response["snapshots"], list)
    assert h._response["total"] >= 1


def test_snapshot_by_page():
    unique_hash = "f" * 64
    _make_snapshot(page_hash=unique_hash)
    h = FakeHandler("GET", f"/api/v1/page-diff/snapshots/by-page?page_hash={unique_hash}")
    h._handle_diff_snapshot_by_page()
    assert h._status == 200
    assert h._response["total"] >= 1
    assert all(s["page_hash"] == unique_hash for s in h._response["snapshots"])


def test_snapshot_delete():
    h1 = _make_snapshot(page_hash="g" * 64)
    snapshot_id = h1._response["snapshot"]["snapshot_id"]

    h2 = FakeHandler("DELETE", f"/api/v1/page-diff/snapshots/{snapshot_id}")
    h2._handle_diff_snapshot_delete(snapshot_id)
    assert h2._status == 200
    assert h2._response["status"] == "deleted"
    assert h2._response["snapshot_id"] == snapshot_id


def test_snapshot_not_found():
    h = FakeHandler("DELETE", "/api/v1/page-diff/snapshots/pss_nonexistent")
    h._handle_diff_snapshot_delete("pss_nonexistent")
    assert h._status == 404


def test_compare_identical():
    h1 = _make_snapshot(content_hash="h" * 64, word_count=200)
    h2 = _make_snapshot(content_hash="h" * 64, word_count=200)
    id_a = h1._response["snapshot"]["snapshot_id"]
    id_b = h2._response["snapshot"]["snapshot_id"]

    h3 = FakeHandler("POST", "/api/v1/page-diff/compare", {
        "snapshot_id_a": id_a,
        "snapshot_id_b": id_b,
    })
    h3._handle_diff_compare()
    assert h3._status == 200
    assert h3._response["change_type"] == "unchanged"
    assert h3._response["change_count"] == 0


def test_compare_different():
    h1 = _make_snapshot(content_hash="i" * 64, word_count=100)
    h2 = _make_snapshot(content_hash="j" * 64, word_count=250)
    id_a = h1._response["snapshot"]["snapshot_id"]
    id_b = h2._response["snapshot"]["snapshot_id"]

    h3 = FakeHandler("POST", "/api/v1/page-diff/compare", {
        "snapshot_id_a": id_a,
        "snapshot_id_b": id_b,
    })
    h3._handle_diff_compare()
    assert h3._status == 200
    assert h3._response["change_type"] == "modified"
    assert h3._response["change_count"] == 150
    assert "change_summary_hash" in h3._response


def test_compare_not_found():
    h = FakeHandler("POST", "/api/v1/page-diff/compare", {
        "snapshot_id_a": "pss_nonexistent_a",
        "snapshot_id_b": "pss_nonexistent_b",
    })
    h._handle_diff_compare()
    assert h._status == 404


def test_no_port_9222_in_diff():
    src = (REPO_ROOT / "yinyang_server.py").read_text()
    diff_section_start = src.find("Task 098")
    diff_section_end = src.find("Task 099")
    diff_section = src[diff_section_start:diff_section_end] if diff_section_start != -1 else ""
    assert "9222" not in diff_section
