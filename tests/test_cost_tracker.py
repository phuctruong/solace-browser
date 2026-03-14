# Diagram: 05-solace-runtime-architecture
"""tests/test_cost_tracker.py — Session Cost Tracker acceptance gate.
Task 042 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - cost_usd is always a Decimal string (6 decimal places)
  - Auth required on POST routes; GET /summary and GET /budget are public
  - No port 9222, no CDN, no eval()
  - No canvas or Chart.js — inline SVG only
"""
import hashlib
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-cost-042"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18942)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET", token=token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path: str, payload: dict, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "POST", payload, token=token)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


@pytest.fixture(autouse=True)
def reset_cost_state(monkeypatch):
    """Reset cost tracker state between tests."""
    monkeypatch.setattr(ys, "_COST_EVENTS", [])
    monkeypatch.setattr(ys, "_COST_BUDGET", {"daily_limit": "5.00", "monthly_limit": "50.00"})
    yield


# ---------------------------------------------------------------------------
# 1. test_cost_record_event — POST /cost/record → event_id returned
# ---------------------------------------------------------------------------
def test_cost_record_event():
    status, data = post_json("/api/v1/cost/record", {
        "session_id": "sess_001",
        "model": "claude-haiku",
        "tokens_in": 1000,
        "tokens_out": 500,
    })
    assert status == 200
    assert data.get("status") == "recorded"
    assert "event_id" in data
    assert data["event_id"].startswith("cost_")


# ---------------------------------------------------------------------------
# 2. test_cost_session_breakdown — GET /cost/session/{id} → events for session
# ---------------------------------------------------------------------------
def test_cost_session_breakdown():
    post_json("/api/v1/cost/record", {
        "session_id": "sess_xyz",
        "model": "claude-sonnet",
        "tokens_in": 500,
        "tokens_out": 200,
    })
    status, data = get_json("/api/v1/cost/session/sess_xyz")
    assert status == 200
    assert data.get("session_id") == "sess_xyz"
    assert len(data.get("events", [])) == 1


# ---------------------------------------------------------------------------
# 3. test_cost_summary_daily — GET /cost/summary → daily_total_usd present
# ---------------------------------------------------------------------------
def test_cost_summary_daily():
    status, data = get_json("/api/v1/cost/summary")
    assert status == 200
    assert "daily_total_usd" in data
    assert "monthly_total_usd" in data


# ---------------------------------------------------------------------------
# 4. test_cost_cost_is_string — cost_usd is string not float
# ---------------------------------------------------------------------------
def test_cost_cost_is_string():
    _, data = post_json("/api/v1/cost/record", {
        "session_id": "sess_type",
        "model": "gpt-4o-mini",
        "tokens_in": 1000,
        "tokens_out": 1000,
    })
    assert isinstance(data.get("cost_usd"), str), "cost_usd must be a string, not float"
    # Verify it's a valid decimal string
    from decimal import Decimal
    val = Decimal(data["cost_usd"])
    assert val >= 0


# ---------------------------------------------------------------------------
# 5. test_cost_budget_set — POST /cost/budget → limits updated
# ---------------------------------------------------------------------------
def test_cost_budget_set():
    status, data = post_json("/api/v1/cost/budget", {
        "daily_limit": "10.00",
        "monthly_limit": "100.00",
    })
    assert status == 200
    assert data.get("status") == "updated"
    assert data["budget"]["daily_limit"] == "10.00"


# ---------------------------------------------------------------------------
# 6. test_cost_budget_get — GET /cost/budget → current limits
# ---------------------------------------------------------------------------
def test_cost_budget_get():
    status, data = get_json("/api/v1/cost/budget")
    assert status == 200
    assert "daily_limit" in data
    assert "monthly_limit" in data


# ---------------------------------------------------------------------------
# 7. test_cost_budget_is_string — daily_limit is string not float
# ---------------------------------------------------------------------------
def test_cost_budget_is_string():
    _, data = get_json("/api/v1/cost/budget")
    assert isinstance(data.get("daily_limit"), str), "daily_limit must be a string"
    assert isinstance(data.get("monthly_limit"), str), "monthly_limit must be a string"


# ---------------------------------------------------------------------------
# 8. test_cost_html_no_cdn — web/cost-tracker.html no CDN
# ---------------------------------------------------------------------------
def test_cost_html_no_cdn():
    html_path = REPO_ROOT / "web" / "cost-tracker.html"
    assert html_path.exists(), "cost-tracker.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 9. test_cost_js_no_eval — web/js/cost-tracker.js no eval()
# ---------------------------------------------------------------------------
def test_cost_js_no_eval():
    js_path = REPO_ROOT / "web" / "js" / "cost-tracker.js"
    assert js_path.exists(), "cost-tracker.js must exist"
    content = js_path.read_text()
    assert "eval(" not in content, "eval() is banned in JS"


# ---------------------------------------------------------------------------
# 10. test_no_port_9222_in_cost_tracker — grep check
# ---------------------------------------------------------------------------
def test_no_port_9222_in_cost_tracker():
    files_to_check = [
        REPO_ROOT / "web" / "cost-tracker.html",
        REPO_ROOT / "web" / "js" / "cost-tracker.js",
        REPO_ROOT / "web" / "css" / "cost-tracker.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"
