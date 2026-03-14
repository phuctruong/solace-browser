# Diagram: 05-solace-runtime-architecture
"""Tests for Network Request Blocker (Task 131). 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token-131").hexdigest()


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
    ys._NET_BLOCK_RULES.clear()
    ys._NET_BLOCKED_LOG.clear()


def _make_rule(**kwargs):
    base = {
        "pattern": "ads.example.com",
        "rule_type": "domain",
        "resource_type": "script",
    }
    base.update(kwargs)
    return base


def test_rule_create():
    """POST creates rule with blr_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/request-blocker/rules", _make_rule())
    h._handle_block_rule_create()
    assert h._status == 201
    r = h._response["rule"]
    assert r["rule_id"].startswith("blr_")


def test_rule_pattern_hashed():
    """POST stores pattern_hash."""
    _reset()
    h = FakeHandler("POST", "/api/v1/request-blocker/rules", _make_rule())
    h._handle_block_rule_create()
    r = h._response["rule"]
    assert "pattern_hash" in r
    assert len(r["pattern_hash"]) == 64


def test_rule_invalid_type():
    """POST with invalid rule_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/request-blocker/rules", _make_rule(rule_type="invalid"))
    h._handle_block_rule_create()
    assert h._status == 400


def test_rule_invalid_resource():
    """POST with invalid resource_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/request-blocker/rules", _make_rule(resource_type="video"))
    h._handle_block_rule_create()
    assert h._status == 400


def test_rule_list():
    """GET returns list of rules."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/request-blocker/rules", _make_rule())
    h_create._handle_block_rule_create()
    h = FakeHandler("GET", "/api/v1/request-blocker/rules")
    h._handle_block_rules_list()
    assert h._status == 200
    assert isinstance(h._response["rules"], list)
    assert h._response["total"] >= 1


def test_rule_delete():
    """DELETE removes rule."""
    _reset()
    h_create = FakeHandler("POST", "/api/v1/request-blocker/rules", _make_rule())
    h_create._handle_block_rule_create()
    rid = h_create._response["rule"]["rule_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/request-blocker/rules/{rid}")
    h_del._handle_block_rule_delete(rid)
    assert h_del._status == 200
    assert not any(r["rule_id"] == rid for r in ys._NET_BLOCK_RULES)


def test_blocked_log():
    """POST to blocked-log creates entry with blk_ prefix and increments hit_count."""
    _reset()
    h_rule = FakeHandler("POST", "/api/v1/request-blocker/rules", _make_rule())
    h_rule._handle_block_rule_create()
    rid = h_rule._response["rule"]["rule_id"]

    h_log = FakeHandler("POST", "/api/v1/request-blocker/blocked-log", {"rule_id": rid, "url": "https://ads.example.com/track"})
    h_log._handle_blocked_log_create()
    assert h_log._status == 201
    b = h_log._response["blocked"]
    assert b["blocked_id"].startswith("blk_")

    # hit_count incremented
    rule = next(r for r in ys._NET_BLOCK_RULES if r["rule_id"] == rid)
    assert rule["hit_count"] == 1


def test_blocked_log_invalid_rule():
    """POST to blocked-log with nonexistent rule_id returns 404."""
    _reset()
    h = FakeHandler("POST", "/api/v1/request-blocker/blocked-log", {"rule_id": "blr_nonexistent", "url": "https://x.com"})
    h._handle_blocked_log_create()
    assert h._status == 404


def test_rule_types_list():
    """GET /rule-types returns 5 rule types."""
    _reset()
    h = FakeHandler("GET", "/api/v1/request-blocker/rule-types")
    h._handle_block_rule_types()
    assert h._status == 200
    assert len(h._response["rule_types"]) == 5


def test_no_port_9222_in_blocker():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
