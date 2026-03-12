"""Tests for Task 191 — Error Boundary Tracker."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yinyang_server as ys


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []

    def _send_json(self, data, status=200):
        self._responses.append((status, data))

    def _check_auth(self):
        return True

    def _read_json_body(self):
        return self._body


def make_handler(body=None):
    h = FakeHandler()
    h._body = body or {}
    return h


def _valid_body(**kwargs):
    base = {
        "error_type": "TypeError",
        "severity": "medium",
        "was_caught": False,
        "url": "https://example.com/page",
        "message": "Cannot read property of undefined",
    }
    base.update(kwargs)
    return base


def test_event_create():
    h = make_handler(_valid_body())
    ys._ERROR_BOUNDARY_EVENTS.clear()
    h._handle_ebt_create()
    assert h._responses[0][0] == 201
    assert h._responses[0][1]["event_id"].startswith("ebt_")


def test_event_url_hashed():
    h = make_handler(_valid_body(url="https://secret.example.com"))
    ys._ERROR_BOUNDARY_EVENTS.clear()
    h._handle_ebt_create()
    record = h._responses[0][1]
    assert "url_hash" in record
    assert record["url_hash"] != "https://secret.example.com"
    assert len(record["url_hash"]) == 64


def test_event_message_hashed():
    h = make_handler(_valid_body(message="Secret error msg"))
    ys._ERROR_BOUNDARY_EVENTS.clear()
    h._handle_ebt_create()
    record = h._responses[0][1]
    assert "message_hash" in record
    assert record["message_hash"] != "Secret error msg"
    assert len(record["message_hash"]) == 64


def test_event_invalid_error_type():
    h = make_handler(_valid_body(error_type="FakeError"))
    h._handle_ebt_create()
    assert h._responses[0][0] == 400


def test_event_invalid_severity():
    h = make_handler(_valid_body(severity="fatal"))
    h._handle_ebt_create()
    assert h._responses[0][0] == 400


def test_event_caught_flag():
    h = make_handler(_valid_body(was_caught=False))
    ys._ERROR_BOUNDARY_EVENTS.clear()
    h._handle_ebt_create()
    assert h._responses[0][1]["was_caught"] is False


def test_event_list():
    ys._ERROR_BOUNDARY_EVENTS.clear()
    h = make_handler(_valid_body())
    h._handle_ebt_create()
    h2 = make_handler()
    h2._handle_ebt_list()
    status, data = h2._responses[0]
    assert status == 200
    assert "events" in data
    assert data["total"] >= 1


def test_event_delete():
    ys._ERROR_BOUNDARY_EVENTS.clear()
    h = make_handler(_valid_body())
    h._handle_ebt_create()
    event_id = h._responses[0][1]["event_id"]
    h2 = make_handler()
    h2._handle_ebt_delete(event_id)
    assert h2._responses[0][0] == 200
    assert h2._responses[0][1]["status"] == "deleted"
    assert len(ys._ERROR_BOUNDARY_EVENTS) == 0


def test_error_stats():
    ys._ERROR_BOUNDARY_EVENTS.clear()
    h = make_handler(_valid_body(was_caught=False))
    h._handle_ebt_create()
    h2 = make_handler()
    h2._handle_ebt_stats()
    status, data = h2._responses[0]
    assert status == 200
    assert "uncaught_rate" in data
    # Must be a Decimal string with 2 decimal places
    import re
    assert re.match(r"^\d+\.\d{2}$", data["uncaught_rate"])


def test_no_port_9222_in_error():
    with open(os.path.abspath(__file__)) as f:
        content = f.read()
    assert "9222" not in content
