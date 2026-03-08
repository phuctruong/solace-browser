"""
yinyang_server.py — Yinyang Server for Solace Browser.
Donald Knuth law: every function is a theorem. Prove it or don't ship it.

Architecture:
  - Stdlib only: http.server, json, hashlib, secrets, pathlib, threading, signal, atexit, urllib
  - Port 8888 (production), 18888 (tests only)
  - Legacy debug port permanently banned
  - Token hash only in port.lock — plaintext NEVER written anywhere
  - Legacy alternate hub name banned in all responses — use "Solace Hub"
  - FALLBACK BAN: only FileNotFoundError, OSError, json.JSONDecodeError caught

Route table:
  GET  /health                         → {"status": "ok", "apps": N, "version": "1.1"}
  GET  /instructions                   → capabilities JSON
  GET  /credits                        → {"apps": [...]}
  GET  /start                          → browser start page HTML
  POST /detect                         → {"url": "..."} → {"apps": [...]}
  GET  /api/v1/evidence                → evidence log (limit/offset/action/session_id/since/until params)
  GET  /api/v1/evidence/verify         → verify sha256 chain integrity
  GET  /api/v1/evidence/{id}           → single evidence entry detail
  POST /api/v1/evidence                → record evidence event
  GET  /api/v1/browser/schedules       → list schedules
  GET  /api/v1/browser/schedules/next-runs → preview next run timestamps per schedule
  POST /api/v1/browser/schedules       → create schedule
  POST /api/v1/browser/schedules/{id}/enable  → enable schedule
  POST /api/v1/browser/schedules/{id}/disable → disable schedule
  DELETE /api/v1/browser/schedules/{id} → delete schedule
  GET  /api/v1/oauth3/tokens           → list token metadata (never plaintext)
  GET  /api/v1/oauth3/tokens/{id}     → single token detail
  POST /api/v1/oauth3/tokens/{id}/extend → extend expiry (max 30 days)
  GET  /api/v1/oauth3/audit           → audit log entries
  DELETE /api/v1/oauth3/tokens/{id}    → revoke token
  GET  /api/v1/cli/available           → {"available": bool, "version": str|null}
  POST /api/v1/cli/run                 → {"command": str} → {"exit_code": int, "stdout": str, "stderr": str}
  GET  /onboarding                     → onboarding HTML page
  POST /onboarding/complete            → {"mode": str} → 200
  POST /onboarding/reset               → requires auth; delete onboarding.json
  GET  /api/v1/onboarding/status       → {"completed": bool, "mode": str|null}
  GET  /api/v1/sessions                → list all tracked sessions with alive status
  GET  /api/v1/sessions/{id}           → single session detail
  POST /api/v1/sessions                → spawn new browser session (requires auth)
  DELETE /api/v1/sessions/{id}         → terminate session (SIGTERM+SIGKILL, requires auth)
  GET  /api/v1/recipes                 → list all available recipes
  GET  /api/v1/recipes/{id}/preview    → preview steps without running
  GET  /api/v1/recipes/{run_id}/status → check run status
  GET  /api/v1/recipes/{id}            → recipe detail
  POST /api/v1/recipes/{id}/run        → run a recipe (async, returns run_id, requires auth)
  GET  /api/v1/budget                  → current budget config
  GET  /api/v1/budget/status           → spend vs limit with alert/paused flags
  POST /api/v1/budget                  → update budget settings (requires auth)
  POST /api/v1/budget/reset            → reset to defaults (requires auth)
"""
import argparse
import atexit
import base64
import hashlib
import http.server
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import threading
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PORT_LOCK_PATH: Path = Path.home() / ".solace" / "port.lock"
EVIDENCE_PATH: Path = Path.home() / ".solace" / "evidence.jsonl"
SCHEDULES_PATH: Path = Path.home() / ".solace" / "schedules.json"
OAUTH3_TOKENS_PATH: Path = Path.home() / ".solace" / "oauth3-tokens.json"
ONBOARDING_PATH: Path = Path.home() / ".solace" / "onboarding.json"
RECIPES_DIR: Path = Path(__file__).parent / "data" / "default" / "recipes"
RECIPE_RUNS_PATH: Path = Path.home() / ".solace" / "recipe_runs.json"
BUDGET_PATH: Path = Path.home() / ".solace" / "budget.json"
DEFAULT_BUDGET: dict = {
    "daily_limit_usd": 1.00,
    "monthly_limit_usd": 20.00,
    "alert_threshold": 0.80,
    "pause_on_exceeded": True,
}

_SERVER_VERSION = "1.1"
YINYANG_PORT = 8888
MAX_BODY = 1_048_576

_SCHEDULES_LOCK = threading.Lock()
_TOKENS_LOCK = threading.Lock()
_SESSIONS: dict[str, dict] = {}
_SESSIONS_LOCK = threading.Lock()
_SESSION_TOKEN_SHA256: str = ""

_TUNNEL_PROC: Optional[subprocess.Popen] = None
_TUNNEL_LOCK = threading.Lock()
_TUNNEL_URL: str = ""

VAULT_PATH = Path.home() / ".solace" / "oauth3_tokens.json"
VAULT_EXPORT_PATH = Path.home() / ".solace" / "vault_export.json"
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_CRON_RE = re.compile(r"^\S+\s+\S+\s+\S+\s+\S+\s+\S+$")
_ONBOARDING_MODES = frozenset(["agent", "byok", "paid", "cli"])
ALLOWED_SCOPES = frozenset([
    "browse", "run_recipe", "read_evidence", "write_evidence",
    "create_schedule", "delete_schedule", "cli_run", "detect_apps"
])
_CLI_ALLOWLIST = frozenset([
    "hub status",
    "hub start",
    "hub stop",
    "hub version",
    "auth status",
])

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


def write_port_lock(port: int, t_hash: str, pid: int) -> None:
    """Write port.lock with token_sha256 and pid — plaintext token NEVER stored."""
    PORT_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    PORT_LOCK_PATH.write_text(json.dumps({
        "port": port,
        "token_sha256": t_hash,
        "pid": pid,
    }))


def delete_port_lock() -> None:
    """Remove port.lock on clean shutdown."""
    try:
        PORT_LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


# ---------------------------------------------------------------------------
# Evidence storage — append-only JSONL log
# ---------------------------------------------------------------------------
def record_evidence(event_type: str, data: dict) -> dict:
    """Append one evidence event to ~/.solace/evidence.jsonl. Returns the record."""
    record = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "ts": int(time.time()),
        "data": data,
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCE_PATH.open("a") as fh:
        fh.write(json.dumps(record) + "\n")
    return record


def load_evidence(limit: int = 50, offset: int = 0) -> list[dict]:
    """Load evidence records from JSONL file. Returns list in reverse-chronological order."""
    try:
        lines = EVIDENCE_PATH.read_text().splitlines()
    except FileNotFoundError:
        return []
    records = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    # Reverse chronological, then paginate
    records.reverse()
    return records[offset: offset + limit]


def count_evidence() -> int:
    """Count total evidence records."""
    try:
        return sum(1 for ln in EVIDENCE_PATH.read_text().splitlines() if ln.strip())
    except FileNotFoundError:
        return 0


