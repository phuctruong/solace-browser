"""Tests for Task 159 — Accessibility Checker."""
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


def _create_check(extra=None):
    h = make_handler()
    ys._A11Y_CHECKS.clear()
    payload = {
        "url": "https://example.com/page",
        "wcag_level": "AA",
        "total_issues": 5,
        "critical_issues": 2,
        "score": 80,
        "top_issue_type": "low_contrast",
    }
    if extra:
        payload.update(extra)
    h._read_json_body = lambda: payload
    h._handle_a11y_check_create()
    return h


def test_check_create():
    h = _create_check()
    assert h._response_code == 201
    assert h._response_body["check"]["check_id"].startswith("a11_")


def test_check_url_hashed():
    h = _create_check()
    check = h._response_body["check"]
    assert "url_hash" in check
    assert len(check["url_hash"]) == 64
    assert "url" not in check


def test_check_invalid_wcag():
    h = make_handler()
    ys._A11Y_CHECKS.clear()
    payload = {
        "url": "https://example.com",
        "wcag_level": "B",
        "total_issues": 0,
        "critical_issues": 0,
        "score": 100,
    }
    h._read_json_body = lambda: payload
    h._handle_a11y_check_create()
    assert h._response_code == 400


def test_check_negative_issues():
    h = make_handler()
    ys._A11Y_CHECKS.clear()
    payload = {
        "url": "https://example.com",
        "wcag_level": "A",
        "total_issues": -1,
        "critical_issues": 0,
        "score": 50,
    }
    h._read_json_body = lambda: payload
    h._handle_a11y_check_create()
    assert h._response_code == 400


def test_check_critical_exceeds_total():
    h = make_handler()
    ys._A11Y_CHECKS.clear()
    payload = {
        "url": "https://example.com",
        "wcag_level": "AA",
        "total_issues": 3,
        "critical_issues": 5,
        "score": 50,
    }
    h._read_json_body = lambda: payload
    h._handle_a11y_check_create()
    assert h._response_code == 400


def test_check_score_out_of_range():
    h = make_handler()
    ys._A11Y_CHECKS.clear()
    payload = {
        "url": "https://example.com",
        "wcag_level": "AAA",
        "total_issues": 0,
        "critical_issues": 0,
        "score": 101,
    }
    h._read_json_body = lambda: payload
    h._handle_a11y_check_create()
    assert h._response_code == 400


def test_check_list():
    _create_check()
    h = make_handler()
    h._handle_a11y_checks_list()
    assert h._response_code == 200
    assert "checks" in h._response_body
    assert h._response_body["total"] >= 1


def test_check_delete():
    create_h = _create_check()
    check_id = create_h._response_body["check"]["check_id"]
    h = make_handler()
    h._handle_a11y_check_delete(check_id)
    assert h._response_code == 200
    assert h._response_body["status"] == "deleted"
    h2 = make_handler()
    h2._handle_a11y_check_delete(check_id)
    assert h2._response_code == 404


def test_a11y_stats():
    ys._A11Y_CHECKS.clear()
    h1 = make_handler()
    h1._read_json_body = lambda: {
        "url": "https://a.com", "wcag_level": "AA",
        "total_issues": 2, "critical_issues": 1, "score": 90,
    }
    h1._handle_a11y_check_create()
    h2 = make_handler()
    h2._read_json_body = lambda: {
        "url": "https://b.com", "wcag_level": "A",
        "total_issues": 0, "critical_issues": 0, "score": 100,
    }
    h2._handle_a11y_check_create()
    h = make_handler()
    h._handle_a11y_stats()
    assert h._response_code == 200
    body = h._response_body
    assert "avg_score" in body
    float(body["avg_score"])
    assert "avg_issues" in body
    assert "by_wcag_level" in body
    assert "perfect_score_count" in body
    assert body["perfect_score_count"] == 1


def test_no_port_9222_in_a11y():
    src = "/home/phuc/projects/solace-browser/yinyang_server.py"
    with open(src) as f:
        content = f.read()
    assert "9222" not in content, "port 9222 found in yinyang_server.py"
