"""
Tests for Task 146 — Focus Mode
Browser: yinyang_server.py routes /api/v1/focus/*
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


def test_session_create():
    import yinyang_server as ys
    ys._FOCUS146_SESSIONS.clear()
    h = _make_handler({"session_type": "deep_work", "target_minutes": 25})
    h._handle_focus146_session_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["session"]["session_id"].startswith("fcs_")
    assert data["session"]["status"] == "active"
    assert data["session"]["ended_at"] is None
    assert data["session"]["actual_minutes"] is None


def test_session_invalid_type():
    import yinyang_server as ys
    ys._FOCUS146_SESSIONS.clear()
    h = _make_handler({"session_type": "napping", "target_minutes": 25})
    h._handle_focus146_session_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_session_zero_target():
    import yinyang_server as ys
    ys._FOCUS146_SESSIONS.clear()
    h = _make_handler({"session_type": "reading", "target_minutes": 0})
    h._handle_focus146_session_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_session_end():
    import yinyang_server as ys
    ys._FOCUS146_SESSIONS.clear()
    h1 = _make_handler({"session_type": "coding", "target_minutes": 30})
    h1._handle_focus146_session_create()
    session_id = h1._responses[0][1]["session"]["session_id"]
    h2 = _make_handler()
    h2._handle_focus146_session_end(session_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["session"]["status"] == "completed"
    assert data["session"]["ended_at"] is not None
    assert data["session"]["actual_minutes"] is not None
    assert isinstance(data["session"]["actual_minutes"], int)


def test_session_end_twice():
    import yinyang_server as ys
    ys._FOCUS146_SESSIONS.clear()
    h1 = _make_handler({"session_type": "research", "target_minutes": 45})
    h1._handle_focus146_session_create()
    session_id = h1._responses[0][1]["session"]["session_id"]
    h2 = _make_handler()
    h2._handle_focus146_session_end(session_id)
    h3 = _make_handler()
    h3._handle_focus146_session_end(session_id)
    status, data = h3._responses[0]
    assert status == 409


def test_session_list():
    import yinyang_server as ys
    ys._FOCUS146_SESSIONS.clear()
    h1 = _make_handler({"session_type": "writing", "target_minutes": 20})
    h1._handle_focus146_session_create()
    h2 = _make_handler()
    h2._handle_focus146_sessions_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["sessions"], list)


def test_session_delete():
    import yinyang_server as ys
    ys._FOCUS146_SESSIONS.clear()
    h1 = _make_handler({"session_type": "planning", "target_minutes": 15})
    h1._handle_focus146_session_create()
    session_id = h1._responses[0][1]["session"]["session_id"]
    h2 = _make_handler()
    h2._handle_focus146_session_delete(session_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    h3 = _make_handler()
    h3._handle_focus146_sessions_list()
    _, list_data = h3._responses[0]
    assert list_data["total"] == 0


def test_session_not_found():
    import yinyang_server as ys
    ys._FOCUS146_SESSIONS.clear()
    h = _make_handler()
    h._handle_focus146_session_delete("fcs_notexist")
    status, data = h._responses[0]
    assert status == 404


def test_focus_stats():
    import yinyang_server as ys
    ys._FOCUS146_SESSIONS.clear()
    # Create and end one session
    h1 = _make_handler({"session_type": "deep_work", "target_minutes": 25})
    h1._handle_focus146_session_create()
    session_id = h1._responses[0][1]["session"]["session_id"]
    h2 = _make_handler()
    h2._handle_focus146_session_end(session_id)
    # Create another but don't end it
    h3 = _make_handler({"session_type": "reading", "target_minutes": 30})
    h3._handle_focus146_session_create()
    h_stats = _make_handler()
    h_stats._handle_focus146_stats()
    status, data = h_stats._responses[0]
    assert status == 200
    assert data["total_sessions"] == 2
    assert data["completed_count"] == 1
    # total_minutes and avg_minutes must be Decimal strings
    total_min = data["total_minutes"]
    avg_min = data["avg_minutes"]
    assert isinstance(total_min, str)
    assert isinstance(avg_min, str)
    float(total_min)
    float(avg_min)
    assert "by_type" in data


def test_no_port_9222_in_focus():
    import re
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0, f"Found port 9222 at positions: {matches}"
