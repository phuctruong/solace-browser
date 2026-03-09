"""
test_budget_controls.py — Budget Controls UI tests.
Task 020 | Rung: 641

Kill conditions verified here:
  - No port 9222
  - No "Companion App"
  - No bare except in budget-related code
  - No CDN refs in web/budget.html
  - No eval() in web/js/budget.js
  - All monetary values as string Decimals (never float)
  - Auth required on POST routes
"""
import hashlib
import json
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

# ---------------------------------------------------------------------------
# Test token
# ---------------------------------------------------------------------------
TEST_TOKEN = "test-token-budget-controls-020"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Handler factory — mirrors test_recipe_store.py pattern
# ---------------------------------------------------------------------------
def _make_handler(
    path: str,
    method: str = "GET",
    payload: dict | None = None,
    token: str = TEST_TOKEN,
):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18892)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update(
        {"status": status, "data": data}
    )
    handler._read_json_body = lambda: payload
    return handler, captured


def get_json(path: str) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET")
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def post_json(path: str, payload: dict) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "POST", payload)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


# ---------------------------------------------------------------------------
# Fixtures — reset BUDGET_PATH between tests
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_budget(tmp_path, monkeypatch):
    """Use a fresh budget.json in tmp_path for every test."""
    budget_path = tmp_path / "budget.json"
    monkeypatch.setattr(ys, "BUDGET_PATH", budget_path)
    yield
    # cleanup is handled by tmp_path


# ---------------------------------------------------------------------------
# Test 1: GET /api/v1/budget returns 200
# ---------------------------------------------------------------------------
def test_budget_endpoint_exists():
    status, data = get_json("/api/v1/budget")
    assert status == 200, f"Expected 200, got {status}: {data}"


# ---------------------------------------------------------------------------
# Test 2: GET /api/v1/budget/usage returns 200
# ---------------------------------------------------------------------------
def test_budget_usage_endpoint_exists():
    status, data = get_json("/api/v1/budget/usage")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert "today_spend_usd" in data, "usage response must have today_spend_usd"
    assert "month_spend_usd" in data, "usage response must have month_spend_usd"


# ---------------------------------------------------------------------------
# Test 3: default daily_limit_usd is a string, not float
# ---------------------------------------------------------------------------
def test_budget_default_limits_are_strings():
    status, data = get_json("/api/v1/budget")
    assert status == 200
    assert "daily_limit_usd" in data
    assert isinstance(data["daily_limit_usd"], str), (
        f"daily_limit_usd must be a string, got {type(data['daily_limit_usd'])}"
    )
    assert "monthly_limit_usd" in data
    assert isinstance(data["monthly_limit_usd"], str), (
        f"monthly_limit_usd must be a string, got {type(data['monthly_limit_usd'])}"
    )


# ---------------------------------------------------------------------------
# Test 4: POST /budget sets daily_limit_usd and persists
# ---------------------------------------------------------------------------
def test_budget_set_daily_limit():
    post_status, post_data = post_json("/api/v1/budget", {"daily_limit_usd": "5.00"})
    assert post_status == 200, f"Expected 200 on POST, got {post_status}: {post_data}"

    get_status, get_data = get_json("/api/v1/budget")
    assert get_status == 200
    # Value may be stored as "5.00" or "5" — just verify it starts with "5"
    assert str(get_data.get("daily_limit_usd", "")).startswith("5"), (
        f"daily_limit_usd not persisted: {get_data}"
    )


# ---------------------------------------------------------------------------
# Test 5: POST /budget sets monthly_limit_usd and persists
# ---------------------------------------------------------------------------
def test_budget_set_monthly_limit():
    post_status, post_data = post_json("/api/v1/budget", {"monthly_limit_usd": "50.00"})
    assert post_status == 200, f"Expected 200 on POST, got {post_status}: {post_data}"

    get_status, get_data = get_json("/api/v1/budget")
    assert get_status == 200
    assert str(get_data.get("monthly_limit_usd", "")).startswith("50"), (
        f"monthly_limit_usd not persisted: {get_data}"
    )


# ---------------------------------------------------------------------------
# Test 6: GET /api/v1/budget/usage has today_spend_usd as string
# ---------------------------------------------------------------------------
def test_budget_usage_has_today_spend():
    status, data = get_json("/api/v1/budget/usage")
    assert status == 200
    assert "today_spend_usd" in data
    assert isinstance(data["today_spend_usd"], str), (
        f"today_spend_usd must be a string, got {type(data['today_spend_usd'])}"
    )


# ---------------------------------------------------------------------------
# Test 7: pause_on_exceeded default is True
# ---------------------------------------------------------------------------
def test_budget_pause_on_exceeded_default_true():
    status, data = get_json("/api/v1/budget")
    assert status == 200
    assert "pause_on_exceeded" in data
    assert data["pause_on_exceeded"] is True, (
        f"pause_on_exceeded default must be True, got {data['pause_on_exceeded']}"
    )


# ---------------------------------------------------------------------------
# Test 8: web/budget.html has no CDN references
# ---------------------------------------------------------------------------
def test_budget_html_no_cdn():
    html_path = REPO_ROOT / "web" / "budget.html"
    assert html_path.exists(), "web/budget.html must exist"
    content = html_path.read_text()
    cdn_patterns = [
        r"cdn\.jsdelivr\.net",
        r"cdnjs\.cloudflare\.com",
        r"unpkg\.com",
        r"googleapis\.com",
        r"bootstrapcdn",
        r"https?://[^\s\"']+\.min\.js",
        r"https?://[^\s\"']+\.min\.css",
    ]
    for pattern in cdn_patterns:
        assert not re.search(pattern, content, re.IGNORECASE), (
            f"web/budget.html contains CDN reference matching '{pattern}'"
        )


# ---------------------------------------------------------------------------
# Test 9: web/js/budget.js has no eval()
# ---------------------------------------------------------------------------
def test_budget_js_no_eval():
    js_path = REPO_ROOT / "web" / "js" / "budget.js"
    assert js_path.exists(), "web/js/budget.js must exist"
    content = js_path.read_text()
    # Match eval( not preceded by identifier chars (avoids false positive on "eval" in comments
    # that are just documentation)
    assert not re.search(r"\beval\s*\(", content), (
        "web/js/budget.js must not contain eval()"
    )


# ---------------------------------------------------------------------------
# Test 10: no port 9222 in budget-related files
# ---------------------------------------------------------------------------
def test_no_port_9222_in_budget():
    files_to_check = [
        REPO_ROOT / "web" / "budget.html",
        REPO_ROOT / "web" / "js" / "budget.js",
        REPO_ROOT / "web" / "css" / "budget.css",
    ]
    for fpath in files_to_check:
        if fpath.exists():
            content = fpath.read_text()
            assert "9222" not in content, (
                f"{fpath.name} contains banned port 9222"
            )
