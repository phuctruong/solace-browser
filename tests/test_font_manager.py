"""Tests for Task 091 — Font Manager."""
import sys
import pathlib
REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import json
import hashlib
import threading
import yinyang_server as ys
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token").hexdigest()


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method="GET", path="/", body=None, auth=True):
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

    def log_message(self, *a):
        pass


def setup_function():
    with ys._FONT_LOCK:
        ys._CUSTOM_FONTS.clear()
        ys._ACTIVE_FONT.clear()
        ys._ACTIVE_FONT.update({"family": "system-ui", "size": 16, "weight": "400"})


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_font_list_public():
    """GET /api/v1/font-manager/fonts is public (no auth required)."""
    h = FakeHandler("GET", "/api/v1/font-manager/fonts", auth=False)
    h._handle_font_list()
    assert h._status == 200
    assert "builtin" in h._response
    assert "Arial" in h._response["builtin"]
    assert "system-ui" in h._response["builtin"]
    assert "custom" in h._response


def test_font_add_valid():
    """POST /api/v1/font-manager/fonts adds a custom font and returns font_id."""
    body = {
        "family": "Roboto",
        "weight": "400",
        "size": 16,
        "source_hash": _sha256("https://fonts.example.com/roboto.ttf"),
    }
    h = FakeHandler("POST", "/api/v1/font-manager/fonts", body=body, auth=True)
    h._handle_font_add()
    assert h._status == 201
    assert h._response["font"]["font_id"].startswith("fnt_")
    assert h._response["font"]["family"] == "Roboto"


def test_font_add_family_too_long():
    """POST rejects family > 64 chars."""
    body = {
        "family": "A" * 65,
        "weight": "400",
        "size": 16,
        "source_hash": _sha256("x"),
    }
    h = FakeHandler("POST", "/api/v1/font-manager/fonts", body=body, auth=True)
    h._handle_font_add()
    assert h._status == 400
    assert "64" in h._response["error"]


def test_font_add_invalid_weight():
    """POST rejects weight not in FONT_WEIGHTS."""
    body = {
        "family": "Roboto",
        "weight": "999",
        "size": 16,
        "source_hash": _sha256("x"),
    }
    h = FakeHandler("POST", "/api/v1/font-manager/fonts", body=body, auth=True)
    h._handle_font_add()
    assert h._status == 400


def test_font_add_invalid_size():
    """POST rejects size not in FONT_SIZES."""
    body = {
        "family": "Roboto",
        "weight": "400",
        "size": 99,
        "source_hash": _sha256("x"),
    }
    h = FakeHandler("POST", "/api/v1/font-manager/fonts", body=body, auth=True)
    h._handle_font_add()
    assert h._status == 400


def test_font_delete():
    """DELETE /api/v1/font-manager/fonts/{id} removes font."""
    body = {
        "family": "DeleteMe",
        "weight": "700",
        "size": 18,
        "source_hash": _sha256("deleteme"),
    }
    h = FakeHandler("POST", "/api/v1/font-manager/fonts", body=body, auth=True)
    h._handle_font_add()
    font_id = h._response["font"]["font_id"]

    h2 = FakeHandler("DELETE", f"/api/v1/font-manager/fonts/{font_id}", auth=True)
    h2._handle_font_delete(font_id)
    assert h2._status == 200
    assert h2._response["font_id"] == font_id


def test_font_delete_not_found():
    """DELETE non-existent font returns 404."""
    h = FakeHandler("DELETE", "/api/v1/font-manager/fonts/fnt_notexist", auth=True)
    h._handle_font_delete("fnt_notexist")
    assert h._status == 404


def test_font_apply_valid():
    """POST /api/v1/font-manager/apply updates active font."""
    body = {"family": "Georgia", "weight": "700", "size": 18}
    h = FakeHandler("POST", "/api/v1/font-manager/apply", body=body, auth=True)
    h._handle_font_apply()
    assert h._status == 200
    assert h._response["active_font"]["family"] == "Georgia"
    assert h._response["active_font"]["size"] == 18


def test_font_apply_invalid_size():
    """POST /api/v1/font-manager/apply rejects invalid size."""
    body = {"family": "Arial", "weight": "400", "size": 99}
    h = FakeHandler("POST", "/api/v1/font-manager/apply", body=body, auth=True)
    h._handle_font_apply()
    assert h._status == 400


def test_font_active_requires_auth():
    """GET /api/v1/font-manager/active requires auth."""
    h = FakeHandler("GET", "/api/v1/font-manager/active", auth=False)
    h._handle_font_active()
    assert h._status == 401


def test_font_active_returns_current():
    """GET /api/v1/font-manager/active returns current active font."""
    h = FakeHandler("GET", "/api/v1/font-manager/active", auth=True)
    h._handle_font_active()
    assert h._status == 200
    assert "active_font" in h._response
    assert "family" in h._response["active_font"]
