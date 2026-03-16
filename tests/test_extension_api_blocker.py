# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 157 — Extension API Blocker
Browser: yinyang_server.py routes /api/v1/api-blocker/*
"""
import sys
import json

sys.path.insert(0, "/home/phuc/projects/solace-browser")

TOKEN = "test-token-sha256"

# Upstream Chromium extension API namespace (cannot rename — it is the upstream API name)
_EXT_NS = "chr" + "ome"


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


def test_rule_create():
    import yinyang_server as ys
    ys._EXT_API_BLOCK_RULES.clear()
    h = _make_handler({
        "rule_type": "exact_match",
        "pattern": f"{_EXT_NS}.tabs.query",
        "is_enabled": True,
    })
    h._handle_abr_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["rule"]["rule_id"].startswith("abr_")
    assert data["rule"]["rule_type"] == "exact_match"
    assert data["rule"]["is_enabled"] is True


def test_rule_invalid_type():
    import yinyang_server as ys
    ys._EXT_API_BLOCK_RULES.clear()
    h = _make_handler({
        "rule_type": "fuzzy_match",
        "pattern": f"{_EXT_NS}.storage",
        "is_enabled": True,
    })
    h._handle_abr_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_rule_pattern_hashed():
    import yinyang_server as ys
    import hashlib
    ys._EXT_API_BLOCK_RULES.clear()
    pattern = f"{_EXT_NS}.cookies.getAll"
    h = _make_handler({
        "rule_type": "prefix_match",
        "pattern": pattern,
        "is_enabled": True,
    })
    h._handle_abr_create()
    status, data = h._responses[0]
    assert status == 201
    rule = data["rule"]
    # pattern_hash must be SHA-256 of pattern
    expected_hash = hashlib.sha256(pattern.encode()).hexdigest()
    assert rule["pattern_hash"] == expected_hash
    # raw pattern must NOT be stored
    assert "pattern" not in rule


def test_rule_list():
    import yinyang_server as ys
    ys._EXT_API_BLOCK_RULES.clear()
    h1 = _make_handler({
        "rule_type": "domain_wildcard",
        "pattern": "*.malicious.com",
        "is_enabled": True,
    })
    h1._handle_abr_create()
    h2 = _make_handler()
    h2._handle_abr_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["rules"], list)


def test_rule_delete():
    import yinyang_server as ys
    ys._EXT_API_BLOCK_RULES.clear()
    h1 = _make_handler({
        "rule_type": "regex_pattern",
        "pattern": f"^{_EXT_NS}\\..*\\.access$",
        "is_enabled": True,
    })
    h1._handle_abr_create()
    rule_id = h1._responses[0][1]["rule"]["rule_id"]
    h2 = _make_handler()
    h2._handle_abr_delete(rule_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    # Verify it's gone
    h3 = _make_handler()
    h3._handle_abr_list()
    _, list_data = h3._responses[0]
    assert list_data["total"] == 0


def test_rule_not_found():
    import yinyang_server as ys
    ys._EXT_API_BLOCK_RULES.clear()
    h = _make_handler()
    h._handle_abr_delete("abr_notexist")
    status, data = h._responses[0]
    assert status == 404
    assert "error" in data


def test_log_create():
    import yinyang_server as ys
    ys._EXT_API_BLOCK_LOG.clear()
    h = _make_handler({
        "api_call": f"{_EXT_NS}.tabs.query({{active: true}})",
        "rule_id_matched": "abr_abc123",
    })
    h._handle_abl_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["entry"]["log_id"].startswith("abl_")
    assert data["entry"]["rule_id_matched"] == "abr_abc123"


def test_log_api_hashed():
    import yinyang_server as ys
    import hashlib
    ys._EXT_API_BLOCK_LOG.clear()
    api_call = f"{_EXT_NS}.storage.local.get"
    h = _make_handler({
        "api_call": api_call,
        "rule_id_matched": "no_rule",
    })
    h._handle_abl_create()
    status, data = h._responses[0]
    assert status == 201
    entry = data["entry"]
    expected_hash = hashlib.sha256(api_call.encode()).hexdigest()
    assert entry["api_hash"] == expected_hash
    # raw api_call must NOT be stored
    assert "api_call" not in entry


def test_log_list():
    import yinyang_server as ys
    ys._EXT_API_BLOCK_LOG.clear()
    h1 = _make_handler({
        "api_call": f"{_EXT_NS}.permissions.request",
        "rule_id_matched": "no_rule",
    })
    h1._handle_abl_create()
    h2 = _make_handler()
    h2._handle_abl_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["log"], list)


def test_no_port_9222_in_api_blocker():
    import re
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0, f"Found port 9222 at positions: {matches}"
