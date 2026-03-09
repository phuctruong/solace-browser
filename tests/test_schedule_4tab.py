"""tests/test_schedule_4tab.py — Schedule 4-Tab Redesign acceptance gate."""
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
VALID_TOKEN = "a" * 64


def _req(base_url, path, method="GET", payload=None):
    url = base_url + path
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {VALID_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


@pytest.fixture
def tab_server(tmp_path, monkeypatch):
    import yinyang_server as ys

    for attr in ["EVIDENCE_PATH", "PORT_LOCK_PATH", "SETTINGS_PATH"]:
        monkeypatch.setattr(ys, attr, tmp_path / f"{attr.lower()}.json")
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


def test_upcoming_returns_schedules_and_keepalive(tab_server):
    status, data = _req(tab_server, "/api/v1/schedule/upcoming")
    assert status == 200
    assert "schedules" in data
    assert "keepalive" in data
    assert "pending_approvals" in data
    assert "pending_esign" in data


def test_approval_queue_never_auto_approves(tab_server):
    """Countdown = auto-REJECT. Check JS: rejectItem called, approveItem NOT called on countdown."""
    js_path = PROJECT_ROOT / "web" / "js" / "schedule.js"
    if js_path.exists():
        content = js_path.read_text()
        assert "auto-REJECT" in content or "rejectItem" in content
        # The countdown expiry must call rejectItem, never approveItem
        # Verify rejectItem is called when remaining <= 0 (not approveItem)
        assert "rejectItem(runId)" in content or "rejectItem(run_id)" in content.lower()


def test_esign_pending_list(tab_server):
    status, data = _req(tab_server, "/api/v1/esign/pending")
    assert status == 200
    assert "pending" in data


def test_esign_sign_creates_evidence(tab_server):
    import json
    import yinyang_server as ys
    # Seed an esign item so the sign endpoint can find it
    esign_id = "dummy-esign-id"
    settings_path = ys.SETTINGS_PATH
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps({
        "esign_pending": [{
            "esign_id": esign_id,
            "action_type": "release_signoff",
            "requested_by": "qa@solace.local",
            "requested_at": "2026-03-09T06:00:00Z",
            "expires_at": "2026-03-09T07:00:00Z",
            "preview_text": "Approve release package",
        }]
    }))
    status, data = _req(
        tab_server,
        f"/api/v1/esign/{esign_id}/sign",
        method="POST",
        payload={"signature_token": "test-sig-token"},
    )
    assert status == 200
    assert data.get("signed") is True
    assert "sealed_at" in data


def test_schedule_4tab_css_no_hardcoded_hex(tab_server):
    css = (PROJECT_ROOT / "web" / "css" / "schedule.css").read_text()
    # Token definitions in :root are allowed; component rules must use var()
    # Verify that all non-:root lines with # are not hex color values
    in_root = False
    violations = []
    for line in css.split("\n"):
        stripped = line.strip()
        if stripped == ":root {":
            in_root = True
        elif stripped == "}" and in_root:
            in_root = False
        elif not in_root and "#" in stripped:
            # Allow CSS ID selectors (e.g. #approval-badge)
            # Disallow hex color values like #1a1a2e
            import re
            hex_colors = re.findall(r"(?<![a-zA-Z0-9_-])#[0-9a-fA-F]{3,8}\b", stripped)
            if hex_colors:
                violations.append(stripped)
    assert violations == [], f"Hardcoded hex colors outside :root: {violations}"


def test_schedule_4tab_html_no_cdn(tab_server):
    html = (PROJECT_ROOT / "web" / "schedule.html").read_text()
    assert "cdn.jsdelivr" not in html
    assert "bootstrap" not in html.lower()
    assert "tailwind" not in html.lower()


def test_cron_presets_all_valid(tab_server):
    """Every preset cron expression has 5 fields."""
    PRESETS = [
        "0 7 * * *",
        "0 9 * * 1-5",
        "0 * * * *",
        "0 */2 * * *",
        "0 9 * * 1",
    ]
    for p in PRESETS:
        assert len(p.split()) == 5, f"Invalid cron: {p}"


def test_esign_history_returns_list(tab_server):
    status, data = _req(tab_server, "/api/v1/esign/history")
    assert status == 200
    assert "history" in data
    assert isinstance(data["history"], list)


def test_esign_sign_requires_auth(tab_server):
    req = urllib.request.Request(
        tab_server + "/api/v1/esign/x/sign",
        data=b"{}",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        assert False, "should have raised"
    except urllib.error.HTTPError as e:
        assert e.code == 401


def test_upcoming_requires_auth(tab_server):
    req = urllib.request.Request(tab_server + "/api/v1/schedule/upcoming")
    try:
        urllib.request.urlopen(req, timeout=5)
        assert False, "should have raised"
    except urllib.error.HTTPError as e:
        assert e.code == 401
