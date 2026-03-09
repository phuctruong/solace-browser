"""Tests for Task 072 — Password Generator."""
import sys
import json
import hashlib

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "a" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
        self.headers = {"content-length": "0", "Authorization": f"Bearer {VALID_TOKEN}"}

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass

    def send_response(self, code):
        self._responses.append((code, {}))

    def end_headers(self):
        pass


def make_handler(body=None):
    h = FakeHandler()
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def setup_function():
    with ys._PW_LOCK:
        ys._PASSWORD_HISTORY.clear()


def test_pw_generate():
    h = make_handler({"length": 16, "charsets": ["uppercase", "lowercase", "numbers"]})
    h._handle_pw_generate()
    code, data = h._responses[0]
    assert code == 201
    ph = data.get("password_hash", "")
    # must be a 64-char hex SHA-256
    assert len(ph) == 64
    assert all(c in "0123456789abcdef" for c in ph)


def test_pw_generate_length_too_short():
    h = make_handler({"length": 7, "charsets": ["lowercase"]})
    h._handle_pw_generate()
    code, data = h._responses[0]
    assert code == 400
    assert "8" in data["error"]


def test_pw_generate_length_too_long():
    h = make_handler({"length": 129, "charsets": ["lowercase"]})
    h._handle_pw_generate()
    code, data = h._responses[0]
    assert code == 400
    assert "128" in data["error"]


def test_pw_generate_no_charsets():
    h = make_handler({"length": 16, "charsets": []})
    h._handle_pw_generate()
    code, data = h._responses[0]
    assert code == 400


def test_pw_audit_strong():
    # Very long password with multiple charsets
    strong_pw = "Abc1!XyZ2@QwE3#MnO4$PqR"
    h = make_handler({"password": strong_pw})
    h._handle_pw_audit()
    code, data = h._responses[0]
    assert code == 200
    assert data["strength_level"] in ("strong", "very_strong")


def test_pw_audit_weak():
    h = make_handler({"password": "abc"})
    h._handle_pw_audit()
    code, data = h._responses[0]
    assert code == 200
    assert data["strength_level"] == "very_weak"


def test_pw_history_requires_auth():
    class NoAuthHandler(FakeHandler):
        def _check_auth(self):
            self._send_json({"error": "unauthorized"}, 401)
            return False

    h = NoAuthHandler()
    h._handle_pw_history_list()
    code, data = h._responses[0]
    assert code == 401


def test_pw_history_cleared():
    h = make_handler()
    h._handle_pw_history_clear()
    # 204 No Content
    assert any(code == 204 for code, _ in h._responses)


def test_pw_options():
    h = FakeHandler()
    h._handle_pw_options()
    code, data = h._responses[0]
    assert code == 200
    assert "charsets" in data
    assert "uppercase" in data["charsets"]
    assert "lowercase" in data["charsets"]
    assert "numbers" in data["charsets"]
    assert "symbols" in data["charsets"]


def test_no_port_9222_in_password():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found in yinyang_server.py — BANNED"
