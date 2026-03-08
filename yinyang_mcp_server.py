#!/usr/bin/env python3
"""
yinyang_mcp_server.py — MCP 2024-11-05 server for Solace Hub.
Transport: stdio (stdin/stdout JSON-RPC). No new dependencies.
Routes: calls yinyang_server.py HTTP endpoints at localhost:8888.
Auth: 65537 | Port: 8888 ONLY.

Stdlib only: json, sys, http.client, urllib.request, urllib.error, argparse.

MCP protocol (2024-11-05):
  initialize    → server info + capabilities
  tools/list    → 8 tool definitions
  tools/call    → dispatch to HTTP endpoint at localhost:8888
  resources/list → 2 resources
  resources/read → resource content from HTTP

Security:
  - Port 8888 ONLY — never 9222 (permanently banned)
  - Bearer token passed via --token-sha256 argument (sha256 of token, never plaintext)
  - FALLBACK BAN: catch only http.client.HTTPException, OSError, urllib.error.URLError
"""

import argparse
import http.client
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MCP_PROTOCOL_VERSION = "2024-11-05"
_SERVER_NAME = "yinyang-mcp"
_SERVER_VERSION = "1.0"
_HUB_PORT = 8888  # ONLY valid port — 9222 is permanently banned
_HUB_BASE = f"http://localhost:{_HUB_PORT}"

# ---------------------------------------------------------------------------
# HTTP helpers — all calls go to localhost:8888
# ---------------------------------------------------------------------------

