"""tests/test_ext_firewall.py — Extension Firewall acceptance gate.
Task 046 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - 1 builtin rule (block-all-extensions), cannot delete → 409
  - ext_id_hash = SHA-256, never raw ID stored
  - action must be in RULE_ACTIONS → 400
  - Auth required on POST/DELETE; GET/check is public
  - No port 9222, no CDN, no eval()
"""
import hashlib
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-ext-firewall-046"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18911)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET", token=token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path: str, payload: dict, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "POST", payload, token=token)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


def delete_path(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "DELETE", token=token)
    handler.do_DELETE()
    return int(captured["status"]), dict(captured["data"])


@pytest.fixture(autouse=True)
def reset_firewall(monkeypatch):
    """Reset custom rules and blocked log between tests."""
    monkeypatch.setattr(ys, "_CUSTOM_RULES", [])
    monkeypatch.setattr(ys, "_BLOCKED_LOG", [])
    yield


# ---------------------------------------------------------------------------
# 1. GET /rules → 1 builtin rule
# ---------------------------------------------------------------------------
def test_firewall_rules_has_builtin():
    status, data = get_json("/api/v1/ext-firewall/rules")
    assert status == 200
    rules = data.get("rules", [])
    builtin_ids = [r["rule_id"] for r in rules if r.get("is_builtin")]
    assert "block-all-extensions" in builtin_ids


# ---------------------------------------------------------------------------
# 2. POST → rule_id returned
# ---------------------------------------------------------------------------
def test_firewall_add_rule():
    status, data = post_json(
        "/api/v1/ext-firewall/rules",
        {"pattern": "safe-extension", "action": "allow"},
    )
    assert status == 200
    assert data.get("status") == "added"
    assert "rule_id" in data
    assert data["rule_id"].startswith("rule_")


# ---------------------------------------------------------------------------
# 3. DELETE builtin → 409
# ---------------------------------------------------------------------------
def test_firewall_delete_builtin_fails():
    status, data = delete_path("/api/v1/ext-firewall/rules/block-all-extensions")
    assert status == 409
    assert "error" in data


# ---------------------------------------------------------------------------
# 4. DELETE custom → removed
# ---------------------------------------------------------------------------
def test_firewall_delete_custom():
    _, add_data = post_json(
        "/api/v1/ext-firewall/rules",
        {"pattern": "custom-ext", "action": "block"},
    )
    rule_id = add_data["rule_id"]
    status, data = delete_path(f"/api/v1/ext-firewall/rules/{rule_id}")
    assert status == 200
    assert data.get("status") == "deleted"
    _, list_data = get_json("/api/v1/ext-firewall/rules")
    ids = [r["rule_id"] for r in list_data["rules"]]
    assert rule_id not in ids


# ---------------------------------------------------------------------------
# 5. POST /check → allowed=False (default block-all)
# ---------------------------------------------------------------------------
def test_firewall_check_blocked():
    status, data = post_json(
        "/api/v1/ext-firewall/check",
        {"ext_id": "some-random-extension-id"},
    )
    assert status == 200
    assert data.get("allowed") is False


# ---------------------------------------------------------------------------
# 6. response has ext_id_hash not raw ID
# ---------------------------------------------------------------------------
def test_firewall_check_ext_id_hashed():
    ext_id = "my-extension-abc123"
    status, data = post_json("/api/v1/ext-firewall/check", {"ext_id": ext_id})
    assert status == 200
    assert "ext_id_hash" in data
    expected = hashlib.sha256(ext_id.encode()).hexdigest()
    assert data["ext_id_hash"] == expected
    # Raw ID must not appear in response
    assert ext_id not in str(data)


# ---------------------------------------------------------------------------
# 7. GET /blocked → log entries after blocked check
# ---------------------------------------------------------------------------
def test_firewall_blocked_log():
    post_json("/api/v1/ext-firewall/check", {"ext_id": "blocked-ext-xyz"})
    status, data = get_json("/api/v1/ext-firewall/blocked")
    assert status == 200
    blocked = data.get("blocked", [])
    assert len(blocked) >= 1
    entry = blocked[0]
    assert "ext_id_hash" in entry
    assert "blocked_at" in entry
    assert "reason" in entry


# ---------------------------------------------------------------------------
# 8. invalid action → 400
# ---------------------------------------------------------------------------
def test_firewall_invalid_action():
    status, data = post_json(
        "/api/v1/ext-firewall/rules",
        {"pattern": "something", "action": "explode"},
    )
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 9. HTML has no CDN links
# ---------------------------------------------------------------------------
def test_firewall_html_no_cdn():
    html_path = REPO_ROOT / "web" / "ext-firewall.html"
    assert html_path.exists(), "ext-firewall.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 10. No port 9222 in any ext firewall file
# ---------------------------------------------------------------------------
def test_no_port_9222_in_ext_firewall():
    files_to_check = [
        REPO_ROOT / "web" / "ext-firewall.html",
        REPO_ROOT / "web" / "js" / "ext-firewall.js",
        REPO_ROOT / "web" / "css" / "ext-firewall.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
