# Diagram: 05-solace-runtime-architecture
"""tests/test_tutorial_modal.py — Task 063: YinYang Tutorial 5-Step First-Run Modal."""
import json
import re
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

WEB_DIR = PROJECT_ROOT / "web"
TUTORIAL_HTML = WEB_DIR / "tutorial.html"
TUTORIAL_JS = WEB_DIR / "js" / "tutorial.js"
TUTORIAL_CSS = WEB_DIR / "css" / "tutorial.css"


def _req(base, path, method="GET", payload=None, token=VALID_TOKEN):
    url = base + path
    data = json.dumps(payload).encode() if payload else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            content_type = r.headers.get("Content-Type", "")
            raw = r.read()
            if "application/json" in content_type:
                return r.status, json.loads(raw), content_type
            return r.status, raw, content_type
    except urllib.error.HTTPError as e:
        raw = e.read() or b"{}"
        try:
            return e.code, json.loads(raw), ""
        except Exception:
            return e.code, raw, ""


@pytest.fixture
def tutorial_server(tmp_path, monkeypatch):
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


# ---------------------------------------------------------------------------
# Static file checks (no server needed)
# ---------------------------------------------------------------------------

def test_tutorial_html_exists():
    """web/tutorial.html must exist on disk."""
    assert TUTORIAL_HTML.exists(), f"Missing: {TUTORIAL_HTML}"


def test_tutorial_js_has_5_steps():
    """STEPS array in tutorial.js must have exactly 5 entries."""
    content = TUTORIAL_JS.read_text(encoding="utf-8")
    # Count icon entries as proxy for step count
    icons = re.findall(r"icon:", content)
    assert len(icons) == 5, f"Expected 5 steps, found {len(icons)} icon entries"


def test_tutorial_js_no_cdn():
    """No external CDN libraries in tutorial.js or tutorial.html."""
    banned_patterns = ["bootstrap", "tailwind", "jquery", "cdn."]
    for file_path in [TUTORIAL_JS, TUTORIAL_HTML]:
        content = file_path.read_text(encoding="utf-8").lower()
        for pattern in banned_patterns:
            assert pattern not in content, (
                f"CDN pattern '{pattern}' found in {file_path.name} — BANNED"
            )


def test_tutorial_css_no_hardcoded_hex():
    """Hex colour values must only appear inside the :root block in tutorial.css."""
    content = TUTORIAL_CSS.read_text(encoding="utf-8")
    # Extract :root block
    root_match = re.search(r":root\s*\{([^}]*)\}", content, re.DOTALL)
    assert root_match, "No :root block found in tutorial.css"
    root_block = root_match.group(0)
    # Remove :root block then check for hex values outside it
    outside_root = content.replace(root_block, "")
    hex_outside = re.findall(r"#[0-9a-fA-F]{3,8}\b", outside_root)
    assert not hex_outside, (
        f"Hardcoded hex values found outside :root in tutorial.css: {hex_outside}"
    )


def test_tutorial_skip_sets_storage_key():
    """JS must declare TUTORIAL_KEY = 'sb_tutorial_v1'."""
    content = TUTORIAL_JS.read_text(encoding="utf-8")
    assert "TUTORIAL_KEY = 'sb_tutorial_v1'" in content, (
        "TUTORIAL_KEY constant with value 'sb_tutorial_v1' not found in tutorial.js"
    )


def test_tutorial_done_state_json():
    """JS must include completed_at, locale, and version in the done state."""
    content = TUTORIAL_JS.read_text(encoding="utf-8")
    assert "completed_at" in content, "completed_at missing from done state in tutorial.js"
    assert "locale" in content, "locale missing from done state in tutorial.js"
    assert "version" in content, "version missing from done state in tutorial.js"


def test_tutorial_keyboard_escape_skips():
    """Escape key must trigger _skip() in tutorial.js."""
    content = TUTORIAL_JS.read_text(encoding="utf-8")
    assert "Escape" in content, "'Escape' key handler not found in tutorial.js"
    # Find the Escape handler and verify it calls _skip
    escape_idx = content.index("Escape")
    nearby = content[escape_idx : escape_idx + 30]
    assert "_skip" in nearby, f"Escape key does not call _skip() — nearby text: {nearby!r}"


def test_tutorial_never_forces_reopening():
    """No server route should force the tutorial to re-open (client-side only)."""
    content = TUTORIAL_JS.read_text(encoding="utf-8")
    # The done/skipped check must guard against re-showing
    assert "_shouldShow" in content, "_shouldShow() guard function missing"
    assert "'done'" in content or '"done"' in content, "done status check missing in _shouldShow"
    assert "'skipped'" in content or '"skipped"' in content, "skipped status check missing"


# ---------------------------------------------------------------------------
# Server integration tests (require live server)
# ---------------------------------------------------------------------------

def test_tutorial_reset_route_exists(tutorial_server):
    """GET /api/v1/tutorial/reset must return 200 with auth."""
    status, data, _ = _req(tutorial_server, "/api/v1/tutorial/reset")
    assert status == 200, f"Expected 200, got {status}"
    assert data.get("reset") is True, f"Expected reset=True, got: {data}"
    assert data.get("storage_key") == "sb_tutorial_v1", f"Wrong storage_key: {data}"


def test_tutorial_html_served(tutorial_server):
    """GET /web/tutorial.html must return 200 with text/html content type."""
    status, body, content_type = _req(tutorial_server, "/web/tutorial.html")
    assert status == 200, f"Expected 200, got {status}"
    assert "text/html" in content_type, f"Expected text/html, got: {content_type}"
    html_text = body.decode("utf-8") if isinstance(body, bytes) else body
    assert "tutorial-overlay" in html_text, "tutorial-overlay element missing from served HTML"
