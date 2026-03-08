"""
Tests for MCP Server — Dynamic App-to-Tool Mapping.

Covers:
  - Core tool definitions (count, schema, names)
  - Dynamic app tool generation from manifests
  - Tool cache invalidation on manifest change
  - OAuth3 scope gating
  - JSON-RPC protocol handling
  - Trade secret boundary enforcement
  - stdio transport

Paper: 47 Section 24 | Auth: 65537
Tests: 28
"""
from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from solace_mcp.tools_core import core_tool_definitions, ACT_TYPE_MAP
from solace_mcp.tools_apps import AppToolGenerator, _safe_tool_name
from solace_mcp.tools_evidence import evidence_tool_definitions
from solace_mcp.oauth3_gate import check_scope, MCPScopeError, requires_step_up
from solace_mcp.server import SolaceMCPServer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_apps_dir(tmp_path):
    """Create a temp apps directory with test manifests."""
    app1_dir = tmp_path / "test-app-one"
    app1_dir.mkdir()
    (app1_dir / "manifest.yaml").write_text(
        "id: test-app-one\n"
        "name: Test App One\n"
        "description: A test application for email triage.\n"
        "site: mail.example.com\n"
        "category: communications\n"
        "tier: free\n"
    )

    app2_dir = tmp_path / "another-app"
    app2_dir.mkdir()
    (app2_dir / "manifest.yaml").write_text(
        "id: another-app\n"
        "name: Another App\n"
        "description: Another test application.\n"
        "site: example.com\n"
    )
    return tmp_path


@pytest.fixture
def mcp_server(temp_apps_dir):
    """Create an MCP server with test apps."""
    return SolaceMCPServer(apps_dir=temp_apps_dir)


# ---------------------------------------------------------------------------
# Core Tools
# ---------------------------------------------------------------------------

class TestCoreTools:
    def test_core_tools_count(self):
        tools = core_tool_definitions()
        assert len(tools) >= 10, f"Expected at least 10 core tools, got {len(tools)}"

    def test_core_tools_have_required_fields(self):
        for tool in core_tool_definitions():
            assert "name" in tool, f"Tool missing name"
            assert "description" in tool, f"Tool {tool.get('name')} missing description"
            assert "inputSchema" in tool, f"Tool {tool.get('name')} missing inputSchema"
            assert tool["name"].startswith("solace_"), f"Tool name must start with 'solace_': {tool['name']}"

    def test_core_tools_names_unique(self):
        names = [t["name"] for t in core_tool_definitions()]
        assert len(names) == len(set(names)), "Duplicate core tool names"

    def test_navigate_tool_requires_url(self):
        tools = {t["name"]: t for t in core_tool_definitions()}
        nav = tools["solace_navigate"]
        assert "url" in nav["inputSchema"]["properties"]
        assert "url" in nav["inputSchema"]["required"]

    def test_act_type_map_has_entries(self):
        assert "solace_click" in ACT_TYPE_MAP
        assert "solace_type" in ACT_TYPE_MAP
        assert "solace_scroll" in ACT_TYPE_MAP


# ---------------------------------------------------------------------------
# Dynamic App Tools
# ---------------------------------------------------------------------------

