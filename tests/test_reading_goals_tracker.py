# Diagram: 05-solace-runtime-architecture
"""Tests for Reading Goals Tracker (Task 141). 10 tests."""
import sys
import pathlib
import hashlib
import json
from decimal import Decimal

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token-141").hexdigest()


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method, path, body=None, auth=True):
        self.command = method
        self.path = path
        self._body = json.dumps(body).encode() if body else b""
        self._auth = auth
        self._status = None
        self._response = None
        self.headers = {
            "Content-Length": str(len(self._body)),
            "Authorization": f"Bearer {VALID_TOKEN}" if auth else "",
        }
        self.server = type("S", (), {
            "session_token_sha256": VALID_TOKEN,
            "repo_root": str(REPO_ROOT),
        })()
        self.rfile = BytesIO(self._body)
        self.wfile = BytesIO()

    def send_response(self, code):
        self._status = code

    def send_header(self, *a):
        pass

    def end_headers(self):
        pass

    def _send_json(self, data, code=200):
        self._status = code
        self._response = data

    def _check_auth(self):
        if not self._auth:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}


def _reset():
    ys._READING_GOALS.clear()


def _make_goal(**kwargs):
    base = {
        "goal_type": "daily_minutes",
        "target_value": "30",
        "deadline": "2026-12-31",
    }
    base.update(kwargs)
    return base


def test_goal_create():
    """POST creates goal with rdg_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reading-goals/goals", _make_goal())
    h._handle_goal_create()
    assert h._status == 201
    g = h._response["goal"]
    assert g["goal_id"].startswith("rdg_")


def test_goal_invalid_type():
    """POST with unknown goal_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reading-goals/goals", _make_goal(goal_type="invalid_type"))
    h._handle_goal_create()
    assert h._status == 400


def test_goal_invalid_target():
    """POST with non-numeric target_value returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reading-goals/goals", _make_goal(target_value="abc"))
    h._handle_goal_create()
    assert h._status == 400


def test_goal_zero_target():
    """POST with target_value=0 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reading-goals/goals", _make_goal(target_value="0"))
    h._handle_goal_create()
    assert h._status == 400


def test_goal_list():
    """GET returns list of goals."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/reading-goals/goals", _make_goal())
    h_c._handle_goal_create()
    h = FakeHandler("GET", "/api/v1/reading-goals/goals")
    h._handle_goals_list()
    assert h._status == 200
    assert isinstance(h._response["goals"], list)
    assert h._response["total"] >= 1


def test_goal_delete():
    """DELETE removes goal."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/reading-goals/goals", _make_goal())
    h_c._handle_goal_create()
    gid = h_c._response["goal"]["goal_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/reading-goals/goals/{gid}")
    h_del._handle_goal_delete(gid)
    assert h_del._status == 200
    assert not any(g["goal_id"] == gid for g in ys._READING_GOALS)


def test_goal_progress():
    """POST /progress updates current_value."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/reading-goals/goals", _make_goal(target_value="60"))
    h_c._handle_goal_create()
    gid = h_c._response["goal"]["goal_id"]
    h_p = FakeHandler("POST", f"/api/v1/reading-goals/goals/{gid}/progress", {"increment": "15"})
    h_p._handle_goal_progress(gid)
    assert h_p._status == 200
    updated = h_p._response["goal"]
    assert Decimal(updated["current_value"]) == Decimal("15")
    assert updated["completed"] is False


def test_goal_completed():
    """Progress bringing current >= target sets completed=True."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/reading-goals/goals", _make_goal(target_value="10"))
    h_c._handle_goal_create()
    gid = h_c._response["goal"]["goal_id"]
    h_p = FakeHandler("POST", f"/api/v1/reading-goals/goals/{gid}/progress", {"increment": "10"})
    h_p._handle_goal_progress(gid)
    assert h_p._response["goal"]["completed"] is True


def test_goal_stats():
    """GET /stats returns completion_rate as Decimal string."""
    _reset()
    # Create one goal and complete it
    h_c = FakeHandler("POST", "/api/v1/reading-goals/goals", _make_goal(target_value="5"))
    h_c._handle_goal_create()
    gid = h_c._response["goal"]["goal_id"]
    h_p = FakeHandler("POST", f"/api/v1/reading-goals/goals/{gid}/progress", {"increment": "5"})
    h_p._handle_goal_progress(gid)
    h = FakeHandler("GET", "/api/v1/reading-goals/stats")
    h._handle_goals_stats()
    assert h._status == 200
    assert "completion_rate" in h._response
    # Should be parseable as Decimal
    Decimal(h._response["completion_rate"])


def test_no_port_9222_in_goals():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
