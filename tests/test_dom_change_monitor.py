"""Tests for Task 160 — DOM Change Monitor."""
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
    ys._DOM_MONITOR_EVENTS.clear()
    payload = {
        "url": "https://example.com",
        "selector": "#main .content",
        "mutation_type": "childList",
        "change_count": 3,
        "nodes_added": 2,
        "nodes_removed": 1,
    }
    if extra:
        payload.update(extra)
    h._read_json_body = lambda: payload
    h._handle_dom_monitor_event_create()
    return h


def test_event_create():
    h = _create_event()
    assert h._response_code == 201
    assert h._response_body["event"]["event_id"].startswith("dom_")


def test_event_url_hashed():
    h = _create_event()
    event = h._response_body["event"]
    assert "url_hash" in event
    assert len(event["url_hash"]) == 64
    assert "url" not in event


def test_event_selector_hashed():
    h = _create_event()
    event = h._response_body["event"]
    assert "selector_hash" in event
    assert len(event["selector_hash"]) == 64
    assert "selector" not in event


def test_event_invalid_mutation():
    h = make_handler()
    ys._DOM_MONITOR_EVENTS.clear()
    payload = {
        "url": "https://example.com",
        "selector": ".x",
        "mutation_type": "unknown_mutation",
        "change_count": 1,
        "nodes_added": 0,
        "nodes_removed": 0,
    }
    h._read_json_body = lambda: payload
    h._handle_dom_monitor_event_create()
    assert h._response_code == 400


def test_event_zero_changes():
    h = make_handler()
    ys._DOM_MONITOR_EVENTS.clear()
    payload = {
        "url": "https://example.com",
        "selector": ".x",
        "mutation_type": "attributes",
        "change_count": 0,
        "nodes_added": 0,
        "nodes_removed": 0,
    }
    h._read_json_body = lambda: payload
    h._handle_dom_monitor_event_create()
    assert h._response_code == 400


def test_event_negative_nodes():
    h = make_handler()
    ys._DOM_MONITOR_EVENTS.clear()
    payload = {
        "url": "https://example.com",
        "selector": ".x",
        "mutation_type": "childList",
        "change_count": 1,
        "nodes_added": -1,
        "nodes_removed": 0,
    }
    h._read_json_body = lambda: payload
    h._handle_dom_monitor_event_create()
    assert h._response_code == 400


def test_event_list():
    _create_event()
    h = make_handler()
    h._handle_dom_monitor_events_list()
    assert h._response_code == 200
    assert "events" in h._response_body
    assert h._response_body["total"] >= 1


def test_event_delete():
    create_h = _create_event()
    event_id = create_h._response_body["event"]["event_id"]
    h = make_handler()
    h._handle_dom_monitor_event_delete(event_id)
    assert h._response_code == 200
    assert h._response_body["status"] == "deleted"
    h2 = make_handler()
    h2._handle_dom_monitor_event_delete(event_id)
    assert h2._response_code == 404


def test_dom_stats():
    ys._DOM_MONITOR_EVENTS.clear()
    _create_event({"change_count": 4, "nodes_added": 3, "nodes_removed": 1})
    _create_event({"mutation_type": "attributes", "change_count": 2, "nodes_added": 0, "nodes_removed": 0})
    h = make_handler()
    h._handle_dom_monitor_stats()
    assert h._response_code == 200
    body = h._response_body
    assert "avg_changes" in body
    float(body["avg_changes"])
    assert "by_mutation_type" in body
    assert "total_nodes_added" in body
    assert "total_nodes_removed" in body


def test_no_port_9222_in_dom_monitor():
    src = "/home/phuc/projects/solace-browser/yinyang_server.py"
    with open(src) as f:
        content = f.read()
    assert "9222" not in content, "port 9222 found in yinyang_server.py"
