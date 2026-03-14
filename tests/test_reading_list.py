# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 059 — Reading List
Browser: yinyang_server.py routes /api/v1/reading-list
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


def test_reading_list_empty():
    import yinyang_server as ys
    ys._READING_LIST.clear()
    h = _make_handler()
    h._handle_reading_list_get()
    status, data = h._responses[0]
    assert status == 200
    assert data["items"] == []
    assert data["total"] == 0


def test_reading_list_add_ok():
    import yinyang_server as ys
    ys._READING_LIST.clear()
    url_hash = "a" * 64
    h = _make_handler({"url_hash": url_hash, "title": "Test Article", "estimated_read_time_min": 5})
    h._handle_reading_list_add()
    status, data = h._responses[0]
    assert status == 201
    assert data["status"] == "added"
    assert data["item"]["item_id"].startswith("rl_")
    assert data["item"]["status"] == "unread"
    assert data["item"]["progress_pct"] == 0


def test_reading_list_add_requires_auth():
    import yinyang_server as ys
    ys._READING_LIST.clear()
    h = _make_handler({"url_hash": "b" * 64, "title": "X"}, auth=False)
    h._handle_reading_list_add()
    status, _ = h._responses[0]
    assert status == 401


def test_reading_list_add_invalid_url_hash():
    import yinyang_server as ys
    ys._READING_LIST.clear()
    h = _make_handler({"url_hash": "short", "title": "X"})
    h._handle_reading_list_add()
    status, data = h._responses[0]
    assert status == 400
    assert "url_hash" in data["error"]


def test_reading_list_item_get_ok():
    import yinyang_server as ys
    ys._READING_LIST.clear()
    url_hash = "c" * 64
    h = _make_handler({"url_hash": url_hash, "title": "Article 2"})
    h._handle_reading_list_add()
    item_id = h._responses[0][1]["item"]["item_id"]

    h2 = _make_handler()
    h2._handle_reading_list_item_get(item_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["item_id"] == item_id


def test_reading_list_item_get_not_found():
    import yinyang_server as ys
    ys._READING_LIST.clear()
    h = _make_handler()
    h._handle_reading_list_item_get("rl_notexist")
    status, data = h._responses[0]
    assert status == 404


def test_reading_list_progress_update():
    import yinyang_server as ys
    ys._READING_LIST.clear()
    url_hash = "d" * 64
    h = _make_handler({"url_hash": url_hash, "title": "Book"})
    h._handle_reading_list_add()
    item_id = h._responses[0][1]["item"]["item_id"]

    h2 = _make_handler({"progress_pct": 50})
    h2._handle_reading_list_progress(item_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["item"]["progress_pct"] == 50
    assert data["item"]["status"] == "reading"


def test_reading_list_progress_100_completes():
    import yinyang_server as ys
    ys._READING_LIST.clear()
    url_hash = "e" * 64
    h = _make_handler({"url_hash": url_hash, "title": "Book 2"})
    h._handle_reading_list_add()
    item_id = h._responses[0][1]["item"]["item_id"]

    h2 = _make_handler({"progress_pct": 100})
    h2._handle_reading_list_progress(item_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["item"]["status"] == "completed"


def test_reading_list_delete_ok():
    import yinyang_server as ys
    ys._READING_LIST.clear()
    url_hash = "f" * 64
    h = _make_handler({"url_hash": url_hash, "title": "To Delete"})
    h._handle_reading_list_add()
    item_id = h._responses[0][1]["item"]["item_id"]

    h2 = _make_handler()
    h2._handle_reading_list_delete(item_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"


def test_reading_list_stats():
    import yinyang_server as ys
    ys._READING_LIST.clear()
    url_hash = "0" * 64
    h = _make_handler({"url_hash": url_hash, "title": "Stats Test"})
    h._handle_reading_list_add()

    h2 = _make_handler()
    h2._handle_reading_list_stats()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert "by_status" in data
    assert "unread" in data["by_status"]
