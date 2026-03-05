#!/usr/bin/env python3
from __future__ import annotations

import collections
import copy
import json
import os
import re
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


SLUG_MAP = {
    "": "home.html",
    "home": "home.html",
    "start": "start.html",
    "download": "download.html",
    "machine-dashboard": "machine-dashboard.html",
    "schedule": "schedule.html",
    "tunnel-connect": "tunnel-connect.html",
    "style-guide": "style-guide.html",
    "app-store": "app-store.html",
    "app-detail": "app-detail.html",
    "settings": "settings.html",
    "demo": "demo.html",
    "docs": "docs.html",
    "docs/quick-start": "docs/quick-start.html",
    "docs/mcp": "docs/mcp.html",
    "docs/oauth3": "docs/oauth3.html",
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

        # SSE stream: /api/yinyang/events
        if request_path == "/api/yinyang/events":
            self._handle_sse_events()
            return

        if (
            request_path.startswith("/api/apps")
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
        """Inject Cache-Control: no-store for JS and CSS assets."""
        path = urlsplit(self.path).path
        if path.endswith(('.js', '.css')):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.send_header('Pragma', 'no-cache')
        super().end_headers()

    def _handle_api_get(self, *, send_body: bool) -> None:
        request_path = urlsplit(self.path).path
        query = parse_qs(urlsplit(self.path).query)
        app_detail_match = re.fullmatch(r"/api/apps/([^/]+)", request_path)
        app_inbox_match = re.fullmatch(r"/api/apps/([^/]+)/inbox", request_path)
        app_outbox_match = re.fullmatch(r"/api/apps/([^/]+)/outbox", request_path)

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
            if request_path == "/api/evidence/list":
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
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "approval-required",
                    "public_url": "Waiting for approval",
                    "message": "Grant tunnel.connect before the browser exposes a public URL.",
                },
            )
            return
        if request_path == "/tunnel/stop":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "disconnected",
                    "public_url": "Not connected",
                    "message": "Tunnel has been closed. Nothing is exposed.",
                },
            )
            return

        # App run: POST /api/apps/{id}/run  — dogfood execution endpoint
        app_run_match = re.fullmatch(r"/api/apps/([^/]+)/run", request_path)
        if app_run_match:
            self._handle_app_run(app_run_match.group(1), payload)
            return

        # YinYang chat: /api/yinyang/chat
        if request_path == "/api/yinyang/chat":
            self._handle_yinyang_chat(payload)
            return

        # YinYang notify (agent pushes notification): /api/yinyang/notify
        if request_path == "/api/yinyang/notify":
            self._handle_yinyang_notify(payload)
            return

        # Schedule Viewer: approve / cancel
        if request_path.startswith("/api/schedule/approve/"):
            run_id = request_path.split("/api/schedule/approve/")[-1]
            self._handle_schedule_approve(run_id, payload)
            return
        if request_path.startswith("/api/schedule/cancel/"):
            run_id = request_path.split("/api/schedule/cancel/")[-1]
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
                                "status":   obj.get("status", "success"),
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
                        except Exception:
                            pass
                except Exception:
                    pass
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
                        except Exception:
                            pass
        # Sort by started_at descending
        activities.sort(key=lambda a: a.get("started_at") or "", reverse=True)
        self._send_json(HTTPStatus.OK, {"activities": activities, "total": len(activities)},
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
                        except Exception:
                            pass
        self._send_json(HTTPStatus.OK, {"queue": pending, "count": len(pending)},
                        send_body=send_body)

    def _handle_schedule_upcoming(self, *, send_body: bool) -> None:
        """Return scheduled future runs from settings cron config."""
        settings = self.data_store.read_settings()
        schedule_config = settings.get("schedule", {})
        upcoming = []
        for app_id, cfg in schedule_config.items():
            if cfg.get("enabled"):
                upcoming.append({
                    "app_id": app_id,
                    "pattern": cfg.get("pattern", "manual"),
                    "next_run": cfg.get("next_run"),
                    "status": "scheduled",
                })
        self._send_json(HTTPStatus.OK, {"upcoming": upcoming, "count": len(upcoming)},
                        send_body=send_body)

    def _handle_settings_export(self, send_body: bool = True) -> None:
        """GET /api/settings/export — Export sanitized settings for cloud sync.

        Strips API keys (llm.api_key, cloud.api_key) before returning.
        Returns settings + metadata envelope for cloud vault.
        """
        import time as _time
        settings = self.data_store.read_settings()
        # Sanitize: strip sensitive fields
        sanitized = {k: v for k, v in settings.items() if k not in ("api_key", "llm_api_key")}
        llm = sanitized.get("llm", {})
        sanitized["llm"] = {k: v for k, v in llm.items() if k not in ("api_key",)}
        cloud = sanitized.get("cloud", {})
        sanitized["cloud"] = {k: v for k, v in cloud.items() if k not in ("api_key",)}
        envelope = {
            "format": "solace-browser-settings-v1",
            "exported_at": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "settings": sanitized,
        }
        self._send_json(HTTPStatus.OK, envelope, send_body=send_body)

    def _handle_settings_import(self, payload: dict) -> None:
        """POST /api/settings/import — Import settings from cloud sync envelope.

        Accepts: {settings: {...}} or raw settings dict.
        Merges into existing settings (does not overwrite API keys already set).
        """
        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "payload must be an object"})
            return
        # Support both envelope format and raw settings
        incoming = payload.get("settings", payload)
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
        self._send_json(HTTPStatus.OK, {"ok": True, "keys_imported": list(incoming.keys()), "settings": written})

    def _handle_evidence_list(self, send_body: bool = True) -> None:
        """GET /api/evidence/list — List all esign records from audit directory.

        Returns records from ~/.solace/audit/esign-*.jsonl sorted by timestamp (newest first).
        """
        import datetime as _dt
        audit_dir = Path.home() / ".solace" / "audit"
        records = []
        if audit_dir.exists():
            for esign_file in sorted(audit_dir.glob("esign-*.jsonl"),
                                     key=lambda f: f.stat().st_mtime, reverse=True)[:50]:
                try:
                    for line in esign_file.read_text(encoding="utf-8").strip().split("\n"):
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        records.append({
                            "run_id": record.get("run_id", ""),
                            "user_id": record.get("user_id", ""),
                            "meaning": record.get("meaning", ""),
                            "event_type": record.get("event_type", "ESIGN"),
                            "esign_hash": record.get("esign_hash", record.get("path", ""))[:16] + "…",
                            "esign_hash_full": record.get("esign_hash", ""),
                            "screenshot": record.get("screenshot"),
                            "timestamp": record.get("timestamp", record.get("sealed_at", "")),
                        })
                except Exception:
                    continue
        self._send_json(HTTPStatus.OK, {
            "count": len(records),
            "records": records[:50],
            "audit_dir": str(audit_dir),
        }, send_body=send_body)

    def _handle_schedule_approve(self, run_id: str, payload: dict) -> None:
        """Approve a pending run — write approved_v1.json + audit entry."""
        import time as _time
        outbox = Path.home() / ".solace" / "outbox" / "apps"
        approved_in_outbox = False
        approval_record = {
            "run_id": run_id,
            "approved_by": payload.get("approved_by", "user"),
            "timestamp": payload.get("timestamp", _time.strftime("%Y-%m-%dT%H:%M:%SZ")),
            "approval_type": "standard",
        }
        for app_dir in (outbox.iterdir() if outbox.exists() else []):
            run_dir = app_dir / run_id if app_dir.is_dir() else None
            if run_dir and run_dir.exists():
                (run_dir / "approved_v1.json").write_text(json.dumps(approval_record, indent=2))
                approved_in_outbox = True
                break
        # Always write audit log (Part 11 — every approval decision is logged)
        audit_dir = Path.home() / ".solace" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        with open(audit_dir / "schedule_actions.jsonl", "a") as f:
            f.write(json.dumps({"event": "approved", "in_outbox": approved_in_outbox,
                                **approval_record}) + "\n")

        # Auto-generate e-sign record for approved run (FDA Part 11 §11.100)
        import hashlib as _hashlib
        user_id = payload.get("approved_by", "user")
        ts = approval_record["timestamp"]
        meaning = "reviewed_and_approved"
        action_desc = f"Approved scheduled run {run_id}"
        action_hash = _hashlib.sha256(action_desc.encode()).hexdigest()
        esign_hash = _hashlib.sha256((user_id + ts + meaning + action_hash).encode()).hexdigest()
        esign_record = {"event_type": "ESIGN", "user_id": user_id, "run_id": run_id,
                        "meaning": meaning, "action_description": action_desc,
                        "action_hash": action_hash, "esign_hash": esign_hash,
                        "timestamp": ts, "sealed_at": ts}
        with open(audit_dir / f"esign-{run_id}.jsonl", "a") as f:
            f.write(json.dumps(esign_record) + "\n")

        # Capture screenshot as Part 11 visual evidence (best-effort, non-blocking)
        screenshot_path: str | None = None
        try:
            import urllib.request as _urlreq
            screenshot_payload = json.dumps({"filename": f"esign-{run_id}.png"}).encode()
            req = _urlreq.Request(
                "http://localhost:9222/api/screenshot",
                data=screenshot_payload,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with _urlreq.urlopen(req, timeout=5) as resp:
                screenshot_result = json.loads(resp.read())
                screenshot_path = screenshot_result.get("filepath")
                # Append screenshot path to esign record
                esign_record["screenshot"] = screenshot_path
                with open(audit_dir / f"esign-{run_id}.jsonl", "a") as f:
                    f.write(json.dumps({"event_type": "SCREENSHOT", "path": screenshot_path,
                                        "run_id": run_id, "timestamp": ts}) + "\n")
        except Exception:
            pass  # Screenshot failure must never block approval

        self._send_json(HTTPStatus.OK, {"ok": True, "run_id": run_id,
                                        "in_outbox": approved_in_outbox,
                                        "esign_hash": esign_hash,
                                        "screenshot": screenshot_path})

    def _handle_schedule_cancel(self, run_id: str, payload: dict) -> None:
        """Cancel a pending run — write cancelled.json + audit entry."""
        import time as _time
        audit_dir = Path.home() / ".solace" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "run_id": run_id,
            "event": "cancelled",
            "reason": payload.get("reason", "user_rejected"),
            "timestamp": payload.get("timestamp", _time.strftime("%Y-%m-%dT%H:%M:%SZ")),
        }
        with open(audit_dir / "schedule_actions.jsonl", "a") as f:
            f.write(json.dumps(record) + "\n")
        self._send_json(HTTPStatus.OK, {"ok": True, "run_id": run_id})

    def _handle_schedule_plan(self, payload: dict) -> None:
        """Add a future run to the schedule config."""
        app_id = payload.get("app_id", "")
        pattern = payload.get("pattern", "manual")
        if not app_id:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "app_id required"})
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
    server = create_server(args.host, args.port)
    print(f"Serving Solace Browser web at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
