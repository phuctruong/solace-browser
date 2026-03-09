"""Tests for Task 121 — Custom Search Engine."""
import sys
import json
import subprocess

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "c" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self, body=b"{}"):
        self._body = body
        self._responses = []
        self.headers = {"Authorization": f"Bearer {VALID_TOKEN}"}

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
    return h


def setup_function():
    with ys._SEARCH_LOCK:
        ys._SEARCH_ENGINES.clear()


def test_engine_create():
    h = make_handler({"name": "DuckDuckGo", "url_template": "https://duckduckgo.com/?q={query}", "category": "general"})
    h._handle_search_engine_create()
    code, data = h._responses[0]
    assert code == 201
    assert data["engine"]["engine_id"].startswith("sce_")


def test_engine_name_hashed():
    h = make_handler({"name": "Google", "url_template": "https://google.com/search?q={query}", "category": "general"})
    h._handle_search_engine_create()
    code, data = h._responses[0]
    assert code == 201
    engine = data["engine"]
    assert "name_hash" in engine
    assert "name" not in engine


def test_engine_invalid_category():
    h = make_handler({"name": "Test", "url_template": "https://test.com?q={query}", "category": "unknown_cat"})
    h._handle_search_engine_create()
    code, data = h._responses[0]
    assert code == 400
    assert "category" in data["error"]


def test_engine_list():
    h1 = make_handler({"name": "Bing", "url_template": "https://bing.com/search?q={query}", "category": "general"})
    h1._handle_search_engine_create()
    h2 = FakeHandler()
    h2._handle_search_engine_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["engines"], list)
    assert data["total"] >= 1


def test_engine_delete():
    h = make_handler({"name": "Yahoo", "url_template": "https://yahoo.com/search?q={query}", "category": "general"})
    h._handle_search_engine_create()
    engine_id = h._responses[0][1]["engine"]["engine_id"]
    h2 = FakeHandler()
    h2._handle_search_engine_delete(engine_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["engine_id"] == engine_id
    with ys._SEARCH_LOCK:
        ids = [e["engine_id"] for e in ys._SEARCH_ENGINES]
    assert engine_id not in ids


def test_engine_not_found():
    h = FakeHandler()
    h._handle_search_engine_delete("sce_notexist")
    code, data = h._responses[0]
    assert code == 404


def test_engine_activate():
    h = make_handler({"name": "Brave", "url_template": "https://search.brave.com?q={query}", "category": "general"})
    h._handle_search_engine_create()
    engine_id = h._responses[0][1]["engine"]["engine_id"]
    h2 = FakeHandler()
    h2._handle_search_engine_activate(engine_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["engine"]["is_active"] is True


def test_engine_only_one_active():
    h1 = make_handler({"name": "Engine A", "url_template": "https://a.com?q={query}", "category": "general"})
    h1._handle_search_engine_create()
    id_a = h1._responses[0][1]["engine"]["engine_id"]

    h2 = make_handler({"name": "Engine B", "url_template": "https://b.com?q={query}", "category": "technical"})
    h2._handle_search_engine_create()
    id_b = h2._responses[0][1]["engine"]["engine_id"]

    # Activate A first
    ha = FakeHandler()
    ha._handle_search_engine_activate(id_a)

    # Then activate B
    hb = FakeHandler()
    hb._handle_search_engine_activate(id_b)

    with ys._SEARCH_LOCK:
        state = {e["engine_id"]: e["is_active"] for e in ys._SEARCH_ENGINES}

    assert state.get(id_b) is True
    assert state.get(id_a) is False


def test_active_engine():
    h1 = make_handler({"name": "Kagi", "url_template": "https://kagi.com/search?q={query}", "category": "general"})
    h1._handle_search_engine_create()
    engine_id = h1._responses[0][1]["engine"]["engine_id"]

    h2 = FakeHandler()
    h2._handle_search_engine_activate(engine_id)

    h3 = FakeHandler()
    h3._handle_search_engine_active()
    code, data = h3._responses[0]
    assert code == 200
    assert data["engine"]["engine_id"] == engine_id


def test_no_port_9222_in_search():
    # Verify no banned port appears in the server implementation handlers for this feature
    result = subprocess.run(
        ["grep", "-n", "9" + "222", "/home/phuc/projects/solace-browser/yinyang_server.py"],
        capture_output=True,
        text=True,
    )
    # grep returns non-zero if no match — banned port must not appear
    assert result.returncode != 0, f"Banned port found in server: {result.stdout}"
