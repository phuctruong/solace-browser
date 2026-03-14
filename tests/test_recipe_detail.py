# Diagram: 05-solace-runtime-architecture
"""tests/test_recipe_detail.py — Task 033: Recipe Detail Panel (10 tests)."""
import hashlib
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-033"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path, method="GET", payload=None, token=TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18933)
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_recipe_catalog_has_6():
    """Test 1: GET /catalog → 6 recipes."""
    status, data = get_json("/api/v1/recipes/catalog")
    assert status == 200
    assert len(data["recipes"]) == 6
    assert data["total"] == 6


def test_recipe_detail_returns_steps():
    """Test 2: GET /{id} → steps field (via catalog)."""
    status, data = get_json("/api/v1/recipes/catalog")
    assert status == 200
    recipe = data["recipes"][0]
    assert "steps" in recipe
    assert isinstance(recipe["steps"], int)
    assert recipe["steps"] > 0


def test_recipe_unknown_returns_404():
    """Test 3: GET /unknown-id → 404."""
    status, data = get_json("/api/v1/recipes/unknown-recipe-id-xyz/runs")
    assert status == 404


def test_recipe_preview_returns_steps():
    """Test 4: POST /preview → preview_steps list."""
    status, data = post_json("/api/v1/recipes/gmail-triage/preview", {})
    assert status == 200
    assert "preview_steps" in data
    assert isinstance(data["preview_steps"], list)
    assert len(data["preview_steps"]) == 4  # gmail-triage has 4 steps


def test_recipe_runs_empty_initially():
    """Test 5: GET /{id}/runs → []."""
    status, data = get_json("/api/v1/recipes/gmail-triage/runs")
    assert status == 200
    assert data["runs"] == []
    assert data["total"] == 0


def test_recipe_cost_estimate_is_string():
    """Test 6: cost_estimate is string not float."""
    status, data = get_json("/api/v1/recipes/catalog")
    assert status == 200
    for recipe in data["recipes"]:
        assert isinstance(recipe["cost_estimate"], str), (
            f"cost_estimate for {recipe['recipe_id']} should be string, got {type(recipe['cost_estimate'])}"
        )
        # Should be decimal formatted (not float repr)
        assert "." in recipe["cost_estimate"]


def test_recipe_catalog_html_no_cdn():
    """Test 7: web/recipe-detail.html no CDN."""
    html_path = REPO_ROOT / "web" / "recipe-detail.html"
    assert html_path.exists(), "recipe-detail.html must exist"
    content = html_path.read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in content
    assert "unpkg.com" not in content
    assert "cdnjs.cloudflare.com" not in content


def test_recipe_js_no_eval():
    """Test 8: web/js/recipe-detail.js no eval()."""
    js_path = REPO_ROOT / "web" / "js" / "recipe-detail.js"
    assert js_path.exists(), "recipe-detail.js must exist"
    content = js_path.read_text(encoding="utf-8")
    assert "eval(" not in content


def test_no_port_9222_in_recipe_detail():
    """Test 9: no port 9222 in recipe detail files."""
    for fpath in [
        REPO_ROOT / "web" / "recipe-detail.html",
        REPO_ROOT / "web" / "js" / "recipe-detail.js",
        REPO_ROOT / "web" / "css" / "recipe-detail.css",
    ]:
        if fpath.exists():
            assert "9222" not in fpath.read_text(), f"port 9222 found in {fpath}"


def test_recipe_preview_requires_auth():
    """Test 10: POST /preview without Bearer → 401."""
    handler = object.__new__(ys.YinyangHandler)
    captured = {"status": None, "data": None}
    t_hash = _token_hash(TEST_TOKEN)
    handler.headers = {"Authorization": "Bearer wrongtoken"}
    handler.path = "/api/v1/recipes/gmail-triage/preview"
    handler.command = "POST"
    handler.client_address = ("127.0.0.1", 18933)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: {}
    handler.do_POST()
    assert captured["status"] == 401
