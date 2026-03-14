# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 145 — Content Copy Tracker
Browser: yinyang_server.py routes /api/v1/copy-tracker/*
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


def test_copy_create():
    import yinyang_server as ys
    ys._COPY_EVENTS.clear()
    h = _make_handler({"content_type": "text", "url": "https://example.com", "content": "Hello World", "char_count": 11, "word_count": 2})
    h._handle_copy_event_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["copy"]["copy_id"].startswith("cct_")


def test_copy_content_hashed():
    import yinyang_server as ys
    ys._COPY_EVENTS.clear()
    h = _make_handler({"content_type": "code", "url": "https://example.com", "content": "def hello(): pass", "char_count": 17, "word_count": 3})
    h._handle_copy_event_create()
    _, data = h._responses[0]
    copy = data["copy"]
    assert "content_hash" in copy
    assert "content" not in copy
    assert len(copy["content_hash"]) == 64


def test_copy_url_hashed():
    import yinyang_server as ys
    ys._COPY_EVENTS.clear()
    h = _make_handler({"content_type": "url", "url": "https://secret.example.com/page", "content": "https://secret.example.com/page", "char_count": 31, "word_count": 1})
    h._handle_copy_event_create()
    _, data = h._responses[0]
    copy = data["copy"]
    assert "url_hash" in copy
    assert "url" not in copy
    assert len(copy["url_hash"]) == 64


def test_copy_invalid_type():
    import yinyang_server as ys
    ys._COPY_EVENTS.clear()
    h = _make_handler({"content_type": "video_clip", "url": "https://example.com", "content": "x", "char_count": 1, "word_count": 1})
    h._handle_copy_event_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_copy_negative_chars():
    import yinyang_server as ys
    ys._COPY_EVENTS.clear()
    h = _make_handler({"content_type": "text", "url": "https://example.com", "content": "x", "char_count": -1, "word_count": 1})
    h._handle_copy_event_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_copy_list():
    import yinyang_server as ys
    ys._COPY_EVENTS.clear()
    h1 = _make_handler({"content_type": "quote", "url": "https://example.com", "content": "A quote", "char_count": 7, "word_count": 2})
    h1._handle_copy_event_create()
    h2 = _make_handler()
    h2._handle_copy_events_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["copies"], list)


def test_copy_delete():
    import yinyang_server as ys
    ys._COPY_EVENTS.clear()
    h1 = _make_handler({"content_type": "email", "url": "https://example.com", "content": "test@example.com", "char_count": 16, "word_count": 1})
    h1._handle_copy_event_create()
    copy_id = h1._responses[0][1]["copy"]["copy_id"]
    h2 = _make_handler()
    h2._handle_copy_event_delete(copy_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    h3 = _make_handler()
    h3._handle_copy_events_list()
    _, list_data = h3._responses[0]
    assert list_data["total"] == 0


def test_copy_not_found():
    import yinyang_server as ys
    ys._COPY_EVENTS.clear()
    h = _make_handler()
    h._handle_copy_event_delete("cct_notexist")
    status, data = h._responses[0]
    assert status == 404


def test_copy_stats():
    import yinyang_server as ys
    ys._COPY_EVENTS.clear()
    h1 = _make_handler({"content_type": "text", "url": "https://example.com", "content": "Hello", "char_count": 5, "word_count": 1})
    h1._handle_copy_event_create()
    h2 = _make_handler({"content_type": "text", "url": "https://example.com", "content": "World", "char_count": 5, "word_count": 1})
    h2._handle_copy_event_create()
    h3 = _make_handler({"content_type": "code", "url": "https://example.com", "content": "x = 1", "char_count": 5, "word_count": 3})
    h3._handle_copy_event_create()
    h_stats = _make_handler()
    h_stats._handle_copy_events_stats()
    status, data = h_stats._responses[0]
    assert status == 200
    assert data["total_copies"] == 3
    assert "most_copied_type" in data
    assert data["most_copied_type"] == "text"  # 2 text vs 1 code
    assert "by_content_type" in data


def test_no_port_9222_in_copy_tracker():
    import re
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0, f"Found port 9222 at positions: {matches}"
