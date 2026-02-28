#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
SLUG_MAP = {
    "": "home.html",
    "home": "home.html",
    "download": "download.html",
    "machine-dashboard": "machine-dashboard.html",
    "tunnel-connect": "tunnel-connect.html",
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


class SlugRequestHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        request_path = urlsplit(path).path
        if request_path.startswith("/css/") or request_path.startswith("/js/") or request_path.startswith("/images/"):
            return str(ROOT / request_path.lstrip("/"))
        if request_path in ("/favicon.ico", "/robots.txt"):
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

    def _handle_request(self, send_body: bool) -> None:
        request_path = urlsplit(self.path).path
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
            if request_path in ("/home.html", "/index.html"):
                target = "/"
            else:
                target = request_path[:-5]
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

    def _handle_post(self) -> None:
        request_path = urlsplit(self.path).path
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        payload = json.loads(raw_body.decode("utf-8") or "{}")

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

    def _send_json(self, status: int, payload: dict, *, send_body: bool = True) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print("[web]", format % args)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8791"))
    host = os.environ.get("BIND_ADDR", "127.0.0.1")
    os.chdir(ROOT)
    server = ThreadingHTTPServer((host, port), SlugRequestHandler)
    print(f"Serving Solace Browser web at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
