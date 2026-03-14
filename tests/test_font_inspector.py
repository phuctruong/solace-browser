# Diagram: 05-solace-runtime-architecture
"""Tests for Task 158 — Font Inspector."""
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
    h = FakeHandler()
    return h


def _create_scan(extra=None):
    h = make_handler()
    ys._FONT_SCANS.clear()
    payload = {
        "url": "https://example.com",
        "font_name": "Arial",
        "category": "sans_serif",
        "font_count": 3,
        "is_variable_font": True,
        "has_web_font": False,
        "load_time_ms": 120,
    }
    if extra:
        payload.update(extra)

    class FakeBody:
        pass

    h._read_json_body = lambda: payload
    h._handle_fns_create()
    return h


def test_scan_create():
    h = _create_scan()
    assert h._response_code == 201
    assert h._response_body["scan"]["scan_id"].startswith("fns_")


def test_scan_url_hashed():
    h = _create_scan()
    scan = h._response_body["scan"]
    assert "url_hash" in scan
    assert len(scan["url_hash"]) == 64  # SHA-256 hex
    assert "url" not in scan


def test_scan_font_name_hashed():
    h = _create_scan()
    scan = h._response_body["scan"]
    assert "font_name_hash" in scan
    assert len(scan["font_name_hash"]) == 64
    assert "font_name" not in scan


def test_scan_invalid_category():
    h = make_handler()
    ys._FONT_SCANS.clear()
    payload = {
        "url": "https://example.com",
        "font_name": "Arial",
        "category": "neon_light",  # invalid
        "font_count": 2,
        "load_time_ms": 10,
    }
    h._read_json_body = lambda: payload
    h._handle_fns_create()
    assert h._response_code == 400
    assert "error" in h._response_body


def test_scan_zero_fonts():
    h = make_handler()
    ys._FONT_SCANS.clear()
    payload = {
        "url": "https://example.com",
        "font_name": "Arial",
        "category": "serif",
        "font_count": 0,  # invalid
        "load_time_ms": 10,
    }
    h._read_json_body = lambda: payload
    h._handle_fns_create()
    assert h._response_code == 400


def test_scan_negative_load_time():
    h = make_handler()
    ys._FONT_SCANS.clear()
    payload = {
        "url": "https://example.com",
        "font_name": "Arial",
        "category": "serif",
        "font_count": 2,
        "load_time_ms": -1,  # invalid
    }
    h._read_json_body = lambda: payload
    h._handle_fns_create()
    assert h._response_code == 400


def test_scan_list():
    _create_scan()
    h = make_handler()
    h._handle_fns_list()
    assert h._response_code == 200
    assert "scans" in h._response_body
    assert h._response_body["total"] >= 1


def test_scan_delete():
    create_h = _create_scan()
    scan_id = create_h._response_body["scan"]["scan_id"]
    h = make_handler()
    h._handle_fns_delete(scan_id)
    assert h._response_code == 200
    assert h._response_body["status"] == "deleted"
    # Confirm gone
    h2 = make_handler()
    h2._handle_fns_delete(scan_id)
    assert h2._response_code == 404


def test_font_stats():
    _create_scan()
    h = make_handler()
    h._handle_fns_stats()
    assert h._response_code == 200
    body = h._response_body
    assert "avg_font_count" in body
    # Decimal string — should be parseable as float
    float(body["avg_font_count"])
    assert "avg_load_time_ms" in body
    float(body["avg_load_time_ms"])
    assert "by_category" in body
    assert "variable_font_count" in body


def test_font_categories():
    h = make_handler()
    h._handle_fns_categories()
    assert h._response_code == 200
    cats = h._response_body["font_categories"]
    assert "serif" in cats
    assert "sans_serif" in cats
    assert len(cats) == 10


def test_no_port_9222_in_fonts():
    src = "/home/phuc/projects/solace-browser/yinyang_server.py"
    with open(src) as f:
        content = f.read()
    assert "9222" not in content, "port 9222 found in yinyang_server.py"
