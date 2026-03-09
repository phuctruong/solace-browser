"""Tests for Password Strength Checker (Task 118). 10 tests."""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
import json
import hashlib
from io import BytesIO


VALID_TOKEN = hashlib.sha256(b"test-pwd-token").hexdigest()


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
    ys._PASSWORD_CHECKS.clear()


def test_check_create():
    """POST creates check with psc_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/password-checker/checks", {
        "password": "MyP@ssw0rd!",
        "score": 4,
        "length": 11,
        "has_uppercase": True,
        "has_numbers": True,
        "has_symbols": True,
    })
    h._handle_password_check_create()
    assert h._status == 201
    check = h._response["check"]
    assert check["check_id"].startswith("psc_")


def test_check_password_hashed():
    """password_hash present, no raw password stored."""
    _reset()
    h = FakeHandler("POST", "/api/v1/password-checker/checks", {
        "password": "secret123",
        "score": 2,
        "length": 9,
        "has_uppercase": False,
        "has_numbers": True,
        "has_symbols": False,
    })
    h._handle_password_check_create()
    assert h._status == 201
    check = h._response["check"]
    assert "password_hash" in check
    assert "secret123" not in str(check)
    expected = hashlib.sha256(b"secret123").hexdigest()
    assert check["password_hash"] == expected


def test_check_score_too_low():
    """score=-1 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/password-checker/checks", {
        "password": "test",
        "score": -1,
        "length": 4,
        "has_uppercase": False,
        "has_numbers": False,
        "has_symbols": False,
    })
    h._handle_password_check_create()
    assert h._status == 400


def test_check_score_too_high():
    """score=6 returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/password-checker/checks", {
        "password": "test",
        "score": 6,
        "length": 4,
        "has_uppercase": False,
        "has_numbers": False,
        "has_symbols": False,
    })
    h._handle_password_check_create()
    assert h._status == 400


def test_check_strength_level():
    """score=5 returns strength_level=very_strong."""
    _reset()
    h = FakeHandler("POST", "/api/v1/password-checker/checks", {
        "password": "Ultra$ecure#99!",
        "score": 5,
        "length": 15,
        "has_uppercase": True,
        "has_numbers": True,
        "has_symbols": True,
    })
    h._handle_password_check_create()
    assert h._status == 201
    assert h._response["check"]["strength_level"] == "very_strong"


def test_check_strength_level_weak():
    """score=1 returns strength_level=weak."""
    _reset()
    h = FakeHandler("POST", "/api/v1/password-checker/checks", {
        "password": "abc",
        "score": 1,
        "length": 3,
        "has_uppercase": False,
        "has_numbers": False,
        "has_symbols": False,
    })
    h._handle_password_check_create()
    assert h._status == 201
    assert h._response["check"]["strength_level"] == "weak"


def test_check_list():
    """GET returns list of checks."""
    _reset()
    h = FakeHandler("POST", "/api/v1/password-checker/checks", {
        "password": "Test123!",
        "score": 3,
        "length": 8,
        "has_uppercase": True,
        "has_numbers": True,
        "has_symbols": True,
    })
    h._handle_password_check_create()
    h2 = FakeHandler("GET", "/api/v1/password-checker/checks")
    h2._handle_password_checks_list()
    assert h2._status == 200
    assert "checks" in h2._response
    assert h2._response["total"] == 1


def test_check_delete():
    """DELETE removes the check."""
    _reset()
    h = FakeHandler("POST", "/api/v1/password-checker/checks", {
        "password": "ToDelete1!",
        "score": 3,
        "length": 10,
        "has_uppercase": True,
        "has_numbers": True,
        "has_symbols": True,
    })
    h._handle_password_check_create()
    check_id = h._response["check"]["check_id"]

    dh = FakeHandler("DELETE", f"/api/v1/password-checker/checks/{check_id}")
    dh._handle_password_check_delete(check_id)
    assert dh._status == 200
    assert dh._response["status"] == "deleted"

    lh = FakeHandler("GET", "/api/v1/password-checker/checks")
    lh._handle_password_checks_list()
    assert lh._response["total"] == 0


def test_strength_levels_list():
    """GET /strength-levels returns 5 levels."""
    h = FakeHandler("GET", "/api/v1/password-checker/strength-levels")
    h._handle_password_strength_levels()
    assert h._status == 200
    assert len(h._response["strength_levels"]) == 5
    assert "very_weak" in h._response["strength_levels"]
    assert "very_strong" in h._response["strength_levels"]


def test_no_legacy_debug_port_in_password():
    """Grep check: legacy debug port must not appear in this file."""
    banned_port = "92" + "22"  # split to avoid self-matching
    source = pathlib.Path(__file__).read_text()
    assert banned_port not in source
