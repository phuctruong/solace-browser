"""
Core browser MCP tools — 1:1 mapping to webservice endpoints.

These tools are always available regardless of installed apps.
Each tool maps directly to an existing handler in solace_browser_server.py.

Paper: 47 Section 24 | Auth: 65537
"""
from __future__ import annotations

from typing import Any


def core_tool_definitions() -> list[dict[str, Any]]:
    """Return MCP tool definitions for core browser capabilities."""
    return [
        {
            "name": "solace_navigate",
            "description": "Navigate the browser to a URL.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"},
                },
                "required": ["url"],
            },
            "_handler": "navigate",
            "_scope": "browser.navigate",
        },
        {
            "name": "solace_screenshot",
            "description": "Take a screenshot of the current page. Returns base64 PNG.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "full_page": {"type": "boolean", "description": "Capture full scrollable page", "default": False},
                },
            },
            "_handler": "screenshot",
            "_scope": "browser.navigate",
        },
        {
            "name": "solace_page_snapshot",
            "description": "Get DOM snapshot with accessibility tree and element references.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
            "_handler": "page_snapshot",
            "_scope": "browser.navigate",
        },
        {
            "name": "solace_click",
            "description": "Click an element on the page by reference ID.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ref": {"type": "string", "description": "Element reference from page snapshot"},
                },
                "required": ["ref"],
            },
            "_handler": "act",
            "_scope": "browser.interact",
        },
        {
            "name": "solace_type",
            "description": "Type text into the currently focused element or specified element.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                    "ref": {"type": "string", "description": "Element reference (optional)"},
                },
                "required": ["text"],
            },
            "_handler": "act",
            "_scope": "browser.interact",
        },
        {
            "name": "solace_scroll",
            "description": "Scroll the page up or down.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down"], "description": "Scroll direction"},
                    "amount": {"type": "integer", "description": "Pixels to scroll", "default": 500},
                },
                "required": ["direction"],
            },
            "_handler": "act",
            "_scope": "browser.navigate",
        },
        {
            "name": "solace_health",
            "description": "Check if Solace Browser server is running and healthy.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
            "_handler": "health",
            "_scope": None,  # No scope required
        },
        {
            "name": "solace_status",
            "description": "Get browser status: current URL, page title, session info.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
            "_handler": "status",
            "_scope": None,
        },
        {
            "name": "solace_list_apps",
            "description": "List all installed Solace Browser apps with their status and matched sites.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
            "_handler": "apps_list",
            "_scope": None,
        },
        {
            "name": "solace_list_models",
            "description": "List available LLM models: BYOK API keys, local CLIs, Solace Managed.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
            "_handler": "models_list",
            "_scope": None,
        },
        {
            "name": "solace_list_screenshots",
            "description": "List captured screenshots from browser sessions.",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
            "_handler": "list_screenshots",
            "_scope": "evidence.read",
        },
        {
            "name": "solace_discovery_map",
            "description": "Map the structure of a website: pages, navigation, forms, interactive elements.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to map"},
                    "depth": {"type": "integer", "description": "Crawl depth", "default": 1},
                },
                "required": ["url"],
            },
            "_handler": "discovery_map_site",
            "_scope": "browser.navigate",
        },
    ]


# Mapping from MCP tool name to the action type for /api/act endpoint
ACT_TYPE_MAP: dict[str, str] = {
    "solace_click": "click",
    "solace_type": "type",
    "solace_scroll": "scroll",
}
