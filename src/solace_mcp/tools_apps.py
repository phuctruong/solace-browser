"""
Dynamic MCP tool generation from app manifests.

Reads manifest.yaml files from data/default/apps/ and generates
MCP tools for each installed app. Cache invalidated when files change.

Paper: 47 Section 24 | Auth: 65537
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


# Default apps directory (relative to repo root)
_DEFAULT_APPS_DIR = Path(__file__).resolve().parents[2] / "data" / "default" / "apps"


def _safe_tool_name(app_id: str) -> str:
    """Convert app_id to valid MCP tool name: only alphanumeric + underscore."""
    return re.sub(r"[^a-z0-9_]", "_", app_id.lower())


def _parse_yaml_basic(text: str) -> dict[str, Any]:
    """Parse simple YAML without PyYAML dependency.

    Handles flat key: value pairs and simple nested structures.
    For production, use PyYAML if available.
    """
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        pass

    result: dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value:
                result[key] = value
    return result


class AppToolGenerator:
    """Generate MCP tools dynamically from app manifests."""

    def __init__(self, apps_dir: Path | None = None) -> None:
        self.apps_dir = apps_dir or _DEFAULT_APPS_DIR
        self._cache: list[dict[str, Any]] | None = None
        self._cache_mtime: dict[str, float] = {}

    def _is_cache_valid(self) -> bool:
        """Check if any manifest file has changed since last cache build."""
        if self._cache is None:
            return False
        for manifest_path in self.apps_dir.glob("*/manifest.yaml"):
            path_str = str(manifest_path)
            try:
                current_mtime = os.path.getmtime(manifest_path)
            except OSError:
                return False
            if path_str not in self._cache_mtime or self._cache_mtime[path_str] != current_mtime:
                return False
        return True

    def _load_manifests(self) -> list[dict[str, Any]]:
        """Load all app manifests from the apps directory."""
        manifests = []
        if not self.apps_dir.exists():
            return manifests
        for manifest_path in sorted(self.apps_dir.glob("*/manifest.yaml")):
            try:
                text = manifest_path.read_text(encoding="utf-8")
                data = _parse_yaml_basic(text)
                if data.get("id") or data.get("app_id"):
                    app_id = str(data.get("id") or data.get("app_id", ""))
                    data["_app_id"] = app_id
                    data["_manifest_path"] = str(manifest_path)
                    manifests.append(data)
                    try:
                        self._cache_mtime[str(manifest_path)] = os.path.getmtime(manifest_path)
                    except OSError:
                        pass
            except (OSError, ValueError):
                continue
        return manifests

    def _app_to_tools(self, manifest: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate MCP tools for a single app manifest."""
        app_id = manifest.get("_app_id", "")
        safe_name = _safe_tool_name(app_id)
        name = manifest.get("name", app_id)
        description = manifest.get("description", f"Run {name}")

        tools = [
            {
                "name": f"solace_app_{safe_name}_run",
                "description": f"Run {name}: {description}",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "LLM model to use (e.g. claude_4_sonnet, solace_managed, gemini_2_5_flash)",
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "Preview without executing (default: false)",
                            "default": False,
                        },
                    },
                },
                "_handler": "app_run",
                "_app_id": app_id,
                "_scope": "companion.app.run",
            },
            {
                "name": f"solace_app_{safe_name}_benchmarks",
                "description": f"Get benchmark data for {name} across all available models. Shows cost, quality, latency.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
                "_handler": "app_benchmarks",
                "_app_id": app_id,
                "_scope": None,
            },
            {
                "name": f"solace_app_{safe_name}_status",
                "description": f"Check the status of the last {name} run.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
                "_handler": "app_status",
                "_app_id": app_id,
                "_scope": None,
            },
        ]
        return tools

    def generate_tools(self) -> list[dict[str, Any]]:
        """Generate all app tools. Uses cache if manifests haven't changed."""
        if self._is_cache_valid():
            return list(self._cache)  # type: ignore[arg-type]

        manifests = self._load_manifests()
        tools = []
        for manifest in manifests:
            tools.extend(self._app_to_tools(manifest))
        self._cache = tools
        return list(tools)

    def get_app_ids(self) -> list[str]:
        """Return list of all app IDs from manifests."""
        manifests = self._load_manifests()
        return [m.get("_app_id", "") for m in manifests if m.get("_app_id")]
