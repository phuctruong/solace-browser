"""Tests for Page Performance Budget (Task 109). 10 tests."""
import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys
import json
import hashlib
from io import BytesIO


VALID_TOKEN = hashlib.sha256(b"test-token").hexdigest()


class FakeHandler(ys.YinyangHandler):
    def __init__(self, method, path, body=None, auth=True):
        self.command = method
        self.path = path
        self._body = json.dumps(body).encode() if body else b""
        self._auth = auth
        self._status = None
        self._response = None
        self.headers = {
            "Content-Length": str(len(self._body)),
            "Authorization": f"Bearer {VALID_TOKEN}" if auth else "",
        }
        self.server = type("S", (), {
            "session_token_sha256": VALID_TOKEN,
            "repo_root": str(REPO_ROOT),
        })()
        self.rfile = BytesIO(self._body)
        self.wfile = BytesIO()

    def send_response(self, code):
        self._status = code

    def send_header(self, *a):
        pass

    def end_headers(self):
        pass

    def _send_json(self, data, code=200):
        self._status = code
        self._response = data

    def _check_auth(self):
        if not self._auth:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}


def _reset():
    ys._PERF_BUDGETS.clear()
    ys._PERF_MEASUREMENTS.clear()


def test_budget_create():
    """POST creates budget with pbg_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/perf-budget/budgets", {
        "metric": "lcp",
        "budget_value": "2500",
        "unit": "ms",
    })
    h._handle_perf_budget_create()
    assert h._status == 201
    budget = h._response["budget"]
    assert budget["budget_id"].startswith("pbg_")
    assert budget["metric"] == "lcp"
    assert budget["unit"] == "ms"


def test_budget_invalid_metric():
    """POST with unknown metric returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/perf-budget/budgets", {
        "metric": "UNKNOWN_METRIC",
        "budget_value": "100",
        "unit": "ms",
    })
    h._handle_perf_budget_create()
    assert h._status == 400


def test_budget_invalid_value():
    """POST with non-numeric budget_value returns 400."""
    _reset()
    h = FakeHandler("POST", "/api/v1/perf-budget/budgets", {
        "metric": "fcp",
        "budget_value": "abc",
        "unit": "ms",
    })
    h._handle_perf_budget_create()
    assert h._status == 400


def test_budget_list():
    """GET returns list of budgets."""
    _reset()
    h = FakeHandler("POST", "/api/v1/perf-budget/budgets", {
        "metric": "cls",
        "budget_value": "0.1",
        "unit": "score",
    })
    h._handle_perf_budget_create()
    h2 = FakeHandler("GET", "/api/v1/perf-budget/budgets")
    h2._handle_perf_budget_list()
    assert h2._status == 200
    assert "budgets" in h2._response
    assert h2._response["total"] == 1


def test_budget_delete():
    """DELETE removes budget."""
    _reset()
    h = FakeHandler("POST", "/api/v1/perf-budget/budgets", {
        "metric": "ttfb",
        "budget_value": "800",
        "unit": "ms",
    })
    h._handle_perf_budget_create()
    budget_id = h._response["budget"]["budget_id"]

    dh = FakeHandler("DELETE", f"/api/v1/perf-budget/budgets/{budget_id}")
    dh._handle_perf_budget_delete(budget_id)
    assert dh._status == 200
    assert dh._response["status"] == "deleted"

    lh = FakeHandler("GET", "/api/v1/perf-budget/budgets")
    lh._handle_perf_budget_list()
    assert lh._response["total"] == 0


def test_measurement_create():
    """POST creates measurement with pms_ prefix."""
    _reset()
    h = FakeHandler("POST", "/api/v1/perf-budget/measurements", {
        "metric": "fid",
        "actual_value": "50",
        "budget_value": "100",
        "unit": "ms",
        "page_hash": "abc123",
    })
    h._handle_perf_measurement_create()
    assert h._status == 201
    m = h._response["measurement"]
    assert m["measurement_id"].startswith("pms_")
    assert m["metric"] == "fid"


def test_measurement_exceeded():
    """actual_value > budget_value sets exceeded=True."""
    _reset()
    h = FakeHandler("POST", "/api/v1/perf-budget/measurements", {
        "metric": "lcp",
        "actual_value": "5000",
        "budget_value": "2500",
        "unit": "ms",
        "page_hash": "abc",
    })
    h._handle_perf_measurement_create()
    assert h._status == 201
    assert h._response["measurement"]["exceeded"] is True


def test_measurement_not_exceeded():
    """actual_value <= budget_value sets exceeded=False."""
    _reset()
    h = FakeHandler("POST", "/api/v1/perf-budget/measurements", {
        "metric": "lcp",
        "actual_value": "1000",
        "budget_value": "2500",
        "unit": "ms",
        "page_hash": "abc",
    })
    h._handle_perf_measurement_create()
    assert h._status == 201
    assert h._response["measurement"]["exceeded"] is False


def test_metrics_list():
    """GET /metrics returns 10 metric types."""
    h = FakeHandler("GET", "/api/v1/perf-budget/metrics")
    h._handle_perf_metrics_list()
    assert h._status == 200
    assert len(h._response["metrics"]) == 10
    assert "lcp" in h._response["metrics"]
    assert "inp" in h._response["metrics"]


def test_no_legacy_debug_port_in_perf():
    """Grep check: legacy debug port must not appear in this file."""
    banned_port = "92" + "22"  # split to avoid self-matching
    source = pathlib.Path(__file__).read_text()
    assert banned_port not in source
