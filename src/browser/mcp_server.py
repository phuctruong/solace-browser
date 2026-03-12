#!/usr/bin/env python3
"""
Solace Browser MCP Server
Exposes browser automation tools via Model Context Protocol (stdio JSON-RPC 2.0).
Routes to yinyang-server.py at http://localhost:8888.

Usage:
  python3 mcp_server.py

CLAUDE.md config:
  {
    "mcpServers": {
      "solace": {
        "command": "python3",
        "args": ["/path/to/solace-browser/mcp_server.py"]
      }
    }
  }

Paper: papers/09-yinyang-tutorial-funpack-mcp.md (Section 6)
Auth: 65537
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

# ── Configuration ────────────────────────────────────────────────────────────

BROWSER_API = os.environ.get("SOLACE_BROWSER_API", "http://localhost:8888")
SERVER_INFO = {
    "name": "solace-browser",
    "version": "1.0.0",
}

# ── Tool definitions ─────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "navigate",
        "description": "Navigate the browser to a URL. Waits for the page to load before returning.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to navigate to (must start with http:// or https://)"
                },
                "wait_until": {
                    "type": "string",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                    "default": "load",
                    "description": "When to consider navigation complete"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "click",
        "description": "Click on an element matching the CSS selector.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector identifying the element to click"
                },
                "timeout_ms": {
                    "type": "integer",
                    "default": 5000,
                    "description": "Milliseconds to wait for the element to be visible"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "fill",
        "description": "Fill a form input with text. Focuses the element, clears it if requested, then types the value.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector identifying the input element"
                },
                "value": {
                    "type": "string",
                    "description": "Text value to type into the element"
                },
                "clear_first": {
                    "type": "boolean",
                    "default": True,
                    "description": "Clear existing content before typing"
                }
            },
            "required": ["selector", "value"]
        }
    },
    {
        "name": "screenshot",
        "description": "Capture a screenshot of the current page or a specific element. Returns base64-encoded PNG.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector to capture (omit for full page)"
                },
                "full_page": {
                    "type": "boolean",
                    "default": False,
                    "description": "Capture the full scrollable page (ignored if selector is set)"
                },
                "format": {
                    "type": "string",
                    "enum": ["png", "jpeg"],
                    "default": "png"
                }
            }
        }
    },
    {
        "name": "snapshot",
        "description": "Capture a Prime Mermaid DOM snapshot — a Mermaid-formatted accessibility tree of the current page with a SHA-256 integrity hash. Useful for understanding page structure.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "Scope snapshot to elements within this CSS selector (omit for full page)"
                }
            }
        }
    },
    {
        "name": "evaluate",
        "description": "Execute JavaScript in the page context and return the result. Use for reading DOM state, triggering events, or performing calculations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "JavaScript expression to evaluate. May return any JSON-serializable value."
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "aria_snapshot",
        "description": "Return the ARIA accessibility tree of the current page as structured text. Useful for understanding what screen readers see and for locating interactive elements.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "Scope the ARIA tree to this CSS selector (omit for full page)"
                }
            }
        }
    }
]

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _browser_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST to the browser API and return the parsed JSON response."""
    url = BROWSER_API.rstrip("/") + path
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            detail = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            detail = {"raw": raw}
        raise RuntimeError(f"Browser API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach browser API at {BROWSER_API} — is solace_browser_server.py running? ({exc.reason})"
        ) from exc


def _browser_get(path: str) -> dict[str, Any]:
    """GET from the browser API and return the parsed JSON response."""
    url = BROWSER_API.rstrip("/") + path
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            detail = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            detail = {"raw": raw}
        raise RuntimeError(f"Browser API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach browser API at {BROWSER_API} — is solace_browser_server.py running? ({exc.reason})"
        ) from exc


# ── Tool handlers ─────────────────────────────────────────────────────────────

def _tool_navigate(args: dict[str, Any]) -> list[dict]:
    url = args.get("url", "")
    wait_until = args.get("wait_until", "load")
    result = _browser_post("/api/navigate", {"url": url, "wait_until": wait_until})
    title = result.get("title", "")
    final_url = result.get("url", url)
    text = f"Navigated to: {final_url}"
    if title:
        text += f"\nPage title: {title}"
    return [{"type": "text", "text": text}]


def _tool_click(args: dict[str, Any]) -> list[dict]:
    selector = args.get("selector", "")
    timeout_ms = args.get("timeout_ms", 5000)
    result = _browser_post("/api/click", {"selector": selector, "timeout_ms": timeout_ms})
    text = result.get("message", f"Clicked element: {selector}")
    return [{"type": "text", "text": text}]


def _tool_fill(args: dict[str, Any]) -> list[dict]:
    selector = args.get("selector", "")
    value = args.get("value", "")
    clear_first = args.get("clear_first", True)
    result = _browser_post("/api/fill", {
        "selector": selector,
        "value": value,
        "clear_first": clear_first,
    })
    text = result.get("message", f"Filled {selector}")
    return [{"type": "text", "text": text}]


