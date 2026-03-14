# Diagram: 05-solace-runtime-architecture
"""tests/test_browser_profiles.py — Task 025: Browser Profile Manager (10 tests)."""
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

TEST_PORT = 18925
VALID_TOKEN = "a" * 64


@pytest.fixture(scope="module")
def profiles_server():
    import yinyang_server as ys

    # Clear profiles file to avoid MAX_BROWSER_PROFILES limit from prior runs
    profiles_path = pathlib.Path.home() / ".solace" / "browser_profiles.json"
    if profiles_path.exists():
        profiles_path.write_text("[]")

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

def test_browser_profiles_html_exists():
    """Test 1: browser-profiles.html exists."""
    assert (REPO_ROOT / "web/browser-profiles.html").exists()


def test_browser_profiles_html_no_cdn():
    """Test 2: HTML has no CDN references."""
    content = (REPO_ROOT / "web/browser-profiles.html").read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in content
    assert "unpkg.com" not in content
    assert "bootstrapcdn" not in content


def test_browser_profiles_html_uses_hub_tokens():
    """Test 3: HTML references var(--hub-*) CSS tokens."""
    # Check CSS file instead (HTML links it externally)
    css_content = (REPO_ROOT / "web/css/browser-profiles.css").read_text(encoding="utf-8")
    assert "var(--hub-" in css_content


def test_browser_profiles_js_no_eval():
    """Test 4: JS has no eval()."""
    content = (REPO_ROOT / "web/js/browser-profiles.js").read_text(encoding="utf-8")
    assert "eval(" not in content


def test_browser_profiles_js_iife():
    """Test 5: JS uses IIFE pattern."""
    content = (REPO_ROOT / "web/js/browser-profiles.js").read_text(encoding="utf-8")
    assert "(function" in content or "})();" in content


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

def test_profiles_list_returns_200(profiles_server):
    """Test 6: GET /api/v1/browser/profiles returns 200."""
    resp = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/browser/profiles", timeout=3
    )
    assert resp.status == 200
    data = json.loads(resp.read())
    assert "profiles" in data
    assert isinstance(data["profiles"], list)


def test_profiles_create_requires_auth(profiles_server):
    """Test 7: POST /api/v1/browser/profiles without auth returns 401."""
    req = urllib.request.Request(
        f"http://localhost:{TEST_PORT}/api/v1/browser/profiles",
        data=json.dumps({"name": "Test"}).encode(),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req, timeout=3)
        assert False, "Expected 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401


def test_profiles_create_and_list(profiles_server):
    """Test 8: Create a profile and verify it appears in list."""
    import time as _time
    unique_name = f"TestProfile025_{int(_time.time() * 1000) % 100000}"
    req = auth_req("/api/v1/browser/profiles", "POST", {"name": unique_name, "avatar_color": "blue"})
    resp = urllib.request.urlopen(req, timeout=3)
    assert resp.status == 201
    data = json.loads(resp.read())
    assert "profile" in data
    profile = data["profile"]
    assert "profile_id" in profile
    assert profile["profile_id"].startswith("prof_")
    assert profile["name"] == unique_name
    assert profile["avatar_color"] == "blue"

    # Verify in list
    list_resp = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/browser/profiles", timeout=3
    )
    list_data = json.loads(list_resp.read())
    names = [p.get("name") for p in list_data.get("profiles", [])]
    assert unique_name in names


def test_profiles_invalid_avatar_color_rejected(profiles_server):
    """Test 9: Invalid avatar_color is rejected with 400."""
    req = auth_req("/api/v1/browser/profiles", "POST", {"name": "BadColor", "avatar_color": "rainbow"})
    try:
        urllib.request.urlopen(req, timeout=3)
        assert False, "Expected 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400


def test_profiles_active_returns_200(profiles_server):
    """Test 10: GET /api/v1/browser/profiles/active returns 200."""
    resp = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/browser/profiles/active", timeout=3
    )
    assert resp.status == 200
    data = json.loads(resp.read())
    assert "active_profile" in data
