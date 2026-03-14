# Diagram: 05-solace-runtime-architecture
"""Tests for Task 165v2 — Web Vitals Tracker /records endpoints."""
import hashlib
import json
import pathlib
import sys
from io import BytesIO

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

VALID_TOKEN = "c" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method="GET", path="/", body=None, auth=True):
        self.command = method
        self.path = path
        raw_body = json.dumps(body).encode("utf-8") if body is not None else b""
        self.headers = {
            "Content-Length": str(len(raw_body)),
            "Authorization": f"Bearer {VALID_TOKEN}" if auth else "",
        }
        self.rfile = BytesIO(raw_body)
        self.wfile = BytesIO()
        self.server = type("Server", (), {"session_token_sha256": VALID_TOKEN})()
        self._response_code = None
        self._response_body = None

    def send_response(self, code):
        self._response_code = code

    def send_header(self, *_args):
        pass

    def end_headers(self):
        pass

    def _send_json(self, data, status=200):
        self._response_code = status
        self._response_body = data

    def log_message(self, *_args):
        pass


def setup_function():
    with ys._WEB_VITALS_LOCK:
        ys._WEB_VITALS_RECORDS.clear()


def test_record_create():
    h = FakeHandler()
    h._handle_wvt2_create({
        "metric_name": "lcp",
        "url": "https://ex.com",
        "value": 1200,
        "rating": "good",
    })
    assert h._response_code == 201
    assert h._response_body["record_id"].startswith("wvt_")


def test_record_url_hashed():
    url = "https://example.com/page"
    h = FakeHandler()
    h._handle_wvt2_create({
        "metric_name": "cls",
        "url": url,
        "value": 0.05,
        "rating": "good",
    })
    assert h._response_body["url_hash"] == hashlib.sha256(url.encode("utf-8")).hexdigest()
    assert "url" not in h._response_body


def test_record_invalid_metric():
    h = FakeHandler()
    h._handle_wvt2_create({
        "metric_name": "speed",
        "url": "https://ex.com",
        "value": 100,
        "rating": "good",
    })
    assert h._response_code == 400
    assert "metric_name" in h._response_body["error"]


def test_record_invalid_rating():
    h = FakeHandler()
    h._handle_wvt2_create({
        "metric_name": "fid",
        "url": "https://ex.com",
        "value": 50,
        "rating": "excellent",
    })
    assert h._response_code == 400
    assert "rating" in h._response_body["error"]


def test_record_negative_value():
    h = FakeHandler()
    h._handle_wvt2_create({
        "metric_name": "ttfb",
        "url": "https://ex.com",
        "value": -1,
        "rating": "poor",
    })
    assert h._response_code == 400
    assert "value" in h._response_body["error"]


def test_record_value_decimal_str():
    h = FakeHandler()
    h._handle_wvt2_create({
        "metric_name": "fcp",
        "url": "https://ex.com",
        "value": 750,
        "rating": "good",
    })
    assert h._response_code == 201
    assert h._response_body["value"] == "750.00"


def test_record_list():
    creator = FakeHandler(method="POST", path="/api/v1/web-vitals/records", body={
        "metric_name": "tti",
        "url": "https://example.com",
        "value": 3000,
        "rating": "needs_improvement",
    })
    creator.do_POST()
    reader = FakeHandler(method="GET", path="/api/v1/web-vitals/records")
    reader.do_GET()
    assert reader._response_code == 200
    assert reader._response_body["total"] == 1
    assert reader._response_body["records"][0]["record_id"].startswith("wvt_")


def test_record_delete():
    creator = FakeHandler()
    creator._handle_wvt2_create({
        "metric_name": "tbt",
        "url": "https://delete.example",
        "value": 200,
        "rating": "needs_improvement",
    })
    record_id = creator._response_body["record_id"]
    deleter = FakeHandler(method="DELETE", path=f"/api/v1/web-vitals/records/{record_id}")
    deleter.do_DELETE()
    assert deleter._response_code == 200
    assert deleter._response_body["record_id"] == record_id


def test_vitals_stats():
    first = FakeHandler()
    first._handle_wvt2_create({
        "metric_name": "inp",
        "url": "https://one.example",
        "value": 100,
        "rating": "good",
    })
    second = FakeHandler()
    second._handle_wvt2_create({
        "metric_name": "lcp",
        "url": "https://two.example",
        "value": 5000,
        "rating": "poor",
    })
    stats = FakeHandler()
    stats._handle_wvt2_stats()
    assert stats._response_code == 200
    body = stats._response_body
    assert body["good_count"] == 1
    assert body["poor_count"] == 1
    assert "good_rate" in body
    assert "avg_value" in body


def test_no_port_9222_in_vitals():
    banned = "922" + "2"
    content = (REPO_ROOT / "yinyang_server.py").read_text(encoding="utf-8")
    assert banned not in content
