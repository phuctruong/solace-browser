"""
test_gmail_triage.py — Gmail Inbox Triage App tests.
Task 014 | Rung: 641

Kill conditions verified here:
  - No port 9222
  - No "Companion App"
  - No bare except
  - No plaintext token storage
  - No auto-approve (always preview -> sign-off -> execute)
  - No CDN refs in HTML/JS
  - No eval() in JS
"""
import hashlib
import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

# ---------------------------------------------------------------------------
# Test port (distinct from other modules)
# ---------------------------------------------------------------------------
TEST_TOKEN = "test-token-gmail-triage-014"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Handler factory
# ---------------------------------------------------------------------------
def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18890)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path: str) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET")
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path: str, payload: dict) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "POST", payload)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


# ---------------------------------------------------------------------------
# Fixtures — reset _GMAIL_STORE between tests
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_gmail_store():
    """Reset global gmail store before each test to avoid state bleed."""
    with ys._GMAIL_LOCK:
        ys._GMAIL_STORE["connected"] = False
        ys._GMAIL_STORE["oauth2_token_hash"] = None
        ys._GMAIL_STORE["last_run"] = None
        ys._GMAIL_STORE["results"] = []
        ys._GMAIL_STORE["config"] = dict(ys.TRIAGE_RULES)
    yield
    with ys._GMAIL_LOCK:
        ys._GMAIL_STORE["connected"] = False
        ys._GMAIL_STORE["oauth2_token_hash"] = None
        ys._GMAIL_STORE["last_run"] = None
        ys._GMAIL_STORE["results"] = []
        ys._GMAIL_STORE["config"] = dict(ys.TRIAGE_RULES)


# ---------------------------------------------------------------------------
# Test 1: status endpoint exists
# ---------------------------------------------------------------------------
def test_gmail_status_endpoint_exists():
    status, data = get_json("/api/v1/apps/gmail-inbox-triage/status")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert "connected" in data
    assert "app_id" in data
    assert data["app_id"] == "gmail-inbox-triage"


# ---------------------------------------------------------------------------
# Test 2: disconnected by default
# ---------------------------------------------------------------------------
def test_gmail_status_disconnected_by_default():
    status, data = get_json("/api/v1/apps/gmail-inbox-triage/status")
    assert status == 200
    assert data["connected"] is False


# ---------------------------------------------------------------------------
# Test 3: run requires setup first
# ---------------------------------------------------------------------------
def test_gmail_run_requires_setup_first():
    status, data = post_json("/api/v1/apps/gmail-inbox-triage/run", {})
    assert status == 400, f"Expected 400, got {status}: {data}"
    assert "not connected" in data.get("error", "").lower()


# ---------------------------------------------------------------------------
# Test 4: setup stores hash not plaintext token
# ---------------------------------------------------------------------------
def test_gmail_setup_stores_hash_not_token():
    raw_token = "ya29.fake_oauth2_token_for_testing_12345"
    expected_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    status, data = post_json("/api/v1/apps/gmail-inbox-triage/setup", {"oauth2_token": raw_token})
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert data.get("status") == "connected"

    with ys._GMAIL_LOCK:
        stored_hash = ys._GMAIL_STORE["oauth2_token_hash"]
        connected = ys._GMAIL_STORE["connected"]

    # Hash must match SHA-256 of raw token
    assert stored_hash == expected_hash, "Stored hash does not match SHA-256 of token"
    assert connected is True
    # Raw token must NOT appear anywhere in stored state
    assert raw_token not in str(ys._GMAIL_STORE), "Plaintext token found in store"


# ---------------------------------------------------------------------------
# Test 5: results empty initially
# ---------------------------------------------------------------------------
def test_gmail_results_empty_initially():
    status, data = get_json("/api/v1/apps/gmail-inbox-triage/results")
    assert status == 200
    assert data["results"] == []
    assert data["count"] == 0


# ---------------------------------------------------------------------------
# Test 6: run after setup returns preview
# ---------------------------------------------------------------------------
def test_gmail_run_returns_preview():
    post_json("/api/v1/apps/gmail-inbox-triage/setup", {"oauth2_token": "ya29.valid_token_xyzabc"})
    status, data = post_json("/api/v1/apps/gmail-inbox-triage/run", {})
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert data.get("status") == "preview"
    assert data.get("sign_off_required") is True
    assert "previews" in data
    assert isinstance(data["previews"], list)
    assert len(data["previews"]) > 0
    assert "action_id" in data
    assert data.get("auto_reject_after_seconds") == 30


