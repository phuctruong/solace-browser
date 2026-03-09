"""
Tests for Task 143 — Form Autofill Tracker
Browser: yinyang_server.py routes /api/v1/autofill/*
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


def test_entry_create():
    import yinyang_server as ys
    ys._AUTOFILL_ENTRIES.clear()
    h = _make_handler({"field_type": "email", "field_name": "email_field", "url": "https://example.com", "value": "user@example.com", "success": True})
    h._handle_autofill_entry_create()
    status, data = h._responses[0]
    assert status == 201
    assert data["entry"]["entry_id"].startswith("aft_")


def test_entry_url_hashed():
    import yinyang_server as ys
    ys._AUTOFILL_ENTRIES.clear()
    h = _make_handler({"field_type": "text", "field_name": "name", "url": "https://example.com/form", "value": "John Doe", "success": True})
    h._handle_autofill_entry_create()
    _, data = h._responses[0]
    entry = data["entry"]
    assert "url_hash" in entry
    assert "url" not in entry
    # Verify hash is SHA-256 (64 hex chars)
    assert len(entry["url_hash"]) == 64


def test_entry_value_hashed():
    import yinyang_server as ys
    ys._AUTOFILL_ENTRIES.clear()
    h = _make_handler({"field_type": "name", "field_name": "fullname", "url": "https://example.com", "value": "Jane Smith", "success": True})
    h._handle_autofill_entry_create()
    _, data = h._responses[0]
    entry = data["entry"]
    assert "value_hash" in entry
    assert "value" not in entry
    assert len(entry["value_hash"]) == 64


def test_entry_invalid_type():
    import yinyang_server as ys
    ys._AUTOFILL_ENTRIES.clear()
    h = _make_handler({"field_type": "invalid_type", "field_name": "x", "url": "https://example.com", "value": "y", "success": True})
    h._handle_autofill_entry_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_entry_field_name_too_long():
    import yinyang_server as ys
    ys._AUTOFILL_ENTRIES.clear()
    long_name = "x" * 101
    h = _make_handler({"field_type": "text", "field_name": long_name, "url": "https://example.com", "value": "val", "success": True})
    h._handle_autofill_entry_create()
    status, data = h._responses[0]
    assert status == 400
    assert "error" in data


def test_entry_list():
    import yinyang_server as ys
    ys._AUTOFILL_ENTRIES.clear()
    h1 = _make_handler({"field_type": "email", "field_name": "e", "url": "https://example.com", "value": "a@b.com", "success": True})
    h1._handle_autofill_entry_create()
    h2 = _make_handler()
    h2._handle_autofill_entries_list()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total"] >= 1
    assert isinstance(data["entries"], list)


def test_entry_delete():
    import yinyang_server as ys
    ys._AUTOFILL_ENTRIES.clear()
    h1 = _make_handler({"field_type": "phone", "field_name": "p", "url": "https://example.com", "value": "555-1234", "success": True})
    h1._handle_autofill_entry_create()
    entry_id = h1._responses[0][1]["entry"]["entry_id"]
    h2 = _make_handler()
    h2._handle_autofill_entry_delete(entry_id)
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "deleted"
    # Verify removed from list
    h3 = _make_handler()
    h3._handle_autofill_entries_list()
    _, list_data = h3._responses[0]
    assert list_data["total"] == 0


def test_entry_not_found():
    import yinyang_server as ys
    ys._AUTOFILL_ENTRIES.clear()
    h = _make_handler()
    h._handle_autofill_entry_delete("aft_notexist")
    status, data = h._responses[0]
    assert status == 404


def test_autofill_stats():
    import yinyang_server as ys
    ys._AUTOFILL_ENTRIES.clear()
    # Add 2 success + 1 fail
    h1 = _make_handler({"field_type": "email", "field_name": "e", "url": "https://example.com", "value": "a@b.com", "success": True})
    h1._handle_autofill_entry_create()
    h2 = _make_handler({"field_type": "text", "field_name": "n", "url": "https://example.com", "value": "John", "success": True})
    h2._handle_autofill_entry_create()
    h3 = _make_handler({"field_type": "phone", "field_name": "p", "url": "https://example.com", "value": "555", "success": False})
    h3._handle_autofill_entry_create()
    h_stats = _make_handler()
    h_stats._handle_autofill_entries_stats()
    status, data = h_stats._responses[0]
    assert status == 200
    assert data["total_fills"] == 3
    assert data["success_count"] == 2
    assert data["fail_count"] == 1
    # success_rate should be a Decimal string
    rate = data["success_rate"]
    assert isinstance(rate, str)
    float(rate)  # must be parseable as float
    assert "by_field_type" in data


def test_no_port_9222_in_autofill():
    import re
    content = open("/home/phuc/projects/solace-browser/yinyang_server.py").read()
    matches = [m.start() for m in re.finditer(r'9222', content)]
    assert len(matches) == 0, f"Found port 9222 at positions: {matches}"
