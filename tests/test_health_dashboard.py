"""tests/test_health_dashboard.py — System Health Dashboard acceptance gate.
Task 023 | Rung 641 | 10 tests minimum
"""
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VALID_TOKEN = "c" * 64


def _req(base, path, method="GET", payload=None, token=VALID_TOKEN):
    url = base + path
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


@pytest.fixture(scope="module")
def health_server(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("health")
    import yinyang_server as ys
    httpd = ys.build_server(0, str(tmp_path), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://localhost:{httpd.server_port}"
    for _ in range(30):
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)
    yield base
    httpd.shutdown()


# ---------------------------------------------------------------------------
# 1. GET /api/v1/health/full returns 200
# ---------------------------------------------------------------------------
def test_health_full_returns_200(health_server):
    """Public endpoint — no auth required."""
    req = urllib.request.Request(health_server + "/api/v1/health/full", method="GET")
    with urllib.request.urlopen(req, timeout=5) as r:
        assert r.status == 200


# ---------------------------------------------------------------------------
# 2. Response has "status" field ("healthy"/"degraded"/"down")
# ---------------------------------------------------------------------------
def test_health_full_has_status(health_server):
    status, data = _req(health_server, "/api/v1/health/full", token=None)
    assert status == 200
    assert "status" in data
    assert data["status"] in ("healthy", "degraded", "down")


# ---------------------------------------------------------------------------
# 3. GET /api/v1/health/metrics → uptime_s is integer >= 0
# ---------------------------------------------------------------------------
def test_health_metrics_has_uptime(health_server):
    status, data = _req(health_server, "/api/v1/health/metrics")
    assert status == 200
    assert "uptime_s" in data
    assert isinstance(data["uptime_s"], int)
    assert data["uptime_s"] >= 0


# ---------------------------------------------------------------------------
# 4. GET /api/v1/health/checks → list of 5 named checks
# ---------------------------------------------------------------------------
def test_health_checks_list(health_server):
    status, data = _req(health_server, "/api/v1/health/checks")
    assert status == 200
    assert "checks" in data
    checks = data["checks"]
    assert isinstance(checks, list)
    assert len(checks) == 5
    check_ids = {c["check_id"] for c in checks}
    assert check_ids == {"server", "oauth3", "recipes", "twin", "budget"}


# ---------------------------------------------------------------------------
# 5. POST /api/v1/health/checks/server/run → returns check result
# ---------------------------------------------------------------------------
def test_health_check_run(health_server):
    status, data = _req(
        health_server, "/api/v1/health/checks/server/run", method="POST"
    )
    assert status == 200
    assert "check_id" in data
    assert data["check_id"] == "server"
    assert "passed" in data
    assert isinstance(data["passed"], bool)


# ---------------------------------------------------------------------------
# 6. After /full call, /history has >= 1 entry
# ---------------------------------------------------------------------------
def test_health_history_appends(health_server):
    import yinyang_server as ys
    # Clear history first for isolation
    with ys._HEALTH_LOCK:
        ys._HEALTH_HISTORY.clear()
    # Call /full to populate history
    _req(health_server, "/api/v1/health/full", token=None)
    # Small sleep to ensure thread sees state
    time.sleep(0.05)
    status, data = _req(health_server, "/api/v1/health/history")
    assert status == 200
    assert "history" in data
    assert len(data["history"]) >= 1


# ---------------------------------------------------------------------------
# 7. web/health-dashboard.html has no CDN refs
# ---------------------------------------------------------------------------
def test_health_html_no_cdn():
    html_path = PROJECT_ROOT / "web" / "health-dashboard.html"
    assert html_path.exists(), "health-dashboard.html must exist"
    content = html_path.read_text()
    cdn_patterns = [
        "cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com",
        "googleapis.com", "bootstrapcdn.com", "ajax.googleapis",
    ]
    for pattern in cdn_patterns:
        assert pattern not in content, f"CDN reference found: {pattern}"


# ---------------------------------------------------------------------------
# 8. web/js/health-dashboard.js has no eval()
# ---------------------------------------------------------------------------
def test_health_js_no_eval():
    js_path = PROJECT_ROOT / "web" / "js" / "health-dashboard.js"
    assert js_path.exists(), "health-dashboard.js must exist"
    content = js_path.read_text()
    assert "eval(" not in content, "eval() found in health-dashboard.js — BANNED"
    assert "eval`" not in content, "eval` found in health-dashboard.js — BANNED"


# ---------------------------------------------------------------------------
# 9. No port 9222 in health dashboard files
# ---------------------------------------------------------------------------
def test_no_port_9222_in_health():
    for rel in [
        "web/health-dashboard.html",
        "web/js/health-dashboard.js",
        "web/css/health-dashboard.css",
    ]:
        path = PROJECT_ROOT / rel
        assert path.exists(), f"{rel} must exist"
        content = path.read_text()
        assert "9222" not in content, f"Banned port 9222 found in {rel}"


# ---------------------------------------------------------------------------
# 10. cpu_pct is a number between 0 and 100
# ---------------------------------------------------------------------------
def test_health_metrics_cpu_pct_valid(health_server):
    status, data = _req(health_server, "/api/v1/health/metrics")
    assert status == 200
    assert "cpu_pct" in data
    cpu = data["cpu_pct"]
    assert isinstance(cpu, (int, float)), f"cpu_pct must be numeric, got {type(cpu)}"
    assert 0 <= cpu <= 100, f"cpu_pct out of range: {cpu}"


# ---------------------------------------------------------------------------
# 11. /full is public (no auth token)
# ---------------------------------------------------------------------------
def test_health_full_no_auth_required(health_server):
    """GET /api/v1/health/full must work without Authorization header."""
    req = urllib.request.Request(health_server + "/api/v1/health/full", method="GET")
    with urllib.request.urlopen(req, timeout=5) as r:
        assert r.status == 200
        data = json.loads(r.read())
        assert "status" in data


# ---------------------------------------------------------------------------
# 12. /metrics requires auth
# ---------------------------------------------------------------------------
def test_health_metrics_requires_auth(health_server):
    status, data = _req(health_server, "/api/v1/health/metrics", token=None)
    assert status == 401


# ---------------------------------------------------------------------------
# 13. /checks requires auth
# ---------------------------------------------------------------------------
def test_health_checks_requires_auth(health_server):
    status, data = _req(health_server, "/api/v1/health/checks", token=None)
    assert status == 401


# ---------------------------------------------------------------------------
# 14. POST /checks/{check_id}/run with unknown check_id → 404
# ---------------------------------------------------------------------------
def test_health_check_run_unknown(health_server):
    status, data = _req(
        health_server, "/api/v1/health/checks/does-not-exist/run", method="POST"
    )
    assert status == 404
    assert "error" in data
