# Diagram: 05-solace-runtime-architecture
"""tests/test_value_dashboard.py — Value Dashboard Top Rail acceptance gate."""

import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VALID_TOKEN = "a" * 64
VALID_STATES = {"IDLE", "EXECUTING", "PREVIEW_READY", "BUDGET_CHECK", "DONE", "FAILED"}


def _seed_session_stats(ys, **overrides):
    stats = {
        "session_id": "sess-123",
        "state": "IDLE",
        "app_name": None,
        "pages_visited": 0,
        "llm_calls": 0,
        "cost_usd": "0.00",
        "cost_saved_pct": 0,
        "duration_seconds": 0,
        "recipes_replayed": 0,
        "evidence_captured": 0,
        "session_start": None,
    }
    stats.update(overrides)
    with ys._SESSION_STATS_LOCK:
        ys._SESSION_STATS.clear()
        ys._SESSION_STATS.update(stats)


def _probe_handler(ys, path, auth_header=f"Bearer {VALID_TOKEN}", server_token=VALID_TOKEN):
    captured = {"status": None, "data": None}
    handler = ys.YinyangHandler.__new__(ys.YinyangHandler)
    handler.server = SimpleNamespace(session_token_sha256=server_token)
    handler.headers = {}
    if auth_header is not None:
        handler.headers["Authorization"] = auth_header
    handler.path = path
    handler._record_history_entry = lambda status: None

    def _capture(data, status=200):
        captured["data"] = data
        captured["status"] = status

    handler._send_json = _capture
    return handler, captured


@pytest.fixture
def ys():
    import yinyang_server as ys_module

    return ys_module


def test_session_stats_returns_valid_fields(ys, monkeypatch):
    _seed_session_stats(
        ys,
        session_id="sess-abc",
        state="EXECUTING",
        app_name="myapp",
        pages_visited=12,
        llm_calls=3,
        cost_usd="0.04",
        cost_saved_pct=90,
        recipes_replayed=4,
        evidence_captured=7,
        session_start=1710000000.0,
    )
    monkeypatch.setattr(ys.time, "time", lambda: 1710000042.0)

    handler, captured = _probe_handler(ys, "/api/v1/session/stats")
    ys.YinyangHandler._handle_session_stats(handler)

    assert captured["status"] == 200
    data = captured["data"]
    assert data["session_id"] == "sess-abc"
    assert data["state"] == "EXECUTING"
    assert data["app_name"] == "myapp"
    assert data["pages_visited"] == 12
    assert data["llm_calls"] == 3
    assert data["cost_usd"] == "0.04"
    assert data["cost_saved_pct"] == 90
    assert data["duration_seconds"] == 42
    assert data["recipes_replayed"] == 4
    assert data["evidence_captured"] == 7
    assert isinstance(data["session_start"], str)
    assert data["session_start"].endswith("Z")


def test_cost_usd_is_decimal_string_not_float(ys):
    _seed_session_stats(ys, cost_usd="12.340000")
    handler, captured = _probe_handler(ys, "/api/v1/session/stats")

    ys.YinyangHandler._handle_session_stats(handler)

    assert captured["status"] == 200
    cost = captured["data"]["cost_usd"]
    assert isinstance(cost, str)
    assert re.fullmatch(r"\d+\.\d+", cost)


def test_state_is_one_of_valid_values(ys):
    _seed_session_stats(ys, state="PREVIEW_READY")
    handler, captured = _probe_handler(ys, "/api/v1/session/stats")

    ys.YinyangHandler._handle_session_stats(handler)

    assert captured["data"]["state"] in VALID_STATES


def test_stats_reset_clears_counters(ys, monkeypatch):
    _seed_session_stats(
        ys,
        state="DONE",
        app_name="myapp",
        pages_visited=12,
        llm_calls=3,
        cost_usd="0.04",
        cost_saved_pct=90,
        duration_seconds=999,
        recipes_replayed=4,
        evidence_captured=7,
        session_start=1710000000.0,
    )
    monkeypatch.setattr(ys.time, "time", lambda: 1710000100.0)

    reset_handler, reset_captured = _probe_handler(ys, "/api/v1/session/stats/reset")
    ys.YinyangHandler._handle_session_stats_reset(reset_handler)
    assert reset_captured["status"] == 200
    assert reset_captured["data"] == {"reset": True}

    stats_handler, stats_captured = _probe_handler(ys, "/api/v1/session/stats")
    ys.YinyangHandler._handle_session_stats(stats_handler)
    data = stats_captured["data"]

    assert data["state"] == "IDLE"
    assert data["app_name"] is None
    assert data["pages_visited"] == 0
    assert data["llm_calls"] == 0
    assert data["cost_usd"] == "0.00"
    assert data["cost_saved_pct"] == 0
    assert data["recipes_replayed"] == 0
    assert data["evidence_captured"] == 0
    assert isinstance(data["session_id"], str)
    assert data["session_id"]
    assert isinstance(data["session_start"], str)
    assert data["session_start"].endswith("Z")


