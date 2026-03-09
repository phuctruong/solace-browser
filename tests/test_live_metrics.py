"""tests/test_live_metrics.py — Live Metrics Dashboard acceptance gate.
Task 031 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - cpu_pct clamped 0–100
  - uptime_s >= 0
  - SVG sparklines inline (no canvas/Chart.js/D3 in HTML/JS)
  - No port 9222, no eval(), no CDN
"""
import hashlib
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-live-metrics-031"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18901)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET", token=token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


# ---------------------------------------------------------------------------
# 1. GET /api/v1/live-metrics returns 200
# ---------------------------------------------------------------------------
def test_live_metrics_returns_200():
    status, data = get_json("/api/v1/live-metrics")
    assert status == 200


# ---------------------------------------------------------------------------
# 2. Response has required fields
# ---------------------------------------------------------------------------
def test_live_metrics_has_required_fields():
    _, data = get_json("/api/v1/live-metrics")
    for field in ("uptime_s", "cpu_pct", "mem_mb", "rps", "req_total", "error_total"):
        assert field in data, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# 3. uptime_s is non-negative integer
# ---------------------------------------------------------------------------
def test_live_metrics_uptime_non_negative():
    _, data = get_json("/api/v1/live-metrics")
    assert isinstance(data["uptime_s"], int)
    assert data["uptime_s"] >= 0


# ---------------------------------------------------------------------------
# 4. cpu_pct is clamped 0–100
# ---------------------------------------------------------------------------
def test_live_metrics_cpu_pct_clamped():
    _, data = get_json("/api/v1/live-metrics")
    assert 0.0 <= data["cpu_pct"] <= 100.0


# ---------------------------------------------------------------------------
# 5. Response includes sparkline arrays
# ---------------------------------------------------------------------------
def test_live_metrics_has_sparkline_arrays():
    _, data = get_json("/api/v1/live-metrics")
    assert "cpu_sparkline" in data
    assert "mem_sparkline" in data
    assert "rps_sparkline" in data
    assert isinstance(data["cpu_sparkline"], list)
    assert isinstance(data["mem_sparkline"], list)
    assert isinstance(data["rps_sparkline"], list)


# ---------------------------------------------------------------------------
# 6. GET /api/v1/live-metrics/history returns arrays
# ---------------------------------------------------------------------------
def test_live_metrics_history_returns_arrays():
    # Poll once to populate history
    get_json("/api/v1/live-metrics")
    status, data = get_json("/api/v1/live-metrics/history")
    assert status == 200
    assert "cpu_pct" in data
    assert "mem_mb" in data
    assert "rps" in data
    assert isinstance(data["cpu_pct"], list)


# ---------------------------------------------------------------------------
# 7. History samples count >= 1 after first poll
# ---------------------------------------------------------------------------
def test_live_metrics_history_samples_at_least_1():
    get_json("/api/v1/live-metrics")
    _, data = get_json("/api/v1/live-metrics/history")
    assert data.get("samples", 0) >= 1


# ---------------------------------------------------------------------------
# 8. web/live-metrics.html has no CDN references
# ---------------------------------------------------------------------------
def test_live_metrics_html_no_cdn():
    html_path = REPO_ROOT / "web" / "live-metrics.html"
    assert html_path.exists(), "web/live-metrics.html must exist"
    content = html_path.read_text()
    cdn_patterns = [
        r"cdn\.jsdelivr\.net", r"cdnjs\.cloudflare\.com", r"unpkg\.com",
        r"googleapis\.com", r"bootstrapcdn",
        r"https?://[^\s\"']+\.min\.js", r"https?://[^\s\"']+\.min\.css",
    ]
    for pattern in cdn_patterns:
        assert not re.search(pattern, content, re.IGNORECASE), (
            f"web/live-metrics.html contains CDN reference matching '{pattern}'"
        )


# ---------------------------------------------------------------------------
# 9. web/live-metrics.html uses inline SVG (no canvas, no Chart.js, no D3)
# ---------------------------------------------------------------------------
def test_live_metrics_html_uses_svg_not_canvas():
    html_path = REPO_ROOT / "web" / "live-metrics.html"
    content = html_path.read_text()
    assert "<svg" in content, "live-metrics.html must use inline SVG sparklines"
    assert "<canvas" not in content, "live-metrics.html must NOT use <canvas>"
    assert "chart.js" not in content.lower(), "live-metrics.html must NOT use Chart.js"
    assert "d3.js" not in content.lower() and "d3.min" not in content.lower(), (
        "live-metrics.html must NOT use D3"
    )


# ---------------------------------------------------------------------------
# 10. web/js/live-metrics.js has no eval() and no port 9222
# ---------------------------------------------------------------------------
def test_live_metrics_js_no_eval_no_banned_port():
    js_path = REPO_ROOT / "web" / "js" / "live-metrics.js"
    assert js_path.exists(), "web/js/live-metrics.js must exist"
    content = js_path.read_text()
    assert not re.search(r"\beval\s*\(", content), "live-metrics.js must not contain eval()"
    assert "9222" not in content, "live-metrics.js must not reference port 9222"
