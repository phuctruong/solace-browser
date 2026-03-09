"""
Tests for Task 102 — Keyboard Macro Manager
Browser: yinyang_server.py routes /api/v1/macros/*
"""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
import json
import hashlib
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token").hexdigest()


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

    def _send_json(self, data, status=200):
        self._status = status
        self._response = data

    def _check_auth(self):
        if not self._auth:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}


def setup_function():
    ys._MACROS.clear()


def _create_macro(trigger_type="hotkey", actions=None):
    if actions is None:
        actions = [{"action_type": "type_text", "params_hash": "a" * 64}]
    h = FakeHandler("POST", "/api/v1/macros", {
        "name_hash": "n" * 64,
        "trigger_type": trigger_type,
        "trigger_hash": "t" * 64,
        "actions": actions,
    })
    h._handle_macro_create()
    return h


def test_create_macro_ok():
    h = _create_macro()
    assert h._status == 201
    assert h._response["macro"]["macro_id"].startswith("mac_")
    assert h._response["macro"]["execute_count"] == 0
    assert h._response["macro"]["last_executed_at"] is None


def test_create_macro_invalid_trigger():
    h = FakeHandler("POST", "/api/v1/macros", {
        "name_hash": "n" * 64,
        "trigger_type": "BADTRIGGER",
        "trigger_hash": "t" * 64,
        "actions": [],
    })
    h._handle_macro_create()
    assert h._status == 400
    assert "trigger_type" in h._response["error"]


def test_create_macro_invalid_action_type():
    h = FakeHandler("POST", "/api/v1/macros", {
        "name_hash": "n" * 64,
        "trigger_type": "hotkey",
        "trigger_hash": "t" * 64,
        "actions": [{"action_type": "BADACTION", "params_hash": "p" * 64}],
    })
    h._handle_macro_create()
    assert h._status == 400
    assert "action_type" in h._response["error"]


def test_create_macro_too_many_actions():
    actions = [{"action_type": "click_element", "params_hash": "p" * 64}] * 21
    h = FakeHandler("POST", "/api/v1/macros", {
        "name_hash": "n" * 64,
        "trigger_type": "hotkey",
        "trigger_hash": "t" * 64,
        "actions": actions,
    })
    h._handle_macro_create()
    assert h._status == 400


def test_list_macros():
    _create_macro()
    h = FakeHandler("GET", "/api/v1/macros")
    h._handle_macro_list()
    assert h._status == 200
    assert h._response["total"] >= 1


def test_delete_macro():
    ch = _create_macro()
    macro_id = ch._response["macro"]["macro_id"]

    h = FakeHandler("DELETE", f"/api/v1/macros/{macro_id}")
    h._handle_macro_delete(macro_id)
    assert h._status == 200
    assert h._response["status"] == "deleted"


def test_delete_macro_not_found():
    h = FakeHandler("DELETE", "/api/v1/macros/mac_nonexistent")
    h._handle_macro_delete("mac_nonexistent")
    assert h._status == 404


def test_execute_macro():
    ch = _create_macro()
    macro_id = ch._response["macro"]["macro_id"]

    h = FakeHandler("POST", f"/api/v1/macros/{macro_id}/execute")
    h._handle_macro_execute(macro_id)
    assert h._status == 200
    assert h._response["macro"]["execute_count"] == 1
    assert h._response["macro"]["last_executed_at"] is not None


def test_execute_macro_not_found():
    h = FakeHandler("POST", "/api/v1/macros/mac_nonexistent/execute")
    h._handle_macro_execute("mac_nonexistent")
    assert h._status == 404


def test_triggers_public():
    h = FakeHandler("GET", "/api/v1/macros/triggers", auth=False)
    h._handle_macro_triggers()
    assert h._status == 200
    assert "trigger_types" in h._response
    assert "hotkey" in h._response["trigger_types"]
    assert "action_types" in h._response
