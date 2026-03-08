"""
MCP Server for Solace Browser — Dynamic App-to-Tool Mapping.

Runs in the companion app process alongside the webservice.
Supports stdio transport (local agents) and SSE (remote/tunnel).

Usage:
    # stdio mode (for Claude Code, Codex):
    solace-browser mcp

    # SSE mode (via webservice):
    GET /mcp/sse on port 9222

Paper: 47 Section 24 | Auth: 65537
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, TextIO

from mcp.tools_core import core_tool_definitions, ACT_TYPE_MAP
from mcp.tools_apps import AppToolGenerator
from mcp.tools_evidence import evidence_tool_definitions
from mcp.oauth3_gate import check_scope, MCPScopeError

logger = logging.getLogger(__name__)

# MCP Protocol version
MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "solace-browser"
SERVER_VERSION = "1.0.0"


class SolaceMCPServer:
    """MCP server with dynamic tool generation from app manifests.

    Two interfaces, one brain: MCP and webservice share the same handler code.
    """

    def __init__(
        self,
        apps_dir: Path | None = None,
        granted_scopes: frozenset[str] | None = None,
    ) -> None:
        self.app_tools = AppToolGenerator(apps_dir)
        self.granted_scopes = granted_scopes  # None = local mode (all allowed)
        self._tool_index: dict[str, dict[str, Any]] = {}

    def _build_tool_index(self) -> dict[str, dict[str, Any]]:
        """Build index of all tools for fast lookup."""
        tools = self.get_all_tools()
        return {t["name"]: t for t in tools}

    def get_all_tools(self) -> list[dict[str, Any]]:
        """Get all available MCP tools: core + dynamic apps + evidence."""
        tools = []
        tools.extend(core_tool_definitions())
        tools.extend(self.app_tools.generate_tools())
        tools.extend(evidence_tool_definitions())
        return tools

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get tool schemas for MCP tools/list response (without internal fields)."""
        tools = self.get_all_tools()
        schemas = []
        for tool in tools:
            schema = {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["inputSchema"],
            }
            schemas.append(schema)
        return schemas

    def handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle MCP initialize request."""
        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": True},
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
            },
        }

    def handle_tools_list(self) -> dict[str, Any]:
        """Handle MCP tools/list request."""
        return {"tools": self.get_tool_schemas()}

    def handle_tools_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle MCP tools/call request.

        Routes to the appropriate handler based on tool name.
        In production, this calls the actual browser_server methods.
        For now, returns the routing info for the handler to execute.
        """
        if not self._tool_index:
            self._tool_index = self._build_tool_index()

        tool = self._tool_index.get(name)
        if tool is None:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                "isError": True,
            }

        # OAuth3 scope check
        try:
            check_scope(tool, self.granted_scopes)
        except MCPScopeError as exc:
            return {
                "content": [{"type": "text", "text": str(exc)}],
                "isError": True,
            }

        # Route to handler
        handler = tool.get("_handler", "")
        app_id = tool.get("_app_id")

        # Build the handler dispatch info
        dispatch = {
            "handler": handler,
            "arguments": arguments,
            "tool_name": name,
        }
        if app_id:
            dispatch["app_id"] = app_id

        # For act-type tools, add the action type
        if name in ACT_TYPE_MAP:
            dispatch["act_type"] = ACT_TYPE_MAP[name]

        return dispatch

    def handle_jsonrpc(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Handle a single JSON-RPC 2.0 message."""
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params", {})

        if method == "initialize":
            result = self.handle_initialize(params)
        elif method == "notifications/initialized":
            return None  # Notification, no response
        elif method == "tools/list":
            result = self.handle_tools_list()
        elif method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = self.handle_tools_call(name, arguments)
        elif method == "ping":
            result = {}
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        if msg_id is not None:
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        return None

    def run_stdio(
        self,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
    ) -> None:
        """Run MCP server on stdio transport.

        Reads JSON-RPC messages from stdin, writes responses to stdout.
        Used by Claude Code, Codex, and other MCP clients.
        """
        _stdin = stdin or sys.stdin
        _stdout = stdout or sys.stdout

        logger.info("MCP server starting on stdio transport")

        for line in _stdin:
            line = line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                error_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {exc}"},
                }
                _stdout.write(json.dumps(error_resp) + "\n")
                _stdout.flush()
                continue

            response = self.handle_jsonrpc(message)
            if response is not None:
                _stdout.write(json.dumps(response) + "\n")
                _stdout.flush()

        logger.info("MCP server stdio transport closed")
