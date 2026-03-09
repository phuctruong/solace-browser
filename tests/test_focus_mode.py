"""
Tests for Task 060 — Focus Mode
Browser: yinyang_server.py routes /api/v1/focus/*
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


def _reset_focus(ys):
    ys._FOCUS_SESSION = None
    ys._FOCUS_BLOCKLIST.clear()
    ys._FOCUS_HISTORY.clear()


def test_focus_status_no_session():
    import yinyang_server as ys
    _reset_focus(ys)
    h = _make_handler()
    h._handle_focus_status()
    status, data = h._responses[0]
    assert status == 200
    assert data["active"] is False
    assert data["session"] is None


def test_focus_start_ok():
    import yinyang_server as ys
    _reset_focus(ys)
    h = _make_handler({"focus_type": "deep-work", "duration_minutes": 25})
    h._handle_focus_start()
    status, data = h._responses[0]
    assert status == 201
    assert data["status"] == "started"
    assert data["session"]["session_id"].startswith("fs_")
    assert data["session"]["focus_type"] == "deep-work"


def test_focus_start_invalid_type():
    import yinyang_server as ys
    _reset_focus(ys)
    h = _make_handler({"focus_type": "gaming", "duration_minutes": 25})
    h._handle_focus_start()
    status, data = h._responses[0]
    assert status == 400
    assert "focus_type" in data["error"]


def test_focus_start_conflict():
    import yinyang_server as ys
    _reset_focus(ys)
    h = _make_handler({"focus_type": "coding", "duration_minutes": 30})
    h._handle_focus_start()
    h2 = _make_handler({"focus_type": "writing", "duration_minutes": 20})
    h2._handle_focus_start()
    status, data = h2._responses[0]
    assert status == 409


def test_focus_stop_ok():
    import yinyang_server as ys
    _reset_focus(ys)
    h = _make_handler({"focus_type": "reading", "duration_minutes": 45})
    h._handle_focus_start()

    h2 = _make_handler()
    h2._handle_focus_stop()
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "stopped"
    assert ys._FOCUS_SESSION is None
    assert len(ys._FOCUS_HISTORY) == 1


def test_focus_stop_no_session():
    import yinyang_server as ys
    _reset_focus(ys)
    h = _make_handler()
    h._handle_focus_stop()
    status, data = h._responses[0]
    assert status == 404


def test_focus_blocklist_add_ok():
    import yinyang_server as ys
    _reset_focus(ys)
    h = _make_handler({"pattern": "*.twitter.com"})
    h._handle_focus_blocklist_add()
    status, data = h._responses[0]
    assert status == 201
    assert data["entry"]["pattern_id"].startswith("bl_")
    assert data["entry"]["pattern"] == "*.twitter.com"


def test_focus_blocklist_delete_ok():
    import yinyang_server as ys
    _reset_focus(ys)
    h = _make_handler({"pattern": "reddit.com"})
    h._handle_focus_blocklist_add()
    pattern_id = h._responses[0][1]["entry"]["pattern_id"]

    h2 = _make_handler()
    h2._handle_focus_blocklist_delete(pattern_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"


def test_focus_history_populated():
    import yinyang_server as ys
    _reset_focus(ys)
    h = _make_handler({"focus_type": "custom", "duration_minutes": 60})
    h._handle_focus_start()
    h2 = _make_handler()
    h2._handle_focus_stop()

    h3 = _make_handler()
    h3._handle_focus_history()
    status, data = h3._responses[0]
    assert status == 200
    assert data["total"] >= 1


def test_focus_start_requires_auth():
    import yinyang_server as ys
    _reset_focus(ys)
    h = _make_handler({"focus_type": "deep-work", "duration_minutes": 25}, auth=False)
    h._handle_focus_start()
    status, _ = h._responses[0]
    assert status == 401
