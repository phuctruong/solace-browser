# Diagram: 05-solace-runtime-architecture
"""Tests for Task 081 — Search Suggestions."""
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
        self.headers = {"content-length": "0", "Authorization": f"Bearer {VALID_TOKEN}"}

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass

    def _parse_query(self, query):
        params = {}
        if query.startswith("?"):
            query = query[1:]
        for part in query.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = v
        return params


def make_handler(body=None):
    h = FakeHandler()
    if body is not None:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def clear_state():
    with ys._SEARCH_LOCK:
        ys._SEARCH_HISTORY.clear()


def test_search_record():
    """POST → srh_ prefix returned."""
    clear_state()
    h = make_handler({"query": "python asyncio", "engine_url": "https://google.com", "result_count": 10})
    h._handle_search_record()
    code, data = h._responses[0]
    assert code == 201
    assert data["search_id"].startswith("srh_")


def test_search_query_hashed():
    """query_hash present, no raw query stored."""
    clear_state()
    h = make_handler({"query": "secret search", "engine_url": "https://bing.com", "result_count": 5})
    h._handle_search_record()
    with ys._SEARCH_LOCK:
        entry = ys._SEARCH_HISTORY[-1]
    assert "query_hash" in entry
    assert "query" not in entry
    expected_hash = hashlib.sha256("secret search".encode()).hexdigest()
    assert entry["query_hash"] == expected_hash


def test_search_engine_hashed():
    """engine_hash present in stored entry."""
    clear_state()
    engine_url = "https://duckduckgo.com"
    h = make_handler({"query": "solace cli", "engine_url": engine_url, "result_count": 3})
    h._handle_search_record()
    with ys._SEARCH_LOCK:
        entry = ys._SEARCH_HISTORY[-1]
    assert "engine_hash" in entry
    expected = hashlib.sha256(engine_url.encode()).hexdigest()
    assert entry["engine_hash"] == expected


def test_search_negative_results():
    """result_count=-1 → 400."""
    clear_state()
    h = make_handler({"query": "test", "engine_url": "https://g.com", "result_count": -1})
    h._handle_search_record()
    code, data = h._responses[0]
    assert code == 400
    assert "error" in data


def test_search_suggest():
    """GET /suggest → list returned."""
    clear_state()
    rec = make_handler({"query": "machine learning", "engine_url": "https://g.com", "result_count": 7})
    rec._handle_search_record()
    h = FakeHandler()
    h._handle_search_suggest("?q=mach")
    code, data = h._responses[0]
    assert code == 200
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)


def test_search_popular():
    """GET /popular → list returned."""
    clear_state()
    for i in range(3):
        rec = make_handler({"query": "popular query", "engine_url": "https://g.com", "result_count": i})
        rec._handle_search_record()
    h = FakeHandler()
    h._handle_search_popular()
    code, data = h._responses[0]
    assert code == 200
    assert "popular" in data
    assert isinstance(data["popular"], list)
    assert data["popular"][0]["count"] >= 1


def test_search_clear_history():
    """DELETE /history → empty."""
    clear_state()
    rec = make_handler({"query": "clear me", "engine_url": "https://g.com", "result_count": 1})
    rec._handle_search_record()
    with ys._SEARCH_LOCK:
        assert len(ys._SEARCH_HISTORY) >= 1
    h = make_handler()
    h._handle_search_history_clear()
    code, data = h._responses[0]
    assert code == 200
    assert data["status"] == "cleared"
    with ys._SEARCH_LOCK:
        assert len(ys._SEARCH_HISTORY) == 0


def test_search_stats():
    """GET /stats → total_searches present."""
    clear_state()
    rec = make_handler({"query": "stats query", "engine_url": "https://g.com", "result_count": 2})
    rec._handle_search_record()
    h = make_handler()
    h._handle_search_stats()
    code, data = h._responses[0]
    assert code == 200
    assert "total_searches" in data
    assert data["total_searches"] >= 1
    assert "unique_hashes" in data


def test_search_history_max():
    """Adding 501 entries evicts oldest."""
    clear_state()
    for i in range(ys.MAX_SEARCH_HISTORY + 1):
        rec = make_handler({"query": f"query {i}", "engine_url": "https://g.com", "result_count": 0})
        rec._handle_search_record()
    with ys._SEARCH_LOCK:
        assert len(ys._SEARCH_HISTORY) == ys.MAX_SEARCH_HISTORY


def test_no_port_9222_in_search():
    """No port 9222 in search suggestions code."""
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found in yinyang_server.py — BANNED"
