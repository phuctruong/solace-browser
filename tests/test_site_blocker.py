"""
Tests for Task 065 — Site Blocker
Browser: yinyang_server.py routes /api/v1/blocker/*
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


def test_blocker_rules_empty():
    import yinyang_server as ys
    ys._BLOCKER_RULES.clear()
    h = _make_handler()
    h._handle_blocker_rules_list()
    status, data = h._responses[0]
    assert status == 200
    assert data["rules"] == []
    assert data["total"] == 0


def test_blocker_add_rule():
    import yinyang_server as ys
    ys._BLOCKER_RULES.clear()
    h = _make_handler({
        "rule_type": "domain",
        "pattern": "twitter.com",
        "category": "social-media",
    })
    h._handle_blocker_rule_add()
    status, data = h._responses[0]
    assert status == 201
    assert data["status"] == "created"
    assert data["rule"]["rule_id"].startswith("blk_")
    assert data["rule"]["rule_type"] == "domain"
    assert data["rule"]["pattern"] == "twitter.com"


def test_blocker_invalid_rule_type():
    import yinyang_server as ys
    ys._BLOCKER_RULES.clear()
    h = _make_handler({
        "rule_type": "invalid-type",
        "pattern": "example.com",
        "category": "social-media",
    })
    h._handle_blocker_rule_add()
    status, data = h._responses[0]
    assert status == 400
    assert "rule_type" in data["error"]


def test_blocker_delete_rule():
    import yinyang_server as ys
    ys._BLOCKER_RULES.clear()
    h = _make_handler({
        "rule_type": "keyword",
        "pattern": "gambling",
        "category": "gambling",
    })
    h._handle_blocker_rule_add()
    rule_id = h._responses[0][1]["rule"]["rule_id"]

    h2 = _make_handler()
    h2._handle_blocker_rule_delete(rule_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    assert len(ys._BLOCKER_RULES) == 0


def test_blocker_check_not_blocked():
    import yinyang_server as ys
    ys._BLOCKER_RULES.clear()
    ys._BLOCKER_LOG.clear()
    h = _make_handler({"url_hash": "a" * 64})
    h._handle_blocker_check()
    status, data = h._responses[0]
    assert status == 200
    assert data["blocked"] is False
    assert data["matched_rule_id"] is None


def test_blocker_check_blocked():
    import yinyang_server as ys
    ys._BLOCKER_RULES.clear()
    ys._BLOCKER_LOG.clear()
    # Add a rule with pattern that will match our url_hash
    h = _make_handler({
        "rule_type": "domain",
        "pattern": "deadbeef",
        "category": "social-media",
    })
    h._handle_blocker_rule_add()

    h2 = _make_handler({"url_hash": "deadbeef" + "0" * 56})
    h2._handle_blocker_check()
    status, data = h2._responses[0]
    assert status == 200
    assert data["blocked"] is True
    assert data["matched_rule_id"] is not None


def test_blocker_log_entry():
    """A blocked check creates a log entry."""
    import yinyang_server as ys
    ys._BLOCKER_RULES.clear()
    ys._BLOCKER_LOG.clear()
    h = _make_handler({
        "rule_type": "keyword",
        "pattern": "cafebabe",
        "category": "entertainment",
    })
    h._handle_blocker_rule_add()

    h2 = _make_handler({"url_hash": "cafebabe" + "1" * 56})
    h2._handle_blocker_check()

    with ys._BLOCKER_LOCK:
        assert len(ys._BLOCKER_LOG) >= 1
        entry = ys._BLOCKER_LOG[-1]
    assert entry["log_id"].startswith("blog_")
    assert "url_hash" in entry
    assert "matched_rule_id" in entry


def test_blocker_log_clear():
    import yinyang_server as ys
    ys._BLOCKER_RULES.clear()
    ys._BLOCKER_LOG.clear()
    # Add something to log
    h = _make_handler({
        "rule_type": "domain",
        "pattern": "aabbccdd",
        "category": "ads",
    })
    h._handle_blocker_rule_add()
    h2 = _make_handler({"url_hash": "aabbccdd" + "2" * 56})
    h2._handle_blocker_check()

    h3 = _make_handler()
    h3._handle_blocker_log_clear()
    status, data = h3._responses[0]
    assert status == 200
    assert data["status"] == "cleared"
    assert len(ys._BLOCKER_LOG) == 0


def test_blocker_html_no_cdn():
    """HTML must not reference external CDN URLs."""
    with open("/home/phuc/projects/solace-browser/web/site-blocker.html") as f:
        content = f.read()
    import re
    cdn_refs = re.findall(r'(?:src|href)\s*=\s*["\']https?://', content)
    assert cdn_refs == [], f"CDN references found: {cdn_refs}"


def test_no_port_9222_in_site_blocker():
    """No port 9222 references in site blocker files."""
    files = [
        "/home/phuc/projects/solace-browser/web/site-blocker.html",
        "/home/phuc/projects/solace-browser/web/js/site-blocker.js",
        "/home/phuc/projects/solace-browser/web/css/site-blocker.css",
    ]
    for path in files:
        with open(path) as f:
            content = f.read()
        assert "9222" not in content, f"Port 9222 found in {path}"