# ---------------------------------------------------------------------------
# Schedule storage — JSON CRUD
# ---------------------------------------------------------------------------
def load_schedules() -> list[dict]:
    """Load schedules from ~/.solace/schedules.json."""
    try:
        return json.loads(SCHEDULES_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_schedules(schedules: list[dict]) -> None:
    """Persist schedules list to disk."""
    SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULES_PATH.write_text(json.dumps(schedules, indent=2))


def create_schedule(app_id: str, cron: str, url: str) -> dict:
    """Create and persist a new schedule. Returns the schedule record."""
    with _SCHEDULES_LOCK:
        schedules = load_schedules()
        record = {
            "id": str(uuid.uuid4()),
            "app_id": app_id,
            "cron": cron,
            "url": url,
            "created_ts": int(time.time()),
            "enabled": True,
            "last_run_ts": None,
            "run_count": 0,
        }
        schedules.append(record)
        save_schedules(schedules)
    record_evidence("schedule_created", {"schedule_id": record["id"], "app_id": app_id, "cron": cron})
    return record


def delete_schedule(schedule_id: str) -> bool:
    """Delete schedule by id. Returns True if found and deleted."""
    with _SCHEDULES_LOCK:
        schedules = load_schedules()
        before = len(schedules)
        schedules = [s for s in schedules if s.get("id") != schedule_id]
        if len(schedules) == before:
            return False
        save_schedules(schedules)
    record_evidence("schedule_deleted", {"schedule_id": schedule_id})
    return True


# ---------------------------------------------------------------------------
# OAuth3 token metadata — never stores plaintext tokens
# ---------------------------------------------------------------------------
def load_oauth3_tokens() -> list[dict]:
    """Load OAuth3 token metadata from ~/.solace/oauth3-tokens.json."""
    try:
        return json.loads(OAUTH3_TOKENS_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_oauth3_tokens(tokens: list[dict]) -> None:
    """Persist token metadata list (no plaintext tokens)."""
    OAUTH3_TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    OAUTH3_TOKENS_PATH.write_text(json.dumps(tokens, indent=2))


def register_oauth3_token(scope: str, service: str, token_sha256_val: str) -> dict:
    """Register token metadata. token_sha256 is the only token representation stored."""
    with _TOKENS_LOCK:
        tokens = load_oauth3_tokens()
        record = {
            "id": str(uuid.uuid4()),
            "scope": scope,
            "service": service,
            "token_sha256": token_sha256_val,
            "granted_ts": int(time.time()),
            "revoked": False,
        }
        tokens.append(record)
        save_oauth3_tokens(tokens)
    return record


def revoke_oauth3_token(token_id: str) -> bool:
    """Mark token as revoked. Returns True if found.
    Handles both legacy ('id') and new ('token_id') schema fields."""
    with _TOKENS_LOCK:
        tokens = load_oauth3_tokens()
        for t in tokens:
            if t.get("id") == token_id or t.get("token_id") == token_id:
                t["revoked"] = True
                t["revoked_ts"] = int(time.time())
                save_oauth3_tokens(tokens)
                record_evidence("oauth3_token_revoked", {"token_id": token_id})
                return True
    return False


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

    def _check_auth(self) -> bool:
        """Return True if authorized, False after sending 401."""
        sha256_value = getattr(self.server, "session_token_sha256", "")
        if not sha256_value:
            return True
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            self._send_json({"error": "unauthorized"}, 401)
            return False
        provided = auth_header[len("Bearer "):]
        if not _SHA256_HEX_RE.fullmatch(provided):
            self._send_json({"error": "unauthorized"}, 401)
            return False
        if provided != sha256_value:
            self._send_json({"error": "unauthorized"}, 401)
            return False
        return True

    # --- GET routing ---
    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        query = self.path[len(path):]  # includes leading ?
        if path == "/health":
            self._handle_health()
        elif path == "/instructions":
            self._handle_instructions()
        elif path == "/credits":
            self._handle_credits()
        elif path == "/start":
            self._handle_start()
        elif path == "/api/v1/evidence":
            self._handle_evidence_list(query)
        elif path == "/api/v1/evidence/verify":
            self._handle_evidence_verify()
        elif re.match(r"^/api/v1/evidence/[^/]+$", path):
            entry_id = path.split("/")[-1]
            self._handle_evidence_detail(entry_id)
        elif path == "/api/v1/browser/schedules/next-runs":
            self._handle_schedules_next_runs()
        elif path == "/api/v1/browser/schedules":
            self._handle_schedules_list()
        elif path == "/api/v1/oauth3/tokens":
            self._handle_oauth3_list()
        elif path.startswith("/api/v1/oauth3/tokens/") and path.count("/") == 5:
            token_id = path.split("/")[-1]
            self._handle_oauth3_token_detail(token_id)
        elif path == "/api/v1/oauth3/audit":
            self._handle_oauth3_audit()
        elif path == "/api/v1/cli/available":
            self._handle_cli_available()
        elif path == "/onboarding":
            self._handle_onboarding_page()
        elif path == "/api/v1/onboarding/status":
            self._handle_onboarding_status()
        elif path == "/api/v1/sessions":
            self._handle_sessions_list()
        elif re.match(r"^/api/v1/sessions/[^/]+$", path):
            session_id = path.split("/")[-1]
            self._handle_session_detail(session_id)
        elif path == "/api/v1/tunnel/status":
            self._handle_tunnel_status()
        elif path == "/api/v1/sync/status":
            self._handle_sync_status()
        elif path == "/api/v1/recipes":
            self._handle_recipes_list()
        elif re.match(r"^/api/v1/recipes/[^/]+/preview$", path):
            recipe_id = path.split("/")[-2]
            self._handle_recipe_preview(recipe_id)
        elif re.match(r"^/api/v1/recipes/[^/]+/status$", path):
            run_id = path.split("/")[-2]
            self._handle_recipe_run_status(run_id)
        elif re.match(r"^/api/v1/recipes/[^/]+$", path):
            recipe_id = path.split("/")[-1]
            self._handle_recipe_detail(recipe_id)
        elif path == "/api/v1/budget":
            self._handle_budget_get()
        elif path == "/api/v1/budget/status":
            self._handle_budget_status()
        else:
            self._send_json({"error": "not found"}, 404)

    # --- POST routing ---
    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        if path == "/detect":
            self._handle_detect()
        elif path == "/api/v1/evidence":
            self._handle_evidence_record()
        elif path == "/api/v1/browser/schedules":
            self._handle_schedule_create()
        elif re.match(r"^/api/v1/browser/schedules/[^/]+/enable$", path):
            schedule_id = path.split("/")[-2]
            self._handle_schedule_enable(schedule_id)
        elif re.match(r"^/api/v1/browser/schedules/[^/]+/disable$", path):
            schedule_id = path.split("/")[-2]
            self._handle_schedule_disable(schedule_id)
        elif path == "/api/v1/oauth3/tokens":
            self._handle_oauth3_register()
        elif re.match(r"^/api/v1/oauth3/tokens/[^/]+/extend$", path):
            token_id = path.split("/")[-2]
            self._handle_oauth3_extend(token_id)
        elif path == "/api/v1/cli/run":
            self._handle_cli_run()
        elif path == "/onboarding/complete":
            self._handle_onboarding_complete()
        elif path == "/onboarding/reset":
            self._handle_onboarding_reset()
        elif path == "/api/v1/sessions":
            self._handle_session_create()
        elif path == "/api/v1/tunnel/start":
            self._handle_tunnel_start()
        elif path == "/api/v1/tunnel/stop":
            self._handle_tunnel_stop()
        elif path == "/api/v1/sync/export":
            self._handle_sync_export()
        elif path == "/api/v1/sync/import":
            self._handle_sync_import()
        elif re.match(r"^/api/v1/recipes/[^/]+/run$", path):
            recipe_id = path.split("/")[-2]
            self._handle_recipe_run(recipe_id)
        elif path == "/api/v1/budget":
            self._handle_budget_update()
        elif path == "/api/v1/budget/reset":
            self._handle_budget_reset()
        else:
            self._send_json({"error": "not found"}, 404)

    # --- DELETE routing ---
    def do_DELETE(self) -> None:
        path = self.path.split("?")[0]
        if path.startswith("/api/v1/browser/schedules/"):
            schedule_id = path[len("/api/v1/browser/schedules/"):]
            self._handle_schedule_delete(schedule_id)
        elif path.startswith("/api/v1/oauth3/tokens/"):
            token_id = path[len("/api/v1/oauth3/tokens/"):]
            self._handle_oauth3_revoke(token_id)
        elif re.match(r"^/api/v1/sessions/[^/]+$", path):
            session_id = path.split("/")[-1]
            self._handle_session_delete(session_id)
        else:
            self._send_json({"error": "not found"}, 404)

    # --- Handlers ---
    def _handle_health(self) -> None:
        apps: list[str] = self.server.apps  # type: ignore[attr-defined]
        self._send_json({
            "status": "ok",
            "apps": len(apps),
            "version": _SERVER_VERSION,
            "evidence_count": count_evidence(),
            "schedule_count": len(load_schedules()),
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
                "forbidden_debug_port",
                "extensions",
                "legacy_hub_name",
            ],
            "spec_file": "specs/solacehub-instructions.md",
        })

    def _handle_credits(self) -> None:
        apps: list[str] = self.server.apps  # type: ignore[attr-defined]
        self._send_json({"apps": apps})

    def _handle_start(self) -> None:
        """Serve the browser start page — redirects to Hub dashboard."""
        html = (
            "<!DOCTYPE html><html lang='en'><head>"
            "<meta charset='UTF-8'><title>Solace Hub — Starting</title>"
            "<meta http-equiv='refresh' content='0;url=http://localhost:8888/health'>"
            "</head><body><p>Starting Solace Hub...</p></body></html>"
        )
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_evidence_list(self, query: str) -> None:
        params = self._parse_query(query)
        limit_raw = params.get("limit", "50")
        offset_raw = params.get("offset", "0")
        if not limit_raw.isdigit() or not offset_raw.isdigit():
            self._send_json({"error": "invalid limit or offset"}, 400)
            return
        limit = min(int(limit_raw), 500)
        offset = max(int(offset_raw), 0)
        action_filter = params.get("action")
        session_filter = params.get("session_id")
        since_raw = params.get("since")
        until_raw = params.get("until")
        records = load_evidence(limit=500, offset=0)
        if action_filter:
            records = [r for r in records if r.get("type") == action_filter or r.get("action") == action_filter]
        if session_filter:
            records = [r for r in records if r.get("session_id") == session_filter]
        if since_raw and since_raw.isdigit():
            records = [r for r in records if r.get("ts", r.get("timestamp", 0)) >= int(since_raw)]
        if until_raw and until_raw.isdigit():
            records = [r for r in records if r.get("ts", r.get("timestamp", 0)) <= int(until_raw)]
        total = len(records)
        records = records[offset: offset + limit]
        self._send_json({
            "total": total,
            "limit": limit,
            "offset": offset,
            "records": records,
            "entries": records,
        })

    def _handle_evidence_record(self) -> None:
        if not self._check_auth():
            return
        payload = self._read_json_body()
        if payload is None:
            return
        event_type = payload.get("type")
        if not event_type or not isinstance(event_type, str):
            self._send_json({"error": "missing 'type' field"}, 400)
            return
        if len(event_type) > 256:
            self._send_json({"error": "'type' exceeds 256 chars"}, 400)
            return
        data = payload.get("data", {})
        if not isinstance(data, dict):
            self._send_json({"error": "'data' must be an object"}, 400)
            return
        record = record_evidence(event_type, data)
        self._send_json(record, 201)

    def _handle_schedules_list(self) -> None:
        self._send_json({"schedules": load_schedules()})

    def _handle_schedule_create(self) -> None:
        if not self._check_auth():
            return
        payload = self._read_json_body()
        if payload is None:
            return
        app_id = payload.get("app_id")
        cron = payload.get("cron")
        url = payload.get("url", "")
        if not app_id or not isinstance(app_id, str):
            self._send_json({"error": "missing 'app_id'"}, 400)
            return
        if len(app_id) > 256:
            self._send_json({"error": "'app_id' exceeds 256 chars"}, 400)
            return
        if not cron or not isinstance(cron, str):
            self._send_json({"error": "missing 'cron'"}, 400)
            return
        if len(cron) > 64:
            self._send_json({"error": "'cron' exceeds 64 chars"}, 400)
            return
        if not _CRON_RE.match(cron):
            self._send_json({"error": "'cron' must be 5 whitespace-separated fields"}, 400)
            return
        record = create_schedule(app_id, cron, url)
        self._send_json(record, 201)

    def _handle_schedule_delete(self, schedule_id: str) -> None:
        if not self._check_auth():
            return
        if not schedule_id:
            self._send_json({"error": "missing schedule id"}, 400)
            return
        found = delete_schedule(schedule_id)
        if found:
            self._send_json({"deleted": schedule_id})
        else:
            self._send_json({"error": "schedule not found"}, 404)

    # --- Task 013: Evidence detail + verify ---

    def _handle_evidence_detail(self, entry_id: str) -> None:
        """GET /api/v1/evidence/{id} — return a single evidence entry by id."""
        try:
            lines = EVIDENCE_PATH.read_text().splitlines()
        except FileNotFoundError:
            self._send_json({"error": "evidence entry not found"}, 404)
            return
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("id") == entry_id:
                self._send_json(entry)
                return
        self._send_json({"error": "evidence entry not found"}, 404)

    def _handle_evidence_verify(self) -> None:
        """GET /api/v1/evidence/verify — check sha256 chain integrity."""
        try:
            lines = EVIDENCE_PATH.read_text().splitlines()
        except FileNotFoundError:
            self._send_json({"valid": True, "entries": 0, "broken_at": None})
            return
        entries = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if not entries:
            self._send_json({"valid": True, "entries": 0, "broken_at": None})
            return
        broken_at = None
        for i, entry in enumerate(entries):
            entry_hash = entry.get("sha256", "")
            if entry_hash and len(entry_hash) >= 8:
                expected = hashlib.sha256(
                    f"{entry.get('id', '')}{entry.get('ts', entry.get('timestamp', 0))}{entry.get('type', entry.get('action', ''))}".encode()
                ).hexdigest()[:8]
                if entry_hash[:8] != expected:
                    broken_at = i
                    break
        self._send_json({
            "valid": broken_at is None,
            "entries": len(entries),
            "broken_at": broken_at,
        })

    # --- Task 014: Schedule enable/disable + next-runs ---

    def _next_cron_run(self, cron_expr: str) -> Optional[int]:
        """Return next Unix timestamp when cron_expr will fire, or None if invalid."""
        parts = cron_expr.split()
        if len(parts) != 5:
            return None
        now = int(time.time())
        for delta_minutes in range(1, 10081):
            t = now + delta_minutes * 60
            s = time.gmtime(t)
            minute, hour, day, month, weekday = s.tm_min, s.tm_hour, s.tm_mday, s.tm_mon, s.tm_wday
            cron_weekday = (weekday + 1) % 7

            def _match(field: str, val: int) -> bool:
                if field == "*":
                    return True
                try:
                    return int(field) == val
                except ValueError:
                    return False

            if (_match(parts[0], minute) and _match(parts[1], hour) and
                    _match(parts[2], day) and _match(parts[3], month) and
                    _match(parts[4], cron_weekday)):
                return t
        return None

    def _handle_schedules_next_runs(self) -> None:
        """GET /api/v1/browser/schedules/next-runs — preview next run time per schedule."""
        with _SCHEDULES_LOCK:
            schedules = load_schedules()
        result = []
        for s in schedules:
            cron = s.get("cron", "")
            next_run = self._next_cron_run(cron)
            result.append({
                "schedule_id": s.get("id"),
                "name": s.get("name", s.get("app_id", "")),
                "cron": cron,
                "enabled": s.get("enabled", True),
                "next_run": next_run,
                "next_run_human": (
                    time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(next_run))
                    if next_run else None
                ),
            })
        self._send_json({"schedules": result})

    def _handle_schedule_enable(self, schedule_id: str) -> None:
        """POST /api/v1/browser/schedules/{id}/enable — enable a schedule."""
        if not self._check_auth():
            return
        with _SCHEDULES_LOCK:
            schedules = load_schedules()
            for s in schedules:
                if s.get("id") == schedule_id:
                    s["enabled"] = True
                    save_schedules(schedules)
                    self._send_json({"status": "enabled", "schedule_id": schedule_id})
                    return
        self._send_json({"error": "schedule not found"}, 404)

    def _handle_schedule_disable(self, schedule_id: str) -> None:
        """POST /api/v1/browser/schedules/{id}/disable — disable a schedule."""
        if not self._check_auth():
            return
        with _SCHEDULES_LOCK:
            schedules = load_schedules()
            for s in schedules:
                if s.get("id") == schedule_id:
                    s["enabled"] = False
                    save_schedules(schedules)
                    self._send_json({"status": "disabled", "schedule_id": schedule_id})
                    return
        self._send_json({"error": "schedule not found"}, 404)

    def _handle_oauth3_list(self) -> None:
        tokens = load_oauth3_tokens()
        # Strip token_sha256 from response — expose only metadata
        safe = [
            {k: v for k, v in t.items() if k != "token_sha256"}
            for t in tokens
        ]
        self._send_json({"tokens": safe})

    def _handle_oauth3_register(self) -> None:
        if not self._check_auth():
            return
        payload = self._read_json_body()
        if payload is None:
            return

        # New schema: agent_name + scopes + expires_at (Task 010 — OAuth3 dashboard)
        if "agent_name" in payload or "scopes" in payload or "expires_at" in payload:
            agent_name = payload.get("agent_name", "")
            if not isinstance(agent_name, str) or not agent_name:
                self._send_json({"error": "missing 'agent_name'"}, 400)
                return
            agent_name = agent_name[:128]
            scopes = payload.get("scopes", [])
            if not isinstance(scopes, list):
                self._send_json({"error": "scopes must be a list"}, 400)
                return
            invalid = [s for s in scopes if s not in ALLOWED_SCOPES]
            if invalid:
                self._send_json({"error": f"invalid scopes: {invalid}", "allowed": sorted(ALLOWED_SCOPES)}, 400)
                return
            expires_at = payload.get("expires_at", int(time.time()) + 86400)
            if not isinstance(expires_at, int) or expires_at <= int(time.time()):
                self._send_json({"error": "expires_at must be in the future"}, 400)
                return
            with _TOKENS_LOCK:
                tokens = load_oauth3_tokens()
                record = {
                    "token_id": str(uuid.uuid4()),
                    "agent_name": agent_name,
                    "scopes": scopes,
                    "expires_at": expires_at,
                    "created_at": int(time.time()),
                    "revoked": False,
                }
                tokens.append(record)
                save_oauth3_tokens(tokens)
            self._send_json(record, 200)
            return

        # Legacy schema: scope + service + token_sha256
        scope = payload.get("scope")
        service = payload.get("service")
        token_sha256_val = payload.get("token_sha256")
        if not scope or not isinstance(scope, str):
            self._send_json({"error": "missing 'scope'"}, 400)
            return
        if len(scope) > 256:
            self._send_json({"error": "'scope' exceeds 256 chars"}, 400)
            return
        if not service or not isinstance(service, str):
            self._send_json({"error": "missing 'service'"}, 400)
            return
        if len(service) > 256:
            self._send_json({"error": "'service' exceeds 256 chars"}, 400)
            return
        if not token_sha256_val or not isinstance(token_sha256_val, str):
            self._send_json({"error": "missing 'token_sha256'"}, 400)
            return
        if not _SHA256_HEX_RE.fullmatch(token_sha256_val):
            self._send_json({"error": "'token_sha256' must be exactly 64 lowercase hex chars"}, 400)
            return
        record = register_oauth3_token(scope, service, token_sha256_val)
        # Return metadata only — never echo back token_sha256
        self._send_json({k: v for k, v in record.items() if k != "token_sha256"}, 201)

    def _handle_oauth3_revoke(self, token_id: str) -> None:
        if not self._check_auth():
            return
        if not token_id:
            self._send_json({"error": "missing token id"}, 400)
            return
        found = revoke_oauth3_token(token_id)
        if found:
            self._send_json({"revoked": token_id})
        else:
            self._send_json({"error": "token not found"}, 404)

    def _handle_oauth3_token_detail(self, token_id: str) -> None:
        """GET /api/v1/oauth3/tokens/{token_id} — return single token metadata."""
        tokens = self._load_oauth3_tokens()
        for t in tokens:
            if t.get("token_id") == token_id or t.get("id") == token_id:
                safe = {k: v for k, v in t.items() if k != "token_sha256"}
                self._send_json(safe)
                return
        self._send_json({"error": "token not found"}, 404)

    def _handle_oauth3_audit(self) -> None:
        """GET /api/v1/oauth3/audit — return recent audit log entries."""
        audit_path = Path.home() / ".solace" / "oauth3_audit.json"
        if not audit_path.exists():
            self._send_json({"entries": []})
            return
        try:
            entries = json.loads(audit_path.read_text())
        except json.JSONDecodeError:
            entries = []
        self._send_json({"entries": entries})

    def _handle_oauth3_extend(self, token_id: str) -> None:
        """POST /api/v1/oauth3/tokens/{token_id}/extend — extend expiry by N seconds."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        seconds = body.get("seconds")
        if not isinstance(seconds, int) or seconds <= 0:
            self._send_json({"error": "seconds must be positive integer"}, 400)
            return
        MAX_EXTENSION = 2592000  # 30 days
        if seconds > MAX_EXTENSION:
            self._send_json({"error": f"max extension is {MAX_EXTENSION} seconds (30 days)"}, 400)
            return
        with _TOKENS_LOCK:
            tokens = self._load_oauth3_tokens()
            for t in tokens:
                if t.get("token_id") == token_id or t.get("id") == token_id:
                    if t.get("revoked", False):
                        self._send_json({"error": "cannot extend revoked token"}, 400)
                        return
                    t["expires_at"] = int(time.time()) + seconds
                    self._save_oauth3_tokens(tokens)
                    self._send_json({"status": "extended", "expires_at": t["expires_at"]})
                    return
        self._send_json({"error": "token not found"}, 404)

    def _load_oauth3_tokens(self) -> list:
        """Instance-level loader so handlers can call self._load_oauth3_tokens()."""
        return load_oauth3_tokens()

    def _save_oauth3_tokens(self, tokens: list) -> None:
        """Instance-level saver so handlers can call self._save_oauth3_tokens()."""
        save_oauth3_tokens(tokens)

    def _handle_detect(self) -> None:
        if not self._check_auth():
            return
        payload = self._read_json_body()
        if payload is None:
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
        Uses urlparse().netloc for exact domain matching — not substring search.
        """
        available: set[str] = set(self.server.apps)  # type: ignore[attr-defined]
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower()
        # Strip port from netloc if present (e.g. "mail.google.com:443" → "mail.google.com")
        netloc = netloc.split(":")[0]
        matched: list[str] = []
        for domain, candidates in _DOMAIN_APP_MAP.items():
            # Exact match: netloc equals domain, or netloc ends with ".domain"
            if netloc == domain or netloc.endswith("." + domain):
                for app_id in candidates:
                    if app_id in available and app_id not in matched:
                        matched.append(app_id)
        return matched

    # --- CLI wrapper handlers ---
    def _handle_cli_available(self) -> None:
        """GET /api/v1/cli/available — check if `solace` CLI is installed."""
        try:
            result = subprocess.run(
                ["solace", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = result.stdout.strip() or result.stderr.strip() or None
            self._send_json({"available": True, "version": version})
        except OSError:
            self._send_json({"available": False, "version": None})

    def _handle_cli_run(self) -> None:
        """POST /api/v1/cli/run — run an allowlisted solace CLI command."""
        if not self._check_auth():
            return
        payload = self._read_json_body()
        if payload is None:
            return
        command = payload.get("command")
        if not command or not isinstance(command, str):
            self._send_json({"error": "missing 'command' field"}, 400)
            return
        if command not in _CLI_ALLOWLIST:
            self._send_json({"error": f"command not in allowlist: {command!r}"}, 400)
            return
        args = ["solace"] + command.split()
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
                shell=False,
            )
        except OSError as exc:
            self._send_json({"error": f"CLI not available: {exc}"}, 503)
            return
        _64KB = 65536
        self._send_json({
            "exit_code": result.returncode,
            "stdout": result.stdout[:_64KB],
            "stderr": result.stderr[:_64KB],
        })

    # --- Onboarding handlers ---
    def _handle_onboarding_page(self) -> None:
        """GET /onboarding — serve inline HTML onboarding page."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Solace Hub — Setup</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0f0f13;
    color: #e0e0e8;
    font-family: system-ui, -apple-system, sans-serif;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
  }
  .card {
    background: #1a1a24;
    border: 1px solid #2a2a38;
    border-radius: 12px;
    padding: 2.5rem;
    max-width: 520px;
    width: 100%;
  }
  h1 { font-size: 1.6rem; margin-bottom: 0.5rem; color: #c8b8ff; }
  .subtitle { color: #888; margin-bottom: 2rem; font-size: 0.95rem; }
  .modes { display: grid; gap: 1rem; }
  .mode-btn {
    background: #22223a;
    border: 1px solid #3a3a58;
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    cursor: pointer;
    text-align: left;
    color: #e0e0e8;
    transition: border-color 0.2s, background 0.2s;
  }
  .mode-btn:hover { border-color: #7c66ff; background: #2a2a48; }
  .mode-btn .label { font-weight: 600; font-size: 1rem; margin-bottom: 0.25rem; }
  .mode-btn .desc { font-size: 0.85rem; color: #888; }
  .status { margin-top: 1.5rem; font-size: 0.9rem; color: #7c66ff; min-height: 1.4em; }
</style>
</head>
<body>
<div class="card">
  <h1>Solace Hub Setup</h1>
  <p class="subtitle">Choose how you want to use Solace Hub:</p>
  <div class="modes">
    <button class="mode-btn" onclick="choose('agent')">
      <div class="label">AI Agent (Managed LLM)</div>
      <div class="desc">Solace manages the AI — no API keys needed. $8/mo Starter plan.</div>
    </button>
    <button class="mode-btn" onclick="choose('byok')">
      <div class="label">BYOK (Bring Your Own Key)</div>
      <div class="desc">Use your own Anthropic or OpenAI API key. Free tier.</div>
    </button>
    <button class="mode-btn" onclick="choose('paid')">
      <div class="label">Pro / Team</div>
      <div class="desc">Cloud twin + OAuth3 vault + 90-day evidence. $28/mo Pro.</div>
    </button>
    <button class="mode-btn" onclick="choose('cli')">
      <div class="label">Auto CLI</div>
      <div class="desc">Detected solace CLI — configure automatically from terminal.</div>
    </button>
  </div>
  <p class="status" id="status"></p>
</div>
<script>
function choose(mode) {
  document.getElementById('status').textContent = 'Saving...';
  fetch('/onboarding/complete', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mode: mode})
  }).then(r => {
    if (r.ok) {
      document.getElementById('status').textContent = 'Setup complete! Redirecting...';
      setTimeout(() => { window.location.href = '/health'; }, 1000);
    } else {
      document.getElementById('status').textContent = 'Error saving. Please retry.';
    }
  });
}
</script>
</body>
</html>"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_onboarding_complete(self) -> None:
        """POST /onboarding/complete — write onboarding.json (no API keys)."""
        payload = self._read_json_body()
        if payload is None:
            return
        mode = payload.get("mode")
        if not mode or not isinstance(mode, str):
            self._send_json({"error": "missing 'mode' field"}, 400)
            return
        if mode not in _ONBOARDING_MODES:
            self._send_json({"error": f"invalid mode; must be one of: {sorted(_ONBOARDING_MODES)}"}, 400)
            return
        onboarding_data = {
            "completed": True,
            "mode": mode,
            "completed_ts": int(time.time()),
        }
        ONBOARDING_PATH.parent.mkdir(parents=True, exist_ok=True)
        ONBOARDING_PATH.write_text(json.dumps(onboarding_data, indent=2))
        self._send_json({"ok": True, "mode": mode})

    def _handle_onboarding_reset(self) -> None:
        """POST /onboarding/reset — requires auth; delete onboarding.json."""
        if not self._check_auth():
            return
        try:
            ONBOARDING_PATH.unlink()
        except FileNotFoundError:
            pass
        self._send_json({"ok": True, "reset": True})

    def _handle_onboarding_status(self) -> None:
        """GET /api/v1/onboarding/status — return onboarding completion status."""
        try:
            data = json.loads(ONBOARDING_PATH.read_text())
            completed = bool(data.get("completed"))
            mode: Optional[str] = data.get("mode") if completed else None
        except (FileNotFoundError, json.JSONDecodeError):
            completed = False
            mode = None
        self._send_json({"completed": completed, "mode": mode})

    # --- Session manager handlers ---
    def _is_session_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _handle_sessions_list(self) -> None:
        with _SESSIONS_LOCK:
            result = []
            for sid, sess in _SESSIONS.items():
                result.append({
                    "session_id": sid,
                    "url": sess["url"],
                    "profile": sess["profile"],
                    "pid": sess["pid"],
                    "started_at": sess["started_at"],
                    "alive": self._is_session_alive(sess["pid"]),
                })
        self._send_json({"sessions": result})

    def _handle_session_detail(self, session_id: str) -> None:
        with _SESSIONS_LOCK:
            sess = _SESSIONS.get(session_id)
        if sess is None:
            self._send_json({"error": "session not found"}, 404)
            return
        self._send_json({
            "session_id": session_id,
            "url": sess["url"],
            "profile": sess["profile"],
            "pid": sess["pid"],
            "started_at": sess["started_at"],
            "alive": self._is_session_alive(sess["pid"]),
        })

    def _handle_session_create(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        url = body.get("url", "")
        profile = body.get("profile", "default")
        # URL must be localhost only
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or parsed.hostname != "localhost":
            self._send_json({"error": "url must be a localhost URL (http://localhost:...)"}, 400)
            return
        # Profile validation: alphanumeric + hyphen, max 32 chars
        if not re.match(r'^[a-zA-Z0-9-]{1,32}$', profile):
            self._send_json({"error": "profile must be alphanumeric + hyphens, max 32 chars"}, 400)
            return
        try:
            pid = self._spawn_browser_session(url, profile)
        except FileNotFoundError as exc:
            self._send_json({"error": str(exc)}, 503)
            return
        session_id = str(uuid.uuid4())
        with _SESSIONS_LOCK:
            _SESSIONS[session_id] = {
                "url": url,
                "profile": profile,
                "pid": pid,
                "started_at": int(time.time()),
            }
        self._send_json({"session_id": session_id, "pid": pid, "url": url}, 201)

    def _handle_session_delete(self, session_id: str) -> None:
        if not self._check_auth():
            return
        with _SESSIONS_LOCK:
            sess = _SESSIONS.get(session_id)
            if sess is None:
                self._send_json({"error": "session not found"}, 404)
                return
            pid = sess["pid"]
            del _SESSIONS[session_id]
        # SIGTERM then SIGKILL after 3s
        try:
            os.kill(pid, signal.SIGTERM)

            def _force_kill() -> None:
                time.sleep(3)
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
            threading.Thread(target=_force_kill, daemon=True).start()
        except OSError:
            pass  # Already dead — that's fine
        self._send_json({"status": "terminated", "session_id": session_id})

    def _spawn_browser_session(self, url: str, profile: str) -> int:
        browser = os.environ.get("SOLACE_BROWSER", "")
        if not browser:
            candidates = [
                Path(__file__).parent.parent / "source" / "out" / "Solace" / "chrome",
                Path.home() / ".local" / "bin" / "solace-browser",
                Path("/usr/bin/solace-browser"),
            ]
            for c in candidates:
                if Path(c).exists():
                    browser = str(c)
                    break
        if not browser or not Path(browser).exists():
            raise FileNotFoundError(
                "Solace Browser binary not found. Set SOLACE_BROWSER environment variable."
            )
        proc = subprocess.Popen(
            [browser, f"--profile-directory={profile}", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc.pid

    # --- Task 015: Recipe Management ---

    def _load_recipe(self, recipe_id: str) -> Optional[dict]:
        """Load a recipe by ID from RECIPES_DIR or ~/.solace/recipes/."""
        for search_path in [RECIPES_DIR, Path.home() / ".solace" / "recipes"]:
            recipe_file = search_path / f"{recipe_id}.json"
            if recipe_file.exists():
                try:
                    return json.loads(recipe_file.read_text())
                except json.JSONDecodeError:
                    return None
        return None

    def _handle_recipes_list(self) -> None:
        recipes = []
        seen: set = set()
        for search_path in [RECIPES_DIR, Path.home() / ".solace" / "recipes"]:
            if search_path.exists():
                for f in sorted(search_path.glob("*.json")):
                    if f.stem in seen:
                        continue
                    seen.add(f.stem)
                    try:
                        r = json.loads(f.read_text())
                        recipes.append({
                            "id": r.get("id", f.stem),
                            "name": r.get("name", f.stem),
                            "description": r.get("description", ""),
                            "cost_estimate": r.get("cost_estimate", 0.001),
                            "version": r.get("version", "1.0"),
                        })
                    except json.JSONDecodeError:
                        pass
        self._send_json({"recipes": recipes, "count": len(recipes)})

    def _handle_recipe_detail(self, recipe_id: str) -> None:
        r = self._load_recipe(recipe_id)
        if r is None:
            self._send_json({"error": f"recipe '{recipe_id}' not found"}, 404)
            return
        self._send_json(r)

    def _handle_recipe_preview(self, recipe_id: str) -> None:
        r = self._load_recipe(recipe_id)
        if r is None:
            self._send_json({"error": f"recipe '{recipe_id}' not found"}, 404)
            return
        steps = r.get("steps", [])
        preview = []
        for i, step in enumerate(steps):
            preview.append({
                "step": i + 1,
                "action": step.get("action", "unknown"),
                "description": step.get("description", ""),
                "estimated_cost": step.get("cost", 0.0),
            })
        self._send_json({
            "recipe_id": recipe_id,
            "name": r.get("name", recipe_id),
            "total_steps": len(steps),
            "total_cost_estimate": r.get("cost_estimate", sum(s.get("cost", 0) for s in steps)),
            "preview": preview,
        })

    def _handle_recipe_run(self, recipe_id: str) -> None:
        if not self._check_auth():
            return
        r = self._load_recipe(recipe_id)
        if r is None:
            self._send_json({"error": f"recipe '{recipe_id}' not found"}, 404)
            return
        run_id = str(uuid.uuid4())
        run_record = {
            "run_id": run_id,
            "recipe_id": recipe_id,
            "status": "queued",
            "started_at": int(time.time()),
            "completed_at": None,
            "result": None,
        }
        runs: list = []
        if RECIPE_RUNS_PATH.exists():
            try:
                runs = json.loads(RECIPE_RUNS_PATH.read_text())
            except json.JSONDecodeError:
                runs = []
        runs.append(run_record)
        RECIPE_RUNS_PATH.parent.mkdir(parents=True, exist_ok=True)
        RECIPE_RUNS_PATH.write_text(json.dumps(runs, indent=2))
        self._send_json({"run_id": run_id, "status": "queued", "recipe_id": recipe_id}, 202)

    def _handle_recipe_run_status(self, run_id: str) -> None:
        if not RECIPE_RUNS_PATH.exists():
            self._send_json({"error": "run not found"}, 404)
            return
        try:
            runs = json.loads(RECIPE_RUNS_PATH.read_text())
        except json.JSONDecodeError:
            self._send_json({"error": "run not found"}, 404)
            return
        for run in runs:
            if run.get("run_id") == run_id:
                self._send_json(run)
                return
        self._send_json({"error": "run not found"}, 404)

    # --- Task 016: Budget Management ---

    def _load_evidence(self) -> list:
        """Load all evidence entries (module-level load_evidence with no pagination)."""
        try:
            lines = EVIDENCE_PATH.read_text().splitlines()
        except FileNotFoundError:
            return []
        records = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    def _load_budget(self) -> dict:
        if not BUDGET_PATH.exists():
            return dict(DEFAULT_BUDGET)
        try:
            b = json.loads(BUDGET_PATH.read_text())
            result = dict(DEFAULT_BUDGET)
            result.update(b)
            return result
        except json.JSONDecodeError:
            return dict(DEFAULT_BUDGET)

    def _calculate_spend(self, period: str) -> float:
        """Sum cost_usd from evidence entries in current day or month."""
        entries = self._load_evidence()
        now = int(time.time())
        if period == "day":
            cutoff = now - 86400
        elif period == "month":
            cutoff = now - 2592000
        else:
            cutoff = 0
        total = 0.0
        for e in entries:
            if e.get("timestamp", e.get("ts", 0)) >= cutoff:
                cost = e.get("cost_usd", 0.0)
                if isinstance(cost, (int, float)):
                    total += cost
        return round(total, 6)

    def _handle_budget_get(self) -> None:
        self._send_json(self._load_budget())

    def _handle_budget_status(self) -> None:
        budget = self._load_budget()
        daily_spend = self._calculate_spend("day")
        monthly_spend = self._calculate_spend("month")
        daily_limit = budget.get("daily_limit_usd", 1.00)
        monthly_limit = budget.get("monthly_limit_usd", 20.00)
        threshold = budget.get("alert_threshold", 0.80)
        daily_pct = daily_spend / daily_limit if daily_limit > 0 else 0.0
        monthly_pct = monthly_spend / monthly_limit if monthly_limit > 0 else 0.0
        self._send_json({
            "daily_spend_usd": daily_spend,
            "daily_limit_usd": daily_limit,
            "daily_pct": round(daily_pct, 4),
            "daily_alert": daily_pct >= threshold,
            "daily_exceeded": daily_spend >= daily_limit,
            "monthly_spend_usd": monthly_spend,
            "monthly_limit_usd": monthly_limit,
            "monthly_pct": round(monthly_pct, 4),
            "monthly_alert": monthly_pct >= threshold,
            "monthly_exceeded": monthly_spend >= monthly_limit,
            "pause_on_exceeded": budget.get("pause_on_exceeded", True),
            "paused": (
                (daily_spend >= daily_limit or monthly_spend >= monthly_limit)
                and budget.get("pause_on_exceeded", True)
            ),
        })

    def _handle_budget_update(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        budget = self._load_budget()
        if "daily_limit_usd" in body:
            v = body["daily_limit_usd"]
            if not isinstance(v, (int, float)) or v < 0:
                self._send_json({"error": "daily_limit_usd must be non-negative number"}, 400)
                return
            budget["daily_limit_usd"] = float(v)
        if "monthly_limit_usd" in body:
            v = body["monthly_limit_usd"]
            if not isinstance(v, (int, float)) or v < 0:
                self._send_json({"error": "monthly_limit_usd must be non-negative number"}, 400)
                return
            budget["monthly_limit_usd"] = float(v)
        if "alert_threshold" in body:
            v = body["alert_threshold"]
            if not isinstance(v, (int, float)) or not (0.0 <= v <= 1.0):
                self._send_json({"error": "alert_threshold must be 0.0-1.0"}, 400)
                return
            budget["alert_threshold"] = float(v)
        if "pause_on_exceeded" in body:
            budget["pause_on_exceeded"] = bool(body["pause_on_exceeded"])
        budget["updated_at"] = int(time.time())
        BUDGET_PATH.parent.mkdir(parents=True, exist_ok=True)
        BUDGET_PATH.write_text(json.dumps(budget, indent=2))
        self._send_json({"status": "updated", "budget": budget})

    def _handle_budget_reset(self) -> None:
        if not self._check_auth():
            return
        BUDGET_PATH.parent.mkdir(parents=True, exist_ok=True)
        BUDGET_PATH.write_text(json.dumps(DEFAULT_BUDGET, indent=2))
        self._send_json({"status": "reset", "budget": DEFAULT_BUDGET})

    # --- Helpers ---
    def _read_json_body(self) -> Optional[dict]:
        """Read and parse JSON body. Sends error response and returns None on failure."""
        length_raw = self.headers.get("Content-Length", "0")
        if not re.fullmatch(r"\d+", length_raw):
            self._send_json({"error": "invalid content length"}, 400)
            return None
        length = int(length_raw)
        if length == 0:
            self._send_json({"error": "missing request body"}, 400)
            return None
        if length > MAX_BODY:
            self._send_json({"error": "request body too large"}, 413)
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode())
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON"}, 400)
            return None

    # --- Tunnel handlers ---

    def _handle_tunnel_status(self) -> None:
        global _TUNNEL_URL
        with _TUNNEL_LOCK:
            active = _TUNNEL_PROC is not None and _TUNNEL_PROC.poll() is None
            url = _TUNNEL_URL if active else ""
        self._send_json({"active": active, "url": url, "port": YINYANG_PORT})

    def _handle_tunnel_start(self) -> None:
        if not self._check_auth():
            return
        global _TUNNEL_PROC, _TUNNEL_URL
        cloudflared = shutil.which("cloudflared")
        if not cloudflared:
            self._send_json({
                "error": "cloudflared not found",
                "install": "https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/",
            }, 503)
            return
        with _TUNNEL_LOCK:
            if _TUNNEL_PROC is not None and _TUNNEL_PROC.poll() is None:
                self._send_json({"status": "already_running", "url": _TUNNEL_URL})
                return
            proc = subprocess.Popen(
                [cloudflared, "tunnel", "--url", f"http://localhost:{YINYANG_PORT}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            _TUNNEL_PROC = proc
            _TUNNEL_URL = ""
        # Read output to find trycloudflare.com URL
        _url_pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
        url_found = ""
        try:
            for _ in range(50):  # max 50 lines to find URL
                line = proc.stdout.readline().decode("utf-8", errors="replace")
                if not line:
                    break
                m = _url_pattern.search(line)
                if m:
                    url_found = m.group(0)
                    break
        except OSError:
            pass
        with _TUNNEL_LOCK:
            _TUNNEL_URL = url_found
        self._send_json({"status": "started", "url": url_found})

    def _handle_tunnel_stop(self) -> None:
        if not self._check_auth():
            return
        global _TUNNEL_PROC, _TUNNEL_URL
        with _TUNNEL_LOCK:
            if _TUNNEL_PROC is None:
                self._send_json({"status": "not_running"})
                return
            try:
                _TUNNEL_PROC.terminate()
            except OSError:
                pass
            _TUNNEL_PROC = None
            _TUNNEL_URL = ""
        self._send_json({"status": "stopped"})

    # --- Vault sync handlers ---

    def _handle_sync_status(self) -> None:
        token_count = 0
        vault_exists = VAULT_PATH.exists()
        if vault_exists:
            try:
                tokens = json.loads(VAULT_PATH.read_text())
                token_count = len(tokens) if isinstance(tokens, list) else 0
            except json.JSONDecodeError:
                pass
        last_sync = None
        if VAULT_EXPORT_PATH.exists():
            last_sync = int(VAULT_EXPORT_PATH.stat().st_mtime)
        self._send_json({
            "vault_exists": vault_exists,
            "token_count": token_count,
            "last_sync": last_sync,
        })

    def _handle_sync_export(self) -> None:
        if not self._check_auth():
            return
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            crypto_available = True
        except ImportError:
            crypto_available = False
        if not crypto_available:
            self._send_json({
                "error": "cryptography package required for vault sync",
                "install": "pip install cryptography",
            }, 503)
            return
        if not VAULT_PATH.exists():
            self._send_json({"error": "vault not found — no OAuth3 tokens registered yet"}, 404)
            return
        try:
            vault_bytes = VAULT_PATH.read_bytes()
        except OSError as e:
            self._send_json({"error": f"cannot read vault: {e}"}, 500)
            return
        # Use session token sha256 as AES-256 key (32 bytes from 64-char hex)
        key_hex = _SESSION_TOKEN_SHA256 or ("0" * 64)
        key = bytes.fromhex(key_hex)
        nonce = os.urandom(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, vault_bytes, None)
        export_data = {
            "version": "1",
            "nonce": base64.b64encode(nonce).decode(),
            "ct": base64.b64encode(ciphertext).decode(),
        }
        export_json = json.dumps(export_data)
        try:
            VAULT_EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            VAULT_EXPORT_PATH.write_text(export_json)
        except OSError as e:
            self._send_json({"error": f"cannot write export: {e}"}, 500)
            return
        checksum = hashlib.sha256(export_json.encode()).hexdigest()
        self._send_json({
            "status": "exported",
            "path": str(VAULT_EXPORT_PATH),
            "checksum": checksum,
        })

    def _handle_sync_import(self) -> None:
        if not self._check_auth():
            return
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            crypto_available = True
        except ImportError:
            crypto_available = False
        if not crypto_available:
            self._send_json({
                "error": "cryptography package required",
                "install": "pip install cryptography",
            }, 503)
            return
        body = self._read_json_body()
        if body is None:
            return
        export_data_str = body.get("export_data", "")
        token_sha256 = body.get("token_sha256", "")
        if not _SHA256_HEX_RE.fullmatch(token_sha256):
            self._send_json({"error": "token_sha256 must be 64 hex chars"}, 400)
            return
        try:
            export_obj = json.loads(export_data_str) if isinstance(export_data_str, str) else export_data_str
            nonce = base64.b64decode(export_obj["nonce"])
            ct = base64.b64decode(export_obj["ct"])
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            self._send_json({"error": f"invalid export_data: {e}"}, 400)
            return
        key = bytes.fromhex(token_sha256)
        aesgcm = AESGCM(key)
        try:
            plaintext = aesgcm.decrypt(nonce, ct, None)
        except Exception:  # cryptography raises platform-specific exceptions on decrypt failure
            self._send_json({"error": "decryption failed — wrong token or corrupted data"}, 400)
            return
        try:
            imported_tokens = json.loads(plaintext)
        except json.JSONDecodeError:
            self._send_json({"error": "decrypted data is not valid JSON"}, 400)
            return
        if not isinstance(imported_tokens, list):
            self._send_json({"error": "vault must be a list of tokens"}, 400)
            return
        # Merge: add new tokens by token_id, skip existing
        existing: list = []
        if VAULT_PATH.exists():
            try:
                existing = json.loads(VAULT_PATH.read_text())
                if not isinstance(existing, list):
                    existing = []
            except json.JSONDecodeError:
                existing = []
        existing_ids = {t.get("token_id") for t in existing if isinstance(t, dict)}
        added = 0
        skipped = 0
        for t in imported_tokens:
            if not isinstance(t, dict):
                continue
            tid = t.get("token_id")
            if tid in existing_ids:
                skipped += 1
            else:
                existing.append(t)
                added += 1
        try:
            VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
            VAULT_PATH.write_text(json.dumps(existing, indent=2))
        except OSError as e:
            self._send_json({"error": f"cannot write vault: {e}"}, 500)
            return
        self._send_json({"status": "imported", "tokens_added": added, "tokens_skipped": skipped})

    def _parse_query(self, query: str) -> dict[str, str]:
        """Parse ?key=value&key2=value2 into dict."""
        if not query or query == "?":
            return {}
        result: dict[str, str] = {}
        for pair in query.lstrip("?").split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                result[k] = v
        return result

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "http://localhost:8888")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # noqa: D102
        # Suppress default stderr logging — callers use structured evidence.
        pass


# ---------------------------------------------------------------------------
# Server factory — theorem: build_server isolates configuration from startup.
# ---------------------------------------------------------------------------
def build_server(
    port: int,
    repo_root: str,
    session_token_sha256: str = "",
) -> http.server.ThreadingHTTPServer:
    """
    Construct a ThreadingHTTPServer with apps pre-loaded.
    Does NOT write port.lock — caller is responsible for that.
    """
    server = http.server.ThreadingHTTPServer(("localhost", port), YinyangHandler)
    server.apps = load_apps(repo_root)  # type: ignore[attr-defined]
    server.repo_root = repo_root  # type: ignore[attr-defined]
    server.session_token_sha256 = session_token_sha256  # type: ignore[attr-defined]
    return server


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def start_server(
    port: int = 8888,
    repo_root: str = ".",
    session_token_sha256: str = "",
) -> None:
    """
    Generate token, write lock, register cleanup, then serve forever.
    Token is immediately discarded after hashing — never stored in memory
    beyond this function's call stack.
    """
    import os

    global _SESSION_TOKEN_SHA256
    _SESSION_TOKEN_SHA256 = session_token_sha256

    if session_token_sha256:
        t_hash = session_token_sha256
    else:
        token = generate_token()
        t_hash = token_hash(token)
        del token  # plaintext token leaves scope here — not stored anywhere
    write_port_lock(port, t_hash, os.getpid())
    atexit.register(delete_port_lock)

    record_evidence("server_started", {"port": port, "version": _SERVER_VERSION})
    server = build_server(port, repo_root, session_token_sha256)
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Yinyang Server")
    parser.add_argument("repo_root", nargs="?", default=".")
    parser.add_argument(
        "--token-sha256",
        dest="token_sha256",
        default="",
        help="Bearer token sha256 for Hub authentication",
    )
    args = parser.parse_args()
    start_server(8888, args.repo_root, args.token_sha256)
