# Diagram: 05-solace-runtime-architecture
"""tests/test_performance_profiler.py — Task 070: Performance Profiler (10 tests)"""
import sys
import json
import hashlib

sys.path.insert(0, "/home/phuc/projects/solace-browser")
import yinyang_server as ys

VALID_TOKEN = "a" * 64


class FakeHandler(ys.YinyangHandler):
    def __init__(self):
        self._responses = []
        self._body = b""
        self.headers = {"content-length": "0"}

    def _read_json_body(self):
        return json.loads(self._body) if self._body else {}

    def _send_json(self, data, code=200):
        self._responses.append((code, data))

    def _check_auth(self):
        return True

    def log_message(self, *a):
        pass


def make_handler(body=None):
    h = FakeHandler()
    if body:
        h._body = json.dumps(body).encode()
        h.headers = {"content-length": str(len(h._body))}
    return h


def setup_function():
    """Clear profiler state before each test."""
    with ys._PROFILER_LOCK:
        ys._PROFILER_SESSIONS.clear()
        ys._PROFILER_METRICS.clear()


def _make_page_hash():
    return hashlib.sha256(b"https://example.com/page").hexdigest()


def _create_session():
    page_hash = _make_page_hash()
    h = make_handler({"page_hash": page_hash})
    h._handle_profiler_session_create()
    code, data = h._responses[-1]
    assert code == 201
    return data["session"]["session_id"]


def test_profiler_sessions_empty():
    """GET /api/v1/profiler/sessions → empty initially."""
    h = make_handler()
    h._handle_profiler_sessions_list()
    code, data = h._responses[-1]
    assert code == 200
    assert data["sessions"] == []
    assert data["total"] == 0


def test_profiler_session_create():
    """POST /api/v1/profiler/sessions → session created."""
    page_hash = _make_page_hash()
    h = make_handler({"page_hash": page_hash})
    h._handle_profiler_session_create()
    code, data = h._responses[-1]
    assert code == 201
    assert data["status"] == "created"
    session = data["session"]
    assert session["session_id"].startswith("prf_")
    assert session["page_hash"] == page_hash
    assert session["metric_count"] == 0


def test_profiler_no_raw_url():
    """Session stores page_hash, NOT raw URL."""
    page_hash = _make_page_hash()
    h = make_handler({"page_hash": page_hash})
    h._handle_profiler_session_create()
    code, data = h._responses[-1]
    assert code == 201
    result_json = json.dumps(data)
    assert "https://example.com" not in result_json
    assert page_hash in result_json


def test_profiler_add_metric():
    """POST metrics → metric stored and session metric_count incremented."""
    session_id = _create_session()
    h = make_handler({
        "metric_type": "cpu",
        "value": 42.5,
        "unit": "percent",
        "timestamp_ms": 1000.0,
    })
    h._handle_profiler_metric_add(session_id)
    code, data = h._responses[-1]
    assert code == 201
    assert data["status"] == "added"
    metric = data["metric"]
    assert metric["metric_type"] == "cpu"
    assert metric["value"] == 42.5
    assert metric["metric_id"].startswith("mtr_")

    h2 = make_handler()
    h2._handle_profiler_sessions_list()
    _, d2 = h2._responses[-1]
    assert d2["sessions"][0]["metric_count"] == 1


def test_profiler_invalid_metric_type():
    """Invalid metric_type → 400."""
    session_id = _create_session()
    h = make_handler({
        "metric_type": "INVALID_TYPE",
        "value": 10.0,
        "unit": "ms",
        "timestamp_ms": 0.0,
    })
    h._handle_profiler_metric_add(session_id)
    code, data = h._responses[-1]
    assert code == 400
    assert "error" in data


def test_profiler_invalid_unit():
    """Invalid unit → 400."""
    session_id = _create_session()
    h = make_handler({
        "metric_type": "memory",
        "value": 100.0,
        "unit": "INVALID_UNIT",
        "timestamp_ms": 0.0,
    })
    h._handle_profiler_metric_add(session_id)
    code, data = h._responses[-1]
    assert code == 400
    assert "error" in data


def test_profiler_session_get():
    """GET /api/v1/profiler/sessions/{id} → session detail with metrics."""
    session_id = _create_session()
    hm = make_handler({
        "metric_type": "render",
        "value": 200.0,
        "unit": "ms",
        "timestamp_ms": 500.0,
    })
    hm._handle_profiler_metric_add(session_id)

    hg = make_handler()
    hg._handle_profiler_session_get(session_id)
    code, data = hg._responses[-1]
    assert code == 200
    assert data["session"]["session_id"] == session_id
    assert len(data["metrics"]) == 1
    assert data["metrics"][0]["metric_type"] == "render"


def test_profiler_session_delete():
    """DELETE /api/v1/profiler/sessions/{id} → session removed."""
    session_id = _create_session()

    hd = make_handler()
    hd._handle_profiler_session_delete(session_id)
    code, data = hd._responses[-1]
    assert code == 200
    assert data["status"] == "deleted"
    assert data["session_id"] == session_id

    h2 = make_handler()
    h2._handle_profiler_sessions_list()
    _, d2 = h2._responses[-1]
    assert d2["total"] == 0


def test_profiler_aggregates():
    """GET /api/v1/profiler/aggregates → correct aggregate structure."""
    session_id = _create_session()
    for v in [10.0, 20.0, 30.0]:
        hm = make_handler({"metric_type": "script", "value": v, "unit": "ms", "timestamp_ms": 0.0})
        hm._handle_profiler_metric_add(session_id)

    ha = make_handler()
    ha._handle_profiler_aggregates()
    code, data = ha._responses[-1]
    assert code == 200
    aggs = data["aggregates"]
    assert "script" in aggs
    s = aggs["script"]
    assert s["count"] == 3
    assert s["avg_value"] == 20.0
    assert s["max_value"] == 30.0
    assert s["min_value"] == 10.0


def test_no_port_9222_in_profiler():
    """Port 9222 must not appear in profiler handlers."""
    import inspect
    src = inspect.getsource(ys.YinyangHandler._handle_profiler_sessions_list)
    src += inspect.getsource(ys.YinyangHandler._handle_profiler_session_create)
    src += inspect.getsource(ys.YinyangHandler._handle_profiler_session_get)
    src += inspect.getsource(ys.YinyangHandler._handle_profiler_session_delete)
    src += inspect.getsource(ys.YinyangHandler._handle_profiler_metric_add)
    src += inspect.getsource(ys.YinyangHandler._handle_profiler_aggregates)
    assert "9222" not in src
    assert "Companion App" not in src
