#!/usr/bin/env python3
from __future__ import annotations

import collections
import copy
import datetime
try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]  # Windows — file locking handled below
import hmac
import json
import logging
import os
import re
import hashlib
import secrets
import select
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

logger = logging.getLogger("solace-browser")

import yaml


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from app_store.backend import (
    AppStoreBackendConfigError,
    AppStoreCatalog,
    AppStoreProposalValidationError,
    create_proposal_store_from_env,
)
from companion.apps import discover_installed_apps
from inbox_outbox import AppFolderNotFoundError, InboxOutboxManager


# ── CLI Agent Registry (auto-detect + webservice wrapper) ────────────────────

CLI_AGENT_DEFS = [
    {
        "id": "claude", "name": "Claude Code", "cmd": "claude",
        "invoke": ["claude", "-p", "--model", "{model}", "{prompt}"],
        "stdin": False,
        "env_remove": ["CLAUDECODE"],
        "models": ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
        "default_model": "claude-sonnet-4-6",
        "provider": "Anthropic",
        "icon": "A",  # first letter fallback
        "cost": "Uses your Anthropic API key (via Claude Code)",
    },
    {
        "id": "codex", "name": "OpenAI Codex", "cmd": "codex",
        "invoke": ["codex", "exec", "{prompt}"],
        "stdin": False, "env_remove": [],
        "models": ["gpt-4.1", "gpt-4.1-mini", "o3", "o4-mini"],
        "default_model": "gpt-4.1",
        "provider": "OpenAI", "icon": "O",
        "cost": "Uses your OpenAI API key (via Codex CLI)",
    },
    {
        "id": "gemini", "name": "Google Gemini", "cmd": "gemini",
        "invoke": ["gemini", "-p", "{prompt}"],
        "stdin": False, "env_remove": [],
        "models": ["gemini-2.5-pro", "gemini-2.5-flash"],
        "default_model": "gemini-2.5-pro",
        "provider": "Google", "icon": "G",
        "cost": "Uses your Google AI API key (via Gemini CLI)",
    },
    {
        "id": "copilot", "name": "GitHub Copilot", "cmd": "copilot",
        "invoke": ["copilot", "{prompt}"],
        "stdin": False, "env_remove": [],
        "models": ["gpt-4.1", "claude-sonnet-4-6", "o4-mini"],
        "default_model": "gpt-4.1",
        "provider": "GitHub", "icon": "C",
        "cost": "Uses your GitHub Copilot subscription",
    },
    {
        "id": "antigravity", "name": "Antigravity", "cmd": "antigravity",
        "invoke": ["antigravity", "-"],
        "stdin": True, "env_remove": [],
        "models": ["claude-sonnet-4-6", "gpt-4.1"],
        "default_model": "claude-sonnet-4-6",
        "provider": "Antigravity", "icon": "AG",
        "cost": "Uses your configured Antigravity backend",
    },
    {
        "id": "cursor", "name": "Cursor", "cmd": "cursor",
        "invoke": ["cursor", "--prompt", "{prompt}"],
        "stdin": False, "env_remove": [],
        "models": ["claude-sonnet-4-6", "gpt-4.1", "cursor-fast"],
        "default_model": "claude-sonnet-4-6",
        "provider": "Cursor", "icon": "Cu",
        "cost": "Uses your Cursor Pro subscription",
    },
    {
        "id": "aider", "name": "Aider", "cmd": "aider",
        "invoke": ["aider", "--message", "{prompt}", "--no-git", "--yes"],
        "stdin": False, "env_remove": [],
        "models": ["claude-sonnet-4-6", "gpt-4.1", "deepseek-v3"],
        "default_model": "claude-sonnet-4-6",
        "provider": "Multiple", "icon": "Ai",
        "cost": "Uses your configured API keys (Anthropic/OpenAI/etc.)",
    },
]

# Cache file for detected CLI agents (avoids re-scanning every request)
_CLI_CACHE_PATH = Path.home() / ".solace" / "cli-agents-cache.json"
_cli_agents_cache: dict[str, Any] | None = None
_cli_cache_lock = threading.Lock()


def _detect_cli_agents(force: bool = False) -> dict[str, Any]:
    """Detect installed CLI agents. Cache results to ~/.solace/cli-agents-cache.json."""
    global _cli_agents_cache

    with _cli_cache_lock:
        # Return cache if available and not forced
        if _cli_agents_cache is not None and not force:
            return _cli_agents_cache

        # Try reading from disk cache (first boot optimization)
        if not force and _CLI_CACHE_PATH.exists():
            try:
                cached = json.loads(_CLI_CACHE_PATH.read_text(encoding="utf-8"))
                if cached.get("version") == 1:
                    _cli_agents_cache = cached
                    return cached
            except Exception:
                pass

        # Fresh scan
        agents = []
        for defn in CLI_AGENT_DEFS:
            agent = dict(defn)
            path = shutil.which(agent["cmd"])
            agent["installed"] = path is not None
            agent["path"] = path or ""
            agents.append(agent)

        installed = [a for a in agents if a["installed"]]
        result = {
            "version": 1,
            "agents": agents,
            "installed_count": len(installed),
            "installed_ids": [a["id"] for a in installed],
            "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        # Write cache to disk
        _CLI_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            _CLI_CACHE_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
        except OSError:
            pass

        _cli_agents_cache = result
        return result


def _cli_generate(agent_id: str, prompt: str, model: str | None = None, timeout: int = 120) -> dict[str, Any]:
    """Call a CLI agent with a prompt and return the response. Ollama-compatible."""
    cache = _detect_cli_agents()
    agent = None
    for a in cache["agents"]:
        if a["id"] == agent_id and a["installed"]:
            agent = a
            break
    if agent is None:
        return {"error": f"Agent '{agent_id}' not found or not installed", "done": True}

    use_model = model or agent["default_model"]

    # Build command from invoke template
    cmd = []
    for part in agent["invoke"]:
        cmd.append(part.replace("{prompt}", prompt).replace("{model}", use_model))

    # Clean environment
    env = os.environ.copy()
    for key in agent.get("env_remove", []):
        env.pop(key, None)

    # Scratch dir for isolation
    scratch = Path.home() / ".solace" / "cli-scratch"
    scratch.mkdir(parents=True, exist_ok=True)

    try:
        if agent.get("stdin"):
            result = subprocess.run(
                cmd, input=prompt, capture_output=True, text=True,
                timeout=timeout, env=env, cwd=str(scratch),
            )
        else:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout, env=env, cwd=str(scratch),
            )

        if result.returncode == 0:
            return {
                "response": result.stdout.strip(),
                "model": use_model,
                "agent": agent_id,
                "done": True,
            }
        else:
            return {
                "error": result.stderr.strip() or f"CLI exited with code {result.returncode}",
                "model": use_model,
                "agent": agent_id,
                "done": True,
            }
    except subprocess.TimeoutExpired:
        return {"error": f"CLI timed out after {timeout}s", "agent": agent_id, "done": True}
    except FileNotFoundError:
        return {"error": f"CLI binary not found: {agent['path']}", "agent": agent_id, "done": True}


SLUG_MAP = {
    "": "home.html",
    "home": "home.html",
    "start": "start.html",
    "download": "download.html",
    "machine-dashboard": "machine-dashboard.html",
    "schedule": "schedule.html",
    "tunnel-connect": "tunnel-connect.html",
    "style-guide": "style-guide.html",
    "apps": "app-store.html",
    "app-store": "app-store.html",
    "app-detail": "app-detail.html",
    "settings": "settings.html",
    "evidence": "settings.html",
    "community": "settings.html",
    "demo": "demo.html",
    "docs": "docs.html",
    "docs/quick-start": "docs/quick-start.html",
    "docs/mcp": "docs/mcp.html",
    "docs/oauth3": "docs/oauth3.html",
    "guide": "guide.html",
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "account": {"status": "logged_out", "user": "", "tier": "free", "api_key_hint": ""},
    "history": {
        "enabled": True,
        "screenshots": False,
        "pzip_sync": True,
        "prime_wiki": True,
        "prime_mermaid": True,
        "max_gb": 10.0,
        "exclude_domains": ["localhost", "127.0.0.1"],
    },
    "llm": {
        "backend": "claude_code",
        "model": "claude-sonnet-4-6",
        "endpoint": "http://localhost:8080",
        "byok_key": "",
    },
    "tunnel": {
        "enabled": False,
        "provider": "cloudflare",
        "public_url": "Not connected",
        "approval": "Required before every connect",
    },
    "part11": {
        "enabled": True,
        "mode": "data",
        "esigning": True,
        "chain_entries": 0,
        "audit_dir": "~/.solace/audit",
    },
    "privacy": {
        "history_local_only": True,
        "vault_encrypted": True,
        "cloud_sync_optional": True,
        "tokens_memory_only": True,
    },
    "yinyang": {
        "top_rail": True,
        "bottom_rail": True,
        "auto_expand": ["PREVIEW_READY", "BLOCKED", "ERROR"],
        "max_transcript": 24,
        "session_ttl_min": 30,
    },
    "about": {
        "version": "0.5.0-dev",
        "build": "source",
        "chrome": "Bundled Chromium (Playwright)",
        "auth_proxy": ":9222 -> :9225",
        "web_ui_port": 8791,
        "config_path": "~/.solace/settings.json",
        "vault_path": "~/.solace/vault.enc",
        "license": "MIT",
    },
}

MOCK_JSON_GET = {
    "/api/tokens/active": {
        "tokens": [
            {"app": "GitHub", "scope": "repo:read,user:email", "status": "Ready", "expires_at": "Rotates on connect"},
            {"app": "Slack", "scope": "channels:read,chat:write", "status": "Approval needed", "expires_at": "Pending grant"},
        ]
    },
    "/api/activity/recent": {
        "items": [
            {"title": "Recipe draft updated", "detail": "Added OAuth3 approval step for GitHub publishing."},
            {"title": "Machine scope narrowed", "detail": "Downloads folder remains readable, shell stays blocked."},
            {"title": "Tunnel request pending", "detail": "Waiting on explicit cloud-connect approval."},
        ]
    },
    "/api/tokens/scopes": {
        "scopes": [
            "browser.read DOM snapshots",
            "machine.read Downloads only",
            "tunnel.connect one-time approval",
            "recipes.write draft only",
        ]
    },
    "/machine/system": {
        "metrics": [
            {"label": "OS", "value": "Local workstation"},
            {"label": "Tunnel", "value": "Disconnected"},
            {"label": "Shell", "value": "Preview-only until approval"},
            {"label": "Vault", "value": "OAuth3 sealed"},
        ]
    },
    "/tunnel/status": {
        "status": "disconnected",
        "public_url": "Not connected",
        "message": "Grant tunnel.connect before the browser exposes a public URL.",
    },
}

APP_DETAIL_ROUTE_EXAMPLE = "/api/apps/gmail-inbox-triage"
APP_LIST_ROUTE = "/api/apps"
APP_INBOX_ROUTE = "/api/apps/{appId}/inbox"
APP_OUTBOX_ROUTE = "/api/apps/{appId}/outbox"
APP_STORE_SYNC_ROUTE = "/api/app-store/sync"
APP_STORE_PROPOSALS_ROUTE = "/api/app-store/proposals"
SETTINGS_ROUTE = "/api/settings"
LOCALES_DIR = REPO_ROOT / "app" / "locales" / "yinyang"
FUN_PACKS_DIR = REPO_ROOT / "data" / "fun-packs"

# In-memory notification queue (max 50 items) + SSE subscribers
_notif_queue: collections.deque = collections.deque(maxlen=50)
_notif_subscribers: list[Any] = []
_notif_lock = threading.Lock()
_notif_id_counter = 0

# In-memory rate limiter for approve/cancel (max 10 per minute per client)
_rate_limit_store: dict[str, list[float]] = {}
_rate_limit_lock = threading.Lock()
_RATE_LIMIT_MAX = 10
_RATE_LIMIT_WINDOW = 60.0  # seconds

# CSRF tokens for schedule approve/cancel (token → expiry timestamp)
_csrf_tokens: dict[str, float] = {}
_csrf_lock = threading.Lock()
_CSRF_TTL = 3600.0  # 1 hour

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"
YY_MODEL = "meta-llama/llama-3.3-70b-instruct"
YY_SYSTEM_PROMPT = (
    "You are Yinyang, the AI assistant for Solace Browser. "
    "You are helpful, warm, and slightly witty — never sycophantic. "
    "You help users understand their browser automation settings, interpret evidence logs, "
    "suggest optimizations, and answer questions about OAuth3, recipes, and apps. "
    "Keep responses concise (3-5 sentences max). Use plain text, no markdown."
)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _safe_read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


