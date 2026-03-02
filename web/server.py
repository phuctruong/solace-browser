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

from companion.apps import discover_installed_apps
from inbox_outbox import AppFolderNotFoundError, InboxOutboxManager


SLUG_MAP = {
    "": "home.html",
    "home": "home.html",
    "start": "start.html",
    "download": "download.html",
    "machine-dashboard": "machine-dashboard.html",
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
    ) -> None:
        self.solace_home = Path(solace_home or "~/.solace").expanduser().resolve()
        self.apps_root = self.solace_home / "apps"
        self.default_library_root = Path(default_library_root or REPO_ROOT / "data" / "default" / "apps").resolve()
        self.settings_path = self.solace_home / "settings.json"

    def list_apps(self, *, category: str | None = None, status: str | None = None) -> dict[str, Any]:
        apps: list[dict[str, Any]] = []
        for app_root in self._app_index().values():
            manifest = _safe_read_yaml(app_root / "manifest.yaml")
            app_summary = {
                "id": manifest.get("id", app_root.name),
                "name": manifest.get("name", app_root.name),
                "category": manifest.get("category", "uncategorized"),
                "status": manifest.get("status", "available"),
                "safety": manifest.get("safety", "A"),
                "site": manifest.get("site", ""),
                "description": manifest.get("description", ""),
                "type": manifest.get("type", "standard"),
            }
            if category and app_summary["category"] != category:
                continue
            if status and app_summary["status"] != status:
                continue
            apps.append(app_summary)
        apps.sort(key=lambda item: str(item["name"]).lower())
        return {"apps": apps}

    def get_app_detail(self, app_id: str) -> dict[str, Any]:
        app_root = self._get_app_root(app_id)
        manager = InboxOutboxManager(apps_root=app_root.parent)
        manifest = manager.read_manifest(app_id)
        detail = {
            "id": manifest.get("id", app_id),
            "name": manifest.get("name", app_id),
            "description": manifest.get("description", ""),
            "category": manifest.get("category", "uncategorized"),
            "status": manifest.get("status", "available"),
            "safety": manifest.get("safety", "A"),
            "site": manifest.get("site", ""),
            "type": manifest.get("type", "standard"),
            "scopes": manifest.get("scopes", []),
            "budgets": manager.read_budget(app_id),
            "inbox": manager.list_inbox(app_id),
            "outbox": manager.list_outbox(app_id),
            "recent_runs": manager.list_runs(app_id),
            "partners": manifest.get("partners", {}),
            "orchestrates": manifest.get("orchestrates", []),
        }
        return detail

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

    def _app_index(self) -> dict[str, Path]:
        installed = discover_installed_apps(self.apps_root)
        if installed:
            return {record.app_id: record.app_root for record in installed}
        return {record.app_id: record.app_root for record in discover_installed_apps(self.default_library_root)}

    def _get_app_root(self, app_id: str) -> Path:
        app_root = self._app_index().get(app_id)
        if app_root is None:
            raise AppFolderNotFoundError(app_id)
        return app_root


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

        if request_path.startswith("/api/apps") or request_path == SETTINGS_ROUTE:
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
        if request_path.endswith(".html"):
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

    def _handle_api_get(self, *, send_body: bool) -> None:
        request_path = urlsplit(self.path).path
        query = parse_qs(urlsplit(self.path).query)
        app_detail_match = re.fullmatch(r"/api/apps/([^/]+)", request_path)
        app_inbox_match = re.fullmatch(r"/api/apps/([^/]+)/inbox", request_path)
        app_outbox_match = re.fullmatch(r"/api/apps/([^/]+)/outbox", request_path)

        try:
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
        except AppFolderNotFoundError:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "App not found"}, send_body=send_body)
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

        # YinYang chat: /api/yinyang/chat
        if request_path == "/api/yinyang/chat":
            self._handle_yinyang_chat(payload)
            return

        # YinYang notify (agent pushes notification): /api/yinyang/notify
        if request_path == "/api/yinyang/notify":
            self._handle_yinyang_notify(payload)
            return

        # Fun pack download: /api/fun-packs/download
        if request_path == "/api/fun-packs/download":
            self._handle_fun_pack_download(payload)
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
    port = int(os.environ.get("PORT", "8791"))
    host = os.environ.get("BIND_ADDR", "127.0.0.1")
    os.chdir(ROOT)
    server = create_server(host, port)
    print(f"Serving Solace Browser web at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
