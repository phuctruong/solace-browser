# Diagram: 05-solace-runtime-architecture
"""Tests for Task 162 — Geolocation Tracker."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yinyang_server as ys


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._response_code = None
        self._response_body = None

    def _send_json(self, data, status=200):
        self._response_code = status
        self._response_body = data

    def _check_auth(self):
        return True

    def _require_auth(self):
        pass


def make_handler():
    return FakeHandler()


def _create_event(extra=None):
    h = make_handler()
    ys._GEO_EVENTS.clear()
    payload = {
        "url": "https://maps.example.com",
        "event_type": "permission_requested",
        "accuracy_meters": 10,
        "is_https": True,
    }
    if extra:
        payload.update(extra)
    h._read_json_body = lambda: payload
    h._handle_geo_event_create()
    return h


def test_event_create():
    h = _create_event()
    assert h._response_code == 201
    assert h._response_body["event"]["event_id"].startswith("geo_")


def test_event_url_hashed():
    h = _create_event()
    event = h._response_body["event"]
    assert "url_hash" in event
    assert len(event["url_hash"]) == 64
    assert "url" not in event


def test_event_invalid_type():
    h = make_handler()
    ys._GEO_EVENTS.clear()
    payload = {
        "url": "https://example.com",
        "event_type": "teleportation",
        "accuracy_meters": None,
        "is_https": True,
    }
    h._read_json_body = lambda: payload
    h._handle_geo_event_create()
    assert h._response_code == 400


def test_event_negative_accuracy():
    h = make_handler()
    ys._GEO_EVENTS.clear()
    payload = {
        "url": "https://example.com",
        "event_type": "position_acquired",
        "accuracy_meters": -1,
        "is_https": True,
    }
    h._read_json_body = lambda: payload
    h._handle_geo_event_create()
    assert h._response_code == 400


def test_event_list():
    _create_event()
    h = make_handler()
    h._handle_geo_events_list()
    assert h._response_code == 200
    assert "events" in h._response_body
    assert h._response_body["total"] >= 1


def test_event_delete():
    create_h = _create_event()
    event_id = create_h._response_body["event"]["event_id"]
    h = make_handler()
    h._handle_geo_event_delete(event_id)
    assert h._response_code == 200
    assert h._response_body["status"] == "deleted"


def test_event_not_found():
    h = make_handler()
    h._handle_geo_event_delete("geo_notexist")
    assert h._response_code == 404


def test_geo_stats():
    ys._GEO_EVENTS.clear()
    h1 = make_handler()
    h1._read_json_body = lambda: {
        "url": "https://a.com", "event_type": "permission_requested",
        "accuracy_meters": None, "is_https": True,
    }
    h1._handle_geo_event_create()
    h2 = make_handler()
    h2._read_json_body = lambda: {
        "url": "https://a.com", "event_type": "permission_granted",
        "accuracy_meters": 5, "is_https": True,
    }
    h2._handle_geo_event_create()
    h = make_handler()
    h._handle_geo_events_stats()
    assert h._response_code == 200
    body = h._response_body
    assert "grant_rate" in body
    float(body["grant_rate"])
    assert body["grant_rate"] == "1.00"
    assert "https_count" in body
    assert body["https_count"] == 2


def test_event_types_list():
    h = make_handler()
    h._handle_geo_event_types()
    assert h._response_code == 200
    types = h._response_body["event_types"]
    assert len(types) == 7
    assert "permission_requested" in types
    assert "permission_granted" in types


def test_no_port_9222_in_geo():
    src = "/home/phuc/projects/solace-browser/yinyang_server.py"
    with open(src) as f:
        content = f.read()
    assert "9222" not in content, "port 9222 found in yinyang_server.py"
