"""Tests for Task 083 — DevTools Assistant."""
import sys
import json
import hashlib

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "c" * 64


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
    with ys._DEVTOOLS_LOCK:
        ys._DEVTOOLS_SNIPPETS.clear()
        ys._CONSOLE_LOGS.clear()


def test_snippet_save():
    """POST → snp_ prefix, content_hash present."""
    clear_state()
    h = make_handler({"language": "javascript", "title": "Hello World", "content": "console.log('hi');"})
    h._handle_devtools_snippet_save()
    code, data = h._responses[0]
    assert code == 201
    assert data["snippet"]["snippet_id"].startswith("snp_")
    assert "content_hash" in data["snippet"]


def test_snippet_content_hashed():
    """No raw code in response — only content_hash."""
    clear_state()
    h = make_handler({"language": "python", "title": "Secret", "content": "import os; os.system('rm -rf /')"})
    h._handle_devtools_snippet_save()
    code, data = h._responses[0]
    assert code == 201
    snippet = data["snippet"]
    assert "content" not in snippet
    assert "content_hash" in snippet
    expected = hashlib.sha256("import os; os.system('rm -rf /')".encode()).hexdigest()
    assert snippet["content_hash"] == expected


def test_snippet_invalid_language():
    """Unknown language → 400."""
    clear_state()
    h = make_handler({"language": "cobol", "title": "Old Code", "content": "MOVE 1 TO X."})
    h._handle_devtools_snippet_save()
    code, data = h._responses[0]
    assert code == 400
    assert "error" in data


def test_snippet_list():
    """GET → list returned."""
    clear_state()
    save = make_handler({"language": "bash", "title": "List Files", "content": "ls -la"})
    save._handle_devtools_snippet_save()
    h = make_handler()
    h._handle_devtools_snippets_list()
    code, data = h._responses[0]
    assert code == 200
    assert "snippets" in data
    assert len(data["snippets"]) >= 1


def test_snippet_delete():
    """DELETE → removed from list."""
    clear_state()
    save = make_handler({"language": "json", "title": "Config", "content": '{"key": "val"}'})
    save._handle_devtools_snippet_save()
    snippet_id = save._responses[0][1]["snippet"]["snippet_id"]
    h = make_handler()
    h._handle_devtools_snippet_delete(snippet_id)
    code, data = h._responses[0]
    assert code == 200
    assert data["status"] == "deleted"
    with ys._DEVTOOLS_LOCK:
        ids = [s["snippet_id"] for s in ys._DEVTOOLS_SNIPPETS]
    assert snippet_id not in ids


def test_snippet_not_found():
    """DELETE snp_notexist → 404."""
    clear_state()
    h = make_handler()
    h._handle_devtools_snippet_delete("snp_doesnotexist")
    code, data = h._responses[0]
    assert code == 404
    assert "error" in data


def test_console_log_record():
    """POST → clog_ prefix."""
    clear_state()
    h = make_handler({"log_level": "error", "message": "TypeError: null is not an object", "page_url": "https://app.example.com"})
    h._handle_devtools_console_record()
    code, data = h._responses[0]
    assert code == 201
    assert data["log_id"].startswith("clog_")


def test_console_invalid_level():
    """Unknown log level → 400."""
    clear_state()
    h = make_handler({"log_level": "critical", "message": "Boom", "page_url": "https://example.com"})
    h._handle_devtools_console_record()
    code, data = h._responses[0]
    assert code == 400
    assert "error" in data


def test_console_clear():
    """DELETE /console-logs → empty."""
    clear_state()
    rec = make_handler({"log_level": "info", "message": "Server started", "page_url": "https://localhost"})
    rec._handle_devtools_console_record()
    with ys._DEVTOOLS_LOCK:
        assert len(ys._CONSOLE_LOGS) >= 1
    h = make_handler()
    h._handle_devtools_console_clear()
    code, data = h._responses[0]
    assert code == 200
    assert data["status"] == "cleared"
    with ys._DEVTOOLS_LOCK:
        assert len(ys._CONSOLE_LOGS) == 0


def test_no_port_9222_in_devtools():
    """No port 9222 in devtools assistant code."""
    with open("/home/phuc/projects/solace-browser/yinyang_server.py") as f:
        content = f.read()
    assert "9222" not in content, "Port 9222 found — BANNED"
