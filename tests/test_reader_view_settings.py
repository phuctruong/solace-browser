# Diagram: 05-solace-runtime-architecture
"""Tests for Reader View Settings (Task 115). 10 tests."""
import sys
import pathlib
import hashlib
import json
from io import BytesIO

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-reader").hexdigest()


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method, path, body=None, auth=True):
        self.command = method
        self.path = path
        self._body = json.dumps(body).encode() if body else b""
        self._auth = auth
        self._status = None
        self._response = None
        self.headers = {
            "Content-Length": str(len(self._body)),
            "Authorization": f"Bearer {VALID_TOKEN}" if auth else "",
        }
        self.server = type("S", (), {
            "session_token_sha256": VALID_TOKEN,
            "repo_root": str(REPO_ROOT),
        })()
        self.rfile = BytesIO(self._body)
        self.wfile = BytesIO()

    def send_response(self, code):
        self._status = code

    def send_header(self, *a):
        pass

    def end_headers(self):
        pass

    def _send_json(self, data, code=200):
        self._status = code
        self._response = data

    def _check_auth(self):
        if not self._auth:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}


def _reset():
    ys._READER_SETTINGS.clear()


def _valid_body(**overrides):
    base = {
        "font": "serif",
        "theme": "light",
        "spacing": "normal",
        "font_size_px": 16,
        "line_width_chars": 80,
        "site_hash": "abc123",
    }
    base.update(overrides)
    return base


def test_setting_create():
    """POST → setting_id has rvs_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reader-view/settings", _valid_body())
    h._handle_reader_settings_create()
    assert h._status == 201
    assert h._response["setting"]["setting_id"].startswith("rvs_")


def test_setting_site_hashed():
    """site_hash stored as-is, no raw URL in response."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reader-view/settings", _valid_body(site_hash="deadbeef"))
    h._handle_reader_settings_create()
    assert h._status == 201
    setting = h._response["setting"]
    assert setting["site_hash"] == "deadbeef"
    # No key named "url" or "site_url" in the stored setting
    assert "site_url" not in setting
    assert "url" not in setting


def test_setting_invalid_font():
    """Unknown font → 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reader-view/settings", _valid_body(font="comic_sans"))
    h._handle_reader_settings_create()
    assert h._status == 400


def test_setting_invalid_theme():
    """Unknown theme → 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reader-view/settings", _valid_body(theme="rainbow"))
    h._handle_reader_settings_create()
    assert h._status == 400


def test_setting_font_size_range():
    """font_size_px=9 (below min 10) → 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reader-view/settings", _valid_body(font_size_px=9))
    h._handle_reader_settings_create()
    assert h._status == 400


def test_setting_font_size_range_high():
    """font_size_px=41 (above max 40) → 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reader-view/settings", _valid_body(font_size_px=41))
    h._handle_reader_settings_create()
    assert h._status == 400


def test_setting_list():
    """GET /settings → returns list of settings."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reader-view/settings", _valid_body())
    h._handle_reader_settings_create()

    h2 = FakeHandler("GET", "/api/v1/reader-view/settings")
    h2._handle_reader_settings_list()
    assert h2._status == 200
    assert isinstance(h2._response["settings"], list)
    assert h2._response["total"] >= 1


def test_setting_by_site():
    """GET /by-site?site_hash=xxx → filtered results."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reader-view/settings", _valid_body(site_hash="site_aaa"))
    h._handle_reader_settings_create()
    h2 = FakeHandler("POST", "/api/v1/reader-view/settings", _valid_body(site_hash="site_bbb"))
    h2._handle_reader_settings_create()

    h3 = FakeHandler("GET", "/api/v1/reader-view/settings/by-site?site_hash=site_aaa")
    h3._handle_reader_settings_by_site()
    assert h3._status == 200
    results = h3._response["settings"]
    assert all(s["site_hash"] == "site_aaa" for s in results)
    assert len(results) == 1


def test_setting_delete():
    """DELETE /settings/{id} → removed from list."""
    _reset()
    h = FakeHandler("POST", "/api/v1/reader-view/settings", _valid_body())
    h._handle_reader_settings_create()
    sid = h._response["setting"]["setting_id"]

    h2 = FakeHandler("DELETE", f"/api/v1/reader-view/settings/{sid}")
    h2._handle_reader_settings_delete(sid)
    assert h2._status == 200
    assert h2._response["status"] == "deleted"
    assert len(ys._READER_SETTINGS) == 0


def test_options_list():
    """GET /options → fonts, themes, spacing present."""
    h = FakeHandler("GET", "/api/v1/reader-view/options")
    h._handle_reader_options()
    assert h._status == 200
    resp = h._response
    assert "fonts" in resp
    assert "themes" in resp
    assert "spacing" in resp
    assert len(resp["fonts"]) == 5
    assert len(resp["themes"]) == 5
    assert len(resp["spacing"]) == 4


def test_no_port_9222_in_reader():
    """No port 9222 reference in reader-view handler code."""
    server_src = (REPO_ROOT / "yinyang_server.py").read_text()
    # Scan only the reader-view handler section for banned port
    start = server_src.find("Task 115")
    end = server_src.find("Task 116", start) if start != -1 else -1
    section = server_src[start:end] if start != -1 and end != -1 else ""
    assert "9222" not in section, "Port 9222 found in reader-view handler — BANNED"
