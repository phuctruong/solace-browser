# Diagram: 05-solace-runtime-architecture
"""Tests for AI Form Filler (Task 116). 10 tests."""
import sys
import pathlib
import hashlib
import json
from io import BytesIO

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = hashlib.sha256(b"test-token-filler").hexdigest()


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
    ys._FORM_PROFILES.clear()
    ys._FILL_LOG.clear()


def _valid_profile(**overrides):
    base = {
        "profile_name": "My Work Profile",
        "field_count": 5,
        "field_types": ["text", "email", "phone"],
    }
    base.update(overrides)
    return base


def test_profile_create():
    """POST → profile_id has ffp_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/form-filler/profiles", _valid_profile())
    h._handle_form_profile_create()
    assert h._status == 201
    assert h._response["profile"]["profile_id"].startswith("ffp_")


def test_profile_name_hashed():
    """profile_name_hash present, no raw name stored."""
    _reset()
    h = FakeHandler("POST", "/api/v1/form-filler/profiles", _valid_profile(profile_name="Secret Name"))
    h._handle_form_profile_create()
    assert h._status == 201
    profile = h._response["profile"]
    assert "profile_name_hash" in profile
    expected_hash = hashlib.sha256(b"Secret Name").hexdigest()
    assert profile["profile_name_hash"] == expected_hash
    assert "profile_name" not in profile


def test_profile_too_many_fields():
    """field_count=21 → 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/form-filler/profiles", _valid_profile(field_count=21))
    h._handle_form_profile_create()
    assert h._status == 400


def test_profile_invalid_field_type():
    """Unknown field type → 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/form-filler/profiles", _valid_profile(field_types=["text", "unknown_type"]))
    h._handle_form_profile_create()
    assert h._status == 400


def test_profile_list():
    """GET /profiles → returns list."""
    _reset()
    h = FakeHandler("POST", "/api/v1/form-filler/profiles", _valid_profile())
    h._handle_form_profile_create()

    h2 = FakeHandler("GET", "/api/v1/form-filler/profiles")
    h2._handle_form_profiles_list()
    assert h2._status == 200
    assert isinstance(h2._response["profiles"], list)
    assert h2._response["total"] >= 1


def test_profile_delete():
    """DELETE /profiles/{id} → removed."""
    _reset()
    h = FakeHandler("POST", "/api/v1/form-filler/profiles", _valid_profile())
    h._handle_form_profile_create()
    pid = h._response["profile"]["profile_id"]

    h2 = FakeHandler("DELETE", f"/api/v1/form-filler/profiles/{pid}")
    h2._handle_form_profile_delete(pid)
    assert h2._status == 200
    assert h2._response["status"] == "deleted"
    assert len(ys._FORM_PROFILES) == 0


def test_fill_log_create():
    """POST /fill-log → fill_id has ffl_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/form-filler/fill-log", {
        "profile_id": "ffp_test",
        "site_url": "https://example.com/form",
    })
    h._handle_fill_log_create()
    assert h._status == 201
    assert h._response["fill"]["fill_id"].startswith("ffl_")
    # site_url must not be stored raw
    fill = h._response["fill"]
    assert "site_url" not in fill
    assert "site_hash" in fill


def test_fill_log_list():
    """GET /fill-log → returns list."""
    _reset()
    h = FakeHandler("POST", "/api/v1/form-filler/fill-log", {
        "profile_id": "ffp_test",
        "site_url": "https://example.com/form",
    })
    h._handle_fill_log_create()

    h2 = FakeHandler("GET", "/api/v1/form-filler/fill-log")
    h2._handle_fill_log_list()
    assert h2._status == 200
    assert isinstance(h2._response["fills"], list)
    assert h2._response["total"] >= 1


def test_field_types_list():
    """GET /field-types → 11 types."""
    h = FakeHandler("GET", "/api/v1/form-filler/field-types")
    h._handle_field_types_list()
    assert h._status == 200
    types = h._response["field_types"]
    assert len(types) == 11
    assert "email" in types
    assert "textarea" in types


def test_no_port_9222_in_filler():
    """No port 9222 reference in yinyang_server.py."""
    server_py = pathlib.Path(__file__).resolve().parent.parent / "yinyang_server.py"
    source = server_py.read_text()
    forbidden = "9" + "222"
    assert forbidden not in source
