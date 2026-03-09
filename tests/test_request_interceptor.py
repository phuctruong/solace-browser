"""Tests for Task 161 — Request Interceptor."""
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


def _create_log(extra=None):
    h = make_handler()
    ys._INTERCEPTOR_LOGS.clear()
    payload = {
        "url": "https://api.example.com/data",
        "origin": "https://example.com",
        "method": "GET",
        "status_code": 200,
        "response_ms": 45,
        "request_size_bytes": 128,
        "response_size_bytes": 1024,
    }
    if extra:
        payload.update(extra)
    h._read_json_body = lambda: payload
    h._handle_ric_create()
    return h


def test_log_create():
    h = _create_log()
    assert h._response_code == 201
    assert h._response_body["log"]["log_id"].startswith("ric_")


def test_log_url_hashed():
    h = _create_log()
    log = h._response_body["log"]
    assert "url_hash" in log
    assert len(log["url_hash"]) == 64
    assert "url" not in log
    assert "origin_hash" in log
    assert len(log["origin_hash"]) == 64


def test_log_invalid_method():
    h = make_handler()
    ys._INTERCEPTOR_LOGS.clear()
    payload = {
        "url": "https://example.com",
        "origin": "https://example.com",
        "method": "BREW",
        "status_code": 200,
        "response_ms": 10,
        "request_size_bytes": 0,
        "response_size_bytes": 0,
    }
    h._read_json_body = lambda: payload
    h._handle_ric_create()
    assert h._response_code == 400


def test_log_invalid_status():
    h = make_handler()
    ys._INTERCEPTOR_LOGS.clear()
    payload = {
        "url": "https://example.com",
        "origin": "https://example.com",
        "method": "GET",
        "status_code": 99,
        "response_ms": 10,
        "request_size_bytes": 0,
        "response_size_bytes": 0,
    }
    h._read_json_body = lambda: payload
    h._handle_ric_create()
    assert h._response_code == 400


def test_log_negative_response():
    h = make_handler()
    ys._INTERCEPTOR_LOGS.clear()
    payload = {
        "url": "https://example.com",
        "origin": "https://example.com",
        "method": "POST",
        "status_code": 201,
        "response_ms": -1,
        "request_size_bytes": 0,
        "response_size_bytes": 0,
    }
    h._read_json_body = lambda: payload
    h._handle_ric_create()
    assert h._response_code == 400


def test_log_status_classification():
    ys._INTERCEPTOR_LOGS.clear()
    _create_log({"status_code": 404, "method": "GET"})
    h = make_handler()
    h._handle_ric_stats()
    assert h._response_code == 200
    by_class = h._response_body["by_status_class"]
    assert by_class["4xx"] == 1
    assert by_class["2xx"] == 0


def test_log_list():
    _create_log()
    h = make_handler()
    h._handle_ric_list()
    assert h._response_code == 200
    assert "logs" in h._response_body
    assert h._response_body["total"] >= 1


def test_log_delete():
    create_h = _create_log()
    log_id = create_h._response_body["log"]["log_id"]
    h = make_handler()
    h._handle_ric_delete(log_id)
    assert h._response_code == 200
    assert h._response_body["status"] == "deleted"
    h2 = make_handler()
    h2._handle_ric_delete(log_id)
    assert h2._response_code == 404


def test_interceptor_stats():
    ys._INTERCEPTOR_LOGS.clear()
    _create_log({"status_code": 200, "response_ms": 100})
    _create_log({"status_code": 500, "method": "POST", "response_ms": 200})
    h = make_handler()
    h._handle_ric_stats()
    assert h._response_code == 200
    body = h._response_body
    assert "by_status_class" in body
    assert "2xx" in body["by_status_class"]
    assert "5xx" in body["by_status_class"]
    assert "avg_response_ms" in body
    float(body["avg_response_ms"])


def test_no_port_9222_in_interceptor():
    src = "/home/phuc/projects/solace-browser/yinyang_server.py"
    with open(src) as f:
        content = f.read()
    assert "9222" not in content, "port 9222 found in yinyang_server.py"
