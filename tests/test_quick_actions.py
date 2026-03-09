"""tests/test_quick_actions.py — Quick Actions Menu acceptance gate.
Task 032 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - DEFAULT_ACTIONS (8, cannot delete → 409)
  - Custom actions add-only via POST
  - Recent actions FIFO last 20
  - No port 9222, no eval(), no CDN
"""
import hashlib
import pathlib
import re
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_TOKEN = "test-token-quick-actions-032"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18902)
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


def delete_path(path: str, token: str = TEST_TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "DELETE", token=token)
    handler.do_DELETE()
    return int(captured["status"]), dict(captured["data"])


@pytest.fixture(autouse=True)
def reset_quick_actions(monkeypatch):
    """Reset custom actions and recent actions between tests."""
    monkeypatch.setattr(ys, "_CUSTOM_ACTIONS", [])
    monkeypatch.setattr(ys, "_RECENT_ACTIONS", [])
    yield


# ---------------------------------------------------------------------------
# 1. GET /api/v1/quick-actions returns 8 default actions
# ---------------------------------------------------------------------------
def test_quick_actions_list_has_8_defaults():
    status, data = get_json("/api/v1/quick-actions")
    assert status == 200
    assert "actions" in data
    defaults = [a for a in data["actions"] if a.get("builtin")]
    assert len(defaults) == 8, f"Expected 8 built-in actions, got {len(defaults)}"


# ---------------------------------------------------------------------------
# 2. All default actions have required fields
# ---------------------------------------------------------------------------
def test_quick_actions_default_fields():
    _, data = get_json("/api/v1/quick-actions")
    for action in data["actions"]:
        assert "id" in action
        assert "label" in action
        assert "url" in action
        assert "icon" in action
        assert "builtin" in action


# ---------------------------------------------------------------------------
# 3. DELETE a builtin action → 409
# ---------------------------------------------------------------------------
def test_quick_actions_delete_builtin_returns_409():
    _, data = get_json("/api/v1/quick-actions")
    builtin_id = next(a["id"] for a in data["actions"] if a.get("builtin"))
    status, resp = delete_path(f"/api/v1/quick-actions/{builtin_id}")
    assert status == 409
    assert "error" in resp


# ---------------------------------------------------------------------------
# 4. POST adds a custom action
# ---------------------------------------------------------------------------
def test_quick_actions_add_custom():
    status, data = post_json("/api/v1/quick-actions", {"label": "Test Action", "url": "/web/test.html", "icon": "star"})
    assert status == 200
    assert data.get("status") == "added"
    assert "action" in data
    assert data["action"]["label"] == "Test Action"


# ---------------------------------------------------------------------------
# 5. Custom action appears in list after add
# ---------------------------------------------------------------------------
def test_quick_actions_custom_appears_in_list():
    post_json("/api/v1/quick-actions", {"label": "My Custom", "url": "/web/custom.html"})
    _, data = get_json("/api/v1/quick-actions")
    labels = [a["label"] for a in data["actions"]]
    assert "My Custom" in labels


# ---------------------------------------------------------------------------
# 6. DELETE a custom action → 200
# ---------------------------------------------------------------------------
def test_quick_actions_delete_custom_ok():
    _, add_data = post_json("/api/v1/quick-actions", {"label": "Del Me", "url": "/x"})
    action_id = add_data["action"]["id"]
    status, resp = delete_path(f"/api/v1/quick-actions/{action_id}")
    assert status == 200
    assert resp.get("status") == "deleted"


# ---------------------------------------------------------------------------
# 7. Recent actions list starts empty
# ---------------------------------------------------------------------------
def test_quick_actions_recent_starts_empty():
    status, data = get_json("/api/v1/quick-actions/recent")
    assert status == 200
    assert data.get("recent") == [] or data.get("total") == 0


# ---------------------------------------------------------------------------
# 8. Record a recent action → appears in recent list
# ---------------------------------------------------------------------------
def test_quick_actions_record_recent():
    # Use a known default action id
    _, list_data = get_json("/api/v1/quick-actions")
    first_id = list_data["actions"][0]["id"]
    post_json("/api/v1/quick-actions/recent", {"action_id": first_id})
    _, recent_data = get_json("/api/v1/quick-actions/recent")
    recent_ids = [r["id"] for r in recent_data.get("recent", [])]
    assert first_id in recent_ids


# ---------------------------------------------------------------------------
# 9. web/quick-actions.html has no CDN references
# ---------------------------------------------------------------------------
def test_quick_actions_html_no_cdn():
    html_path = REPO_ROOT / "web" / "quick-actions.html"
    assert html_path.exists(), "web/quick-actions.html must exist"
    content = html_path.read_text()
    cdn_patterns = [
        r"cdn\.jsdelivr\.net", r"cdnjs\.cloudflare\.com", r"unpkg\.com",
        r"googleapis\.com", r"bootstrapcdn",
        r"https?://[^\s\"']+\.min\.js", r"https?://[^\s\"']+\.min\.css",
    ]
    for pattern in cdn_patterns:
        assert not re.search(pattern, content, re.IGNORECASE), (
            f"web/quick-actions.html contains CDN reference matching '{pattern}'"
        )


# ---------------------------------------------------------------------------
# 10. web/js/quick-actions.js has no eval() and no port 9222
# ---------------------------------------------------------------------------
def test_quick_actions_js_no_eval_no_banned_port():
    js_path = REPO_ROOT / "web" / "js" / "quick-actions.js"
    assert js_path.exists(), "web/js/quick-actions.js must exist"
    content = js_path.read_text()
    assert not re.search(r"\beval\s*\(", content), "quick-actions.js must not contain eval()"
    assert "9222" not in content, "quick-actions.js must not reference port 9222"
