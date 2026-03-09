"""
Tests for Task 064 — Media Downloader
Browser: yinyang_server.py routes /api/v1/media/*
"""
import json
import sys

sys.path.insert(0, "/home/phuc/projects/solace-browser")

TOKEN = "test-token-sha256"


def _make_handler(body=None, auth=True):
    import yinyang_server as ys

    class FakeHandler(ys.YinyangHandler):
        def __init__(self):
            self._token = TOKEN
            self._responses = []
            self._body = json.dumps(body).encode() if body else b"{}"

        def _read_json_body(self):
            return json.loads(self._body)

        def _send_json(self, data, status=200):
            self._responses.append((status, data))

        def _check_auth(self):
            if not auth:
                self._send_json({"error": "unauthorized"}, 401)
                return False
            return True

    return FakeHandler()


def test_media_queue_empty():
    import yinyang_server as ys
    ys._MEDIA_QUEUE.clear()
    h = _make_handler()
    h._handle_media_queue_list()
    status, data = h._responses[0]
    assert status == 200
    assert data["queue"] == []
    assert data["total"] == 0


def test_media_add_to_queue():
    import yinyang_server as ys
    ys._MEDIA_QUEUE.clear()
    h = _make_handler({"url": "https://example.com/image.jpg", "media_type": "image", "filename": "image.jpg"})
    h._handle_media_queue_add()
    status, data = h._responses[0]
    assert status == 201
    assert data["status"] == "queued"
    assert data["item"]["item_id"].startswith("med_")
    assert data["item"]["status"] == "queued"
    assert "url_hash" in data["item"]


def test_media_url_hashed():
    """url_hash must be present and no raw URL stored."""
    import yinyang_server as ys
    ys._MEDIA_QUEUE.clear()
    h = _make_handler({"url": "https://example.com/video.mp4", "media_type": "video", "filename": "v.mp4"})
    h._handle_media_queue_add()
    status, data = h._responses[0]
    assert status == 201
    item = data["item"]
    assert "url_hash" in item
    # url_hash should be 64 hex chars (SHA-256)
    assert len(item["url_hash"]) == 64
    # raw URL must NOT be stored in item
    assert "url" not in item


def test_media_invalid_type():
    import yinyang_server as ys
    ys._MEDIA_QUEUE.clear()
    h = _make_handler({"url": "https://example.com/x", "media_type": "unknown-type"})
    h._handle_media_queue_add()
    status, data = h._responses[0]
    assert status == 400
    assert "media_type" in data["error"]


def test_media_complete_item():
    import yinyang_server as ys
    ys._MEDIA_QUEUE.clear()
    h = _make_handler({"url": "https://example.com/audio.mp3", "media_type": "audio", "filename": "a.mp3"})
    h._handle_media_queue_add()
    item_id = h._responses[0][1]["item"]["item_id"]

    h2 = _make_handler()
    h2._handle_media_queue_complete(item_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "completed"
    assert data["item"]["status"] == "completed"
    assert data["item"]["completed_at"] is not None


def test_media_remove_from_queue():
    import yinyang_server as ys
    ys._MEDIA_QUEUE.clear()
    h = _make_handler({"url": "https://example.com/doc.pdf", "media_type": "document", "filename": "d.pdf"})
    h._handle_media_queue_add()
    item_id = h._responses[0][1]["item"]["item_id"]

    h2 = _make_handler()
    h2._handle_media_queue_remove(item_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "removed"
    assert len(ys._MEDIA_QUEUE) == 0


def test_media_stats():
    import yinyang_server as ys
    ys._MEDIA_QUEUE.clear()
    h = _make_handler({"url": "https://example.com/img2.jpg", "media_type": "image",
                       "filename": "i.jpg", "file_size_bytes": 1024})
    h._handle_media_queue_add()

    h2 = _make_handler()
    h2._handle_media_stats()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert "queued" in data
    assert "completed" in data
    assert "failed" in data
    assert "total_bytes" in data


def test_media_types_list():
    import yinyang_server as ys
    h = _make_handler()
    h._handle_media_types()
    status, data = h._responses[0]
    assert status == 200
    assert "types" in data
    assert "image" in data["types"]
    assert "video" in data["types"]
    assert "statuses" in data


def test_media_html_no_cdn():
    """HTML must not reference external CDN URLs."""
    with open("/home/phuc/projects/solace-browser/web/media-downloader.html") as f:
        content = f.read()
    # No http:// or https:// in script/link src
    import re
    cdn_refs = re.findall(r'(?:src|href)\s*=\s*["\']https?://', content)
    assert cdn_refs == [], f"CDN references found: {cdn_refs}"


def test_no_port_9222_in_media():
    """No port 9222 references in media downloader files."""
    files = [
        "/home/phuc/projects/solace-browser/web/media-downloader.html",
        "/home/phuc/projects/solace-browser/web/js/media-downloader.js",
        "/home/phuc/projects/solace-browser/web/css/media-downloader.css",
    ]
    for path in files:
        with open(path) as f:
            content = f.read()
        assert "9222" not in content, f"Port 9222 found in {path}"
