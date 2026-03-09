"""tests/test_bookmarks.py — Task 036: URL Bookmarks Manager (10 tests)."""
import hashlib
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-036"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path, method="GET", payload=None, token=TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18936)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path, token=TEST_TOKEN):
    handler, captured = _make_handler(path, "GET", token=token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path, payload, token=TEST_TOKEN):
    handler, captured = _make_handler(path, "POST", payload, token=token)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


def delete_json(path, token=TEST_TOKEN):
    handler, captured = _make_handler(path, "DELETE", token=token)
    handler.do_DELETE()
    return int(captured["status"]), dict(captured["data"])


# ---------------------------------------------------------------------------
# Fixture: clear state before each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_state():
    """Clear in-memory bookmark state before each test."""
    ys._BOOKMARKS.clear()
    yield
    ys._BOOKMARKS.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_bookmarks_empty_initially():
    """Test 1: GET /bookmarks → []."""
    status, data = get_json("/api/v1/bookmarks")
    assert status == 200
    assert data["bookmarks"] == []
    assert data["total"] == 0


def test_bookmark_add():
    """Test 2: POST → bookmark_id returned."""
    status, data = post_json("/api/v1/bookmarks", {
        "url": "https://gmail.com",
        "title": "Gmail",
        "tags": ["email", "google"],
    })
    assert status == 201
    assert "bookmark_id" in data["bookmark"]
    assert data["bookmark"]["bookmark_id"].startswith("bm_")
    assert data["status"] == "added"


def test_bookmark_delete():
    """Test 3: DELETE → removed."""
    _, create_data = post_json("/api/v1/bookmarks", {
        "url": "https://example.com",
        "title": "To Delete",
        "tags": [],
    })
    bm_id = create_data["bookmark"]["bookmark_id"]

    status, data = delete_json(f"/api/v1/bookmarks/{bm_id}")
    assert status == 200
    assert data["status"] == "deleted"

    status2, data2 = get_json("/api/v1/bookmarks")
    assert data2["total"] == 0


def test_bookmark_invalid_url():
    """Test 4: no http/https → 400."""
    status, data = post_json("/api/v1/bookmarks", {
        "url": "ftp://example.com",
        "title": "FTP",
        "tags": [],
    })
    assert status == 400
    assert "http" in data["error"].lower()


def test_bookmark_search():
    """Test 5: GET /search?q=gmail → returns matching bookmarks."""
    post_json("/api/v1/bookmarks", {
        "url": "https://gmail.com",
        "title": "Gmail Inbox",
        "tags": ["email"],
    })
    post_json("/api/v1/bookmarks", {
        "url": "https://github.com",
        "title": "GitHub",
        "tags": ["dev"],
    })

    # URL has "?" so need to use the full path
    handler = object.__new__(ys.YinyangHandler)
    captured = {"status": None, "data": None}
    t_hash = _token_hash(TEST_TOKEN)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = "/api/v1/bookmarks/search?q=gmail"
    handler.command = "GET"
    handler.client_address = ("127.0.0.1", 18936)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: None
    handler.do_GET()

    assert captured["status"] == 200
    results = captured["data"]["bookmarks"]
    assert len(results) >= 1
    assert any("gmail" in b["url"].lower() or "gmail" in b["title"].lower() for b in results)


def test_bookmark_tags_list():
    """Test 6: GET /tags → unique tags across all bookmarks."""
    post_json("/api/v1/bookmarks", {
        "url": "https://gmail.com",
        "title": "Gmail",
        "tags": ["email", "google"],
    })
    post_json("/api/v1/bookmarks", {
        "url": "https://github.com",
        "title": "GitHub",
        "tags": ["dev", "google"],
    })

    status, data = get_json("/api/v1/bookmarks/tags")
    assert status == 200
    tags = data["tags"]
    assert "email" in tags
    assert "dev" in tags
    assert "google" in tags
    # Unique — "google" appears only once
    assert len(set(tags)) == len(tags)


def test_bookmark_add_tags():
    """Test 7: POST /{id}/tags → tags updated."""
    _, create_data = post_json("/api/v1/bookmarks", {
        "url": "https://example.com",
        "title": "Example",
        "tags": ["initial"],
    })
    bm_id = create_data["bookmark"]["bookmark_id"]

    status, data = post_json(f"/api/v1/bookmarks/{bm_id}/tags", {
        "tags": ["added-tag"],
    })
    assert status == 200
    assert "added-tag" in data["tags"]
    assert "initial" in data["tags"]


def test_bookmark_max_tags():
    """Test 8: > 10 tags → 422."""
    status, data = post_json("/api/v1/bookmarks", {
        "url": "https://example.com",
        "title": "Too Many Tags",
        "tags": [f"tag{i}" for i in range(11)],
    })
    assert status == 422


def test_bookmarks_html_no_cdn():
    """Test 9: web/bookmarks.html no CDN."""
    html_path = REPO_ROOT / "web" / "bookmarks.html"
    assert html_path.exists(), "bookmarks.html must exist"
    content = html_path.read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in content
    assert "unpkg.com" not in content
    assert "cdnjs.cloudflare.com" not in content


def test_no_port_9222_in_bookmarks():
    """Test 10: no port 9222 in bookmarks files."""
    for fpath in [
        REPO_ROOT / "web" / "bookmarks.html",
        REPO_ROOT / "web" / "js" / "bookmarks.js",
        REPO_ROOT / "web" / "css" / "bookmarks.css",
    ]:
        if fpath.exists():
            assert "9222" not in fpath.read_text(), f"port 9222 found in {fpath}"
