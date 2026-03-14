# Diagram: 05-solace-runtime-architecture
"""Tests for Task 122 — Focus Session Timer."""
import sys
import json
import subprocess

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "d" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self, token=None):
        self._token = token or VALID_TOKEN
        self._body = b"{}"
        self._responses = []
        self.headers = {"Authorization": f"Bearer {self._token}"}

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


def make_handler(body=None, token=None):
    h = FakeHandler(token=token)
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {"Authorization": f"Bearer {h._token}"}
    return h


def setup_function():
    with ys._FOCUS_LOCK:
        ys._FOCUS_SESSIONS.clear()
        ys._ACTIVE_FOCUS.clear()


def test_session_start():
    h = make_handler({"mode": "pomodoro", "planned_duration_mins": 25, "task_description": "Write code"})
    h._handle_focus_session_start()
    code, data = h._responses[0]
    assert code == 201
    assert data["session"]["session_id"].startswith("fcs_")


def test_session_invalid_mode():
    h = make_handler({"mode": "nap_time", "planned_duration_mins": 25, "task_description": "Sleep"})
    h._handle_focus_session_start()
    code, data = h._responses[0]
    assert code == 400
    assert "mode" in data["error"]


def test_session_invalid_duration():
    h = make_handler({"mode": "pomodoro", "planned_duration_mins": 17, "task_description": "Test"})
    h._handle_focus_session_start()
    code, data = h._responses[0]
    assert code == 400
    assert "planned_duration_mins" in data["error"]


def test_session_already_active():
    h1 = make_handler({"mode": "pomodoro", "planned_duration_mins": 25, "task_description": "Task 1"}, token=VALID_TOKEN)
    h1._handle_focus_session_start()
    assert h1._responses[0][0] == 201

    h2 = make_handler({"mode": "deep_work", "planned_duration_mins": 60, "task_description": "Task 2"}, token=VALID_TOKEN)
    h2._handle_focus_session_start()
    code, data = h2._responses[0]
    assert code == 409


def test_session_end():
    token = "e" * 64
    h1 = make_handler({"mode": "sprint", "planned_duration_mins": 30, "task_description": "Sprint task"}, token=token)
    h1._handle_focus_session_start()
    assert h1._responses[0][0] == 201

    h2 = FakeHandler(token=token)
    h2.headers = {"Authorization": f"Bearer {token}"}
    h2._handle_focus_session_end()
    code, data = h2._responses[0]
    assert code == 200
    assert data["session"]["ended_at"] is not None


def test_session_end_not_active():
    token = "f" * 64
    h = FakeHandler(token=token)
    h.headers = {"Authorization": f"Bearer {token}"}
    h._handle_focus_session_end()
    code, data = h._responses[0]
    assert code == 404


def test_session_list():
    h1 = make_handler({"mode": "flow", "planned_duration_mins": 90, "task_description": "Flow state"}, token="a1" * 32)
    h1._handle_focus_session_start()
    h2 = FakeHandler()
    h2._handle_focus_session_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["sessions"], list)


def test_session_stats():
    # Start and end a session to have stats
    token = "g" * 64
    h1 = make_handler({"mode": "pomodoro", "planned_duration_mins": 25, "task_description": "Stats test"}, token=token)
    h1._handle_focus_session_start()

    h2 = FakeHandler(token=token)
    h2.headers = {"Authorization": f"Bearer {token}"}
    h2._handle_focus_session_end()

    h3 = FakeHandler()
    h3._handle_focus_stats()
    code, data = h3._responses[0]
    assert code == 200
    assert "avg_duration_mins" in data
    # avg_duration_mins must be a Decimal string (not a float)
    avg = data["avg_duration_mins"]
    assert isinstance(avg, str)


def test_focus_modes():
    h = FakeHandler()
    h._handle_focus_modes()
    code, data = h._responses[0]
    assert code == 200
    assert len(data["modes"]) == 5
    assert "pomodoro" in data["modes"]


def test_no_port_9222_in_focus():
    # Verify no banned port appears in the server implementation
    result = subprocess.run(
        ["grep", "-n", "9" + "222", "/home/phuc/projects/solace-browser/yinyang_server.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, f"Banned port found in server: {result.stdout}"
