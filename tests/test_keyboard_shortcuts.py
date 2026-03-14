# Diagram: 05-solace-runtime-architecture
"""tests/test_keyboard_shortcuts.py — Task 028: Keyboard Shortcuts Panel (10 tests)."""
import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18928
VALID_TOKEN = "d" * 64


@pytest.fixture(scope="module")
def shortcuts_server():
    import yinyang_server as ys

    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://localhost:{TEST_PORT}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield httpd
    httpd.shutdown()


def auth_req(path: str, method: str = "GET", body: dict | None = None, port: int = TEST_PORT):
    url = f"http://localhost:{port}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {VALID_TOKEN}")
    if data:
        req.add_header("Content-Type", "application/json")
    return req


# ---------------------------------------------------------------------------
# Static file checks
# ---------------------------------------------------------------------------

def test_keyboard_shortcuts_html_exists():
    """Test 1: keyboard-shortcuts.html exists."""
    assert (REPO_ROOT / "web/keyboard-shortcuts.html").exists()


def test_keyboard_shortcuts_html_no_cdn():
    """Test 2: HTML has no CDN references."""
    content = (REPO_ROOT / "web/keyboard-shortcuts.html").read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in content
    assert "unpkg.com" not in content


def test_keyboard_shortcuts_html_has_defaults_section():
    """Test 3: HTML references default shortcuts."""
    content = (REPO_ROOT / "web/keyboard-shortcuts.html").read_text(encoding="utf-8")
    assert "default" in content.lower() or "Default" in content


def test_keyboard_shortcuts_js_no_eval():
    """Test 4: JS has no eval()."""
    content = (REPO_ROOT / "web/js/keyboard-shortcuts.js").read_text(encoding="utf-8")
    assert "eval(" not in content


def test_keyboard_shortcuts_js_iife():
    """Test 5: JS uses IIFE pattern."""
    content = (REPO_ROOT / "web/js/keyboard-shortcuts.js").read_text(encoding="utf-8")
    assert "(function" in content or "})();" in content


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

def test_shortcuts_list_returns_200(shortcuts_server):
    """Test 6: GET /api/v1/keyboard-shortcuts returns 200 with defaults."""
    resp = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/keyboard-shortcuts", timeout=3
    )
    assert resp.status == 200
    data = json.loads(resp.read())
    assert "defaults" in data
    assert isinstance(data["defaults"], list)
    assert len(data["defaults"]) > 0  # DEFAULT_SHORTCUTS must be non-empty
    assert "custom" in data
    assert "total" in data


def test_shortcuts_list_has_question_mark_default(shortcuts_server):
    """Test 7: Default shortcuts include the '?' key."""
    resp = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/keyboard-shortcuts", timeout=3
    )
    data = json.loads(resp.read())
    keys = [s.get("key") for s in data.get("defaults", [])]
    assert "?" in keys


def test_shortcuts_add_requires_auth(shortcuts_server):
    """Test 8: POST /api/v1/keyboard-shortcuts without auth returns 401."""
    req = urllib.request.Request(
        f"http://localhost:{TEST_PORT}/api/v1/keyboard-shortcuts",
        data=json.dumps({"key": "x", "description": "Test"}).encode(),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req, timeout=3)
        assert False, "Expected 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401


def test_shortcuts_add_custom_and_list(shortcuts_server):
    """Test 9: Add custom shortcut and verify it appears."""
    import time as _time
    unique_key = f"Ctrl+Shift+{int(_time.time() * 1000) % 10000}"
    req = auth_req("/api/v1/keyboard-shortcuts", "POST", {"key": unique_key, "description": "Test shortcut 028"})
    resp = urllib.request.urlopen(req, timeout=3)
    assert resp.status == 201
    data = json.loads(resp.read())
    assert "shortcut" in data
    s = data["shortcut"]
    assert "shortcut_id" in s
    assert s["shortcut_id"].startswith("sc_")
    assert s["key"] == unique_key

    # Verify in list
    list_resp = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/keyboard-shortcuts", timeout=3
    )
    list_data = json.loads(list_resp.read())
    custom_keys = [c.get("key") for c in list_data.get("custom", [])]
    assert unique_key in custom_keys


def test_shortcuts_cannot_add_duplicate_default_key(shortcuts_server):
    """Test 10: Adding a shortcut with a default key returns 409."""
    req = auth_req("/api/v1/keyboard-shortcuts", "POST", {"key": "?", "description": "Duplicate default"})
    try:
        urllib.request.urlopen(req, timeout=3)
        assert False, "Expected 409"
    except urllib.error.HTTPError as e:
        assert e.code == 409
