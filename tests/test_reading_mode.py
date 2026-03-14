# Diagram: 05-solace-runtime-architecture
"""Tests for Task 094 — Reading Mode."""
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
        self.path = ""
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


def make_handler(body=None, path=""):
    h = FakeHandler()
    h.path = path
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def setup_function():
    with ys._READING_LOCK:
        ys._READING_SESSIONS.clear()
        ys._READING_SETTINGS.update({"theme": "light", "font_size": 18, "line_height": "1.6", "column_width": "medium"})


def test_reading_session_create():
    url_hash = hashlib.sha256(b"https://example.com").hexdigest()
    title_hash = hashlib.sha256(b"Example Article").hexdigest()
    h = make_handler({"url_hash": url_hash, "title_hash": title_hash, "word_count": 400})
    h._handle_reading_session_create()
    assert len(h._responses) == 1
    code, data = h._responses[0]
    assert code == 201
    assert data["session"]["session_id"].startswith("rds_")
    assert data["session"]["reading_time_mins"] == 2  # ceil(400/200)


def test_reading_url_hashed():
    url_hash = hashlib.sha256(b"https://secret.example.com").hexdigest()
    title_hash = hashlib.sha256(b"Secret").hexdigest()
    h = make_handler({"url_hash": url_hash, "title_hash": title_hash, "word_count": 0})
    h._handle_reading_session_create()
    code, data = h._responses[0]
    assert code == 201
    session = data["session"]
    assert "url_hash" in session
    assert session["url_hash"] == url_hash
    # raw url must NOT be stored
    assert "url" not in session


def test_reading_session_list():
    url_hash = hashlib.sha256(b"https://list.example.com").hexdigest()
    title_hash = hashlib.sha256(b"List Test").hexdigest()
    h = make_handler({"url_hash": url_hash, "title_hash": title_hash, "word_count": 100})
    h._handle_reading_session_create()

    h2 = FakeHandler()
    h2._handle_reading_session_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["sessions"], list)
    assert data["total"] >= 1


def test_reading_session_delete():
    url_hash = hashlib.sha256(b"https://del.example.com").hexdigest()
    title_hash = hashlib.sha256(b"Delete Test").hexdigest()
    h = make_handler({"url_hash": url_hash, "title_hash": title_hash, "word_count": 50})
    h._handle_reading_session_create()
    session_id = h._responses[0][1]["session"]["session_id"]

    h2 = make_handler()
    h2._handle_reading_session_delete(session_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["session_id"] == session_id

    with ys._READING_LOCK:
        ids = [s["session_id"] for s in ys._READING_SESSIONS]
    assert session_id not in ids


def test_reading_session_not_found():
    h = make_handler()
    h._handle_reading_session_delete("rds_notexist")
    code, data = h._responses[0]
    assert code == 404


def test_reading_settings_update():
    h = make_handler({"theme": "sepia", "font_size": 20, "column_width": "wide"})
    h._handle_reading_settings_update()
    code, data = h._responses[0]
    assert code == 200
    assert data["settings"]["theme"] == "sepia"
    assert data["settings"]["font_size"] == 20
    assert data["settings"]["column_width"] == "wide"


def test_reading_settings_invalid_theme():
    h = make_handler({"theme": "neon"})
    h._handle_reading_settings_update()
    code, data = h._responses[0]
    assert code == 400
    assert "theme" in data["error"]


def test_reading_settings_invalid_size():
    h = make_handler({"font_size": 99})
    h._handle_reading_settings_update()
    code, data = h._responses[0]
    assert code == 400
    assert "font_size" in data["error"]


def test_reading_themes():
    h = FakeHandler()
    h._handle_reading_themes()
    code, data = h._responses[0]
    assert code == 200
    assert len(data["themes"]) == 5
    assert "light" in data["themes"]
    assert "sepia" in data["themes"]
    assert "paper" in data["themes"]


def test_no_port_9222_in_reading():
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found in yinyang_server.py — BANNED"
