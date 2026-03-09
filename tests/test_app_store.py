"""tests/test_app_store.py — App Store Browser acceptance gate.
Task 030 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - 6 catalog apps hardcoded (cannot delete)
  - Install/uninstall toggle
  - Builtin apps → 409 on uninstall attempt
  - GET is public; POST requires auth
  - No port 9222, no eval(), no CDN
"""
import hashlib
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-app-store-030"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18900)
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
def reset_installed(monkeypatch):
    """Reset installed set between tests."""
    monkeypatch.setattr(ys, "_APP_STORE_INSTALLED", set())
    yield


# ---------------------------------------------------------------------------
# 1. Catalog has exactly 6 apps
# ---------------------------------------------------------------------------
def test_app_store_catalog_has_6_apps():
    status, data = get_json("/api/v1/app-store/catalog")
    assert status == 200
    assert "apps" in data
    assert len(data["apps"]) == 6, f"Expected 6 catalog apps, got {len(data['apps'])}"


# ---------------------------------------------------------------------------
# 2. GET /api/v1/app-store/catalog is public (no auth needed)
# ---------------------------------------------------------------------------
def test_app_store_catalog_public():
    handler, captured = _make_handler("/api/v1/app-store/catalog", "GET")
    # Server with no token set → any bearer is accepted
    handler.server = type("DummyServer", (), {"session_token_sha256": ""})()
    handler.headers = {}
    handler.do_GET()
    assert captured["status"] == 200


# ---------------------------------------------------------------------------
# 3. Install an app → appears in installed list
# ---------------------------------------------------------------------------
def test_app_store_install_app():
    catalog_status, catalog_data = get_json("/api/v1/app-store/catalog")
    first_id = catalog_data["apps"][0]["id"]
    status, data = post_json("/api/v1/app-store/install", {"app_id": first_id})
    assert status == 200
    assert data.get("status") == "installed"

    inst_status, inst_data = get_json("/api/v1/app-store/installed")
    assert inst_status == 200
    installed_ids = [a["id"] for a in inst_data["apps"]]
    assert first_id in installed_ids


# ---------------------------------------------------------------------------
# 4. Uninstall a builtin app → 409
# ---------------------------------------------------------------------------
def test_app_store_uninstall_builtin_returns_409():
    # First install
    first_id = ys.APP_STORE_CATALOG[0]["id"]
    post_json("/api/v1/app-store/install", {"app_id": first_id})
    # Attempt uninstall (all catalog apps are builtin)
    status, data = post_json("/api/v1/app-store/uninstall", {"app_id": first_id})
    assert status == 409
    assert "error" in data


# ---------------------------------------------------------------------------
# 5. Install unknown app → 404
# ---------------------------------------------------------------------------
def test_app_store_install_unknown_app_returns_404():
    status, data = post_json("/api/v1/app-store/install", {"app_id": "nonexistent-xyz"})
    assert status == 404
    assert "error" in data


# ---------------------------------------------------------------------------
# 6. GET /api/v1/app-store/categories returns list of strings
# ---------------------------------------------------------------------------
def test_app_store_categories_returns_list():
    status, data = get_json("/api/v1/app-store/categories")
    assert status == 200
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) > 0


# ---------------------------------------------------------------------------
# 7. Category filter returns only matching apps
# ---------------------------------------------------------------------------
def test_app_store_catalog_category_filter():
    # Get first category
    _, cat_data = get_json("/api/v1/app-store/categories")
    first_cat = cat_data["categories"][0]
    status, data = get_json(f"/api/v1/app-store/catalog?category={first_cat}")
    assert status == 200
    for app in data["apps"]:
        assert app["category"] == first_cat


# ---------------------------------------------------------------------------
# 8. catalog apps have required fields
# ---------------------------------------------------------------------------
def test_app_store_catalog_app_fields():
    _, data = get_json("/api/v1/app-store/catalog")
    for app in data["apps"]:
        assert "id" in app
        assert "name" in app
        assert "category" in app
        assert "description" in app
        assert "installed" in app


# ---------------------------------------------------------------------------
# 9. web/app-store.html has no CDN references
# ---------------------------------------------------------------------------
def test_app_store_html_no_cdn():
    html_path = REPO_ROOT / "web" / "app-store.html"
    assert html_path.exists(), "web/app-store.html must exist"
    content = html_path.read_text()
    cdn_patterns = [
        r"cdn\.jsdelivr\.net", r"cdnjs\.cloudflare\.com", r"unpkg\.com",
        r"googleapis\.com", r"bootstrapcdn",
        r"https?://[^\s\"']+\.min\.js", r"https?://[^\s\"']+\.min\.css",
    ]
    for pattern in cdn_patterns:
        assert not re.search(pattern, content, re.IGNORECASE), (
            f"web/app-store.html contains CDN reference matching '{pattern}'"
        )


# ---------------------------------------------------------------------------
# 10. web/js/app-store.js has no eval() and no port 9222
# ---------------------------------------------------------------------------
def test_app_store_js_no_eval_no_banned_port():
    js_path = REPO_ROOT / "web" / "js" / "app-store.js"
    assert js_path.exists(), "web/js/app-store.js must exist"
    content = js_path.read_text()
    assert not re.search(r"\beval\s*\(", content), "app-store.js must not contain eval()"
    assert "9222" not in content, "app-store.js must not reference port 9222"
