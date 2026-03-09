"""Tests for Task 133 — Video Downloader Tracker. 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-133").hexdigest()


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
    with ys._VIDEO_LOCK:
        ys._VIDEO_DOWNLOADS.clear()


def _make_download(**kwargs):
    base = {
        "url": "https://example.com/video.mp4",
        "title": "Test Video",
        "quality": "1080p",
        "format": "mp4",
        "status": "queued",
        "file_size_bytes": 1024000,
        "duration_seconds": 120,
    }
    base.update(kwargs)
    return base


def test_download_create():
    """POST creates download with vdl_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/video-tracker/downloads", _make_download())
    h._handle_vdt_create()
    assert h._status == 201
    d = h._response["download"]
    assert d["download_id"].startswith("vdl_")


def test_download_url_hashed():
    """POST stores url_hash, no raw URL."""
    _reset()
    url = "https://secret.com/video.mp4"
    h = FakeHandler("POST", "/api/v1/video-tracker/downloads", _make_download(url=url))
    h._handle_vdt_create()
    assert h._status == 201
    d = h._response["download"]
    assert "url_hash" in d
    assert d["url_hash"] == hashlib.sha256(url.encode()).hexdigest()
    assert "url" not in d


def test_download_invalid_quality():
    """POST with unknown quality returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/video-tracker/downloads", _make_download(quality="8K"))
    h._handle_vdt_create()
    assert h._status == 400


def test_download_invalid_format():
    """POST with unknown format returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/video-tracker/downloads", _make_download(format="mpeg"))
    h._handle_vdt_create()
    assert h._status == 400


def test_download_invalid_status():
    """POST with unknown status returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/video-tracker/downloads", _make_download(status="unknown"))
    h._handle_vdt_create()
    assert h._status == 400


def test_download_negative_size():
    """POST with file_size_bytes=-1 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/video-tracker/downloads", _make_download(file_size_bytes=-1))
    h._handle_vdt_create()
    assert h._status == 400


def test_download_list():
    """GET returns list of downloads."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/video-tracker/downloads", _make_download())
    h_create._handle_vdt_create()
    h = FakeHandler("GET", "/api/v1/video-tracker/downloads")
    h._handle_vdt_list()
    assert h._status == 200
    assert isinstance(h._response["downloads"], list)
    assert h._response["total"] >= 1


def test_download_delete():
    """DELETE removes the download record."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/video-tracker/downloads", _make_download())
    h_create._handle_vdt_create()
    dl_id = h_create._response["download"]["download_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/video-tracker/downloads/{dl_id}")
    h_del._handle_vdt_delete(dl_id)
    assert h_del._status == 200
    with ys._VIDEO_LOCK:
        ids = [d["download_id"] for d in ys._VIDEO_DOWNLOADS]
    assert dl_id not in ids


def test_download_stats():
    """GET /stats returns total_size_bytes."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/video-tracker/downloads", _make_download(file_size_bytes=5000))
    h_create._handle_vdt_create()
    h = FakeHandler("GET", "/api/v1/video-tracker/stats")
    h._handle_vdt_stats()
    assert h._status == 200
    assert "total_size_bytes" in h._response
    assert h._response["total_size_bytes"] >= 5000


def test_no_port_9222_in_video():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
