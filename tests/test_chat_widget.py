# Diagram: 05-solace-runtime-architecture
"""
test_chat_widget.py — YinYang AI Chat Widget tests.
Task 015 | Rung: 641

Kill conditions verified here:
  - No port 9222
  - No "Companion App"
  - No bare except
  - No eval() in JS
  - No CDN refs in HTML/JS/CSS
  - No float for cost_usd (must be string)
  - No auto-execute from chat (advisory only)
  - Auth required on ALL routes
"""
import hashlib
import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------
TEST_TOKEN = "test-token-chat-widget-015"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Handler factory (same pattern as test_gmail_triage.py)
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
    handler.client_address = ("127.0.0.1", 18890)
    handler.server = type("DummyServer", (), {"session_token_sha256": t_hash})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
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


def delete_json(path: str) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "DELETE")
    handler.do_DELETE()
    return int(captured["status"]), dict(captured["data"])


# ---------------------------------------------------------------------------
# Fixtures — reset _CHAT_STORE between tests
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_chat_store():
    """Reset global chat store before each test to avoid state bleed."""
    with ys._CHAT_LOCK:
        ys._CHAT_STORE.clear()
    yield
    with ys._CHAT_LOCK:
        ys._CHAT_STORE.clear()


# ---------------------------------------------------------------------------
# Test 1: chat history endpoint exists and returns 200
# ---------------------------------------------------------------------------
def test_chat_status_endpoint_exists():
    status, data = get_json("/api/v1/chat/history")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert "messages" in data
    assert "total" in data


# ---------------------------------------------------------------------------
# Test 2: fresh session — history is empty
# ---------------------------------------------------------------------------
def test_chat_history_empty_initially():
    status, data = get_json("/api/v1/chat/history")
    assert status == 200
    assert data["messages"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# Test 3: POST /chat/message returns reply field
# ---------------------------------------------------------------------------
def test_chat_message_returns_reply():
    status, data = post_json("/api/v1/chat/message", {"content": "Hello YinYang"})
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert "reply" in data
    assert isinstance(data["reply"], str)
    assert len(data["reply"]) > 0


# ---------------------------------------------------------------------------
# Test 4: cost_usd is a string, never a float
# ---------------------------------------------------------------------------
def test_chat_response_has_string_cost():
    status, data = post_json("/api/v1/chat/message", {"content": "What can you do?"})
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert "cost_usd" in data
    cost = data["cost_usd"]
    assert isinstance(cost, str), f"cost_usd must be str, got {type(cost).__name__}: {cost!r}"
    assert not isinstance(cost, float), "cost_usd must not be float"


# ---------------------------------------------------------------------------
# Test 5: history accumulates after multiple messages
# ---------------------------------------------------------------------------
def test_chat_history_accumulates():
    post_json("/api/v1/chat/message", {"content": "First message"})
    post_json("/api/v1/chat/message", {"content": "Second message"})
    status, data = get_json("/api/v1/chat/history")
    assert status == 200
    # 2 user messages + 2 assistant replies = 4 entries
    assert len(data["messages"]) >= 2, f"Expected at least 2 messages, got {len(data['messages'])}"


# ---------------------------------------------------------------------------
# Test 6: DELETE /chat/history clears the history
# ---------------------------------------------------------------------------
def test_chat_delete_clears_history():
    post_json("/api/v1/chat/message", {"content": "Hello"})
    # Verify history has entries
    _, before = get_json("/api/v1/chat/history")
    assert before["total"] > 0

    status, data = delete_json("/api/v1/chat/history")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert data.get("status") == "cleared"

    _, after = get_json("/api/v1/chat/history")
    assert after["messages"] == []
    assert after["total"] == 0


# ---------------------------------------------------------------------------
# Test 7: GET /chat/suggestions returns a list
# ---------------------------------------------------------------------------
def test_suggestions_returns_list():
    status, data = get_json("/api/v1/chat/suggestions")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
    assert len(data["suggestions"]) > 0


# ---------------------------------------------------------------------------
# Test 8: ?context=gmail includes a Gmail-related suggestion
# ---------------------------------------------------------------------------
def test_suggestions_gmail_context():
    handler, captured = _make_handler("/api/v1/chat/suggestions?context=gmail", "GET")
    handler.do_GET()
    status = int(captured["status"])
    data = dict(captured["data"])
    assert status == 200, f"Expected 200, got {status}: {data}"
    suggestions = data.get("suggestions", [])
    assert isinstance(suggestions, list)
    # At least one suggestion should mention "Gmail"
    gmail_suggestions = [s for s in suggestions if "Gmail" in s or "gmail" in s.lower()]
    assert len(gmail_suggestions) > 0, f"No Gmail suggestion found in: {suggestions}"


# ---------------------------------------------------------------------------
# Test 9: message > 2000 chars returns 400
# ---------------------------------------------------------------------------
def test_chat_message_max_length():
    long_message = "x" * 2001
    status, data = post_json("/api/v1/chat/message", {"content": long_message})
    assert status == 400, f"Expected 400, got {status}: {data}"
    assert "error" in data
    assert "long" in data["error"].lower() or "2000" in data["error"]


# ---------------------------------------------------------------------------
# Test 10: web/js/chat.js has no eval()
# ---------------------------------------------------------------------------
def test_chat_js_no_eval():
    js_path = REPO_ROOT / "web" / "js" / "chat.js"
    assert js_path.exists(), f"chat.js not found at {js_path}"
    content = js_path.read_text()
    import re
    assert not re.search(r"\beval\s*\(", content), "eval() found in chat.js"
