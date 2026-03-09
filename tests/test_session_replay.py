"""tests/test_session_replay.py — Task 027: Session Replay Viewer (10 tests)."""
import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18927
VALID_TOKEN = "c" * 64


@pytest.fixture(scope="module")
def replay_server():
    import yinyang_server as ys

    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://localhost:{TEST_PORT}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield httpd
    httpd.shutdown()


def auth_req(path: str, method: str = "GET", body: dict | None = None, port: int = TEST_PORT):
    url = f"http://localhost:{port}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {VALID_TOKEN}")
    if data:
        req.add_header("Content-Type", "application/json")
    return req


# ---------------------------------------------------------------------------
# Static file checks
# ---------------------------------------------------------------------------

def test_session_replay_html_exists():
    """Test 1: session-replay.html exists."""
    assert (REPO_ROOT / "web/session-replay.html").exists()


def test_session_replay_html_no_cdn():
    """Test 2: HTML has no CDN references."""
    content = (REPO_ROOT / "web/session-replay.html").read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in content
    assert "unpkg.com" not in content


def test_session_replay_html_has_timeline():
    """Test 3: HTML has action timeline element."""
    content = (REPO_ROOT / "web/session-replay.html").read_text(encoding="utf-8")
    assert "timeline" in content.lower()


def test_session_replay_js_no_eval():
    """Test 4: JS has no eval()."""
    content = (REPO_ROOT / "web/js/session-replay.js").read_text(encoding="utf-8")
    assert "eval(" not in content


def test_session_replay_js_iife():
    """Test 5: JS uses IIFE pattern."""
    content = (REPO_ROOT / "web/js/session-replay.js").read_text(encoding="utf-8")
    assert "(function" in content or "})();" in content


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

def test_replay_sessions_list_returns_200(replay_server):
    """Test 6: GET /api/v1/replay/sessions returns 200."""
    resp = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/replay/sessions", timeout=3
    )
    assert resp.status == 200
    data = json.loads(resp.read())
    assert "sessions" in data
    assert isinstance(data["sessions"], list)


def test_replay_create_requires_auth(replay_server):
    """Test 7: POST /api/v1/replay/sessions without auth returns 401."""
    req = urllib.request.Request(
        f"http://localhost:{TEST_PORT}/api/v1/replay/sessions",
        data=json.dumps({"name": "Test"}).encode(),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    try:
        urllib.request.urlopen(req, timeout=3)
        assert False, "Expected 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401


def test_replay_create_and_retrieve(replay_server):
    """Test 8: Create session then retrieve its detail."""
    req = auth_req("/api/v1/replay/sessions", "POST", {"name": "TestReplay027", "start_url": "https://example.com"})
    resp = urllib.request.urlopen(req, timeout=3)
    assert resp.status == 201
    data = json.loads(resp.read())
    session = data["session"]
    assert "replay_id" in session
    assert session["replay_id"].startswith("replay_")
    assert session["name"] == "TestReplay027"

    # Retrieve detail
    det_resp = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/replay/sessions/{session['replay_id']}", timeout=3
    )
    det_data = json.loads(det_resp.read())
    assert det_data["session"]["replay_id"] == session["replay_id"]


def test_replay_add_action_to_session(replay_server):
    """Test 9: Add action to replay session and verify action_count increases."""
    req = auth_req("/api/v1/replay/sessions", "POST", {"name": "ActionTest027"})
    resp = urllib.request.urlopen(req, timeout=3)
    session = json.loads(resp.read())["session"]
    rid = session["replay_id"]

    act_req = auth_req(f"/api/v1/replay/sessions/{rid}/actions", "POST",
                       {"action": "click", "selector": "#submit-btn"})
    act_resp = urllib.request.urlopen(act_req, timeout=3)
    assert act_resp.status == 200
    act_data = json.loads(act_resp.read())
    assert act_data["status"] == "added"
    assert act_data["action"]["action"] == "click"

    # Verify action appears in session detail
    det_resp = urllib.request.urlopen(
        f"http://localhost:{TEST_PORT}/api/v1/replay/sessions/{rid}", timeout=3
    )
    det = json.loads(det_resp.read())["session"]
    assert len(det.get("actions", [])) == 1
    assert det["actions"][0]["selector"] == "#submit-btn"


def test_replay_invalid_action_type_rejected(replay_server):
    """Test 10: Invalid action type returns 400."""
    req = auth_req("/api/v1/replay/sessions", "POST", {"name": "BadActionTest027"})
    resp = urllib.request.urlopen(req, timeout=3)
    rid = json.loads(resp.read())["session"]["replay_id"]

    act_req = auth_req(f"/api/v1/replay/sessions/{rid}/actions", "POST",
                       {"action": "invalid_action_xyz"})
    try:
        urllib.request.urlopen(act_req, timeout=3)
        assert False, "Expected 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400
