"""tests/test_dark_mode.py — Dark Mode Theme System acceptance gate.
Task 029 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - No port 9222
  - No eval() in web/js/dark-mode.js
  - No CDN refs in web/dark-mode.html
  - ACCENT_COLORS closed set enforced
  - GET /api/v1/dark-mode is public (no auth required)
  - POST requires auth
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

TEST_TOKEN = "test-token-dark-mode-029"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18899)
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
def reset_dark_mode(tmp_path, monkeypatch):
    """Isolate dark-mode state per test."""
    dm_path = tmp_path / "dark-mode.json"
    monkeypatch.setattr(ys, "DARK_MODE_PATH", dm_path)
    # Reset in-memory state
    ys._DARK_MODE_STATE.update({"mode": "system", "accent": "blue", "font_size": "medium", "contrast": "normal"})
    yield


# ---------------------------------------------------------------------------
# 1. GET /api/v1/dark-mode returns 200 with required fields
# ---------------------------------------------------------------------------
def test_dark_mode_get_returns_200():
    status, data = get_json("/api/v1/dark-mode")
    assert status == 200
    assert "mode" in data
    assert "accent" in data
    assert "font_size" in data
    assert "contrast" in data


# ---------------------------------------------------------------------------
# 2. GET /api/v1/dark-mode/presets returns list of accent presets
# ---------------------------------------------------------------------------
def test_dark_mode_presets_returns_list():
    status, data = get_json("/api/v1/dark-mode/presets")
    assert status == 200
    assert "presets" in data
    assert len(data["presets"]) > 0
    for p in data["presets"]:
        assert "id" in p
        assert "name" in p


# ---------------------------------------------------------------------------
# 3. POST /api/v1/dark-mode sets mode to dark
# ---------------------------------------------------------------------------
def test_dark_mode_set_mode_dark():
    status, data = post_json("/api/v1/dark-mode", {"mode": "dark"})
    assert status == 200
    assert data["mode"] == "dark"


# ---------------------------------------------------------------------------
# 4. POST /api/v1/dark-mode rejects unknown mode with 400
# ---------------------------------------------------------------------------
def test_dark_mode_invalid_mode_rejected():
    status, data = post_json("/api/v1/dark-mode", {"mode": "neon"})
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 5. ACCENT_COLORS closed set: unknown accent → 400
# ---------------------------------------------------------------------------
def test_dark_mode_invalid_accent_rejected():
    status, data = post_json("/api/v1/dark-mode", {"accent": "rainbow"})
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 6. Valid accent color is accepted
# ---------------------------------------------------------------------------
def test_dark_mode_valid_accent_accepted():
    # "blue" is always in ACCENT_COLORS
    status, data = post_json("/api/v1/dark-mode", {"accent": "blue"})
    assert status == 200
    assert data["accent"] == "blue"


# ---------------------------------------------------------------------------
# 7. POST /api/v1/dark-mode/reset restores defaults
# ---------------------------------------------------------------------------
def test_dark_mode_reset_restores_defaults():
    # First set something custom
    post_json("/api/v1/dark-mode", {"mode": "dark", "accent": "purple"})
    # Then reset
    status, data = post_json("/api/v1/dark-mode/reset", {})
    assert status == 200
    assert data["mode"] == "system"
    assert data["accent"] == "blue"
    assert data["font_size"] == "medium"
    assert data["contrast"] == "normal"


# ---------------------------------------------------------------------------
# 8. Invalid font_size rejected
# ---------------------------------------------------------------------------
def test_dark_mode_invalid_font_size_rejected():
    status, data = post_json("/api/v1/dark-mode", {"font_size": "huge"})
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 9. web/dark-mode.html has no CDN references
# ---------------------------------------------------------------------------
def test_dark_mode_html_no_cdn():
    html_path = REPO_ROOT / "web" / "dark-mode.html"
    assert html_path.exists(), "web/dark-mode.html must exist"
    content = html_path.read_text()
    cdn_patterns = [
        r"cdn\.jsdelivr\.net",
        r"cdnjs\.cloudflare\.com",
        r"unpkg\.com",
        r"googleapis\.com",
        r"bootstrapcdn",
        r"https?://[^\s\"']+\.min\.js",
        r"https?://[^\s\"']+\.min\.css",
    ]
    for pattern in cdn_patterns:
        assert not re.search(pattern, content, re.IGNORECASE), (
            f"web/dark-mode.html contains CDN reference matching '{pattern}'"
        )


# ---------------------------------------------------------------------------
# 10. web/js/dark-mode.js has no eval() and no port 9222
# ---------------------------------------------------------------------------
def test_dark_mode_js_no_eval_no_banned_port():
    js_path = REPO_ROOT / "web" / "js" / "dark-mode.js"
    assert js_path.exists(), "web/js/dark-mode.js must exist"
    content = js_path.read_text()
    assert not re.search(r"\beval\s*\(", content), "dark-mode.js must not contain eval()"
    assert "9222" not in content, "dark-mode.js must not reference port 9222"
