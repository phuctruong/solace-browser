# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 063 — History Search
Browser: yinyang_server.py routes /api/v1/history/*
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


def test_history_list_empty():
    import yinyang_server as ys
    ys._HISTORY_ENTRIES.clear()
    h = _make_handler()
    h._handle_history_list()
    status, data = h._responses[0]
    assert status == 200
    assert data["entries"] == []
    assert data["total"] == 0


def test_history_add_ok():
    import yinyang_server as ys
    ys._HISTORY_ENTRIES.clear()
    url_hash = "a" * 64
    h = _make_handler({"url_hash": url_hash, "title": "Example Page", "content_type": "page"})
    h._handle_history_add()
    status, data = h._responses[0]
    assert status == 201
    assert data["entry"]["entry_id"].startswith("hist_")
    assert data["entry"]["visit_count"] == 1
    assert data["entry"]["title"] == "Example Page"


def test_history_add_duplicate_increments_visit():
    import yinyang_server as ys
    ys._HISTORY_ENTRIES.clear()
    url_hash = "b" * 64
    h = _make_handler({"url_hash": url_hash, "title": "Page", "content_type": "page"})
    h._handle_history_add()
    h2 = _make_handler({"url_hash": url_hash, "title": "Page", "content_type": "page"})
    h2._handle_history_add()

    with ys._HISTORY_LOCK:
        entries = [e for e in ys._HISTORY_ENTRIES if e["url_hash"] == url_hash]
    assert len(entries) == 1
    assert entries[0]["visit_count"] == 2


def test_history_add_invalid_content_type():
    import yinyang_server as ys
    ys._HISTORY_ENTRIES.clear()
    h = _make_handler({"url_hash": "c" * 64, "title": "Page", "content_type": "unknown-type"})
    h._handle_history_add()
    status, data = h._responses[0]
    assert status == 400
    assert "content_type" in data["error"]


def test_history_add_requires_auth():
    import yinyang_server as ys
    ys._HISTORY_ENTRIES.clear()
    h = _make_handler({"url_hash": "d" * 64, "title": "Page", "content_type": "page"}, auth=False)
    h._handle_history_add()
    status, _ = h._responses[0]
    assert status == 401


def test_history_clear_ok():
    import yinyang_server as ys
    ys._HISTORY_ENTRIES.clear()
    h = _make_handler({"url_hash": "e" * 64, "title": "Page", "content_type": "download"})
    h._handle_history_add()

    h2 = _make_handler()
    h2._handle_history_clear()
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "cleared"
    assert data["count"] >= 1
    assert len(ys._HISTORY_ENTRIES) == 0


def test_history_search_finds_title():
    import yinyang_server as ys
    ys._HISTORY_ENTRIES.clear()
    h = _make_handler({"url_hash": "f" * 64, "title": "Python Tutorial", "content_type": "page"})
    h._handle_history_add()

    h2 = _make_handler({"query": "python", "limit": 10})
    h2._handle_history_search()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert any("python" in r["title"].lower() for r in data["results"])


def test_history_stats():
    import yinyang_server as ys
    ys._HISTORY_ENTRIES.clear()
    h = _make_handler({"url_hash": "1" * 64, "title": "Stats Page", "content_type": "page"})
    h._handle_history_add()

    h2 = _make_handler()
    h2._handle_history_stats()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total_entries"] >= 1
    assert "by_content_type" in data
    assert "page" in data["by_content_type"]


def test_history_top_domains():
    import yinyang_server as ys
    ys._HISTORY_ENTRIES.clear()
    h = _make_handler({"url_hash": "2" * 64, "title": "Domain Test", "content_type": "page"})
    h._handle_history_add()

    h2 = _make_handler()
    h2._handle_history_top_domains()
    status, data = h2._responses[0]
    assert status == 200
    assert "domains" in data
    assert data["total"] >= 1
    for d in data["domains"]:
        assert "domain_hash" in d
        assert "visit_count" in d


def test_history_add_invalid_url_hash():
    import yinyang_server as ys
    ys._HISTORY_ENTRIES.clear()
    h = _make_handler({"url_hash": "short", "title": "Page", "content_type": "page"})
    h._handle_history_add()
    status, data = h._responses[0]
    assert status == 400
    assert "url_hash" in data["error"]