def test_stats_reset_requires_auth(ys):
    handler, captured = _probe_handler(ys, "/api/v1/session/stats/reset", auth_header=None)
    ys.YinyangHandler._handle_session_stats_reset(handler)
    assert captured["status"] == 401
    assert captured["data"] == {"error": "unauthorized"}


def test_dashboard_css_no_hardcoded_hex():
    css_path = PROJECT_ROOT / "web" / "css" / "dashboard.css"
    assert css_path.exists(), "dashboard.css must exist"
    content = css_path.read_text()
    component_css = re.sub(r":root\s*\{.*?\}", "", content, flags=re.DOTALL)
    assert "var(--hub-" in content
    assert re.search(r"#[0-9a-fA-F]{3,6}", component_css) is None


def test_dashboard_js_no_jquery():
    js_path = PROJECT_ROOT / "web" / "js" / "dashboard.js"
    assert js_path.exists(), "dashboard.js must exist"
    content = js_path.read_text()
    assert "jquery" not in content.lower()
    assert "bootstrap" not in content.lower()


def test_dashboard_html_no_cdn():
    html_path = PROJECT_ROOT / "web" / "dashboard.html"
    assert html_path.exists(), "dashboard.html must exist"
    content = html_path.read_text()
    assert "cdn.jsdelivr" not in content
    assert "bootstrap" not in content.lower()
    assert "tailwind" not in content.lower()


def test_rotation_content_has_7_facts():
    js_path = PROJECT_ROOT / "web" / "js" / "dashboard.js"
    content = js_path.read_text()
    facts_match = re.search(r"const FACTS\s*=\s*\[([^\]]+)\]", content, re.DOTALL)
    assert facts_match is not None
    facts_count = len([line for line in facts_match.group(1).splitlines() if line.strip().startswith('"')])
    assert facts_count >= 7, f"Need 7 facts, found {facts_count}"


def test_anti_clippy_no_interruption_routes():
    server_path = PROJECT_ROOT / "yinyang_server.py"
    js_path = PROJECT_ROOT / "web" / "js" / "dashboard.js"
    html_path = PROJECT_ROOT / "web" / "dashboard.html"

    server_content = server_path.read_text()
    js_content = js_path.read_text()
    html_content = html_path.read_text()

    assert "/api/v1/notify" not in server_content
    assert "alert(" not in js_content
    assert "modal" not in html_content.lower()


def test_dashboard_constructor_accepts_token_and_metrics_url():
    js_path = PROJECT_ROOT / "web" / "js" / "dashboard.js"
    content = js_path.read_text()
    assert re.search(r"constructor\(\s*apiToken\s*,\s*metricsUrl", content)


def test_dashboard_idle_prefers_delight_mode():
    js_path = PROJECT_ROOT / "web" / "js" / "dashboard.js"
    content = js_path.read_text()
    assert "EXECUTING" in content
    assert "PREVIEW_READY" in content
    assert "BUDGET_CHECK" in content
    assert re.search(r"_shouldShowStats\(", content)


def test_dashboard_stats_mode_mentions_evidence():
    js_path = PROJECT_ROOT / "web" / "js" / "dashboard.js"
    content = js_path.read_text()
    stats_match = re.search(r"_showStatsMode\(data\)\s*\{(.*?)\n  \}", content, re.DOTALL)
    assert stats_match is not None
    stats_block = stats_match.group(1)
    assert "evidence" in stats_block.lower()


def test_dashboard_html_uses_four_summary_cards():
    html_path = PROJECT_ROOT / "web" / "dashboard.html"
    content = html_path.read_text()
    assert content.count('class="stat-card"') == 4