def _tool_screenshot(args: dict[str, Any]) -> list[dict]:
    payload: dict[str, Any] = {}
    if "selector" in args:
        payload["selector"] = args["selector"]
    payload["full_page"] = args.get("full_page", False)
    payload["format"] = args.get("format", "png")
    result = _browser_post("/api/screenshot", payload)

    content: list[dict] = []
    if "data" in result:
        # base64-encoded image data
        mime = "image/jpeg" if payload["format"] == "jpeg" else "image/png"
        content.append({
            "type": "image",
            "data": result["data"],
            "mimeType": mime,
        })
    elif "path" in result:
        # Server saved to file, read it
        try:
            with open(result["path"], "rb") as f:
                raw = f.read()
            mime = "image/jpeg" if payload["format"] == "jpeg" else "image/png"
            content.append({
                "type": "image",
                "data": base64.b64encode(raw).decode("ascii"),
                "mimeType": mime,
            })
        except (OSError, KeyError, ValueError) as exc:
            content.append({"type": "text", "text": f"Screenshot saved to: {result['path']}"})

    if not content:
        content.append({"type": "text", "text": "Screenshot captured (no image data returned)"})

    return content


def _tool_snapshot(args: dict[str, Any]) -> list[dict]:
    payload: dict[str, Any] = {}
    if "selector" in args:
        payload["selector"] = args["selector"]
    result = _browser_post("/api/snapshot", payload)
    mermaid = result.get("mermaid", "")
    sha256 = result.get("sha256", "")
    parts = []
    if mermaid:
        parts.append(f"```mermaid\n{mermaid}\n```")
    if sha256:
        parts.append(f"SHA-256: {sha256}")
    text = "\n".join(parts) if parts else str(result)
    return [{"type": "text", "text": text}]


def _tool_evaluate(args: dict[str, Any]) -> list[dict]:
    expression = args.get("expression", "")
    result = _browser_post("/api/evaluate", {"expression": expression})
    value = result.get("result", result)
    if isinstance(value, (dict, list)):
        text = json.dumps(value, indent=2, ensure_ascii=False)
    else:
        text = str(value)
    return [{"type": "text", "text": text}]


def _tool_aria_snapshot(args: dict[str, Any]) -> list[dict]:
    payload: dict[str, Any] = {}
    if "selector" in args:
        payload["selector"] = args["selector"]
    result = _browser_post("/api/aria_snapshot", payload)
    tree = result.get("tree", result.get("aria", ""))
    if not tree:
        tree = str(result)
    return [{"type": "text", "text": tree}]


_TOOL_DISPATCH = {
    "navigate": _tool_navigate,
    "click": _tool_click,
    "fill": _tool_fill,
    "screenshot": _tool_screenshot,
    "snapshot": _tool_snapshot,
    "evaluate": _tool_evaluate,
    "aria_snapshot": _tool_aria_snapshot,
}

# ── JSON-RPC 2.0 dispatcher ───────────────────────────────────────────────────

def _handle_request(req: dict[str, Any]) -> dict[str, Any] | None:
    """Process one JSON-RPC request and return a response dict (or None for notifications)."""
    req_id = req.get("id")  # None for notifications
    method = req.get("method", "")
    params = req.get("params") or {}

    def ok(result: Any) -> dict[str, Any]:
        resp: dict[str, Any] = {"jsonrpc": "2.0", "result": result}
        if req_id is not None:
            resp["id"] = req_id
        return resp

    def err(code: int, message: str, data: Any = None) -> dict[str, Any]:
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        resp: dict[str, Any] = {"jsonrpc": "2.0", "error": error}
        if req_id is not None:
            resp["id"] = req_id
        return resp

    # ── MCP lifecycle ──────────────────────────────────────────────────────

    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
            },
            "serverInfo": SERVER_INFO,
        })

    if method == "initialized":
        # Notification — no response
        return None

    if method == "ping":
        return ok({})

    # ── Tool discovery ─────────────────────────────────────────────────────

    if method == "tools/list":
        return ok({"tools": TOOLS})

    # ── Tool execution ─────────────────────────────────────────────────────

    if method == "tools/call":
        tool_name: str = params.get("name", "")
        tool_args: dict[str, Any] = params.get("arguments") or {}

        handler = _TOOL_DISPATCH.get(tool_name)
        if handler is None:
            return err(-32601, f"Unknown tool: {tool_name}")

        try:
            content = handler(tool_args)
            return ok({"content": content, "isError": False})
        except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
            return ok({
                "content": [{"type": "text", "text": f"Error: {exc}"}],
                "isError": True,
            })

    # ── Resources (not implemented) ────────────────────────────────────────

    if method in ("resources/list", "resources/read", "prompts/list", "prompts/get"):
        return ok({})

    # ── Unknown method ─────────────────────────────────────────────────────

    if req_id is not None:
        return err(-32601, f"Method not found: {method}")

    # Notification with unknown method — ignore
    return None


# ── stdio loop ────────────────────────────────────────────────────────────────

def main() -> None:
    """Read newline-delimited JSON-RPC from stdin, write responses to stdout."""
    # Use binary I/O to avoid platform encoding surprises
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    while True:
        line = stdin.readline()
        if not line:
            break  # EOF — client closed connection
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            stdout.write(json.dumps(resp).encode("utf-8") + b"\n")
            stdout.flush()
            continue

        try:
            resp = _handle_request(req)
        except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
            resp = {
                "jsonrpc": "2.0",
                "id": req.get("id"),
                "error": {"code": -32603, "message": f"Internal error: {exc}"},
            }

        if resp is not None:
            stdout.write(json.dumps(resp).encode("utf-8") + b"\n")
            stdout.flush()


if __name__ == "__main__":
    main()
