# Diagram: 05-solace-runtime-architecture
"""
test_mcp_server.py — Tests for yinyang_mcp_server.py (MCP 2024-11-05).
Donald Knuth law: every test is a proof. RED → GREEN gate.

Strategy: test handle_message() directly (no I/O) + mock HTTP calls.
Port under test: 8888 (yinyang_mcp_server calls localhost:8888 — never 9222).
"""
import json
import pathlib
import sys
import unittest.mock

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_mcp_server as mcp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _call(method: str, params: dict = None, req_id: int = 1) -> dict:
    """Build an MCP JSON-RPC message and call handle_message with no token."""
    msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
    if params is not None:
        msg["params"] = params
    return mcp.handle_message(msg, token_sha256="")


# ---------------------------------------------------------------------------
# MCP tool tests
# ---------------------------------------------------------------------------
class TestMCPInitialize:
    def test_initialize_returns_protocol_version(self):
        """initialize → protocolVersion must be '2024-11-05'."""
        resp = _call("initialize", {})
        assert resp["result"]["protocolVersion"] == "2024-11-05"

    def test_initialize_has_server_info(self):
        """initialize → serverInfo.name == 'yinyang-mcp'."""
        resp = _call("initialize", {})
        assert resp["result"]["serverInfo"]["name"] == "yinyang-mcp"

    def test_initialize_has_capabilities(self):
        """initialize → capabilities has tools and resources keys."""
        resp = _call("initialize", {})
        caps = resp["result"]["capabilities"]
        assert "tools" in caps
        assert "resources" in caps


class TestMCPToolsList:
    def test_tools_list_returns_21_tools(self):
        """tools/list → exactly 21 tools defined."""
        resp = _call("tools/list")
        tools = resp["result"]["tools"]
        assert len(tools) == 21

    def test_tools_list_tool_names(self):
        """tools/list → all expected tool names present."""
        resp = _call("tools/list")
        names = {t["name"] for t in resp["result"]["tools"]}
        expected = {
            "detect_apps", "list_apps", "create_schedule", "list_schedules",
            "delete_schedule", "record_evidence", "list_evidence", "get_hub_status",
            "hub_status", "hub_windows", "hub_accessibility", "hub_screenshot", "hub_action",
            "browser_status", "browser_open", "browser_close", "browser_navigate",
            "browser_click", "browser_fill", "browser_evaluate", "browser_screenshot",
        }
        assert names == expected

    def test_tools_list_have_input_schema(self):
        """tools/list → every tool has inputSchema."""
        resp = _call("tools/list")
        for tool in resp["result"]["tools"]:
            assert "inputSchema" in tool, f"Tool {tool['name']!r} missing inputSchema"


