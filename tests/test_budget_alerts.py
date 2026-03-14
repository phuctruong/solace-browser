# Diagram: 05-solace-runtime-architecture
"""tests/test_budget_alerts.py — Task 034: Budget Alert System (10 tests)."""
import hashlib
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-034"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path, method="GET", payload=None, token=TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18934)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path, token=TEST_TOKEN):
    handler, captured = _make_handler(path, "GET", token=token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path, payload, token=TEST_TOKEN):
    handler, captured = _make_handler(path, "POST", payload, token=token)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


def delete_json(path, token=TEST_TOKEN):
    handler, captured = _make_handler(path, "DELETE", token=token)
    handler.do_DELETE()
    return int(captured["status"]), dict(captured["data"])


# ---------------------------------------------------------------------------
# Fixture: clear state before each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_state():
    """Clear in-memory alert state before each test."""
    ys._ALERT_RULES.clear()
    ys._TRIGGERED_ALERTS.clear()
    yield
    ys._ALERT_RULES.clear()
    ys._TRIGGERED_ALERTS.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_budget_alerts_list_empty_initially():
    """Test 1: GET /alert-rules → []."""
    status, data = get_json("/api/v1/budget/alert-rules")
    assert status == 200
    assert data["rules"] == []
    assert data["total"] == 0


def test_budget_alert_create():
    """Test 2: POST → alert_id returned."""
    status, data = post_json("/api/v1/budget/alert-rules", {
        "metric": "daily_cost",
        "threshold": "10.00",
        "action": "notify",
    })
    assert status == 201
    assert "alert_id" in data["rule"]
    assert data["rule"]["alert_id"].startswith("alrt_")
    assert data["status"] == "created"


def test_budget_alert_delete():
    """Test 3: DELETE → removed."""
    _, create_data = post_json("/api/v1/budget/alert-rules", {
        "metric": "monthly_cost",
        "threshold": "50.00",
        "action": "pause",
    })
    alert_id = create_data["rule"]["alert_id"]

    status, data = delete_json(f"/api/v1/budget/alert-rules/{alert_id}")
    assert status == 200
    assert data["status"] == "deleted"

    # Verify removed
    status2, data2 = get_json("/api/v1/budget/alert-rules")
    assert data2["total"] == 0


def test_budget_alert_invalid_metric():
    """Test 4: unknown metric → 400."""
    status, data = post_json("/api/v1/budget/alert-rules", {
        "metric": "unknown_metric",
        "threshold": "10.00",
        "action": "notify",
    })
    assert status == 400
    assert "metric" in data["error"].lower()


def test_budget_alert_invalid_action():
    """Test 5: unknown action → 400."""
    status, data = post_json("/api/v1/budget/alert-rules", {
        "metric": "daily_cost",
        "threshold": "10.00",
        "action": "explode",
    })
    assert status == 400
    assert "action" in data["error"].lower()


def test_budget_alert_threshold_is_string():
    """Test 6: threshold is string not float."""
    _, create_data = post_json("/api/v1/budget/alert-rules", {
        "metric": "token_count",
        "threshold": "1000",
        "action": "block",
    })
    rule = create_data["rule"]
    assert isinstance(rule["threshold"], str), "threshold must be a string"


def test_budget_triggered_empty_initially():
    """Test 7: GET /triggered → []."""
    status, data = get_json("/api/v1/budget/alert-rules/triggered")
    assert status == 200
    assert data["triggered"] == []
    assert data["total"] == 0


def test_budget_alert_acknowledge():
    """Test 8: POST /acknowledge → acknowledged=True."""
    # Manually inject a triggered alert into state
    alert_id = "alrt_test-ack-001"
    ys._TRIGGERED_ALERTS.append({
        "alert_id": alert_id,
        "metric": "daily_cost",
        "actual_value": "15.00",
        "triggered_at": "2026-01-01T00:00:00Z",
        "acknowledged": False,
    })

    status, data = post_json(f"/api/v1/budget/alert-rules/{alert_id}/acknowledge", {})
    assert status == 200
    assert data["acknowledged"] is True
    assert data["alert_id"] == alert_id


def test_budget_alerts_html_no_cdn():
    """Test 9: web/budget-alerts.html no CDN."""
    html_path = REPO_ROOT / "web" / "budget-alerts.html"
    assert html_path.exists(), "budget-alerts.html must exist"
    content = html_path.read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in content
    assert "unpkg.com" not in content
    assert "cdnjs.cloudflare.com" not in content


def test_no_port_9222_in_budget_alerts():
    """Test 10: no port 9222 in budget alerts files."""
    for fpath in [
        REPO_ROOT / "web" / "budget-alerts.html",
        REPO_ROOT / "web" / "js" / "budget-alerts.js",
        REPO_ROOT / "web" / "css" / "budget-alerts.css",
    ]:
        if fpath.exists():
            assert "9222" not in fpath.read_text(), f"port 9222 found in {fpath}"
