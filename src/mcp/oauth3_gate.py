"""
OAuth3 scope checking for MCP tool calls.

Enforces the same scoping model used by the webservice API.
Every MCP call is scope-checked before execution.

Paper: 47 Section 24 | Auth: 65537
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Scope risk levels — determines if step-up auth is needed
SCOPE_RISK: dict[str, str] = {
    "browser.navigate": "LOW",
    "browser.interact": "MEDIUM",
    "companion.app.run": "MEDIUM",
    "evidence.read": "LOW",
    "evidence.write": "MEDIUM",
}


class MCPScopeError(Exception):
    """Raised when an MCP call lacks required OAuth3 scope."""

    def __init__(self, tool_name: str, required_scope: str) -> None:
        self.tool_name = tool_name
        self.required_scope = required_scope
        super().__init__(
            f"MCP tool '{tool_name}' requires OAuth3 scope '{required_scope}'. "
            f"Grant this scope to proceed."
        )


def check_scope(tool_def: dict[str, Any], granted_scopes: frozenset[str] | None = None) -> bool:
    """Check if the tool's required scope is in the granted set.

    Args:
        tool_def: Tool definition dict with optional '_scope' field.
        granted_scopes: Set of granted OAuth3 scopes. None = all scopes granted (local mode).

    Returns:
        True if scope check passes.

    Raises:
        MCPScopeError: If required scope is not granted.
    """
    required = tool_def.get("_scope")
    if required is None:
        return True  # No scope required (public tools like health, status)

    if granted_scopes is None:
        return True  # Local mode — all scopes granted

    if required in granted_scopes:
        return True

    raise MCPScopeError(tool_def.get("name", "unknown"), required)


def requires_step_up(tool_def: dict[str, Any]) -> bool:
    """Check if this tool requires step-up authentication."""
    scope = tool_def.get("_scope")
    if scope is None:
        return False
    risk = SCOPE_RISK.get(scope, "MEDIUM")
    return risk in ("HIGH", "CRITICAL")
