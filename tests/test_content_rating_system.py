# Diagram: 05-solace-runtime-architecture
"""Tests for Task 114 — Content Rating System."""
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
    with ys._RATINGS_LOCK:
        ys._RATINGS.clear()


def test_rating_create():
    h = make_handler({"url": "https://article.com", "criterion": "accuracy",
                      "score": 4, "notes": "Great article"})
    h._handle_rating_create()
    code, data = h._responses[0]
    assert code == 201
    assert data["rating"]["rating_id"].startswith("crt_")


def test_rating_url_hashed():
    h = make_handler({"url": "https://secret-article.com", "criterion": "clarity",
                      "score": 3})
    h._handle_rating_create()
    code, data = h._responses[0]
    assert code == 201
    rating = data["rating"]
    assert "url_hash" in rating
    assert "secret-article.com" not in str(rating)
    assert "https://secret-article.com" not in str(rating)


def test_rating_invalid_criterion():
    h = make_handler({"url": "https://x.com", "criterion": "badcriterion", "score": 3})
    h._handle_rating_create()
    code, data = h._responses[0]
    assert code == 400
    assert "criterion" in data["error"]


def test_rating_score_too_low():
    h = make_handler({"url": "https://x.com", "criterion": "accuracy", "score": 0})
    h._handle_rating_create()
    code, data = h._responses[0]
    assert code == 400
    assert "score" in data["error"]


def test_rating_score_too_high():
    h = make_handler({"url": "https://x.com", "criterion": "depth", "score": 6})
    h._handle_rating_create()
    code, data = h._responses[0]
    assert code == 400
    assert "score" in data["error"]


def test_rating_quality_level():
    h = make_handler({"url": "https://top.com", "criterion": "originality", "score": 5})
    h._handle_rating_create()
    code, data = h._responses[0]
    assert code == 201
    assert data["rating"]["quality_level"] == "outstanding"


def test_rating_list():
    h = make_handler({"url": "https://list.com", "criterion": "relevance", "score": 2})
    h._handle_rating_create()
    h2 = FakeHandler()
    h2._handle_rating_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["ratings"], list)
    assert data["total"] >= 1


def test_rating_delete():
    h = make_handler({"url": "https://del.com", "criterion": "credibility", "score": 3})
    h._handle_rating_create()
    rid = h._responses[0][1]["rating"]["rating_id"]
    h2 = FakeHandler()
    h2._handle_rating_delete(rid)
    code, data = h2._responses[0]
    assert code == 200
    assert data["rating_id"] == rid
    with ys._RATINGS_LOCK:
        ids = [r["rating_id"] for r in ys._RATINGS]
    assert rid not in ids


def test_rating_stats():
    h1 = make_handler({"url": "https://s1.com", "criterion": "accuracy", "score": 4})
    h1._handle_rating_create()
    h2 = make_handler({"url": "https://s2.com", "criterion": "accuracy", "score": 2})
    h2._handle_rating_create()
    h3 = FakeHandler()
    h3._handle_rating_stats()
    code, data = h3._responses[0]
    assert code == 200
    assert "avg_score" in data
    assert isinstance(data["avg_score"], str)
    # avg of 4 and 2 = 3.00
    assert data["avg_score"] == "3.00"
    assert "by_criterion" in data
    assert "by_quality" in data


def test_no_port_9222_in_rating():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "922" + "2" not in content, "Port 9222 found in yinyang_server.py — BANNED"