class TestMCPToolsCall:
    def test_detect_apps_dispatches_to_post_detect(self):
        """tools/call detect_apps → calls POST /detect."""
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (200, {"apps": ["gmail-inbox-triage"]})
            resp = _call("tools/call", {
                "name": "detect_apps",
                "arguments": {"url": "https://mail.google.com/"},
            })
        mock_post.assert_called_once_with(
            "/detect", {"url": "https://mail.google.com/"}, ""
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content == ["gmail-inbox-triage"]

    def test_list_apps_dispatches_to_get_credits(self):
        """tools/call list_apps → calls GET /credits."""
        with unittest.mock.patch.object(mcp, "_http_get") as mock_get:
            mock_get.return_value = {"apps": ["gmail-inbox-triage", "linkedin-poster"]}
            resp = _call("tools/call", {"name": "list_apps", "arguments": {}})
        mock_get.assert_called_once_with("/credits", "")
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "gmail-inbox-triage" in content

    def test_create_schedule_dispatches_correctly(self):
        """tools/call create_schedule → calls POST /api/v1/browser/schedules."""
        fake_record = {"id": "abc123", "app_id": "gmail-inbox-triage", "cron": "0 9 * * 1-5"}
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (201, fake_record)
            resp = _call("tools/call", {
                "name": "create_schedule",
                "arguments": {
                    "app_id": "gmail-inbox-triage",
                    "cron": "0 9 * * 1-5",
                    "url": "https://mail.google.com/",
                },
            })
        mock_post.assert_called_once_with(
            "/api/v1/browser/schedules",
            {"app_id": "gmail-inbox-triage", "cron": "0 9 * * 1-5", "url": "https://mail.google.com/"},
            "",
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["id"] == "abc123"

    def test_list_schedules_dispatches_correctly(self):
        """tools/call list_schedules → calls GET /api/v1/browser/schedules."""
        with unittest.mock.patch.object(mcp, "_http_get") as mock_get:
            mock_get.return_value = {"schedules": [{"id": "s1"}]}
            resp = _call("tools/call", {"name": "list_schedules", "arguments": {}})
        mock_get.assert_called_once_with("/api/v1/browser/schedules", "")
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content[0]["id"] == "s1"

    def test_delete_schedule_dispatches_correctly(self):
        """tools/call delete_schedule → calls DELETE /api/v1/browser/schedules/{id}."""
        with unittest.mock.patch.object(mcp, "_http_delete") as mock_del:
            mock_del.return_value = (200, {"deleted": "sched-99"})
            resp = _call("tools/call", {
                "name": "delete_schedule",
                "arguments": {"schedule_id": "sched-99"},
            })
        mock_del.assert_called_once_with("/api/v1/browser/schedules/sched-99", "")
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content is True

    def test_record_evidence_dispatches_correctly(self):
        """tools/call record_evidence → calls POST /api/v1/evidence."""
        fake_record = {"id": "ev1", "type": "mcp_test", "ts": 1000, "data": {}}
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (201, fake_record)
            resp = _call("tools/call", {
                "name": "record_evidence",
                "arguments": {"type": "mcp_test", "data": {"x": 1}},
            })
        mock_post.assert_called_once_with(
            "/api/v1/evidence",
            {"type": "mcp_test", "data": {"x": 1}},
            "",
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["id"] == "ev1"

    def test_list_evidence_dispatches_with_pagination(self):
        """tools/call list_evidence → calls GET /api/v1/evidence with limit/offset."""
        with unittest.mock.patch.object(mcp, "_http_get") as mock_get:
            mock_get.return_value = {"total": 5, "records": [], "limit": 10, "offset": 0}
            resp = _call("tools/call", {
                "name": "list_evidence",
                "arguments": {"limit": 10, "offset": 0},
            })
        mock_get.assert_called_once_with("/api/v1/evidence?limit=10&offset=0", "")
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "total" in content

    def test_get_hub_status_dispatches_correctly(self):
        """tools/call get_hub_status → calls GET /health."""
        with unittest.mock.patch.object(mcp, "_http_get") as mock_get:
            mock_get.return_value = {"status": "ok", "apps": 34, "version": "1.1"}
            resp = _call("tools/call", {"name": "get_hub_status", "arguments": {}})
        mock_get.assert_called_once_with("/health", "")
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["status"] == "ok"

    def test_browser_status_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_get") as mock_get:
            mock_get.return_value = {"tracked_session_count": 1, "browser_visible": True}
            resp = _call("tools/call", {"name": "browser_status", "arguments": {}})
        mock_get.assert_called_once_with("/api/v1/browser/status", "")
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["tracked_session_count"] == 1

    def test_hub_status_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_get") as mock_get:
            mock_get.return_value = {"status": "ok", "hub_visible": True}
            resp = _call("tools/call", {"name": "hub_status", "arguments": {}})
        mock_get.assert_called_once_with("/api/v1/hub/status", "")
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["hub_visible"] is True

    def test_hub_windows_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_get") as mock_get:
            mock_get.return_value = {"status": "ok", "windows": [{"title": "Solace Hub"}]}
            resp = _call("tools/call", {"name": "hub_windows", "arguments": {}})
        mock_get.assert_called_once_with("/api/v1/hub/windows", "")
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["windows"][0]["title"] == "Solace Hub"

    def test_hub_accessibility_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_get") as mock_get:
            mock_get.return_value = {"status": "ok", "root": {"name": "solace-hub"}}
            resp = _call("tools/call", {"name": "hub_accessibility", "arguments": {}})
        mock_get.assert_called_once_with("/api/v1/hub/accessibility", "")
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["root"]["name"] == "solace-hub"

    def test_hub_screenshot_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (200, {"status": "ok", "filename": "hub.png"})
            resp = _call("tools/call", {"name": "hub_screenshot", "arguments": {"filename": "hub.png"}})
        mock_post.assert_called_once_with(
            "/api/v1/hub/screenshot",
            {"filename": "hub.png"},
            "",
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["filename"] == "hub.png"

    def test_hub_action_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (200, {"status": "ok", "name": "Open Solace Browser"})
            resp = _call(
                "tools/call",
                {"name": "hub_action", "arguments": {"name": "Open Solace Browser", "action": "click", "role": "push button"}},
            )
        mock_post.assert_called_once_with(
            "/api/v1/hub/action",
            {"name": "Open Solace Browser", "action": "click", "role": "push button"},
            "",
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["name"] == "Open Solace Browser"

    def test_browser_open_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (201, {"session_id": "sess-1"})
            resp = _call(
                "tools/call",
                {
                    "name": "browser_open",
                    "arguments": {
                        "url": "http://127.0.0.1:8888/agents",
                        "profile": "default",
                        "mode": "standard",
                        "session_name": "QA",
                        "head_hidden": False,
                    },
                },
            )
        mock_post.assert_called_once_with(
            "/api/v1/hub/browser/open",
            {
                "url": "http://127.0.0.1:8888/agents",
                "profile": "default",
                "mode": "standard",
                "session_name": "QA",
                "head_hidden": False,
            },
            "",
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["session_id"] == "sess-1"

    def test_browser_close_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (200, {"status": "terminated"})
            resp = _call("tools/call", {"name": "browser_close", "arguments": {"session_id": "sess-1"}})
        mock_post.assert_called_once_with(
            "/api/v1/hub/browser/close",
            {"session_id": "sess-1", "all": False},
            "",
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["status"] == "terminated"

    def test_browser_navigate_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (200, {"success": True, "url": "http://127.0.0.1:8888/agents"})
            resp = _call(
                "tools/call",
                {"name": "browser_navigate", "arguments": {"session_id": "sess-1", "url": "http://127.0.0.1:8888/agents"}},
            )
        mock_post.assert_called_once_with(
            "/api/navigate",
            {"session_id": "sess-1", "url": "http://127.0.0.1:8888/agents"},
            "",
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["success"] is True

    def test_browser_click_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (200, {"success": True, "selector": "#confirm"})
            resp = _call("tools/call", {"name": "browser_click", "arguments": {"session_id": "sess-1", "selector": "#confirm"}})
        mock_post.assert_called_once_with(
            "/api/click",
            {"session_id": "sess-1", "selector": "#confirm"},
            "",
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["selector"] == "#confirm"

    def test_browser_fill_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (200, {"success": True, "text": "user@example.com"})
            resp = _call(
                "tools/call",
                {"name": "browser_fill", "arguments": {"session_id": "sess-1", "selector": "#email", "text": "user@example.com"}},
            )
        mock_post.assert_called_once_with(
            "/api/fill",
            {"session_id": "sess-1", "selector": "#email", "text": "user@example.com"},
            "",
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["text"] == "user@example.com"

    def test_browser_evaluate_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (200, {"success": True, "result": "Solace Agents"})
            resp = _call(
                "tools/call",
                {"name": "browser_evaluate", "arguments": {"session_id": "sess-1", "expression": "document.title"}},
            )
        mock_post.assert_called_once_with(
            "/api/evaluate",
            {"session_id": "sess-1", "expression": "document.title"},
            "",
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["result"] == "Solace Agents"

    def test_browser_screenshot_dispatches_correctly(self):
        with unittest.mock.patch.object(mcp, "_http_post") as mock_post:
            mock_post.return_value = (200, {"capture": {"filepath": "/tmp/proof.png"}})
            resp = _call(
                "tools/call",
                {
                    "name": "browser_screenshot",
                    "arguments": {"session_id": "sess-1", "filename": "proof.png", "full_page": True},
                },
            )
        mock_post.assert_called_once_with(
            "/api/screenshot",
            {"session_id": "sess-1", "filename": "proof.png", "full_page": True},
            "",
        )
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["capture"]["filepath"] == "/tmp/proof.png"


class TestMCPResourcesList:
    def test_resources_list_returns_2_resources(self):
        """resources/list → exactly 2 resources."""
        resp = _call("resources/list")
        resources = resp["result"]["resources"]
        assert len(resources) == 2

    def test_resources_list_uris(self):
        """resources/list → expected URIs present."""
        resp = _call("resources/list")
        uris = {r["uri"] for r in resp["result"]["resources"]}
        assert "solace://apps" in uris
        assert "solace://health" in uris


class TestMCPResourcesRead:
    def test_resources_read_apps(self):
        """resources/read solace://apps → returns app list."""
        with unittest.mock.patch.object(mcp, "_http_get") as mock_get:
            mock_get.return_value = {"apps": ["gmail-inbox-triage"]}
            resp = _call("resources/read", {"uri": "solace://apps"})
        contents = resp["result"]["contents"]
        assert len(contents) == 1
        assert contents[0]["uri"] == "solace://apps"
        parsed = json.loads(contents[0]["text"])
        assert "apps" in parsed

    def test_resources_read_health(self):
        """resources/read solace://health → returns hub status."""
        with unittest.mock.patch.object(mcp, "_http_get") as mock_get:
            mock_get.return_value = {"status": "ok", "apps": 34}
            resp = _call("resources/read", {"uri": "solace://health"})
        contents = resp["result"]["contents"]
        parsed = json.loads(contents[0]["text"])
        assert parsed["status"] == "ok"


class TestMCPUnknownMethod:
    def test_unknown_method_returns_error_32601(self):
        """Unknown method → error code -32601 Method not found."""
        resp = _call("nonexistent/method")
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_unknown_tool_returns_error_info(self):
        """tools/call with unknown tool name → error info in content."""
        resp = _call("tools/call", {"name": "nonexistent_tool", "arguments": {}})
        content = json.loads(resp["result"]["content"][0]["text"])
        assert "error" in content


class TestMCPPortSecurity:
    def test_hub_base_uses_port_8888(self):
        """_HUB_BASE must reference port 8888, never 9222."""
        assert "8888" in mcp._HUB_BASE
        assert "9222" not in mcp._HUB_BASE

    def test_hub_port_constant(self):
        """_HUB_PORT must be 8888."""
        assert mcp._HUB_PORT == 8888
