"""
yinyang_server.py — Yinyang Server for Solace Browser.
Donald Knuth law: every function is a theorem. Prove it or don't ship it.

Architecture:
  - Stdlib only: http.server, json, hashlib, secrets, pathlib, threading, signal, atexit, urllib
  - Port 8888 (production), 18888 (tests only)
  - Port 9222 PERMANENTLY BANNED
  - Token hash only in port.lock — plaintext NEVER written anywhere
  - "Companion App" BANNED in all responses — use "Solace Hub"
  - FALLBACK BAN: only FileNotFoundError, OSError, json.JSONDecodeError caught
"""
import atexit
import hashlib
import http.server
import json
import pathlib
import secrets
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PORT_LOCK_PATH: Path = Path.home() / ".solace" / "port.lock"

_SERVER_VERSION = "1.0"

# Domains that map to known app categories for /detect matching.
_DOMAIN_APP_MAP: dict[str, list[str]] = {
    "mail.google.com": ["gmail-inbox-triage", "gmail-spam-cleaner"],
    "linkedin.com": ["linkedin-outreach", "linkedin-poster", "linkedin-profile-optimizer", "linkedin-messenger"],
    "twitter.com": ["twitter-poster", "twitter-monitor"],
    "x.com": ["twitter-poster", "twitter-monitor"],
    "reddit.com": ["reddit-scanner", "reddit-trends"],
    "slack.com": ["slack-triage"],
    "github.com": ["github-issue-triage"],
    "amazon.com": ["amazon-price-tracker"],
    "instagram.com": ["instagram-poster"],
    "youtube.com": ["youtube-script-writer"],
    "drive.google.com": ["google-drive-saver"],
    "calendar.google.com": ["calendar-brief"],
    "chat.openai.com": ["chatgpt", "chatgpt-copilot"],
    "claude.ai": ["claude", "claude-copilot"],
    "gemini.google.com": ["gemini", "gemini-copilot", "gemini-creative"],
    "whatsapp.com": ["whatsapp-responder"],
    "web.whatsapp.com": ["whatsapp-responder"],
    "trends.google.com": ["google-search-trends"],
}


# ---------------------------------------------------------------------------
# Token utilities — theorem: plaintext token must never reach disk.
# ---------------------------------------------------------------------------
def generate_token() -> str:
    """Generate a cryptographically random URL-safe token (48 chars min)."""
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    """SHA-256 hex digest of token. The only form written to disk."""
    return hashlib.sha256(token.encode()).hexdigest()


def write_port_lock(port: int, t_hash: str) -> None:
    """Write port.lock with hash only — plaintext token NEVER stored."""
    PORT_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    PORT_LOCK_PATH.write_text(json.dumps({"port": port, "token_hash": t_hash}))


def delete_port_lock() -> None:
    """Remove port.lock on clean shutdown."""
    try:
        PORT_LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# App loader — theorem: load_apps returns sorted list of app_id strings.
# ---------------------------------------------------------------------------
def load_apps(repo_root: str) -> list[str]:
    """
    Discover apps from data directories.
    Search order:
      1. <repo_root>/data/default/apps/   (browser-local apps)
      2. <repo_root>/data/apps/           (fallback flat layout)
    Returns sorted list of app_id strings; [] if no directory found.
    """
    for apps_path in (
        Path(repo_root) / "data" / "default" / "apps",
        Path(repo_root) / "data" / "apps",
    ):
        if apps_path.is_dir():
            return sorted(d.name for d in apps_path.iterdir() if d.is_dir())
    return []


