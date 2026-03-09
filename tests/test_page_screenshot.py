"""
Tests for Task 054 — Page Screenshot API
Browser: yinyang_server.py routes /api/v1/screenshots/*
"""
import sys
import json

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


def test_screenshot_list_empty():
    import yinyang_server as ys
    ys._SCREENSHOTS.clear()
    h = _make_handler()
    h._handle_screenshot_list()
    status, data = h._responses[0]
    assert status == 200
    assert data["screenshots"] == []
    assert data["total"] == 0


def test_screenshot_capture():
    import yinyang_server as ys
    ys._SCREENSHOTS.clear()
    h = _make_handler({
        "url": "https://example.com",
        "format": "png",
        "quality": "medium",
        "width": 1280,
        "height": 720,
    })
    h._handle_screenshot_capture()
    status, data = h._responses[0]
    assert status == 200
    assert data["status"] == "captured"
    assert data["screenshot_id"].startswith("ss_")


def test_screenshot_url_hashed():
    import yinyang_server as ys
    ys._SCREENSHOTS.clear()
    h = _make_handler({
        "url": "https://example.com/secret",
        "format": "png",
        "quality": "high",
        "width": 1280,
        "height": 720,
    })
    h._handle_screenshot_capture()
    ss_id = h._responses[0][1]["screenshot_id"]

    h2 = _make_handler()
    h2._handle_screenshot_get(ss_id)
    _, data = h2._responses[0]
    assert "url_hash" in data
    assert "url" not in data or data.get("url") is None or "secret" not in str(data.get("url", ""))


def test_screenshot_get_by_id():
    import yinyang_server as ys
    ys._SCREENSHOTS.clear()
    h1 = _make_handler({
        "url": "https://example.com",
        "format": "jpeg",
        "quality": "low",
        "width": 800,
        "height": 600,
    })
    h1._handle_screenshot_capture()
    ss_id = h1._responses[0][1]["screenshot_id"]

    h2 = _make_handler()
    h2._handle_screenshot_get(ss_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["screenshot_id"] == ss_id
    assert data["format"] == "jpeg"


def test_screenshot_delete():
    import yinyang_server as ys
    ys._SCREENSHOTS.clear()
    h1 = _make_handler({
        "url": "https://example.com",
        "format": "webp",
        "quality": "lossless",
        "width": 1920,
        "height": 1080,
    })
    h1._handle_screenshot_capture()
    ss_id = h1._responses[0][1]["screenshot_id"]

    h2 = _make_handler()
    h2._handle_screenshot_delete(ss_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"


def test_screenshot_invalid_format():
    import yinyang_server as ys
    ys._SCREENSHOTS.clear()
    h = _make_handler({
        "url": "https://example.com",
        "format": "bmp",
        "quality": "medium",
        "width": 1280,
        "height": 720,
    })
    h._handle_screenshot_capture()
    status, data = h._responses[0]
    assert status == 400
    assert "format" in data["error"]


def test_screenshot_invalid_quality():
    import yinyang_server as ys
    ys._SCREENSHOTS.clear()
    h = _make_handler({
        "url": "https://example.com",
        "format": "png",
        "quality": "ultra",
        "width": 1280,
        "height": 720,
    })
    h._handle_screenshot_capture()
    status, data = h._responses[0]
    assert status == 400
    assert "quality" in data["error"]


def test_screenshot_stats():
    import yinyang_server as ys
    ys._SCREENSHOTS.clear()
    h1 = _make_handler({
        "url": "https://example.com",
        "format": "png",
        "quality": "medium",
        "width": 1280,
        "height": 720,
    })
    h1._handle_screenshot_capture()

    h2 = _make_handler()
    h2._handle_screenshot_stats()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] == 1
    assert "by_format" in data
    assert "total_size_bytes" in data


def test_screenshot_html_no_cdn():
    html = open("/home/phuc/projects/solace-browser/web/page-screenshot.html").read()
    assert "cdn.jsdelivr" not in html
    assert "unpkg.com" not in html
    assert "cloudflare.com" not in html


def test_no_port_9222_in_screenshot():
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    import re
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0
