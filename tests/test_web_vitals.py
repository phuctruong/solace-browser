# Diagram: 05-solace-runtime-architecture
"""
Tests for Task 061 — Web Vitals Monitor
Browser: yinyang_server.py routes /api/v1/vitals/*
"""
import json
import sys

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


def test_vitals_summary_empty():
    import yinyang_server as ys
    ys._VITALS_DATA.clear()
    h = _make_handler()
    h._handle_vitals_summary()
    status, data = h._responses[0]
    assert status == 200
    assert data["total_measurements"] == 0
    for m in ys.VITAL_METRICS:
        assert m in data["summary"]


def test_vitals_record_ok():
    import yinyang_server as ys
    ys._VITALS_DATA.clear()
    page_hash = "a" * 64
    h = _make_handler({"page_hash": page_hash, "metric": "LCP", "value": 1500.0})
    h._handle_vitals_record()
    status, data = h._responses[0]
    assert status == 201
    assert data["measurement"]["measurement_id"].startswith("vit_")
    assert data["measurement"]["rating"] == "good"


def test_vitals_record_needs_improvement():
    import yinyang_server as ys
    ys._VITALS_DATA.clear()
    page_hash = "b" * 64
    h = _make_handler({"page_hash": page_hash, "metric": "LCP", "value": 3000.0})
    h._handle_vitals_record()
    status, data = h._responses[0]
    assert status == 201
    assert data["measurement"]["rating"] == "needs-improvement"


def test_vitals_record_poor():
    import yinyang_server as ys
    ys._VITALS_DATA.clear()
    page_hash = "c" * 64
    h = _make_handler({"page_hash": page_hash, "metric": "LCP", "value": 5000.0})
    h._handle_vitals_record()
    status, data = h._responses[0]
    assert status == 201
    assert data["measurement"]["rating"] == "poor"


def test_vitals_record_invalid_metric():
    import yinyang_server as ys
    ys._VITALS_DATA.clear()
    h = _make_handler({"page_hash": "d" * 64, "metric": "BADMETRIC", "value": 100.0})
    h._handle_vitals_record()
    status, data = h._responses[0]
    assert status == 400
    assert "metric" in data["error"]


def test_vitals_record_requires_auth():
    import yinyang_server as ys
    ys._VITALS_DATA.clear()
    h = _make_handler({"page_hash": "e" * 64, "metric": "LCP", "value": 100.0}, auth=False)
    h._handle_vitals_record()
    status, _ = h._responses[0]
    assert status == 401


def test_vitals_clear_ok():
    import yinyang_server as ys
    ys._VITALS_DATA.clear()
    h = _make_handler({"page_hash": "f" * 64, "metric": "FCP", "value": 900.0})
    h._handle_vitals_record()

    h2 = _make_handler()
    h2._handle_vitals_clear()
    status, data = h2._responses[0]
    assert status == 200
    assert data["status"] == "cleared"
    assert data["count"] >= 1
    assert len(ys._VITALS_DATA) == 0


def test_vitals_by_page():
    import yinyang_server as ys
    ys._VITALS_DATA.clear()
    page_hash = "0" * 64
    h = _make_handler({"page_hash": page_hash, "metric": "TTFB", "value": 400.0})
    h._handle_vitals_record()

    h2 = _make_handler()
    h2._handle_vitals_by_page()
    status, data = h2._responses[0]
    assert status == 200
    assert data["total_pages"] >= 1
    assert any(p["page_hash"] == page_hash for p in data["pages"])


def test_vitals_thresholds():
    import yinyang_server as ys
    h = _make_handler()
    h._handle_vitals_thresholds()
    status, data = h._responses[0]
    assert status == 200
    assert "LCP" in data["thresholds"]
    assert "good" in data["thresholds"]["LCP"]
    assert "poor" in data["thresholds"]["LCP"]


def test_vitals_page_hash_must_be_64():
    import yinyang_server as ys
    ys._VITALS_DATA.clear()
    h = _make_handler({"page_hash": "short", "metric": "LCP", "value": 100.0})
    h._handle_vitals_record()
    status, data = h._responses[0]
    assert status == 400
    assert "page_hash" in data["error"]
