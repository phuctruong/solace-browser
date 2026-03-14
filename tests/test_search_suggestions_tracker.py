# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 152 — Search Suggestions Tracker
Browser: yinyang_server.py routes /api/v1/search-suggestions/*
"""
import sys
import json
import re

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


def test_event_create():
    import yinyang_server as ys
    ys._SUGGESTION_EVENTS.clear()
    h = _make_handler({"event_type": "shown", "query": "python tutorial", "suggestion": "python tutorials for beginners", "position": 1, "engine": "google"})
    h._handle_sgt_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["event_id"].startswith("sgt_")


def test_event_query_hashed():
    import yinyang_server as ys
    ys._SUGGESTION_EVENTS.clear()
    h = _make_handler({"event_type": "shown", "query": "secret search", "suggestion": "secret search results", "position": 2, "engine": "bing"})
    h._handle_sgt_create()
    _, resp = h._responses[0]
    event_id = resp["event_id"]
    with ys._SUGGESTION_LOCK:
        event = next(e for e in ys._SUGGESTION_EVENTS if e["event_id"] == event_id)
    assert "query_hash" in event
    assert "query" not in event


def test_event_suggestion_hashed():
    import yinyang_server as ys
    ys._SUGGESTION_EVENTS.clear()
    h = _make_handler({"event_type": "clicked", "query": "flask", "suggestion": "flask documentation", "position": 3, "engine": "duckduckgo"})
    h._handle_sgt_create()
    _, resp = h._responses[0]
    event_id = resp["event_id"]
    with ys._SUGGESTION_LOCK:
        event = next(e for e in ys._SUGGESTION_EVENTS if e["event_id"] == event_id)
    assert "suggestion_hash" in event
    assert "suggestion" not in event


def test_event_invalid_type():
    import yinyang_server as ys
    ys._SUGGESTION_EVENTS.clear()
    h = _make_handler({"event_type": "hovered", "query": "x", "suggestion": "y", "position": 1, "engine": "g"})
    h._handle_sgt_create()
    status, data = h._responses[0]
    assert status == 400


def test_event_invalid_position():
    import yinyang_server as ys
    ys._SUGGESTION_EVENTS.clear()
    h = _make_handler({"event_type": "shown", "query": "x", "suggestion": "y", "position": 0, "engine": "g"})
    h._handle_sgt_create()
    status, data = h._responses[0]
    assert status == 400


def test_event_position_too_high():
    import yinyang_server as ys
    ys._SUGGESTION_EVENTS.clear()
    h = _make_handler({"event_type": "shown", "query": "x", "suggestion": "y", "position": 11, "engine": "g"})
    h._handle_sgt_create()
    status, data = h._responses[0]
    assert status == 400


def test_event_list():
    import yinyang_server as ys
    ys._SUGGESTION_EVENTS.clear()
    h1 = _make_handler({"event_type": "dismissed", "query": "cats", "suggestion": "cat videos", "position": 5, "engine": "google"})
    h1._handle_sgt_create()
    h2 = _make_handler()
    h2._handle_sgt_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["events"], list)


def test_event_delete():
    import yinyang_server as ys
    ys._SUGGESTION_EVENTS.clear()
    h1 = _make_handler({"event_type": "typed_over", "query": "del", "suggestion": "delete me", "position": 4, "engine": "brave"})
    h1._handle_sgt_create()
    event_id = h1._responses[0][1]["event_id"]
    h2 = _make_handler()
    h2._handle_sgt_delete(event_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    with ys._SUGGESTION_LOCK:
        assert not any(e["event_id"] == event_id for e in ys._SUGGESTION_EVENTS)


def test_suggestion_stats():
    import yinyang_server as ys
    ys._SUGGESTION_EVENTS.clear()
    # Add 2 shown, 1 clicked
    for i in range(2):
        h = _make_handler({"event_type": "shown", "query": f"q{i}", "suggestion": f"s{i}", "position": 1, "engine": "google"})
        h._handle_sgt_create()
    h = _make_handler({"event_type": "clicked", "query": "qc", "suggestion": "sc", "position": 1, "engine": "google"})
    h._handle_sgt_create()
    h_stats = _make_handler()
    h_stats._handle_sgt_stats()
    status, data = h_stats._responses[0]
    assert status == 200
    assert "click_through_rate" in data
    # CTR = clicked/shown = 1/2 = 0.50
    assert data["click_through_rate"] == "0.50"
    assert "by_event_type" in data
    assert "avg_position" in data


def test_no_port_9222_in_suggestions():
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0
