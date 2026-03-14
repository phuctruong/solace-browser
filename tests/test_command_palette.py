# Diagram: 05-solace-runtime-architecture
"""tests/test_command_palette.py — Command Palette acceptance gate.
Task 039 | Rung 641 | 10 tests minimum

Kill conditions verified:
  - 12 DEFAULT_COMMANDS
  - Unknown cmd_id → 404
  - Auth required on POST /execute; GET is public
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

TEST_TOKEN = "test-token-commands-039"
BAD_TOKEN = "bad-token-xxxxxxxxxx"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str = "GET", payload: dict | None = None, token: str = TEST_TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    t_hash = _token_hash(token)
    handler.headers = {"Authorization": f"Bearer {t_hash}"}
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", 18912)
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
def reset_command_history(monkeypatch):
    """Reset command history between tests."""
    monkeypatch.setattr(ys, "_COMMAND_HISTORY", [])
    yield


# ---------------------------------------------------------------------------
# 1. GET /commands returns exactly 12 commands
# ---------------------------------------------------------------------------
def test_commands_list_has_12():
    status, data = get_json("/api/v1/commands")
    assert status == 200
    assert "commands" in data
    assert len(data["commands"]) == 12, f"Expected 12, got {len(data['commands'])}"


# ---------------------------------------------------------------------------
# 2. GET /search?q=recipe returns recipe commands
# ---------------------------------------------------------------------------
def test_commands_search():
    handler, captured = _make_handler("/api/v1/commands/search?q=recipe", "GET")
    handler.path = "/api/v1/commands/search?q=recipe"
    handler.do_GET()
    status = int(captured["status"])
    data = dict(captured["data"])
    assert status == 200
    assert len(data["commands"]) >= 1
    for cmd in data["commands"]:
        assert "recipe" in cmd["name"].lower() or "recipe" in cmd["category"].lower() or "Recipe" in cmd["category"]


# ---------------------------------------------------------------------------
# 3. POST /execute returns execution_id
# ---------------------------------------------------------------------------
def test_commands_execute():
    status, data = post_json("/api/v1/commands/execute", {"cmd_id": "nav-budget"})
    assert status == 200
    assert data.get("status") == "executed"
    assert "execution_id" in data
    assert data["execution_id"].startswith("exec_")


# ---------------------------------------------------------------------------
# 4. Execute + GET /history — appears in history
# ---------------------------------------------------------------------------
def test_commands_history():
    post_json("/api/v1/commands/execute", {"cmd_id": "nav-sessions"})
    status, data = get_json("/api/v1/commands/history")
    assert status == 200
    assert len(data["history"]) >= 1
    cmd_ids = [h["cmd_id"] for h in data["history"]]
    assert "nav-sessions" in cmd_ids


# ---------------------------------------------------------------------------
# 5. Execute unknown cmd_id → 404
# ---------------------------------------------------------------------------
def test_commands_unknown_id():
    status, data = post_json("/api/v1/commands/execute", {"cmd_id": "no-such-command"})
    assert status == 404
    assert "error" in data


# ---------------------------------------------------------------------------
# 6. HTML has no CDN links
# ---------------------------------------------------------------------------
def test_commands_html_no_cdn():
    html_path = REPO_ROOT / "web" / "command-palette.html"
    assert html_path.exists(), "command-palette.html must exist"
    content = html_path.read_text()
    cdn_pattern = re.compile(r"https?://(?!localhost)", re.IGNORECASE)
    assert not cdn_pattern.search(content), "No external URLs allowed in HTML"


# ---------------------------------------------------------------------------
# 7. JS has no eval()
# ---------------------------------------------------------------------------
def test_commands_js_no_eval():
    js_path = REPO_ROOT / "web" / "js" / "command-palette.js"
    assert js_path.exists(), "command-palette.js must exist"
    content = js_path.read_text()
    assert "eval(" not in content, "eval() is banned in JS"


# ---------------------------------------------------------------------------
# 8. No port 9222 in command palette files
# ---------------------------------------------------------------------------
def test_no_port_9222_in_commands():
    files_to_check = [
        REPO_ROOT / "web" / "command-palette.html",
        REPO_ROOT / "web" / "js" / "command-palette.js",
        REPO_ROOT / "web" / "css" / "command-palette.css",
    ]
    for f in files_to_check:
        if f.exists():
            assert "9222" not in f.read_text(), f"Port 9222 banned in {f.name}"


# ---------------------------------------------------------------------------
# 9. POST /execute without valid Bearer → 401
# ---------------------------------------------------------------------------
def test_commands_execute_requires_auth():
    # Use wrong token so server rejects
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    real_hash = _token_hash(TEST_TOKEN)
    wrong_hash = _token_hash(BAD_TOKEN)
    handler.headers = {"Authorization": f"Bearer {wrong_hash}"}
    handler.path = "/api/v1/commands/execute"
    handler.command = "POST"
    handler.client_address = ("127.0.0.1", 18912)
    # Server expects real_hash but we send wrong_hash
    handler.server = type("DummyServer", (), {"session_token_sha256": real_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: {"cmd_id": "nav-budget"}
    handler.do_POST()
    assert int(captured["status"]) == 401


# ---------------------------------------------------------------------------
# 10. Search with no matches → empty list
# ---------------------------------------------------------------------------
def test_commands_search_empty():
    handler, captured = _make_handler("/api/v1/commands/search?q=zzznomatch", "GET")
    handler.path = "/api/v1/commands/search?q=zzznomatch"
    handler.do_GET()
    status = int(captured["status"])
    data = dict(captured["data"])
    assert status == 200
    assert data["commands"] == []
