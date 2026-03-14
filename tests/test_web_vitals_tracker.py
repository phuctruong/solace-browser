# Diagram: 05-solace-runtime-architecture
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
    with ys._WVM_LOCK:
        ys._WVM_MEASUREMENTS.clear()


def test_measurement_create():
    h = FakeHandler()
    h._handle_web_vitals_create({
        "metric_type": "LCP",
        "url": "https://ex.com",
        "value_ms": "2500",
        "rating": "good",
        "navigation_type": "navigate",
    })
    assert h._response_code == 201
    assert h._response_body["measurement_id"].startswith("wvm_")


def test_measurement_url_hashed():
    url = "https://example.com/perf"
    h = FakeHandler()
    h._handle_web_vitals_create({
        "metric_type": "CLS",
        "url": url,
        "value_ms": "0.1",
        "rating": "needs_improvement",
        "navigation_type": "reload",
    })
    assert h._response_body["url_hash"] == hashlib.sha256(url.encode("utf-8")).hexdigest()
    assert "url" not in h._response_body


def test_measurement_invalid_metric():
    h = FakeHandler()
    h._handle_web_vitals_create({
        "metric_type": "BAD",
        "url": "https://ex.com",
        "value_ms": "1",
        "rating": "good",
        "navigation_type": "navigate",
    })
    assert h._response_code == 400
    assert "metric_type" in h._response_body["error"]


def test_measurement_invalid_rating():
    h = FakeHandler()
    h._handle_web_vitals_create({
        "metric_type": "FID",
        "url": "https://ex.com",
        "value_ms": "1",
        "rating": "BAD",
        "navigation_type": "navigate",
    })
    assert h._response_code == 400
    assert "rating" in h._response_body["error"]


def test_measurement_negative_value():
    h = FakeHandler()
    h._handle_web_vitals_create({
        "metric_type": "TTFB",
        "url": "https://ex.com",
        "value_ms": "-1",
        "rating": "poor",
        "navigation_type": "navigate",
    })
    assert h._response_code == 400
    assert "value_ms" in h._response_body["error"]


def test_measurement_invalid_nav_type():
    h = FakeHandler()
    h._handle_web_vitals_create({
        "metric_type": "INP",
        "url": "https://ex.com",
        "value_ms": "1",
        "rating": "good",
        "navigation_type": "unknown",
    })
    assert h._response_code == 400
    assert "navigation_type" in h._response_body["error"]


def test_measurement_list_route():
    creator = FakeHandler(method="POST", path="/api/v1/web-vitals/measurements", body={
        "metric_type": "FCP",
        "url": "https://ex.com",
        "value_ms": "1200",
        "rating": "good",
        "navigation_type": "navigate",
    })
    creator.do_POST()
    reader = FakeHandler(method="GET", path="/api/v1/web-vitals/measurements")
    reader.do_GET()
    assert reader._response_code == 200
    assert reader._response_body["total"] == 1


def test_measurement_delete_route():
    creator = FakeHandler()
    creator._handle_web_vitals_create({
        "metric_type": "TBT",
        "url": "https://delete.example",
        "value_ms": "300",
        "rating": "poor",
        "navigation_type": "reload",
    })
    measurement_id = creator._response_body["measurement_id"]
    deleter = FakeHandler(method="DELETE", path=f"/api/v1/web-vitals/measurements/{measurement_id}")
    deleter.do_DELETE()
    assert deleter._response_code == 200
    assert deleter._response_body["measurement_id"] == measurement_id


def test_vitals_stats():
    first = FakeHandler()
    first._handle_web_vitals_create({
        "metric_type": "LCP",
        "url": "https://one.example",
        "value_ms": "2000",
        "rating": "good",
        "navigation_type": "navigate",
    })
    second = FakeHandler()
    second._handle_web_vitals_create({
        "metric_type": "LCP",
        "url": "https://two.example",
        "value_ms": "4000",
        "rating": "poor",
        "navigation_type": "reload",
    })
    stats = FakeHandler(method="GET", path="/api/v1/web-vitals/stats")
    stats.do_GET()
    assert stats._response_code == 200
    assert stats._response_body["avg_by_metric"]["LCP"] == "3000.00"


def test_banned_debug_port_absent_in_vitals_files():
    banned = "922" + "2"
    for rel_path in [
        "yinyang_server.py",
        "web/web-vitals-tracker.html",
        "web/css/web-vitals-tracker.css",
        "web/js/web-vitals-tracker.js",
    ]:
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert banned not in content
