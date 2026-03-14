# Diagram: 05-solace-runtime-architecture
"""Tests for Task 082 — User Preferences."""
import sys
import json

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "b" * 64


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
    if body is not None:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def clear_state():
    with ys._PREFS_LOCK:
        ys._USER_PREFS.clear()


def test_prefs_get_defaults():
    """GET → all schema keys present with defaults."""
    clear_state()
    h = make_handler()
    h._handle_prefs_get()
    code, data = h._responses[0]
    assert code == 200
    prefs = data["preferences"]
    for key, schema in ys.PREFERENCE_SCHEMA.items():
        assert key in prefs
        assert prefs[key] == schema["default"]


def test_prefs_set_theme():
    """POST theme=dark → saved."""
    clear_state()
    h = make_handler({"key": "theme", "value": "dark"})
    h._handle_prefs_set()
    code, data = h._responses[0]
    assert code == 200
    assert data["status"] == "saved"
    assert data["value"] == "dark"


def test_prefs_invalid_key():
    """Unknown pref_key → 400."""
    clear_state()
    h = make_handler({"key": "unknown_key_xyz", "value": "whatever"})
    h._handle_prefs_set()
    code, data = h._responses[0]
    assert code == 400
    assert "error" in data


def test_prefs_invalid_enum_value():
    """theme=purple → 400."""
    clear_state()
    h = make_handler({"key": "theme", "value": "purple"})
    h._handle_prefs_set()
    code, data = h._responses[0]
    assert code == 400
    assert "error" in data


def test_prefs_invalid_boolean():
    """notifications_enabled=42 → 400."""
    clear_state()
    h = make_handler({"key": "notifications_enabled", "value": 42})
    h._handle_prefs_set()
    code, data = h._responses[0]
    assert code == 400
    assert "error" in data


def test_prefs_integer_out_of_range():
    """session_timeout_minutes=4 → 400 (min is 5)."""
    clear_state()
    h = make_handler({"key": "session_timeout_minutes", "value": 4})
    h._handle_prefs_set()
    code, data = h._responses[0]
    assert code == 400
    assert "error" in data


def test_prefs_reset_key():
    """DELETE /theme → reverts to 'auto'."""
    clear_state()
    # First set theme to dark
    set_h = make_handler({"key": "theme", "value": "dark"})
    set_h._handle_prefs_set()
    # Now reset
    h = make_handler()
    h._handle_prefs_reset_key("theme")
    code, data = h._responses[0]
    assert code == 200
    assert data["status"] == "reset"
    assert data["value"] == "auto"  # schema default for theme


def test_prefs_reset_all():
    """POST /reset-all → all defaults."""
    clear_state()
    set_h = make_handler({"key": "theme", "value": "dark"})
    set_h._handle_prefs_set()
    h = make_handler()
    h._handle_prefs_reset_all()
    code, data = h._responses[0]
    assert code == 200
    assert data["status"] == "reset"
    prefs = data["preferences"]
    assert prefs["theme"] == "auto"
    assert prefs["language"] == "en"


def test_prefs_schema():
    """GET /schema → 8 keys with types."""
    h = FakeHandler()
    h._handle_prefs_schema()
    code, data = h._responses[0]
    assert code == 200
    schema = data["schema"]
    assert len(schema) == 8
    for key in ["theme", "language", "timezone", "notifications_enabled",
                "auto_save", "compact_view", "session_timeout_minutes", "result_page_size"]:
        assert key in schema
        assert "type" in schema[key]


def test_no_port_9222_in_prefs():
    """No port 9222 in preferences code."""
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found — BANNED"
