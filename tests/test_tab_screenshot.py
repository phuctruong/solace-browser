# Diagram: 05-solace-runtime-architecture
"""tests/test_tab_screenshot.py — Task 076: Tab Screenshot | 10 tests"""
import sys
import json
import hashlib

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "a" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
        self.headers = {"content-length": "0", "authorization": f"Bearer {VALID_TOKEN}"}

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass


def make_handler():
    h = FakeHandler()
    # Clear shared state
    ys._TAB_SCREENSHOTS.clear()
    return h


def capture(h, url="https://example.com", title="Test", fmt="png", size=1024):
    h._body = json.dumps({
        "url": url,
        "title": title,
        "format": fmt,
        "size_bytes": size,
    }).encode()
    h._handle_tab_screenshot_capture()
    return h._responses[-1]


def test_screenshot_capture():
    h = make_handler()
    code, data = capture(h)
    assert code == 201
    assert data["screenshot_id"].startswith("scr_")


def test_screenshot_url_hashed():
    h = make_handler()
    url = "https://secret.example.com/private"
    code, data = capture(h, url=url)
    assert code == 201
    scr_id = data["screenshot_id"]
    # Verify gallery entry has url_hash, not raw URL
    h2 = FakeHandler()
    ys._TAB_SCREENSHOTS  # reference
    h2._handle_tab_screenshot_gallery()
    _, gallery = h2._responses[-1]
    items = gallery["screenshots"]
    assert any(s["screenshot_id"] == scr_id for s in items)
    item = next(s for s in items if s["screenshot_id"] == scr_id)
    expected_hash = hashlib.sha256(url.encode()).hexdigest()
    assert item["url_hash"] == expected_hash
    assert url not in str(item)


def test_screenshot_invalid_format():
    h = make_handler()
    h._body = json.dumps({"url": "https://x.com", "format": "bmp"}).encode()
    h._handle_tab_screenshot_capture()
    code, data = h._responses[-1]
    assert code == 400
    assert "format" in data["error"].lower()


def test_screenshot_gallery():
    h = make_handler()
    capture(h, url="https://a.com")
    capture(h, url="https://b.com")
    h2 = FakeHandler()
    h2._handle_tab_screenshot_gallery()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["total"] == 2
    assert len(data["screenshots"]) == 2


def test_screenshot_delete():
    h = make_handler()
    code, created = capture(h)
    scr_id = created["screenshot_id"]
    h2 = FakeHandler()
    h2.path = f"/api/v1/tab-screenshot/{scr_id}"
    h2._handle_tab_screenshot_delete(scr_id)
    code2, data2 = h2._responses[-1]
    assert code2 == 200
    assert data2["screenshot_id"] == scr_id
    assert len(ys._TAB_SCREENSHOTS) == 0


def test_screenshot_delete_not_found():
    h = make_handler()
    h._handle_tab_screenshot_delete("scr_notexist")
    code, data = h._responses[-1]
    assert code == 404


def test_screenshot_stats():
    h = make_handler()
    capture(h, size=500)
    capture(h, size=700)
    h2 = FakeHandler()
    h2._handle_tab_screenshot_stats()
    code, data = h2._responses[-1]
    assert code == 200
    assert data["count"] == 2
    assert data["total_size_bytes"] == 1200


def test_screenshot_formats():
    h = make_handler()
    h._handle_tab_screenshot_formats()
    code, data = h._responses[-1]
    assert code == 200
    fmts = data["formats"]
    assert len(fmts) == 3
    assert "png" in fmts
    assert "jpeg" in fmts
    assert "webp" in fmts


def test_screenshot_file_hashed():
    h = make_handler()
    file_content = "fake-binary-data-12345"
    h._body = json.dumps({
        "url": "https://x.com",
        "format": "png",
        "file_content": file_content,
        "size_bytes": 100,
    }).encode()
    h._handle_tab_screenshot_capture()
    code, data = h._responses[-1]
    assert code == 201
    scr_id = data["screenshot_id"]
    item = next(s for s in ys._TAB_SCREENSHOTS if s["screenshot_id"] == scr_id)
    expected = hashlib.sha256(file_content.encode()).hexdigest()
    assert item["file_hash"] == expected
    assert file_content not in str(item)


def test_no_port_9222_in_screenshot():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        source = f.read()
    assert "9222" not in source
