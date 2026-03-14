# Diagram: 05-solace-runtime-architecture
"""Tests for Task 074 — Content Blocker."""
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
    with ys._CONTENT_LOCK:
        ys._CONTENT_RULES.clear()
        ys._BLOCK_STATS.clear()


def test_cb_add_rule():
    h = make_handler({"rule_type": "domain", "pattern": "ads.example.com"})
    h._handle_cb_rule_add()
    code, data = h._responses[0]
    assert code == 201
    assert data["rule"]["rule_id"].startswith("cbr_")


def test_cb_list_rules():
    h = make_handler({"rule_type": "tracker", "pattern": "tracker.io"})
    h._handle_cb_rule_add()
    h2 = FakeHandler()
    h2._handle_cb_rules_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["rules"], list)
    assert data["total"] >= 1


def test_cb_invalid_type():
    h = make_handler({"rule_type": "unicorn", "pattern": "x.com"})
    h._handle_cb_rule_add()
    code, data = h._responses[0]
    assert code == 400


def test_cb_delete_rule():
    h = make_handler({"rule_type": "domain", "pattern": "spam.com"})
    h._handle_cb_rule_add()
    rule_id = h._responses[0][1]["rule"]["rule_id"]
    h2 = make_handler()
    h2._handle_cb_rule_delete(rule_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["rule_id"] == rule_id
    with ys._CONTENT_LOCK:
        ids = [r["rule_id"] for r in ys._CONTENT_RULES]
    assert rule_id not in ids


def test_cb_delete_not_found():
    h = make_handler()
    h._handle_cb_rule_delete("cbr_notexist")
    code, data = h._responses[0]
    assert code == 404


def test_cb_check_no_match():
    # Empty rules → no match
    h = make_handler({"url": "https://safe.example.com/page"})
    h._handle_cb_check()
    code, data = h._responses[0]
    assert code == 200
    assert data["matched"] is False
    assert data["rule_id"] is None


def test_cb_stats():
    h = make_handler({"rule_type": "domain", "pattern": "badads.com"})
    h._handle_cb_rule_add()
    h2 = FakeHandler()
    h2._handle_cb_stats()
    code, data = h2._responses[0]
    assert code == 200
    assert "total_rules" in data
    assert data["total_rules"] >= 1


def test_cb_rule_types():
    h = FakeHandler()
    h._handle_cb_rule_types()
    code, data = h._responses[0]
    assert code == 200
    assert len(data["rule_types"]) == 5
    assert "domain" in data["rule_types"]
    assert "tracker" in data["rule_types"]


def test_cb_pattern_hashed():
    pattern = "evil-tracker.net"
    h = make_handler({"rule_type": "tracker", "pattern": pattern})
    h._handle_cb_rule_add()
    code, data = h._responses[0]
    assert code == 201
    rule = data["rule"]
    assert rule["pattern_hash"] == hashlib.sha256(pattern.encode()).hexdigest()
    assert "pattern" not in rule


def test_no_port_9222_in_content_blocker():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found in yinyang_server.py — BANNED"
