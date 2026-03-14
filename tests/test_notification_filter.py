# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 104 — Notification Filter
Browser: yinyang_server.py routes /api/v1/notification-filter/*
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
    ys._FILTER_RULES.clear()
    ys._NOTIFICATION_LOG.clear()


def test_create_rule_ok():
    h = FakeHandler("POST", "/api/v1/notification-filter/rules", {
        "site_hash": "a" * 64,
        "action": "block",
        "title_hash": "b" * 64,
    })
    h._handle_notif_filter_rule_create()
    assert h._status == 201
    assert h._response["rule"]["rule_id"].startswith("nfr_")
    assert h._response["rule"]["action"] == "block"


def test_create_rule_invalid_action():
    h = FakeHandler("POST", "/api/v1/notification-filter/rules", {
        "site_hash": "c" * 64,
        "action": "BADACTION",
        "title_hash": "d" * 64,
    })
    h._handle_notif_filter_rule_create()
    assert h._status == 400
    assert "action" in h._response["error"]


def test_create_rule_requires_auth():
    h = FakeHandler("POST", "/api/v1/notification-filter/rules", {
        "site_hash": "e" * 64,
        "action": "allow",
        "title_hash": "f" * 64,
    }, auth=False)
    h._handle_notif_filter_rule_create()
    assert h._status == 401


def test_list_rules():
    h = FakeHandler("POST", "/api/v1/notification-filter/rules", {
        "site_hash": "g" * 64,
        "action": "mute",
        "title_hash": "h" * 64,
    })
    h._handle_notif_filter_rule_create()

    h2 = FakeHandler("GET", "/api/v1/notification-filter/rules")
    h2._handle_notif_filter_rule_list()
    assert h2._status == 200
    assert h2._response["total"] >= 1


def test_delete_rule():
    h = FakeHandler("POST", "/api/v1/notification-filter/rules", {
        "site_hash": "i" * 64,
        "action": "delay",
        "title_hash": "j" * 64,
    })
    h._handle_notif_filter_rule_create()
    rule_id = h._response["rule"]["rule_id"]

    h2 = FakeHandler("DELETE", f"/api/v1/notification-filter/rules/{rule_id}")
    h2._handle_notif_filter_rule_delete(rule_id)
    assert h2._status == 200
    assert h2._response["status"] == "deleted"


def test_delete_rule_not_found():
    h = FakeHandler("DELETE", "/api/v1/notification-filter/rules/nfr_nonexistent")
    h._handle_notif_filter_rule_delete("nfr_nonexistent")
    assert h._status == 404


def test_log_notification_ok():
    h = FakeHandler("POST", "/api/v1/notification-filter/log", {
        "site_hash": "k" * 64,
        "title_hash": "l" * 64,
        "priority": "high",
        "action_taken": "block",
    })
    h._handle_notif_filter_log_add()
    assert h._status == 201
    assert h._response["entry"]["log_id"].startswith("nfl_")
    assert h._response["entry"]["priority"] == "high"


def test_log_invalid_priority():
    h = FakeHandler("POST", "/api/v1/notification-filter/log", {
        "site_hash": "m" * 64,
        "title_hash": "n" * 64,
        "priority": "BADPRIORITY",
        "action_taken": "allow",
    })
    h._handle_notif_filter_log_add()
    assert h._status == 400
    assert "priority" in h._response["error"]


def test_log_invalid_action_taken():
    h = FakeHandler("POST", "/api/v1/notification-filter/log", {
        "site_hash": "o" * 64,
        "title_hash": "p" * 64,
        "priority": "normal",
        "action_taken": "BADACTION",
    })
    h._handle_notif_filter_log_add()
    assert h._status == 400
    assert "action_taken" in h._response["error"]


def test_list_log():
    h = FakeHandler("POST", "/api/v1/notification-filter/log", {
        "site_hash": "q" * 64,
        "title_hash": "r" * 64,
        "priority": "urgent",
        "action_taken": "redirect",
    })
    h._handle_notif_filter_log_add()

    h2 = FakeHandler("GET", "/api/v1/notification-filter/log")
    h2._handle_notif_filter_log_list()
    assert h2._status == 200
    assert h2._response["total"] >= 1


def test_actions_public():
    h = FakeHandler("GET", "/api/v1/notification-filter/actions", auth=False)
    h._handle_notif_filter_actions()
    assert h._status == 200
    assert "actions" in h._response
    assert "block" in h._response["actions"]
    assert "priorities" in h._response