def _http_get(path: str, token_sha256: str = "") -> dict:
    """GET localhost:8888{path}, return parsed JSON."""
    req = urllib.request.Request(f"{_HUB_BASE}{path}")
    if token_sha256:
        req.add_header("Authorization", f"Bearer {token_sha256}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        return {"error": f"hub unreachable: {exc}"}


def _http_post(path: str, payload: dict, token_sha256: str = "") -> tuple[int, dict]:
    """POST localhost:8888{path}, return (status_code, parsed JSON)."""
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{_HUB_BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token_sha256:
        req.add_header("Authorization", f"Bearer {token_sha256}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        if hasattr(exc, "code") and hasattr(exc, "read"):
            try:
                return exc.code, json.loads(exc.read().decode())
            except (json.JSONDecodeError, OSError):
                return exc.code, {"error": str(exc)}
        return 503, {"error": f"hub unreachable: {exc}"}


def _http_delete(path: str, token_sha256: str = "") -> tuple[int, dict]:
    """DELETE localhost:8888{path}, return (status_code, parsed JSON)."""
    req = urllib.request.Request(f"{_HUB_BASE}{path}", method="DELETE")
    if token_sha256:
        req.add_header("Authorization", f"Bearer {token_sha256}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        if hasattr(exc, "code") and hasattr(exc, "read"):
            try:
                return exc.code, json.loads(exc.read().decode())
            except (json.JSONDecodeError, OSError):
                return exc.code, {"error": str(exc)}
        return 503, {"error": f"hub unreachable: {exc}"}


# ---------------------------------------------------------------------------
# Tool definitions — 8 tools
# ---------------------------------------------------------------------------
_TOOL_DEFINITIONS = [
    {
        "name": "detect_apps",
        "description": "Detect which Solace apps are available for a given URL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The page URL to detect apps for."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "list_apps",
        "description": "List all apps loaded in Solace Hub.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "create_schedule",
        "description": "Create a cron schedule for a Solace app. Requires bearer token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_id": {"type": "string", "description": "The app identifier (max 256 chars)."},
                "cron": {"type": "string", "description": "5-field cron expression e.g. '0 9 * * 1-5' (max 64 chars)."},
                "url": {"type": "string", "description": "Target URL for the scheduled run."},
            },
            "required": ["app_id", "cron"],
        },
    },
    {
        "name": "list_schedules",
        "description": "List all active schedules in Solace Hub.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "delete_schedule",
        "description": "Delete a schedule by ID. Requires bearer token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schedule_id": {"type": "string", "description": "The schedule UUID to delete."},
            },
            "required": ["schedule_id"],
        },
    },
    {
        "name": "record_evidence",
        "description": "Record an evidence event to the append-only evidence log. Requires bearer token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Event type (max 256 chars)."},
                "data": {"type": "object", "description": "Arbitrary event data."},
            },
            "required": ["type"],
        },
    },
    {
        "name": "list_evidence",
        "description": "List evidence records with pagination.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max records to return (default 50, max 200)."},
                "offset": {"type": "integer", "description": "Pagination offset (default 0)."},
            },
            "required": [],
        },
    },
    {
        "name": "get_hub_status",
        "description": "Get Solace Hub health status.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

# ---------------------------------------------------------------------------
# Resource definitions — 2 resources
# ---------------------------------------------------------------------------
_RESOURCE_DEFINITIONS = [
    {
        "uri": "solace://apps",
        "name": "Solace Apps",
        "description": "List of all apps loaded in Solace Hub.",
        "mimeType": "application/json",
    },
    {
        "uri": "solace://health",
        "name": "Hub Status",
        "description": "Current Solace Hub health and statistics.",
        "mimeType": "application/json",
    },
]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------
def _dispatch_tool(name: str, arguments: dict, token_sha256: str) -> Any:
    """Dispatch an MCP tools/call to the Yinyang Server HTTP endpoint."""
    if name == "detect_apps":
        url = arguments.get("url", "")
        _status, data = _http_post("/detect", {"url": url}, token_sha256)
        return data.get("apps", [])

    if name == "list_apps":
        data = _http_get("/credits", token_sha256)
        return data.get("apps", [])

    if name == "create_schedule":
        app_id = arguments.get("app_id", "")
        cron = arguments.get("cron", "")
        url = arguments.get("url", "")
        _status, data = _http_post(
            "/api/v1/browser/schedules",
            {"app_id": app_id, "cron": cron, "url": url},
            token_sha256,
        )
        return data

    if name == "list_schedules":
        data = _http_get("/api/v1/browser/schedules", token_sha256)
        return data.get("schedules", [])

    if name == "delete_schedule":
        schedule_id = arguments.get("schedule_id", "")
        _status, data = _http_delete(
            f"/api/v1/browser/schedules/{schedule_id}", token_sha256
        )
        return data.get("deleted") == schedule_id

    if name == "record_evidence":
        event_type = arguments.get("type", "")
        event_data = arguments.get("data", {})
        _status, data = _http_post(
            "/api/v1/evidence",
            {"type": event_type, "data": event_data},
            token_sha256,
        )
        return data

    if name == "list_evidence":
        limit = int(arguments.get("limit", 50))
        offset = int(arguments.get("offset", 0))
        data = _http_get(
            f"/api/v1/evidence?limit={limit}&offset={offset}", token_sha256
        )
        return data

    if name == "get_hub_status":
        return _http_get("/health", token_sha256)

    return {"error": f"unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Resource dispatch
# ---------------------------------------------------------------------------
def _dispatch_resource(uri: str, token_sha256: str) -> str:
    """Read a resource by URI, return JSON string."""
    if uri == "solace://apps":
        data = _http_get("/credits", token_sha256)
        return json.dumps(data)
    if uri == "solace://health":
        data = _http_get("/health", token_sha256)
        return json.dumps(data)
    return json.dumps({"error": f"unknown resource: {uri}"})


# ---------------------------------------------------------------------------
# MCP JSON-RPC message handling
# ---------------------------------------------------------------------------
def _make_result(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _make_error(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_message(msg: dict, token_sha256: str) -> dict:
    """Handle one MCP JSON-RPC message and return the response dict."""
    req_id = msg.get("id")
    method = msg.get("method", "")
    params = msg.get("params", {})

    if method == "initialize":
        return _make_result(req_id, {
            "protocolVersion": _MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {},
                "resources": {},
            },
            "serverInfo": {
                "name": _SERVER_NAME,
                "version": _SERVER_VERSION,
            },
        })

    if method == "tools/list":
        return _make_result(req_id, {"tools": _TOOL_DEFINITIONS})

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = _dispatch_tool(tool_name, arguments, token_sha256)
        return _make_result(req_id, {
            "content": [{"type": "text", "text": json.dumps(result)}],
        })

    if method == "resources/list":
        return _make_result(req_id, {"resources": _RESOURCE_DEFINITIONS})

    if method == "resources/read":
        uri = params.get("uri", "")
        content_text = _dispatch_resource(uri, token_sha256)
        return _make_result(req_id, {
            "contents": [{
                "uri": uri,
                "mimeType": "application/json",
                "text": content_text,
            }],
        })

    # Unknown method
    return _make_error(req_id, -32601, "Method not found")


# ---------------------------------------------------------------------------
# Main loop — read one JSON line from stdin, write one JSON line to stdout
# ---------------------------------------------------------------------------
def run_stdio_loop(token_sha256: str) -> None:
    """Read JSON-RPC messages from stdin line-by-line, write responses to stdout."""
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            msg = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            response = _make_error(None, -32700, f"Parse error: {exc}")
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue
        response = handle_message(msg, token_sha256)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yinyang MCP Server (stdio)")
    parser.add_argument(
        "--token-sha256",
        dest="token_sha256",
        default="",
        help="SHA-256 hex of Bearer token for Hub authentication (64 hex chars).",
    )
    args = parser.parse_args()
    run_stdio_loop(args.token_sha256)
