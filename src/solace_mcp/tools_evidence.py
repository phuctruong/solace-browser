"""
Evidence and model marketplace MCP tools.

Paper: 47 Section 24 | Auth: 65537
"""
from __future__ import annotations

from typing import Any


def evidence_tool_definitions() -> list[dict[str, Any]]:
    """Return MCP tool definitions for evidence and model tools."""
    return [
        {
            "name": "solace_search_evidence",
            "description": "Search evidence bundles from browser task executions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "app_id": {"type": "string", "description": "Filter by app ID"},
                    "limit": {"type": "integer", "description": "Max results", "default": 10},
                },
            },
            "_handler": "evidence_search",
            "_scope": "evidence.read",
        },
        {
            "name": "solace_verify_evidence",
            "description": "Verify an evidence chain for tamper detection (SHA-256 hash chain).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "chain_id": {"type": "string", "description": "Evidence chain ID to verify"},
                },
                "required": ["chain_id"],
            },
            "_handler": "evidence_verify",
            "_scope": "evidence.read",
        },
        {
            "name": "solace_run_recipe",
            "description": "Execute a recipe file (JSON). Requires OAuth3 scope per recipe.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "recipe_path": {"type": "string", "description": "Path to recipe.json file"},
                    "dry_run": {"type": "boolean", "description": "Preview only", "default": True},
                },
                "required": ["recipe_path"],
            },
            "_handler": "run_recipe",
            "_scope": "companion.app.run",
        },
    ]