class SolaceDataStore:
    """Filesystem-backed app and settings API."""

    def __init__(
        self,
        *,
        solace_home: str | Path | None = None,
        default_library_root: str | Path | None = None,
        official_catalog_path: str | Path | None = None,
    ) -> None:
        self.solace_home = Path(solace_home or "~/.solace").expanduser().resolve()
        self.apps_root = self.solace_home / "apps"
        self.default_library_root = Path(default_library_root or REPO_ROOT / "data" / "default" / "apps").resolve()
        self.official_catalog_path = Path(
            official_catalog_path or REPO_ROOT / "data" / "default" / "app-store" / "official-store.json"
        ).resolve()
        self.settings_path = self.solace_home / "settings.json"
        self.catalog_store = AppStoreCatalog(
            catalog_path=self.official_catalog_path,
            default_apps_root=self.default_library_root,
        )
        self.proposal_store_error: str | None = None
        self.proposal_store = None
        try:
            self.proposal_store = create_proposal_store_from_env(
                repo_root=REPO_ROOT,
                solace_home=self.solace_home,
            )
        except AppStoreBackendConfigError as exc:
            self.proposal_store_error = str(exc)

    def list_apps(self, *, category: str | None = None, status: str | None = None) -> dict[str, Any]:
        apps: list[dict[str, Any]] = []
        installed_index = self._installed_index()
        catalog = self.catalog_store.load_catalog()
        catalog_map = {entry["id"]: entry for entry in catalog["apps"]}

        for entry in catalog["apps"]:
            app_summary = {
                "id": entry["id"],
                "name": entry["name"],
                "category": entry["category"],
                "status": "installed" if entry["id"] in installed_index else entry["status"],
                "safety": entry["safety"],
                "site": entry["site"],
                "description": entry["description"],
                "type": entry["type"],
                "source": entry.get("source", "official_git"),
            }
            if category and app_summary["category"] != category:
                continue
            if status and app_summary["status"] != status:
                continue
            apps.append(app_summary)

        # Include local-installed apps that are not in official git catalog yet.
        for app_id, app_root in installed_index.items():
            if app_id in catalog_map:
                continue
            manifest = _safe_read_yaml(app_root / "manifest.yaml")
            app_summary = {
                "id": manifest.get("id", app_id),
                "name": manifest.get("name", app_id),
                "category": manifest.get("category", "uncategorized"),
                "status": "installed",
                "safety": manifest.get("safety", "A"),
                "site": manifest.get("site", ""),
                "description": manifest.get("description", ""),
                "type": manifest.get("type", "standard"),
                "source": "local_filesystem",
            }
            if category and app_summary["category"] != category:
                continue
            if status and app_summary["status"] != status:
                continue
            apps.append(app_summary)

        apps.sort(key=lambda item: str(item["name"]).lower())
        return {"apps": apps}

    def get_app_detail(self, app_id: str) -> dict[str, Any]:
        catalog = self.catalog_store.load_catalog()
        catalog_map = {entry["id"]: entry for entry in catalog["apps"]}
        app_root = self._app_index().get(app_id)

        if app_root is not None:
            manager = InboxOutboxManager(apps_root=app_root.parent)
            manifest = manager.read_manifest(app_id)
            official = catalog_map.get(app_id, {})
            detail = {
                "id": manifest.get("id", app_id),
                "name": manifest.get("name", official.get("name", app_id)),
                "description": manifest.get("description", official.get("description", "")),
                "category": manifest.get("category", official.get("category", "uncategorized")),
                "status": "installed",
                "safety": manifest.get("safety", official.get("safety", "A")),
                "site": manifest.get("site", official.get("site", "")),
                "type": manifest.get("type", official.get("type", "standard")),
                "scopes": manifest.get("scopes", official.get("scopes", [])),
                "budgets": manager.read_budget(app_id),
                "inbox": manager.list_inbox(app_id),
                "outbox": manager.list_outbox(app_id),
                "recent_runs": manager.list_runs(app_id),
                "partners": manifest.get("partners", {}),
                "orchestrates": manifest.get("orchestrates", []),
                "source": official.get("source", "local_filesystem"),
            }
            return detail

        official = catalog_map.get(app_id)
        if official is not None:
            return {
                "id": official["id"],
                "name": official["name"],
                "description": official["description"],
                "category": official["category"],
                "status": official["status"],
                "safety": official["safety"],
                "site": official["site"],
                "type": official["type"],
                "scopes": official.get("scopes", []),
                "budgets": {},
                "inbox": self._empty_inbox_listing(),
                "outbox": self._empty_outbox_listing(),
                "recent_runs": [],
                "partners": {},
                "orchestrates": [],
                "source": official.get("source", "official_git"),
            }

        raise AppFolderNotFoundError(app_id)

    def get_inbox_listing(self, app_id: str) -> dict[str, Any]:
        app_root = self._get_app_root(app_id)
        return InboxOutboxManager(apps_root=app_root.parent).list_inbox(app_id)

    def get_outbox_listing(self, app_id: str) -> dict[str, Any]:
        app_root = self._get_app_root(app_id)
        return InboxOutboxManager(apps_root=app_root.parent).list_outbox(app_id)

    def read_settings(self) -> dict[str, Any]:
        if not self.settings_path.exists():
            return copy.deepcopy(DEFAULT_SETTINGS)
        payload = _safe_read_json(self.settings_path)
        return _deep_merge(DEFAULT_SETTINGS, payload)

    def write_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.solace_home.mkdir(parents=True, exist_ok=True)
        merged = _deep_merge(DEFAULT_SETTINGS, payload)
        self.settings_path.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return merged

    def get_app_store_sync(self) -> dict[str, Any]:
        catalog = self.catalog_store.load_catalog()
        installed_apps = self._installed_index()
        official_apps = catalog["apps"]
        return {
            "official_source": {
                "mode": catalog["metadata"]["mode"],
                "catalog_path": catalog["metadata"]["catalog_path"],
                "catalog_sha256": catalog["metadata"]["catalog_sha256"],
                "generated_at": catalog["metadata"]["generated_at"],
            },
            "proposal_source": {
                "backend": self.proposal_store.backend_name() if self.proposal_store is not None else "disabled",
                "error": self.proposal_store_error,
            },
            "counts": {
                "official_apps": len(official_apps),
                "installed_apps": len(installed_apps),
            },
        }

    def list_app_proposals(self, *, status: str | None = None, limit: int = 100) -> dict[str, Any]:
        if self.proposal_store is None:
            raise AppStoreBackendConfigError(self.proposal_store_error or "Proposal backend unavailable")
        proposals = self.proposal_store.list_proposals(status=status, limit=limit)
        return {
            "backend": self.proposal_store.backend_name(),
            "proposals": proposals,
        }

    def submit_app_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.proposal_store is None:
            raise AppStoreBackendConfigError(self.proposal_store_error or "Proposal backend unavailable")
        proposal = self.proposal_store.submit_proposal(payload)
        return {
            "backend": self.proposal_store.backend_name(),
            "proposal": proposal,
        }

    def _app_index(self) -> dict[str, Path]:
        installed = self._installed_index()
        if installed:
            return installed
        return self._default_index()

    def _installed_index(self) -> dict[str, Path]:
        installed = discover_installed_apps(self.apps_root)
        return {record.app_id: record.app_root for record in installed}

    def _default_index(self) -> dict[str, Path]:
        return {record.app_id: record.app_root for record in discover_installed_apps(self.default_library_root)}

    def _get_app_root(self, app_id: str) -> Path:
        app_root = self._app_index().get(app_id)
        if app_root is None:
            raise AppFolderNotFoundError(app_id)
        return app_root

    @staticmethod
    def _empty_inbox_listing() -> dict[str, Any]:
        return {
            "prompts": [],
            "templates": [],
            "assets": [],
            "policies": [],
            "datasets": [],
            "requests": [],
            "conventions": {"config": None, "defaults": None},
        }

    @staticmethod
    def _empty_outbox_listing() -> dict[str, Any]:
        return {
            "previews": [],
            "drafts": [],
            "reports": [],
            "suggestions": [],
            "runs": [],
        }


