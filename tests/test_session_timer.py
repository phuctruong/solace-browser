# Diagram: 05-solace-runtime-architecture
"""Tests for Task 075 — Session Timer."""
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

    def send_response(self, code):
        self._responses.append((code, {}))

    def end_headers(self):
        pass

    def _timer_token_key(self):
        return "test_user_key"


def make_handler(body=None):
    h = FakeHandler()
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def setup_function():
    with ys._TIMER_LOCK:
        ys._TIMER_ACTIVE.clear()
        ys._TIMER_HISTORY.clear()


def test_timer_start():
    h = make_handler({"session_type": "focus", "goal_minutes": 25})
    h._handle_timer_start()
    code, data = h._responses[0]
    assert code == 201
    assert data["session"]["session_id"].startswith("stm_")
    assert data["session"]["status"] == "active"


def test_timer_start_already_active():
    h = make_handler({"session_type": "focus", "goal_minutes": 25})
    h._handle_timer_start()
    h2 = make_handler({"session_type": "focus", "goal_minutes": 25})
    h2._handle_timer_start()
    code, data = h2._responses[0]
    assert code == 409


def test_timer_current():
    h = make_handler({"session_type": "break", "goal_minutes": 10})
    h._handle_timer_start()
    h2 = FakeHandler()
    h2._handle_timer_current()
    code, data = h2._responses[0]
    assert code == 200
    assert data["active"] is True
    assert data["session"]["session_id"].startswith("stm_")


def test_timer_stop():
    h = make_handler({"session_type": "focus", "goal_minutes": 30})
    h._handle_timer_start()
    h2 = make_handler({})
    h2._handle_timer_stop()
    code, data = h2._responses[0]
    assert code == 200
    assert data["session"]["status"] == "completed"
    assert data["session"]["duration_minutes"] >= 0


def test_timer_stop_no_active():
    h = make_handler({})
    h._handle_timer_stop()
    code, data = h._responses[0]
    assert code == 404


def test_timer_invalid_type():
    h = make_handler({"session_type": "marathon", "goal_minutes": 25})
    h._handle_timer_start()
    code, data = h._responses[0]
    assert code == 400


def test_timer_goal_too_long():
    h = make_handler({"session_type": "focus", "goal_minutes": 481})
    h._handle_timer_start()
    code, data = h._responses[0]
    assert code == 400
    assert "480" in data["error"]


def test_timer_history():
    h = make_handler({"session_type": "focus", "goal_minutes": 5})
    h._handle_timer_start()
    h2 = make_handler({})
    h2._handle_timer_stop()
    h3 = FakeHandler()
    h3._handle_timer_history()
    code, data = h3._responses[0]
    assert code == 200
    assert isinstance(data["history"], list)
    assert data["total"] >= 1


def test_timer_stats():
    h = FakeHandler()
    h._handle_timer_stats()
    code, data = h._responses[0]
    assert code == 200
    assert "today_minutes" in data
    assert "this_week_minutes" in data
    assert "session_count" in data


def test_no_port_9222_in_timer():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found in yinyang_server.py — BANNED"
