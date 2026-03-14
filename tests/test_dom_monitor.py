# Diagram: 05-solace-runtime-architecture
"""Tests for DOM Monitor (Task 107). 10 tests."""
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
    ys._DOM_RULES.clear()
    ys._DOM_EVENTS.clear()


def test_dom_rule_create():
    """POST creates rule with dmr_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dom-monitor/rules", {
        "page_hash": "pg_hash",
        "selector_hash": "sel_hash",
        "selector_type": "css",
    })
    h._handle_dom_rule_create()
    assert h._status == 201
    rule = h._response["rule"]
    assert rule["rule_id"].startswith("dmr_")
    assert rule["selector_type"] == "css"


def test_dom_rule_invalid_selector_type():
    """POST with invalid selector_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dom-monitor/rules", {
        "page_hash": "pg",
        "selector_hash": "sel",
        "selector_type": "INVALID",
    })
    h._handle_dom_rule_create()
    assert h._status == 400


def test_dom_rule_list():
    """GET returns rules list."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dom-monitor/rules", {
        "page_hash": "pg", "selector_hash": "sel", "selector_type": "id",
    })
    h._handle_dom_rule_create()
    h2 = FakeHandler("GET", "/api/v1/dom-monitor/rules")
    h2._handle_dom_rule_list()
    assert h2._status == 200
    assert "rules" in h2._response
    assert h2._response["total"] == 1


def test_dom_rule_delete():
    """DELETE rule returns 200."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dom-monitor/rules", {
        "page_hash": "pg", "selector_hash": "sel", "selector_type": "class",
    })
    h._handle_dom_rule_create()
    rule_id = h._response["rule"]["rule_id"]

    dh = FakeHandler("DELETE", f"/api/v1/dom-monitor/rules/{rule_id}")
    dh._handle_dom_rule_delete(rule_id)
    assert dh._status == 200
    assert dh._response["status"] == "deleted"


def test_dom_rule_delete_not_found():
    """DELETE nonexistent rule returns 404."""
    _reset()
    h = FakeHandler("DELETE", "/api/v1/dom-monitor/rules/dmr_nonexistent")
    h._handle_dom_rule_delete("dmr_nonexistent")
    assert h._status == 404


def test_dom_event_record():
    """POST event creates record with dme_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dom-monitor/events", {
        "page_hash": "pg",
        "selector_hash": "sel",
        "change_type": "added",
        "old_value_hash": "old",
        "new_value_hash": "new",
    })
    h._handle_dom_event_record()
    assert h._status == 201
    event = h._response["event"]
    assert event["event_id"].startswith("dme_")
    assert event["change_type"] == "added"
    assert event["old_value_hash"] == "old"


def test_dom_event_invalid_change_type():
    """POST event with invalid change_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dom-monitor/events", {
        "page_hash": "pg",
        "selector_hash": "sel",
        "change_type": "INVALID",
    })
    h._handle_dom_event_record()
    assert h._status == 400


def test_dom_event_list():
    """GET returns events list."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dom-monitor/events", {
        "page_hash": "pg", "selector_hash": "sel", "change_type": "modified",
    })
    h._handle_dom_event_record()
    h2 = FakeHandler("GET", "/api/v1/dom-monitor/events")
    h2._handle_dom_event_list()
    assert h2._status == 200
    assert "events" in h2._response
    assert h2._response["total"] == 1


def test_dom_change_types():
    """GET /change-types returns 6 types."""
    h = FakeHandler("GET", "/api/v1/dom-monitor/change-types")
    h._handle_dom_change_types()
    assert h._status == 200
    assert len(h._response["change_types"]) == 6


def test_dom_event_optional_hashes():
    """POST event without old/new hash succeeds."""
    _reset()
    h = FakeHandler("POST", "/api/v1/dom-monitor/events", {
        "page_hash": "pg",
        "selector_hash": "sel",
        "change_type": "style",
    })
    h._handle_dom_event_record()
    assert h._status == 201
    event = h._response["event"]
    assert "old_value_hash" not in event
    assert "new_value_hash" not in event