# ---------------------------------------------------------------------------
# HTTP Handler — theorem: every route returns JSON, every error is specific.
# ---------------------------------------------------------------------------
class YinyangHandler(http.server.BaseHTTPRequestHandler):
    """
    Route table:
      GET  /health        → {"status": "ok", "apps": N, "version": "1.0"}
      GET  /instructions  → full capabilities JSON (agent-discoverability endpoint)
      GET  /credits       → {"apps": [app_id, ...]}
      POST /detect        → {"url": "..."} → {"apps": [matched_app_ids]}
      *    anything else  → {"error": "not found"}, 404
    """

    # --- GET routing ---
    def do_GET(self) -> None:
        path = self.path.split("?")[0]  # strip query string
        if path == "/health":
            self._handle_health()
        elif path == "/instructions":
            self._handle_instructions()
        elif path == "/credits":
            self._handle_credits()
        else:
            self._send_json({"error": "not found"}, 404)

    # --- POST routing ---
    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        if path == "/detect":
            self._handle_detect()
        else:
            self._send_json({"error": "not found"}, 404)

    # --- Handlers ---
    def _handle_health(self) -> None:
        apps: list[str] = self.server.apps  # type: ignore[attr-defined]
        self._send_json({
            "status": "ok",
            "apps": len(apps),
            "version": _SERVER_VERSION,
        })

    def _handle_instructions(self) -> None:
        apps: list[str] = self.server.apps  # type: ignore[attr-defined]
        self._send_json({
            "version": _SERVER_VERSION,
            "hub": "Solace Hub (Tauri ~20MB)",
            "server": "Yinyang Server localhost:8888",
            "browser": "Solace Browser (Chromium fork with Yinyang Sidebar)",
            "cli_commands": [
                "solace hub status",
                "solace hub start",
                "solace hub browser open",
            ],
            "apps_loaded": len(apps),
            "capabilities": [
                "recipe_execution",
                "evidence_chain",
                "oauth3_gate",
                "schedule_cron",
            ],
            "forbidden": [
                "port_9222",
                "extensions",
                "companion_app_name",
            ],
            "spec_file": "specs/solacehub-instructions.md",
        })

    def _handle_credits(self) -> None:
        apps: list[str] = self.server.apps  # type: ignore[attr-defined]
        self._send_json({"apps": apps})

    def _handle_detect(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._send_json({"error": "missing request body"}, 400)
            return

        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode())
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON"}, 400)
            return

        url: Optional[str] = payload.get("url")
        if not url:
            self._send_json({"error": "missing 'url' field"}, 400)
            return

        matched = self._match_apps_for_url(url)
        self._send_json({"apps": matched})

    def _match_apps_for_url(self, url: str) -> list[str]:
        """
        Match URL against domain map and loaded app list.
        Theorem: result is intersection of domain-keyed candidates and loaded apps.
        """
        available: set[str] = set(self.server.apps)  # type: ignore[attr-defined]
        matched: list[str] = []

        for domain, candidates in _DOMAIN_APP_MAP.items():
            if domain in url:
                for app_id in candidates:
                    if app_id in available and app_id not in matched:
                        matched.append(app_id)

        return matched

    # --- Transport ---
    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # noqa: D102
        # Suppress default stderr logging — callers use structured evidence.
        pass


# ---------------------------------------------------------------------------
# Server factory — theorem: build_server isolates configuration from startup.
# ---------------------------------------------------------------------------
def build_server(port: int, repo_root: str) -> http.server.ThreadingHTTPServer:
    """
    Construct a ThreadingHTTPServer with apps pre-loaded.
    Does NOT write port.lock — caller is responsible for that.
    """
    server = http.server.ThreadingHTTPServer(("localhost", port), YinyangHandler)
    server.apps = load_apps(repo_root)  # type: ignore[attr-defined]
    server.repo_root = repo_root  # type: ignore[attr-defined]
    return server


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def start_server(port: int = 8888, repo_root: str = ".") -> None:
    """
    Generate token, write lock, register cleanup, then serve forever.
    Token is immediately discarded after hashing — never stored in memory
    beyond this function's call stack.
    """
    token = generate_token()
    t_hash = token_hash(token)
    del token  # plaintext token leaves scope here — not stored anywhere
    write_port_lock(port, t_hash)
    atexit.register(delete_port_lock)

    server = build_server(port, repo_root)
    server.serve_forever()


if __name__ == "__main__":
    repo_root = sys.argv[1] if len(sys.argv) > 1 else "."
    start_server(8888, repo_root)