class SlugRequestHandler(SimpleHTTPRequestHandler):
    data_store: SolaceDataStore = SolaceDataStore()

    # Tunnel state (class-level — shared across requests)
    _tunnel_proc: subprocess.Popen | None = None
    _tunnel_url: str | None = None
    _tunnel_started_at: float | None = None
    _tunnel_local_port: int = 8791

    def translate_path(self, path: str) -> str:
        request_path = urlsplit(path).path
        if request_path.startswith("/css/") or request_path.startswith("/js/") or request_path.startswith("/images/"):
            return str(ROOT / request_path.lstrip("/"))
        if request_path.startswith("/data/"):
            return str(REPO_ROOT / request_path.lstrip("/"))
        if request_path in ("/favicon.ico", "/favicon.svg", "/robots.txt"):
            return str(ROOT / request_path.lstrip("/"))
        if request_path == "/":
            return str(ROOT / "home.html")
        slug = request_path.strip("/")
        if slug in SLUG_MAP:
            return str(ROOT / SLUG_MAP[slug])
        return str(ROOT / request_path.lstrip("/"))

    def do_OPTIONS(self) -> None:  # noqa: N802
        """CORS preflight — allow cross-origin requests from solaceagi.com and dev tools."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Remote-Token")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_HEAD(self) -> None:  # noqa: N802
        self._handle_request(send_body=False)

    def do_GET(self) -> None:  # noqa: N802
        self._handle_request(send_body=True)

    def do_POST(self) -> None:  # noqa: N802
        self._handle_post()

    def do_PUT(self) -> None:  # noqa: N802
        self._handle_put()

    def _handle_request(self, send_body: bool) -> None:
        request_path = urlsplit(self.path).path

        # Locale endpoint: /api/locale?key=tutorial&locale=es
        if request_path == "/api/locale":
            self._handle_locale(send_body=send_body)
            return

        # Fun packs listing: /api/fun-packs
        if request_path == "/api/fun-packs":
            self._handle_fun_packs_list(send_body=send_body)
            return

        # Schedule Viewer: /api/schedule, /api/schedule/queue, /api/schedule/upcoming
        if request_path == "/api/schedule":
            self._handle_schedule_list(send_body=send_body)
            return
        if request_path == "/api/schedule/queue":
            self._handle_schedule_queue(send_body=send_body)
            return
        if request_path == "/api/schedule/upcoming":
            self._handle_schedule_upcoming(send_body=send_body)
            return

        # YinYang notification status: /api/yinyang/status
        if request_path == "/api/yinyang/status":
            notifs = list(_notif_queue)
            unread = sum(1 for n in notifs if not n.get("read"))
            self._send_json(HTTPStatus.OK, {
                "queue_size": len(notifs),
                "unread": unread,
                "notifications": notifs,
            }, send_body=send_body)
            return

        # Budget: /api/budget
        if request_path == "/api/budget":
            settings = self.data_store.read_settings()
            budget_usd = settings.get("llm", {}).get("budget_usd", 5.0)
            self._send_json(HTTPStatus.OK, {"remaining_usd": budget_usd}, send_body=send_body)
            return

        # CLI Agents: /api/cli-agents
        if request_path == "/api/cli-agents":
            self._handle_cli_agents(send_body)
            return

        # SSE stream: /api/yinyang/events
        if request_path == "/api/yinyang/events":
            self._handle_sse_events()
            return

        # Tunnel status (GET)
        if request_path == "/tunnel/status":
            self._handle_tunnel_status()
            return

        # Remote control API (GET endpoints)
        if request_path == "/api/remote/status":
            self._handle_remote_status(send_body=send_body)
            return
        if request_path == "/api/remote/token":
            self._handle_remote_token(send_body=send_body)
            return

        # solaceagi.com proxy (GET endpoints)
        if request_path == "/api/cloud/esign/chain-status":
            self._handle_cloud_esign_chain_status(send_body=send_body)
            return
        if request_path == "/api/cloud/esign/attestations":
            self._handle_cloud_esign_attestations(send_body=send_body)
            return
        if request_path == "/api/cloud/sync/status":
            self._handle_cloud_sync_status(send_body=send_body)
            return
        if request_path == "/api/cloud/billing/status":
            self._handle_cloud_billing_status(send_body=send_body)
            return
        if request_path == "/api/cloud/user/tier":
            self._handle_cloud_user_tier(send_body=send_body)
            return
        if request_path == "/api/offline/queue":
            self._handle_offline_queue_list(send_body=send_body)
            return

        if (
            request_path.startswith("/api/apps")
            or request_path.startswith("/api/evidence")
            or request_path == SETTINGS_ROUTE
            or request_path == APP_STORE_SYNC_ROUTE
            or request_path == APP_STORE_PROPOSALS_ROUTE
        ):
            self._handle_api_get(send_body=send_body)
            return
        if request_path in MOCK_JSON_GET:
            self._send_json(HTTPStatus.OK, MOCK_JSON_GET[request_path], send_body=send_body)
            return
        if request_path == "/machine/files":
            query = parse_qs(urlsplit(self.path).query)
            path = query.get("path", ["/"])[0]
            self._send_json(
                HTTPStatus.OK,
                {
                    "path": path,
                    "items": [
                        {"name": "Downloads", "type": "folder", "detail": "scoped"},
                        {"name": "Recipes", "type": "folder", "detail": "editable"},
                        {"name": "session.log", "type": "file", "detail": "audit only"},
                        {"name": "Desktop", "type": "folder", "detail": "blocked"},
                    ],
                },
                send_body=send_body,
            )
            return
        if request_path.endswith(".html") and "/partials-" not in request_path:
            target = "/" if request_path in ("/home.html", "/index.html") else request_path[:-5]
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", target)
            self.end_headers()
            return
        if request_path == "/index":
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", "/")
            self.end_headers()
            return
        if send_body:
            super().do_GET()
        else:
            super().do_HEAD()

    def end_headers(self):  # noqa: N802
        """Inject Cache-Control: no-store for JS/CSS assets and CORS headers for all responses."""
        path = urlsplit(self.path).path
        if path.endswith(('.js', '.css')):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.send_header('Pragma', 'no-cache')
        # CORS headers — localhost-only for safety (Hashimoto/Vogels/Hightower: never wildcard)
        origin = self.headers.get('Origin', '')
        allowed_origins = ('http://localhost', 'http://127.0.0.1', 'null')
        if any(origin == ao or origin.startswith(ao + ':') for ao in allowed_origins):
            self.send_header('Access-Control-Allow-Origin', origin)
        else:
            self.send_header('Access-Control-Allow-Origin', 'http://localhost:8791')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Remote-Token')
        # Security headers (Hashimoto/Hightower: defense-in-depth)
        self.send_header('Content-Security-Policy',
                         "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                         "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
                         "font-src 'self'; connect-src 'self' "
                         "https://solaceagi-mfjzxmegpq-uc.a.run.app "
                         "https://solaceagi-qa-mfjzxmegpq-uc.a.run.app;")
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        super().end_headers()

    def _handle_api_get(self, *, send_body: bool) -> None:
        request_path = urlsplit(self.path).path
        query = parse_qs(urlsplit(self.path).query)
        app_detail_match = re.fullmatch(r"/api/apps/([^/]+)", request_path)
        app_inbox_match = re.fullmatch(r"/api/apps/([^/]+)/inbox", request_path)
        app_outbox_match = re.fullmatch(r"/api/apps/([^/]+)/outbox", request_path)
        app_runs_match = re.fullmatch(r"/api/apps/([^/]+)/runs", request_path)
        app_diagrams_match = re.fullmatch(r"/api/apps/([^/]+)/diagrams", request_path)
        app_status_match = re.fullmatch(r"/api/apps/([^/]+)/status", request_path)

        try:
            if request_path == APP_STORE_SYNC_ROUTE:
                payload = self.data_store.get_app_store_sync()
                self._send_json(HTTPStatus.OK, payload, send_body=send_body)
                return
            if request_path == APP_STORE_PROPOSALS_ROUTE:
                status_filter = query.get("status", [None])[0]
                limit_raw = query.get("limit", ["100"])[0]
                try:
                    limit = int(limit_raw) if limit_raw else 100
                except ValueError:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "limit must be an integer"}, send_body=send_body)
                    return
                payload = self.data_store.list_app_proposals(status=status_filter, limit=limit)
                self._send_json(HTTPStatus.OK, payload, send_body=send_body)
                return
            if request_path == APP_LIST_ROUTE:
                payload = self.data_store.list_apps(
                    category=query.get("category", [None])[0],
                    status=query.get("status", [None])[0],
                )
                self._send_json(HTTPStatus.OK, payload, send_body=send_body)
                return
            if request_path == "/api/apps/installed":
                payload = self.data_store.list_apps(status="installed")
                self._send_json(HTTPStatus.OK, payload, send_body=send_body)
                return
            if app_status_match:
                detail = self.data_store.get_app_detail(app_status_match.group(1))
                self._send_json(HTTPStatus.OK, {"id": detail["id"], "status": detail["status"]}, send_body=send_body)
                return
            if app_runs_match:
                self._handle_app_runs(app_runs_match.group(1), send_body)
                return
            if app_diagrams_match:
                self._handle_app_diagrams(app_diagrams_match.group(1), send_body)
                return
            if app_inbox_match:
                payload = self.data_store.get_inbox_listing(app_inbox_match.group(1))
                self._send_json(HTTPStatus.OK, payload, send_body=send_body)
                return
            if app_outbox_match:
                payload = self.data_store.get_outbox_listing(app_outbox_match.group(1))
                self._send_json(HTTPStatus.OK, payload, send_body=send_body)
                return
            if app_detail_match:
                payload = self.data_store.get_app_detail(app_detail_match.group(1))
                self._send_json(HTTPStatus.OK, payload, send_body=send_body)
                return
            if request_path == SETTINGS_ROUTE:
                self._send_json(HTTPStatus.OK, self.data_store.read_settings(), send_body=send_body)
                return
            if request_path == "/api/settings/export":
                self._handle_settings_export(send_body)
                return
            if request_path in ("/api/evidence", "/api/evidence/list"):
                self._handle_evidence_list(send_body)
                return
        except AppFolderNotFoundError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "App not found"}, send_body=send_body)
            return
        except ValueError as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)}, send_body=send_body)
            return
        except AppStoreBackendConfigError as exc:
            self._send_json(HTTPStatus.NOT_IMPLEMENTED, {"error": str(exc)}, send_body=send_body)
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"}, send_body=send_body)

    def _handle_put(self) -> None:
        request_path = urlsplit(self.path).path
        if request_path != SETTINGS_ROUTE:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        try:
            payload = self._read_json_body()
        except JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return
        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Settings payload must be an object"})
            return
        written = self.data_store.write_settings(payload)
        self._send_json(HTTPStatus.OK, written)

    def _handle_post(self) -> None:
        request_path = urlsplit(self.path).path
        try:
            payload = self._read_json_body()
        except JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return

        if request_path == APP_STORE_PROPOSALS_ROUTE:
            if not isinstance(payload, dict):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid proposal payload"})
                return
            try:
                created = self.data_store.submit_app_proposal(payload)
                self._send_json(HTTPStatus.CREATED, created)
            except AppStoreProposalValidationError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid proposal payload"})
            except AppStoreBackendConfigError as exc:
                self._send_json(HTTPStatus.NOT_IMPLEMENTED, {"error": str(exc)})
            return

        if request_path == "/machine/terminal/execute":
            command = payload.get("command", "")
            self._send_json(
                HTTPStatus.OK,
                {"output": f"preview only > {command}\ncommand blocked until machine.execute is approved"},
            )
            return
        if request_path == "/tunnel/start":
            self._handle_tunnel_start(payload)
            return
        if request_path == "/tunnel/stop":
            self._handle_tunnel_stop()
            return

        # App install: POST /api/apps/{id}/install
        app_install_match = re.fullmatch(r"/api/apps/([^/]+)/install", request_path)
        if app_install_match:
            app_id = app_install_match.group(1)
            try:
                detail = self.data_store.get_app_detail(app_id)
                self._send_json(HTTPStatus.OK, {"id": app_id, "status": "installed", "name": detail.get("name", app_id)})
            except AppFolderNotFoundError:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": f"App '{app_id}' not found in catalog"})
            return

        # App uninstall: POST /api/apps/{id}/uninstall
        app_uninstall_match = re.fullmatch(r"/api/apps/([^/]+)/uninstall", request_path)
        if app_uninstall_match:
            app_id = app_uninstall_match.group(1)
            self._send_json(HTTPStatus.OK, {"id": app_id, "status": "uninstalled"})
            return

        # App run: POST /api/apps/{id}/run  — dogfood execution endpoint
        app_run_match = re.fullmatch(r"/api/apps/([^/]+)/run", request_path)
        if app_run_match:
            self._handle_app_run(app_run_match.group(1), payload)
            return

        # App approve: POST /api/apps/{id}/approve
        app_approve_match = re.fullmatch(r"/api/apps/([^/]+)/approve", request_path)
        if app_approve_match:
            self._handle_app_approve(app_approve_match.group(1), payload)
            return

        # CLI agent generate: POST /api/cli-agents/generate
        if request_path == "/api/cli-agents/generate":
            self._handle_cli_generate(payload)
            return

        # YinYang chat: /api/yinyang/chat
        if request_path == "/api/yinyang/chat":
            self._handle_yinyang_chat(payload)
            return

        # YinYang notify (agent pushes notification): /api/yinyang/notify
        if request_path == "/api/yinyang/notify":
            self._handle_yinyang_notify(payload)
            return

        # Schedule Viewer: approve / cancel (run_id sanitized against path traversal)
        # CSRF + rate-limit gate for approve/cancel (Fixes 3 + 4)
        if request_path.startswith("/api/schedule/approve/") or request_path.startswith("/api/schedule/cancel/"):
            # Fix 3: CSRF validation
            csrf_token = payload.get("csrf_token", "")
            with _csrf_lock:
                if csrf_token not in _csrf_tokens or _csrf_tokens[csrf_token] < time.time():
                    _csrf_tokens.pop(csrf_token, None)
                    self._send_json(HTTPStatus.FORBIDDEN, {"error": "Invalid or expired CSRF token. Refresh the schedule list."})
                    return
            # Fix 4: Rate limiting (10 per minute per client)
            client_ip = self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or "127.0.0.1"
            now = time.time()
            with _rate_limit_lock:
                timestamps = _rate_limit_store.get(client_ip, [])
                timestamps = [t for t in timestamps if t > now - _RATE_LIMIT_WINDOW]
                if not timestamps:
                    _rate_limit_store.pop(client_ip, None)
                    # IP has no recent requests, allow
                else:
                    if len(timestamps) >= _RATE_LIMIT_MAX:
                        self._send_json(HTTPStatus.TOO_MANY_REQUESTS,
                                        {"error": f"Rate limit exceeded. Max {_RATE_LIMIT_MAX} approvals per minute."})
                        return
                timestamps.append(now)
                _rate_limit_store[client_ip] = timestamps

        if request_path.startswith("/api/schedule/approve/"):
            run_id = self._extract_run_id(request_path, "/api/schedule/approve/")
            if run_id is None:
                return
            self._handle_schedule_approve(run_id, payload)
            return
        if request_path.startswith("/api/schedule/cancel/"):
            run_id = self._extract_run_id(request_path, "/api/schedule/cancel/")
            if run_id is None:
                return
            self._handle_schedule_cancel(run_id, payload)
            return
        if request_path == "/api/schedule/plan":
            self._handle_schedule_plan(payload)
            return

        # Fun pack download: /api/fun-packs/download
        if request_path == "/api/fun-packs/download":
            self._handle_fun_pack_download(payload)
            return

        # Settings import (cloud sync): /api/settings/import
        if request_path == "/api/settings/import":
            self._handle_settings_import(payload)
            return

        # Budget update: /api/budget
        if request_path == "/api/budget":
            budget_usd = float(payload.get("budget_usd", 5.0))
            settings = self.data_store.read_settings()
            settings.setdefault("llm", {})["budget_usd"] = budget_usd
            self.data_store.write_settings(settings)
            self._send_json(HTTPStatus.OK, {"remaining_usd": budget_usd})
            return

        # Remote control API (POST endpoints)
        if request_path == "/api/remote/run":
            self._handle_remote_run(payload)
            return
        if request_path == "/api/remote/approve":
            self._handle_remote_approve(payload)
            return
        if request_path == "/api/remote/config":
            self._handle_remote_config(payload)
            return

        # Sync endpoints
        if request_path == "/api/sync/push":
            self._handle_sync_push(payload)
            return
        if request_path == "/api/sync/pull":
            self._handle_sync_pull(payload)
            return

        # solaceagi.com proxy: eSign
        if request_path == "/api/cloud/esign/token":
            self._handle_cloud_esign_token(payload)
            return
        if request_path == "/api/cloud/esign/sign":
            self._handle_cloud_esign_sign(payload)
            return
        if request_path == "/api/cloud/esign/verify":
            self._handle_cloud_esign_verify(payload)
            return

        # solaceagi.com proxy: sync
        if request_path == "/api/cloud/sync/push":
            self._handle_cloud_sync_push(payload)
            return
        if request_path == "/api/cloud/sync/pull":
            self._handle_cloud_sync_pull(payload)
            return

        # solaceagi.com proxy: evidence
        if request_path == "/api/cloud/evidence":
            self._handle_cloud_evidence_push(payload)
            return

        # Offline queue: flush pending items
        if request_path == "/api/offline/flush":
            self._handle_offline_flush(payload)
            return

        # GDPR: Account deletion + data export (proxy to solaceagi.com)
        if request_path == "/api/cloud/account/delete":
            self._handle_cloud_account_delete(payload)
            return
        if request_path == "/api/cloud/account/export":
            self._handle_cloud_account_export(payload)
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    # ── Locale ──────────────────────────────────────────────────────────────────

    def _handle_locale(self, *, send_body: bool) -> None:
        query = parse_qs(urlsplit(self.path).query)
        locale = query.get("locale", ["en"])[0]
        key = query.get("key", [None])[0]
        if locale not in {"en","es","vi","zh","pt","fr","ja","de","ar","hi","ko","id","ru"}:
            locale = "en"
        locale_path = LOCALES_DIR / f"{locale}.json"
        if not locale_path.exists():
            locale_path = LOCALES_DIR / "en.json"
        try:
            data = json.loads(locale_path.read_text(encoding="utf-8"))
            # Strip _meta
            data = {k: v for k, v in data.items() if not k.startswith("_")}
            if key:
                # Check delight section first, then top-level sections
                delight = data.get("delight", {})
                if key in delight:
                    self._send_json(HTTPStatus.OK, {key: delight[key]}, send_body=send_body)
                elif key in data:
                    self._send_json(HTTPStatus.OK, {key: data[key]}, send_body=send_body)
                else:
                    self._send_json(HTTPStatus.OK, {}, send_body=send_body)
            else:
                self._send_json(HTTPStatus.OK, data, send_body=send_body)
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)}, send_body=send_body)

    # ── YinYang Chat ─────────────────────────────────────────────────────────────

    def _handle_yinyang_chat(self, payload: dict[str, Any]) -> None:
        message = str(payload.get("message", "")).strip()
        if not message:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "message required"})
            return

        # Read settings context to include in system prompt
        settings = self.data_store.read_settings()
        context = json.dumps({
            "account": settings.get("account", {}),
            "llm": {k: v for k, v in settings.get("llm", {}).items() if k != "byok_key"},
            "yinyang": settings.get("yinyang", {}),
        })
        system = YY_SYSTEM_PROMPT + f"\n\nCurrent settings context: {context}"

        api_key = self._get_openrouter_key()
        if not api_key:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {
                "error": "OPENROUTER_API_KEY not configured",
                "hint": "Add OPENROUTER_API_KEY to ~/.solace/settings.json or environment"
            })
            return

        req_body = json.dumps({
            "model": YY_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            "max_tokens": 256,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                OPENROUTER_BASE,
                data=req_body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://browser.solaceagi.com",
                    "X-Title": "Solace Browser YinYang",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                reply = result["choices"][0]["message"]["content"].strip()
                self._send_json(HTTPStatus.OK, {"reply": reply, "model": YY_MODEL})
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": f"OpenRouter {exc.code}: {body[:200]}"})
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def _get_openrouter_key(self) -> str:
        # 1. Environment variable
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if key:
            return key
        # 2. ~/.solace/settings.json
        try:
            settings = self.data_store.read_settings()
            return settings.get("llm", {}).get("openrouter_api_key", "")
        except Exception:
            return ""

    # ── YinYang Notifications ────────────────────────────────────────────────────

    def _handle_yinyang_notify(self, payload: dict[str, Any]) -> None:
        global _notif_id_counter
        with _notif_lock:
            _notif_id_counter += 1
            notif = {
                "id": _notif_id_counter,
                "type": payload.get("type", "info"),
                "message": str(payload.get("message", ""))[:500],
                "priority": payload.get("priority", "low"),
                "agent_id": str(payload.get("agent_id", "unknown"))[:64],
                "ts": int(time.time()),
            }
            _notif_queue.append(notif)
            # Broadcast to SSE subscribers
            for sub in list(_notif_subscribers):
                try:
                    sub.put(notif)
                except Exception:
                    _notif_subscribers.discard(sub)
        self._send_json(HTTPStatus.OK, {"ok": True, "id": notif["id"]})

    def _handle_sse_events(self) -> None:
        """Server-Sent Events stream for real-time YinYang notifications."""
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        import queue as _queue
        q: _queue.Queue = _queue.Queue()
        with _notif_lock:
            _notif_subscribers.append(q)

        try:
            # Send existing queue on connect
            for notif in _notif_queue:
                data = f"data: {json.dumps(notif)}\n\n"
                self.wfile.write(data.encode("utf-8"))
            self.wfile.flush()

            # Stream new notifications
            while True:
                try:
                    notif = q.get(timeout=20)
                    data = f"data: {json.dumps(notif)}\n\n"
                    self.wfile.write(data.encode("utf-8"))
                    self.wfile.flush()
                except _queue.Empty:
                    # Heartbeat
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with _notif_lock:
                if q in _notif_subscribers:
                    _notif_subscribers.remove(q)

    # ── Fun Packs ────────────────────────────────────────────────────────────────

    # ── Schedule Viewer Handlers ─────────────────────────────────────────────

    def _handle_schedule_list(self, *, send_body: bool) -> None:
        """Read ~/.solace/audit/*.jsonl and return structured activity list."""
        audit_dir = Path.home() / ".solace" / "audit"
        activities = []
        if audit_dir.exists():
            for jf in sorted(audit_dir.glob("*.jsonl"), reverse=True)[:50]:
                try:
                    for line in jf.read_text(encoding="utf-8").strip().splitlines():
                        if not line.strip():
                            continue
                        try:
                            obj = json.loads(line)
                            # Normalize to activity schema
                            activity = {
                                "id": obj.get("run_id") or obj.get("id") or jf.stem,
                                "app_id":   obj.get("app_id", jf.stem.split("-")[0]),
                                "app_name": obj.get("app_name") or obj.get("app_id") or jf.stem,
                                "status":   obj.get("status", "unknown"),
                                "safety_tier": obj.get("safety_tier", "A"),
                                "started_at":  obj.get("started_at") or obj.get("timestamp"),
                                "ended_at":    obj.get("ended_at"),
                                "duration_ms": obj.get("duration_ms"),
                                "cost_usd":    obj.get("cost_usd"),
                                "tokens_used": obj.get("tokens_used"),
                                "output_summary": obj.get("output_summary") or obj.get("summary"),
                                "scopes_used": obj.get("scopes_used", []),
                                "evidence_hash": obj.get("evidence_hash") or obj.get("hash"),
                                "cross_app_triggers": obj.get("cross_app_triggers", []),
                                "approval_deadline": obj.get("approval_deadline"),
                                "schedule_pattern": obj.get("schedule_pattern"),
                            }
                            activities.append(activity)
                        except (json.JSONDecodeError, KeyError, TypeError) as exc:
                            logger.warning("Skipping malformed audit entry in %s: %s", jf, exc)
                except (OSError, PermissionError) as exc:
                    logger.warning("Cannot read audit file %s: %s", jf, exc)
        # Also check outbox for pending approvals
        outbox = Path.home() / ".solace" / "outbox" / "apps"
        if outbox.exists():
            for app_dir in outbox.iterdir():
                for run_dir in app_dir.iterdir() if app_dir.is_dir() else []:
                    approved_path = run_dir / "approved_v1.json"
                    if approved_path.exists():
                        continue  # already approved
                    preview_path = run_dir / "preview.json"
                    if preview_path.exists():
                        try:
                            pdata = json.loads(preview_path.read_text())
                            activities.append({
                                "id": run_dir.name,
                                "app_id": app_dir.name,
                                "app_name": pdata.get("app_name", app_dir.name),
                                "status": "pending_approval",
                                "safety_tier": pdata.get("safety_tier", "B"),
                                "started_at": pdata.get("created_at"),
                                "output_summary": pdata.get("preview_summary"),
                                "scopes_used": pdata.get("scopes", []),
                                "approval_deadline": pdata.get("approval_deadline"),
                            })
                        except (json.JSONDecodeError, KeyError, OSError) as exc:
                            logger.warning("Skipping preview %s: %s", preview_path, exc)
        # Sort by started_at descending
        activities.sort(key=lambda a: a.get("started_at") or "", reverse=True)
        # Generate CSRF token for subsequent approve/cancel POST requests
        csrf_token = secrets.token_urlsafe(32)
        with _csrf_lock:
            # Prune expired tokens
            now = time.time()
            expired = [t for t, exp in _csrf_tokens.items() if exp < now]
            for t in expired:
                del _csrf_tokens[t]
            _csrf_tokens[csrf_token] = now + _CSRF_TTL
        self._send_json(HTTPStatus.OK, {"activities": activities, "total": len(activities),
                                        "csrf_token": csrf_token},
                        send_body=send_body)

    def _handle_schedule_queue(self, *, send_body: bool) -> None:
        """Return only pending_approval and cooldown items."""
        audit_dir = Path.home() / ".solace" / "audit"
        pending = []
        # Check outbox for preview files without approved_v1.json
        outbox = Path.home() / ".solace" / "outbox" / "apps"
        if outbox.exists():
            for app_dir in outbox.iterdir():
                for run_dir in (app_dir.iterdir() if app_dir.is_dir() else []):
                    if (run_dir / "approved_v1.json").exists():
                        continue
                    preview_path = run_dir / "preview.json"
                    if preview_path.exists():
                        try:
                            pdata = json.loads(preview_path.read_text())
                            pending.append({
                                "id": run_dir.name,
                                "app_id": app_dir.name,
                                "status": "pending_approval",
                                "output_summary": pdata.get("preview_summary", ""),
                                "scopes_used": pdata.get("scopes", []),
                                "safety_tier": pdata.get("safety_tier", "B"),
                                "approval_deadline": pdata.get("approval_deadline"),
                            })
                        except (json.JSONDecodeError, KeyError, OSError) as exc:
                            logger.warning("Skipping preview in queue %s: %s", preview_path, exc)
        self._send_json(HTTPStatus.OK, {"queue": pending, "count": len(pending)},
                        send_body=send_body)

    def _handle_schedule_upcoming(self, *, send_body: bool) -> None:
        """Return unified operations view: app schedules + keep-alive + Part 11 + eSign."""
        settings = self.data_store.read_settings()
        upcoming = []

        # 1. App cron schedules
        schedule_config = settings.get("schedule", {})
        pattern_labels = {
            "daily_6am": "Daily at 6:00 AM",
            "daily_7am": "Daily at 7:00 AM",
            "daily_9am": "Daily at 9:00 AM",
            "weekdays_8am": "Weekdays at 8:00 AM",
            "weekdays_10am": "Weekdays at 10:00 AM",
            "weekly_monday_8am": "Mondays at 8:00 AM",
            "manual": "Manual only",
        }
        for app_id, cfg in schedule_config.items():
            if cfg.get("enabled"):
                upcoming.append({
                    "type": "app_schedule",
                    "app_id": app_id,
                    "pattern": cfg.get("pattern", "manual"),
                    "pattern_label": pattern_labels.get(cfg.get("pattern", ""), cfg.get("pattern", "manual")),
                    "next_run": cfg.get("next_run"),
                    "status": "scheduled",
                })

        # 2. Keep-alive sessions
        keep_alive = settings.get("keep_alive", {})
        for domain, ka_cfg in keep_alive.items():
            if ka_cfg.get("enabled"):
                upcoming.append({
                    "type": "keep_alive",
                    "app_id": f"keep-alive-{domain}",
                    "domain": domain,
                    "last_ping": ka_cfg.get("last_ping"),
                    "pattern": "every_30min",
                    "pattern_label": "Every 30 min",
                    "status": "active",
                })

        # 3. Part 11 evidence status
        part11 = settings.get("part11", {})
        if part11.get("enabled"):
            audit_dir = Path.home() / ".solace" / "audit"
            chain_count = 0
            if audit_dir.exists():
                chain_count = sum(1 for f in audit_dir.glob("*.jsonl"))
            upcoming.append({
                "type": "part11",
                "app_id": "part11-evidence",
                "status": "active" if part11.get("enabled") else "disabled",
                "mode": part11.get("mode", "data"),
                "esigning": part11.get("esigning", False),
                "chain_entries": chain_count,
                "audit_dir": "configured",
                "pattern_label": "Continuous (every action)",
            })

        # 4. eSign attestation count
        esign_dir = Path.home() / ".solace" / "esign"
        if esign_dir.exists():
            attestation_count = sum(1 for f in esign_dir.glob("*.json"))
        else:
            attestation_count = 0
        upcoming.append({
            "type": "esign",
            "app_id": "esign-attestations",
            "status": "active" if part11.get("esigning") else "disabled",
            "attestation_count": attestation_count,
            "pattern_label": "On approval",
        })

        self._send_json(HTTPStatus.OK, {
            "upcoming": upcoming,
            "count": len(upcoming),
            "summary": {
                "app_schedules": len(schedule_config),
                "keep_alive_sessions": sum(1 for k in keep_alive.values() if k.get("enabled")),
                "part11_enabled": part11.get("enabled", False),
                "esign_enabled": part11.get("esigning", False),
            }
        }, send_body=send_body)

    def _handle_settings_export(self, send_body: bool = True) -> None:
        """GET /api/settings/export — Export sanitized settings for cloud sync.

        Strips API keys (llm.api_key, cloud.api_key) before returning.
        Returns settings + metadata envelope for cloud vault.
        """
        settings = self.data_store.read_settings()
        # Sanitize: strip sensitive fields
        sanitized = {k: v for k, v in settings.items() if k not in ("api_key", "llm_api_key")}
        llm = sanitized.get("llm", {})
        sanitized["llm"] = {k: v for k, v in llm.items() if k not in ("api_key",)}
        cloud = sanitized.get("cloud", {})
        sanitized["cloud"] = {k: v for k, v in cloud.items() if k not in ("api_key",)}
        envelope = {
            "format": "solace-browser-settings-v1",
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "settings": sanitized,
        }
        self._send_json(HTTPStatus.OK, envelope, send_body=send_body)

    # Fix 6: Whitelist of allowed top-level keys for settings import
    # Only these keys can be imported from cloud sync — prevents injection of arbitrary config
    ALLOWED_SETTINGS_KEYS = frozenset({
        "schedule", "keep_alive", "theme", "notifications",
        "locale", "budget", "evidence", "privacy", "accessibility",
        "display", "apps", "oauth3", "sync", "esign", "compliance", "roi",
    })

    def _handle_settings_import(self, payload: dict) -> None:
        """POST /api/settings/import — Import settings from cloud sync envelope.

        Accepts: {settings: {...}} or raw settings dict.
        Merges into existing settings (does not overwrite API keys already set).
        Fix 6: Only whitelisted top-level keys are accepted — rejects llm, cloud, api_key, etc.
        """
        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "payload must be an object"})
            return
        # Support both envelope format and raw settings
        incoming = payload.get("settings", payload)
        # Fix 6: Filter to whitelisted keys only — reject unknown/dangerous keys
        rejected_keys = [k for k in incoming if k not in self.ALLOWED_SETTINGS_KEYS]
        incoming = {k: v for k, v in incoming.items() if k in self.ALLOWED_SETTINGS_KEYS}
        if rejected_keys:
            logger.warning("Settings import rejected keys: %s (not in whitelist)", rejected_keys)
        # Safety: never overwrite existing API keys from import
        existing = self.data_store.read_settings()
        existing_llm_key = existing.get("llm", {}).get("api_key")
        existing_cloud_key = existing.get("cloud", {}).get("api_key")
        merged = {**existing, **incoming}
        # Restore API keys that were in existing but not in import
        if existing_llm_key and not merged.get("llm", {}).get("api_key"):
            merged.setdefault("llm", {})["api_key"] = existing_llm_key
        if existing_cloud_key and not merged.get("cloud", {}).get("api_key"):
            merged.setdefault("cloud", {})["api_key"] = existing_cloud_key
        written = self.data_store.write_settings(merged)
        self._send_json(HTTPStatus.OK, {"ok": True,
                                        "keys_imported": list(incoming.keys()),
                                        "keys_rejected": rejected_keys,
                                        "settings": written})

    def _handle_evidence_list(self, send_body: bool = True) -> None:
        """GET /api/evidence/list — List all esign records from audit directory.

        Returns records from ~/.solace/audit/esign-*.jsonl sorted by timestamp (newest first).
        Fix 2: Verifies hash chain integrity — each ESIGN entry's hash is recomputed
        from its prev_hash + fields and compared to stored esign_hash.
        """
        audit_dir = Path.home() / ".solace" / "audit"
        records = []
        chain_valid = True
        tampered_entries: list[str] = []
        if audit_dir.exists():
            for esign_file in sorted(audit_dir.glob("esign-*.jsonl"),
                                     key=lambda f: f.stat().st_mtime, reverse=True)[:50]:
                try:
                    file_prev_hash = "genesis"
                    for line in esign_file.read_text(encoding="utf-8").strip().split("\n"):
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        event_type = record.get("event_type", "")
                        # Only verify ESIGN entries (SCREENSHOT entries don't have hash chain)
                        if event_type == "ESIGN":
                            stored_hash = record.get("esign_hash", "")
                            prev_hash = record.get("prev_hash", "genesis")
                            user_id = record.get("user_id", "")
                            ts = record.get("timestamp", "")
                            meaning = record.get("meaning", "")
                            action_hash = record.get("action_hash", "")
                            # Recompute hash to verify integrity
                            expected_hash = hashlib.sha256(
                                f"{prev_hash}|{user_id}|{ts}|{meaning}|{action_hash}".encode()
                            ).hexdigest()
                            # Also accept legacy format (without prev_hash) for backward compatibility
                            legacy_hash = hashlib.sha256(
                                f"{user_id}|{ts}|{meaning}|{action_hash}".encode()
                            ).hexdigest()
                            entry_valid = (stored_hash == expected_hash or stored_hash == legacy_hash)
                            if not entry_valid:
                                chain_valid = False
                                tampered_entries.append(record.get("run_id", "unknown"))
                                logger.warning("Evidence chain tampered in %s: run_id=%s stored=%s expected=%s",
                                               esign_file.name, record.get("run_id"), stored_hash[:16], expected_hash[:16])
                            # Verify prev_hash chain continuity
                            if prev_hash != "genesis" and prev_hash != file_prev_hash:
                                chain_valid = False
                                logger.warning("Evidence chain break in %s: expected prev_hash=%s got=%s",
                                               esign_file.name, file_prev_hash[:16], prev_hash[:16])
                            file_prev_hash = stored_hash
                        records.append({
                            "run_id": record.get("run_id", ""),
                            "user_id": record.get("user_id", ""),
                            "meaning": record.get("meaning", ""),
                            "event_type": record.get("event_type", "ESIGN"),
                            "esign_hash": record.get("esign_hash", record.get("path", ""))[:16] + "...",
                            "esign_hash_full": record.get("esign_hash", ""),
                            "prev_hash": record.get("prev_hash", ""),
                            "screenshot": record.get("screenshot"),
                            "timestamp": record.get("timestamp", record.get("sealed_at", "")),
                        })
                except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
                    logger.warning("Skipping malformed evidence entry in %s: %s", esign_file, exc)
                    chain_valid = False
                    continue
        self._send_json(HTTPStatus.OK, {
            "count": len(records),
            "records": records[:50],
            "chain_valid": chain_valid,
            "tampered_entries": tampered_entries,
        }, send_body=send_body)

    def _extract_run_id(self, request_path: str, prefix: str) -> str | None:
        """Extract and validate run_id from request path."""
        run_id = Path(request_path.split(prefix)[-1]).name
        if not re.match(r'^[a-zA-Z0-9_\-]+$', run_id):
            self._send_json(400, {"error": "Invalid run_id"})
            return None
        return run_id

    def _append_audit_entry(self, filepath: Path, record: dict) -> None:
        """Append a JSON record to an audit JSONL file with file locking."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "a") as f:
            if fcntl is not None:
                fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(record) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def _handle_schedule_approve(self, run_id: str, payload: dict) -> None:
        """Approve a pending run — write approved_v1.json + audit entry."""
        logger.info("schedule_approve: run_id=%s", run_id)
        outbox = Path.home() / ".solace" / "outbox" / "apps"
        approved_in_outbox = False
        # Torvalds: always use server timestamp — client can forge time
        # Hopper Q72/Q73: gmtime() ensures UTC — strftime() alone uses local time
        server_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        approval_record = {
            "run_id": run_id,
            "approved_by": payload.get("approved_by", "user"),
            "timestamp": server_ts,
            "client_timestamp": payload.get("timestamp"),
            "approval_type": "standard",
        }
        for app_dir in (outbox.iterdir() if outbox.exists() else []):
            if not app_dir.is_dir():
                continue
            run_dir = app_dir / run_id
            # Verify resolved path stays within outbox (prevent path traversal)
            try:
                run_dir.resolve().relative_to(outbox.resolve())
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid run_id"})
                return
            if run_dir.exists():
                # Fix 5: Validate approval_deadline — reject if deadline has passed
                preview_path = run_dir / "preview.json"
                if preview_path.exists():
                    try:
                        preview_data = json.loads(preview_path.read_text(encoding="utf-8"))
                        deadline_str = preview_data.get("approval_deadline")
                        if deadline_str:
                            deadline_dt = datetime.datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                            now_utc = datetime.datetime.now(datetime.timezone.utc)
                            if now_utc > deadline_dt:
                                self._send_json(HTTPStatus.GONE,
                                                {"error": f"Approval deadline expired at {deadline_str}. "
                                                 "Re-run the task to generate a fresh preview.",
                                                 "run_id": run_id, "deadline": deadline_str})
                                return
                    except (json.JSONDecodeError, ValueError, OSError) as exc:
                        logger.warning("Could not read preview for deadline check %s: %s", preview_path, exc)
                # Prevent approving a cancelled run (race condition guard)
                if (run_dir / "cancelled.json").exists():
                    self._send_json(409, {"error": "Run was already cancelled"})
                    return
                # Idempotency: if already approved, return success without overwriting
                approved_path = run_dir / "approved_v1.json"
                if approved_path.exists():
                    existing = json.loads(approved_path.read_text())
                    self._send_json(HTTPStatus.OK, {"ok": True, "run_id": run_id,
                                                    "in_outbox": True,
                                                    "already_approved": True,
                                                    "esign_hash": existing.get("esign_hash", "")})
                    return
                # Atomic write: temp file + rename (Vogels/Kleppmann: crash-safe)
                tmp_file = run_dir / "approved_v1.json.tmp"
                tmp_file.write_text(json.dumps(approval_record, indent=2))
                tmp_file.rename(approved_path)
                approved_in_outbox = True
                break
        # Torvalds: reject phantom approvals — run must exist in outbox
        if not approved_in_outbox:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Run {run_id} not found in outbox"})
            return
        # Always write audit log (Part 11 — every approval decision is logged)
        audit_dir = Path.home() / ".solace" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(audit_dir, 0o700)
        except OSError as exc:
            logger.debug("chmod 0o700 on audit dir failed (read-only or externally-managed): %s", exc)
        self._append_audit_entry(audit_dir / "schedule_actions.jsonl",
                                 {"event": "approved", "in_outbox": approved_in_outbox,
                                  **approval_record})

        # Auto-generate e-sign record for approved run (FDA Part 11 §11.100)
        user_id = payload.get("approved_by", "user")
        ts = approval_record["timestamp"]
        meaning = "reviewed_and_approved"
        action_desc = f"Approved scheduled run {run_id}"
        action_hash = hashlib.sha256(action_desc.encode()).hexdigest()
        # Fix 1: Read prev_hash from last esign entry for hash-chain integrity
        esign_file = audit_dir / f"esign-{run_id}.jsonl"
        prev_hash = "genesis"
        if esign_file.exists():
            try:
                lines = esign_file.read_text(encoding="utf-8").strip().splitlines()
                for line in reversed(lines):
                    if not line.strip():
                        continue
                    last_entry = json.loads(line)
                    prev_hash = last_entry.get("esign_hash", "genesis")
                    break
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not read prev_hash from %s: %s — using genesis", esign_file, exc)
        # Hash chain: prev_hash links this entry to its predecessor (Kleppmann: tamper-evident log)
        esign_hash = hashlib.sha256(
            f"{prev_hash}|{user_id}|{ts}|{meaning}|{action_hash}".encode()
        ).hexdigest()
        esign_record = {"event_type": "ESIGN", "user_id": user_id, "run_id": run_id,
                        "meaning": meaning, "action_description": action_desc,
                        "action_hash": action_hash, "prev_hash": prev_hash,
                        "esign_hash": esign_hash,
                        "timestamp": ts, "sealed_at": ts}
        # Safe filename: run_id already validated by regex at entry point
        self._append_audit_entry(esign_file, esign_record)

        # Capture screenshot as Part 11 visual evidence (best-effort, logged on failure)
        screenshot_path: str | None = None
        try:
            screenshot_payload = json.dumps({"filename": f"esign-{run_id}.png"}).encode()
            req = urllib.request.Request(
                "http://localhost:9222/api/screenshot",
                data=screenshot_payload,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                screenshot_result = json.loads(resp.read())
                screenshot_path = screenshot_result.get("filepath")
                esign_record["screenshot"] = screenshot_path
                self._append_audit_entry(esign_file, {"event_type": "SCREENSHOT", "path": screenshot_path,
                                                      "run_id": run_id, "timestamp": ts})
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            logger.warning("Screenshot capture failed for run %s: %s", run_id, exc)
            self._append_audit_entry(esign_file, {"event_type": "SCREENSHOT_FAILED", "error": str(exc),
                                                  "run_id": run_id, "timestamp": ts})

        self._send_json(HTTPStatus.OK, {"ok": True, "run_id": run_id,
                                        "in_outbox": approved_in_outbox,
                                        "esign_hash": esign_hash,
                                        "screenshot": screenshot_path})

    def _handle_schedule_cancel(self, run_id: str, payload: dict) -> None:
        """Cancel a pending run — write cancelled.json to outbox + audit entry."""
        logger.info("schedule_cancel: run_id=%s", run_id)
        # Hopper Q72/Q73: gmtime() ensures UTC — strftime() alone uses local time
        server_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        # Kleppmann: write cancel sentinel to outbox so cancelled runs don't resurrect
        outbox = Path.home() / ".solace" / "outbox" / "apps"
        for app_dir in (outbox.iterdir() if outbox.exists() else []):
            if not app_dir.is_dir():
                continue
            run_dir = app_dir / run_id
            # Hopper Q11: prevent path traversal via crafted run_id
            try:
                run_dir.resolve().relative_to(outbox.resolve())
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid run path"})
                return
            if run_dir.exists():
                cancel_file = run_dir / "cancelled.json"
                if not cancel_file.exists():
                    tmp = run_dir / "cancelled.json.tmp"
                    tmp.write_text(json.dumps({"run_id": run_id,
                        "cancelled_by": payload.get("cancelled_by", "user"),
                        "reason": payload.get("reason", "user_rejected"),
                        "timestamp": server_ts}, indent=2))
                    tmp.rename(cancel_file)
                break
        # Always write audit record (user intent is valid even if run was cleaned up)
        audit_dir = Path.home() / ".solace" / "audit"
        record = {
            "run_id": run_id,
            "event": "cancelled",
            "cancelled_by": payload.get("cancelled_by", "user"),
            "reason": payload.get("reason", "user_rejected"),
            "timestamp": server_ts,
        }
        self._append_audit_entry(audit_dir / "schedule_actions.jsonl", record)
        self._send_json(HTTPStatus.OK, {"ok": True, "run_id": run_id})

    # Vogels/Hashimoto: whitelist valid schedule patterns
    VALID_PATTERNS = {"daily_6am", "daily_7am", "daily_9am", "weekdays_8am",
                      "weekdays_10am", "weekly_monday_8am", "manual"}

    def _handle_schedule_plan(self, payload: dict) -> None:
        """Add a future run to the schedule config."""
        app_id = payload.get("app_id", "")
        pattern = payload.get("pattern", "manual")
        if not app_id:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "app_id required"})
            return
        if pattern not in self.VALID_PATTERNS:
            self._send_json(HTTPStatus.BAD_REQUEST,
                            {"error": f"Invalid pattern '{pattern}'. Valid: {sorted(self.VALID_PATTERNS)}"})
            return
        settings = self.data_store.read_settings()
        if "schedule" not in settings:
            settings["schedule"] = {}
        settings["schedule"][app_id] = {
            "enabled": True,
            "pattern": pattern,
            "next_run": payload.get("next_run"),
        }
        self.data_store.write_settings(settings)
        self._send_json(HTTPStatus.OK, {"ok": True, "app_id": app_id, "pattern": pattern})

    def _handle_fun_packs_list(self, *, send_body: bool) -> None:
        FUN_PACKS_DIR.mkdir(parents=True, exist_ok=True)
        index_path = FUN_PACKS_DIR / "index.json"
        if index_path.exists():
            try:
                data = json.loads(index_path.read_text(encoding="utf-8"))
                self._send_json(HTTPStatus.OK, data, send_body=send_body)
                return
            except Exception:
                pass
        # Auto-discover pack files
        packs = []
        for pack_file in sorted(FUN_PACKS_DIR.glob("*.json")):
            if pack_file.name == "index.json":
                continue
            try:
                pack = json.loads(pack_file.read_text(encoding="utf-8"))
                meta = pack.get("_meta", {})
                packs.append({
                    "id": meta.get("id", pack_file.stem),
                    "name": meta.get("name", pack_file.stem),
                    "locale": meta.get("locale", "en"),
                    "jokes": len(pack.get("jokes", [])),
                    "facts": len(pack.get("facts", [])),
                    "file": pack_file.name,
                    "author": meta.get("author", ""),
                    "license": meta.get("license", "MIT"),
                    "tags": meta.get("tags", []),
                })
            except Exception:
                pass
        self._send_json(HTTPStatus.OK, {"packs": packs}, send_body=send_body)

    def _handle_fun_pack_download(self, payload: dict[str, Any]) -> None:
        url = str(payload.get("url", "")).strip()
        if not url.startswith("https://"):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "url must start with https://"})
            return
        try:
            FUN_PACKS_DIR.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            pack_id = data.get("_meta", {}).get("id", "custom")
            # Sanitize filename
            safe_id = re.sub(r"[^a-z0-9_\-]", "", pack_id.lower())[:40] or "custom"
            dest = FUN_PACKS_DIR / f"{safe_id}.json"
            dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self._send_json(HTTPStatus.OK, {"ok": True, "saved": dest.name, "id": safe_id})
        except Exception as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})

    # ── App Execution Endpoints ──────────────────────────────────────────────
    BROWSER_API = "http://127.0.0.1:9222"
    APPS_DATA = REPO_ROOT / "data" / "default" / "apps"
    PRIMEWIKI_DATA = REPO_ROOT / "data" / "default" / "primewiki"

    def _handle_app_run(self, app_id: str, payload: dict[str, Any]) -> None:
        """POST /api/apps/{id}/run — Execute app via real browser automation."""
        import hashlib
        from datetime import datetime, timezone

        safe_id = re.sub(r"[^a-z0-9_\-]", "", app_id)
        if not safe_id or safe_id != app_id:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid app_id"})
            return

        app_dir = self.APPS_DATA / safe_id
        if not app_dir.is_dir():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": f"app {safe_id} not found"})
            return

        config = payload.get("config", {})
        run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        # Determine target URL from manifest
        manifest_path = app_dir / "manifest.yaml"
        target_url = None
        if manifest_path.exists():
            try:
                manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
                keep_alive = manifest.get("keep_alive", {})
                target_url = keep_alive.get("url")
            except Exception:
                pass

        # App-specific URL fallbacks
        url_map = {
            "gmail-inbox-triage": "https://mail.google.com/mail/u/0/#inbox",
            "whatsapp-responder": "https://web.whatsapp.com/",
            "linkedin-outreach": "https://www.linkedin.com/feed/",
        }
        if not target_url:
            target_url = url_map.get(safe_id, "about:blank")

        # Phase 1: Navigate browser
        try:
            nav_resp = urllib.request.urlopen(
                urllib.request.Request(
                    f"{self.BROWSER_API}/api/navigate",
                    data=json.dumps({"url": target_url}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                ),
                timeout=15,
            )
            nav_data = json.loads(nav_resp.read().decode("utf-8"))
        except Exception as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {
                "error": "browser_offline",
                "detail": f"Could not navigate: {exc}",
                "run_id": run_id,
            })
            return

        # Phase 2: Wait for page load then extract data
        time.sleep(3)

        # App-specific extraction JS
        extract_js = self._get_extraction_js(safe_id)
        items = []
        try:
            ext_resp = urllib.request.urlopen(
                urllib.request.Request(
                    f"{self.BROWSER_API}/api/evaluate",
                    data=json.dumps({"expression": extract_js}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                ),
                timeout=15,
            )
            ext_data = json.loads(ext_resp.read().decode("utf-8"))
            items = ext_data.get("result", []) if ext_data.get("success") else []
        except Exception:
            pass

        # Phase 3: Screenshot
        screenshot_path = ""
        try:
            ss_resp = urllib.request.urlopen(
                urllib.request.Request(
                    f"{self.BROWSER_API}/api/screenshot",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                ),
                timeout=10,
            )
            ss_data = json.loads(ss_resp.read().decode("utf-8"))
            screenshot_path = ss_data.get("filepath", "")
        except Exception:
            pass

        # Phase 4: Save run to inbox
        inbox_dir = app_dir / "inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)
        run_data = {
            "run_id": run_id,
            "app_id": safe_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": config,
            "items": items if isinstance(items, list) else [],
            "total": len(items) if isinstance(items, list) else 0,
            "screenshot": screenshot_path,
            "status": "preview_ready",
        }
        (inbox_dir / f"{run_id}.json").write_text(
            json.dumps(run_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Build preview text
        preview = self._build_preview_text(safe_id, items, config)

        self._send_json(HTTPStatus.OK, {
            "run_id": run_id,
            "status": "preview_ready",
            "total": len(items) if isinstance(items, list) else 0,
            "items": items if isinstance(items, list) else [],
            "screenshot": screenshot_path,
            "preview": preview,
        })

    def _handle_app_approve(self, app_id: str, payload: dict[str, Any]) -> None:
        """POST /api/apps/{id}/approve — Approve and execute actions."""
        import hashlib
        from datetime import datetime, timezone

        safe_id = re.sub(r"[^a-z0-9_\-]", "", app_id)
        run_id = payload.get("run_id", "")
        actions = payload.get("actions", [])

        # Execute approval actions via browser
        action_results = []
        for action in actions:
            if action.get("action") == "archive":
                # Gmail: use keyboard shortcut 'e' to archive selected
                pass  # Real archiving handled by browser-side JS
            elif action.get("action") == "draft_reply":
                pass  # Draft creation handled by browser-side JS

        # Create evidence seal
        now = datetime.now(timezone.utc)
        evidence_payload = json.dumps({
            "run_id": run_id,
            "app_id": safe_id,
            "approved_at": now.isoformat(),
            "actions": actions,
        }, sort_keys=True)
        evidence_hash = "sha256:" + hashlib.sha256(evidence_payload.encode()).hexdigest()

        # Create eSign attestation
        esign_payload = json.dumps({
            "user_id": "phuc",
            "timestamp": now.isoformat(),
            "meaning": "reviewed_and_approved",
            "action_description": f"Approved {safe_id} run {run_id}",
        }, sort_keys=True)
        esign_hash = "sha256:" + hashlib.sha256(esign_payload.encode()).hexdigest()

        # Save to outbox
        app_dir = self.APPS_DATA / safe_id
        outbox_dir = app_dir / "outbox" / "runs" / run_id
        outbox_dir.mkdir(parents=True, exist_ok=True)
        (outbox_dir / "evidence.json").write_text(
            json.dumps({
                "evidence_hash": evidence_hash,
                "esign_hash": esign_hash,
                "approved_at": now.isoformat(),
                "run_id": run_id,
                "app_id": safe_id,
            }, indent=2),
            encoding="utf-8",
        )

        # Take post-action screenshot
        screenshot_path = ""
        try:
            ss_resp = urllib.request.urlopen(
                urllib.request.Request(
                    f"{self.BROWSER_API}/api/screenshot",
                    data=b"{}",
                    headers={"Content-Type": "application/json"},
                    method="POST",
                ),
                timeout=10,
            )
            ss_data = json.loads(ss_resp.read().decode("utf-8"))
            screenshot_path = ss_data.get("filepath", "")
        except Exception:
            pass

        self._send_json(HTTPStatus.OK, {
            "status": "completed",
            "run_id": run_id,
            "evidence_hash": evidence_hash,
            "esign_hash": esign_hash,
            "screenshot": screenshot_path,
        })

    def _handle_cli_agents(self, send_body: bool) -> None:
        """GET /api/cli-agents — Detect installed AI coding CLIs (cached).
        GET /api/cli-agents?rescan=1 — Force rescan."""
        qs = parse_qs(urlsplit(self.path).query)
        force = "rescan" in qs
        result = _detect_cli_agents(force=force)
        self._send_json(HTTPStatus.OK, result, send_body=send_body)

    def _handle_cli_generate(self, payload: dict[str, Any]) -> None:
        """POST /api/cli-agents/generate — Call a CLI agent for LLM inference.

        Request:  {"agent": "claude", "prompt": "...", "model": "claude-opus-4-6"}
        Response: {"response": "...", "model": "...", "agent": "claude", "done": true}
        Ollama-compatible response shape.
        """
        agent_id = payload.get("agent", "")
        prompt = payload.get("prompt", "")
        model = payload.get("model")
        timeout = min(int(payload.get("timeout", 120)), 300)

        if not agent_id or not prompt:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "agent and prompt required"})
            return

        result = _cli_generate(agent_id, prompt, model=model, timeout=timeout)
        status = HTTPStatus.OK if "error" not in result else HTTPStatus.INTERNAL_SERVER_ERROR
        self._send_json(status, result)

    def _handle_app_runs(self, app_id: str, send_body: bool) -> None:
        """GET /api/apps/{id}/runs — List run history."""
        safe_id = re.sub(r"[^a-z0-9_\-]", "", app_id)
        app_dir = self.APPS_DATA / safe_id
        inbox_dir = app_dir / "inbox"
        runs = []
        if inbox_dir.is_dir():
            for f in sorted(inbox_dir.glob("run-*.json"), reverse=True)[:50]:
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    runs.append(data)
                except Exception:
                    pass
        self._send_json(HTTPStatus.OK, {"runs": runs}, send_body=send_body)

    def _handle_app_diagrams(self, app_id: str, send_body: bool) -> None:
        """GET /api/apps/{id}/diagrams — List app diagrams + Prime Wiki mermaid."""
        safe_id = re.sub(r"[^a-z0-9_\-]", "", app_id)
        diagrams = []

        # App-specific diagrams
        app_diag_dir = self.APPS_DATA / safe_id / "diagrams"
        if app_diag_dir.is_dir():
            for f in sorted(app_diag_dir.glob("*.md")):
                try:
                    content = f.read_text(encoding="utf-8")
                    diagrams.append({"name": f.stem, "source": "app", "content": content})
                except Exception:
                    pass

        # Prime Wiki mermaid files
        platform_map = {
            "gmail-inbox-triage": "gmail",
            "whatsapp-responder": "whatsapp",
            "linkedin-outreach": "linkedin",
        }
        platform = platform_map.get(safe_id, safe_id.split("-")[0])
        pw_dir = self.PRIMEWIKI_DATA / platform
        if pw_dir.is_dir():
            for f in sorted(pw_dir.glob("*.prime-mermaid.md")):
                try:
                    content = f.read_text(encoding="utf-8")
                    diagrams.append({"name": f.stem, "source": "primewiki", "content": content})
                except Exception:
                    pass

        self._send_json(HTTPStatus.OK, {"diagrams": diagrams}, send_body=send_body)

    def _get_extraction_js(self, app_id: str) -> str:
        """Return app-specific JS extraction code for the browser."""
        if app_id == "gmail-inbox-triage":
            return """(function() {
                var rows = Array.from(document.querySelectorAll('tr.zA')).slice(0, 20);
                return rows.map(function(r) {
                    var se = r.querySelector('span[email]');
                    var sender = se ? (se.getAttribute('email') || se.textContent.trim())
                                   : (r.querySelector('.yW') || {textContent:''}).textContent.trim();
                    var bog = r.querySelector('.a4W .bog') || r.querySelector('.bog');
                    var snip = r.querySelector('.y2');
                    var dt = r.querySelector('.xW span[title]');
                    return {
                        sender: sender,
                        subject: bog ? bog.textContent.trim() : '',
                        snippet: snip ? snip.textContent.trim().slice(0,150) : '',
                        is_unread: r.classList.contains('zE'),
                        date: dt ? dt.getAttribute('title') : ''
                    };
                });
            })()"""
        elif app_id == "whatsapp-responder":
            return """(function() {
                var chats = Array.from(document.querySelectorAll('[data-testid="cell-frame-container"]')).slice(0, 10);
                return chats.map(function(c) {
                    var name = c.querySelector('[data-testid="cell-frame-title"] span') || {};
                    var msg = c.querySelector('[data-testid="last-msg-status"] span') || c.querySelector('.Hy9nV span') || {};
                    var time = c.querySelector('[data-testid="cell-frame-primary-detail"]') || {};
                    var unread = c.querySelector('[data-testid="icon-unread-count"]');
                    return {
                        sender: name.textContent ? name.textContent.trim() : '',
                        subject: msg.textContent ? msg.textContent.trim().slice(0,100) : '',
                        date: time.textContent ? time.textContent.trim() : '',
                        is_unread: !!unread
                    };
                });
            })()"""
        elif app_id == "linkedin-outreach":
            return """(function() {
                var items = Array.from(document.querySelectorAll('.feed-shared-update-v2')).slice(0, 10);
                return items.map(function(item) {
                    var author = item.querySelector('.update-components-actor__name span') || {};
                    var text = item.querySelector('.feed-shared-update-v2__description') || {};
                    return {
                        sender: author.textContent ? author.textContent.trim() : '',
                        subject: text.textContent ? text.textContent.trim().slice(0,150) : '',
                        is_unread: false,
                        date: ''
                    };
                });
            })()"""
        return "(function() { return []; })()"

    def _build_preview_text(self, app_id: str, items: list, config: dict) -> str:
        """Build human-readable preview text for approval."""
        if not isinstance(items, list) or not items:
            return f"No items found. The browser may need to be logged into the service first."

        lines = []
        if app_id == "gmail-inbox-triage":
            email = config.get("cfgEmail", config.get("email", ""))
            unread = [e for e in items if e.get("is_unread")]
            lines.append(f"Gmail Inbox Triage — {email}")
            lines.append("=" * 50)
            lines.append(f"Scanned: {len(items)} emails | Unread: {len(unread)}")
            lines.append("")
            for i, e in enumerate(items):
                badge = "[UNREAD]" if e.get("is_unread") else "[READ]"
                lines.append(f"{i+1}. {badge} {e.get('subject', '(no subject)')}")
                lines.append(f"   From: {e.get('sender', 'Unknown')}")
                if e.get("snippet"):
                    lines.append(f"   {e['snippet'][:80]}")
                lines.append("")
        elif app_id == "whatsapp-responder":
            lines.append("WhatsApp Responder — Preview")
            lines.append("=" * 50)
            for i, c in enumerate(items):
                badge = "[UNREAD]" if c.get("is_unread") else ""
                lines.append(f"{i+1}. {badge} {c.get('sender', 'Unknown')}: {c.get('subject', '')}")
            lines.append("")
        elif app_id == "linkedin-outreach":
            lines.append("LinkedIn Outreach — Preview")
            lines.append("=" * 50)
            for i, item in enumerate(items):
                lines.append(f"{i+1}. {item.get('sender', 'Unknown')}")
                lines.append(f"   {item.get('subject', '')[:100]}")
                lines.append("")
        else:
            lines.append(f"{app_id} — {len(items)} items found")
            for i, item in enumerate(items):
                lines.append(f"{i+1}. {json.dumps(item)[:120]}")

        lines.append("=" * 50)
        lines.append("Nothing happens until you approve.")
        return "\n".join(lines)

    # ── Remote Control API ───────────────────────────────────────────────────

    _REMOTE_TOKEN_PATH = Path.home() / ".solace" / "remote-token"

    @classmethod
    def _validate_remote_token(cls, token: str) -> bool:
        """Validate a bearer token against ~/.solace/remote-token.

        Auto-generates the token file on first use. Uses hmac.compare_digest
        for timing-safe comparison to prevent timing attacks.
        Returns True if valid, False otherwise.
        """
        token_path = cls._REMOTE_TOKEN_PATH
        if not token_path.exists():
            # Auto-generate on first use
            token_path.parent.mkdir(parents=True, exist_ok=True)
            generated = secrets.token_hex(32)
            token_path.write_text(generated, encoding="utf-8")
            token_path.chmod(0o600)
        stored = token_path.read_text(encoding="utf-8").strip()
        if not token or not stored:
            return False
        return hmac.compare_digest(stored, token)

    def _get_remote_token_from_request(self, payload: dict[str, Any] | None = None) -> str:
        """Extract remote token from request — checks Authorization header first, then payload.token."""
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        if payload and isinstance(payload, dict):
            return str(payload.get("token", ""))
        # For GET requests check query string
        qs = parse_qs(urlsplit(self.path).query)
        return qs.get("token", [""])[0]

    def _handle_remote_run(self, payload: dict[str, Any]) -> None:
        """POST /api/remote/run — Trigger an app run remotely.

        Body: { "app_id": "gmail-inbox-triage", "config": {...}, "token": "..." }
        Returns: { "run_id": "...", "status": "pending_approval" | "running", "preview": "..." }
        """
        token = self._get_remote_token_from_request(payload)
        if not self._validate_remote_token(token):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Invalid or missing remote token"})
            return

        app_id = str(payload.get("app_id", "")).strip()
        if not app_id:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "app_id required"})
            return

        # Delegate to the same run logic as local /api/apps/{id}/run
        run_payload = {
            "config": payload.get("config", {}),
        }
        # Capture response by temporarily redirecting — simulate the run
        self._handle_app_run(app_id, run_payload)

    def _handle_remote_approve(self, payload: dict[str, Any]) -> None:
        """POST /api/remote/approve — Approve or reject a pending run remotely.

        Body: { "run_id": "...", "action": "approve" | "reject", "token": "..." }
        Returns: { "status": "approved" | "rejected", "evidence_hash": "..." }
        """
        import hashlib
        from datetime import datetime, timezone

        token = self._get_remote_token_from_request(payload)
        if not self._validate_remote_token(token):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Invalid or missing remote token"})
            return

        run_id = str(payload.get("run_id", "")).strip()
        action = str(payload.get("action", "approve")).strip().lower()

        if not run_id:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "run_id required"})
            return
        if action not in ("approve", "reject"):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "action must be 'approve' or 'reject'"})
            return

        now = datetime.now(timezone.utc)
        audit_dir = Path.home() / ".solace" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        if action == "approve":
            # Write approved_v1.json to the outbox run directory
            outbox = Path.home() / ".solace" / "outbox" / "apps"
            approved_in_outbox = False
            approval_record = {
                "run_id": run_id,
                "approved_by": "remote",
                "timestamp": now.isoformat(),
                "approval_type": "remote",
            }
            for app_dir in (outbox.iterdir() if outbox.exists() else []):
                run_dir = app_dir / run_id if app_dir.is_dir() else None
                if run_dir and run_dir.exists():
                    (run_dir / "approved_v1.json").write_text(
                        json.dumps(approval_record, indent=2), encoding="utf-8"
                    )
                    approved_in_outbox = True
                    break

            evidence_payload = json.dumps({
                "run_id": run_id,
                "action": "approve",
                "approved_at": now.isoformat(),
                "source": "remote",
            }, sort_keys=True)
            evidence_hash = "sha256:" + hashlib.sha256(evidence_payload.encode()).hexdigest()

            with open(audit_dir / "remote_actions.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "event": "remote_approved",
                    "run_id": run_id,
                    "evidence_hash": evidence_hash,
                    "timestamp": now.isoformat(),
                    "in_outbox": approved_in_outbox,
                }) + "\n")

            self._send_json(HTTPStatus.OK, {
                "status": "approved",
                "run_id": run_id,
                "evidence_hash": evidence_hash,
            })
        else:
            # Reject: write cancelled record to audit log
            with open(audit_dir / "remote_actions.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "event": "remote_rejected",
                    "run_id": run_id,
                    "timestamp": now.isoformat(),
                    "reason": payload.get("reason", "remote_reject"),
                }) + "\n")

            self._send_json(HTTPStatus.OK, {
                "status": "rejected",
                "run_id": run_id,
                "evidence_hash": "",
            })

    def _handle_remote_status(self, *, send_body: bool = True) -> None:
        """GET /api/remote/status?token=... — Get status of all apps, recent runs, savings.

        Returns: { "apps": [...], "recent_runs": [...], "cli_agents": [...], "savings": {...} }
        """
        token = self._get_remote_token_from_request()
        if not self._validate_remote_token(token):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Invalid or missing remote token"},
                            send_body=send_body)
            return

        # Apps list
        try:
            apps_data = self.data_store.list_apps()
            apps = apps_data.get("apps", [])
        except Exception:
            apps = []

        # Recent runs from audit + outbox
        recent_runs: list[dict[str, Any]] = []
        audit_dir = Path.home() / ".solace" / "audit"
        if audit_dir.exists():
            for jf in sorted(audit_dir.glob("*.jsonl"), reverse=True)[:10]:
                try:
                    for line in jf.read_text(encoding="utf-8").strip().splitlines()[-5:]:
                        if not line.strip():
                            continue
                        obj = json.loads(line)
                        recent_runs.append({
                            "run_id": obj.get("run_id", ""),
                            "app_id": obj.get("app_id", ""),
                            "status": obj.get("status", ""),
                            "timestamp": obj.get("timestamp") or obj.get("started_at", ""),
                        })
                except Exception:
                    pass
        recent_runs = recent_runs[:20]

        # CLI agents status
        try:
            cli_data = _detect_cli_agents()
            cli_agents = [
                {"id": a["id"], "name": a["name"], "installed": a["installed"]}
                for a in cli_data.get("agents", [])
            ]
        except Exception:
            cli_agents = []

        # Savings estimate
        run_count = len(recent_runs)
        savings = {
            "estimated_runs": run_count,
            "cost_per_run_usd": 0.001,
            "total_saved_usd": round(run_count * 0.001, 4),
            "note": "Recipe replay cost vs LLM-per-run cost estimate",
        }

        self._send_json(HTTPStatus.OK, {
            "apps": apps,
            "recent_runs": recent_runs,
            "cli_agents": cli_agents,
            "savings": savings,
        }, send_body=send_body)

    def _handle_remote_token(self, *, send_body: bool = True) -> None:
        """GET /api/remote/token — Display the remote access token (local-only, no auth needed).

        This endpoint is intentionally unauthenticated because it only runs on localhost.
        The token is used by solaceagi.com to authenticate remote control requests.
        Returns: { "token": "...", "instructions": "..." }
        """
        token_path = self._REMOTE_TOKEN_PATH
        if not token_path.exists():
            token_path.parent.mkdir(parents=True, exist_ok=True)
            generated = secrets.token_hex(32)
            token_path.write_text(generated, encoding="utf-8")
            token_path.chmod(0o600)
        token = token_path.read_text(encoding="utf-8").strip()
        self._send_json(HTTPStatus.OK, {
            "token": token,
            "token_path": str(token_path),
            "instructions": (
                "Add this token to your solaceagi.com account settings under "
                "Settings > Remote Access > Local Token. "
                "Keep it secret — it grants full remote control of your local browser."
            ),
        }, send_body=send_body)

    def _handle_remote_config(self, payload: dict[str, Any]) -> None:
        """POST /api/remote/config — Update app config remotely.

        Body: { "app_id": "...", "config": {...}, "token": "..." }
        Writes config to the app's inbox/conventions/ directory.
        """
        token = self._get_remote_token_from_request(payload)
        if not self._validate_remote_token(token):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Invalid or missing remote token"})
            return

        app_id = str(payload.get("app_id", "")).strip()
        config = payload.get("config", {})

        if not app_id:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "app_id required"})
            return
        if not isinstance(config, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "config must be an object"})
            return

        safe_id = re.sub(r"[^a-z0-9_\-]", "", app_id)
        if not safe_id or safe_id != app_id:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid app_id"})
            return

        app_dir = self.APPS_DATA / safe_id
        if not app_dir.is_dir():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": f"app {safe_id} not found"})
            return

        conventions_dir = app_dir / "inbox" / "conventions"
        conventions_dir.mkdir(parents=True, exist_ok=True)
        config_path = conventions_dir / "config.json"

        # Merge with existing config
        existing: dict[str, Any] = {}
        if config_path.exists():
            try:
                existing = json.loads(config_path.read_text(encoding="utf-8"))
                if not isinstance(existing, dict):
                    existing = {}
            except Exception:
                existing = {}

        merged = {**existing, **config}
        config_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

        self._send_json(HTTPStatus.OK, {
            "ok": True,
            "app_id": safe_id,
            "config_path": str(config_path),
            "keys_updated": list(config.keys()),
        })

    # ─────────────────────────────────────────────────────────────────────
    # solaceagi.com Cloud Proxy — eSign, Sync, Evidence, Billing
    # OAuth3 + Part 11 compliant. Offline queue if unreachable.
    # ─────────────────────────────────────────────────────────────────────

    _SOLACE_CLOUD_URL = "https://solaceagi-mfjzxmegpq-uc.a.run.app"
    _OFFLINE_QUEUE: Path = Path.home() / ".solace" / "sync" / "offline-queue.jsonl"

    def _cloud_auth_token(self) -> str | None:
        """Get the user's cloud auth token from settings."""
        settings = self.data_store.read_settings()
        return settings.get("cloud", {}).get("auth_token")

    def _cloud_request(self, method: str, path: str, payload: dict | None = None,
                       *, token: str | None = None) -> tuple[int, dict]:
        """Make authenticated request to solaceagi.com. Returns (status, json_body)."""
        url = f"{self._SOLACE_CLOUD_URL}{path}"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        # Longer timeout for POST (crypto operations), shorter for GET
        timeout = 30 if method == "POST" else 15
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                # Verify response URL matches expected host (prevent redirect attacks)
                if hasattr(resp, 'url') and not resp.url.startswith(self._SOLACE_CLOUD_URL):
                    return 502, {"error": f"Unexpected redirect to {resp.url}"}
                body = json.loads(resp.read().decode("utf-8"))
                return resp.status, body
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode("utf-8"))
            except Exception:
                body = {"error": str(exc)}
            return exc.code, body
        except (urllib.error.URLError, OSError) as exc:
            return 0, {"error": f"offline: {exc}", "offline": True}

    def _audit_cloud_call(self, endpoint: str, method: str, status: int, payload: dict | None = None) -> None:
        """Log cloud API call to Part 11 audit trail."""
        import hashlib as _hashlib
        audit_dir = Path.home() / ".solace" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        entry = {
            "type": "cloud_api_call",
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "timestamp": ts,
        }
        entry["evidence_hash"] = _hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
        with open(audit_dir / "cloud_api_calls.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")

    _OFFLINE_QUEUE_MAX = 10_000  # Max queue entries (prevent unbounded growth)

    def _queue_offline(self, action: str, payload: dict) -> None:
        """Queue an action for later sync when back online."""
        self._OFFLINE_QUEUE.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(self._OFFLINE_QUEUE.parent, 0o700)
        # Strip sensitive tokens from payload before queuing (security)
        safe_payload = {k: v for k, v in payload.items()
                        if k not in ("auth_token", "bearer_token", "password", "secret")}
        entry = {
            "action": action,
            "payload": safe_payload,
            "queued_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "retry_count": 0,
        }
        # Check queue size limit
        if self._OFFLINE_QUEUE.exists():
            line_count = sum(1 for _ in open(self._OFFLINE_QUEUE))
            if line_count >= self._OFFLINE_QUEUE_MAX:
                logger.warning("Offline queue full (%d items). Dropping oldest entry.", line_count)
                lines = self._OFFLINE_QUEUE.read_text().strip().split("\n")
                with open(self._OFFLINE_QUEUE, "w") as f:
                    for line in lines[1:]:  # Drop oldest
                        f.write(line + "\n")
        with open(self._OFFLINE_QUEUE, "a") as f:
            f.write(json.dumps(entry) + "\n")

    # ── Cloud eSign Proxy ───────────────────────────────────────────────

    def _handle_cloud_esign_token(self, payload: dict) -> None:
        """POST /api/cloud/esign/token — Request eSign token from solaceagi.com."""
        token = self._cloud_auth_token()
        if not token:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "No cloud auth token. Login at solaceagi.com first."})
            return
        status, body = self._cloud_request("POST", "/api/v1/esign/token", payload, token=token)
        self._audit_cloud_call("/api/v1/esign/token", "POST", status)
        if status == 0:
            self._queue_offline("esign_token", payload)
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Offline — queued for sync", "offline": True})
            return
        self._send_json(HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY, body)

    def _handle_cloud_esign_sign(self, payload: dict) -> None:
        """POST /api/cloud/esign/sign — Submit eSign to solaceagi.com."""
        status, body = self._cloud_request("POST", "/api/v1/esign/sign", payload)
        self._audit_cloud_call("/api/v1/esign/sign", "POST", status)
        if status == 0:
            self._queue_offline("esign_sign", payload)
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Offline — queued for sync", "offline": True})
            return
        # Also store locally for offline access
        if body.get("signed"):
            esign_dir = Path.home() / ".solace" / "esign"
            esign_dir.mkdir(parents=True, exist_ok=True)
            sig_id = body.get("signature_id", "unknown")
            (esign_dir / f"{sig_id}.json").write_text(json.dumps(body, indent=2))
        self._send_json(HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY, body)

    def _handle_cloud_esign_verify(self, payload: dict) -> None:
        """POST /api/cloud/esign/verify — Verify eSign against solaceagi.com."""
        status, body = self._cloud_request("POST", "/api/v1/esign/verify", payload)
        self._audit_cloud_call("/api/v1/esign/verify", "POST", status)
        if status == 0:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Offline — cannot verify", "offline": True})
            return
        self._send_json(HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY, body)

    def _handle_cloud_esign_chain_status(self, *, send_body: bool) -> None:
        """GET /api/cloud/esign/chain-status — Get eSign chain from solaceagi.com."""
        token = self._cloud_auth_token()
        if not token:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "No cloud auth token"}, send_body=send_body)
            return
        status, body = self._cloud_request("GET", "/api/v1/esign/chain/status", token=token)
        self._audit_cloud_call("/api/v1/esign/chain/status", "GET", status)
        self._send_json(HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY, body, send_body=send_body)

    def _handle_cloud_esign_attestations(self, *, send_body: bool) -> None:
        """GET /api/cloud/esign/attestations — List attestation statements."""
        status, body = self._cloud_request("GET", "/api/v1/esign/attestations")
        self._send_json(HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY, body, send_body=send_body)

    # ── Cloud Sync Proxy ────────────────────────────────────────────────

    def _handle_cloud_sync_push(self, payload: dict) -> None:
        """POST /api/cloud/sync/push — Push local state to solaceagi.com vault."""
        token = self._cloud_auth_token()
        if not token:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "No cloud auth token"})
            return
        settings = self.data_store.read_settings()
        sync_payload = {
            "run_id": payload.get("run_id", f"sync-{int(time.time())}"),
            "manifest": {
                "apps": payload.get("apps", []),
                "schedule": settings.get("schedule", {}),
                "keep_alive": settings.get("keep_alive", {}),
                "part11": settings.get("part11", {}),
            },
            "evidence": payload.get("evidence", []),
        }
        status, body = self._cloud_request("POST", "/api/v1/fs/sync/push", sync_payload, token=token)
        self._audit_cloud_call("/api/v1/fs/sync/push", "POST", status)
        if status == 0:
            self._queue_offline("cloud_sync_push", sync_payload)
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Offline — queued for sync", "offline": True})
            return
        settings.setdefault("sync", {})["last_push"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.data_store.write_settings(settings)
        self._send_json(HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY, body)

    def _handle_cloud_sync_pull(self, payload: dict) -> None:
        """POST /api/cloud/sync/pull — Pull state from solaceagi.com vault."""
        token = self._cloud_auth_token()
        if not token:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "No cloud auth token"})
            return
        pull_payload = {"run_id": payload.get("run_id", "latest")}
        status, body = self._cloud_request("POST", "/api/v1/fs/sync/pull", pull_payload, token=token)
        self._audit_cloud_call("/api/v1/fs/sync/pull", "POST", status)
        if status == 0:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Offline — cannot pull", "offline": True})
            return
        settings = self.data_store.read_settings()
        settings.setdefault("sync", {})["last_pull"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.data_store.write_settings(settings)
        self._send_json(HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY, body)

    def _handle_cloud_sync_status(self, *, send_body: bool) -> None:
        """GET /api/cloud/sync/status — Check sync status with solaceagi.com."""
        token = self._cloud_auth_token()
        if not token:
            settings = self.data_store.read_settings()
            sync_info = settings.get("sync", {})
            queue_count = 0
            if self._OFFLINE_QUEUE.exists():
                queue_count = sum(1 for _ in open(self._OFFLINE_QUEUE))
            self._send_json(HTTPStatus.OK, {
                "connected": False,
                "last_push": sync_info.get("last_push"),
                "last_pull": sync_info.get("last_pull"),
                "offline_queue_count": queue_count,
                "message": "Not connected to solaceagi.com — working locally",
            }, send_body=send_body)
            return
        status, body = self._cloud_request("GET", "/api/v1/fs/sync/status", token=token)
        self._audit_cloud_call("/api/v1/fs/sync/status", "GET", status)
        if status == 0:
            self._send_json(HTTPStatus.OK, {"connected": False, "offline": True,
                                             "message": "solaceagi.com unreachable — working offline"}, send_body=send_body)
            return
        body["connected"] = True
        self._send_json(HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY, body, send_body=send_body)

    # ── Cloud Evidence Proxy ────────────────────────────────────────────

    def _handle_cloud_evidence_push(self, payload: dict) -> None:
        """POST /api/cloud/evidence — Push evidence entry to solaceagi.com."""
        token = self._cloud_auth_token()
        if not token:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "No cloud auth token"})
            return
        status, body = self._cloud_request("POST", "/api/v1/evidence", payload, token=token)
        self._audit_cloud_call("/api/v1/evidence", "POST", status)
        if status == 0:
            self._queue_offline("cloud_evidence_push", payload)
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Offline — queued for sync", "offline": True})
            return
        self._send_json(HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY, body)

    # ── Cloud Billing / Tier Proxy ──────────────────────────────────────

    def _handle_cloud_billing_status(self, *, send_body: bool) -> None:
        """GET /api/cloud/billing/status — Check billing status on solaceagi.com."""
        token = self._cloud_auth_token()
        if not token:
            self._send_json(HTTPStatus.OK, {
                "tier": "free",
                "connected": False,
                "esign_limit": 0,
                "esign_remaining": 0,
                "message": "Not connected — free tier (0 eSign/mo)",
            }, send_body=send_body)
            return
        status, body = self._cloud_request("GET", "/api/v1/billing/status", token=token)
        self._audit_cloud_call("/api/v1/billing/status", "GET", status)
        if status == 0:
            self._send_json(HTTPStatus.OK, {"tier": "unknown", "connected": False,
                                             "offline": True}, send_body=send_body)
            return
        self._send_json(HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY, body, send_body=send_body)

    def _handle_cloud_user_tier(self, *, send_body: bool) -> None:
        """GET /api/cloud/user/tier — Get user tier from solaceagi.com."""
        token = self._cloud_auth_token()
        if not token:
            self._send_json(HTTPStatus.OK, {"tier": "free", "connected": False}, send_body=send_body)
            return
        status, body = self._cloud_request("GET", "/api/v1/users/tier", token=token)
        self._send_json(HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY, body, send_body=send_body)

    # ── Offline Queue Management ────────────────────────────────────────

    def _handle_offline_queue_list(self, *, send_body: bool) -> None:
        """GET /api/offline/queue — List pending offline items."""
        items = []
        if self._OFFLINE_QUEUE.exists():
            for line in self._OFFLINE_QUEUE.read_text().strip().split("\n"):
                if line.strip():
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        self._send_json(HTTPStatus.OK, {"count": len(items), "items": items}, send_body=send_body)

    def _handle_offline_flush(self, payload: dict) -> None:
        """POST /api/offline/flush — Flush offline queue to solaceagi.com."""
        token = self._cloud_auth_token()
        if not token:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "No cloud auth token — cannot flush"})
            return
        if not self._OFFLINE_QUEUE.exists():
            self._send_json(HTTPStatus.OK, {"flushed": 0, "errors": 0})
            return

        items = []
        for line in self._OFFLINE_QUEUE.read_text().strip().split("\n"):
            if line.strip():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        flushed = 0
        errors = 0
        remaining = []
        action_map = {
            "cloud_sync_push": ("POST", "/api/v1/fs/sync/push"),
            "cloud_evidence_push": ("POST", "/api/v1/evidence"),
            "esign_sign": ("POST", "/api/v1/esign/sign"),
            "esign_token": ("POST", "/api/v1/esign/token"),
        }
        for item in items:
            action = item.get("action", "")
            route = action_map.get(action)
            if not route:
                logger.warning("Unknown offline queue action: %s — dropping", action)
                errors += 1
                continue
            # Skip items that have been retried too many times (max 5 retries)
            retry_count = item.get("retry_count", 0)
            if retry_count >= 5:
                logger.warning("Dropping offline item after %d retries: %s", retry_count, action)
                errors += 1
                continue
            # Skip items older than 24 hours (tokens likely expired)
            queued_at = item.get("queued_at", "")
            if queued_at:
                try:
                    queued_time = datetime.datetime.fromisoformat(queued_at.replace("Z", "+00:00"))
                    age_hours = (datetime.datetime.now(datetime.timezone.utc) - queued_time).total_seconds() / 3600
                    if age_hours > 24:
                        logger.warning("Dropping stale offline item (%.0fh old): %s", age_hours, action)
                        errors += 1
                        continue
                except (ValueError, TypeError):
                    pass
            method, path = route
            status, body = self._cloud_request(method, path, item.get("payload"), token=token)
            if status == 0 or status >= 500:
                item["retry_count"] = retry_count + 1
                remaining.append(item)
                errors += 1
            else:
                flushed += 1
                self._audit_cloud_call(path, method, status, item.get("payload"))

        if remaining:
            with open(self._OFFLINE_QUEUE, "w") as f:
                for item in remaining:
                    f.write(json.dumps(item) + "\n")
        elif self._OFFLINE_QUEUE.exists():
            self._OFFLINE_QUEUE.unlink()

        self._send_json(HTTPStatus.OK, {"flushed": flushed, "errors": errors, "remaining": len(remaining)})

    # ─────────────────────────────────────────────────────────────────────
    # GDPR — Account Deletion + Data Export (proxy to solaceagi.com)
    # ─────────────────────────────────────────────────────────────────────

    def _handle_cloud_account_delete(self, payload: dict) -> None:
        """POST /api/cloud/account/delete — Delete user account on solaceagi.com (GDPR Art. 17)."""
        confirm_value = payload.get("confirm", "")
        if confirm_value != "DELETE":
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Confirmation required: set confirm='DELETE'"})
            return
        token = self._cloud_auth_token()
        if not token:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Not logged in. Connect to solaceagi.com first."})
            return
        status, body = self._cloud_request("DELETE", "/api/v1/account", token=token)
        self._audit_cloud_call("/api/v1/account", "DELETE", status)
        if status == 0:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {
                "error": "Cannot reach solaceagi.com. Try again later.",
                "offline": True,
            })
            return
        http_status = HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY
        self._send_json(http_status, body)

    def _handle_cloud_account_export(self, payload: dict) -> None:
        """POST /api/cloud/account/export — Export user data from solaceagi.com (GDPR Art. 20)."""
        token = self._cloud_auth_token()
        if not token:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Not logged in. Connect to solaceagi.com first."})
            return
        status, body = self._cloud_request("GET", "/api/v1/account/export", token=token)
        self._audit_cloud_call("/api/v1/account/export", "GET", status)
        if status == 0:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {
                "error": "Cannot reach solaceagi.com. Try again later.",
                "offline": True,
            })
            return
        http_status = HTTPStatus(status) if 100 <= status <= 599 else HTTPStatus.BAD_GATEWAY
        self._send_json(http_status, body)

    # ─────────────────────────────────────────────────────────────────────
    # Sync — push/pull app state to/from solaceagi.com (or local file)
    # ─────────────────────────────────────────────────────────────────────

    _SYNC_DIR: Path = Path.home() / ".solace" / "sync"

    def _handle_sync_push(self, payload: dict[str, Any]) -> None:
        """POST /api/sync/push — Push local app state to sync storage.

        Serializes app list, run history, and settings into a timestamped
        snapshot that can be pulled from another device or solaceagi.com.
        """
        self._SYNC_DIR.mkdir(parents=True, exist_ok=True)

        # Gather local state
        apps = list_apps(self.data_store.apps_root)
        settings = self.data_store.read_settings()

        # Gather run counts from all apps
        run_counts: dict[str, int] = {}
        for app in apps:
            app_id = app.get("id", "")
            outbox = self.data_store.apps_root / app_id / "outbox"
            if outbox.is_dir():
                run_counts[app_id] = len([d for d in outbox.iterdir() if d.is_dir()])

        snapshot = {
            "version": 1,
            "timestamp": time.time(),
            "timestamp_iso": datetime.datetime.now(datetime.timezone.utc).isoformat() if hasattr(datetime, 'datetime') else "",
            "apps": [{"id": a.get("id"), "name": a.get("name")} for a in apps],
            "run_counts": run_counts,
            "settings_hash": str(hash(json.dumps(settings, sort_keys=True))),
            "agent_count": len(self._detect_cli_agents()),
        }

        # Write locally
        snap_path = self._SYNC_DIR / "latest.json"
        snap_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

        # If a remote sync URL is configured, push to it
        remote_url = payload.get("remote_url") or settings.get("sync", {}).get("remote_url")
        pushed_remote = False
        if remote_url:
            try:
                req = urllib.request.Request(
                    remote_url,
                    data=json.dumps(snapshot).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    pushed_remote = resp.status == 200
            except (urllib.error.URLError, OSError) as exc:
                logger.warning("sync push to remote failed: %s", exc)

        self._send_json(HTTPStatus.OK, {
            "ok": True,
            "snapshot_path": str(snap_path),
            "pushed_remote": pushed_remote,
            "apps_count": len(apps),
            "total_runs": sum(run_counts.values()),
        })

    def _handle_sync_pull(self, payload: dict[str, Any]) -> None:
        """POST /api/sync/pull — Pull latest sync snapshot.

        Returns the most recent snapshot from local sync dir or remote.
        """
        snap_path = self._SYNC_DIR / "latest.json"

        # Try remote first if configured
        settings = self.data_store.read_settings()
        remote_url = payload.get("remote_url") or settings.get("sync", {}).get("remote_url")

        if remote_url:
            try:
                req = urllib.request.Request(remote_url, method="GET")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    remote_data = json.loads(resp.read().decode("utf-8"))
                    self._send_json(HTTPStatus.OK, {
                        "source": "remote",
                        "snapshot": remote_data,
                    })
                    return
            except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
                logger.warning("sync pull from remote failed: %s", exc)

        # Fall back to local
        if snap_path.exists():
            snapshot = json.loads(snap_path.read_text(encoding="utf-8"))
            self._send_json(HTTPStatus.OK, {
                "source": "local",
                "snapshot": snapshot,
            })
        else:
            self._send_json(HTTPStatus.OK, {
                "source": "none",
                "snapshot": None,
                "message": "No sync snapshot found. Run /api/sync/push first.",
            })

    # ─────────────────────────────────────────────────────────────────────
    # Tunnel management (cloudflared quick-tunnel or mock)
    # ─────────────────────────────────────────────────────────────────────

    def _handle_tunnel_start(self, payload: dict[str, Any]) -> None:
        """POST /tunnel/start — Start a cloudflared quick tunnel to expose local server."""
        cls = type(self)

        if cls._tunnel_proc is not None and cls._tunnel_proc.poll() is None:
            self._send_json(HTTPStatus.OK, {
                "status": "already-running",
                "public_url": cls._tunnel_url or "unknown",
                "message": "Tunnel is already running.",
            })
            return

        port = payload.get("port", cls._tunnel_local_port)
        cloudflared_path = shutil.which("cloudflared")

        if not cloudflared_path:
            # No cloudflared — return instructions to install
            self._send_json(HTTPStatus.OK, {
                "status": "not-installed",
                "public_url": None,
                "message": (
                    "cloudflared not found. Install it:\n"
                    "  Ubuntu/Debian: sudo apt install cloudflared\n"
                    "  macOS: brew install cloudflared\n"
                    "  Or: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
                ),
                "install_commands": {
                    "debian": "sudo apt install cloudflared",
                    "macos": "brew install cloudflared",
                    "manual": "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/",
                },
            })
            return

        # Start cloudflared quick tunnel (no account needed)
        try:
            proc = subprocess.Popen(
                [cloudflared_path, "tunnel", "--url", f"http://localhost:{port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            cls._tunnel_proc = proc
            cls._tunnel_started_at = time.time()
            cls._tunnel_local_port = port

            # cloudflared prints the URL to stderr — wait briefly to capture it
            public_url = None
            deadline = time.time() + 15  # wait up to 15s for URL
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                # Read stderr line by line for the URL
                # select.select on pipes only works on Unix; use polling on Windows
                if sys.platform == "win32":
                    line = proc.stderr.readline()
                else:
                    ready, _, _ = select.select([proc.stderr], [], [], 1.0)
                    if not ready:
                        continue
                    line = proc.stderr.readline()
                if line:
                    logger.info("cloudflared: %s", line.strip())
                    # cloudflared prints: "... https://xxx.trycloudflare.com ..."
                    url_match = re.search(r"(https://[a-z0-9\-]+\.trycloudflare\.com)", line)
                    if url_match:
                        public_url = url_match.group(1)
                        break

            cls._tunnel_url = public_url

            if public_url:
                self._send_json(HTTPStatus.OK, {
                    "status": "connected",
                    "public_url": public_url,
                    "local_port": port,
                    "message": f"Tunnel active! Your browser is accessible at {public_url}",
                    "pid": proc.pid,
                })
            else:
                self._send_json(HTTPStatus.OK, {
                    "status": "starting",
                    "public_url": None,
                    "local_port": port,
                    "message": "Tunnel process started but URL not yet available. Check /tunnel/status.",
                    "pid": proc.pid,
                })

        except (OSError, subprocess.SubprocessError) as exc:
            logger.error("cloudflared start failed: %s", exc)
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "status": "error",
                "public_url": None,
                "message": f"Failed to start cloudflared: {exc}",
            })

    def _handle_tunnel_stop(self) -> None:
        """POST /tunnel/stop — Stop the active cloudflared tunnel."""
        cls = type(self)

        if cls._tunnel_proc is None or cls._tunnel_proc.poll() is not None:
            cls._tunnel_proc = None
            cls._tunnel_url = None
            cls._tunnel_started_at = None
            self._send_json(HTTPStatus.OK, {
                "status": "disconnected",
                "public_url": None,
                "message": "No tunnel was running.",
            })
            return

        try:
            cls._tunnel_proc.terminate()
            cls._tunnel_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls._tunnel_proc.kill()
            cls._tunnel_proc.wait(timeout=3)

        old_url = cls._tunnel_url
        cls._tunnel_proc = None
        cls._tunnel_url = None
        cls._tunnel_started_at = None

        self._send_json(HTTPStatus.OK, {
            "status": "disconnected",
            "public_url": None,
            "message": f"Tunnel closed. Was: {old_url or 'unknown'}",
        })

    def _handle_tunnel_status(self) -> None:
        """GET /tunnel/status — Check if tunnel is running and return URL."""
        cls = type(self)

        running = cls._tunnel_proc is not None and cls._tunnel_proc.poll() is None

        if not running:
            # Clean up stale state
            if cls._tunnel_proc is not None:
                cls._tunnel_proc = None
                cls._tunnel_url = None
                cls._tunnel_started_at = None

        uptime = 0
        if running and cls._tunnel_started_at:
            uptime = int(time.time() - cls._tunnel_started_at)

        cloudflared_path = shutil.which("cloudflared")

        self._send_json(HTTPStatus.OK, {
            "running": running,
            "public_url": cls._tunnel_url if running else None,
            "local_port": cls._tunnel_local_port if running else None,
            "uptime_seconds": uptime,
            "cloudflared_installed": cloudflared_path is not None,
            "cloudflared_path": cloudflared_path,
            "pid": cls._tunnel_proc.pid if running and cls._tunnel_proc else None,
        })

    # ─────────────────────────────────────────────────────────────────────

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        payload = json.loads(raw_body.decode("utf-8") or "{}")
        return payload if isinstance(payload, dict) else {}

    def _send_json(self, status: int, payload: dict[str, Any], *, send_body: bool = True) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print("[web]", format % args)


def build_handler_class(data_store: SolaceDataStore) -> type[SlugRequestHandler]:
    class BoundSlugRequestHandler(SlugRequestHandler):
        pass

    BoundSlugRequestHandler.data_store = data_store
    return BoundSlugRequestHandler


def create_server(host: str, port: int, *, data_store: SolaceDataStore | None = None) -> ThreadingHTTPServer:
    store = data_store or SolaceDataStore()
    return ThreadingHTTPServer((host, port), build_handler_class(store))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="python3 web/server.py",
        description="Solace Browser Web Server — serves the browser UI and API",
    )
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8791")),
                        help="Port to listen on (default: 8791, env: PORT)")
    parser.add_argument("--host", default=os.environ.get("BIND_ADDR", "127.0.0.1"),
                        help="Host to bind to (default: 127.0.0.1, env: BIND_ADDR)")
    args = parser.parse_args()

    os.chdir(ROOT)

    # Auto-detect CLI agents on startup (cached to ~/.solace/cli-agents-cache.json)
    cli_result = _detect_cli_agents(force=True)
    installed = cli_result["installed_ids"]
    if installed:
        print(f"  AI Agents detected: {', '.join(installed)} ({len(installed)}/{len(CLI_AGENT_DEFS)})")
        print(f"  POST /api/cli-agents/generate — Ollama-compatible inference via any detected CLI")
    else:
        print("  No AI coding CLIs detected. Install claude, codex, gemini, etc. to enable AI agent mode.")

    server = create_server(args.host, args.port)
    print(f"Serving Solace Browser web at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
