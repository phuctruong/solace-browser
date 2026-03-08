"""
MCP Server for Solace Browser — Dynamic App-to-Tool Mapping.

Exposes browser capabilities and installed apps as MCP tools for AI agents
(Claude Code, Codex, Gemini CLI, Cursor, Windsurf).

Architecture:
  - tools_core.py: Core browser tools (navigate, screenshot, click, type, scroll)
  - tools_apps.py: Dynamic tools generated from app manifests
  - tools_evidence.py: Evidence + model marketplace tools
  - server.py: MCP protocol handler (stdio + SSE transport)
  - oauth3_gate.py: OAuth3 scope checking for MCP calls

Paper: 47 Section 24 | Auth: 65537
"""
