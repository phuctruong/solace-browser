"""Tests for Task 084 — Request Interceptor."""
import sys
import json
import hashlib

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "d" * 64


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


def make_handler(body=None):
    h = FakeHandler()
    if body is not None:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def clear_state():
    with ys._INTERCEPT_LOCK:
        ys._INTERCEPT_RULES.clear()
        ys._INTERCEPT_LOG.clear()


def test_rule_create():
    """POST → irl_ prefix returned."""
    clear_state()
    h = make_handler({
        "rule_type": "block",
        "action": "block",
        "method": "GET",
        "pattern": "*.ads.example.com/*",
    })
    h._handle_interceptor_rule_create()
    code, data = h._responses[0]
    assert code == 201
    assert data["rule"]["rule_id"].startswith("irl_")


def test_rule_pattern_hashed():
    """pattern_hash present, no raw pattern stored."""
    clear_state()
    pattern = "https://tracking.example.com/pixel"
    h = make_handler({
        "rule_type": "log_only",
        "action": "allow",
        "method": "ALL",
        "pattern": pattern,
    })
    h._handle_interceptor_rule_create()
    code, data = h._responses[0]
    assert code == 201
    rule = data["rule"]
    assert "pattern_hash" in rule
    assert "pattern" not in rule
    expected = hashlib.sha256(pattern.encode()).hexdigest()
    assert rule["pattern_hash"] == expected


def test_rule_invalid_type():
    """Unknown rule_type → 400."""
    clear_state()
    h = make_handler({
        "rule_type": "invalid_type_xyz",
        "action": "block",
        "method": "GET",
        "pattern": "*.example.com",
    })
    h._handle_interceptor_rule_create()
    code, data = h._responses[0]
    assert code == 400
    assert "error" in data


def test_rule_invalid_action():
    """Unknown action → 400."""
    clear_state()
    h = make_handler({
        "rule_type": "block",
        "action": "teleport",
        "method": "GET",
        "pattern": "*.example.com",
    })
    h._handle_interceptor_rule_create()
    code, data = h._responses[0]
    assert code == 400
    assert "error" in data


def test_rule_list():
    """GET /rules → list returned."""
    clear_state()
    save = make_handler({
        "rule_type": "redirect",
        "action": "redirect",
        "method": "GET",
        "pattern": "*.old-domain.com/*",
    })
    save._handle_interceptor_rule_create()
    h = make_handler()
    h._handle_interceptor_rules_list()
    code, data = h._responses[0]
    assert code == 200
    assert "rules" in data
    assert len(data["rules"]) >= 1


def test_rule_delete():
    """DELETE → removed."""
    clear_state()
    save = make_handler({
        "rule_type": "block",
        "action": "block",
        "method": "POST",
        "pattern": "api.spam.com/track",
    })
    save._handle_interceptor_rule_create()
    rule_id = save._responses[0][1]["rule"]["rule_id"]
    h = make_handler()
    h._handle_interceptor_rule_delete(rule_id)
    code, data = h._responses[0]
    assert code == 200
    assert data["status"] == "deleted"
    with ys._INTERCEPT_LOCK:
        ids = [r["rule_id"] for r in ys._INTERCEPT_RULES]
    assert rule_id not in ids


def test_rule_delete_not_found():
    """DELETE irl_notexist → 404."""
    clear_state()
    h = make_handler()
    h._handle_interceptor_rule_delete("irl_doesnotexist")
    code, data = h._responses[0]
    assert code == 404
    assert "error" in data


def test_intercept_log_record():
    """POST /log → ilog_ prefix."""
    clear_state()
    h = make_handler({
        "url": "https://tracking.example.com/pixel.gif",
        "action_taken": "block",
    })
    h._handle_interceptor_log_record()
    code, data = h._responses[0]
    assert code == 201
    assert data["log_id"].startswith("ilog_")


def test_intercept_log_list():
    """GET /log → list returned."""
    clear_state()
    rec = make_handler({"url": "https://ads.example.com/banner.js", "action_taken": "log_only"})
    rec._handle_interceptor_log_record()
    h = make_handler()
    h._handle_interceptor_log_list()
    code, data = h._responses[0]
    assert code == 200
    assert "log" in data
    assert len(data["log"]) >= 1


def test_no_port_9222_in_interceptor():
    """No port 9222 in request interceptor code."""
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found — BANNED"
