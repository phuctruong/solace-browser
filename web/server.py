#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import re
import sys
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
    "download": "download.html",
    "machine-dashboard": "machine-dashboard.html",
    "tunnel-connect": "tunnel-connect.html",
    "style-guide": "style-guide.html",
    "app-store": "app-store.html",
    "app-detail": "app-detail.html",
    "settings": "settings.html",
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
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

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
