"""Tests for Dark Mode Scheduler (Task 142). 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token-142").hexdigest()


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
    ys._DM_SCHEDULES.clear()
    ys._DM_OVERRIDE.clear()


def _make_schedule(**kwargs):
    base = {
        "trigger_type": "time_based",
        "dark_start_hour": 20,
        "dark_end_hour": 7,
        "enabled": True,
    }
    base.update(kwargs)
    return base


def test_schedule_create():
    """POST creates schedule with dms_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dark-mode/schedules", _make_schedule())
    h._handle_dm_schedule_create()
    assert h._status == 201
    s = h._response["schedule"]
    assert s["schedule_id"].startswith("dms_")


def test_schedule_invalid_trigger():
    """POST with unknown trigger_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dark-mode/schedules", _make_schedule(trigger_type="invalid"))
    h._handle_dm_schedule_create()
    assert h._status == 400


def test_schedule_invalid_start_hour():
    """POST with dark_start_hour=24 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dark-mode/schedules", _make_schedule(dark_start_hour=24))
    h._handle_dm_schedule_create()
    assert h._status == 400


def test_schedule_same_hours():
    """POST with dark_start_hour == dark_end_hour returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dark-mode/schedules", _make_schedule(dark_start_hour=22, dark_end_hour=22))
    h._handle_dm_schedule_create()
    assert h._status == 400


def test_schedule_list():
    """GET returns list of schedules."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/dark-mode/schedules", _make_schedule())
    h_c._handle_dm_schedule_create()
    h = FakeHandler("GET", "/api/v1/dark-mode/schedules")
    h._handle_dm_schedules_list()
    assert h._status == 200
    assert isinstance(h._response["schedules"], list)
    assert h._response["total"] >= 1


def test_schedule_delete():
    """DELETE removes schedule."""
    _reset()
    h_c = FakeHandler("POST", "/api/v1/dark-mode/schedules", _make_schedule())
    h_c._handle_dm_schedule_create()
    sid = h_c._response["schedule"]["schedule_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/dark-mode/schedules/{sid}")
    h_del._handle_dm_schedule_delete(sid)
    assert h_del._status == 200
    assert not any(s["schedule_id"] == sid for s in ys._DM_SCHEDULES)


def test_current_mode():
    """GET /current returns mode field."""
    _reset()
    h = FakeHandler("GET", "/api/v1/dark-mode/current")
    h._handle_dm_current()
    assert h._status == 200
    assert "mode" in h._response
    assert h._response["mode"] in ("dark", "light")


def test_override_dark():
    """POST /override sets mode to dark."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dark-mode/override", {"mode": "dark", "until_hour": 6})
    h._handle_dm_override()
    assert h._status == 200
    assert h._response["mode"] == "dark"
    # Verify current reflects override
    h2 = FakeHandler("GET", "/api/v1/dark-mode/current")
    h2._handle_dm_current()
    assert h2._response["mode"] == "dark"
    assert h2._response["source"] == "override"


def test_override_invalid():
    """POST /override with mode=rainbow returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dark-mode/override", {"mode": "rainbow"})
    h._handle_dm_override()
    assert h._status == 400


def test_no_port_9222_in_dark():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
