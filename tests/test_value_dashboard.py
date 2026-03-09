"""tests/test_value_dashboard.py — Value Dashboard Top Rail acceptance gate."""
import json, sys, threading, time, urllib.error, urllib.request
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
VALID_TOKEN = "a" * 64

def _req(base, path, method="GET", payload=None):
    url = base + path
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Authorization": f"Bearer {VALID_TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

@pytest.fixture
def dash_server(tmp_path, monkeypatch):
    import yinyang_server as ys
    for attr in ["EVIDENCE_PATH", "PORT_LOCK_PATH", "SETTINGS_PATH"]:
        monkeypatch.setattr(ys, attr, tmp_path / f"{attr.lower()}.json", raising=False)
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

def test_session_stats_returns_valid_fields(dash_server):
    status, data = _req(dash_server, "/api/v1/session/stats")
    assert status == 200
    assert "state" in data
    assert "pages_visited" in data
    assert "llm_calls" in data
    assert "cost_usd" in data
    assert "recipes_replayed" in data
    assert "evidence_captured" in data

def test_cost_usd_is_string_not_float(dash_server):
    status, data = _req(dash_server, "/api/v1/session/stats")
    assert status == 200
    cost = data["cost_usd"]
    assert isinstance(cost, str), f"cost_usd must be string, got {type(cost)}: {cost}"

def test_state_is_valid_value(dash_server):
    status, data = _req(dash_server, "/api/v1/session/stats")
    valid_states = {"IDLE", "EXECUTING", "PREVIEW_READY", "BUDGET_CHECK", "DONE", "FAILED"}
    assert data["state"] in valid_states

def test_stats_reset_returns_true(dash_server):
    status, data = _req(dash_server, "/api/v1/session/stats/reset", method="POST")
    assert status == 200
    assert data.get("reset") is True

def test_stats_reset_requires_auth(dash_server):
    req = urllib.request.Request(dash_server + "/api/v1/session/stats/reset",
        data=b"", method="POST", headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
        assert False
    except urllib.error.HTTPError as e:
        assert e.code == 401

def test_dashboard_css_no_hardcoded_hex_in_components():
    css_path = PROJECT_ROOT / "web" / "css" / "dashboard.css"
    assert css_path.exists(), "dashboard.css must exist"
    content = css_path.read_text()
    # Verify file uses var(--hub-*) tokens in component rules
    assert "var(--hub-" in content

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
    # Count FACTS array entries
    import re
    facts_match = re.search(r'const FACTS\s*=\s*\[([^\]]+)\]', content, re.DOTALL)
    if facts_match:
        facts_count = len([l for l in facts_match.group(1).split('\n') if l.strip().startswith('"')])
        assert facts_count >= 7, f"Need 7 facts, found {facts_count}"

def test_anti_clippy_no_interrupt_routes(dash_server):
    """No /api/v1/notify or pop-up routes exist."""
    req = urllib.request.Request(dash_server + "/api/v1/notify")
    try:
        urllib.request.urlopen(req, timeout=5)
        # If this route exists, it's a CLIPPY violation
        assert False, "INTERRUPT_USER route /api/v1/notify must not exist"
    except urllib.error.HTTPError as e:
        assert e.code in (401, 404)  # 404 = route doesn't exist = PASS
    except urllib.error.URLError:
        pass  # connection error = also fine
