"""
Tests for Task 051 — Session Notes
Browser: yinyang_server.py routes /api/v1/notes/*
"""
import sys
import json

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


def test_notes_list_empty():
    import yinyang_server as ys
    ys._NOTES.clear()
    h = _make_handler()
    h._handle_notes_list()
    status, data = h._responses[0]
    assert status == 200
    assert data["notes"] == []
    assert data["total"] == 0


def test_notes_add():
    import yinyang_server as ys
    ys._NOTES.clear()
    h = _make_handler({"title": "My Note", "body": "body text", "tags": []})
    h._handle_notes_add()
    status, data = h._responses[0]
    assert status == 200
    assert data["note_id"].startswith("note_")


def test_notes_list_includes_added():
    import yinyang_server as ys
    ys._NOTES.clear()
    h1 = _make_handler({"title": "Listed", "body": "b", "tags": []})
    h1._handle_notes_add()
    h2 = _make_handler()
    h2._handle_notes_list()
    status, data = h2._responses[0]
    assert data["total"] == 1


def test_notes_get():
    import yinyang_server as ys
    ys._NOTES.clear()
    h1 = _make_handler({"title": "GetMe", "body": "txt", "tags": []})
    h1._handle_notes_add()
    note_id = h1._responses[0][1]["note_id"]
    h2 = _make_handler()
    h2._handle_notes_get(note_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["note_id"] == note_id


def test_notes_delete():
    import yinyang_server as ys
    ys._NOTES.clear()
    h1 = _make_handler({"title": "Del", "body": "b", "tags": []})
    h1._handle_notes_add()
    note_id = h1._responses[0][1]["note_id"]
    h2 = _make_handler()
    h2._handle_notes_delete(note_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"


def test_notes_delete_not_found():
    h = _make_handler()
    h._handle_notes_delete("note_nonexistent_xyz")
    status, data = h._responses[0]
    assert status == 404


def test_notes_no_auth():
    h = _make_handler({"title": "X", "body": "b", "tags": []}, auth=False)
    h._handle_notes_add()
    status, data = h._responses[0]
    assert status == 401


def test_notes_search():
    import yinyang_server as ys
    ys._NOTES.clear()
    h1 = _make_handler({"title": "Searchable Note", "body": "find me", "tags": []})
    h1._handle_notes_add()
    h2 = _make_handler({"title": "Other", "body": "unrelated", "tags": []})
    h2._handle_notes_add()
    h3 = _make_handler()
    h3._handle_notes_search("searchable")
    status, data = h3._responses[0]
    assert status == 200
    assert data["total"] >= 1


def test_notes_tags():
    import yinyang_server as ys
    ys._NOTES.clear()
    h1 = _make_handler({"title": "Tagged", "body": "b", "tags": ["work", "urgent"]})
    h1._handle_notes_add()
    note_id = h1._responses[0][1]["note_id"]
    h2 = _make_handler()
    h2._handle_notes_get(note_id)
    _, data = h2._responses[0]
    assert "work" in data.get("tags", [])


def test_notes_html_no_cdn():
    html = open("/home/phuc/projects/solace-browser/web/session-notes.html").read()
    assert "cdn.jsdelivr" not in html and "unpkg.com" not in html


def test_no_port_9222_in_notes():
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    import re
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0
