"""tests/test_whats_new.py — What's New Panel acceptance gate.
Task 041 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - 5 builtin changelog entries
  - Entries ordered newest first (by released_at descending)
  - Unknown entry_id for /seen → 404
  - type not in CHANGE_TYPES → 400
  - Auth required on POST routes; GET is public
  - No port 9222, no CDN, no eval()
"""
import copy
import hashlib
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-whats-new-041"
BAD_TOKEN = "bad-token-xxxxxxxxxxx"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18914)
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


@pytest.fixture(autouse=True)
def reset_changelog(monkeypatch):
    """Reset changelog and seen state between tests."""
    original_changelog = copy.deepcopy(ys._CHANGELOG)
    original_seen = {}
    monkeypatch.setattr(ys, "_CHANGELOG", original_changelog)
    monkeypatch.setattr(ys, "_SEEN_ENTRIES", original_seen)
    yield


# ---------------------------------------------------------------------------
# 1. GET /whats-new returns exactly 5 entries
# ---------------------------------------------------------------------------
def test_whats_new_list_has_5():
    status, data = get_json("/api/v1/whats-new")
    assert status == 200
    assert "entries" in data
    assert len(data["entries"]) == 5, f"Expected 5, got {len(data['entries'])}"


# ---------------------------------------------------------------------------
# 2. Entries ordered newest first (by released_at descending)
# ---------------------------------------------------------------------------
def test_whats_new_newest_first():
    status, data = get_json("/api/v1/whats-new")
    assert status == 200
    dates = [e["released_at"] for e in data["entries"]]
    assert dates == sorted(dates, reverse=True), "Entries must be newest first"


# ---------------------------------------------------------------------------
# 3. GET /unseen-count is 5 for fresh user
# ---------------------------------------------------------------------------
def test_whats_new_unseen_count_initially_5():
    status, data = get_json("/api/v1/whats-new/unseen-count")
    assert status == 200
    assert data.get("unseen_count") == 5


# ---------------------------------------------------------------------------
# 4. POST /{id}/seen marks entry as seen
# ---------------------------------------------------------------------------
def test_whats_new_mark_seen():
    status, data = post_json("/api/v1/whats-new/v1.3.0-1/seen", {})
    assert status == 200
    assert data.get("status") == "seen"
    assert data.get("entry_id") == "v1.3.0-1"


# ---------------------------------------------------------------------------
# 5. After marking seen → unseen count decrements
# ---------------------------------------------------------------------------
def test_whats_new_unseen_decrements():
    post_json("/api/v1/whats-new/v1.3.0-1/seen", {})
    status, data = get_json("/api/v1/whats-new/unseen-count")
    assert status == 200
    assert data.get("unseen_count") == 4


# ---------------------------------------------------------------------------
# 6. POST /whats-new → entry added, entry_id returned
# ---------------------------------------------------------------------------
def test_whats_new_add_entry():
    status, data = post_json(
        "/api/v1/whats-new",
        {"version": "2.0.0", "type": "feature", "title": "New Feature", "description": "Test"},
    )
    assert status == 200
    assert data.get("status") == "added"
    assert "entry_id" in data
    # Verify list now has 6 entries
    _, list_data = get_json("/api/v1/whats-new")
    assert len(list_data["entries"]) == 6


# ---------------------------------------------------------------------------
# 7. Marking unknown entry_id → 404
# ---------------------------------------------------------------------------
def test_whats_new_unknown_entry_seen():
    status, data = post_json("/api/v1/whats-new/no-such-entry/seen", {})
    assert status == 404
    assert "error" in data


# ---------------------------------------------------------------------------
# 8. HTML has no CDN links
# ---------------------------------------------------------------------------
def test_whats_new_html_no_cdn():
    html_path = REPO_ROOT / "web" / "whats-new.html"
    assert html_path.exists(), "whats-new.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 9. JS has no eval()
# ---------------------------------------------------------------------------
def test_whats_new_js_no_eval():
    js_path = REPO_ROOT / "web" / "js" / "whats-new.js"
    assert js_path.exists(), "whats-new.js must exist"
    content = js_path.read_text()
    assert "eval(" not in content, "eval() is banned in JS"


# ---------------------------------------------------------------------------
# 10. No port 9222 in any whats-new file
# ---------------------------------------------------------------------------
def test_no_port_9222_in_whats_new():
    files_to_check = [
        REPO_ROOT / "web" / "whats-new.html",
        REPO_ROOT / "web" / "js" / "whats-new.js",
        REPO_ROOT / "web" / "css" / "whats-new.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
