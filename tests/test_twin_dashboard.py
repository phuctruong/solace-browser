"""tests/test_twin_dashboard.py — Twin Browser Dashboard acceptance gate.
Task 022 | Rung 641 | 10 tests minimum
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

VALID_TOKEN = "b" * 64


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
def twin_server(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("twin")
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
# 1. GET /api/v1/twin/status returns 200
# ---------------------------------------------------------------------------
def test_twin_status_endpoint_exists(twin_server):
    status, data = _req(twin_server, "/api/v1/twin/status")
    assert status == 200


# ---------------------------------------------------------------------------
# 2. Response has "status" field
# ---------------------------------------------------------------------------
def test_twin_status_has_status_field(twin_server):
    status, data = _req(twin_server, "/api/v1/twin/status")
    assert status == 200
    assert "status" in data
    assert data["status"] in ("idle", "running", "active", "error")


# ---------------------------------------------------------------------------
# 3. GET /api/v1/twin/queue returns empty list initially
# ---------------------------------------------------------------------------
def test_twin_queue_empty_initially(twin_server):
    import yinyang_server as ys
    # Reset queue state to empty for isolation
    with ys._TWIN_LOCK:
        ys._TWIN_QUEUE.clear()
        ys._TWIN_STATUS["status"] = "idle"
    status, data = _req(twin_server, "/api/v1/twin/queue")
    assert status == 200
    assert isinstance(data.get("queue"), list)
    assert data["queue"] == []


# ---------------------------------------------------------------------------
# 4. POST /api/v1/twin/queue adds task, visible in GET
# ---------------------------------------------------------------------------
def test_twin_add_to_queue(twin_server):
    import yinyang_server as ys
    with ys._TWIN_LOCK:
        ys._TWIN_QUEUE.clear()
    status, data = _req(twin_server, "/api/v1/twin/queue", method="POST",
                        payload={"action": "navigate", "payload": {"url": "https://example.com"}})
    assert status == 201
    assert "task_id" in data

    status2, data2 = _req(twin_server, "/api/v1/twin/queue")
    assert status2 == 200
    task_ids = [t["task_id"] for t in data2.get("queue", [])]
    assert data["task_id"] in task_ids


# ---------------------------------------------------------------------------
# 5. DELETE removes task from queue
# ---------------------------------------------------------------------------
def test_twin_cancel_from_queue(twin_server):
    import yinyang_server as ys
    with ys._TWIN_LOCK:
        ys._TWIN_QUEUE.clear()

    _, add_data = _req(twin_server, "/api/v1/twin/queue", method="POST",
                       payload={"action": "screenshot"})
    task_id = add_data["task_id"]

    status, data = _req(twin_server, f"/api/v1/twin/queue/{task_id}", method="DELETE")
    assert status == 200
    assert data.get("cancelled") is True

    _, queue_data = _req(twin_server, "/api/v1/twin/queue")
    task_ids = [t["task_id"] for t in queue_data.get("queue", [])]
    assert task_id not in task_ids


# ---------------------------------------------------------------------------
# 6. GET /api/v1/twin/history returns empty list initially
# ---------------------------------------------------------------------------
def test_twin_history_empty_initially(twin_server):
    import yinyang_server as ys
    with ys._TWIN_LOCK:
        ys._TWIN_HISTORY.clear()
    status, data = _req(twin_server, "/api/v1/twin/history")
    assert status == 200
    assert isinstance(data.get("history"), list)
    assert data["history"] == []


# ---------------------------------------------------------------------------
# 7. History entry cost_usd is string not float
# ---------------------------------------------------------------------------
def test_twin_cost_is_string(twin_server):
    import yinyang_server as ys
    import uuid
    from decimal import Decimal
    # Inject a synthetic history entry to validate cost_usd type
    entry = {
        "task_id": str(uuid.uuid4()),
        "action": "navigate",
        "status": "ok",
        "duration_ms": 1234,
        "cost_usd": str(Decimal("0.001")),
    }
    with ys._TWIN_LOCK:
        ys._TWIN_HISTORY.clear()
        ys._TWIN_HISTORY.append(entry)
    status, data = _req(twin_server, "/api/v1/twin/history")
    assert status == 200
    entries = data.get("history", [])
    assert len(entries) == 1
    cost = entries[0]["cost_usd"]
    assert isinstance(cost, str), f"cost_usd must be string, got {type(cost)}: {cost}"
    # Must not be a float literal — API must not convert it
    assert "." in cost or cost.isdigit()


# ---------------------------------------------------------------------------
# 8. web/twin-dashboard.html has no CDN links
# ---------------------------------------------------------------------------
def test_twin_dashboard_html_no_cdn():
    html_path = PROJECT_ROOT / "web" / "twin-dashboard.html"
    assert html_path.exists(), "twin-dashboard.html must exist"
    content = html_path.read_text()
    cdn_patterns = [
        "cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com",
        "googleapis.com", "bootstrapcdn.com", "ajax.googleapis",
    ]
    for pattern in cdn_patterns:
        assert pattern not in content, f"CDN reference found: {pattern}"


# ---------------------------------------------------------------------------
# 9. web/js/twin-dashboard.js has no eval()
# ---------------------------------------------------------------------------
def test_twin_dashboard_js_no_eval():
    js_path = PROJECT_ROOT / "web" / "js" / "twin-dashboard.js"
    assert js_path.exists(), "twin-dashboard.js must exist"
    content = js_path.read_text()
    # eval( or eval` — banned absolutely
    assert "eval(" not in content, "eval() found in twin-dashboard.js — BANNED"
    assert "eval`" not in content, "eval` found in twin-dashboard.js — BANNED"


# ---------------------------------------------------------------------------
# 10. No port 9222 anywhere in twin dashboard files
# ---------------------------------------------------------------------------
def test_no_port_9222_in_twin_dashboard():
    for rel in [
        "web/twin-dashboard.html",
        "web/js/twin-dashboard.js",
        "web/css/twin-dashboard.css",
    ]:
        path = PROJECT_ROOT / rel
        assert path.exists(), f"{rel} must exist"
        content = path.read_text()
        assert "9222" not in content, f"Banned port 9222 found in {rel}"


# ---------------------------------------------------------------------------
# 11. POST /api/v1/twin/queue rejects unknown action
# ---------------------------------------------------------------------------
def test_twin_queue_rejects_unknown_action(twin_server):
    status, data = _req(twin_server, "/api/v1/twin/queue", method="POST",
                        payload={"action": "hack_the_planet"})
    assert status == 400
    assert "error" in data


# ---------------------------------------------------------------------------
# 12. POST /api/v1/twin/queue requires auth
# ---------------------------------------------------------------------------
def test_twin_queue_requires_auth(twin_server):
    status, data = _req(twin_server, "/api/v1/twin/queue", method="POST",
                        payload={"action": "navigate"}, token=None)
    assert status == 401


# ---------------------------------------------------------------------------
# 13. DELETE /api/v1/twin/queue/{task_id} requires auth
# ---------------------------------------------------------------------------
def test_twin_cancel_requires_auth(twin_server):
    status, data = _req(twin_server, "/api/v1/twin/queue/nonexistent-id",
                        method="DELETE", token=None)
    assert status == 401


# ---------------------------------------------------------------------------
# 14. DELETE unknown task_id returns 404
# ---------------------------------------------------------------------------
def test_twin_cancel_unknown_task_returns_404(twin_server):
    status, data = _req(twin_server, "/api/v1/twin/queue/does-not-exist-xyz",
                        method="DELETE")
    assert status == 404
    assert "error" in data
