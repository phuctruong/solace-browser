# Diagram: 05-solace-runtime-architecture
"""Tests for Cookie Consent Tracker (Task 111). 10 tests."""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
import json
import hashlib
from io import BytesIO


VALID_TOKEN = hashlib.sha256(b"test-token").hexdigest()

# Task 111 categories: necessary, functional, analytics, marketing, preferences
VALID_CATEGORIES = ["necessary", "functional", "analytics", "marketing", "preferences"]


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
    ys._COOKIE_DECISIONS.clear()


def test_decision_create():
    """POST creates decision with ccd_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/cookie-consent/decisions", {
        "site_url": "https://example.com",
        "decision": "accept_all",
        "categories_accepted": ["necessary", "analytics"],
    })
    h._handle_cookie_decision_create()
    assert h._status == 201
    decision = h._response["decision"]
    assert decision["decision_id"].startswith("ccd_")
    assert decision["decision"] == "accept_all"


def test_decision_site_hashed():
    """POST stores site_hash, not raw site URL."""
    _reset()
    h = FakeHandler("POST", "/api/v1/cookie-consent/decisions", {
        "site_url": "https://private.example.com/path",
        "decision": "reject_all",
        "categories_accepted": [],
    })
    h._handle_cookie_decision_create()
    assert h._status == 201
    decision = h._response["decision"]
    assert "site_hash" in decision
    assert "https://private.example.com/path" not in str(decision)
    expected = hashlib.sha256(b"https://private.example.com/path").hexdigest()
    assert decision["site_hash"] == expected


def test_decision_invalid_type():
    """POST with unknown decision type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/cookie-consent/decisions", {
        "site_url": "https://example.com",
        "decision": "UNKNOWN_DECISION",
        "categories_accepted": [],
    })
    h._handle_cookie_decision_create()
    assert h._status == 400


def test_decision_invalid_category():
    """POST with unknown category in categories_accepted returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/cookie-consent/decisions", {
        "site_url": "https://example.com",
        "decision": "custom",
        "categories_accepted": ["necessary", "INVALID_CATEGORY"],
    })
    h._handle_cookie_decision_create()
    assert h._status == 400


def test_decision_list():
    """GET returns list of decisions."""
    _reset()
    h = FakeHandler("POST", "/api/v1/cookie-consent/decisions", {
        "site_url": "https://example.com",
        "decision": "accept_all",
        "categories_accepted": ["necessary"],
    })
    h._handle_cookie_decision_create()
    h2 = FakeHandler("GET", "/api/v1/cookie-consent/decisions")
    h2._handle_cookie_decision_list()
    assert h2._status == 200
    assert "decisions" in h2._response
    assert h2._response["total"] == 1


def test_decision_delete():
    """DELETE removes decision."""
    _reset()
    h = FakeHandler("POST", "/api/v1/cookie-consent/decisions", {
        "site_url": "https://example.com",
        "decision": "withdraw",
        "categories_accepted": [],
    })
    h._handle_cookie_decision_create()
    decision_id = h._response["decision"]["decision_id"]

    dh = FakeHandler("DELETE", f"/api/v1/cookie-consent/decisions/{decision_id}")
    dh._handle_cookie_decision_delete(decision_id)
    assert dh._status == 200
    assert dh._response["status"] == "deleted"

    lh = FakeHandler("GET", "/api/v1/cookie-consent/decisions")
    lh._handle_cookie_decision_list()
    assert lh._response["total"] == 0


def test_decision_not_found():
    """DELETE nonexistent decision returns 404."""
    _reset()
    h = FakeHandler("DELETE", "/api/v1/cookie-consent/decisions/ccd_notexist")
    h._handle_cookie_decision_delete("ccd_notexist")
    assert h._status == 404


def test_consent_stats():
    """GET /stats returns by_decision and totals."""
    _reset()
    for decision, cats in [
        ("accept_all", ["necessary", "analytics"]),
        ("accept_all", ["necessary"]),
        ("reject_all", []),
    ]:
        h = FakeHandler("POST", "/api/v1/cookie-consent/decisions", {
            "site_url": "https://example.com",
            "decision": decision,
            "categories_accepted": cats,
        })
        h._handle_cookie_decision_create()

    sh = FakeHandler("GET", "/api/v1/cookie-consent/stats")
    sh._handle_cookie_consent_stats()
    assert sh._status == 200
    data = sh._response
    assert data["total_decisions"] == 3
    assert "by_decision" in data
    assert data["by_decision"]["accept_all"] == 2
    assert data["by_decision"]["reject_all"] == 1
    assert data["most_common_decision"] == "accept_all"


def test_categories_list():
    """GET /categories returns 5 consent categories."""
    h = FakeHandler("GET", "/api/v1/cookie-consent/categories")
    h._handle_cookie_categories_list()
    assert h._status == 200
    assert len(h._response["categories"]) == 5
    assert "necessary" in h._response["categories"]
    assert "marketing" in h._response["categories"]


def test_no_legacy_debug_port_in_cookie():
    """Grep check: legacy debug port must not appear in this file."""
    banned_port = "92" + "22"  # split to avoid self-matching
    source = pathlib.Path(__file__).read_text()
    assert banned_port not in source