class TestAppTools:
    def test_safe_tool_name(self):
        assert _safe_tool_name("gmail-inbox-triage") == "gmail_inbox_triage"
        assert _safe_tool_name("test.app") == "test_app"
        assert _safe_tool_name("My App!") == "my_app_"

    def test_generates_tools_from_manifests(self, temp_apps_dir):
        gen = AppToolGenerator(temp_apps_dir)
        tools = gen.generate_tools()
        # Each app generates 3 tools: run, benchmarks, status
        assert len(tools) == 6, f"Expected 6 tools (2 apps × 3), got {len(tools)}"

    def test_tool_names_include_app_id(self, temp_apps_dir):
        gen = AppToolGenerator(temp_apps_dir)
        tools = gen.generate_tools()
        names = [t["name"] for t in tools]
        assert "solace_app_test_app_one_run" in names
        assert "solace_app_test_app_one_benchmarks" in names
        assert "solace_app_test_app_one_status" in names
        assert "solace_app_another_app_run" in names

    def test_cache_is_used(self, temp_apps_dir):
        gen = AppToolGenerator(temp_apps_dir)
        tools1 = gen.generate_tools()
        tools2 = gen.generate_tools()
        assert tools1 == tools2

    def test_cache_invalidated_on_manifest_change(self, temp_apps_dir):
        gen = AppToolGenerator(temp_apps_dir)
        tools1 = gen.generate_tools()
        assert len(tools1) == 6

        # Add a new app
        app3_dir = temp_apps_dir / "new-app"
        app3_dir.mkdir()
        (app3_dir / "manifest.yaml").write_text(
            "id: new-app\nname: New App\ndescription: Brand new.\n"
        )

        # Cache should be invalidated
        tools2 = gen.generate_tools()
        assert len(tools2) == 9, f"Expected 9 tools (3 apps × 3), got {len(tools2)}"

    def test_get_app_ids(self, temp_apps_dir):
        gen = AppToolGenerator(temp_apps_dir)
        ids = gen.get_app_ids()
        assert "test-app-one" in ids
        assert "another-app" in ids

    def test_empty_apps_dir(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        gen = AppToolGenerator(empty_dir)
        assert gen.generate_tools() == []

    def test_nonexistent_apps_dir(self, tmp_path):
        gen = AppToolGenerator(tmp_path / "nonexistent")
        assert gen.generate_tools() == []


# ---------------------------------------------------------------------------
# Evidence Tools
# ---------------------------------------------------------------------------

class TestEvidenceTools:
    def test_evidence_tools_count(self):
        tools = evidence_tool_definitions()
        assert len(tools) >= 2

    def test_evidence_tools_have_scopes(self):
        for tool in evidence_tool_definitions():
            assert "_scope" in tool
            assert "_handler" in tool


# ---------------------------------------------------------------------------
# OAuth3 Gate
# ---------------------------------------------------------------------------

class TestOAuth3Gate:
    def test_no_scope_required_passes(self):
        tool = {"name": "solace_health", "_scope": None}
        assert check_scope(tool, frozenset()) is True

    def test_scope_granted_passes(self):
        tool = {"name": "solace_navigate", "_scope": "browser.navigate"}
        assert check_scope(tool, frozenset({"browser.navigate"})) is True

    def test_scope_missing_raises(self):
        tool = {"name": "solace_navigate", "_scope": "browser.navigate"}
        with pytest.raises(MCPScopeError) as exc_info:
            check_scope(tool, frozenset())
        assert "browser.navigate" in str(exc_info.value)

    def test_local_mode_all_allowed(self):
        tool = {"name": "solace_navigate", "_scope": "browser.navigate"}
        assert check_scope(tool, None) is True  # None = local mode

    def test_requires_step_up_low_risk(self):
        tool = {"_scope": "browser.navigate"}
        assert requires_step_up(tool) is False

    def test_requires_step_up_no_scope(self):
        tool = {"_scope": None}
        assert requires_step_up(tool) is False


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

class TestMCPServer:
    def test_get_all_tools_includes_core_and_apps(self, mcp_server):
        tools = mcp_server.get_all_tools()
        names = [t["name"] for t in tools]
        # Core tools
        assert "solace_navigate" in names
        assert "solace_screenshot" in names
        # App tools
        assert "solace_app_test_app_one_run" in names
        # Evidence tools
        assert "solace_search_evidence" in names

    def test_get_tool_schemas_no_internal_fields(self, mcp_server):
        schemas = mcp_server.get_tool_schemas()
        for schema in schemas:
            assert "_handler" not in schema, f"Internal field leaked: {schema['name']}"
            assert "_scope" not in schema, f"Internal field leaked: {schema['name']}"
            assert "_app_id" not in schema, f"Internal field leaked: {schema['name']}"

    def test_handle_initialize(self, mcp_server):
        result = mcp_server.handle_initialize({})
        assert result["protocolVersion"] == "2024-11-05"
        assert "tools" in result["capabilities"]
        assert result["serverInfo"]["name"] == "solace-browser"

    def test_handle_tools_list(self, mcp_server):
        result = mcp_server.handle_tools_list()
        assert "tools" in result
        assert len(result["tools"]) > 10

    def test_handle_tools_call_unknown(self, mcp_server):
        result = mcp_server.handle_tools_call("nonexistent_tool", {})
        assert result.get("isError") is True

    def test_handle_tools_call_routes_correctly(self, mcp_server):
        result = mcp_server.handle_tools_call("solace_navigate", {"url": "https://example.com"})
        assert result["handler"] == "navigate"
        assert result["arguments"]["url"] == "https://example.com"

    def test_handle_tools_call_app_includes_app_id(self, mcp_server):
        result = mcp_server.handle_tools_call("solace_app_test_app_one_run", {"model": "solace_managed"})
        assert result["handler"] == "app_run"
        assert result["app_id"] == "test-app-one"

    def test_handle_jsonrpc_initialize(self, mcp_server):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = mcp_server.handle_jsonrpc(msg)
        assert resp["id"] == 1
        assert "protocolVersion" in resp["result"]

    def test_handle_jsonrpc_notification_no_response(self, mcp_server):
        msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp = mcp_server.handle_jsonrpc(msg)
        assert resp is None

    def test_handle_jsonrpc_unknown_method(self, mcp_server):
        msg = {"jsonrpc": "2.0", "id": 99, "method": "nonexistent"}
        resp = mcp_server.handle_jsonrpc(msg)
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_stdio_transport(self, mcp_server):
        """Test full stdio round-trip: init → tools/list → tools/call."""
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
                "name": "solace_health", "arguments": {}
            }},
        ]
        stdin = io.StringIO("\n".join(json.dumps(m) for m in messages) + "\n")
        stdout = io.StringIO()

        mcp_server.run_stdio(stdin=stdin, stdout=stdout)

        stdout.seek(0)
        responses = [json.loads(line) for line in stdout.readlines() if line.strip()]
        assert len(responses) == 3
        assert responses[0]["id"] == 1
        assert responses[1]["id"] == 2
        assert len(responses[1]["result"]["tools"]) > 10
        assert responses[2]["id"] == 3


# ---------------------------------------------------------------------------
# Trade Secret Boundary
# ---------------------------------------------------------------------------

class TestTradeSecretBoundary:
    def test_no_tool_leaks_trade_secrets(self, mcp_server):
        """Tool schemas must not contain trade secret references."""
        schemas = mcp_server.get_tool_schemas()
        text = json.dumps(schemas)
        forbidden = [
            "uplift_stack", "injection_content", "principle_weight",
            "prompt_template", "persona_routing", "interaction_matrix",
            "P13 ", "P16 ", "P22 ",
        ]
        for term in forbidden:
            assert term not in text, f"Trade secret term '{term}' found in tool schemas"