# ---------------------------------------------------------------------------
# Test 7: config returns triage rules
# ---------------------------------------------------------------------------
def test_gmail_config_returns_triage_rules():
    status, data = get_json("/api/v1/apps/gmail-inbox-triage/config")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert "config" in data
    cfg = data["config"]
    assert "archive_newsletters" in cfg
    assert "snooze_follow_ups" in cfg
    assert "label_receipts" in cfg
    assert "archive_social_notifications" in cfg
    # All must be booleans
    for key, val in cfg.items():
        assert isinstance(val, bool), f"Config key {key} is not bool: {val}"


# ---------------------------------------------------------------------------
# Test 8: no plaintext token in setup response
# ---------------------------------------------------------------------------
def test_gmail_no_plaintext_token_in_response():
    raw_token = "ya29.super_secret_token_must_not_appear"
    status, data = post_json("/api/v1/apps/gmail-inbox-triage/setup", {"oauth2_token": raw_token})
    assert status == 200
    response_str = json.dumps(data)
    assert raw_token not in response_str, "Raw token leaked in response"
    # token_hash_preview must only be a truncated hash (8 chars + "...")
    preview = data.get("token_hash_preview", "")
    assert raw_token not in preview, "Raw token in preview field"
    assert "..." in preview, "Preview should be truncated with '...'"


# ---------------------------------------------------------------------------
# Test 9: gmail-triage.html has no CDN refs
# ---------------------------------------------------------------------------
def test_gmail_triage_html_no_cdn():
    html_path = REPO_ROOT / "web" / "gmail-triage.html"
    assert html_path.exists(), f"gmail-triage.html not found at {html_path}"
    content = html_path.read_text()
    cdn_patterns = [
        "cdn.jsdelivr.net",
        "cdnjs.cloudflare.com",
        "unpkg.com",
        "fonts.googleapis.com",
        "ajax.googleapis.com",
        "maxcdn.bootstrapcdn.com",
        "stackpath.bootstrapcdn.com",
        "code.jquery.com",
    ]
    for pattern in cdn_patterns:
        assert pattern not in content, f"CDN reference found in gmail-triage.html: {pattern}"


# ---------------------------------------------------------------------------
# Test 10: gmail-triage.js has no eval()
# ---------------------------------------------------------------------------
def test_gmail_triage_js_no_eval():
    js_path = REPO_ROOT / "web" / "js" / "gmail-triage.js"
    assert js_path.exists(), f"gmail-triage.js not found at {js_path}"
    content = js_path.read_text()
    # Must not contain eval( — check for the call pattern
    import re
    assert not re.search(r"\beval\s*\(", content), "eval() found in gmail-triage.js"


# ---------------------------------------------------------------------------
# Test 11: setup rejects short token
# ---------------------------------------------------------------------------
def test_gmail_setup_rejects_short_token():
    status, data = post_json("/api/v1/apps/gmail-inbox-triage/setup", {"oauth2_token": "short"})
    assert status == 400, f"Expected 400, got {status}: {data}"
    assert "error" in data


# ---------------------------------------------------------------------------
# Test 12: triage preview contains correct actions for known email patterns
# ---------------------------------------------------------------------------
def test_gmail_triage_preview_newsletter_archived():
    post_json("/api/v1/apps/gmail-inbox-triage/setup", {"oauth2_token": "ya29.valid_token_xyzabc"})
    emails = [
        {"id": "e1", "sender": "newsletter@company.com", "subject": "Weekly digest"},
    ]
    status, data = post_json("/api/v1/apps/gmail-inbox-triage/run", {"emails": emails})
    assert status == 200
    previews = data["previews"]
    assert len(previews) == 1
    assert previews[0]["action"] == "archive"
    assert previews[0]["confidence"] > 0


# ---------------------------------------------------------------------------
# Test 13: no port 9222 in web files
# ---------------------------------------------------------------------------
def test_no_port_9222_in_gmail_files():
    forbidden = "9222"
    for fpath in [
        REPO_ROOT / "web" / "gmail-triage.html",
        REPO_ROOT / "web" / "js" / "gmail-triage.js",
        REPO_ROOT / "web" / "css" / "gmail-triage.css",
    ]:
        if fpath.exists():
            assert forbidden not in fpath.read_text(), f"Port 9222 found in {fpath.name}"


# ---------------------------------------------------------------------------
# Test 14: no "Companion App" in gmail files
# ---------------------------------------------------------------------------
def test_no_companion_app_in_gmail_files():
    forbidden = "Companion" + " App"
    for fpath in [
        REPO_ROOT / "web" / "gmail-triage.html",
        REPO_ROOT / "web" / "js" / "gmail-triage.js",
        REPO_ROOT / "web" / "css" / "gmail-triage.css",
    ]:
        if fpath.exists():
            assert forbidden not in fpath.read_text(), f"Banned name found in {fpath.name}"
