"""
Tests for Task 156 — Tab Productivity Scorer
Browser: yinyang_server.py routes /api/v1/tab-productivity/*
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


def test_score_create():
    import yinyang_server as ys
    ys._TAB_SCORES.clear()
    h = _make_handler({
        "category": "work",
        "url": "https://example.com/work",
        "time_spent_minutes": 30,
        "productivity_score": 8,
        "tab_count": 3,
    })
    h._handle_tps_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["score"]["score_id"].startswith("tps_")
    assert data["score"]["category"] == "work"
    assert data["score"]["tab_count"] == 3


def test_score_url_hashed():
    import yinyang_server as ys
    ys._TAB_SCORES.clear()
    h = _make_handler({
        "category": "research",
        "url": "https://scholar.google.com",
        "time_spent_minutes": 45,
        "productivity_score": 9,
        "tab_count": 1,
    })
    h._handle_tps_create()
    status, data = h._responses[0]
    assert status == 201
    score = data["score"]
    # url_hash must be present, raw URL must NOT be stored
    assert "url_hash" in score
    assert len(score["url_hash"]) == 64  # SHA-256 hex
    assert "url" not in score


def test_score_invalid_category():
    import yinyang_server as ys
    ys._TAB_SCORES.clear()
    h = _make_handler({
        "category": "gaming",
        "url": "https://example.com",
        "time_spent_minutes": 60,
        "productivity_score": 2,
        "tab_count": 1,
    })
    h._handle_tps_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_score_invalid_productivity():
    import yinyang_server as ys
    ys._TAB_SCORES.clear()
    h = _make_handler({
        "category": "entertainment",
        "url": "https://example.com",
        "time_spent_minutes": 20,
        "productivity_score": 11,
        "tab_count": 1,
    })
    h._handle_tps_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_score_zero_tab_count():
    import yinyang_server as ys
    ys._TAB_SCORES.clear()
    h = _make_handler({
        "category": "work",
        "url": "https://example.com",
        "time_spent_minutes": 15,
        "productivity_score": 7,
        "tab_count": 0,
    })
    h._handle_tps_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_score_negative_time():
    import yinyang_server as ys
    ys._TAB_SCORES.clear()
    h = _make_handler({
        "category": "learning",
        "url": "https://example.com",
        "time_spent_minutes": -1,
        "productivity_score": 8,
        "tab_count": 1,
    })
    h._handle_tps_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_score_productive_flag():
    import yinyang_server as ys
    ys._TAB_SCORES.clear()
    # score=6 → is_productive=True
    h = _make_handler({
        "category": "development",
        "url": "https://github.com",
        "time_spent_minutes": 90,
        "productivity_score": 6,
        "tab_count": 2,
    })
    h._handle_tps_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["score"]["is_productive"] is True
    # score=5 → is_productive=False
    ys._TAB_SCORES.clear()
    h2 = _make_handler({
        "category": "social_media",
        "url": "https://twitter.com",
        "time_spent_minutes": 10,
        "productivity_score": 5,
        "tab_count": 1,
    })
    h2._handle_tps_create()
    status2, data2 = h2._responses[0]
    assert status2 == 201
    assert data2["score"]["is_productive"] is False


def test_score_list():
    import yinyang_server as ys
    ys._TAB_SCORES.clear()
    h1 = _make_handler({
        "category": "news",
        "url": "https://news.example.com",
        "time_spent_minutes": 5,
        "productivity_score": 4,
        "tab_count": 1,
    })
    h1._handle_tps_create()
    h2 = _make_handler()
    h2._handle_tps_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["scores"], list)


def test_score_stats():
    import yinyang_server as ys
    ys._TAB_SCORES.clear()
    h1 = _make_handler({
        "category": "work",
        "url": "https://work.example.com",
        "time_spent_minutes": 60,
        "productivity_score": 9,
        "tab_count": 4,
    })
    h1._handle_tps_create()
    h2 = _make_handler({
        "category": "shopping",
        "url": "https://shop.example.com",
        "time_spent_minutes": 15,
        "productivity_score": 3,
        "tab_count": 1,
    })
    h2._handle_tps_create()
    h_stats = _make_handler()
    h_stats._handle_tps_stats()
    status, data = h_stats._responses[0]
    assert status == 200
    assert data["total_scores"] == 2
    assert data["productive_count"] == 1
    assert data["unproductive_count"] == 1
    assert data["total_time_minutes"] == 75
    avg = data["avg_productivity_score"]
    assert isinstance(avg, str)
    float(avg)
    assert "by_category" in data


def test_no_port_9222_in_productivity():
    import re
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0, f"Found port 9222 at positions: {matches}"
