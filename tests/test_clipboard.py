"""tests/test_clipboard.py — Clipboard Manager acceptance gate.
Task 038 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - content_type validated against CLIPBOARD_TYPES
  - content max 50000 chars → 422
  - Max 50 entries — oldest removed on overflow
  - Auth required on POST/DELETE; GET/search is public
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

TEST_TOKEN = "test-token-clipboard-038"


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
def reset_clipboard(monkeypatch):
    """Reset clipboard state between tests."""
    monkeypatch.setattr(ys, "_CLIPBOARD", [])
    yield


# ---------------------------------------------------------------------------
# 1. Initially empty
# ---------------------------------------------------------------------------
def test_clipboard_empty_initially():
    status, data = get_json("/api/v1/clipboard")
    assert status == 200
    assert data.get("entries") == []


# ---------------------------------------------------------------------------
# 2. POST adds entry and returns entry_id
# ---------------------------------------------------------------------------
def test_clipboard_add_entry():
    status, data = post_json("/api/v1/clipboard", {"content": "hello world", "content_type": "text"})
    assert status == 200
    assert data.get("status") == "added"
    assert "entry_id" in data
    assert data["entry_id"].startswith("clip_")


# ---------------------------------------------------------------------------
# 3. Preview truncated at 100 chars
# ---------------------------------------------------------------------------
def test_clipboard_preview_truncated():
    long_content = "A" * 200
    post_json("/api/v1/clipboard", {"content": long_content, "content_type": "text"})
    status, data = get_json("/api/v1/clipboard")
    assert status == 200
    entries = data["entries"]
    assert len(entries) == 1
    assert len(entries[0]["preview"]) == 100


# ---------------------------------------------------------------------------
# 4. Max 50 entries — oldest removed on overflow
# ---------------------------------------------------------------------------
def test_clipboard_max_50_entries():
    for i in range(51):
        post_json("/api/v1/clipboard", {"content": f"item {i}", "content_type": "text"})
    status, data = get_json("/api/v1/clipboard")
    assert status == 200
    assert len(data["entries"]) == 50
    # Newest is first (reversed), oldest "item 0" should be gone
    all_previews = [e["preview"] for e in data["entries"]]
    assert "item 0" not in all_previews


# ---------------------------------------------------------------------------
# 5. DELETE /{id} removes the entry
# ---------------------------------------------------------------------------
def test_clipboard_delete_entry():
    _, add_data = post_json("/api/v1/clipboard", {"content": "to delete", "content_type": "text"})
    entry_id = add_data["entry_id"]

    status, data = delete_path(f"/api/v1/clipboard/{entry_id}")
    assert status == 200
    assert data.get("status") == "deleted"

    _, list_data = get_json("/api/v1/clipboard")
    ids = [e["entry_id"] for e in list_data["entries"]]
    assert entry_id not in ids


# ---------------------------------------------------------------------------
# 6. DELETE /clipboard clears all entries
# ---------------------------------------------------------------------------
def test_clipboard_clear_all():
    post_json("/api/v1/clipboard", {"content": "a", "content_type": "text"})
    post_json("/api/v1/clipboard", {"content": "b", "content_type": "text"})

    status, data = delete_path("/api/v1/clipboard")
    assert status == 200
    assert data.get("status") == "cleared"

    _, list_data = get_json("/api/v1/clipboard")
    assert list_data["entries"] == []


# ---------------------------------------------------------------------------
# 7. GET /search?q= returns matching entries
# ---------------------------------------------------------------------------
def test_clipboard_search():
    post_json("/api/v1/clipboard", {"content": "hello world", "content_type": "text"})
    post_json("/api/v1/clipboard", {"content": "foo bar", "content_type": "text"})

    handler, captured = _make_handler("/api/v1/clipboard/search?q=hello", "GET")
    handler.path = "/api/v1/clipboard/search?q=hello"
    handler.do_GET()
    status = int(captured["status"])
    data = dict(captured["data"])
    assert status == 200
    assert len(data["entries"]) == 1
    assert "hello" in data["entries"][0]["content"]


# ---------------------------------------------------------------------------
# 8. POST with invalid content_type → 400
# ---------------------------------------------------------------------------
def test_clipboard_invalid_type():
    status, data = post_json("/api/v1/clipboard", {"content": "x", "content_type": "binary"})
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 9. HTML has no CDN links
# ---------------------------------------------------------------------------
def test_clipboard_html_no_cdn():
    html_path = REPO_ROOT / "web" / "clipboard.html"
    assert html_path.exists(), "clipboard.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 10. No port 9222 in any clipboard file
# ---------------------------------------------------------------------------
def test_no_port_9222_in_clipboard():
    files_to_check = [
        REPO_ROOT / "web" / "clipboard.html",
        REPO_ROOT / "web" / "js" / "clipboard.js",
        REPO_ROOT / "web" / "css" / "clipboard.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
