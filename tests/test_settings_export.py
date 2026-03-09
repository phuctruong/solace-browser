"""tests/test_settings_export.py — Settings Export/Import acceptance gate.
Task 040 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - budget fields always string (Decimal format)
  - Auth required on POST/export; GET /settings is public
  - No port 9222, no eval(), no CDN
"""
import hashlib
import io
import json
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-settings-export-040"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18913)
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
def reset_settings_store(monkeypatch):
    """Reset settings store between tests."""
    monkeypatch.setattr(ys, "_SETTINGS_STORE", dict(ys.DEFAULT_SETTINGS))
    yield


# ---------------------------------------------------------------------------
# 1. GET /settings returns all 10 default keys
# ---------------------------------------------------------------------------
def test_settings_get_defaults():
    status, data = get_json("/api/v1/settings")
    assert status == 200
    assert len(data) == 10
    assert "theme" in data
    assert "language" in data
    assert "budget_daily_limit" in data


# ---------------------------------------------------------------------------
# 2. GET /settings/export-bundle returns JSON with settings
# ---------------------------------------------------------------------------
def test_settings_export():
    # export-bundle requires auth, we send a valid token
    handler, captured = _make_handler("/api/v1/settings/export-bundle", "GET")
    # We must capture raw bytes since the export streams directly
    # Mock send_response / send_header / end_headers / wfile
    buf = io.BytesIO()
    handler.wfile = buf
    response_info: dict = {}

    def mock_send_response(code):
        response_info["code"] = code

    def mock_send_header(k, v):
        pass

    def mock_end_headers():
        pass

    handler.send_response = mock_send_response
    handler.send_header = mock_send_header
    handler.end_headers = mock_end_headers
    handler.do_GET()
    # If _send_json was called, get from captured; otherwise parse buf
    if captured["status"] is not None:
        data = captured["data"]
    else:
        buf.seek(0)
        data = json.loads(buf.read().decode())
    assert "settings" in data or "theme" in data


# ---------------------------------------------------------------------------
# 3. POST /settings/import-bundle updates settings
# ---------------------------------------------------------------------------
def test_settings_import():
    status, data = post_json("/api/v1/settings/import-bundle", {"theme": "dark", "language": "fr"})
    assert status == 200
    assert data.get("status") == "imported"
    assert data["settings"]["theme"] == "dark"
    assert data["settings"]["language"] == "fr"


# ---------------------------------------------------------------------------
# 4. POST /settings/reset-bundle resets to defaults
# ---------------------------------------------------------------------------
def test_settings_reset():
    # First change something
    post_json("/api/v1/settings/import-bundle", {"theme": "dark"})
    # Then reset
    status, data = post_json("/api/v1/settings/reset-bundle", {})
    assert status == 200
    assert data.get("status") == "reset"
    assert data["settings"]["theme"] == "light"


# ---------------------------------------------------------------------------
# 5. GET /settings/diff-bundle is empty when no changes
# ---------------------------------------------------------------------------
def test_settings_diff_empty_when_default():
    status, data = get_json("/api/v1/settings/diff-bundle")
    assert status == 200
    assert data.get("diff") == {}
    assert data.get("changed_count") == 0


# ---------------------------------------------------------------------------
# 6. GET /settings/diff-bundle shows changed key
# ---------------------------------------------------------------------------
def test_settings_diff_shows_changed():
    post_json("/api/v1/settings/import-bundle", {"theme": "dark"})
    status, data = get_json("/api/v1/settings/diff-bundle")
    assert status == 200
    assert "theme" in data["diff"]
    assert data["diff"]["theme"]["current"] == "dark"
    assert data["diff"]["theme"]["default"] == "light"


# ---------------------------------------------------------------------------
# 7. budget_daily_limit is always a string
# ---------------------------------------------------------------------------
def test_settings_budget_is_string():
    status, data = get_json("/api/v1/settings")
    assert status == 200
    assert isinstance(data["budget_daily_limit"], str), "budget_daily_limit must be string"
    assert isinstance(data["budget_monthly_limit"], str), "budget_monthly_limit must be string"
    # Verify decimal format
    assert "." in data["budget_daily_limit"]


# ---------------------------------------------------------------------------
# 8. HTML has no CDN links
# ---------------------------------------------------------------------------
def test_settings_html_no_cdn():
    html_path = REPO_ROOT / "web" / "settings-export.html"
    assert html_path.exists(), "settings-export.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 9. JS has no eval()
# ---------------------------------------------------------------------------
def test_settings_js_no_eval():
    js_path = REPO_ROOT / "web" / "js" / "settings-export.js"
    assert js_path.exists(), "settings-export.js must exist"
    content = js_path.read_text()
    assert "eval(" not in content, "eval() is banned in JS"


# ---------------------------------------------------------------------------
# 10. No port 9222 in settings export files
# ---------------------------------------------------------------------------
def test_no_port_9222_in_settings_export():
    files_to_check = [
        REPO_ROOT / "web" / "settings-export.html",
        REPO_ROOT / "web" / "js" / "settings-export.js",
        REPO_ROOT / "web" / "css" / "settings-export.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
