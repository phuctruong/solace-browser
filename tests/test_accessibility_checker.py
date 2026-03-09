"""Tests for Task 087 — Accessibility Checker."""
import sys
import json

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "b" * 64


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
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {
            "content-length": str(len(h._body)),
            "Authorization": f"Bearer {VALID_TOKEN}",
        }
    return h


def setup_function():
    with ys._ACCESS_LOCK:
        ys._ACCESSIBILITY_SCANS.clear()


def test_scan_record():
    h = make_handler({"url_hash": "url1", "wcag_level": "AA", "pass_count": 80, "fail_count": 20})
    h._handle_accessibility_scan()
    code, data = h._responses[0]
    assert code == 201
    assert data["scan_id"].startswith("acs_")


def test_scan_invalid_wcag():
    h = make_handler({"url_hash": "url1", "wcag_level": "B", "pass_count": 10, "fail_count": 5})
    h._handle_accessibility_scan()
    code, data = h._responses[0]
    assert code == 400
    assert "wcag_level" in data["error"]


def test_scan_missing_url_hash():
    h = make_handler({"wcag_level": "A", "pass_count": 5, "fail_count": 0})
    h._handle_accessibility_scan()
    code, data = h._responses[0]
    assert code == 400
    assert "url_hash" in data["error"]


def test_scan_score_calculation():
    h = make_handler({"url_hash": "url2", "wcag_level": "AA", "pass_count": 80, "fail_count": 20})
    h._handle_accessibility_scan()
    scan_id = h._responses[0][1]["scan_id"]
    h2 = FakeHandler()
    h2._handle_accessibility_get(scan_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["scan"]["score"] == "80.00"


def test_scan_score_both_zero():
    h = make_handler({"url_hash": "url3", "wcag_level": "A", "pass_count": 0, "fail_count": 0})
    h._handle_accessibility_scan()
    scan_id = h._responses[0][1]["scan_id"]
    h2 = FakeHandler()
    h2._handle_accessibility_get(scan_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["scan"]["score"] == "100.00"


def test_scan_list():
    h = make_handler({"url_hash": "url4", "wcag_level": "AAA", "pass_count": 50, "fail_count": 50})
    h._handle_accessibility_scan()
    h2 = FakeHandler()
    h2._handle_accessibility_list()
    code, data = h2._responses[0]
    assert code == 200
    assert isinstance(data["scans"], list)
    assert data["total"] >= 1


def test_scan_get_not_found():
    h = FakeHandler()
    h._handle_accessibility_get("acs_ghost")
    code, data = h._responses[0]
    assert code == 404


def test_scan_delete():
    h = make_handler({"url_hash": "url5", "wcag_level": "AA", "pass_count": 10, "fail_count": 0})
    h._handle_accessibility_scan()
    scan_id = h._responses[0][1]["scan_id"]
    h2 = FakeHandler()
    h2._handle_accessibility_delete(scan_id)
    code, data = h2._responses[0]
    assert code == 200
    assert data["scan_id"] == scan_id
    with ys._ACCESS_LOCK:
        ids = [s["scan_id"] for s in ys._ACCESSIBILITY_SCANS]
    assert scan_id not in ids


def test_scan_delete_not_found():
    h = FakeHandler()
    h._handle_accessibility_delete("acs_notexist")
    code, data = h._responses[0]
    assert code == 404


def test_wcag_levels():
    h = FakeHandler()
    h._handle_accessibility_wcag_levels()
    code, data = h._responses[0]
    assert code == 200
    assert "A" in data["wcag_levels"]
    assert "AA" in data["wcag_levels"]
    assert "AAA" in data["wcag_levels"]
    assert "perceivable" in data["categories"]
