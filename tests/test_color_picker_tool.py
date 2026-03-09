"""
Tests for Task 097 — Color Picker Tool
Browser: yinyang_server.py routes /api/v1/color-picker
"""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
import json
import hashlib
from io import BytesIO

VALID_TOKEN = hashlib.sha256(b"test-token").hexdigest()


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


def setup_function():
    ys._SAVED_COLORS.clear()
    ys._COLOR_PALETTES.clear()


def test_color_save():
    h = FakeHandler("POST", "/api/v1/color-picker/colors", {
        "format": "hex",
        "value_hash": "a" * 64,
        "source_url_hash": "b" * 64,
    })
    h._handle_color_save()
    assert h._status == 201
    assert h._response["color"]["color_id"].startswith("clr_")
    assert h._response["status"] == "saved"


def test_color_value_hashed():
    h = FakeHandler("POST", "/api/v1/color-picker/colors", {
        "format": "rgb",
        "value_hash": "c" * 64,
        "source_url_hash": "d" * 64,
    })
    h._handle_color_save()
    assert h._status == 201
    assert "value_hash" in h._response["color"]
    assert h._response["color"]["value_hash"] == "c" * 64


def test_color_invalid_format():
    h = FakeHandler("POST", "/api/v1/color-picker/colors", {
        "format": "invalid_fmt",
        "value_hash": "e" * 64,
        "source_url_hash": "f" * 64,
    })
    h._handle_color_save()
    assert h._status == 400
    assert "format" in h._response["error"]


def test_color_list():
    # Save a color first
    h1 = FakeHandler("POST", "/api/v1/color-picker/colors", {
        "format": "hsl",
        "value_hash": "g" * 64,
        "source_url_hash": "h" * 64,
    })
    h1._handle_color_save()

    h2 = FakeHandler("GET", "/api/v1/color-picker/colors")
    h2._handle_color_list()
    assert h2._status == 200
    assert isinstance(h2._response["colors"], list)
    assert h2._response["total"] >= 1


def test_color_delete():
    h1 = FakeHandler("POST", "/api/v1/color-picker/colors", {
        "format": "oklch",
        "value_hash": "i" * 64,
        "source_url_hash": "j" * 64,
    })
    h1._handle_color_save()
    color_id = h1._response["color"]["color_id"]

    h2 = FakeHandler("DELETE", f"/api/v1/color-picker/colors/{color_id}")
    h2._handle_color_delete(color_id)
    assert h2._status == 200
    assert h2._response["status"] == "deleted"
    assert h2._response["color_id"] == color_id


def test_color_not_found():
    h = FakeHandler("DELETE", "/api/v1/color-picker/colors/clr_nonexistent")
    h._handle_color_delete("clr_nonexistent")
    assert h._status == 404


def test_palette_create():
    # First save some colors
    h1 = FakeHandler("POST", "/api/v1/color-picker/colors", {
        "format": "rgba",
        "value_hash": "k" * 64,
        "source_url_hash": "l" * 64,
    })
    h1._handle_color_save()
    color_id = h1._response["color"]["color_id"]

    h2 = FakeHandler("POST", "/api/v1/color-picker/palettes", {
        "name_hash": "m" * 64,
        "color_ids": [color_id],
    })
    h2._handle_palette_create()
    assert h2._status == 201
    assert h2._response["palette"]["palette_id"].startswith("pal_")
    assert h2._response["status"] == "created"
    assert h2._response["palette"]["size"] == 1


def test_palette_list():
    h = FakeHandler("GET", "/api/v1/color-picker/palettes")
    h._handle_palette_list()
    assert h._status == 200
    assert "palettes" in h._response
    assert "total" in h._response


def test_formats_list():
    h = FakeHandler("GET", "/api/v1/color-picker/formats")
    h._handle_color_formats()
    assert h._status == 200
    assert "formats" in h._response
    assert len(h._response["formats"]) == 7
    assert "hex" in h._response["formats"]
    assert "oklch" in h._response["formats"]


def test_no_port_9222_in_color():
    src = (REPO_ROOT / "yinyang_server.py").read_text()
    # Ensure the banned port does not appear
    assert "9222" not in src or src.count("9222") == src.count("permanently banned") + src.count("debug port")
    # Simple check: file does not contain raw 9222 usage in color routes
    color_section_start = src.find("Task 097")
    color_section_end = src.find("Task 098")
    color_section = src[color_section_start:color_section_end] if color_section_start != -1 else ""
    assert "9222" not in color_section
