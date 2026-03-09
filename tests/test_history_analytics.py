"""Tests for Task 112 — Browser History Analytics."""
import sys
import json

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
        self.headers = {"content-length": "0", "Authorization": "Bearer valid"}

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
    with ys._VISITS_LOCK:
        ys._VISITS.clear()


def test_visit_create():
    h = make_handler({"url": "https://example.com", "domain": "example.com",
                      "category": "work", "duration_seconds": 30})
    h._handle_visit_create()
    code, data = h._responses[0]
    assert code == 201
    assert data["visit"]["visit_id"].startswith("vis_")


def test_visit_url_hashed():
    h = make_handler({"url": "https://secret.com", "domain": "secret.com",
                      "category": "work", "duration_seconds": 10})
    h._handle_visit_create()
    code, data = h._responses[0]
    assert code == 201
    visit = data["visit"]
    assert "url_hash" in visit
    assert "secret.com" not in str(visit)
    assert "https://secret.com" not in str(visit)


def test_visit_invalid_category():
    h = make_handler({"url": "https://x.com", "domain": "x.com",
                      "category": "nonexistent", "duration_seconds": 5})
    h._handle_visit_create()
    code, data = h._responses[0]
    assert code == 400
    assert "category" in data["error"]


def test_visit_negative_duration():
    h = make_handler({"url": "https://x.com", "domain": "x.com",
                      "category": "news", "duration_seconds": -1})
    h._handle_visit_create()
    code, data = h._responses[0]
    assert code == 400
    assert "duration_seconds" in data["error"]


def test_visit_list():
    h = make_handler({"url": "https://y.com", "domain": "y.com",
                      "category": "social", "duration_seconds": 60})
    h._handle_visit_create()
    h2 = FakeHandler()
    h2._handle_visit_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["visits"], list)
    assert data["total"] >= 1


def test_visit_delete():
    h = make_handler({"url": "https://z.com", "domain": "z.com",
                      "category": "education", "duration_seconds": 120})
    h._handle_visit_create()
    visit_id = h._responses[0][1]["visit"]["visit_id"]
    h2 = FakeHandler()
    h2._handle_visit_delete(visit_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["visit_id"] == visit_id
    with ys._VISITS_LOCK:
        ids = [v["visit_id"] for v in ys._VISITS]
    assert visit_id not in ids


def test_visit_not_found():
    h = FakeHandler()
    h._handle_visit_delete("vis_notexist")
    code, data = h._responses[0]
    assert code == 404


def test_history_stats():
    h = make_handler({"url": "https://stats.com", "domain": "stats.com",
                      "category": "work", "duration_seconds": 45})
    h._handle_visit_create()
    h2 = FakeHandler()
    h2._handle_visit_stats()
    code, data = h2._responses[0]
    assert code == 200
    assert "top_domains" in data
    assert "total_visits" in data
    assert "by_category" in data


def test_categories_list():
    h = FakeHandler()
    h._handle_visit_categories()
    code, data = h._responses[0]
    assert code == 200
    cats = data["categories"]
    assert len(cats) == 7
    assert "social" in cats
    assert "work" in cats
    assert "other" in cats


def test_no_port_9222_in_history():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "922" + "2" not in content, "Port 9222 found in yinyang_server.py — BANNED"
