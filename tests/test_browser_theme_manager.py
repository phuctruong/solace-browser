# Diagram: 05-solace-runtime-architecture
"""Tests for Browser Theme Manager (Task 132). 10 tests."""
import sys
import pathlib
import hashlib
import json

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token-132").hexdigest()


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
    ys._THEMES.clear()


def _make_theme(**kwargs):
    base = {
        "name": "My Dark Theme",
        "theme_type": "dark",
        "accent_color": "blue",
    }
    base.update(kwargs)
    return base


def _create_theme(**kwargs):
    h = FakeHandler("POST", "/api/v1/theme-manager/themes", _make_theme(**kwargs))
    h._handle_theme_create()
    return h._response["theme"]


def test_theme_create():
    """POST creates theme with thm_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/theme-manager/themes", _make_theme())
    h._handle_theme_create()
    assert h._status == 201
    t = h._response["theme"]
    assert t["theme_id"].startswith("thm_")


def test_theme_name_hashed():
    """POST stores name_hash."""
    _reset()
    h = FakeHandler("POST", "/api/v1/theme-manager/themes", _make_theme())
    h._handle_theme_create()
    t = h._response["theme"]
    assert "name_hash" in t
    assert len(t["name_hash"]) == 64


def test_theme_invalid_type():
    """POST with invalid theme_type returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/theme-manager/themes", _make_theme(theme_type="rainbow"))
    h._handle_theme_create()
    assert h._status == 400


def test_theme_invalid_accent():
    """POST with invalid accent_color returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/theme-manager/themes", _make_theme(accent_color="cyan"))
    h._handle_theme_create()
    assert h._status == 400


def test_theme_list():
    """GET returns list of themes."""
    _reset()
    _create_theme()
    h = FakeHandler("GET", "/api/v1/theme-manager/themes")
    h._handle_themes_list()
    assert h._status == 200
    assert isinstance(h._response["themes"], list)
    assert h._response["total"] >= 1


def test_theme_delete():
    """DELETE removes theme."""
    _reset()
    t = _create_theme()
    tid = t["theme_id"]
    h_del = FakeHandler("DELETE", f"/api/v1/theme-manager/themes/{tid}")
    h_del._handle_theme_delete(tid)
    assert h_del._status == 200
    assert not any(t["theme_id"] == tid for t in ys._THEMES)


def test_theme_activate():
    """POST /activate sets is_active=True."""
    _reset()
    t = _create_theme()
    tid = t["theme_id"]
    h = FakeHandler("POST", f"/api/v1/theme-manager/themes/{tid}/activate", {})
    h._handle_theme_activate(tid)
    assert h._status == 200
    active = next(t for t in ys._THEMES if t["theme_id"] == tid)
    assert active["is_active"] is True


def test_theme_only_one_active():
    """Activating theme B deactivates theme A."""
    _reset()
    ta = _create_theme(name="Theme A")
    tb = _create_theme(name="Theme B")
    # Activate A first
    h_a = FakeHandler("POST", f"/api/v1/theme-manager/themes/{ta['theme_id']}/activate", {})
    h_a._handle_theme_activate(ta["theme_id"])
    # Activate B
    h_b = FakeHandler("POST", f"/api/v1/theme-manager/themes/{tb['theme_id']}/activate", {})
    h_b._handle_theme_activate(tb["theme_id"])
    # A must now be inactive
    theme_a = next(t for t in ys._THEMES if t["theme_id"] == ta["theme_id"])
    assert theme_a["is_active"] is False
    theme_b = next(t for t in ys._THEMES if t["theme_id"] == tb["theme_id"])
    assert theme_b["is_active"] is True


def test_active_theme():
    """GET /active returns the active theme."""
    _reset()
    t = _create_theme()
    tid = t["theme_id"]
    h_act = FakeHandler("POST", f"/api/v1/theme-manager/themes/{tid}/activate", {})
    h_act._handle_theme_activate(tid)
    h = FakeHandler("GET", "/api/v1/theme-manager/active")
    h._handle_active_theme()
    assert h._status == 200
    assert h._response["theme"]["theme_id"] == tid


def test_no_port_9222_in_theme():
    """yinyang_server.py must not reference port 9222."""
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert "9222" not in content
