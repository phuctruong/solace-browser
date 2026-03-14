# Diagram: 05-solace-runtime-architecture
"""tests/test_tab_manager.py — Task 035: Multi-Tab Manager (10 tests)."""
import hashlib
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-035"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path, method="GET", payload=None, token=TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18935)
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
    """Clear in-memory tab state before each test."""
    ys._TABS.clear()
    yield
    ys._TABS.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_tabs_list_empty_initially():
    """Test 1: GET /tabs → []."""
    status, data = get_json("/api/v1/tabs")
    assert status == 200
    assert data["tabs"] == []
    assert data["total"] == 0


def test_tabs_register():
    """Test 2: POST → tab_id returned."""
    status, data = post_json("/api/v1/tabs", {
        "url": "https://example.com",
        "title": "Example",
        "status": "ready",
    })
    assert status == 201
    assert "tab_id" in data["tab"]
    assert data["tab"]["tab_id"].startswith("tab_")
    assert data["status"] == "registered"


def test_tabs_detail():
    """Test 3: GET /{id} → full tab record."""
    _, create_data = post_json("/api/v1/tabs", {
        "url": "https://example.com/detail",
        "title": "Detail Page",
        "status": "idle",
        "session_id": "sess_001",
    })
    tab_id = create_data["tab"]["tab_id"]

    status, data = get_json(f"/api/v1/tabs/{tab_id}")
    assert status == 200
    tab = data["tab"]
    assert tab["tab_id"] == tab_id
    assert tab["url"] == "https://example.com/detail"
    assert tab["title"] == "Detail Page"
    assert tab["status"] == "idle"
    assert tab["session_id"] == "sess_001"


def test_tabs_delete():
    """Test 4: DELETE → removed."""
    _, create_data = post_json("/api/v1/tabs", {
        "url": "https://example.com",
        "title": "To Delete",
        "status": "ready",
    })
    tab_id = create_data["tab"]["tab_id"]

    status, data = delete_json(f"/api/v1/tabs/{tab_id}")
    assert status == 200
    assert data["status"] == "deleted"

    # Verify removed
    status2, data2 = get_json("/api/v1/tabs")
    assert data2["total"] == 0


def test_tabs_unknown_returns_404():
    """Test 5: GET /unknown-id → 404."""
    status, data = get_json("/api/v1/tabs/tab_nonexistent-xyz")
    assert status == 404


def test_tabs_invalid_status():
    """Test 6: POST with status='invisible' → 400."""
    status, data = post_json("/api/v1/tabs", {
        "url": "https://example.com",
        "title": "Bad Status",
        "status": "invisible",
    })
    assert status == 400
    assert "status" in data["error"].lower()


def test_tabs_focus_updates_timestamp():
    """Test 7: POST /focus → last_focused_at set."""
    _, create_data = post_json("/api/v1/tabs", {
        "url": "https://example.com",
        "title": "Focus Me",
        "status": "ready",
    })
    tab_id = create_data["tab"]["tab_id"]
    assert create_data["tab"]["last_focused_at"] is None

    status, data = post_json(f"/api/v1/tabs/{tab_id}/focus", {})
    assert status == 200
    assert data["last_focused_at"] is not None
    assert data["status"] == "focused"


def test_tabs_url_max_length():
    """Test 8: url > 2000 chars → 422."""
    long_url = "https://example.com/" + "a" * 2000
    status, data = post_json("/api/v1/tabs", {
        "url": long_url,
        "title": "Too Long",
        "status": "ready",
    })
    assert status == 422


def test_tabs_html_no_cdn():
    """Test 9: web/tab-manager.html no CDN."""
    html_path = REPO_ROOT / "web" / "tab-manager.html"
    assert html_path.exists(), "tab-manager.html must exist"
    content = html_path.read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in content
    assert "unpkg.com" not in content
    assert "cdnjs.cloudflare.com" not in content


def test_no_port_9222_in_tab_manager():
    """Test 10: no port 9222 in tab manager files."""
    for fpath in [
        REPO_ROOT / "web" / "tab-manager.html",
        REPO_ROOT / "web" / "js" / "tab-manager.js",
        REPO_ROOT / "web" / "css" / "tab-manager.css",
    ]:
        if fpath.exists():
            assert "9222" not in fpath.read_text(), f"port 9222 found in {fpath}"
