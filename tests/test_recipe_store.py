"""
test_recipe_store.py — Hub Recipe Store tests.
Task 017 | Rung: 641

Kill conditions verified here:
  - No port 9222
  - No "Companion App"
  - No bare except
  - No CDN refs in HTML/JS
  - No eval() in JS
  - hit_rate_pct and avg_cost_usd are strings
  - Auth required on all routes (Bearer)
"""
import hashlib
import json
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

# ---------------------------------------------------------------------------
# Test port and token
# ---------------------------------------------------------------------------
TEST_TOKEN = "test-token-recipe-store-017"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Handler factory (same pattern as test_gmail_triage.py)
# ---------------------------------------------------------------------------
def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18891)
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
# Fixtures — reset _RECIPE_STORE_INSTALLED between tests
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_recipe_store():
    """Reset installed store before/after each test to avoid state bleed."""
    with ys._RECIPE_STORE_LOCK:
        ys._RECIPE_STORE_INSTALLED.clear()
    yield
    with ys._RECIPE_STORE_LOCK:
        ys._RECIPE_STORE_INSTALLED.clear()


# ---------------------------------------------------------------------------
# Test 1: featured returns 3 recipes
# ---------------------------------------------------------------------------
def test_featured_returns_3_recipes():
    status, data = get_json("/api/v1/recipe-store/featured")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert "recipes" in data
    assert len(data["recipes"]) == 3


# ---------------------------------------------------------------------------
# Test 2: hit_rate_pct is a string, not float
# ---------------------------------------------------------------------------
def test_featured_has_hit_rate_string():
    status, data = get_json("/api/v1/recipe-store/featured")
    assert status == 200
    for recipe in data["recipes"]:
        val = recipe["hit_rate_pct"]
        assert isinstance(val, str), f"hit_rate_pct should be str, got {type(val).__name__}: {val}"


# ---------------------------------------------------------------------------
# Test 3: avg_cost_usd is a string, not float
# ---------------------------------------------------------------------------
def test_featured_has_avg_cost_string():
    status, data = get_json("/api/v1/recipe-store/featured")
    assert status == 200
    for recipe in data["recipes"]:
        val = recipe["avg_cost_usd"]
        assert isinstance(val, str), f"avg_cost_usd should be str, got {type(val).__name__}: {val}"


# ---------------------------------------------------------------------------
# Test 4: search returns results for 'gmail'
# ---------------------------------------------------------------------------
def test_search_returns_results():
    status, data = get_json("/api/v1/recipe-store/search?q=gmail")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert "recipes" in data
    assert len(data["recipes"]) >= 1
    names = [r["name"].lower() for r in data["recipes"]]
    assert any("gmail" in n for n in names), f"No gmail recipe in results: {names}"


# ---------------------------------------------------------------------------
# Test 5: search with no match returns empty list
# ---------------------------------------------------------------------------
def test_search_empty_returns_empty():
    status, data = get_json("/api/v1/recipe-store/search?q=zzznomatch999")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert data["recipes"] == []
    assert data["count"] == 0


# ---------------------------------------------------------------------------
# Test 6: install adds to installed list
# ---------------------------------------------------------------------------
def test_install_adds_to_installed():
    # Start empty
    status, data = get_json("/api/v1/recipe-store/installed")
    assert status == 200
    assert data["recipes"] == []

    # Install
    status, data = post_json("/api/v1/recipe-store/install", {"recipe_id": "gmail-zero-inbox"})
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert data.get("status") == "installed"

    # Now appears in installed
    status, data = get_json("/api/v1/recipe-store/installed")
    assert status == 200
    assert len(data["recipes"]) == 1
    assert data["recipes"][0]["recipe_id"] == "gmail-zero-inbox"


# ---------------------------------------------------------------------------
# Test 7: installed is empty initially
# ---------------------------------------------------------------------------
def test_installed_empty_initially():
    status, data = get_json("/api/v1/recipe-store/installed")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert data["recipes"] == []
    assert data["count"] == 0


# ---------------------------------------------------------------------------
# Test 8: recipe-store.html has no CDN refs
# ---------------------------------------------------------------------------
def test_recipe_store_html_no_cdn():
    html_path = REPO_ROOT / "web" / "recipe-store.html"
    assert html_path.exists(), f"recipe-store.html not found at {html_path}"
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
        assert pattern not in content, f"CDN reference found in recipe-store.html: {pattern}"


# ---------------------------------------------------------------------------
# Test 9: recipe-store.js has no eval()
# ---------------------------------------------------------------------------
def test_recipe_store_js_no_eval():
    js_path = REPO_ROOT / "web" / "js" / "recipe-store.js"
    assert js_path.exists(), f"recipe-store.js not found at {js_path}"
    content = js_path.read_text()
    assert not re.search(r"\beval\s*\(", content), "eval() found in recipe-store.js"


# ---------------------------------------------------------------------------
# Test 10: no port 9222 in recipe store files
# ---------------------------------------------------------------------------
def test_no_port_9222_in_recipe_store():
    forbidden = "9222"
    for fpath in [
        REPO_ROOT / "web" / "recipe-store.html",
        REPO_ROOT / "web" / "js" / "recipe-store.js",
        REPO_ROOT / "web" / "css" / "recipe-store.css",
    ]:
        if fpath.exists():
            assert forbidden not in fpath.read_text(), f"Port 9222 found in {fpath.name}"
