# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 151 — Clipboard History
Browser: yinyang_server.py routes /api/v1/clipboard/*
"""
import sys
import json
import re

sys.path.insert(0, "/home/phuc/projects/solace-browser")

TOKEN = "test-token-sha256"


def _make_handler(body=None, auth=True):
    import yinyang_server as ys

    class FakeHandler(ys.YinyangHandler):
        def __init__(self):
            self._token = TOKEN
            self._responses = []
            self._body = json.dumps(body).encode() if body else b"{}"

        def _read_json_body(self):
            return json.loads(self._body)

        def _send_json(self, data, status=200):
            self._responses.append((status, data))

        def _check_auth(self):
            if not auth:
                self._send_json({"error": "unauthorized"}, 401)
                return False
            return True

    return FakeHandler()


def test_entry_create():
    import yinyang_server as ys
    ys._CLIPBOARD_ENTRIES.clear()
    h = _make_handler({"content_type": "text", "content": "hello world", "char_count": 11})
    h._handle_clp_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["entry_id"].startswith("clp_")


def test_entry_content_hashed():
    import yinyang_server as ys
    ys._CLIPBOARD_ENTRIES.clear()
    h = _make_handler({"content_type": "code", "content": "print('hi')", "char_count": 11})
    h._handle_clp_create()
    _, data = h._responses[0]
    entry_id = data["entry_id"]
    # Check the stored entry has content_hash, not raw content
    with ys._CLIPBOARD_LOCK:
        entry = next(e for e in ys._CLIPBOARD_ENTRIES if e["entry_id"] == entry_id)
    assert "content_hash" in entry
    assert "content" not in entry


def test_entry_invalid_type():
    import yinyang_server as ys
    ys._CLIPBOARD_ENTRIES.clear()
    h = _make_handler({"content_type": "video", "content": "x", "char_count": 1})
    h._handle_clp_create()
    status, data = h._responses[0]
    assert status == 400


def test_entry_negative_chars():
    import yinyang_server as ys
    ys._CLIPBOARD_ENTRIES.clear()
    h = _make_handler({"content_type": "text", "content": "x", "char_count": -1})
    h._handle_clp_create()
    status, data = h._responses[0]
    assert status == 400


def test_entry_sensitive_flag():
    import yinyang_server as ys
    ys._CLIPBOARD_ENTRIES.clear()
    h = _make_handler({"content_type": "password", "content": "s3cr3t", "char_count": 6})
    h._handle_clp_create()
    _, resp = h._responses[0]
    entry_id = resp["entry_id"]
    with ys._CLIPBOARD_LOCK:
        entry = next(e for e in ys._CLIPBOARD_ENTRIES if e["entry_id"] == entry_id)
    assert entry["is_sensitive"] is True


def test_entry_list():
    import yinyang_server as ys
    ys._CLIPBOARD_ENTRIES.clear()
    h1 = _make_handler({"content_type": "url", "content": "https://example.com", "char_count": 19})
    h1._handle_clp_create()
    h2 = _make_handler()
    h2._handle_clp_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["entries"], list)


def test_entry_delete_single():
    import yinyang_server as ys
    ys._CLIPBOARD_ENTRIES.clear()
    h1 = _make_handler({"content_type": "text", "content": "delete me", "char_count": 9})
    h1._handle_clp_create()
    entry_id = h1._responses[0][1]["entry_id"]
    h2 = _make_handler()
    h2._handle_clp_delete(entry_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    with ys._CLIPBOARD_LOCK:
        assert not any(e["entry_id"] == entry_id for e in ys._CLIPBOARD_ENTRIES)


def test_entry_clear_all():
    import yinyang_server as ys
    ys._CLIPBOARD_ENTRIES.clear()
    for i in range(3):
        h = _make_handler({"content_type": "text", "content": f"item {i}", "char_count": 6})
        h._handle_clp_create()
    h_del = _make_handler()
    h_del._handle_clp_clear_all()
    status, data = h_del._responses[0]
    assert status == 200
    assert data["status"] == "cleared"
    with ys._CLIPBOARD_LOCK:
        assert len(ys._CLIPBOARD_ENTRIES) == 0


def test_entry_not_found():
    import yinyang_server as ys
    ys._CLIPBOARD_ENTRIES.clear()
    h = _make_handler()
    h._handle_clp_delete("clp_notexist")
    status, data = h._responses[0]
    assert status == 404


def test_no_port_9222_in_clipboard():
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0
