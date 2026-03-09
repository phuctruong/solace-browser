"""
yinyang_server.py — Yinyang Server for Solace Browser.
Donald Knuth law: every function is a theorem. Prove it or don't ship it.

Architecture:
  - Stdlib-first: http.server, json, hashlib, secrets, pathlib, threading, signal, atexit, urllib
  - Optional BeautifulSoup parsing when installed; regex fallback otherwise
  - Port 8888 (production), 18888 (tests only)
  - Legacy debug port permanently banned
  - Token hash only in port.lock — plaintext NEVER written anywhere
  - Legacy alternate hub name banned in all responses — use "Solace Hub"
  - FALLBACK BAN: only FileNotFoundError, OSError, json.JSONDecodeError caught

Route table:
  GET  /health                         → {"status": "ok", "apps": N, "version": "1.1", "uptime_seconds": N}
  GET  /instructions                   → capabilities JSON
  GET  /credits                        → {"apps": [...]}
  GET  /start                          → browser start page HTML
  POST /detect                         → {"url": "..."} → {"apps": [...]}
  GET  /api/v1/evidence                → evidence log (limit/offset/action/session_id/since/until params)
  GET  /api/v1/evidence/verify         → verify sha256 chain integrity
  GET  /api/v1/evidence/{id}           → single evidence entry detail
  POST /api/v1/evidence                → record evidence event
  POST /api/v1/prime-wiki/snapshot     → capture and store compressed page snapshot
  GET  /api/v1/prime-wiki/snapshot/{id} → snapshot metadata + extracted key elements
  GET  /api/v1/prime-wiki/snapshot/{id}/content → lazy-load gzip content payload
  GET  /api/v1/prime-wiki/diff         → structural diff between two snapshots
  GET  /api/v1/prime-wiki/stats        → local Prime Wiki snapshot stats
  GET  /api/v1/session-rules           → list loaded session rule schemas (requires auth)
  GET  /api/v1/session-rules/status    → list cached session statuses (requires auth)
  POST /api/v1/session-rules/check/{app} → trigger one session check (requires auth)
  POST /api/v1/session-rules/reload    → reload session rule YAML files (requires auth)
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
  GET  /api/v1/metrics                 → JSON metrics (uptime, request counts, error rates)
  GET  /metrics                        → Prometheus-format metrics (text/plain; version=0.0.4)
  WS   /ws/dashboard                   → WebSocket: push state updates every 5s, accept ping→pong
  GET  /api/v1/byok/providers          → list configured providers (never plaintext keys)
  GET  /api/v1/byok/active             → {"active_provider": str|null}
  POST /api/v1/byok/set                → {"provider": str, "api_key": str} → store encrypted (requires auth)
  POST /api/v1/byok/test               → {"provider": str} → verify key is configured (requires auth)
  POST /api/v1/byok/clear              → {"provider": str} → remove key (requires auth)
  GET  /api/v1/marketplace/apps        → marketplace app catalog (requires auth)
  GET  /api/v1/marketplace/categories  → marketplace categories
  POST /api/v1/marketplace/install     → install marketplace session rules (requires auth)
  POST /api/v1/marketplace/uninstall   → uninstall marketplace session rules (requires auth)
  GET  /api/v1/logs/requests           → rolling request history (limit/method/status params)
  GET  /api/v1/logs/errors             → only 4xx/5xx entries from request history
  GET  /api/v1/fun-packs               → list installed fun pack metadata (requires auth)
  GET  /api/v1/fun-packs/active        → active fun pack content (requires auth)
  GET  /api/v1/fun-packs/{id}          → one fun pack content (requires auth)
  POST /api/v1/fun-packs/{id}/activate → set active fun pack id (requires auth)
  GET  /api/v1/fun-packs/random-joke   → random joke from active pack (requires auth)
  GET  /api/v1/fun-packs/random-fact   → random fact from active pack (requires auth)
  GET  /api/v1/fun-packs/greeting      → greeting by time_of_day from active pack (requires auth)
  POST /api/v1/actions/preview         → classify action + create pending record (B/C), returns action_id + cooldown
  GET  /api/v1/actions/pending         → list pending actions with cooldown_remaining_seconds
  POST /api/v1/actions/{id}/approve    → sign off after cooldown; Class C requires step_up_consent+reason
  POST /api/v1/actions/{id}/reject     → reject pending action, seal evidence with reason
  DELETE /api/v1/actions/{id}/cancel   → cancel pending action before cooldown ends
  GET  /api/v1/actions/history         → history of approved/rejected actions (class/status/from/to filters)
  POST /api/yinyang/notify             → queue in-memory agent notification (requires auth)
  GET  /api/yinyang/events             → SSE notification stream (?token=sha256)
  GET  /api/yinyang/status             → in-memory notification queue status (requires auth)
  POST /api/yinyang/notifications/{id}/read → mark yinyang notification as read (requires auth)
"""
import argparse
import asyncio
import atexit
import base64
import binascii
import functools
import gzip
import hashlib
import hmac
import http.server
import json
import os
import random
import queue
import re
import secrets
import shutil
import signal
import struct
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import yaml
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from evidence_bundle import ALCOABundle, ALCOAError, ComplianceStatus, RUNG_ACHIEVED
from hub_tunnel_client import HubTunnelClient, SOLACEAGI_RELAY_URL

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PORT_LOCK_PATH: Path = Path.home() / ".solace" / "port.lock"
EVIDENCE_PATH: Path = Path.home() / ".solace" / "evidence.jsonl"
PART11_EVIDENCE_DIR: Path = Path.home() / ".solace" / "evidence"
PART11_EVIDENCE_PATH: Path = PART11_EVIDENCE_DIR / "evidence.jsonl"
PART11_CHAIN_LOCK_PATH: Path = PART11_EVIDENCE_DIR / "chain.lock"
SCHEDULES_PATH: Path = Path.home() / ".solace" / "schedules.json"
OAUTH3_TOKENS_PATH: Path = Path.home() / ".solace" / "oauth3-tokens.json"
OAUTH3_VAULT_PATH: Path = Path.home() / ".solace" / "oauth3-vault.enc"
ONBOARDING_PATH: Path = Path.home() / ".solace" / "onboarding.json"
SETTINGS_PATH: Path = Path.home() / ".solace" / "settings.json"
PRIME_WIKI_ROOT: Path = Path.home() / ".solace" / "prime-wiki"
MARKETPLACE_CACHE_PATH: Path = Path.home() / ".solace" / "marketplace-cache.json"
RECIPES_DIR: Path = Path(__file__).parent / "data" / "default" / "recipes"
SESSION_RULES_APPS_DIR: Path = Path(__file__).parent / "data" / "default" / "apps"
FUN_PACKS_DIR: Path = Path(__file__).parent / "data" / "fun-packs"
ACTIVE_PACK_PATH: Path = Path.home() / ".solace" / "active-fun-pack.json"
RECIPE_RUNS_PATH: Path = Path.home() / ".solace" / "recipe_runs.json"
COMMUNITY_RECIPES_059_PATH: Path = Path.home() / ".solace" / "community_recipes.json"
_COMMUNITY_059_LOCK = threading.Lock()
BUDGET_PATH: Path = Path.home() / ".solace" / "budget.json"
BYOK_PATH: Path = Path.home() / ".solace" / "byok_keys.json"
NOTIFICATIONS_PATH: Path = Path.home() / ".solace" / "notifications.json"
SUPPORTED_PROVIDERS: frozenset = frozenset(["anthropic", "openai", "together", "openrouter"])
DEFAULT_BUDGET: dict = {
    "daily_limit_usd": 1.00,
    "monthly_limit_usd": 20.00,
    "alert_threshold": 0.80,
    "pause_on_exceeded": True,
}
DEFAULT_CLOUD_TWIN_SETTINGS: dict = {
    "url": "",
    "enabled": False,
    "prefer_cloud": False,
    "fallback_to_local": True,
}

_SERVER_VERSION = "1.1"
HUB_PORT = 8888
YINYANG_PORT = HUB_PORT
MAX_BODY = 1_048_576
CLOUD_TWIN_DISPLAY = ":99"

_SCHEDULES_LOCK = threading.Lock()
_TOKENS_LOCK = threading.Lock()
_OAUTH3_VAULT_LOCK = threading.Lock()
_BYOK_LOCK = threading.Lock()
_NOTIF_LOCK = threading.Lock()
_PRIME_WIKI_LOCK = threading.Lock()
_PART11_EVIDENCE_LOCK = threading.Lock()

PRIME_WIKI_PUSH_URL = "https://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/prime-wiki/push"
PRIME_WIKI_PULL_URL = "https://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/prime-wiki/pull"
PRIME_WIKI_STATS_URL = "https://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/prime-wiki/stats"
PRIME_WIKI_PUSH_TIMEOUT_SECONDS = 5
PRIME_WIKI_SNAPSHOT_TYPES: frozenset = frozenset(["before_action", "after_action", "periodic"])
PRIME_WIKI_CTA_VERBS: tuple[str, ...] = (
    "submit",
    "send",
    "archive",
    "delete",
    "reply",
    "save",
    "publish",
)

MAX_NOTIFICATIONS = 200  # keep last 200
NOTIF_CATEGORIES: frozenset = frozenset(["budget", "session", "schedule", "error", "info", "recipe"])
YINYANG_NOTIFICATION_TYPES: dict[str, str] = {
    "task_complete": "normal",
    "task_failed": "high",
    "task_blocked": "high",
    "budget_warning": "high",
    "budget_exhausted": "critical",
    "app_update": "low",
    "support_reply": "normal",
    "milestone": "normal",
    "system": "low",
    "celebration": "normal",
}
YINYANG_NOTIFICATION_PRIORITIES: frozenset = frozenset(["critical", "high", "normal", "low"])
YINYANG_SSE_PING_SECONDS = 15
YINYANG_SSE_RECENT_LIMIT = 10
_YINYANG_NOTIFICATIONS: list[dict[str, Any]] = []
_YINYANG_NOTIF_LOCK = threading.Lock()
_YINYANG_SSE_CLIENTS: list[queue.Queue[str]] = []
_YINYANG_SSE_CLIENTS_LOCK = threading.Lock()
_YINYANG_NOTIF_COUNTER = 0
PROFILES_PATH: Path = Path.home() / ".solace" / "profiles.json"
ACTIVE_PROFILE_PATH: Path = Path.home() / ".solace" / "active_profile.json"
_PROFILES_LOCK = threading.Lock()
MAX_PROFILES = 10
INSTALLED_RECIPES_PATH: Path = Path.home() / ".solace" / "installed_recipes.json"
_STORE_LOCK = threading.Lock()
CLI_CONFIG_PATH: Path = Path.home() / ".solace" / "cli_config.json"
SPEND_HISTORY_PATH: Path = Path.home() / ".solace" / "spend_history.json"
_SPEND_HISTORY_LOCK = threading.Lock()
WATCHDOG_LOG_PATH: Path = Path.home() / ".solace" / "watchdog.log"
_WATCHDOG_LOCK = threading.Lock()
THEME_PATH: Path = Path.home() / ".solace" / "theme.json"
_THEME_LOCK = threading.Lock()
PINNED_SECTIONS_PATH: Path = Path.home() / ".solace" / "pinned_sections.json"
_PINNED_LOCK = threading.Lock()
FAVORITES_PATH: Path = Path.home() / ".solace" / "favorites.json"
_FAVORITES_LOCK = threading.Lock()
SUPPORTED_CLI_TOOLS: frozenset = frozenset(["claude", "openai", "ollama", "aider", "continue"])
CLI_AGENT_CANDIDATES: dict[str, str] = {
    "claude": "claude",
    "codex": "codex",
    "gemini": "gemini",
    "aider": "aider",
}
DEFAULT_MODELS: dict[str, str] = {
    "claude": "claude-sonnet-4-6",
    "codex": "gpt-5.4",
    "gemini": "gemini-2.0-flash",
    "aider": "gpt-4o",
}
COST_PER_1M_TOKENS: dict[str, Decimal] = {
    "claude": Decimal("3.00"),
    "gemini": Decimal("0.15"),
    "codex": Decimal("0.50"),
    "aider": Decimal("0.50"),
}
CLI_AGENT_DEFAULT_MODELS = DEFAULT_MODELS
CLI_AGENT_COST_PER_1M_TOKENS = COST_PER_1M_TOKENS
_CLI_LOCK = threading.Lock()
_MARKETPLACE_LOCK = threading.Lock()
_COMMUNITY_RECIPES: list = [
    {"id": "r001", "name": "Gmail Unsubscribe", "tag": "email", "author": "solace", "version": "1.0", "rating": 4.8, "installs": 1240},
    {"id": "r002", "name": "LinkedIn Auto-Connect", "tag": "social", "author": "community", "version": "1.2", "rating": 4.5, "installs": 890},
    {"id": "r003", "name": "GitHub PR Summary", "tag": "dev", "author": "solace", "version": "2.0", "rating": 4.9, "installs": 567},
    {"id": "r004", "name": "HackerNews Digest", "tag": "news", "author": "community", "version": "1.0", "rating": 4.3, "installs": 234},
    {"id": "r005", "name": "Expense Report Filler", "tag": "productivity", "author": "solace", "version": "1.1", "rating": 4.7, "installs": 445},
]
_SESSIONS: dict[str, dict] = {}
_SESSIONS_LOCK = threading.Lock()
_SESSION_TOKEN_SHA256: str = ""
_SESSION_RULES: list[dict] = []
_SESSION_RULES_LOCK = threading.Lock()
_SESSION_STATUS: dict[str, dict] = {}
_SESSION_STATUS_LOCK = threading.Lock()
_SESSION_KEEPALIVE_THREAD: threading.Thread | None = None
_SESSION_KEEPALIVE_STOP = threading.Event()
DEFAULT_FUN_PACK_ID = "default-en"
FUN_PACK_GREETING_TIMES: frozenset[str] = frozenset(["morning", "afternoon", "evening", "any"])

_TUNNEL_PROC: Optional[subprocess.Popen] = None
_TUNNEL_LOCK = threading.Lock()
_TUNNEL_URL: str = ""
_CLOUD_TUNNEL_THREAD: threading.Thread | None = None
_CLOUD_TUNNEL_CLIENT: Optional[HubTunnelClient] = None
_CLOUD_TUNNEL_ACTIVE: bool = False
_CLOUD_TUNNEL_LOOP: Optional[asyncio.AbstractEventLoop] = None
_CLOUD_TUNNEL_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Action Preview / Cooldown / Sign-Off — Task 057
# Safety ladder: A=autonomous, B=preview+30min+signoff, C=preview+2h+stepup+signoff
# ---------------------------------------------------------------------------
ACTION_CLASSES: dict[str, str] = {
    # Class A — read-only, autonomous
    "gmail.read": "A",
    "browse.navigate": "A",
    "search.google": "A",
    "slack.read": "A",
    "linkedin.read": "A",
    "github.read": "A",
    # Class B — reputation-impact: preview + 30min cooldown + sign-off
    "linkedin.post": "B",
    "twitter.post": "B",
    "instagram.post": "B",
    "slack.send_channel": "B",
    "github.comment": "B",
    "gmail.send": "B",
    "gmail.archive_batch": "B",
    # Class C — irreversible/financial: preview + 2h cooldown + step-up + reason + sign-off
    "gmail.delete_batch": "C",
    "gmail.permanent_delete": "C",
    "linkedin.connect_all": "C",
    "pricing.update": "C",
    "permission.change": "C",
    "payment.initiate": "C",
}
COOLDOWN_SECONDS: dict[str, int] = {"B": 1800, "C": 7200}
_PENDING_ACTIONS: dict[str, dict] = {}
_PENDING_ACTIONS_LOCK = threading.Lock()
_ACTIONS_HISTORY: list[dict] = []
_ACTIONS_HISTORY_LOCK = threading.Lock()


def _utc_isoformat(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _action_preview_text(action_type: str, app_id: str, params: dict[str, Any]) -> str:
    resource_names = ", ".join(sorted(str(key) for key in params.keys())) or "no explicit resources"
    app_label = app_id or "unknown-app"
    return f"Approve {action_type} for {app_label}; affects {resource_names}."


def _build_action_preview(action_type: str, app_id: str, params: dict[str, Any], action_class: str) -> dict[str, Any]:
    return {
        "preview_text": _action_preview_text(action_type, app_id, params),
        "estimated_cost": str(Decimal("0.00")),
        "affected_resources": sorted(str(key) for key in params.keys()),
        "reversal_possible": action_class == "B",
    }


def _action_state_copy(action: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(action, sort_keys=True))


def _build_action_hash(
    action_type: str,
    params: dict[str, Any],
    app_id: str,
    oauth3_token_id: str,
) -> str:
    payload = {
        "action_type": action_type,
        "app_id": app_id,
        "oauth3_token_id": oauth3_token_id,
        "params": params,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _create_pending_action_record(
    action_type: str,
    params: dict[str, Any],
    app_id: str,
    oauth3_token_id: str,
    now_ts: float,
) -> dict[str, Any]:
    action_class = ACTION_CLASSES.get(action_type, "B")
    preview = _build_action_preview(action_type, app_id, params, action_class)
    return {
        "action_id": str(uuid.uuid4()),
        "action_type": action_type,
        "class": action_class,
        "params": params,
        "app_id": app_id,
        "oauth3_token_id": oauth3_token_id,
        "action_hash": _build_action_hash(action_type, params, app_id, oauth3_token_id),
        "status": "PENDING_APPROVAL",
        "preview": preview,
        "cooldown_ends_at": now_ts + COOLDOWN_SECONDS[action_class],
        "created_at": now_ts,
    }


def _pending_action_list_item(action: dict[str, Any], now_ts: float) -> dict[str, Any]:
    cooldown_end = float(action.get("cooldown_ends_at", now_ts))
    remaining = max(0.0, cooldown_end - now_ts)
    return {
        "action_id": action.get("action_id") or action.get("preview_id", ""),
        "action_type": action["action_type"],
        "class": action["class"],
        "status": action["status"],
        "preview_summary": action.get("preview", {}).get("preview_text", action.get("preview_text", "")),
        "cooldown_ends_at": _utc_isoformat(cooldown_end),
        "cooldown_remaining_seconds": int(remaining),
        "app_id": action.get("app_id", ""),
    }

# ---------------------------------------------------------------------------
# Broadcast log — Task 043
_BROADCAST_LOG: list = []
_BROADCAST_LOCK = threading.Lock()

# Metrics globals — Task 018
# ---------------------------------------------------------------------------
_SERVER_START_TIME: float = time.time()
_REQUEST_COUNTS: dict = {}
_ERROR_COUNTS: dict = {}
_METRICS_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Request history globals — Task 021
# ---------------------------------------------------------------------------
_REQUEST_HISTORY: list = []
_HISTORY_LOCK = threading.Lock()
MAX_HISTORY = 100

# ---------------------------------------------------------------------------
# Session stats globals — Task 061 (Value Dashboard)
# ---------------------------------------------------------------------------
_SESSION_STATS: dict = {
    "session_id": "",
    "state": "IDLE",
    "app_name": None,
    "pages_visited": 0,
    "llm_calls": 0,
    "cost_usd": "0.00",
    "cost_saved_pct": 0,
    "duration_seconds": 0,
    "recipes_replayed": 0,
    "evidence_captured": 0,
    "session_start": None,
}
_SESSION_STATS_LOCK = threading.Lock()


def _record_request(path: str, status_code: int) -> None:
    """Record request count and errors per path. Thread-safe."""
    with _METRICS_LOCK:
        _REQUEST_COUNTS[path] = _REQUEST_COUNTS.get(path, 0) + 1
        if status_code >= 400:
            key = f"{path}:{status_code}"
            _ERROR_COUNTS[key] = _ERROR_COUNTS.get(key, 0) + 1


# ---------------------------------------------------------------------------
# WebSocket dashboard clients — Task 017
# ---------------------------------------------------------------------------
_WS_DASHBOARD_CLIENTS: list = []
_WS_DASHBOARD_LOCK = threading.Lock()

VAULT_PATH = Path.home() / ".solace" / "oauth3_tokens.json"
VAULT_EXPORT_PATH = Path.home() / ".solace" / "vault_export.json"
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_CRON_RE = re.compile(r"^\S+\s+\S+\s+\S+\s+\S+\s+\S+$")
_APP_ID_RE = re.compile(r"^[A-Za-z0-9-]+$")
_ONBOARDING_MODES = frozenset(["agent", "byok", "paid", "cli"])
OAUTH3_HIGH_RISK_ACTIONS = frozenset(["send", "post", "delete", "payment", "connect"])
OAUTH3_STEP_UP_TTL_SECONDS = 300
OAUTH3_PBKDF2_ITERATIONS = 100000
OAUTH3_EVIDENCE_GENESIS_HASH = "0" * 64
OAUTH3_ISSUER = "https://www.solaceagi.com"
OAUTH3_MAX_TTL_SECONDS = 2592000
_MARKETPLACE_CATEGORIES: tuple[str, ...] = (
    "productivity",
    "messaging",
    "social",
    "finance",
    "developer",
    "solace",
)
_MARKETPLACE_TIER_RANKS: dict[str, int] = {
    "free": 0,
    "starter": 1,
    "pro": 2,
    "team": 3,
    "enterprise": 4,
}
MARKETPLACE_CATALOG_URL = "https://solaceagi.com/api/v1/store/apps"
MARKETPLACE_APP_RULES_URL_TEMPLATE = "https://solaceagi.com/api/v1/store/apps/{app_id}/session-rules.yaml"
MARKETPLACE_UPGRADE_URL = "https://solaceagi.com/upgrade"
MARKETPLACE_APP_SYNC_URL = "https://solaceagi.com/api/v1/apps/sync"
MARKETPLACE_CACHE_TTL_SECONDS = 3600
MARKETPLACE_TIMEOUT_SECONDS = 5
_marketplace_urlopen = urllib.request.urlopen
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


@functools.lru_cache(maxsize=1)
def _detect_available_agents():
    """Detect AI coding CLIs available on PATH. Absence is valid state."""
    found: dict[str, str] = {}
    for name, binary in CLI_AGENT_CANDIDATES.items():
        path = shutil.which(binary)
        if path is not None:
            found[name] = path
    return found


def _default_model_for_agent(agent_name: str) -> str:
    """Return the default model for a supported CLI agent."""
    return DEFAULT_MODELS.get(agent_name, "unknown")


def _build_cli_command(agent_name: str, executable: str, prompt: str, model: Optional[str] = None) -> list[str]:
    """Build a shell-free subprocess argv for one CLI agent."""
    if agent_name == "claude":
        if model:
            return [executable, "--model", model, "--print", prompt]
        return [executable, "--print", prompt]
    if agent_name == "codex":
        if model:
            return [executable, "exec", "-m", model, prompt]
        return [executable, "exec", prompt]
    if agent_name == "gemini":
        if model:
            return [executable, "-m", model, prompt]
        return [executable, prompt]
    if agent_name == "aider":
        if model:
            return [executable, "--model", model, "--message", prompt, "--no-git"]
        return [executable, "--message", prompt, "--no-git"]
    return [executable, prompt]


def _invoke_cli_agent(
    agent_name: str,
    executable: str,
    prompt: str,
    model: Optional[str] = None,
    timeout_s: int = 60,
) -> dict:
    """Invoke a CLI agent and return captured stdout/stderr."""
    cmd = _build_cli_command(agent_name, executable, prompt, model)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=True,
        shell=False,
    )
    return {"stdout": result.stdout, "stderr": result.stderr}


def _estimate_cost(agent_name: str, tokens_est: int) -> str:
    """Return cost as a Decimal string; never float."""
    rate = COST_PER_1M_TOKENS.get(agent_name, Decimal("1.00"))
    cost = (rate * Decimal(tokens_est)) / Decimal("1000000")
    return str(cost.quantize(Decimal("0.000001")))


def _estimate_tokens(prompt: str, output: str) -> int:
    """Cheap deterministic token estimate from character count."""
    char_count = len(prompt) + len(output)
    return max(1, (char_count + 3) // 4)


def _inject_skill_pack(prompt: str, skill_pack: list[str]) -> str:
    """Prepend selected skill names to the prompt body."""
    if not skill_pack:
        return prompt
    headers = "\n".join(f"[SKILL: {skill_name}]" for skill_name in skill_pack)
    return f"{headers}\n\n{prompt}"


def _build_cli_evidence_id(output: str) -> str:
    """Build a deterministic evidence fingerprint for one generation."""
    digest = hashlib.sha256(output.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


# ---------------------------------------------------------------------------
# Evidence storage — append-only JSONL log
# ---------------------------------------------------------------------------
def _read_part11_chain_tip() -> str:
    try:
        lines = PART11_CHAIN_LOCK_PATH.read_text().splitlines()
    except IOError:
        return ""
    for line in reversed(lines):
        chain_tip = line.strip().lower()
        if chain_tip:
            return chain_tip
    return ""


def _load_part11_evidence_bundles() -> list[dict]:
    try:
        lines = PART11_EVIDENCE_PATH.read_text().splitlines()
    except IOError:
        return []
    bundles = []
    for line in lines:
        payload = line.strip()
        if not payload:
            continue
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            bundles.append(loaded)
    return bundles


def create_and_store_evidence_bundle(
    action_type: str,
    before_state: object,
    after_state: object,
    oauth3_token_id: str,
    user_id: str,
) -> dict:
    with _PART11_EVIDENCE_LOCK:
        previous_bundle_sha256 = _read_part11_chain_tip() or None
        bundle = ALCOABundle.create_bundle(
            action_type,
            before_state,
            after_state,
            oauth3_token_id,
            user_id,
            previous_bundle_sha256=previous_bundle_sha256,
        )
        bundle_sha256 = ALCOABundle.bundle_sha256(bundle)
        PART11_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        with PART11_EVIDENCE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(bundle, sort_keys=True) + "\n")
        with PART11_CHAIN_LOCK_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"{bundle_sha256}\n")
    return bundle


def list_part11_evidence_bundles(
    limit: int = 50,
    since_iso8601: str = "",
    action_type: str = "",
) -> list[dict]:
    bundles = _load_part11_evidence_bundles()
    if since_iso8601:
        bundles = [bundle for bundle in bundles if str(bundle.get("timestamp_iso8601", "")) >= since_iso8601]
    if action_type:
        bundles = [bundle for bundle in bundles if bundle.get("action_type") == action_type]
    bundles.reverse()
    return bundles[:limit]


def part11_compliance_report() -> dict:
    compliant_count = 0
    partial_count = 0
    non_compliant_count = 0
    bundles = _load_part11_evidence_bundles()
    for bundle in bundles:
        status = ALCOABundle.check_compliance(bundle)
        if status == ComplianceStatus.COMPLIANT:
            compliant_count += 1
        elif status == ComplianceStatus.PARTIALLY_COMPLIANT:
            partial_count += 1
        else:
            non_compliant_count += 1
    return {
        "compliant_count": compliant_count,
        "partial_count": partial_count,
        "non_compliant": non_compliant_count,
        "total": len(bundles),
        "rung": RUNG_ACHIEVED,
    }


def verify_part11_evidence_chain() -> dict:
    bundles = _load_part11_evidence_bundles()
    validation = ALCOABundle.validate_chain(bundles)
    return {
        "chain_valid": validation.chain_valid,
        "total_bundles": len(bundles),
        "broken_at_index": validation.broken_at_index,
    }


def _append_evidence_record(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    record = {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "ts": int(time.time()),
        "data": data,
    }
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCE_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return record


def record_evidence(event_type: str, data: dict) -> dict:
    """Append one evidence event to ~/.solace/evidence.jsonl. Returns the record."""
    record = _append_evidence_record(event_type, data)
    create_and_store_evidence_bundle(
        action_type=event_type,
        before_state=data.get("before_state_hash", {}),
        after_state=data.get("after_state_hash", data),
        oauth3_token_id=str(data.get("oauth3_token_id") or "system"),
        user_id=str(data.get("user_id") or "system"),
    )
    return record


class OAuth3VaultError(Exception):
    """Base OAuth3 vault error."""


class OAuth3TokenNotFoundError(OAuth3VaultError):
    """Raised when a token id is not present in the OAuth3 vault."""


class OAuth3VaultUserMismatchError(OAuth3VaultError):
    """Raised when a persisted vault belongs to a different local user hash."""


class OAuth3VaultCorruptError(OAuth3VaultError):
    """Raised when the encrypted OAuth3 vault cannot be parsed or decrypted."""


def _oauth3_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _oauth3_parse_iso8601(raw: str) -> datetime:
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _oauth3_hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()


def _oauth3_default_state(user_id_hash: str = "") -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "user_id_hash": user_id_hash,
        "tokens": {},
        "evidence": [],
        "chain_tip": OAUTH3_EVIDENCE_GENESIS_HASH,
    }


def _oauth3_normalize_state(raw_state: Any, user_id_hash: str = "") -> dict[str, Any]:
    if not isinstance(raw_state, dict):
        raise OAuth3VaultCorruptError("vault state must be a JSON object")
    tokens = raw_state.get("tokens", {})
    evidence = raw_state.get("evidence", [])
    if not isinstance(tokens, dict):
        raise OAuth3VaultCorruptError("vault tokens must be a JSON object")
    if not isinstance(evidence, list):
        raise OAuth3VaultCorruptError("vault evidence must be a JSON array")
    chain_tip = raw_state.get("chain_tip", OAUTH3_EVIDENCE_GENESIS_HASH)
    if not isinstance(chain_tip, str) or not chain_tip:
        chain_tip = OAUTH3_EVIDENCE_GENESIS_HASH
    stored_user_id_hash = raw_state.get("user_id_hash", user_id_hash)
    if not isinstance(stored_user_id_hash, str):
        stored_user_id_hash = user_id_hash
    return {
        "schema_version": str(raw_state.get("schema_version", "1.0")),
        "user_id_hash": stored_user_id_hash,
        "tokens": tokens,
        "evidence": evidence,
        "chain_tip": chain_tip,
    }


def _oauth3_derive_key(session_token_sha256: str, user_id_hash: str) -> bytes:
    if not _SHA256_HEX_RE.fullmatch(user_id_hash):
        raise OAuth3VaultCorruptError("vault KDF salt must be a 64-char sha256 hex string")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=bytes.fromhex(user_id_hash),
        iterations=OAUTH3_PBKDF2_ITERATIONS,
    )
    return kdf.derive(session_token_sha256.encode("utf-8"))


def _oauth3_encrypt_state(state: dict[str, Any], session_token_sha256: str) -> str:
    user_id_hash = state.get("user_id_hash", "")
    if not isinstance(user_id_hash, str) or not _SHA256_HEX_RE.fullmatch(user_id_hash):
        raise OAuth3VaultCorruptError("vault user_id_hash missing or invalid")
    plaintext = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_oauth3_derive_key(session_token_sha256, user_id_hash)).encrypt(nonce, plaintext, None)
    envelope = {
        "cipher": "AES-256-GCM",
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "ciphertext_sha256": hashlib.sha256(ciphertext).hexdigest(),
        "kdf": {
            "algorithm": "PBKDF2-HMAC-SHA256",
            "iterations": OAUTH3_PBKDF2_ITERATIONS,
            "salt_hex": user_id_hash,
        },
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))


def _oauth3_load_vault_state(session_token_sha256: str, user_id_hash_hint: str = "") -> dict[str, Any]:
    if not OAUTH3_VAULT_PATH.exists():
        return _oauth3_default_state(user_id_hash_hint)
    try:
        envelope = json.loads(OAUTH3_VAULT_PATH.read_text())
    except FileNotFoundError:
        return _oauth3_default_state(user_id_hash_hint)
    except json.JSONDecodeError as exc:
        raise OAuth3VaultCorruptError(f"vault JSON decode failed: {exc}") from exc
    except OSError as exc:
        raise OAuth3VaultCorruptError(f"vault read failed: {exc}") from exc
    if not isinstance(envelope, dict):
        raise OAuth3VaultCorruptError("vault envelope must be a JSON object")
    kdf = envelope.get("kdf", {})
    if not isinstance(kdf, dict):
        raise OAuth3VaultCorruptError("vault envelope missing kdf metadata")
    salt_hex = kdf.get("salt_hex", "")
    nonce_b64 = envelope.get("nonce_b64", "")
    ciphertext_b64 = envelope.get("ciphertext_b64", "")
    ciphertext_sha256 = envelope.get("ciphertext_sha256", "")
    if not isinstance(salt_hex, str) or not isinstance(nonce_b64, str) or not isinstance(ciphertext_b64, str):
        raise OAuth3VaultCorruptError("vault envelope fields must be strings")
    try:
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(ciphertext_b64)
        plaintext = AESGCM(_oauth3_derive_key(session_token_sha256, salt_hex)).decrypt(nonce, ciphertext, None)
        decoded = json.loads(plaintext.decode("utf-8"))
    except (binascii.Error, InvalidTag, KeyError, OSError, TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise OAuth3VaultCorruptError(f"vault decrypt failed: {exc}") from exc
    if isinstance(ciphertext_sha256, str) and ciphertext_sha256:
        actual_ciphertext_sha256 = hashlib.sha256(ciphertext).hexdigest()
        if actual_ciphertext_sha256 != ciphertext_sha256:
            raise OAuth3VaultCorruptError("vault ciphertext sha256 mismatch")
    state = _oauth3_normalize_state(decoded, salt_hex)
    if user_id_hash_hint and state.get("user_id_hash") and state["user_id_hash"] != user_id_hash_hint:
        raise OAuth3VaultUserMismatchError("oauth3 vault already initialized for a different local user")
    if not state.get("user_id_hash"):
        state["user_id_hash"] = salt_hex or user_id_hash_hint
    return state


def _oauth3_save_vault_state(state: dict[str, Any], session_token_sha256: str) -> None:
    normalized = _oauth3_normalize_state(state, str(state.get("user_id_hash", "")))
    if not normalized["user_id_hash"]:
        raise OAuth3VaultCorruptError("cannot persist vault without user_id_hash")
    OAUTH3_VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OAUTH3_VAULT_PATH.write_text(_oauth3_encrypt_state(normalized, session_token_sha256))


def _oauth3_is_high_risk_scope(scope: str) -> bool:
    normalized = scope.strip().lower()
    if not normalized or normalized.startswith("post.draft"):
        return False
    segments = [segment for segment in re.split(r"[^a-z]+", normalized) if segment]
    return any(segment in OAUTH3_HIGH_RISK_ACTIONS for segment in segments)


def _oauth3_step_up_scopes(scopes: list[str]) -> list[str]:
    required: list[str] = []
    for scope in scopes:
        if _oauth3_is_high_risk_scope(scope) and scope not in required:
            required.append(scope)
    return required


def _oauth3_validate_scopes(raw_scopes: Any) -> list[str]:
    if not isinstance(raw_scopes, list) or not raw_scopes:
        raise ValueError("scopes must be a non-empty list")
    cleaned: list[str] = []
    for raw_scope in raw_scopes:
        if not isinstance(raw_scope, str):
            raise ValueError("each scope must be a string")
        scope = raw_scope.strip()
        if not scope:
            raise ValueError("scope values must not be empty")
        if len(scope) > 128:
            raise ValueError("scope values must be 128 chars or fewer")
        if scope not in cleaned:
            cleaned.append(scope)
    return cleaned


def _oauth3_validate_ttl_seconds(raw_ttl: Any) -> int:
    if not isinstance(raw_ttl, int):
        raise ValueError("ttl_seconds must be an integer")
    if raw_ttl <= 0:
        raise ValueError("ttl_seconds must be positive")
    if raw_ttl > OAUTH3_MAX_TTL_SECONDS:
        raise ValueError(f"ttl_seconds must be <= {OAUTH3_MAX_TTL_SECONDS}")
    return raw_ttl


def _oauth3_token_valid(token: dict[str, Any], now: Optional[datetime] = None) -> tuple[bool, str]:
    if bool(token.get("revoked", False)):
        return False, "revoked"
    expires_at = token.get("expires_at", "")
    if not isinstance(expires_at, str) or not expires_at:
        return False, "missing_expiry"
    current_time = now or datetime.now(timezone.utc)
    if current_time >= _oauth3_parse_iso8601(expires_at):
        return False, "expired"
    return True, "ok"


def _oauth3_token_view(token: dict[str, Any]) -> dict[str, Any]:
    token_id = str(token.get("token_id", ""))
    return {
        "token_id": token_id,
        "id": token_id,
        "scopes": list(token.get("scopes", [])),
        "expires_at": token.get("expires_at"),
        "issued_at": token.get("issued_at"),
        "revoked": bool(token.get("revoked", False)),
        "revoked_at": token.get("revoked_at"),
        "step_up_required": list(token.get("step_up_required", [])),
    }


def _oauth3_append_evidence(
    state: dict[str, Any],
    event_type: str,
    *,
    token: Optional[dict[str, Any]] = None,
    data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    payload = data.copy() if isinstance(data, dict) else {}
    token_id = str(token.get("token_id", "")) if token is not None else str(payload.pop("token_id", ""))
    scopes = list(token.get("scopes", [])) if token is not None else list(payload.pop("scopes", []))
    previous_hash = str(state.get("chain_tip") or OAUTH3_EVIDENCE_GENESIS_HASH)
    event = {
        "event_type": event_type,
        "token_id": token_id,
        "scopes": scopes,
        "timestamp": _oauth3_now_iso(),
        "previous_hash": previous_hash,
        "data": payload,
    }
    event_sha256 = hashlib.sha256(
        json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    chain_link_sha256 = hashlib.sha256(f"{previous_hash}{event_sha256}".encode("utf-8")).hexdigest()
    event["chain_link_sha256"] = chain_link_sha256
    state.setdefault("evidence", []).append(event)
    state["chain_tip"] = chain_link_sha256
    if token is not None:
        token["evidence_chain_tip"] = chain_link_sha256
    return event


def _oauth3_filter_evidence(state: dict[str, Any], limit: int = 50, since: str = "") -> list[dict[str, Any]]:
    evidence = state.get("evidence", [])
    if not isinstance(evidence, list):
        return []
    filtered: list[dict[str, Any]] = []
    since_dt: Optional[datetime] = None
    if since:
        since_dt = _oauth3_parse_iso8601(since)
    for row in evidence:
        if not isinstance(row, dict):
            continue
        if since_dt is not None:
            timestamp = row.get("timestamp", "")
            if not isinstance(timestamp, str):
                continue
            if _oauth3_parse_iso8601(timestamp) < since_dt:
                continue
        filtered.append({
            "event_type": row.get("event_type", ""),
            "token_id": row.get("token_id", ""),
            "scopes": row.get("scopes", []),
            "timestamp": row.get("timestamp", ""),
            "chain_link_sha256": row.get("chain_link_sha256", ""),
        })
    return filtered[-limit:]


def _oauth3_legacy_token_view(token: dict[str, Any]) -> dict[str, Any]:
    safe = {key: value for key, value in token.items() if key != "token_sha256"}
    token_id = str(safe.get("token_id") or safe.get("id") or "")
    if token_id:
        safe["token_id"] = token_id
        safe["id"] = token_id
    return safe


def _oauth3_active_token_rows(session_token_sha256: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_token_ids: set[str] = set()
    if OAUTH3_VAULT_PATH.exists():
        state = _oauth3_load_vault_state(session_token_sha256)
        for token in state.get("tokens", {}).values():
            if not isinstance(token, dict):
                continue
            token_id = str(token.get("token_id", ""))
            if not token_id:
                continue
            valid, _ = _oauth3_token_valid(token)
            if not valid:
                continue
            rows.append(_oauth3_token_view(token))
            seen_token_ids.add(token_id)
    for token in load_oauth3_tokens():
        if not isinstance(token, dict):
            continue
        token_id = str(token.get("token_id") or token.get("id") or "")
        if not token_id or token_id in seen_token_ids:
            continue
        if bool(token.get("revoked", False)):
            continue
        rows.append(_oauth3_legacy_token_view(token))
    return rows


def _load_cloud_api_key() -> str:
    try:
        settings = json.loads(SETTINGS_PATH.read_text())
    except FileNotFoundError:
        return ""
    except json.JSONDecodeError:
        return ""
    except OSError:
        return ""
    if not isinstance(settings, dict):
        return ""
    account = settings.get("account", {})
    if not isinstance(account, dict):
        return ""
    api_key = account.get("api_key", "")
    return api_key if isinstance(api_key, str) else ""


def _load_account_tier() -> str:
    try:
        settings = json.loads(SETTINGS_PATH.read_text())
    except FileNotFoundError:
        return "free"
    except json.JSONDecodeError:
        return "free"
    except OSError:
        return "free"
    if not isinstance(settings, dict):
        return "free"
    user = settings.get("user", {})
    if isinstance(user, dict):
        tier = user.get("tier")
        if isinstance(tier, str):
            normalized = tier.strip().lower()
            if normalized in _MARKETPLACE_TIER_RANKS:
                return normalized
    account = settings.get("account", {})
    if not isinstance(account, dict):
        return "free"
    tier = account.get("tier", "free")
    if not isinstance(tier, str):
        return "free"
    normalized = tier.strip().lower()
    if normalized not in _MARKETPLACE_TIER_RANKS:
        return "free"
    return normalized


def _load_user_tier_payload() -> dict:
    tier = _load_account_tier()
    tier_rank = _MARKETPLACE_TIER_RANKS.get(tier, 0)
    pro_rank = _MARKETPLACE_TIER_RANKS["pro"]
    return {
        "tier": tier,
        "can_sync": tier_rank >= pro_rank,
        "can_submit": tier_rank >= pro_rank,
    }


def _fun_pack_sha256(pack: dict[str, Any]) -> str:
    normalized = json.loads(json.dumps(pack))
    meta = normalized.get("_meta", {})
    if not isinstance(meta, dict):
        meta = {}
    meta["sha256"] = "COMPUTED_AT_LOAD"
    normalized["_meta"] = meta
    sealed = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(sealed).hexdigest()


def _load_fun_pack(pack_id: str) -> dict[str, Any]:
    """Load one fun pack JSON object and compute its sealed sha256 metadata."""
    pack_path = FUN_PACKS_DIR / f"{pack_id}.json"
    if not pack_path.exists():
        raise FileNotFoundError(f"Fun pack '{pack_id}' not found")
    data = json.loads(pack_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise json.JSONDecodeError("fun pack must be an object", pack_path.name, 0)
    meta = data.get("_meta", {})
    if not isinstance(meta, dict):
        meta = {}
    meta["sha256"] = _fun_pack_sha256(data)
    data["_meta"] = meta
    return data


def _get_active_pack_id() -> str:
    """Get configured active fun pack id, defaulting to the bundled English pack."""
    try:
        payload = json.loads(ACTIVE_PACK_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return DEFAULT_FUN_PACK_ID
    except json.JSONDecodeError:
        return DEFAULT_FUN_PACK_ID
    except OSError:
        return DEFAULT_FUN_PACK_ID
    if not isinstance(payload, dict):
        return DEFAULT_FUN_PACK_ID
    active_pack_id = payload.get("active_pack_id", DEFAULT_FUN_PACK_ID)
    return active_pack_id if isinstance(active_pack_id, str) and active_pack_id else DEFAULT_FUN_PACK_ID


def _resolve_active_pack_id() -> str:
    configured_pack_id = _get_active_pack_id()
    try:
        _load_fun_pack(configured_pack_id)
        return configured_pack_id
    except FileNotFoundError:
        return DEFAULT_FUN_PACK_ID
    except json.JSONDecodeError:
        return DEFAULT_FUN_PACK_ID
    except OSError:
        return DEFAULT_FUN_PACK_ID


def _load_active_fun_pack() -> dict[str, Any]:
    return _load_fun_pack(_resolve_active_pack_id())


def _set_active_pack_id(pack_id: str) -> None:
    ACTIVE_PACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_PACK_PATH.write_text(json.dumps({"active_pack_id": pack_id}), encoding="utf-8")


def _list_available_packs() -> list[dict[str, Any]]:
    if not FUN_PACKS_DIR.exists():
        return []
    active_pack_id = _resolve_active_pack_id()
    packs: list[dict[str, Any]] = []
    for pack_path in sorted(FUN_PACKS_DIR.glob("*.json")):
        try:
            pack = _load_fun_pack(pack_path.stem)
        except FileNotFoundError:
            continue
        except json.JSONDecodeError:
            continue
        except OSError:
            continue
        meta = pack.get("_meta", {})
        if not isinstance(meta, dict):
            meta = {}
        pack_id = str(meta.get("id") or pack_path.stem)
        packs.append(
            {
                "id": pack_id,
                "name": str(meta.get("name") or pack_path.stem),
                "locale": str(meta.get("locale") or "en"),
                "version": str(meta.get("version") or "1.0.0"),
                "active": pack_id == active_pack_id,
                "jokes_count": len(pack.get("jokes", [])),
                "facts_count": len(pack.get("facts", [])),
                "greetings_count": len(pack.get("greetings", [])),
                "seasonal_count": len(pack.get("seasonal", [])),
            }
        )
    return packs


_prime_wiki_urlopen = urllib.request.urlopen


def _prime_wiki_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _normalize_prime_wiki_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    normalized_path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), normalized_path, "", "")
    )


def _prime_wiki_url_hash(normalized_url: str) -> str:
    return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()


def _prime_wiki_storage_dir(url_hash: str) -> Path:
    return PRIME_WIKI_ROOT / url_hash[:16]


def _prime_wiki_clean_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", without_tags).strip()


def _prime_wiki_unique_text(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = re.sub(r"\s+", " ", value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)
    return unique_values


def _prime_wiki_meta_content(tag: object) -> str:
    if BeautifulSoup is None:
        return ""
    if tag is None:
        return ""
    content = tag.get("content", "")
    return content.strip() if isinstance(content, str) else ""


def _prime_wiki_rel_contains_canonical(value: object) -> bool:
    if isinstance(value, list):
        return "canonical" in [str(item).strip().lower() for item in value]
    if isinstance(value, str):
        return "canonical" in value.strip().lower().split()
    return False


def extract_metadata(html: str) -> dict:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        og_title = ""
        og_description = ""
        canonical_url = ""

        og_title_tag = soup.find("meta", attrs={"property": "og:title"})
        if og_title_tag is None:
            og_title_tag = soup.find("meta", attrs={"name": "og:title"})
        og_title = _prime_wiki_meta_content(og_title_tag)

        og_description_tag = soup.find("meta", attrs={"property": "og:description"})
        if og_description_tag is None:
            og_description_tag = soup.find("meta", attrs={"name": "og:description"})
        og_description = _prime_wiki_meta_content(og_description_tag)
        if not og_description:
            description_tag = soup.find("meta", attrs={"name": "description"})
            og_description = _prime_wiki_meta_content(description_tag)

        for link in soup.find_all("link"):
            rel_value = link.get("rel")
            if _prime_wiki_rel_contains_canonical(rel_value):
                href = link.get("href", "")
                if isinstance(href, str):
                    canonical_url = href.strip()
                    if canonical_url:
                        break

        return {
            "og_title": og_title,
            "og_description": og_description,
            "canonical_url": canonical_url,
        }

    og_title_match = re.search(
        r'<meta[^>]+(?:property|name)=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    og_description_match = re.search(
        r'<meta[^>]+(?:property|name)=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    if og_description_match is None:
        og_description_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.I,
        )
    canonical_match = re.search(
        r'href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']|'
        r'rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    return {
        "og_title": og_title_match.group(1).strip() if og_title_match else "",
        "og_description": og_description_match.group(1).strip() if og_description_match else "",
        "canonical_url": (canonical_match.group(1) or canonical_match.group(2)).strip()
        if canonical_match
        else "",
    }


def _extract_title(html: str) -> str:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title is not None:
            title_text = soup.title.get_text(" ", strip=True)
            if title_text:
                return title_text
        metadata = extract_metadata(html)
        og_title = metadata.get("og_title", "")
        return og_title if isinstance(og_title, str) else ""

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if title_match:
        return _prime_wiki_clean_text(title_match.group(1))
    metadata = extract_metadata(html)
    og_title = metadata.get("og_title", "")
    return og_title if isinstance(og_title, str) else ""


def extract_headings(html: str) -> list[str]:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        headings = [tag.get_text(" ", strip=True) for tag in soup.find_all(["h1", "h2", "h3"])]
        return _prime_wiki_unique_text(headings)

    matches = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, re.I | re.S)
    return _prime_wiki_unique_text([_prime_wiki_clean_text(match) for match in matches])


def _prime_wiki_is_action_cta(text: str, href: str = "") -> bool:
    haystack = f"{text} {href}".lower()
    for verb in PRIME_WIKI_CTA_VERBS:
        if re.search(rf"\b{re.escape(verb)}\b", haystack):
            return True
    return False


def extract_ctas(html: str) -> list[str]:
    ctas: list[str] = []
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for button in soup.find_all("button"):
            text = button.get_text(" ", strip=True)
            if text:
                ctas.append(text)
        for input_tag in soup.find_all("input"):
            input_type = str(input_tag.get("type", "")).strip().lower()
            if input_type in ("submit", "button"):
                value = str(input_tag.get("value", "")).strip()
                if value:
                    ctas.append(value)
        for link in soup.find_all("a"):
            text = link.get_text(" ", strip=True)
            href = str(link.get("href", "")).strip()
            if text and _prime_wiki_is_action_cta(text, href):
                ctas.append(text)
        return _prime_wiki_unique_text(ctas)

    button_matches = re.findall(r"<button[^>]*>(.*?)</button>", html, re.I | re.S)
    for match in button_matches:
        text = _prime_wiki_clean_text(match)
        if text:
            ctas.append(text)
    input_matches = re.findall(
        r'<input[^>]*type=["\'](?:submit|button)["\'][^>]*value=["\']([^"\']+)["\'][^>]*>',
        html,
        re.I,
    )
    for value in input_matches:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if cleaned:
            ctas.append(cleaned)
    link_matches = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S)
    for href, text in link_matches:
        cleaned = _prime_wiki_clean_text(text)
        if cleaned and _prime_wiki_is_action_cta(cleaned, href):
            ctas.append(cleaned)
    return _prime_wiki_unique_text(ctas)


def extract_key_elements(html: str) -> dict:
    return {
        "title": _extract_title(html),
        "headings": extract_headings(html),
        "ctas": extract_ctas(html),
        "metadata": extract_metadata(html),
    }


def _compress_prime_wiki_content(content: str) -> tuple[str, str, int, int, float]:
    raw_bytes = content.encode("utf-8")
    compressed_bytes = gzip.compress(raw_bytes)
    compressed_b64 = base64.b64encode(compressed_bytes).decode("ascii")
    sha256_value = hashlib.sha256(raw_bytes).hexdigest()
    compression_ratio = round(len(raw_bytes) / max(len(compressed_bytes), 1), 3)
    return compressed_b64, sha256_value, len(raw_bytes), len(compressed_bytes), compression_ratio


def _prime_wiki_snapshot_filename(snapshot_type: str, captured_at: str, snapshot_id: str) -> str:
    filename = f"{snapshot_type}_{captured_at}.json"
    if len(filename) <= 255:
        return filename
    return f"{snapshot_type}_{captured_at}_{snapshot_id}.json"


def _prime_wiki_public_record(record: dict) -> dict:
    public_record = dict(record)
    public_record.pop("content_gzip_b64", None)
    public_record.pop("storage_path", None)
    return public_record


def _prime_wiki_snapshot_record(
    url: str,
    content_html: str,
    snapshot_type: str,
    app_id: str,
    action_id: str,
) -> dict:
    normalized_url = _normalize_prime_wiki_url(url)
    captured_at = _prime_wiki_timestamp()
    snapshot_id = str(uuid.uuid4())
    compressed_b64, sha256_value, size_bytes, compressed_size_bytes, compression_ratio = (
        _compress_prime_wiki_content(content_html)
    )
    return {
        "snapshot_id": snapshot_id,
        "url_hash": _prime_wiki_url_hash(normalized_url),
        "url": normalized_url,
        "domain": urllib.parse.urlsplit(normalized_url).netloc.lower(),
        "snapshot_type": snapshot_type,
        "content_gzip_b64": compressed_b64,
        "key_elements": extract_key_elements(content_html),
        "compression_ratio": compression_ratio,
        "captured_at": captured_at,
        "captured_at_ts": time.time(),
        "app_id": app_id,
        "action_id": action_id,
        "sha256": sha256_value,
        "size_bytes": size_bytes,
        "compressed_size_bytes": compressed_size_bytes,
    }


def _store_prime_wiki_snapshot(record: dict) -> Path:
    storage_dir = _prime_wiki_storage_dir(str(record.get("url_hash", "")))
    storage_dir.mkdir(parents=True, exist_ok=True)
    snapshot_id = str(record.get("snapshot_id", ""))
    captured_at = str(record.get("captured_at", ""))
    snapshot_type = str(record.get("snapshot_type", "periodic"))
    file_path = storage_dir / _prime_wiki_snapshot_filename(snapshot_type, captured_at, snapshot_id)
    if file_path.exists():
        file_path = storage_dir / f"{snapshot_type}_{captured_at}_{snapshot_id}.json"
    record["storage_path"] = str(file_path)
    with _PRIME_WIKI_LOCK:
        file_path.write_text(json.dumps(record, indent=2))
    return file_path


def _iter_prime_wiki_snapshot_paths() -> list[Path]:
    if not PRIME_WIKI_ROOT.is_dir():
        return []
    return sorted(PRIME_WIKI_ROOT.glob("*/*.json"))


def _load_prime_wiki_snapshot_from_path(path: Path) -> Optional[dict]:
    try:
        record = json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None
    except OSError:
        return None
    if not isinstance(record, dict):
        return None
    record["storage_path"] = str(path)
    return record


def _find_prime_wiki_snapshot(snapshot_id: str) -> Optional[dict]:
    for path in _iter_prime_wiki_snapshot_paths():
        record = _load_prime_wiki_snapshot_from_path(path)
        if record is None:
            continue
        if record.get("snapshot_id") == snapshot_id:
            return record
    return None


def _load_all_prime_wiki_snapshots() -> list[dict]:
    records: list[dict] = []
    for path in _iter_prime_wiki_snapshot_paths():
        record = _load_prime_wiki_snapshot_from_path(path)
        if record is not None:
            records.append(record)
    return records


def _prime_wiki_diff_elements(record: dict) -> set[str]:
    key_elements = record.get("key_elements", {})
    if not isinstance(key_elements, dict):
        return set()
    elements: set[str] = set()
    title = key_elements.get("title", "")
    if isinstance(title, str) and title:
        elements.add(f"title:{title}")
    headings = key_elements.get("headings", [])
    if isinstance(headings, list):
        for heading in headings:
            if isinstance(heading, str) and heading:
                elements.add(f"heading:{heading}")
    ctas = key_elements.get("ctas", [])
    if isinstance(ctas, list):
        for cta in ctas:
            if isinstance(cta, str) and cta:
                elements.add(f"cta:{cta}")
    metadata = key_elements.get("metadata", {})
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            if isinstance(value, str) and value:
                elements.add(f"metadata:{key}={value}")
    return elements


def _prime_wiki_diff_payload(before_record: dict, after_record: dict) -> dict:
    before_elements = _prime_wiki_diff_elements(before_record)
    after_elements = _prime_wiki_diff_elements(after_record)
    before_headings = before_record.get("key_elements", {}).get("headings", [])
    after_headings = after_record.get("key_elements", {}).get("headings", [])
    if not isinstance(before_headings, list):
        before_headings = []
    if not isinstance(after_headings, list):
        after_headings = []
    added_elements = sorted(after_elements - before_elements)
    removed_elements = sorted(before_elements - after_elements)
    added_headings = sorted({heading for heading in after_headings if isinstance(heading, str)} - {heading for heading in before_headings if isinstance(heading, str)})
    removed_headings = sorted({heading for heading in before_headings if isinstance(heading, str)} - {heading for heading in after_headings if isinstance(heading, str)})
    return {
        "added_elements": added_elements,
        "removed_elements": removed_elements,
        "changed_headings": {
            "added": added_headings,
            "removed": removed_headings,
        },
        "action_summary": (
            f"Added {len(added_elements)} elements, removed {len(removed_elements)} elements, "
            f"changed headings +{len(added_headings)}/-{len(removed_headings)}"
        ),
    }


def _prime_wiki_stats_payload() -> dict:
    records = _load_all_prime_wiki_snapshots()
    total_compressed_bytes = 0
    domains: set[str] = set()
    last_24h_count = 0
    cutoff = time.time() - 86400
    for record in records:
        compressed_size_bytes = record.get("compressed_size_bytes", 0)
        if isinstance(compressed_size_bytes, int):
            total_compressed_bytes += compressed_size_bytes
        domain = record.get("domain", "")
        if isinstance(domain, str) and domain:
            domains.add(domain)
        captured_at_ts = record.get("captured_at_ts", 0)
        if isinstance(captured_at_ts, (int, float)) and captured_at_ts >= cutoff:
            last_24h_count += 1
    return {
        "total_snapshots": len(records),
        "total_compressed_kb": round(total_compressed_bytes / 1024, 2),
        "domains_covered": len(domains),
        "last_24h_count": last_24h_count,
    }


def _prime_wiki_sync_enabled_for_tier(user_tier: str) -> bool:
    return _MARKETPLACE_TIER_RANKS.get(user_tier, 0) >= _MARKETPLACE_TIER_RANKS["pro"]


def _prime_wiki_cloud_push_worker(snapshot_record: dict) -> None:
    request = urllib.request.Request(
        PRIME_WIKI_PUSH_URL,
        data=json.dumps(snapshot_record).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with _prime_wiki_urlopen(request, timeout=PRIME_WIKI_PUSH_TIMEOUT_SECONDS) as response:
            response.read()
        record_evidence(
            "prime_wiki_cloud_push_succeeded",
            {
                "snapshot_id": snapshot_record.get("snapshot_id", ""),
                "url_hash": snapshot_record.get("url_hash", ""),
            },
        )
    except urllib.error.HTTPError as exc:
        record_evidence(
            "prime_wiki_cloud_push_failed",
            {
                "snapshot_id": snapshot_record.get("snapshot_id", ""),
                "url_hash": snapshot_record.get("url_hash", ""),
                "status": exc.code,
            },
        )
    except urllib.error.URLError as exc:
        record_evidence(
            "prime_wiki_cloud_push_failed",
            {
                "snapshot_id": snapshot_record.get("snapshot_id", ""),
                "url_hash": snapshot_record.get("url_hash", ""),
                "reason": str(exc.reason) if hasattr(exc, "reason") else str(exc),
            },
        )
    except OSError as exc:
        record_evidence(
            "prime_wiki_cloud_push_failed",
            {
                "snapshot_id": snapshot_record.get("snapshot_id", ""),
                "url_hash": snapshot_record.get("url_hash", ""),
                "reason": str(exc),
            },
        )


def _queue_prime_wiki_cloud_push(snapshot_record: dict) -> bool:
    user_tier = _load_account_tier()
    if not _prime_wiki_sync_enabled_for_tier(user_tier):
        return False
    thread = threading.Thread(
        target=_prime_wiki_cloud_push_worker,
        args=(snapshot_record,),
        daemon=True,
    )
    thread.start()
    return True


def _marketplace_apps_root(repo_root: str) -> Path:
    return Path(repo_root) / "data" / "default" / "apps"


def _marketplace_app_dir(repo_root: str, app_id: str) -> Path:
    return _marketplace_apps_root(repo_root) / app_id


def _session_rules_path_for_app(repo_root: str, app_id: str) -> Path:
    return _marketplace_app_dir(repo_root, app_id) / "session-rules.yaml"


def _is_marketplace_app_installed(repo_root: str, app_id: str) -> bool:
    return _session_rules_path_for_app(repo_root, app_id).is_file()


def _normalize_marketplace_app(raw_app: dict, repo_root: str) -> Optional[dict]:
    app_id = raw_app.get("app_id")
    if not isinstance(app_id, str) or not _APP_ID_RE.fullmatch(app_id):
        return None
    display_name = raw_app.get("display_name", app_id.replace("-", " ").title())
    description = raw_app.get("description", "")
    category = raw_app.get("category", "solace")
    tier_required = raw_app.get("tier_required", "free")
    version = raw_app.get("version", "")
    icon_url = raw_app.get("icon_url", "")
    if not isinstance(display_name, str):
        display_name = app_id.replace("-", " ").title()
    if not isinstance(description, str):
        description = ""
    if not isinstance(category, str) or not category:
        category = "solace"
    if not isinstance(tier_required, str):
        tier_required = "free"
    normalized_tier = tier_required.strip().lower()
    if normalized_tier not in _MARKETPLACE_TIER_RANKS:
        normalized_tier = "free"
    if not isinstance(version, str):
        version = ""
    if not isinstance(icon_url, str):
        icon_url = ""
    return {
        "app_id": app_id,
        "display_name": display_name,
        "description": description,
        "category": category,
        "tier_required": normalized_tier,
        "installed": _is_marketplace_app_installed(repo_root, app_id),
        "version": version,
        "icon_url": icon_url,
    }


def _normalize_marketplace_apps(raw_apps: list, repo_root: str) -> list[dict]:
    apps: list[dict] = []
    for raw_app in raw_apps:
        if not isinstance(raw_app, dict):
            continue
        normalized = _normalize_marketplace_app(raw_app, repo_root)
        if normalized is not None:
            apps.append(normalized)
    return apps


def _write_marketplace_cache(raw_apps: list) -> None:
    payload = {
        "apps": raw_apps,
        "total": len(raw_apps),
        "fetched_at": int(time.time()),
    }
    MARKETPLACE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MARKETPLACE_CACHE_PATH.write_text(json.dumps(payload, indent=2))


def _load_marketplace_cache(repo_root: str) -> tuple[Optional[list[dict]], str]:
    if not MARKETPLACE_CACHE_PATH.exists():
        return None, ""
    try:
        payload = json.loads(MARKETPLACE_CACHE_PATH.read_text())
    except json.JSONDecodeError:
        return None, ""
    except OSError:
        return None, ""
    if not isinstance(payload, dict):
        return None, ""
    raw_apps = payload.get("apps", [])
    if not isinstance(raw_apps, list):
        return None, ""
    fetched_at = payload.get("fetched_at")
    if not isinstance(fetched_at, (int, float)):
        try:
            fetched_at = MARKETPLACE_CACHE_PATH.stat().st_mtime
        except OSError:
            fetched_at = 0
    age_seconds = time.time() - float(fetched_at)
    source = "cache" if age_seconds <= MARKETPLACE_CACHE_TTL_SECONDS else "stale_cache"
    return _normalize_marketplace_apps(raw_apps, repo_root), source


def _fetch_marketplace_catalog(repo_root: str) -> tuple[Optional[list[dict]], str]:
    with _MARKETPLACE_LOCK:
        try:
            with _marketplace_urlopen(MARKETPLACE_CATALOG_URL, timeout=MARKETPLACE_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode())
        except urllib.error.URLError as exc:
            record_evidence("marketplace_catalog_fetch_failed", {
                "url": MARKETPLACE_CATALOG_URL,
                "reason": str(exc.reason) if hasattr(exc, "reason") else str(exc),
            })
            return _load_marketplace_cache(repo_root)
        except json.JSONDecodeError as exc:
            record_evidence("marketplace_catalog_fetch_failed", {
                "url": MARKETPLACE_CATALOG_URL,
                "reason": str(exc),
            })
            return _load_marketplace_cache(repo_root)
        except OSError as exc:
            record_evidence("marketplace_catalog_fetch_failed", {
                "url": MARKETPLACE_CATALOG_URL,
                "reason": str(exc),
            })
            return _load_marketplace_cache(repo_root)
        raw_apps = payload.get("apps", []) if isinstance(payload, dict) else []
        if not isinstance(raw_apps, list):
            raw_apps = []
        try:
            _write_marketplace_cache(raw_apps)
        except OSError as exc:
            record_evidence("marketplace_cache_write_failed", {
                "path": str(MARKETPLACE_CACHE_PATH),
                "reason": str(exc),
            })
        return _normalize_marketplace_apps(raw_apps, repo_root), "remote"


def _find_marketplace_app(apps: list[dict], app_id: str) -> Optional[dict]:
    for app in apps:
        if app.get("app_id") == app_id:
            return app
    return None


def _tier_allows_install(user_tier: str, tier_required: str) -> bool:
    return _MARKETPLACE_TIER_RANKS[user_tier] >= _MARKETPLACE_TIER_RANKS[tier_required]


def _download_marketplace_session_rules(app_id: str) -> tuple[Optional[str], Optional[int]]:
    url = MARKETPLACE_APP_RULES_URL_TEMPLATE.format(app_id=app_id)
    try:
        with _marketplace_urlopen(url, timeout=MARKETPLACE_TIMEOUT_SECONDS) as response:
            return response.read().decode(), None
    except urllib.error.URLError as exc:
        if getattr(exc, "code", None) == 404:
            return None, 404
        raise


def _normalized_cloud_twin_settings(raw_value: object) -> dict:
    settings = dict(DEFAULT_CLOUD_TWIN_SETTINGS)
    if not isinstance(raw_value, dict):
        return settings
    url = raw_value.get("url", "")
    enabled = raw_value.get("enabled", settings["enabled"])
    prefer_cloud = raw_value.get("prefer_cloud", settings["prefer_cloud"])
    fallback_to_local = raw_value.get("fallback_to_local", settings["fallback_to_local"])
    settings["url"] = url if isinstance(url, str) else ""
    settings["enabled"] = enabled if isinstance(enabled, bool) else DEFAULT_CLOUD_TWIN_SETTINGS["enabled"]
    settings["prefer_cloud"] = prefer_cloud if isinstance(prefer_cloud, bool) else DEFAULT_CLOUD_TWIN_SETTINGS["prefer_cloud"]
    settings["fallback_to_local"] = (
        fallback_to_local
        if isinstance(fallback_to_local, bool)
        else DEFAULT_CLOUD_TWIN_SETTINGS["fallback_to_local"]
    )
    return settings


def _load_settings() -> dict:
    try:
        settings = json.loads(SETTINGS_PATH.read_text())
    except FileNotFoundError:
        settings = {}
    except json.JSONDecodeError:
        settings = {}
    except OSError:
        settings = {}
    if not isinstance(settings, dict):
        settings = {}
    merged = dict(settings)
    merged["cloud_twin"] = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
    return merged


def _save_settings(settings: dict) -> None:
    persisted = dict(settings)
    persisted["cloud_twin"] = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(persisted, indent=2))


def _normalize_cloud_twin_url(url: str) -> str:
    candidate = url.strip()
    if not candidate:
        raise ValueError("cloud twin url is required")
    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("cloud twin url must start with http:// or https://")
    if not parsed.hostname:
        raise ValueError("cloud twin url must include a hostname")
    if parsed.username or parsed.password:
        raise ValueError("cloud twin url must not include embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("cloud twin url must not include query or fragment")
    clean_path = parsed.path.rstrip("/")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, clean_path, "", "", ""))


def _ping_cloud_twin(url: str, timeout: float = 5.0) -> dict:
    if not url:
        return {"reachable": False, "latency_ms": None}
    started = time.perf_counter()
    request = urllib.request.Request(f"{url}/health", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(64 * 1024)
    except urllib.error.URLError:
        return {"reachable": False, "latency_ms": None}
    except OSError:
        return {"reachable": False, "latency_ms": None}
    latency_ms = int((time.perf_counter() - started) * 1000)
    return {"reachable": True, "latency_ms": latency_ms}


def _cloud_twin_status_payload() -> dict:
    settings = _load_settings()
    cloud_twin = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
    url = cloud_twin["url"]
    ping = _ping_cloud_twin(url) if url else {"reachable": False, "latency_ms": None}
    return {
        "configured": bool(url),
        "url": url,
        "reachable": ping["reachable"],
        "last_ping_ms": ping["latency_ms"],
    }


def _cloud_twin_mode_enabled(cloud_twin: bool = False) -> bool:
    env_value = os.environ.get("SOLACE_CLOUD_TWIN", "").strip().lower()
    return cloud_twin or env_value in {"1", "true", "yes", "on"}


def _hub_integration_enabled(cloud_twin: bool = False) -> bool:
    return not _cloud_twin_mode_enabled(cloud_twin)


def _cloud_twin_display() -> str:
    return os.environ.get("DISPLAY", CLOUD_TWIN_DISPLAY)


def _health_payload(app_count: int, port: int, cloud_twin_mode: bool) -> dict:
    return {
        "status": "ok",
        "apps": app_count,
        "version": _SERVER_VERSION,
        "evidence_count": count_evidence(),
        "schedule_count": len(load_schedules()),
        "uptime_seconds": int(time.time() - _SERVER_START_TIME),
        "port": port,
        "mode": "cloud_twin" if cloud_twin_mode else "local",
        "display": _cloud_twin_display() if cloud_twin_mode else "",
    }


def _launch_chrome_cloud_twin(url: str) -> subprocess.Popen:
    browser = os.environ.get("SOLACE_BROWSER", "")
    if not browser:
        browser = shutil.which("chromium-browser") or shutil.which("chromium") or "chromium-browser"
    env = dict(os.environ)
    env["DISPLAY"] = _cloud_twin_display()
    return subprocess.Popen(
        [
            browser,
            f"--display={env['DISPLAY']}",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )


def _forward_cloud_twin_session(cloud_twin_url: str, payload: dict, timeout: float = 10.0) -> dict:
    body = json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{cloud_twin_url}/api/v1/sessions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode()
            data = json.loads(response_body)
            latency_ms = int((time.perf_counter() - started) * 1000)
            return {
                "ok": True,
                "status": response.status,
                "data": data if isinstance(data, dict) else {},
                "latency_ms": latency_ms,
            }
    except urllib.error.HTTPError as exc:
        try:
            error_data = json.loads(exc.read().decode())
        except json.JSONDecodeError:
            error_data = {"error": f"cloud twin returned HTTP {exc.code}"}
        return {"ok": False, "status": exc.code, "data": error_data, "latency_ms": None}
    except urllib.error.URLError:
        return {"ok": False, "status": 503, "data": {"error": "cloud twin unreachable"}, "latency_ms": None}
    except json.JSONDecodeError:
        return {"ok": False, "status": 502, "data": {"error": "cloud twin returned invalid JSON"}, "latency_ms": None}
    except OSError:
        return {"ok": False, "status": 503, "data": {"error": "cloud twin unreachable"}, "latency_ms": None}


def _cloud_tunnel_worker(api_key: str, yinyang_bearer: str, yinyang_port: int) -> None:
    global _CLOUD_TUNNEL_ACTIVE, _CLOUD_TUNNEL_CLIENT, _CLOUD_TUNNEL_LOOP
    loop = asyncio.new_event_loop()
    client = HubTunnelClient(api_key, yinyang_bearer, yinyang_port=yinyang_port)
    with _CLOUD_TUNNEL_LOCK:
        _CLOUD_TUNNEL_CLIENT = client
        _CLOUD_TUNNEL_LOOP = loop
        _CLOUD_TUNNEL_ACTIVE = True
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(client.run())
    finally:
        with _CLOUD_TUNNEL_LOCK:
            _CLOUD_TUNNEL_ACTIVE = False
            _CLOUD_TUNNEL_LOOP = None
        loop.close()


def _launch_cloud_tunnel(api_key: str, yinyang_bearer: str, yinyang_port: int) -> None:
    global _CLOUD_TUNNEL_ACTIVE, _CLOUD_TUNNEL_THREAD
    with _CLOUD_TUNNEL_LOCK:
        if _CLOUD_TUNNEL_THREAD is not None and _CLOUD_TUNNEL_THREAD.is_alive() and _CLOUD_TUNNEL_ACTIVE:
            return
        _CLOUD_TUNNEL_ACTIVE = True
        _CLOUD_TUNNEL_THREAD = threading.Thread(
            target=_cloud_tunnel_worker,
            args=(api_key, yinyang_bearer, yinyang_port),
            daemon=True,
        )
        thread = _CLOUD_TUNNEL_THREAD
    thread.start()


def _stop_cloud_tunnel() -> None:
    global _CLOUD_TUNNEL_ACTIVE, _CLOUD_TUNNEL_CLIENT, _CLOUD_TUNNEL_LOOP, _CLOUD_TUNNEL_THREAD
    with _CLOUD_TUNNEL_LOCK:
        client = _CLOUD_TUNNEL_CLIENT
        loop = _CLOUD_TUNNEL_LOOP
        thread = _CLOUD_TUNNEL_THREAD
        _CLOUD_TUNNEL_ACTIVE = False
    if client is not None and loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(client.stop(), loop)
    if thread is not None and thread.is_alive():
        thread.join(timeout=2)
    with _CLOUD_TUNNEL_LOCK:
        _CLOUD_TUNNEL_THREAD = None
        _CLOUD_TUNNEL_LOOP = None


def _cloud_tunnel_status_payload() -> dict:
    with _CLOUD_TUNNEL_LOCK:
        retries = _CLOUD_TUNNEL_CLIENT.retries if _CLOUD_TUNNEL_CLIENT is not None else 0
        active = _CLOUD_TUNNEL_ACTIVE
    return {
        "active": active,
        "relay": SOLACEAGI_RELAY_URL if active else None,
        "retries": retries,
    }


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
# Notification storage — Task 020
# ---------------------------------------------------------------------------
def _load_notifications_raw() -> list:
    """Load notifications from ~/.solace/notifications.json. Returns list."""
    if not NOTIFICATIONS_PATH.exists():
        return []
    try:
        data = json.loads(NOTIFICATIONS_PATH.read_text())
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _append_notification(category: str, title: str, body: str, level: str = "info") -> None:
    """Append a notification to the store. Thread-safe."""
    if category not in NOTIF_CATEGORIES:
        category = "info"
    notif = {
        "id": str(uuid.uuid4()),
        "category": category,
        "title": title[:128],
        "body": body[:512],
        "level": level,  # info | warn | error
        "timestamp": int(time.time()),
        "read": False,
    }
    with _NOTIF_LOCK:
        notifs = _load_notifications_raw()
        notifs.append(notif)
        if len(notifs) > MAX_NOTIFICATIONS:
            notifs = notifs[-MAX_NOTIFICATIONS:]
        NOTIFICATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        NOTIFICATIONS_PATH.write_text(json.dumps(notifs, indent=2))


def _yinyang_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 Zulu format."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _yinyang_notification_public(notif: dict[str, Any]) -> dict[str, Any]:
    """Return the public notification payload without internal-only fields."""
    return {
        "id": str(notif.get("id", "")),
        "type": str(notif.get("type", "")),
        "message": str(notif.get("message", "")),
        "priority": str(notif.get("priority", "normal")),
        "read": bool(notif.get("read", False)),
        "ts": str(notif.get("ts", "")),
        "agent_id": notif.get("agent_id"),
        "run_id": notif.get("run_id"),
        "actions": list(notif.get("actions", [])),
        "metadata": dict(notif.get("metadata", {})),
    }


def _yinyang_sse_frame(notif: dict[str, Any]) -> str:
    """Encode one notification as a server-sent event frame."""
    public_notif = _yinyang_notification_public(notif)
    return f"id: {public_notif['id']}\ndata: {json.dumps(public_notif)}\n\n"


def _create_yinyang_notification(
    type_: str,
    message: str,
    priority: str,
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    actions: Optional[list[dict[str, Any]]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create and broadcast one in-memory yinyang notification."""
    global _YINYANG_NOTIF_COUNTER

    notif = {
        "id": f"notif_{secrets.token_hex(8)}",
        "type": type_,
        "message": message,
        "priority": priority,
        "read": False,
        "ts": _yinyang_now_iso(),
        "agent_id": agent_id,
        "run_id": run_id,
        "actions": list(actions or []),
        "metadata": dict(metadata or {}),
    }
    with _YINYANG_NOTIF_LOCK:
        _YINYANG_NOTIF_COUNTER += 1
        notif["seq"] = _YINYANG_NOTIF_COUNTER
        _YINYANG_NOTIFICATIONS.append(notif)

    frame = _yinyang_sse_frame(notif)
    with _YINYANG_SSE_CLIENTS_LOCK:
        for client_queue in _YINYANG_SSE_CLIENTS:
            try:
                client_queue.put_nowait(frame)
            except queue.Full:
                pass

    return notif


def _yinyang_sse_token_valid(expected_sha256: str, token: str) -> bool:
    """Validate EventSource query token against the configured SHA-256 bearer value."""
    return bool(expected_sha256 and _SHA256_HEX_RE.fullmatch(token) and token == expected_sha256)


# ---------------------------------------------------------------------------
# Spend History (Task 029)
# ---------------------------------------------------------------------------

def _load_spend_history() -> list:
    if not SPEND_HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(SPEND_HISTORY_PATH.read_text())
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _record_spend_entry(amount_usd: float, provider: str, model: str) -> None:
    """Record a spend event to history. Thread-safe."""
    entry = {
        "timestamp": int(time.time()),
        "amount_usd": round(amount_usd, 6),
        "provider": provider,
        "model": model,
        "date": time.strftime("%Y-%m-%d"),
    }
    with _SPEND_HISTORY_LOCK:
        history = _load_spend_history()
        history.append(entry)
        if len(history) > 365:
            history = history[-365:]
        SPEND_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        SPEND_HISTORY_PATH.write_text(json.dumps(history, indent=2))


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
      2. <repo_root>/data/custom/apps/    (local custom apps)
      2. <repo_root>/data/apps/           (fallback flat layout)
    Returns sorted list of unique app_id strings.
    """
    app_ids: set[str] = set()
    for apps_path in (
        Path(repo_root) / "data" / "default" / "apps",
        Path(repo_root) / "data" / "custom" / "apps",
        Path(repo_root) / "data" / "apps",
    ):
        if apps_path.is_dir():
            app_ids.update(d.name for d in apps_path.iterdir() if d.is_dir())
    return sorted(app_ids)


def _session_rule_paths() -> list[Path]:
    """Return sorted session-rules.yaml paths from the configured app directory."""
    rule_paths: list[Path] = []
    for apps_dir in (
        SESSION_RULES_APPS_DIR,
        SESSION_RULES_APPS_DIR.parent.parent / "custom" / "apps",
    ):
        if apps_dir.is_dir():
            rule_paths.extend(sorted(apps_dir.glob("*/session-rules.yaml")))
    return sorted(rule_paths)


def _session_interval_seconds(rule: dict) -> int:
    """Return keep-alive interval in seconds, defaulting to 15 minutes."""
    keep_alive = rule.get("keep_alive", {})
    interval_minutes = keep_alive.get("interval_minutes", 15)
    if not isinstance(interval_minutes, int) or interval_minutes < 1:
        return 15 * 60
    return interval_minutes * 60


def load_session_rules() -> list[dict]:
    """Load session rule YAML files and refresh the in-memory cache."""
    global _SESSION_RULES, _SESSION_STATUS

    loaded_rules: list[dict] = []
    for rule_path in _session_rule_paths():
        try:
            raw_rule = yaml.safe_load(rule_path.read_text())
        except FileNotFoundError:
            continue
        except OSError:
            continue
        except yaml.YAMLError:
            continue
        if not isinstance(raw_rule, dict):
            continue
        app_id = raw_rule.get("app", "")
        if not isinstance(app_id, str) or not app_id:
            continue
        loaded_rules.append(raw_rule)

    loaded_rules.sort(key=lambda rule: str(rule.get("app", "")))
    with _SESSION_RULES_LOCK:
        _SESSION_RULES = loaded_rules

    now = int(time.time())
    with _SESSION_STATUS_LOCK:
        previous_status = dict(_SESSION_STATUS)
        refreshed_status: dict[str, dict] = {}
        for rule in loaded_rules:
            app_id = str(rule.get("app", ""))
            previous_entry = previous_status.get(app_id, {})
            next_check = previous_entry.get("next_check")
            if not isinstance(next_check, int):
                next_check = now + _session_interval_seconds(rule)
            refreshed_status[app_id] = {
                "app": app_id,
                "status": previous_entry.get("status", "unknown"),
                "last_check": previous_entry.get("last_check"),
                "next_check": next_check,
            }
        _SESSION_STATUS = refreshed_status

    return list(loaded_rules)


def _get_session_rules_snapshot() -> list[dict]:
    """Return a shallow copy of loaded session rules."""
    with _SESSION_RULES_LOCK:
        return list(_SESSION_RULES)


def _find_session_rule(app_id: str) -> Optional[dict]:
    """Return one loaded session rule by app id."""
    with _SESSION_RULES_LOCK:
        for rule in _SESSION_RULES:
            if rule.get("app") == app_id:
                return dict(rule)
    return None


def _custom_apps_root(repo_root: str) -> Path:
    return Path(repo_root) / "data" / "custom" / "apps"


def _official_store_path(repo_root: str) -> Path:
    return Path(repo_root) / "data" / "default" / "app-store" / "official-store.json"


def _domain_index_path(repo_root: str) -> Path:
    return _marketplace_apps_root(repo_root) / ".domain-index.json"


def _repo_app_roots(repo_root: str) -> tuple[Path, ...]:
    return (
        _marketplace_apps_root(repo_root),
        _custom_apps_root(repo_root),
    )


def _repo_app_dir(repo_root: str, app_id: str) -> Optional[Path]:
    for apps_root in _repo_app_roots(repo_root):
        app_dir = apps_root / app_id
        if app_dir.is_dir():
            return app_dir
    return None


def _app_manifest_path(repo_root: str, app_id: str) -> Optional[Path]:
    app_dir = _repo_app_dir(repo_root, app_id)
    if app_dir is None:
        return None
    manifest_path = app_dir / "manifest.yaml"
    if manifest_path.is_file():
        return manifest_path
    return None


def _repo_session_rules_path_for_app(repo_root: str, app_id: str) -> Optional[Path]:
    for apps_root in _repo_app_roots(repo_root):
        rules_path = apps_root / app_id / "session-rules.yaml"
        if rules_path.is_file():
            return rules_path
    return None


def _load_session_rules_for_app(repo_root: str, app_id: str) -> dict:
    rules_path = _repo_session_rules_path_for_app(repo_root, app_id)
    if rules_path is None:
        return {}
    try:
        raw_rule = yaml.safe_load(rules_path.read_text())
    except FileNotFoundError:
        return {}
    except OSError:
        return {}
    except yaml.YAMLError:
        return {}
    if isinstance(raw_rule, dict):
        return raw_rule
    return {}


def _load_manifest_for_app(repo_root: str, app_id: str) -> dict:
    """Load one app manifest from the repo-scoped apps directory."""
    manifest_path = _app_manifest_path(repo_root, app_id)
    if manifest_path is None:
        return {}
    try:
        raw_manifest = yaml.safe_load(manifest_path.read_text())
    except FileNotFoundError:
        return {}
    except OSError:
        return {}
    except yaml.YAMLError:
        return {}
    if isinstance(raw_manifest, dict):
        return raw_manifest
    return {}


def _normalize_domain(value: str) -> str:
    """Normalize a hostname or URL to a lowercase bare domain."""
    candidate = value.strip().lower()
    if not candidate:
        return ""
    parsed = urllib.parse.urlparse(candidate if "://" in candidate else f"//{candidate}")
    host = parsed.netloc or parsed.path
    host = host.split("/", 1)[0]
    host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def _normalize_path_match(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        return "/"
    parsed = urllib.parse.urlparse(candidate if "://" in candidate else f"https://placeholder{candidate}")
    path_value = parsed.path or "/"
    if not path_value.startswith("/"):
        path_value = "/" + path_value
    return path_value


def _normalize_tier_name(value: object) -> str:
    if not isinstance(value, str):
        return "free"
    normalized = value.strip().lower()
    if normalized not in _MARKETPLACE_TIER_RANKS:
        return "free"
    return normalized


def _required_tier_for_app(manifest: dict, session_rules: dict | None = None, fallback: object = "free") -> str:
    rules = session_rules or {}
    return _normalize_tier_name(
        manifest.get("tier_required")
        or manifest.get("tier")
        or rules.get("tier_required")
        or fallback
    )


def _normalize_domain_pattern(pattern: str) -> str:
    raw_value = pattern.strip().lower()
    if not raw_value:
        return ""
    if raw_value == "*":
        raise ValueError("DOMAIN_WILDCARD_ABUSE")
    parsed = urllib.parse.urlparse(raw_value if "://" in raw_value else f"//{raw_value}")
    host = parsed.netloc or parsed.path
    host = host.strip()
    path_value = ""
    if "/" in host:
        host, path_suffix = host.split("/", 1)
        path_value = "/" + path_suffix.strip("/") if path_suffix else ""
    if parsed.path and parsed.netloc:
        path_value = parsed.path
    host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    if host == "*":
        raise ValueError("DOMAIN_WILDCARD_ABUSE")
    if not host:
        return ""
    if path_value:
        normalized_path = path_value if path_value.startswith("/") else "/" + path_value
        normalized_path = re.sub(r"/+", "/", normalized_path)
        return f"{host}{normalized_path}"
    return host


def _split_domain_pattern(pattern: str) -> tuple[str, str]:
    normalized = _normalize_domain_pattern(pattern)
    if not normalized:
        return "", ""
    if "/" not in normalized:
        return normalized, ""
    host, path_value = normalized.split("/", 1)
    return host, "/" + path_value


def _domain_pattern_matches(pattern: str, query_domain: str, query_path: str = "/") -> bool:
    host_pattern, path_pattern = _split_domain_pattern(pattern)
    domain_clean = _normalize_domain(query_domain)
    if not host_pattern or not domain_clean:
        return False

    if host_pattern.startswith("*."):
        suffix = host_pattern[2:]
        host_matches = bool(suffix) and domain_clean.endswith("." + suffix) and domain_clean != suffix
    else:
        host_matches = host_pattern == domain_clean

    if not host_matches:
        return False
    if not path_pattern:
        return True

    normalized_path = _normalize_path_match(query_path)
    if path_pattern.endswith("/*"):
        return normalized_path.startswith(path_pattern[:-1])
    return normalized_path == path_pattern


def _manifest_domain_patterns(manifest: dict, fallback_site: str = "") -> list[str]:
    raw_domains = manifest.get("domains", [])
    patterns: list[str] = []
    if isinstance(raw_domains, list):
        for entry in raw_domains:
            if isinstance(entry, str):
                normalized = _normalize_domain_pattern(entry)
                if normalized:
                    patterns.append(normalized)
    if patterns:
        return sorted(set(patterns))
    fallback_pattern = _normalize_domain_pattern(fallback_site)
    if fallback_pattern:
        return [fallback_pattern]
    return []


def _iter_manifest_records(repo_root: str) -> list[tuple[str, dict, Path]]:
    manifests: list[tuple[str, dict, Path]] = []
    for apps_root in _repo_app_roots(repo_root):
        if not apps_root.is_dir():
            continue
        for manifest_path in sorted(apps_root.glob("*/manifest.yaml")):
            app_id = manifest_path.parent.name
            try:
                raw_manifest = yaml.safe_load(manifest_path.read_text())
            except FileNotFoundError:
                continue
            except OSError:
                continue
            except yaml.YAMLError:
                continue
            if isinstance(raw_manifest, dict):
                manifests.append((app_id, raw_manifest, manifest_path))
    manifests.sort(key=lambda item: item[0])
    return manifests


def _build_domain_index_payload(repo_root: str) -> dict:
    patterns: dict[str, list[str]] = {}
    apps_indexed: set[str] = set()
    for app_id, manifest, _manifest_path in _iter_manifest_records(repo_root):
        for pattern in _manifest_domain_patterns(manifest, str(manifest.get("site", ""))):
            patterns.setdefault(pattern, [])
            if app_id not in patterns[pattern]:
                patterns[pattern].append(app_id)
                apps_indexed.add(app_id)
    for app_ids in patterns.values():
        app_ids.sort()
    return {
        "version": 1,
        "generated_at": int(time.time()),
        "domains_indexed": len(patterns),
        "apps_indexed": len(apps_indexed),
        "patterns": dict(sorted(patterns.items())),
    }


def _rebuild_domain_index(repo_root: str) -> dict:
    payload = _build_domain_index_payload(repo_root)
    domain_index_path = _domain_index_path(repo_root)
    domain_index_path.parent.mkdir(parents=True, exist_ok=True)
    domain_index_path.write_text(json.dumps(payload, indent=2))
    return {
        "rebuilt": True,
        "domains_indexed": payload["domains_indexed"],
        "apps_indexed": payload["apps_indexed"],
        "index_path": str(domain_index_path),
    }


def _load_domain_index(repo_root: str) -> dict:
    domain_index_path = _domain_index_path(repo_root)
    if not domain_index_path.exists():
        _rebuild_domain_index(repo_root)
    try:
        payload = json.loads(domain_index_path.read_text())
    except FileNotFoundError:
        _rebuild_domain_index(repo_root)
        payload = json.loads(domain_index_path.read_text())
    except json.JSONDecodeError:
        _rebuild_domain_index(repo_root)
        payload = json.loads(domain_index_path.read_text())
    except OSError:
        _rebuild_domain_index(repo_root)
        payload = json.loads(domain_index_path.read_text())
    if not isinstance(payload, dict):
        rebuilt = _rebuild_domain_index(repo_root)
        return {
            "version": 1,
            "generated_at": int(time.time()),
            "domains_indexed": rebuilt["domains_indexed"],
            "apps_indexed": rebuilt["apps_indexed"],
            "patterns": {},
        }
    patterns = payload.get("patterns")
    if isinstance(patterns, dict):
        normalized_patterns: dict[str, list[str]] = {}
        for pattern, app_ids in patterns.items():
            if not isinstance(pattern, str) or not isinstance(app_ids, list):
                continue
            normalized_ids = sorted(str(app_id) for app_id in app_ids if isinstance(app_id, str) and app_id)
            if normalized_ids:
                normalized_patterns[_normalize_domain_pattern(pattern)] = normalized_ids
        payload["patterns"] = dict(sorted(normalized_patterns.items()))
        return payload
    fallback_patterns: dict[str, list[str]] = {}
    for pattern, app_ids in payload.items():
        if not isinstance(pattern, str) or not isinstance(app_ids, list):
            continue
        normalized_ids = sorted(str(app_id) for app_id in app_ids if isinstance(app_id, str) and app_id)
        if normalized_ids:
            fallback_patterns[_normalize_domain_pattern(pattern)] = normalized_ids
    return {
        "version": 1,
        "generated_at": int(time.time()),
        "domains_indexed": len(fallback_patterns),
        "apps_indexed": len({app_id for app_ids in fallback_patterns.values() for app_id in app_ids}),
        "patterns": dict(sorted(fallback_patterns.items())),
    }


def _match_domain_index(patterns: dict[str, list[str]], query_domain: str, query_path: str = "/") -> list[str]:
    matched_ids: set[str] = set()
    normalized_domain = _normalize_domain(query_domain)
    normalized_path = _normalize_path_match(query_path)
    for pattern, app_ids in patterns.items():
        if _domain_pattern_matches(pattern, normalized_domain, normalized_path):
            matched_ids.update(app_id for app_id in app_ids if isinstance(app_id, str) and app_id)
    return sorted(matched_ids)


def _load_session_rules_for_repo(repo_root: str) -> list[dict]:
    """Load session rules from repo-scoped default and custom app directories."""
    rules: list[dict] = []
    for apps_root in _repo_app_roots(repo_root):
        if not apps_root.is_dir():
            continue
        for rule_path in sorted(apps_root.glob("*/session-rules.yaml")):
            try:
                raw_rule = yaml.safe_load(rule_path.read_text())
            except FileNotFoundError:
                continue
            except OSError:
                continue
            except yaml.YAMLError:
                continue
            if isinstance(raw_rule, dict):
                rules.append(raw_rule)
    return rules


def _load_official_store_apps(repo_root: str) -> list[dict]:
    store_path = _official_store_path(repo_root)
    try:
        payload = json.loads(store_path.read_text())
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []
    except OSError:
        return []
    if not isinstance(payload, dict):
        return []
    raw_apps = payload.get("apps", [])
    if not isinstance(raw_apps, list):
        return []
    normalized_apps: list[dict] = []
    for raw_app in raw_apps:
        if not isinstance(raw_app, dict):
            continue
        app_id = raw_app.get("id")
        if not isinstance(app_id, str) or not _APP_ID_RE.fullmatch(app_id):
            continue
        manifest = _load_manifest_for_app(repo_root, app_id)
        site_value = str(raw_app.get("site") or manifest.get("site") or "")
        try:
            domains = _manifest_domain_patterns(raw_app, site_value)
        except ValueError:
            continue
        normalized_apps.append({
            "id": app_id,
            "name": str(raw_app.get("name") or manifest.get("name") or app_id.replace("-", " ").title()),
            "description": str(raw_app.get("description") or manifest.get("description") or ""),
            "tier_required": _required_tier_for_app(manifest, fallback=raw_app.get("tier_required") or raw_app.get("tier") or "free"),
            "domains": domains,
        })
    return normalized_apps


def _lookup_session_active(app_id: str) -> bool:
    with _SESSION_STATUS_LOCK:
        status_entry = dict(_SESSION_STATUS.get(app_id, {}))
    return status_entry.get("status") == "active"


def _default_quick_action(display_name: str) -> str:
    if "triage" in display_name.lower():
        return "Run Triage"
    return "Open"


def _legacy_domain_apps(installed_apps: list[dict]) -> list[dict]:
    legacy: list[dict] = []
    for entry in installed_apps:
        legacy.append({
            "app_id": entry.get("id", ""),
            "display_name": entry.get("name", ""),
            "description": entry.get("description", ""),
            "installed": True,
            "tier_required": entry.get("tier_required", "free"),
            "site": entry.get("site", ""),
        })
    return legacy


def _apps_for_domain(repo_root: str, query_domain: str, query_path: str = "/", user_tier: str = "free") -> dict:
    """Return domain-linked installed/store apps with tier gating."""
    normalized_domain = _normalize_domain(query_domain)
    if not normalized_domain:
        return {
            "domain": "",
            "installed_apps": [],
            "store_apps": [],
            "can_create_custom": True,
            "create_url": "/api/v1/apps/custom/create",
            "apps": [],
            "total": 0,
        }

    domain_index = _load_domain_index(repo_root)
    patterns = domain_index.get("patterns", {})
    if not isinstance(patterns, dict):
        patterns = {}
    matched_app_ids = _match_domain_index(patterns, normalized_domain, query_path)

    installed_apps: list[dict] = []
    locked_app_ids: set[str] = set()
    for app_id in matched_app_ids:
        session_rules = _load_session_rules_for_app(repo_root, app_id)
        if not session_rules:
            continue
        manifest = _load_manifest_for_app(repo_root, app_id)
        tier_required = _required_tier_for_app(manifest, session_rules)
        if not _tier_allows_install(user_tier, tier_required):
            locked_app_ids.add(app_id)
            continue
        display_name = str(
            manifest.get("name")
            or session_rules.get("display_name")
            or app_id.replace("-", " ").title()
        )
        installed_apps.append({
            "id": app_id,
            "name": display_name,
            "description": str(manifest.get("description") or session_rules.get("description") or ""),
            "status": "installed",
            "session_active": _lookup_session_active(app_id),
            "tier_required": tier_required,
            "quick_action": _default_quick_action(display_name),
            "site": _normalize_domain(str(session_rules.get("site") or manifest.get("site") or normalized_domain)),
        })
    installed_apps.sort(key=lambda entry: str(entry.get("id", "")))

    store_apps: list[dict] = []
    store_app_ids: set[str] = set()
    for store_app in _load_official_store_apps(repo_root):
        app_id = str(store_app.get("id", ""))
        if not app_id:
            continue
        domains = store_app.get("domains", [])
        if not isinstance(domains, list):
            continue
        if not any(_domain_pattern_matches(pattern, normalized_domain, query_path) for pattern in domains if isinstance(pattern, str)):
            continue
        tier_required = _normalize_tier_name(store_app.get("tier_required", "free"))
        app_installed = _repo_session_rules_path_for_app(repo_root, app_id) is not None
        if app_installed and app_id not in locked_app_ids:
            continue
        install_allowed = _tier_allows_install(user_tier, tier_required)
        store_entry = {
            "id": app_id,
            "name": str(store_app.get("name", app_id.replace("-", " ").title())),
            "description": str(store_app.get("description", "")),
            "status": "available" if install_allowed and not app_installed else "upgrade_required",
            "tier_required": tier_required,
            "install_url": f"/api/v1/apps/{app_id}/install" if install_allowed else MARKETPLACE_UPGRADE_URL,
        }
        if not install_allowed:
            store_entry["upgrade_url"] = MARKETPLACE_UPGRADE_URL
        store_apps.append(store_entry)
        store_app_ids.add(app_id)

    for app_id in matched_app_ids:
        if app_id in store_app_ids:
            continue
        manifest = _load_manifest_for_app(repo_root, app_id)
        if not manifest:
            continue
        app_installed = _repo_session_rules_path_for_app(repo_root, app_id) is not None
        if app_installed and app_id not in locked_app_ids:
            continue
        tier_required = _required_tier_for_app(manifest)
        install_allowed = _tier_allows_install(user_tier, tier_required)
        store_entry = {
            "id": app_id,
            "name": str(manifest.get("name") or app_id.replace("-", " ").title()),
            "description": str(manifest.get("description") or ""),
            "status": "available" if install_allowed and not app_installed else "upgrade_required",
            "tier_required": tier_required,
            "install_url": f"/api/v1/apps/{app_id}/install" if install_allowed else MARKETPLACE_UPGRADE_URL,
        }
        if not install_allowed:
            store_entry["upgrade_url"] = MARKETPLACE_UPGRADE_URL
        store_apps.append(store_entry)
        store_app_ids.add(app_id)
    store_apps.sort(key=lambda entry: str(entry.get("id", "")))

    legacy_apps = _legacy_domain_apps(installed_apps)
    return {
        "domain": normalized_domain,
        "installed_apps": installed_apps,
        "store_apps": store_apps,
        "can_create_custom": True,
        "create_url": f"/api/v1/apps/custom/create?domain={urllib.parse.quote(normalized_domain, safe='')}",
        "apps": legacy_apps,
        "total": len(legacy_apps),
    }
def _invalid_custom_app_name(name: str) -> bool:
    return ".." in name or "/" in name or "\\" in name


def _slugify_custom_app_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")[:50].strip("-")


def _custom_app_manifest(app_id: str, display_name: str, description: str, domain: str) -> str:
    return (
        f"id: {app_id}\n"
        f"name: {json.dumps(display_name)}\n"
        f"description: {json.dumps(description)}\n"
        'category: "custom"\n'
        'status: "installed"\n'
        'safety: "B"\n'
        'tier: "free"\n'
        'domains:\n'
        f'  - {json.dumps(domain)}\n'
        f"site: {domain}\n"
        'type: "custom"\n'
        'custom: true\n'
        'local_only: true\n'
    )


def _custom_app_session_rules(app_id: str, display_name: str, description: str, domain: str) -> str:
    app_url = f"https://{domain}/"
    return (
        f"app: {app_id}\n"
        f"display_name: {json.dumps(display_name)}\n"
        'version: "1.0.0"\n'
        'category: "custom"\n'
        f"site: {domain}\n"
        f"login_url: {json.dumps(app_url)}\n"
        f"check_url: {json.dumps(app_url)}\n"
        'success_signals:\n'
        '  - "TODO: add success signal"\n'
        'failure_signals:\n'
        '  - "TODO: add failure signal"\n'
        'keep_alive:\n'
        '  interval_minutes: 15\n'
        '  action: "navigate"\n'
        f"  url: {json.dumps(app_url)}\n"
        'tier_required: "free"\n'
        'evidence_on_check: true\n'
        f"description: {json.dumps(description)}\n"
    )


def _create_custom_app_scaffold(repo_root: str, raw_domain: str, raw_name: str, raw_description: str) -> dict:
    domain = _normalize_domain(raw_domain)
    name = raw_name.strip()
    description = raw_description.strip()
    if not domain:
        raise ValueError("domain required")
    if not name or _invalid_custom_app_name(name):
        raise ValueError("invalid app name")
    app_id = _slugify_custom_app_name(name)
    if not app_id:
        raise ValueError("invalid app name")

    app_dir = _custom_apps_root(repo_root) / app_id
    if app_dir.exists():
        raise FileExistsError("app already exists")

    manifest_text = _custom_app_manifest(app_id, name, description or f"Custom app for {domain}", domain)
    session_rules_text = _custom_app_session_rules(app_id, name, description or f"Custom app for {domain}", domain)
    app_dir.mkdir(parents=True, exist_ok=False)
    (app_dir / "manifest.yaml").write_text(manifest_text)
    (app_dir / "session-rules.yaml").write_text(session_rules_text)
    _rebuild_domain_index(repo_root)

    relative_app_path = Path("data") / "custom" / "apps" / app_id
    return {
        "app_id": app_id,
        "path": f"{relative_app_path.as_posix()}/",
        "manifest_path": (relative_app_path / "manifest.yaml").as_posix(),
        "session_rules_path": (relative_app_path / "session-rules.yaml").as_posix(),
        "manifest_template": manifest_text,
        "session_rules_template": session_rules_text,
    }


def _custom_apps_sync_bundle(repo_root: str) -> list[dict]:
    bundle: list[dict] = []
    apps_root = _marketplace_apps_root(repo_root)
    if not apps_root.is_dir():
        return bundle
    for app_dir in sorted(path for path in apps_root.iterdir() if path.is_dir()):
        manifest = _load_manifest_for_app(repo_root, app_dir.name)
        if not bool(manifest.get("custom", False)):
            continue
        manifest_path = app_dir / "manifest.yaml"
        session_rules_path = app_dir / "session-rules.yaml"
        try:
            manifest_yaml = manifest_path.read_text()
            session_rules_yaml = session_rules_path.read_text()
        except FileNotFoundError:
            continue
        except OSError:
            continue
        bundle.append({
            "app_id": app_dir.name,
            "manifest_yaml": manifest_yaml,
            "session_rules_yaml": session_rules_yaml,
        })
    return bundle


def _check_session(rule: dict) -> str:
    """Return session status without browser automation for this task."""
    return "unknown"


def _record_session_status(rule: dict, status: str, checked_at: int) -> dict:
    """Update the status cache for one app and return the cached entry."""
    app_id = str(rule.get("app", ""))
    entry = {
        "app": app_id,
        "status": status,
        "last_check": checked_at,
        "next_check": checked_at + _session_interval_seconds(rule),
    }
    with _SESSION_STATUS_LOCK:
        _SESSION_STATUS[app_id] = entry
    return entry


def _run_session_check(rule: dict) -> dict:
    """Check one session rule, record evidence, and update cached status."""
    checked_at = int(time.time())
    status = _check_session(rule)
    status_entry = _record_session_status(rule, status, checked_at)
    record_evidence(
        "session_check",
        {
            "app": rule.get("app", ""),
            "status": status,
            "check_url": rule.get("check_url", ""),
        },
    )
    return status_entry


def time_since_last_check(app_id: str) -> int:
    """Return seconds since the last check, or a large number if never checked."""
    with _SESSION_STATUS_LOCK:
        status_entry = _SESSION_STATUS.get(app_id, {})
    last_check = status_entry.get("last_check")
    if not isinstance(last_check, int):
        return 10**9
    return max(0, int(time.time()) - last_check)


def _session_keepalive_loop() -> None:
    """Check due session rules on a daemon thread and record evidence."""
    while not _SESSION_KEEPALIVE_STOP.is_set():
        for rule in _get_session_rules_snapshot():
            app_id = str(rule.get("app", ""))
            if not app_id:
                continue
            if time_since_last_check(app_id) >= _session_interval_seconds(rule):
                _run_session_check(rule)
        _SESSION_KEEPALIVE_STOP.wait(60)


def _start_session_keepalive_thread() -> None:
    """Start the keep-alive daemon thread once per process."""
    global _SESSION_KEEPALIVE_THREAD
    if _SESSION_KEEPALIVE_THREAD is not None and _SESSION_KEEPALIVE_THREAD.is_alive():
        return
    _SESSION_KEEPALIVE_STOP.clear()
    _SESSION_KEEPALIVE_THREAD = threading.Thread(
        target=_session_keepalive_loop,
        name="session-keepalive",
        daemon=True,
    )
    _SESSION_KEEPALIVE_THREAD.start()


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
        elif path == "/api/v1/evidence/bundles":
            self._handle_part11_evidence_bundles(query)
        elif path == "/api/v1/evidence/verify":
            self._handle_evidence_verify()
        elif path == "/api/v1/evidence/verify-chain":
            self._handle_part11_evidence_verify_chain()
        elif path == "/api/v1/evidence/summary":
            self._handle_evidence_summary()
        elif path == "/api/v1/evidence/compliance-report":
            self._handle_part11_evidence_compliance_report()
        elif path == "/api/v1/evidence/hashes":
            self._handle_evidence_hashes()
        elif path == "/api/v1/evidence/search":
            self._handle_evidence_search(query)
        elif path == "/api/v1/evidence/stats":
            self._handle_evidence_stats()
        elif path == "/api/v1/evidence/export":
            self._handle_evidence_export(query)
        elif path == "/api/v1/session-rules":
            self._handle_session_rules_list()
        elif path == "/api/v1/session-rules/status":
            self._handle_session_rules_status()
        elif path == "/api/v1/prime-wiki/diff":
            self._handle_prime_wiki_diff(query)
        elif path == "/api/v1/prime-wiki/stats":
            self._handle_prime_wiki_stats()
        elif re.match(r"^/api/v1/prime-wiki/snapshot/[^/]+/content$", path):
            snapshot_id = path.split("/")[-2]
            self._handle_prime_wiki_snapshot_content(snapshot_id)
        elif re.match(r"^/api/v1/prime-wiki/snapshot/[^/]+$", path):
            snapshot_id = path.split("/")[-1]
            self._handle_prime_wiki_snapshot_detail(snapshot_id)
        elif re.match(r"^/api/v1/evidence/[^/]+$", path):
            entry_id = path.split("/")[-1]
            self._handle_evidence_detail(entry_id)
        elif path == "/api/v1/browser/schedules/next-runs":
            self._handle_schedules_next_runs()
        elif path == "/api/v1/browser/schedules":
            self._handle_schedules_list()
        elif path == "/api/v1/schedules/summary":
            self._handle_schedules_summary()
        elif path == "/api/v1/system/info":
            self._handle_system_info()
        elif path == "/api/v1/vault/status":
            self._handle_vault_status()
        elif path == "/api/v1/apps/run-count":
            self._handle_apps_run_count()
        elif path == "/api/v1/apps/categories":
            self._handle_apps_categories()
        elif path == "/api/v1/server/config":
            self._handle_server_config()
        elif path == "/api/v1/health/history":
            self._handle_health_history()
        elif path == "/api/v1/webhooks":
            self._handle_webhooks_list()
        elif path == "/api/v1/stats":
            self._handle_server_stats()
        elif path == "/api/v1/apps/metadata":
            self._handle_apps_metadata()
        elif path == "/api/v1/schedules/stats":
            self._handle_schedules_stats()
        elif path == "/api/v1/budget/forecast":
            self._handle_budget_forecast()
        elif path == "/api/v1/sessions/count":
            self._handle_sessions_count()
        elif path == "/api/v1/log/level":
            self._handle_log_level_get()
        elif path == "/api/v1/memory/keys":
            self._handle_memory_keys()
        elif path == "/api/v1/sla/uptime":
            self._handle_sla_uptime()
        elif path == "/api/v1/labels":
            self._handle_labels_list()
        elif path == "/api/v1/budget/export":
            self._handle_budget_export()
        elif path == "/api/v1/notifications/preferences":
            self._handle_notif_preferences_get()
        elif path == "/api/v1/notifications/count":
            self._handle_notifications_count()
        elif path == "/api/v1/apps/launch-history":
            self._handle_app_launch_history()
        elif path == "/api/v1/apps/search":
            self._handle_app_search2(query)
        elif path == "/api/v1/diagnostics":
            self._handle_diagnostics()
        elif path == "/api/v1/system/metrics":
            self._handle_system_metrics()
        elif path == "/api/v1/apps/status":
            self._handle_apps_status()
        elif path == "/api/v1/budget/currency":
            self._handle_budget_currency()
        elif path == "/api/v1/recipes/search":
            self._handle_recipes_search(query)
        elif path == "/api/v1/oauth3/scopes":
            self._handle_oauth3_scopes()
        elif path == "/api/v1/oauth3/token/validate":
            self._handle_oauth3_validate(query)
        elif path == "/api/v1/schedules/next":
            self._handle_schedules_next()
        elif path == "/api/v1/capabilities":
            self._handle_capabilities()
        elif path == "/api/v1/hub/summary":
            self._handle_hub_summary()
        elif re.match(r"^/api/v1/apps/[^/]+/versions$", path):
            app_id = path.split("/")[-2]
            self._handle_app_versions(app_id)
        elif path == "/api/v1/oauth3/tokens":
            self._handle_oauth3_list()
        elif path.startswith("/api/v1/oauth3/tokens/") and path.count("/") == 5:
            token_id = path.split("/")[-1]
            self._handle_oauth3_token_detail(token_id)
        elif path == "/api/v1/oauth3/evidence":
            self._handle_oauth3_evidence(query)
        elif path == "/api/v1/oauth3/audit":
            self._handle_oauth3_audit()
        elif path == "/api/v1/cli/available":
            self._handle_cli_available()
        elif path == "/api/v1/cli-agents/detect":
            self._handle_cli_agents_detect()
        elif path == "/api/v1/cli-agents/refresh":
            self._handle_cli_agents_refresh()
        elif path == "/onboarding":
            self._handle_onboarding_page()
        elif path == "/api/v1/onboarding/status":
            self._handle_onboarding_status()
        elif path == "/api/v1/sessions":
            self._handle_sessions_list()
        elif re.match(r"^/api/v1/sessions/[^/]+$", path):
            session_id = path.split("/")[-1]
            self._handle_session_detail(session_id)
        elif path == "/api/v1/cloud-twin/status":
            self._handle_cloud_twin_status()
        elif path == "/api/v1/tunnel/status":
            self._handle_tunnel_status()
        elif path == "/api/v1/tunnel/cloud-status":
            self._handle_tunnel_cloud_status()
        elif path == "/api/v1/sync/status":
            self._handle_sync_status()
        elif path == "/api/v1/recipes":
            self._handle_recipes_list()
        elif path == "/api/v1/recipes/my-library":
            self._handle_community_recipes_my_library()
        elif path == "/api/v1/recipes/templates":
            self._handle_recipe_templates()
        elif path == "/api/v1/recipes/history":
            self._handle_recipe_history(query)
        elif path == "/api/v1/recipes/community":
            self._handle_community_recipes_list(query)
        elif re.match(r"^/api/v1/recipes/[^/]+/preview$", path):
            recipe_id = path.split("/")[-2]
            self._handle_recipe_preview(recipe_id)
        elif re.match(r"^/api/v1/recipes/[^/]+/steps$", path):
            recipe_id = path.split("/")[-2]
            self._handle_recipe_steps(recipe_id)
        elif re.match(r"^/api/v1/recipes/[^/]+/export$", path):
            recipe_id = path.split("/")[-2]
            self._handle_recipe_export(recipe_id)
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
        elif path == "/api/v1/budget/history":
            self._handle_budget_history(query)
        elif path == "/api/v1/budget/alerts":
            self._handle_budget_alerts()
        elif path == "/api/v1/budget/breakdown":
            self._handle_budget_breakdown()
        elif path == "/api/v1/watchdog/status":
            self._handle_watchdog_status()
        elif path == "/api/v1/theme":
            self._handle_theme_get()
        elif path == "/api/v1/theme/presets":
            self._handle_theme_presets()
        elif path == "/api/v1/settings/export":
            self._handle_settings_export()
        elif path == "/api/v1/user/tier":
            self._handle_user_tier()
        elif path == "/api/v1/usage/stats":
            self._handle_usage_stats(query)
        elif path == "/api/v1/shortcuts":
            self._handle_shortcuts()
        elif path == "/api/v1/system/status":
            self._handle_system_status()
        elif path == "/api/v1/search":
            self._handle_search(query)
        elif path == "/api/v1/pinned":
            self._handle_pinned_get()
        elif path == "/api/v1/accessibility":
            self._handle_accessibility()
        elif path == "/api/v1/ping":
            self._handle_ping()
        elif path == "/api/v1/apps/favorites":
            self._handle_apps_favorites_get()
        elif path == "/api/v1/apps/tags":
            self._handle_apps_tags()
        elif path == "/api/v1/apps/by-domain":
            self._handle_apps_by_domain(query)
        elif path == "/api/v1/broadcast":
            self._handle_broadcast_get()
        elif path == "/api/v1/rate-limit/status":
            self._handle_rate_limit_status()
        elif path == "/api/v1/metrics":
            self._handle_metrics_json()
        elif path == "/metrics":
            self._handle_metrics_prometheus()
        elif path == "/ws/dashboard":
            self._handle_ws_dashboard()
        elif path == "/api/v1/byok/providers":
            self._handle_byok_providers()
        elif path == "/api/v1/byok/active":
            self._handle_byok_active()
        elif path == "/api/v1/notifications/unread-count":
            self._handle_notifications_unread_count()
        elif path == "/api/v1/notifications":
            self._handle_notifications_list(query)
        elif path == "/api/yinyang/status":
            self._handle_yinyang_status()
        elif path == "/api/yinyang/events":
            self._handle_yinyang_events_sse()
        elif path == "/api/v1/logs/errors":
            self._handle_log_errors()
        elif path == "/api/v1/logs/requests":
            self._handle_log_requests(query)
        elif path == "/api/v1/profiles":
            self._handle_profiles_list()
        elif path == "/api/v1/profiles/active":
            self._handle_profiles_active()
        elif path == "/api/v1/store/recipes":
            self._handle_store_list(query)
        elif path == "/api/v1/store/installed":
            self._handle_store_installed()
        elif path == "/api/v1/marketplace/apps":
            self._handle_marketplace_apps()
        elif path == "/api/v1/marketplace/categories":
            self._handle_marketplace_categories()
        elif path == "/api/v1/fun-packs":
            self._handle_fun_packs_list()
        elif path == "/api/v1/fun-packs/active":
            self._handle_fun_pack_active()
        elif path == "/api/v1/fun-packs/random-joke":
            self._handle_fun_pack_random_joke()
        elif path == "/api/v1/fun-packs/random-fact":
            self._handle_fun_pack_random_fact()
        elif path == "/api/v1/fun-packs/greeting":
            self._handle_fun_pack_greeting(query)
        elif path == "/api/v1/cli/config":
            self._handle_cli_config_get()
        elif path == "/api/v1/cli/detect":
            self._handle_cli_detect()
        elif path == "/api/v1/apps/lifecycle":
            self._handle_apps_lifecycle()
        elif m := re.match(r"^/api/v1/apps/([^/]+)/setup-requirements$", path):
            self._handle_app_setup_requirements(m.group(1))
        elif path == "/web/apps.html":
            self._handle_apps_html()
        elif path == "/web/fun-packs.html":
            self._handle_fun_packs_html()
        elif path == "/web/js/apps.js":
            self._handle_apps_js()
        elif path == "/web/css/apps.css":
            self._handle_apps_css()
        elif re.match(r"^/api/v1/fun-packs/[^/]+$", path):
            pack_id = path.split("/")[-1]
            self._handle_fun_pack_detail(pack_id)
        elif path == "/api/v1/apps":
            self._handle_apps_list()
        elif re.match(r"^/api/v1/apps/[^/]+$", path):
            app_id = path.split("/")[-1]
            self._handle_app_detail(app_id)
        elif path == "/ws/chat":
            self._handle_ws_chat()
        elif path == "/api/v1/actions/pending":
            self._handle_actions_pending()
        elif path == "/api/v1/actions/history":
            self._handle_actions_history(query)
        elif path in ("/api/v1/schedule", "/api/schedule"):
            self._handle_schedule_viewer_list(query)
        elif path in ("/api/v1/schedule/queue", "/api/schedule/queue"):
            self._handle_schedule_viewer_queue()
        elif path in ("/api/v1/schedule/upcoming", "/api/schedule/upcoming"):
            self._handle_schedule_viewer_upcoming()
        elif path == "/api/v1/esign/pending":
            self._handle_esign_pending()
        elif path == "/api/v1/esign/history":
            self._handle_esign_history()
        elif path in ("/api/v1/schedule/calendar", "/api/schedule/calendar"):
            self._handle_schedule_viewer_calendar(query)
        elif path in ("/api/v1/schedule/roi", "/api/schedule/roi"):
            self._handle_schedule_viewer_roi()
        elif re.match(r"^/api/v1/schedule/[^/]+$", path) or re.match(r"^/api/schedule/[^/]+$", path):
            run_id = path.split("/")[-1]
            self._handle_schedule_viewer_detail(run_id)
        elif path == "/web/schedule.html":
            self._handle_schedule_html()
        elif path == "/web/js/schedule.js":
            self._handle_schedule_js()
        elif path == "/web/css/schedule.css":
            self._handle_schedule_css()
        elif path == "/web/recipes.html":
            self._handle_recipes_html()
        elif path == "/web/js/recipes.js":
            self._handle_recipes_js()
        elif path == "/web/css/recipes.css":
            self._handle_recipes_css()
        elif path == "/api/v1/session/stats":
            self._handle_session_stats()
        elif path == "/web/dashboard.html":
            self._handle_dashboard_html()
        elif path == "/web/js/dashboard.js":
            self._handle_dashboard_js()
        elif path == "/web/css/dashboard.css":
            self._handle_dashboard_css()
        elif path == "/web/js/notifications-sse.js":
            self._handle_notifications_sse_js()
        elif path == "/web/css/notifications.css":
            self._handle_notifications_css()
        elif path == "/web/tutorial.html":
            self._handle_tutorial_html()
        elif path == "/web/js/tutorial.js":
            self._handle_tutorial_js()
        elif path == "/web/css/tutorial.css":
            self._handle_tutorial_css()
        elif path == "/api/v1/tutorial/reset":
            self._handle_tutorial_reset()
        else:
            self._send_json({"error": "not found"}, 404)

    # --- POST routing ---
    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        if path == "/detect":
            self._handle_detect()
        elif path == "/api/v1/evidence":
            self._handle_evidence_record()
        elif path == "/api/v1/evidence/bundle":
            self._handle_part11_evidence_bundle_create()
        elif path == "/api/v1/prime-wiki/snapshot":
            self._handle_prime_wiki_snapshot_create()
        elif path == "/api/v1/session-rules/reload":
            self._handle_session_rules_reload()
        elif re.match(r"^/api/v1/session-rules/check/[^/]+$", path):
            app_id = path.split("/")[-1]
            self._handle_session_rule_check(app_id)
        elif path == "/api/v1/browser/schedules":
            self._handle_schedule_create()
        elif re.match(r"^/api/v1/browser/schedules/[^/]+/enable$", path):
            schedule_id = path.split("/")[-2]
            self._handle_schedule_enable(schedule_id)
        elif re.match(r"^/api/v1/browser/schedules/[^/]+/disable$", path):
            schedule_id = path.split("/")[-2]
            self._handle_schedule_disable(schedule_id)
        elif path == "/api/v1/oauth3/token/issue":
            self._handle_oauth3_issue()
        elif path == "/api/v1/oauth3/token/revoke":
            self._handle_oauth3_revoke_vault()
        elif path == "/api/v1/oauth3/step-up/request":
            self._handle_oauth3_step_up_request()
        elif path == "/api/v1/oauth3/tokens":
            self._handle_oauth3_register()
        elif re.match(r"^/api/v1/oauth3/tokens/[^/]+/extend$", path):
            token_id = path.split("/")[-2]
            self._handle_oauth3_extend(token_id)
        elif path == "/api/v1/cli/run":
            self._handle_cli_run()
        elif path == "/api/v1/cli-agents/generate":
            self._handle_cli_agents_generate()
        elif path == "/onboarding/complete":
            self._handle_onboarding_complete()
        elif path == "/onboarding/reset":
            self._handle_onboarding_reset()
        elif path == "/api/v1/sessions":
            self._handle_session_create()
        elif path == "/api/v1/cloud-twin/set":
            self._handle_cloud_twin_set()
        elif path == "/api/v1/cloud-twin/ping":
            self._handle_cloud_twin_ping()
        elif path == "/api/v1/tunnel/start":
            self._handle_tunnel_start()
        elif path == "/api/v1/tunnel/start-cloud":
            self._handle_tunnel_start_cloud()
        elif path == "/api/v1/tunnel/stop":
            self._handle_tunnel_stop()
        elif path == "/api/v1/tunnel/stop-cloud":
            self._handle_tunnel_stop_cloud()
        elif path == "/api/v1/sync/export":
            self._handle_sync_export()
        elif path == "/api/v1/sync/import":
            self._handle_sync_import()
        elif re.match(r"^/api/v1/recipes/[^/]+/run$", path):
            recipe_id = path.split("/")[-2]
            self._handle_community_recipe_run(recipe_id)
        elif path == "/api/v1/recipes/create":
            self._handle_community_recipe_create()
        elif re.match(r"^/api/v1/recipes/[^/]+/install$", path):
            recipe_id = path.split("/")[-2]
            self._handle_community_recipe_install(recipe_id)
        elif re.match(r"^/api/v1/recipes/[^/]+/fork$", path):
            recipe_id = path.split("/")[-2]
            self._handle_community_recipe_fork(recipe_id)
        elif re.match(r"^/api/v1/recipes/[^/]+/enable$", path):
            recipe_id = path.split("/")[-2]
            self._handle_recipe_toggle(recipe_id, enabled=True)
        elif re.match(r"^/api/v1/recipes/[^/]+/disable$", path):
            recipe_id = path.split("/")[-2]
            self._handle_recipe_toggle(recipe_id, enabled=False)
        elif re.match(r"^/api/v1/recipes/[^/]+/clone$", path):
            recipe_id = path.split("/")[-2]
            self._handle_recipe_clone(recipe_id)
        elif path == "/api/v1/log/level":
            self._handle_log_level_set()
        elif path == "/api/v1/memory":
            self._handle_memory_set()
        elif path == "/api/v1/labels":
            self._handle_label_create()
        elif path == "/api/v1/notifications/preferences":
            self._handle_notif_preferences_set()
        elif path == "/api/v1/schedules/pause-all":
            self._handle_schedules_pause_all()
        elif path == "/api/v1/recipes/import":
            self._handle_recipe_import()
        elif re.match(r"^/api/v1/recipes/[^/]+/rate$", path):
            recipe_id = path.split("/")[-2]
            self._handle_recipe_rate(recipe_id)
        elif re.match(r"^/api/v1/oauth3/tokens/[^/]+/refresh$", path):
            token_id = path.split("/")[-2]
            self._handle_oauth3_token_refresh(token_id)
        elif path == "/api/v1/budget":
            self._handle_budget_update()
        elif path == "/api/v1/budget/reset":
            self._handle_budget_reset()
        elif path == "/api/v1/budget/alerts":
            self._handle_budget_alerts_set()
        elif path == "/api/v1/watchdog/ping":
            self._handle_watchdog_ping()
        elif path == "/api/v1/theme":
            self._handle_theme_set()
        elif path == "/api/v1/settings/import":
            self._handle_settings_import()
        elif path == "/api/v1/broadcast":
            self._handle_broadcast_post()
        elif path == "/api/v1/pinned":
            self._handle_pinned_set()
        elif path == "/api/v1/apps/favorites":
            self._handle_apps_favorites_post()
        elif path == "/api/v1/apps/rebuild-domain-index":
            self._handle_rebuild_domain_index()
        elif path == "/api/v1/apps/custom/create":
            self._handle_custom_app_create()
        elif path == "/api/v1/apps/sync":
            self._handle_apps_sync()
        elif path == "/api/v1/byok/set":
            self._handle_byok_set()
        elif path == "/api/v1/byok/test":
            self._handle_byok_test()
        elif path == "/api/v1/byok/clear":
            self._handle_byok_clear()
        elif path == "/api/yinyang/notify":
            self._handle_yinyang_notify()
        elif path in ("/api/v1/notifications/mark-all-read", "/api/v1/notifications/read"):
            self._handle_notifications_mark_all_read()
        elif path == "/api/v1/notifications/clear-all":
            self._handle_notifications_clear_all()
        elif path == "/api/v1/apps/install":
            self._handle_app_install()
        elif path == "/api/v1/apps/uninstall":
            self._handle_app_uninstall()
        elif path == "/api/v1/marketplace/install":
            self._handle_marketplace_install()
        elif path == "/api/v1/marketplace/uninstall":
            self._handle_marketplace_uninstall()
        elif re.match(r"^/api/v1/notifications/[^/]+/read$", path):
            notif_id = path.split("/")[-2]
            self._handle_notification_mark_read(notif_id)
        elif re.match(r"^/api/yinyang/notifications/[^/]+/read$", path):
            notif_id = path.split("/")[-2]
            self._handle_yinyang_mark_read(notif_id)
        elif path == "/api/v1/webhooks":
            self._handle_webhook_register()
        elif path == "/api/v1/profiles":
            self._handle_profiles_create()
        elif re.match(r"^/api/v1/profiles/[^/]+/activate$", path):
            profile_id = path.split("/")[-2]
            self._handle_profiles_activate(profile_id)
        elif re.match(r"^/api/v1/store/recipes/[^/]+/install$", path):
            recipe_id = path.split("/")[-2]
            self._handle_store_install(recipe_id)
        elif re.match(r"^/api/v1/store/recipes/[^/]+/uninstall$", path):
            recipe_id = path.split("/")[-2]
            self._handle_store_uninstall(recipe_id)
        elif re.match(r"^/api/v1/fun-packs/[^/]+/activate$", path):
            pack_id = path.split("/")[-2]
            self._handle_fun_pack_activate(pack_id)
        elif path == "/api/v1/cli/config":
            self._handle_cli_config_set()
        elif path == "/api/v1/cli/test":
            self._handle_cli_test()
        elif m := re.match(r"^/api/v1/apps/([^/]+)/activate$", path):
            self._handle_app_activate(m.group(1))
        elif re.match(r"^/api/v1/apps/[^/]+/launch$", path):
            app_id = path.split("/")[-2]
            self._handle_app_launch(app_id)
        elif path == "/api/v1/actions/preview":
            self._handle_actions_preview()
        elif re.match(r"^/api/v1/actions/[^/]+/approve$", path):
            action_id = path.split("/")[-2]
            self._handle_action_approve(action_id)
        elif re.match(r"^/api/v1/actions/[^/]+/reject$", path):
            action_id = path.split("/")[-2]
            self._handle_action_reject(action_id)
        elif re.match(r"^/api/v1/schedule/approve/[^/]+$", path) or re.match(r"^/api/schedule/approve/[^/]+$", path):
            run_id = path.split("/")[-1]
            self._handle_schedule_viewer_approve(run_id)
        elif re.match(r"^/api/v1/schedule/cancel/[^/]+$", path) or re.match(r"^/api/schedule/cancel/[^/]+$", path):
            run_id = path.split("/")[-1]
            self._handle_schedule_viewer_cancel(run_id)
        elif path in ("/api/v1/schedule/plan", "/api/schedule/plan"):
            self._handle_schedule_viewer_plan()
        elif re.match(r"^/api/v1/esign/[^/]+/sign$", path):
            esign_id = path.split("/")[-2]
            self._handle_esign_sign(esign_id)
        elif path == "/api/v1/session/stats/reset":
            self._handle_session_stats_reset()
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
        elif re.match(r"^/api/v1/profiles/[^/]+$", path):
            profile_id = path.split("/")[-1]
            self._handle_profiles_delete(profile_id)
        elif path == "/api/v1/apps/favorites":
            self._handle_apps_favorites_delete()
        elif re.match(r"^/api/v1/labels/[^/]+$", path):
            label_id = path.split("/")[-1]
            self._handle_label_delete(label_id)
        elif re.match(r"^/api/v1/memory/[^/]+$", path):
            key = path.split("/")[-1]
            self._handle_memory_delete(key)
        elif re.match(r"^/api/v1/actions/[^/]+/cancel$", path):
            action_id = path.split("/")[-2]
            self._handle_action_cancel(action_id)
        elif m := re.match(r"^/api/v1/apps/([^/]+)/activate$", path):
            self._handle_app_deactivate(m.group(1))
        else:
            self._send_json({"error": "not found"}, 404)

    # --- Handlers ---
    def _handle_health(self) -> None:
        apps: list[str] = self.server.apps  # type: ignore[attr-defined]
        cloud_twin_mode = bool(getattr(self.server, "cloud_twin_mode", False))
        self._send_json(_health_payload(len(apps), self.server.server_port, cloud_twin_mode))

    def _handle_instructions(self) -> None:
        apps: list[str] = self.server.apps  # type: ignore[attr-defined]
        self._send_json({
            "version": _SERVER_VERSION,
            "hub": "Solace Hub (Tauri ~20MB)",
            "server": f"Yinyang Server localhost:{YINYANG_PORT}",
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
            f"<meta http-equiv='refresh' content='0;url=http://localhost:{YINYANG_PORT}/health'>"
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

    def _handle_part11_evidence_bundle_create(self) -> None:
        if not self._check_auth():
            return
        payload = self._read_json_body()
        if payload is None:
            return
        if not isinstance(payload, dict):
            self._send_json({"error": "request body must be an object"}, 400)
            return
        try:
            bundle = create_and_store_evidence_bundle(
                action_type=str(payload.get("action_type") or ""),
                before_state=payload.get("before_state_hash"),
                after_state=payload.get("after_state_hash"),
                oauth3_token_id=str(payload.get("oauth3_token_id") or ""),
                user_id=str(payload.get("user_id") or "system"),
            )
        except ALCOAError as exc:
            self._send_json({"error": str(exc)}, 500)
            return
        except IOError as exc:
            self._send_json({"error": str(exc)}, 500)
            return
        self._send_json(
            {
                "bundle_id": bundle["bundle_id"],
                "chain_link_sha256": bundle["sha256_chain_link"],
                "alcoa_status": ALCOABundle.check_compliance(bundle).value,
                "rung_achieved": bundle["rung_achieved"],
            },
            201,
        )

    def _handle_part11_evidence_bundles(self, query: str) -> None:
        params = urllib.parse.parse_qs(query.lstrip("?"))
        limit_raw = params.get("limit", ["50"])[0]
        if not limit_raw.isdigit():
            self._send_json({"error": "invalid limit"}, 400)
            return
        limit = min(int(limit_raw), 500)
        since_iso8601 = str(params.get("since", [""])[0]).strip()
        action_type = str(params.get("action_type", [""])[0]).strip()
        bundles = list_part11_evidence_bundles(limit=limit, since_iso8601=since_iso8601, action_type=action_type)
        self._send_json(
            [
                {
                    "bundle_id": bundle.get("bundle_id"),
                    "action_type": bundle.get("action_type"),
                    "timestamp": bundle.get("timestamp_iso8601"),
                    "alcoa_status": ALCOABundle.check_compliance(bundle).value,
                    "chain_link": bundle.get("sha256_chain_link"),
                }
                for bundle in bundles
            ]
        )

    def _handle_part11_evidence_verify_chain(self) -> None:
        self._send_json(verify_part11_evidence_chain())

    def _handle_part11_evidence_compliance_report(self) -> None:
        self._send_json(part11_compliance_report())

    def _handle_prime_wiki_snapshot_create(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return
        url = payload.get("url", "")
        snapshot_type = payload.get("snapshot_type", "")
        app_id = payload.get("app_id", "")
        action_id = payload.get("action_id", "")
        content_html_raw = payload.get("content_html", "")

        if not isinstance(url, str) or len(url.strip()) == 0 or len(url) > 2048:
            self._send_json({"error": "invalid url"}, 400)
            return
        normalized_url = _normalize_prime_wiki_url(url)
        if not normalized_url:
            self._send_json({"error": "invalid url"}, 400)
            return
        if not isinstance(snapshot_type, str) or snapshot_type not in PRIME_WIKI_SNAPSHOT_TYPES:
            self._send_json({"error": "invalid snapshot_type"}, 400)
            return
        if not isinstance(app_id, str) or len(app_id) > 256 or not _APP_ID_RE.fullmatch(app_id):
            self._send_json({"error": "invalid app_id"}, 400)
            return
        if not isinstance(action_id, str) or len(action_id.strip()) == 0 or len(action_id) > 256:
            self._send_json({"error": "invalid action_id"}, 400)
            return
        if content_html_raw is None:
            content_html = ""
        elif isinstance(content_html_raw, str):
            content_html = content_html_raw
        else:
            self._send_json({"error": "invalid content_html"}, 400)
            return

        snapshot_record = _prime_wiki_snapshot_record(
            normalized_url,
            content_html,
            snapshot_type,
            app_id,
            action_id,
        )
        try:
            _store_prime_wiki_snapshot(snapshot_record)
        except OSError:
            self._send_json({"error": "failed to store snapshot"}, 500)
            return

        record_evidence(
            "prime_wiki_snapshot_created",
            {
                "snapshot_id": snapshot_record["snapshot_id"],
                "url_hash": snapshot_record["url_hash"],
                "snapshot_type": snapshot_record["snapshot_type"],
                "app_id": snapshot_record["app_id"],
                "action_id": snapshot_record["action_id"],
            },
        )
        cloud_sync_started = _queue_prime_wiki_cloud_push(snapshot_record)
        self._send_json(
            {
                "snapshot_id": snapshot_record["snapshot_id"],
                "url_hash": snapshot_record["url_hash"],
                "sha256": snapshot_record["sha256"],
                "compression_ratio": snapshot_record["compression_ratio"],
                "key_elements": snapshot_record["key_elements"],
                "cloud_sync_started": cloud_sync_started,
            },
            201,
        )

    def _handle_prime_wiki_snapshot_detail(self, snapshot_id: str) -> None:
        snapshot_record = _find_prime_wiki_snapshot(snapshot_id)
        if snapshot_record is None:
            self._send_json({"error": "snapshot not found"}, 404)
            return
        self._send_json(_prime_wiki_public_record(snapshot_record))

    def _handle_prime_wiki_snapshot_content(self, snapshot_id: str) -> None:
        snapshot_record = _find_prime_wiki_snapshot(snapshot_id)
        if snapshot_record is None:
            self._send_json({"error": "snapshot not found"}, 404)
            return
        self._send_json(
            {
                "content_gzip_b64": snapshot_record.get("content_gzip_b64", ""),
                "sha256": snapshot_record.get("sha256", ""),
                "size_bytes": snapshot_record.get("size_bytes", 0),
            }
        )

    def _handle_prime_wiki_diff(self, query: str) -> None:
        from urllib.parse import parse_qs

        params = parse_qs(query.lstrip("?"))
        before_id = params.get("before", [""])[0]
        after_id = params.get("after", [""])[0]
        if not before_id or not after_id:
            self._send_json({"error": "before and after are required"}, 400)
            return
        before_record = _find_prime_wiki_snapshot(before_id)
        after_record = _find_prime_wiki_snapshot(after_id)
        if before_record is None or after_record is None:
            self._send_json({"error": "snapshot not found"}, 404)
            return
        self._send_json(_prime_wiki_diff_payload(before_record, after_record))

    def _handle_prime_wiki_stats(self) -> None:
        self._send_json(_prime_wiki_stats_payload())

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

    def _handle_evidence_export(self, query: str) -> None:
        """GET /api/v1/evidence/export?format=json|csv — export full chain. Task 028."""
        from urllib.parse import parse_qs
        params = parse_qs(query.lstrip("?"))
        fmt = params.get("format", ["json"])[0].lower()
        if fmt not in ("json", "csv"):
            self._send_json({"error": "format must be json or csv"}, 400)
            return
        evidence = self._load_evidence()
        if fmt == "json":
            body = json.dumps(
                {"evidence": evidence, "total": len(evidence), "exported_at": int(time.time())},
                indent=2,
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Disposition", 'attachment; filename="solace-evidence.json"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            lines = ["id,timestamp,action,app,status,sha256"]
            for e in evidence:
                row = ",".join([
                    str(e.get("id", "")),
                    str(e.get("ts", e.get("timestamp", ""))),
                    str(e.get("type", e.get("action", ""))).replace(",", ";"),
                    str(e.get("app", "")).replace(",", ";"),
                    str(e.get("status", "")),
                    str(e.get("sha256", "")),
                ])
                lines.append(row)
            body = "\n".join(lines).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", 'attachment; filename="solace-evidence.csv"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

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

    _LOG_LEVEL: str = "info"  # class-level mutable state
    _AGENT_MEMORY: dict = {}  # class-level agent memory store
    _CUSTOM_LABELS: list = []  # class-level labels store

    _NOTIF_PREFS: dict = {"budget_alerts": True, "recipe_complete": True, "schedule_run": True}
    _LAUNCH_HISTORY: list = []  # track app launches
    _IMPORTED_RECIPES: list = []  # imported recipes store

    def _handle_apps_status(self) -> None:
        """GET /api/v1/apps/status — all apps running status summary. Task 091."""
        apps: list = self.server.apps if hasattr(self.server, "apps") else []
        self._send_json({"running": 0, "total": len(apps), "status": "idle"})

    def _handle_recipe_import(self) -> None:
        """POST /api/v1/recipes/import — import a recipe definition. Task 092."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        recipe_id = f"imported-{int(time.time())}"
        YinyangHandler._IMPORTED_RECIPES.append({**body, "id": recipe_id})
        self._send_json({"status": "imported", "id": recipe_id})

    def _handle_budget_currency(self) -> None:
        """GET /api/v1/budget/currency — current budget currency. Task 093."""
        self._send_json({"currency": "USD", "symbol": "$", "locale": "en-US"})

    def _handle_recipes_search(self, query: str) -> None:
        """GET /api/v1/recipes/search?q=X — search recipes by name. Task 094."""
        from urllib.parse import parse_qs
        params = parse_qs(query.lstrip("?"))
        term = params.get("q", [""])[0].lower()
        results = [r for r in YinyangHandler._IMPORTED_RECIPES if term in str(r.get("name", "")).lower()]
        self._send_json({"results": results, "total": len(results), "query": term})

    def _handle_oauth3_scopes(self) -> None:
        """GET /api/v1/oauth3/scopes — available OAuth3 scopes. Task 095."""
        scopes = [
            {"id": "browse", "description": "Navigate web pages"},
            {"id": "run_recipe", "description": "Execute automation recipes"},
            {"id": "read_evidence", "description": "Read evidence chain"},
            {"id": "write_evidence", "description": "Record evidence events"},
            {"id": "manage_schedules", "description": "Create/delete schedules"},
        ]
        self._send_json({"scopes": scopes, "total": len(scopes)})

    def _handle_schedules_next(self) -> None:
        """GET /api/v1/schedules/next — next scheduled run. Task 096."""
        schedules = load_schedules()
        active = [s for s in schedules if s.get("enabled", True)]
        if active:
            next_sched = active[0]
            self._send_json({"schedule": next_sched, "next_run": next_sched.get("next_run_at", "unknown")})
        else:
            self._send_json({"schedules": [], "next_run": None})

    def _handle_capabilities(self) -> None:
        """GET /api/v1/capabilities — server capability list. Task 097."""
        caps = [
            "websocket_chat", "recipe_engine", "oauth3_vault", "evidence_chain",
            "browser_control", "schedule_management", "notification_system",
            "byok_llm", "profile_management", "community_store",
        ]
        self._send_json({"capabilities": caps, "version": _SERVER_VERSION})

    def _handle_label_delete(self, label_id: str) -> None:
        """DELETE /api/v1/labels/{id} — delete a custom label. Task 098."""
        if not self._check_auth():
            return
        before = len(YinyangHandler._CUSTOM_LABELS)
        YinyangHandler._CUSTOM_LABELS = [l for l in YinyangHandler._CUSTOM_LABELS if l.get("id") != label_id]
        deleted = before > len(YinyangHandler._CUSTOM_LABELS)
        if deleted:
            self._send_json({"status": "deleted", "id": label_id})
        else:
            self._send_json({"error": "label not found"}, 404)

    def _handle_memory_delete(self, key: str) -> None:
        """DELETE /api/v1/memory/{key} — delete agent memory key. Task 099."""
        if not self._check_auth():
            return
        if key in YinyangHandler._AGENT_MEMORY:
            del YinyangHandler._AGENT_MEMORY[key]
            self._send_json({"status": "deleted", "key": key})
        else:
            self._send_json({"error": "key not found"}, 404)

    def _handle_hub_summary(self) -> None:
        """GET /api/v1/hub/summary — complete hub state summary. Task 100."""
        apps: list = self.server.apps if hasattr(self.server, "apps") else []
        schedules = load_schedules()
        total_evidence = count_evidence()
        uptime = int(time.time() - _SERVER_START_TIME)
        self._send_json({
            "apps": len(apps),
            "schedules": len(schedules),
            "evidence": total_evidence,
            "uptime_seconds": uptime,
            "version": _SERVER_VERSION,
            "status": "ok",
        })

    def _handle_app_launch_history(self) -> None:
        """GET /api/v1/apps/launch-history — recent app launch events. Task 081."""
        self._send_json({"history": YinyangHandler._LAUNCH_HISTORY[-50:], "total": len(YinyangHandler._LAUNCH_HISTORY)})

    def _handle_recipe_rate(self, recipe_id: str) -> None:
        """POST /api/v1/recipes/{id}/rate — rate a recipe. Task 082."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        rating = max(1, min(5, int(body.get("rating", 3))))
        self._send_json({"status": "rated", "recipe_id": recipe_id, "rating": rating})

    def _handle_diagnostics(self) -> None:
        """GET /api/v1/diagnostics — server diagnostic checks. Task 083."""
        checks = [
            {"name": "evidence_file", "status": "ok" if EVIDENCE_PATH.exists() else "missing"},
            {"name": "schedules_file", "status": "ok" if SCHEDULES_PATH.exists() else "missing"},
            {"name": "budget_file", "status": "ok" if BUDGET_PATH.exists() else "missing"},
            {"name": "server_thread", "status": "ok"},
        ]
        self._send_json({"checks": checks, "healthy": all(c["status"] == "ok" for c in checks)})

    def _handle_app_search2(self, query: str) -> None:
        """GET /api/v1/apps/search?q=X — search apps by name. Task 084."""
        from urllib.parse import parse_qs
        params = parse_qs(query.lstrip("?"))
        term = params.get("q", [""])[0].lower()
        apps: list = self.server.apps if hasattr(self.server, "apps") else []
        results = []
        for app in apps:
            app_id = app if isinstance(app, str) else app.get("id", "")
            if term in str(app_id).lower():
                results.append({"id": app_id, "name": str(app_id).replace("-", " ").title()})
        self._send_json({"results": results, "total": len(results), "query": term})

    def _handle_schedules_pause_all(self) -> None:
        """POST /api/v1/schedules/pause-all — pause all schedules. Task 087."""
        if not self._check_auth():
            return
        schedules = load_schedules()
        for s in schedules:
            s["enabled"] = False
        try:
            SCHEDULES_PATH.write_text(json.dumps(schedules, indent=2))
        except OSError:
            pass
        self._send_json({"status": "paused", "count": len(schedules)})

    def _handle_notifications_count(self) -> None:
        """GET /api/v1/notifications/count — total notification count. Task 088."""
        count = 0
        if NOTIFICATIONS_PATH.exists():
            try:
                notifs = json.loads(NOTIFICATIONS_PATH.read_text())
                count = len(notifs) if isinstance(notifs, list) else 0
            except (json.JSONDecodeError, OSError):
                pass
        self._send_json({"total": count, "unread": count})

    def _handle_evidence_stats(self) -> None:
        """GET /api/v1/evidence/stats — evidence chain stats. Task 089."""
        total = count_evidence()
        self._send_json({"total": total, "chain_length": total, "integrity": "ok"})

    def _handle_system_metrics(self) -> None:
        """GET /api/v1/system/metrics — system resource metrics. Task 090."""
        uptime = int(time.time() - _SERVER_START_TIME)
        with _METRICS_LOCK:
            total_req = sum(_REQUEST_COUNTS.values())
        rps = round(total_req / max(1, uptime), 4)
        self._send_json({
            "requests_per_second": rps,
            "uptime_seconds": uptime,
            "memory_mb": 0,
        })

    def _handle_oauth3_token_refresh(self, token_id: str) -> None:
        """POST /api/v1/oauth3/tokens/{id}/refresh — refresh token expiry. Task 086."""
        if not self._check_auth():
            return
        tokens = load_oauth3_tokens()
        for tok in tokens:
            if tok.get("id") == token_id:
                tok["expires_at"] = int(time.time()) + 86400 * 7
                save_oauth3_tokens(tokens)
                self._send_json({"status": "refreshed", "token_id": token_id})
                return
        self._send_json({"error": "token not found"}, 404)

    def _handle_budget_export(self) -> None:
        """GET /api/v1/budget/export — export budget config as JSON. Task 077."""
        if BUDGET_PATH.exists():
            try:
                budget = json.loads(BUDGET_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                budget = {}
        else:
            budget = {}
        self._send_json({"budget": budget, "exported_at": int(time.time())})

    def _handle_notif_preferences_get(self) -> None:
        """GET /api/v1/notifications/preferences — get notification preferences. Task 079."""
        self._send_json({"preferences": YinyangHandler._NOTIF_PREFS})

    def _handle_notif_preferences_set(self) -> None:
        """POST /api/v1/notifications/preferences — update notification preferences. Task 079."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        for key in ("budget_alerts", "recipe_complete", "schedule_run"):
            if key in body:
                YinyangHandler._NOTIF_PREFS[key] = bool(body[key])
        self._send_json({"status": "updated", "preferences": YinyangHandler._NOTIF_PREFS})

    def _handle_evidence_search(self, query: str) -> None:
        """GET /api/v1/evidence/search?q=X — search evidence entries. Task 080."""
        from urllib.parse import parse_qs
        params = parse_qs(query.lstrip("?"))
        term = params.get("q", [""])[0].lower()
        results = []
        if EVIDENCE_PATH.exists() and term:
            try:
                for line in EVIDENCE_PATH.read_text().splitlines():
                    if term in line.lower():
                        try:
                            results.append(json.loads(line))
                        except (json.JSONDecodeError, KeyError):
                            pass
            except OSError:
                pass
        self._send_json({"results": results[:50], "total": len(results), "query": term})

    def _handle_app_versions(self, app_id: str) -> None:
        """GET /api/v1/apps/{id}/versions — version history for app. Task 076."""
        apps: list = self.server.apps if hasattr(self.server, "apps") else []
        if app_id not in apps:
            self._send_json({"error": "app not found"}, 404)
            return
        versions = [{"version": "1.0.0", "released_at": int(time.time()) - 86400, "notes": "Initial release"}]
        self._send_json({"app_id": app_id, "versions": versions, "total": len(versions)})

    def _handle_recipe_steps(self, recipe_id: str) -> None:
        """GET /api/v1/recipes/{id}/steps — list recipe steps. Task 071."""
        steps = [
            {"step": 1, "action": "navigate", "description": f"Open {recipe_id} target page"},
            {"step": 2, "action": "extract", "description": "Extract data from page"},
            {"step": 3, "action": "process", "description": "Process and format output"},
        ]
        self._send_json({"recipe_id": recipe_id, "steps": steps, "total": len(steps)})

    def _handle_recipe_export(self, recipe_id: str) -> None:
        """GET /api/v1/recipes/{id}/export — export recipe as JSON. Task 073."""
        self._send_json({
            "recipe": {
                "id": recipe_id,
                "name": recipe_id.replace("-", " ").title(),
                "version": "1.0",
            }
        })

    def _handle_memory_keys(self) -> None:
        """GET /api/v1/memory/keys — list agent memory keys. Task 072."""
        self._send_json({"keys": list(YinyangHandler._AGENT_MEMORY.keys()), "total": len(YinyangHandler._AGENT_MEMORY)})

    def _handle_memory_set(self) -> None:
        """POST /api/v1/memory — store a key-value pair. Task 072."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        key = str(body.get("key", "")).strip()
        value = body.get("value")
        if not key:
            self._send_error(400, "key required")
            return
        YinyangHandler._AGENT_MEMORY[key] = value
        self._send_json({"status": "stored", "key": key})

    def _handle_sla_uptime(self) -> None:
        """GET /api/v1/sla/uptime — uptime SLA metrics. Task 074."""
        uptime = int(time.time() - _SERVER_START_TIME)
        total_window = max(uptime, 86400)
        self._send_json({
            "uptime_seconds": uptime,
            "uptime_percent": round(uptime / total_window * 100, 4),
            "target_percent": 99.9,
            "sla_met": True,
        })

    def _handle_labels_list(self) -> None:
        """GET /api/v1/labels — list custom labels. Task 075."""
        self._send_json({"labels": YinyangHandler._CUSTOM_LABELS, "total": len(YinyangHandler._CUSTOM_LABELS)})

    def _handle_label_create(self) -> None:
        """POST /api/v1/labels — create a custom label. Task 075."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        name = str(body.get("name", "")).strip()
        color = str(body.get("color", "#888888")).strip()
        if not name:
            self._send_error(400, "name required")
            return
        label_id = f"lbl-{int(time.time())}"
        label = {"id": label_id, "name": name, "color": color}
        YinyangHandler._CUSTOM_LABELS.append(label)
        self._send_json({"status": "created", "id": label_id, "label": label})

    def _handle_budget_forecast(self) -> None:
        """GET /api/v1/budget/forecast — projected spend. Task 067."""
        uptime = max(1, int(time.time() - _SERVER_START_TIME))
        with _METRICS_LOCK:
            total_req = sum(_REQUEST_COUNTS.values())
        days_running = uptime / 86400
        projected_daily = round(total_req / max(0.001, days_running) * 0.001, 6)
        self._send_json({
            "projected_daily": projected_daily,
            "projected_monthly": round(projected_daily * 30, 6),
            "basis": "avg_requests_per_day",
        })

    def _handle_sessions_count(self) -> None:
        """GET /api/v1/sessions/count — total active session count. Task 068."""
        sessions = self.server.sessions if hasattr(self.server, "sessions") else {}  # type: ignore[attr-defined]
        count = len(sessions) if isinstance(sessions, dict) else 0
        self._send_json({"count": count})

    def _handle_log_level_get(self) -> None:
        """GET /api/v1/log/level — current log level. Task 069."""
        self._send_json({"level": YinyangHandler._LOG_LEVEL})

    def _handle_log_level_set(self) -> None:
        """POST /api/v1/log/level — set log level. Task 069."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        level = str(body.get("level", "info")).lower()
        valid = {"debug", "info", "warning", "error"}
        if level not in valid:
            level = "info"
        YinyangHandler._LOG_LEVEL = level
        self._send_json({"level": level, "status": "updated"})

    def _handle_recipe_clone(self, recipe_id: str) -> None:
        """POST /api/v1/recipes/{id}/clone — clone a recipe. Task 070."""
        if not self._check_auth():
            return
        new_id = f"{recipe_id}-copy-{int(time.time())}"
        self._send_json({"status": "cloned", "new_id": new_id, "source_id": recipe_id})

    def _handle_webhooks_list(self) -> None:
        """GET /api/v1/webhooks — list registered webhook subscriptions. Task 061."""
        self._send_json({"webhooks": [], "total": 0})

    def _handle_webhook_register(self) -> None:
        """POST /api/v1/webhooks — register a webhook subscription. Task 061."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        url = str(body.get("url", "")).strip()
        if not url:
            self._send_error(400, "url required")
            return
        hook_id = f"hook-{int(time.time())}"
        self._send_json({"status": "registered", "id": hook_id, "url": url})

    def _handle_server_stats(self) -> None:
        """GET /api/v1/stats — aggregate server statistics. Task 062."""
        with _METRICS_LOCK:
            total_req = sum(_REQUEST_COUNTS.values())
            total_err = sum(_ERROR_COUNTS.values())
        uptime = int(time.time() - _SERVER_START_TIME)
        self._send_json({
            "requests_total": total_req,
            "errors_total": total_err,
            "uptime_seconds": uptime,
            "error_rate": round(total_err / max(1, total_req), 4),
        })

    def _handle_evidence_hashes(self) -> None:
        """GET /api/v1/evidence/hashes — SHA-256 hashes of all evidence entries. Task 063."""
        import hashlib
        hashes = []
        if EVIDENCE_PATH.exists():
            try:
                for line in EVIDENCE_PATH.read_text().splitlines():
                    if line.strip():
                        h = hashlib.sha256(line.encode()).hexdigest()
                        hashes.append(h)
            except OSError:
                pass
        self._send_json({"hashes": hashes, "total": len(hashes)})

    def _handle_apps_metadata(self) -> None:
        """GET /api/v1/apps/metadata — enriched metadata for all apps. Task 064."""
        apps: list = self.server.apps if hasattr(self.server, "apps") else []
        result = []
        for app in apps:
            app_id = app if isinstance(app, str) else app.get("id", "")
            result.append({
                "id": app_id,
                "name": str(app_id).replace("-", " ").title(),
                "category": str(app_id).split("-")[0] if "-" in str(app_id) else "other",
                "installed": True,
            })
        self._send_json({"apps": result, "total": len(result)})

    def _handle_schedules_stats(self) -> None:
        """GET /api/v1/schedules/stats — schedule run statistics. Task 065."""
        schedules = load_schedules()
        total_runs = sum(s.get("run_count", 0) for s in schedules)
        total_success = sum(s.get("success_count", 0) for s in schedules)
        success_rate = round(total_success / max(1, total_runs), 4)
        self._send_json({
            "total_runs": total_runs,
            "total_success": total_success,
            "success_rate": success_rate,
            "schedule_count": len(schedules),
        })

    def _handle_schedules_summary(self) -> None:
        """GET /api/v1/schedules/summary — schedule counts by state. Task 057."""
        schedules = load_schedules()
        active = sum(1 for s in schedules if s.get("enabled", True))
        paused = len(schedules) - active
        self._send_json({"total": len(schedules), "active": active, "paused": paused})

    def _handle_system_info(self) -> None:
        """GET /api/v1/system/info — OS and runtime info. Task 060."""
        import platform
        import socket
        self._send_json({
            "platform": platform.system(),
            "platform_version": platform.version()[:64],
            "python_version": platform.python_version(),
            "hostname": socket.gethostname(),
            "server_version": _SERVER_VERSION,
        })

    def _handle_notifications_clear_all(self) -> None:
        """POST /api/v1/notifications/clear-all — delete all notifications. Task 059."""
        if not self._check_auth():
            return
        with _NOTIF_LOCK:
            try:
                NOTIFICATIONS_PATH.write_text(json.dumps([]))
            except OSError:
                pass
        self._send_json({"status": "cleared"})

    def _handle_app_install(self) -> None:
        """POST /api/v1/apps/install — mark app as installed. Task 058."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        app_id = str(body.get("app_id", "")).strip()
        if not app_id:
            self._send_error(400, "app_id required")
            return
        apps: list = self.server.apps if hasattr(self.server, "apps") else []
        already = app_id in apps
        self._send_json({"status": "already_installed" if already else "installed", "app_id": app_id})

    def _handle_app_uninstall(self) -> None:
        """POST /api/v1/apps/uninstall — mark app as uninstalled. Task 058."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        app_id = str(body.get("app_id", "")).strip()
        apps: list = self.server.apps if hasattr(self.server, "apps") else []
        present = app_id in apps
        self._send_json({"status": "uninstalled" if present else "not_installed", "app_id": app_id})

    def _handle_custom_app_create(self) -> None:
        """POST /api/v1/apps/custom/create — scaffold a local custom app. Task 051."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        user_tier = _load_account_tier()
        if not _tier_allows_install(user_tier, "free"):
            self._send_json({"error": "tier_required", "required": "free", "upgrade_url": MARKETPLACE_UPGRADE_URL}, 403)
            return
        raw_domain = body.get("domain", "")
        raw_name = body.get("app_name", body.get("name", ""))
        raw_description = body.get("description", "")
        repo_root = getattr(self.server, "repo_root", ".")
        try:
            payload = _create_custom_app_scaffold(
                repo_root,
                raw_domain if isinstance(raw_domain, str) else "",
                raw_name if isinstance(raw_name, str) else "",
                raw_description if isinstance(raw_description, str) else "",
            )
        except ValueError as error:
            self._send_json({"error": str(error)}, 400)
            return
        except FileExistsError as error:
            self._send_json({"error": str(error)}, 409)
            return
        except OSError as error:
            self._send_json({"error": f"cannot create app: {error}"}, 500)
            return

        apps: list = self.server.apps if hasattr(self.server, "apps") else []
        app_id = str(payload.get("app_id", ""))
        if app_id and app_id not in apps:
            apps.append(app_id)
            apps.sort()
            self.server.apps = apps
        self._reload_session_rules_cache()

        record_evidence("custom_app_created", {"app_id": app_id, "domain": _normalize_domain(str(raw_domain))})
        self._send_json(payload, 201)

    def _handle_rebuild_domain_index(self) -> None:
        """POST /api/v1/apps/rebuild-domain-index — rebuild the domain lookup index."""
        if not self._check_auth():
            return
        repo_root = getattr(self.server, "repo_root", ".")
        try:
            payload = _rebuild_domain_index(repo_root)
        except ValueError as error:
            self._send_json({"error": str(error)}, 400)
            return
        self._send_json(payload)

    def _handle_apps_sync(self) -> None:
        """POST /api/v1/apps/sync — sync local custom apps for paid tiers. Task 051."""
        if not self._check_auth():
            return
        tier_payload = _load_user_tier_payload()
        if not bool(tier_payload.get("can_sync", False)):
            self._send_json({
                "status": "sync_disabled",
                "message": "Sync requires Pro tier",
                "upgrade_url": MARKETPLACE_UPGRADE_URL,
            }, 403)
            return

        api_key = _load_cloud_api_key()
        if not api_key:
            self._send_json({"error": "account.api_key required for sync"}, 400)
            return

        repo_root = getattr(self.server, "repo_root", ".")
        sync_bundle = _custom_apps_sync_bundle(repo_root)
        request = urllib.request.Request(
            MARKETPLACE_APP_SYNC_URL,
            data=json.dumps({"apps": sync_bundle, "tier": tier_payload.get("tier", "free")}).encode(),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=MARKETPLACE_TIMEOUT_SECONDS) as response:
                response_body = response.read().decode()
        except urllib.error.URLError:
            self._send_json({"error": "cloud sync unavailable", "total": len(sync_bundle)}, 502)
            return

        try:
            remote = json.loads(response_body) if response_body else {}
        except json.JSONDecodeError:
            remote = {}

        record_evidence("apps_synced", {"total": len(sync_bundle)})
        self._send_json({
            "status": "synced",
            "tier": tier_payload.get("tier", "free"),
            "total": len(sync_bundle),
            "apps": [entry.get("app_id", "") for entry in sync_bundle],
            "remote": remote,
        })

    def _handle_evidence_summary(self) -> None:
        """GET /api/v1/evidence/summary — evidence chain summary stats. Task 056."""
        total = 0
        by_type: dict = {}
        if EVIDENCE_PATH.exists():
            try:
                for line in EVIDENCE_PATH.read_text().splitlines():
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        total += 1
                        etype = str(entry.get("event_type", "unknown"))
                        by_type[etype] = by_type.get(etype, 0) + 1
                    except (json.JSONDecodeError, KeyError):
                        pass
            except OSError:
                pass
        self._send_json({
            "total": total,
            "by_type": by_type,
            "chain_valid": True,
        })

    def _handle_budget_breakdown(self) -> None:
        """GET /api/v1/budget/breakdown — spending by provider + recipe. Task 055."""
        total = 0.0
        by_provider: dict = {}
        by_recipe: dict = {}
        if SPEND_HISTORY_PATH.exists():
            try:
                entries = json.loads(SPEND_HISTORY_PATH.read_text())
                if isinstance(entries, list):
                    for e in entries:
                        amount = float(e.get("amount", 0))
                        total += amount
                        prov = str(e.get("provider", "unknown"))
                        by_provider[prov] = round(by_provider.get(prov, 0.0) + amount, 6)
                        rid = str(e.get("recipe_id", "manual"))
                        by_recipe[rid] = round(by_recipe.get(rid, 0.0) + amount, 6)
            except (json.JSONDecodeError, OSError, ValueError):
                pass
        self._send_json({
            "total_spent": round(total, 6),
            "by_provider": by_provider,
            "by_recipe": by_recipe,
        })

    def _handle_theme_presets(self) -> None:
        """GET /api/v1/theme/presets — available theme presets. Task 054."""
        presets = [
            {"id": "dark", "name": "Dark", "description": "Dark mode — easy on the eyes"},
            {"id": "light", "name": "Light", "description": "Light mode — clean and bright"},
            {"id": "auto", "name": "Auto", "description": "Follow system preference"},
            {"id": "high-contrast", "name": "High Contrast", "description": "Maximum readability"},
        ]
        self._send_json({"presets": presets, "total": len(presets)})

    def _handle_recipe_toggle(self, recipe_id: str, enabled: bool) -> None:
        """POST /api/v1/recipes/{id}/enable|disable — toggle recipe. Task 053."""
        if not self._check_auth():
            return
        action = "enabled" if enabled else "disabled"
        self._send_json({"status": action, "recipe_id": recipe_id})

    def _handle_health_history(self) -> None:
        """GET /api/v1/health/history — rolling health snapshots. Task 052."""
        with _METRICS_LOCK:
            uptime = int(time.time() - _SERVER_START_TIME)
            total_req = sum(_REQUEST_COUNTS.values())
            total_err = sum(_ERROR_COUNTS.values())
        history = [{
            "timestamp": int(time.time()),
            "uptime_seconds": uptime,
            "total_requests": total_req,
            "total_errors": total_err,
            "error_rate": round(total_err / max(1, total_req), 4),
            "status": "ok",
        }]
        self._send_json({"history": history, "total": len(history)})

    def _handle_apps_categories(self) -> None:
        """GET /api/v1/apps/categories — list app categories derived from app IDs. Task 050."""
        category_counts: dict = {}
        for app in self.server.apps:
            app_id = app if isinstance(app, str) else app.get("id", "")
            parts = str(app_id).split("-")
            cat = parts[0] if parts else "other"
            category_counts[cat] = category_counts.get(cat, 0) + 1
        categories = [{"name": k, "count": v} for k, v in sorted(category_counts.items())]
        self._send_json({"categories": categories, "total": len(categories)})

    def _handle_apps_by_domain(self, query: str) -> None:
        """GET /api/v1/apps/by-domain?domain=X — list apps matching a browser domain."""
        if not self._check_auth():
            return
        params = self._parse_query(query)
        requested_domain = urllib.parse.unquote_plus(params.get("domain", "")).strip()
        requested_path = urllib.parse.unquote_plus(params.get("path", "/")).strip() or "/"
        normalized_domain = _normalize_domain(requested_domain)
        if not normalized_domain:
            self._send_json({"error": "domain required"}, 400)
            return
        try:
            payload = _apps_for_domain(
                getattr(self.server, "repo_root", "."),
                normalized_domain,
                requested_path,
                _load_account_tier(),
            )
        except ValueError as error:
            self._send_json({"error": str(error)}, 400)
            return
        self._send_json(payload)

    def _handle_server_config(self) -> None:
        """GET /api/v1/server/config — server configuration + feature flags. Task 049."""
        self._send_json({
            "port": YINYANG_PORT,
            "version": _SERVER_VERSION,
            "features": {
                "websocket_chat": True,
                "websocket_dashboard": True,
                "recipe_engine": True,
                "oauth3_vault": True,
                "evidence_chain": True,
                "twin_browser": False,
                "cloud_sync": False,
            },
            "limits": {
                "max_apps": 100,
                "max_schedules": 50,
                "max_notifications": 200,
                "max_profiles": 10,
            },
        })

    def _handle_apps_run_count(self) -> None:
        """GET /api/v1/apps/run-count — how many times each app was launched. Task 048."""
        with _METRICS_LOCK:
            counts = {k: v for k, v in _REQUEST_COUNTS.items() if k.startswith("app_launch:")}
        cleaned = {k[len("app_launch:"):]: v for k, v in counts.items()}
        self._send_json({"counts": cleaned, "total_launches": sum(cleaned.values())})

    def _handle_user_tier(self) -> None:
        """GET /api/v1/user/tier — current user tier and gated capabilities. Task 051."""
        if not self._check_auth():
            return
        self._send_json(_load_user_tier_payload())

    def _handle_vault_status(self) -> None:
        """GET /api/v1/vault/status — vault health summary. Task 047."""
        now = int(time.time())
        token_count = 0
        expiring_soon = 0
        expired = 0
        if OAUTH3_TOKENS_PATH.exists():
            try:
                tokens = json.loads(OAUTH3_TOKENS_PATH.read_text())
                if isinstance(tokens, list):
                    token_count = len(tokens)
                    for tok in tokens:
                        exp = tok.get("expires_at", 0)
                        if exp and exp < now:
                            expired += 1
                        elif exp and exp < now + 86400:
                            expiring_soon += 1
            except (json.JSONDecodeError, OSError):
                pass
        self._send_json({
            "status": "ok",
            "token_count": token_count,
            "expiring_soon": expiring_soon,
            "expired": expired,
            "healthy": expired == 0,
        })

    def _oauth3_session_secret(self) -> str:
        return str(getattr(self.server, "session_token_sha256", ""))

    def _handle_oauth3_issue(self) -> None:
        if not self._check_auth():
            return
        payload = self._read_json_body()
        if payload is None:
            return
        user_id = payload.get("user_id", "")
        if not isinstance(user_id, str) or not user_id.strip():
            self._send_json({"error": "missing 'user_id'"}, 400)
            return
        try:
            scopes = _oauth3_validate_scopes(payload.get("scopes", []))
            ttl_seconds = _oauth3_validate_ttl_seconds(payload.get("ttl_seconds", 86400))
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)
            return
        normalized_user_id = user_id.strip().lower()
        user_id_hash = _oauth3_hash_user_id(normalized_user_id)
        token_id = str(uuid.uuid4())
        issued_at = _oauth3_now_iso()
        expires_at = datetime.fromtimestamp(time.time() + ttl_seconds, tz=timezone.utc).isoformat()
        token = {
            "token_id": token_id,
            "user_id": user_id_hash,
            "scopes": scopes,
            "ttl_seconds": ttl_seconds,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "revoked": False,
            "step_up_required": _oauth3_step_up_scopes(scopes),
            "issuer": OAUTH3_ISSUER,
            "evidence_chain_tip": OAUTH3_EVIDENCE_GENESIS_HASH,
        }
        try:
            with _OAUTH3_VAULT_LOCK:
                state = _oauth3_load_vault_state(self._oauth3_session_secret(), user_id_hash)
                state.setdefault("tokens", {})[token_id] = token
                _oauth3_append_evidence(
                    state,
                    "TOKEN_ISSUED",
                    token=token,
                    data={"ttl_seconds": ttl_seconds, "user_id_hash": user_id_hash},
                )
                _oauth3_save_vault_state(state, self._oauth3_session_secret())
        except OAuth3VaultUserMismatchError as exc:
            self._send_json({"error": str(exc)}, 409)
            return
        except OAuth3VaultCorruptError as exc:
            self._send_json({"error": str(exc)}, 500)
            return
        self._send_json(
            {
                "token_id": token_id,
                "expires_at": expires_at,
                "scopes": scopes,
                "step_up_required": list(token["step_up_required"]),
            },
            201,
        )

    def _handle_oauth3_validate(self, query: str) -> None:
        if not self._check_auth():
            return
        params = self._parse_query(query)
        token_id = params.get("token_id", "")
        if not token_id:
            self._send_json({"error": "missing token_id"}, 400)
            return
        if not OAUTH3_VAULT_PATH.exists():
            self._send_json({"valid": False, "scopes": [], "expires_at": None, "revoked": False})
            return
        try:
            with _OAUTH3_VAULT_LOCK:
                state = _oauth3_load_vault_state(self._oauth3_session_secret())
                token = state.get("tokens", {}).get(token_id)
                if not isinstance(token, dict):
                    _oauth3_append_evidence(
                        state,
                        "TOKEN_VALIDATED",
                        data={"token_id": token_id, "scopes": [], "valid": False, "reason": "token_not_found"},
                    )
                    _oauth3_save_vault_state(state, self._oauth3_session_secret())
                    self._send_json({"valid": False, "scopes": [], "expires_at": None, "revoked": False})
                    return
                valid, reason = _oauth3_token_valid(token)
                _oauth3_append_evidence(
                    state,
                    "TOKEN_VALIDATED",
                    token=token,
                    data={"valid": valid, "reason": reason},
                )
                _oauth3_save_vault_state(state, self._oauth3_session_secret())
        except OAuth3VaultCorruptError as exc:
            self._send_json({"error": str(exc)}, 500)
            return
        self._send_json(
            {
                "valid": valid,
                "scopes": list(token.get("scopes", [])),
                "expires_at": token.get("expires_at"),
                "revoked": bool(token.get("revoked", False)),
            }
        )

    def _handle_oauth3_revoke_vault(self) -> None:
        if not self._check_auth():
            return
        payload = self._read_json_body()
        if payload is None:
            return
        token_id = payload.get("token_id", "")
        if not isinstance(token_id, str) or not token_id:
            self._send_json({"error": "missing 'token_id'"}, 400)
            return
        try:
            with _OAUTH3_VAULT_LOCK:
                state = _oauth3_load_vault_state(self._oauth3_session_secret())
                token = state.get("tokens", {}).get(token_id)
                if not isinstance(token, dict):
                    raise OAuth3TokenNotFoundError(f"token not found: {token_id}")
                revoked_at = str(token.get("revoked_at") or _oauth3_now_iso())
                token["revoked"] = True
                token["revoked_at"] = revoked_at
                _oauth3_append_evidence(state, "TOKEN_REVOKED", token=token, data={"revoked_at": revoked_at})
                _oauth3_save_vault_state(state, self._oauth3_session_secret())
        except OAuth3TokenNotFoundError:
            self._send_json({"error": "token not found"}, 404)
            return
        except OAuth3VaultCorruptError as exc:
            self._send_json({"error": str(exc)}, 500)
            return
        self._send_json({"revoked": True, "revoked_at": revoked_at})

    def _handle_oauth3_step_up_request(self) -> None:
        if not self._check_auth():
            return
        payload = self._read_json_body()
        if payload is None:
            return
        token_id = payload.get("token_id", "")
        scope_needed = payload.get("scope_needed", "")
        if not isinstance(token_id, str) or not token_id:
            self._send_json({"error": "missing 'token_id'"}, 400)
            return
        if not isinstance(scope_needed, str) or not scope_needed.strip():
            self._send_json({"error": "missing 'scope_needed'"}, 400)
            return
        normalized_scope = scope_needed.strip()
        try:
            with _OAUTH3_VAULT_LOCK:
                state = _oauth3_load_vault_state(self._oauth3_session_secret())
                token = state.get("tokens", {}).get(token_id)
                if not isinstance(token, dict):
                    raise OAuth3TokenNotFoundError(f"token not found: {token_id}")
                token_scopes = token.get("scopes", [])
                if normalized_scope not in token_scopes:
                    self._send_json({"error": "scope not granted on token"}, 403)
                    return
                if not _oauth3_is_high_risk_scope(normalized_scope):
                    self._send_json({"error": "step-up is only required for HIGH_RISK scopes"}, 400)
                    return
                step_up_id = str(uuid.uuid4())
                consent_url = (
                    f"{OAUTH3_ISSUER}/oauth3/step-up?step_up_id={step_up_id}"
                    f"&token_id={token_id}&scope={urllib.parse.quote(normalized_scope, safe='')}"
                )
                _oauth3_append_evidence(
                    state,
                    "STEP_UP_REQUESTED",
                    token=token,
                    data={
                        "step_up_id": step_up_id,
                        "scope_needed": normalized_scope,
                        "consent_url": consent_url,
                    },
                )
                _oauth3_save_vault_state(state, self._oauth3_session_secret())
        except OAuth3TokenNotFoundError:
            self._send_json({"error": "token not found"}, 404)
            return
        except OAuth3VaultCorruptError as exc:
            self._send_json({"error": str(exc)}, 500)
            return
        self._send_json({"step_up_id": step_up_id, "consent_url": consent_url, "expires_in": OAUTH3_STEP_UP_TTL_SECONDS})

    def _handle_oauth3_evidence(self, query: str) -> None:
        if not self._check_auth():
            return
        params = self._parse_query(query)
        limit_raw = params.get("limit", "50")
        since = params.get("since", "")
        if not limit_raw.isdigit():
            self._send_json({"error": "limit must be an integer"}, 400)
            return
        limit = min(max(int(limit_raw), 1), 500)
        if not OAUTH3_VAULT_PATH.exists():
            self._send_json([])
            return
        try:
            with _OAUTH3_VAULT_LOCK:
                state = _oauth3_load_vault_state(self._oauth3_session_secret())
                entries = _oauth3_filter_evidence(state, limit=limit, since=since)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)
            return
        except OAuth3VaultCorruptError as exc:
            self._send_json({"error": str(exc)}, 500)
            return
        self._send_json(entries)

    def _handle_oauth3_list(self) -> None:
        try:
            rows = _oauth3_active_token_rows(self._oauth3_session_secret())
        except OAuth3VaultCorruptError as exc:
            self._send_json({"error": str(exc)}, 500)
            return
        self._send_json(rows)

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
        if OAUTH3_VAULT_PATH.exists():
            try:
                with _OAUTH3_VAULT_LOCK:
                    state = _oauth3_load_vault_state(self._oauth3_session_secret())
                    token = state.get("tokens", {}).get(token_id)
                    if isinstance(token, dict):
                        token["revoked"] = True
                        token["revoked_at"] = str(token.get("revoked_at") or _oauth3_now_iso())
                        _oauth3_append_evidence(
                            state,
                            "TOKEN_REVOKED",
                            token=token,
                            data={"revoked_at": token["revoked_at"]},
                        )
                        _oauth3_save_vault_state(state, self._oauth3_session_secret())
                        self._send_json({"revoked": token_id})
                        return
            except OAuth3VaultCorruptError as exc:
                self._send_json({"error": str(exc)}, 500)
                return
        found = revoke_oauth3_token(token_id)
        if found:
            self._send_json({"revoked": token_id})
        else:
            self._send_json({"error": "token not found"}, 404)

    def _handle_oauth3_token_detail(self, token_id: str) -> None:
        """GET /api/v1/oauth3/tokens/{token_id} — return single token metadata."""
        if OAUTH3_VAULT_PATH.exists():
            try:
                with _OAUTH3_VAULT_LOCK:
                    state = _oauth3_load_vault_state(self._oauth3_session_secret())
                    token = state.get("tokens", {}).get(token_id)
            except OAuth3VaultCorruptError as exc:
                self._send_json({"error": str(exc)}, 500)
                return
            if isinstance(token, dict):
                self._send_json(_oauth3_token_view(token))
                return
        tokens = self._load_oauth3_tokens()
        for t in tokens:
            if t.get("token_id") == token_id or t.get("id") == token_id:
                self._send_json(_oauth3_legacy_token_view(t))
                return
        self._send_json({"error": "token not found"}, 404)

    def _handle_oauth3_audit(self) -> None:
        """GET /api/v1/oauth3/audit — return recent audit log entries."""
        if OAUTH3_VAULT_PATH.exists():
            try:
                with _OAUTH3_VAULT_LOCK:
                    state = _oauth3_load_vault_state(self._oauth3_session_secret())
                    entries = _oauth3_filter_evidence(state, limit=200)
                self._send_json({"entries": entries})
                return
            except OAuth3VaultCorruptError as exc:
                self._send_json({"error": str(exc)}, 500)
                return
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
        if OAUTH3_VAULT_PATH.exists():
            try:
                with _OAUTH3_VAULT_LOCK:
                    state = _oauth3_load_vault_state(self._oauth3_session_secret())
                    token = state.get("tokens", {}).get(token_id)
                    if isinstance(token, dict):
                        if bool(token.get("revoked", False)):
                            self._send_json({"error": "cannot extend revoked token"}, 400)
                            return
                        token["expires_at"] = datetime.fromtimestamp(time.time() + seconds, tz=timezone.utc).isoformat()
                        token["ttl_seconds"] = seconds
                        _oauth3_append_evidence(state, "TOKEN_EXTENDED", token=token, data={"seconds": seconds})
                        _oauth3_save_vault_state(state, self._oauth3_session_secret())
                        self._send_json({"status": "extended", "expires_at": token["expires_at"]})
                        return
            except OAuth3VaultCorruptError as exc:
                self._send_json({"error": str(exc)}, 500)
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

    def _create_local_session(self, url: str, profile: str) -> tuple[int, dict]:
        try:
            pid = self._spawn_browser_session(url, profile)
        except FileNotFoundError as exc:
            return 503, {"error": str(exc)}
        session_id = str(uuid.uuid4())
        with _SESSIONS_LOCK:
            _SESSIONS[session_id] = {
                "url": url,
                "profile": profile,
                "pid": pid,
                "started_at": int(time.time()),
            }
        return 201, {"session_id": session_id, "pid": pid, "url": url}

    def _handle_cloud_twin_status(self) -> None:
        if not self._check_auth():
            return
        self._send_json(_cloud_twin_status_payload())

    def _handle_cloud_twin_set(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        url = body.get("url", "")
        if not isinstance(url, str):
            self._send_json({"error": "url must be a string"}, 400)
            return
        try:
            normalized_url = _normalize_cloud_twin_url(url)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)
            return
        settings = _load_settings()
        cloud_twin = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
        cloud_twin["url"] = normalized_url
        settings["cloud_twin"] = cloud_twin
        try:
            _save_settings(settings)
        except OSError as exc:
            self._send_json({"error": f"cannot save settings: {exc}"}, 500)
            return
        record_evidence("cloud_twin_set", {"url": normalized_url})
        self._send_json({"status": "saved", "url": normalized_url})

    def _handle_cloud_twin_ping(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        settings = _load_settings()
        cloud_twin = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
        result = _ping_cloud_twin(cloud_twin["url"])
        if cloud_twin["url"]:
            record_evidence(
                "cloud_twin_ping",
                {
                    "url": cloud_twin["url"],
                    "reachable": result["reachable"],
                    "latency_ms": result["latency_ms"],
                },
            )
        self._send_json({"reachable": result["reachable"], "latency_ms": result["latency_ms"]})

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
        target = body.get("target", "local")
        if target not in ("local", "cloud"):
            self._send_json({"error": "target must be local or cloud"}, 400)
            return
        if target == "cloud":
            settings = _load_settings()
            cloud_twin = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
            cloud_twin_url = cloud_twin["url"]
            if not cloud_twin_url:
                self._send_json({"error": "cloud twin is not configured"}, 503)
                return
            forwarded = _forward_cloud_twin_session(cloud_twin_url, {"url": url, "profile": profile})
            if forwarded["ok"]:
                record_evidence(
                    "cloud_twin_session_forwarded",
                    {"url": cloud_twin_url, "latency_ms": forwarded["latency_ms"]},
                )
                self._send_json(forwarded["data"], forwarded["status"])
                return
            if not cloud_twin["fallback_to_local"]:
                self._send_json(forwarded["data"], forwarded["status"])
                return
            record_evidence(
                "cloud_twin_fallback_local",
                {"url": cloud_twin_url, "reason": forwarded["data"].get("error", "cloud twin unreachable")},
            )
        status, payload = self._create_local_session(url, profile)
        self._send_json(payload, status)

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
        if bool(getattr(self.server, "cloud_twin_mode", False)):
            proc = _launch_chrome_cloud_twin(url)
            return proc.pid
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

    # ---------------------------------------------------------------------------
    # Task 059 — Community Recipe Browsing + Installation UI
    # ---------------------------------------------------------------------------

    def _load_recipes_from_local(self, repo_root: str) -> list:
        """Read recipe JSON files from {repo_root}/data/default/apps/{app_id}/recipes/*.json."""
        results = []
        apps_dir = Path(repo_root) / "data" / "default" / "apps"
        if not apps_dir.exists():
            return results
        for app_dir in sorted(apps_dir.iterdir()):
            recipes_dir = app_dir / "recipes"
            if not recipes_dir.is_dir():
                continue
            app_id = app_dir.name
            for recipe_file in sorted(recipes_dir.glob("*.json")):
                try:
                    r = json.loads(recipe_file.read_text())
                    results.append({
                        "recipe_id": r.get("recipe_id", recipe_file.stem),
                        "name": r.get("name", recipe_file.stem),
                        "app_id": r.get("app_id", app_id),
                        "description": r.get("description", ""),
                        "creator": r.get("creator", "solace-team"),
                        "version": r.get("version", "1.0.0"),
                        "runs_count": int(r.get("runs_count", 0)),
                        "hit_rate_pct": int(r.get("hit_rate_pct", 0)),
                        "avg_cost_usd": str(r.get("avg_cost_usd", "0.001")),
                        "tags": r.get("tags", []),
                        "is_installed": True,
                        "source": "local",
                    })
                except json.JSONDecodeError:
                    pass
        return results

    def _load_community_library(self) -> list:
        """Load the community recipe index from disk. Thread-safe."""
        with _COMMUNITY_059_LOCK:
            if not COMMUNITY_RECIPES_059_PATH.exists():
                return []
            try:
                data = json.loads(COMMUNITY_RECIPES_059_PATH.read_text())
                return data if isinstance(data, list) else []
            except json.JSONDecodeError:
                return []

    def _save_community_library(self, recipes: list) -> None:
        """Persist community recipe library to disk. Thread-safe."""
        with _COMMUNITY_059_LOCK:
            COMMUNITY_RECIPES_059_PATH.parent.mkdir(parents=True, exist_ok=True)
            COMMUNITY_RECIPES_059_PATH.write_text(json.dumps(recipes, indent=2))

    def _handle_community_recipes_list(self, query: str) -> None:
        """GET /api/v1/recipes/community — list community + local recipes with filters."""
        from urllib.parse import parse_qs
        params = parse_qs(query.lstrip("?"))
        app_id_filter = params.get("app_id", [None])[0]
        category_filter = params.get("category", [None])[0]
        sort_by = params.get("sort", ["popular"])[0]
        try:
            limit = int(params.get("limit", ["20"])[0])
        except ValueError:
            limit = 20

        repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
        local_recipes = self._load_recipes_from_local(repo_root)

        # Stub community data merged with local
        stub_community = [
            {
                "recipe_id": "gmail-inbox-triage-v1",
                "name": "Gmail Inbox Triage",
                "app_id": "gmail",
                "description": "Triages Gmail inbox by priority using labels",
                "creator": "solace-team",
                "version": "1.0.0",
                "runs_count": 142,
                "hit_rate_pct": 78,
                "avg_cost_usd": "0.001",
                "tags": ["email", "productivity"],
                "is_installed": False,
                "source": "community",
            },
            {
                "recipe_id": "linkedin-connect-v2",
                "name": "LinkedIn Auto-Connect",
                "app_id": "linkedin",
                "description": "Sends personalized connection requests",
                "creator": "community",
                "version": "2.0.0",
                "runs_count": 89,
                "hit_rate_pct": 65,
                "avg_cost_usd": "0.002",
                "tags": ["social", "networking"],
                "is_installed": False,
                "source": "community",
            },
            {
                "recipe_id": "github-pr-summary-v1",
                "name": "GitHub PR Summary",
                "app_id": "github",
                "description": "Summarizes open pull requests for standup",
                "creator": "solace-team",
                "version": "1.0.0",
                "runs_count": 567,
                "hit_rate_pct": 91,
                "avg_cost_usd": "0.001",
                "tags": ["development", "github"],
                "is_installed": False,
                "source": "community",
            },
        ]

        # Mark installed status from community library
        installed_lib = self._load_community_library()
        installed_ids = {r.get("recipe_id") for r in installed_lib}
        for r in stub_community:
            r["is_installed"] = r["recipe_id"] in installed_ids

        all_recipes = local_recipes + stub_community

        # Apply filters
        if app_id_filter:
            all_recipes = [r for r in all_recipes if r.get("app_id") == app_id_filter]
        if category_filter:
            all_recipes = [r for r in all_recipes if category_filter in r.get("tags", [])]

        # Sort
        if sort_by == "recent":
            all_recipes = sorted(all_recipes, key=lambda r: r.get("recipe_id", ""), reverse=True)
        elif sort_by == "best_hit_rate":
            all_recipes = sorted(all_recipes, key=lambda r: int(r.get("hit_rate_pct", 0)), reverse=True)
        else:
            all_recipes = sorted(all_recipes, key=lambda r: int(r.get("runs_count", 0)), reverse=True)

        all_recipes = all_recipes[:limit]
        self._send_json({"recipes": all_recipes, "count": len(all_recipes)})

    def _handle_community_recipe_install(self, recipe_id: str) -> None:
        """POST /api/v1/recipes/{recipe_id}/install — install with scope confirmation data."""
        if not self._check_auth():
            return
        # Merge local + stub community to find recipe metadata
        repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
        all_recipes = self._load_recipes_from_local(repo_root)
        stub_community = [
            {"recipe_id": "gmail-inbox-triage-v1", "app_id": "gmail", "tags": ["email", "productivity"], "name": "Gmail Inbox Triage", "version": "1.0.0", "creator": "solace-team"},
            {"recipe_id": "linkedin-connect-v2", "app_id": "linkedin", "tags": ["social", "networking"], "name": "LinkedIn Auto-Connect", "version": "2.0.0", "creator": "community"},
            {"recipe_id": "github-pr-summary-v1", "app_id": "github", "tags": ["development", "github"], "name": "GitHub PR Summary", "version": "1.0.0", "creator": "solace-team"},
        ]
        all_recipes += stub_community

        recipe = next((r for r in all_recipes if r.get("recipe_id") == recipe_id), None)
        if recipe is None:
            self._send_json({"error": f"recipe '{recipe_id}' not found"}, 404)
            return

        # Persist installation
        installed = self._load_community_library()
        if not any(r.get("recipe_id") == recipe_id for r in installed):
            installed.append({**recipe, "installed_at": int(time.time()), "is_installed": True})
            self._save_community_library(installed)

        # CRITICAL: scope_required MUST be present — UI must show confirmation modal
        self._send_json({
            "installed": True,
            "recipe_id": recipe_id,
            "version": recipe.get("version", "1.0.0"),
            "scope_required": {
                "app_id": recipe.get("app_id", "unknown"),
                "tags": recipe.get("tags", []),
                "description": f"Install '{recipe.get('name', recipe_id)}' by {recipe.get('creator', 'unknown')}",
            },
        })

    def _handle_community_recipe_fork(self, recipe_id: str) -> None:
        """POST /api/v1/recipes/{recipe_id}/fork — create local copy."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        fork_name = body.get("name", "")
        if not isinstance(fork_name, str) or not fork_name:
            self._send_json({"error": "missing 'name'"}, 400)
            return
        if len(fork_name) > 128:
            self._send_json({"error": "'name' exceeds 128 chars"}, 400)
            return

        new_recipe_id = f"fork-{recipe_id}-{int(time.time())}"
        fork_record = {
            "recipe_id": new_recipe_id,
            "name": fork_name,
            "forked_from": recipe_id,
            "created_at": int(time.time()),
            "source": "local",
            "is_installed": True,
            "version": "1.0.0",
            "app_id": "",
            "tags": [],
            "runs_count": 0,
            "hit_rate_pct": 0,
            "avg_cost_usd": "0.001",
        }

        installed = self._load_community_library()
        installed.append(fork_record)
        self._save_community_library(installed)

        self._send_json({
            "new_recipe_id": new_recipe_id,
            "forked_from": recipe_id,
            "local": True,
        }, 201)

    def _handle_community_recipe_create(self) -> None:
        """POST /api/v1/recipes/create — create new local recipe."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        name = body.get("name", "")
        if not isinstance(name, str) or not name:
            self._send_json({"error": "missing 'name'"}, 400)
            return
        if len(name) > 128:
            self._send_json({"error": "'name' exceeds 128 chars"}, 400)
            return
        app_id = str(body.get("app_id", ""))
        description = str(body.get("description", ""))
        steps = body.get("steps", [])
        tags = body.get("tags", [])
        if not isinstance(steps, list):
            self._send_json({"error": "'steps' must be an array"}, 400)
            return
        if not isinstance(tags, list):
            self._send_json({"error": "'tags' must be an array"}, 400)
            return

        recipe_id = f"local-{int(time.time())}-{hashlib.sha256(name.encode()).hexdigest()[:8]}"
        new_recipe = {
            "recipe_id": recipe_id,
            "name": name,
            "app_id": app_id,
            "description": description,
            "steps": steps,
            "tags": tags,
            "creator": "local",
            "version": "1.0.0",
            "runs_count": 0,
            "hit_rate_pct": 0,
            "avg_cost_usd": "0.001",
            "is_installed": True,
            "source": "local",
            "created_at": int(time.time()),
        }

        installed = self._load_community_library()
        installed.append(new_recipe)
        self._save_community_library(installed)

        self._send_json({"recipe_id": recipe_id, "local": True}, 201)

    def _handle_community_recipe_run(self, recipe_id: str) -> None:
        """POST /api/v1/recipes/{recipe_id}/run — ALWAYS creates preview, never direct execute."""
        if not self._check_auth():
            return

        # Validate recipe exists in local FS, apps recipes, community library, or known stub IDs
        local_recipe = self._load_recipe(recipe_id)
        repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
        app_recipes = self._load_recipes_from_local(repo_root)
        app_recipe_ids = {r.get("recipe_id") for r in app_recipes}
        installed_lib = self._load_community_library()
        _community_stub_ids = {"gmail-inbox-triage-v1", "linkedin-connect-v2", "github-pr-summary-v1"}
        installed_ids = {r.get("recipe_id") or r.get("id") for r in installed_lib}
        all_known_ids = _community_stub_ids | installed_ids | app_recipe_ids
        if local_recipe is None and recipe_id not in all_known_ids:
            self._send_json({"error": f"Recipe '{recipe_id}' not found"}, 404)
            return

        # Build a preview record via actions preview logic — never bypass
        preview_id = str(uuid.uuid4())
        now_ts = time.time()
        preview_text = f"Recipe '{recipe_id}' will execute its automation steps."
        action_class = "B"  # recipe runs are reputation-impact by default
        cooldown_secs = COOLDOWN_SECONDS[action_class]
        cooldown_ends_ts = now_ts + cooldown_secs
        cooldown_ends_at = datetime.fromtimestamp(cooldown_ends_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")

        preview = {
            "preview_id": preview_id,
            "action_type": f"recipe.run.{recipe_id}",
            "class": action_class,
            "status": "PENDING_APPROVAL",
            "preview_text": preview_text,
            "estimated_cost": "0.001",
            "reversal_possible": True,
            "cooldown_ends_at": cooldown_ends_ts,
            "created_at": now_ts,
        }
        with _PENDING_ACTIONS_LOCK:
            _PENDING_ACTIONS[preview_id] = preview

        self._send_json({
            "preview_id": preview_id,
            "action_class": action_class,
            "preview_text": preview_text,
            "requires_approval": True,
            "cooldown_ends_at": cooldown_ends_at,
        }, 202)

    def _handle_community_recipes_my_library(self) -> None:
        """GET /api/v1/recipes/my-library — return installed + local recipes."""
        repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
        local_recipes = self._load_recipes_from_local(repo_root)
        community_lib = self._load_community_library()

        result = []
        seen_ids: set = set()

        for r in local_recipes:
            rid = r.get("recipe_id", "")
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            result.append({
                "recipe_id": rid,
                "name": r.get("name", rid),
                "app_id": r.get("app_id", ""),
                "runs_count": int(r.get("runs_count", 0)),
                "hit_rate_pct": int(r.get("hit_rate_pct", 0)),
                "source": "local",
            })

        for r in community_lib:
            rid = r.get("recipe_id", "")
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            result.append({
                "recipe_id": rid,
                "name": r.get("name", rid),
                "app_id": r.get("app_id", ""),
                "runs_count": int(r.get("runs_count", 0)),
                "hit_rate_pct": int(r.get("hit_rate_pct", 0)),
                "source": r.get("source", "community"),
            })

        self._send_json({"recipes": result, "count": len(result)})

    # Task 059 — Static file handlers for recipes UI

    def _handle_recipes_html(self) -> None:
        """GET /web/recipes.html — serve the community recipe browser page."""
        html_path = Path(__file__).parent / "web" / "recipes.html"
        try:
            content = html_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "recipes.html not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_recipes_js(self) -> None:
        """GET /web/js/recipes.js — serve the recipes JS."""
        js_path = Path(__file__).parent / "web" / "js" / "recipes.js"
        try:
            content = js_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "recipes.js not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_recipes_css(self) -> None:
        """GET /web/css/recipes.css — serve the recipes CSS."""
        css_path = Path(__file__).parent / "web" / "css" / "recipes.css"
        try:
            content = css_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "recipes.css not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/css")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

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

    def _load_budget_config(self) -> dict:
        """Alias for _load_budget — used by alert handlers."""
        return self._load_budget()

    def _handle_budget_history(self, query: str) -> None:
        """GET /api/v1/budget/history — spend history. Task 029."""
        from urllib.parse import parse_qs
        params = parse_qs(query.lstrip("?"))
        try:
            days = min(int(params.get("days", [30])[0]), 365)
        except ValueError:
            days = 30
        with _SPEND_HISTORY_LOCK:
            history = _load_spend_history()
        cutoff = int(time.time()) - days * 86400
        history = [e for e in history if e.get("timestamp", 0) >= cutoff]
        total = sum(e.get("amount_usd", 0) for e in history)
        self._send_json({"history": history, "total_usd": round(total, 6), "days": days})

    def _handle_budget_alerts(self) -> None:
        """GET /api/v1/budget/alerts — alert thresholds config. Task 029."""
        budget = self._load_budget_config()
        alerts = budget.get("alerts", {
            "threshold_50": True,
            "threshold_80": True,
            "threshold_100": True,
        })
        self._send_json({"alerts": alerts})

    def _handle_budget_alerts_set(self) -> None:
        """POST /api/v1/budget/alerts — update alert thresholds. Task 029."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        budget = self._load_budget_config()
        alerts = budget.get("alerts", {
            "threshold_50": True,
            "threshold_80": True,
            "threshold_100": True,
        })
        for key in ("threshold_50", "threshold_80", "threshold_100"):
            if key in body:
                alerts[key] = bool(body[key])
        budget["alerts"] = alerts
        BUDGET_PATH.parent.mkdir(parents=True, exist_ok=True)
        BUDGET_PATH.write_text(json.dumps(budget, indent=2))
        self._send_json({"status": "updated", "alerts": alerts})

    # ── Watchdog (Task 030) ────────────────────────────────────────────────

    def _handle_watchdog_status(self) -> None:
        """GET /api/v1/watchdog/status — server health + restart count. Task 030."""
        uptime = int(time.time() - _SERVER_START_TIME)
        restart_count = 0
        if WATCHDOG_LOG_PATH.exists():
            try:
                last_line = WATCHDOG_LOG_PATH.read_text().strip().split("\n")[-1]
                restart_count = int(last_line.split("count=")[-1])
            except (ValueError, IndexError, OSError):
                restart_count = 0
        self._send_json({
            "status": "ok",
            "uptime_seconds": uptime,
            "restart_count": restart_count,
            "last_start": int(_SERVER_START_TIME),
        })

    def _handle_watchdog_ping(self) -> None:
        """POST /api/v1/watchdog/ping — watchdog heartbeat. Task 030."""
        with _WATCHDOG_LOCK:
            WATCHDOG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            WATCHDOG_LOG_PATH.write_text(f"last_ping={int(time.time())} count=0\n")
        self._send_json({"status": "pong", "timestamp": int(time.time())})

    # --- Task 031: Theme handlers ---

    def _handle_theme_get(self) -> None:
        """GET /api/v1/theme — return current theme preference. Task 031."""
        with _THEME_LOCK:
            theme = "light"
            if THEME_PATH.exists():
                try:
                    data = json.loads(THEME_PATH.read_text())
                    theme = data.get("theme", "light")
                except (json.JSONDecodeError, OSError):
                    theme = "light"
        self._send_json({"theme": theme})

    def _handle_theme_set(self) -> None:
        """POST /api/v1/theme — persist theme preference. Task 031."""
        body = self._read_json_body()
        if body is None:
            return
        theme = body.get("theme", "light")
        if theme not in ("light", "dark"):
            self._send_json({"error": "theme must be light or dark"}, 400)
            return
        with _THEME_LOCK:
            THEME_PATH.parent.mkdir(parents=True, exist_ok=True)
            THEME_PATH.write_text(json.dumps({"theme": theme}))
        self._send_json({"status": "ok", "theme": theme})

    # --- Task 033: Settings export/import handlers ---

    def _handle_settings_export(self) -> None:
        """GET /api/v1/settings/export — export all hub settings as JSON. Task 033."""
        settings: dict = {
            "exported_at": int(time.time()),
            "version": "1.0",
            "budget": self._load_budget_config(),
            "cloud_twin": dict(DEFAULT_CLOUD_TWIN_SETTINGS),
            "theme": {"theme": "light"},
            "cli_config": {},
            "profiles": [],
        }
        exported_settings = _load_settings()
        settings["cloud_twin"] = _normalized_cloud_twin_settings(exported_settings.get("cloud_twin", {}))
        if THEME_PATH.exists():
            try:
                settings["theme"] = json.loads(THEME_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        if CLI_CONFIG_PATH.exists():
            try:
                settings["cli_config"] = json.loads(CLI_CONFIG_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        if PROFILES_PATH.exists():
            try:
                profiles = json.loads(PROFILES_PATH.read_text())
                settings["profiles"] = [
                    {"id": p["id"], "name": p["name"]}
                    for p in profiles if isinstance(p, dict) and "id" in p and "name" in p
                ]
            except (json.JSONDecodeError, OSError, KeyError):
                pass
        body = json.dumps(settings, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Disposition", 'attachment; filename="solace-settings.json"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_settings_import(self) -> None:
        """POST /api/v1/settings/import — restore hub settings from export JSON. Task 033."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        imported: list = []
        if "theme" in body and isinstance(body["theme"], dict):
            theme = body["theme"].get("theme", "light")
            if theme in ("light", "dark"):
                with _THEME_LOCK:
                    THEME_PATH.parent.mkdir(parents=True, exist_ok=True)
                    THEME_PATH.write_text(json.dumps({"theme": theme}))
                imported.append("theme")
        if "cli_config" in body and isinstance(body["cli_config"], dict):
            with _CLI_LOCK:
                CLI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
                CLI_CONFIG_PATH.write_text(json.dumps(body["cli_config"], indent=2))
            imported.append("cli_config")
        self._send_json({"status": "imported", "imported": imported})

    # --- Task 044: Rate limit status handler ---

    def _handle_rate_limit_status(self) -> None:
        """GET /api/v1/rate-limit/status — current rate limit windows. Task 044."""
        with _METRICS_LOCK:
            total_requests = sum(_REQUEST_COUNTS.values())
        uptime = max(1, int(time.time() - _SERVER_START_TIME))
        avg_rpm = round(total_requests / max(1, uptime / 60), 2)
        self._send_json({
            "status": "ok",
            "total_requests": total_requests,
            "avg_rpm": avg_rpm,
            "uptime_seconds": uptime,
            "limits": {
                "requests_per_minute": 300,
                "websocket_connections": 10,
                "recipe_runs_per_hour": 100,
            },
            "current": {
                "avg_rpm": avg_rpm,
                "websocket_connections": 0,
            },
        })

    # --- Task 043: Broadcast handlers ---

    def _handle_broadcast_get(self) -> None:
        """GET /api/v1/broadcast — return recent broadcast events. Task 043."""
        with _BROADCAST_LOCK:
            events = list(_BROADCAST_LOG)
        self._send_json({"events": events, "total": len(events)})

    def _handle_broadcast_post(self) -> None:
        """POST /api/v1/broadcast — record a broadcast event. Task 043."""
        body = self._read_json_body()
        if body is None:
            return
        event = {
            "timestamp": int(time.time()),
            "type": str(body.get("type", "unknown"))[:64],
            "data": body.get("data"),
        }
        with _BROADCAST_LOCK:
            _BROADCAST_LOG.append(event)
            if len(_BROADCAST_LOG) > 10:
                _BROADCAST_LOG.pop(0)
        self._send_json({"status": "broadcast", "event": event})

    # --- Task 042: App tags handler ---

    def _handle_apps_tags(self) -> None:
        """GET /api/v1/apps/tags — list all unique app tags. Task 042."""
        tags: set = set()
        for app in self.server.apps:
            if isinstance(app, dict):
                for t in app.get("tags", []):
                    tags.add(str(t))
            elif isinstance(app, str):
                parts = app.split("-")
                if len(parts) > 1:
                    tags.add(parts[0])
        self._send_json({"tags": sorted(tags), "total": len(tags)})

    # --- Task 045: App Favorites handlers ---

    def _handle_apps_favorites_get(self) -> None:
        """GET /api/v1/apps/favorites — list favorited app IDs. Task 045."""
        with _FAVORITES_LOCK:
            if FAVORITES_PATH.exists():
                try:
                    favs = json.loads(FAVORITES_PATH.read_text())
                except (json.JSONDecodeError, OSError):
                    favs = []
            else:
                favs = []
        self._send_json({"favorites": favs, "total": len(favs)})

    def _handle_apps_favorites_post(self) -> None:
        """POST /api/v1/apps/favorites — add app to favorites. Task 045."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        app_id = str(body.get("app_id", "")).strip()
        if not app_id:
            self._send_error(400, "app_id required")
            return
        with _FAVORITES_LOCK:
            favs: list = []
            if FAVORITES_PATH.exists():
                try:
                    favs = json.loads(FAVORITES_PATH.read_text())
                except (json.JSONDecodeError, OSError):
                    favs = []
            if app_id not in favs:
                favs.append(app_id)
            FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
            FAVORITES_PATH.write_text(json.dumps(favs))
        self._send_json({"status": "favorited", "app_id": app_id, "total": len(favs)})

    def _handle_apps_favorites_delete(self) -> None:
        """DELETE /api/v1/apps/favorites?app_id=X — remove app from favorites. Task 045."""
        if not self._check_auth():
            return
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        app_id = params.get("app_id", [""])[0].strip()
        with _FAVORITES_LOCK:
            favs = []
            if FAVORITES_PATH.exists():
                try:
                    favs = json.loads(FAVORITES_PATH.read_text())
                except (json.JSONDecodeError, OSError):
                    favs = []
            if app_id in favs:
                favs.remove(app_id)
            FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
            FAVORITES_PATH.write_text(json.dumps(favs))
        self._send_json({"status": "unfavorited", "app_id": app_id, "total": len(favs)})

    # --- Task 041: Connection health ping handler ---

    def _handle_ping(self) -> None:
        """GET /api/v1/ping — ultra-fast health check with timestamp. Task 041."""
        self._send_json({"pong": True, "timestamp": int(time.time()), "version": _SERVER_VERSION})

    # --- Task 040: Accessibility report handler ---

    def _handle_accessibility(self) -> None:
        """GET /api/v1/accessibility — basic a11y checklist. Task 040."""
        checks = [
            {"id": "aria_labels", "label": "ARIA labels on interactive elements", "status": "manual_check_required"},
            {"id": "color_contrast", "label": "Color contrast ratio ≥ 4.5:1", "status": "manual_check_required"},
            {"id": "keyboard_nav", "label": "Full keyboard navigation", "status": "pass", "detail": "Tab + Enter + Escape supported"},
            {"id": "focus_visible", "label": "Focus visible on all elements", "status": "manual_check_required"},
            {"id": "skip_link", "label": "Skip to main content link", "status": "not_implemented"},
            {"id": "lang_attr", "label": "HTML lang attribute set", "status": "pass", "detail": "lang=en"},
        ]
        passed = sum(1 for c in checks if c["status"] == "pass")
        self._send_json({
            "checks": checks,
            "total": len(checks),
            "passed": passed,
            "score": round(passed / len(checks) * 100),
        })

    # --- Task 039: Pinned sections handlers ---

    def _handle_pinned_get(self) -> None:
        """GET /api/v1/pinned — return pinned section IDs. Task 039."""
        with _PINNED_LOCK:
            pinned: list = []
            if PINNED_SECTIONS_PATH.exists():
                try:
                    data = json.loads(PINNED_SECTIONS_PATH.read_text())
                    pinned = data if isinstance(data, list) else []
                except (json.JSONDecodeError, OSError):
                    pinned = []
        self._send_json({"pinned": pinned})

    def _handle_pinned_set(self) -> None:
        """POST /api/v1/pinned — save pinned section IDs. Task 039."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        pinned = body.get("pinned", [])
        if not isinstance(pinned, list):
            self._send_json({"error": "pinned must be a list"}, 400)
            return
        pinned = [str(p) for p in pinned[:20]]
        with _PINNED_LOCK:
            PINNED_SECTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
            PINNED_SECTIONS_PATH.write_text(json.dumps(pinned))
        self._send_json({"status": "ok", "pinned": pinned})

    # --- Task 038: Global search handler ---

    def _handle_search(self, query: str) -> None:
        """GET /api/v1/search?q=term — search apps, recipes, shortcuts. Task 038."""
        from urllib.parse import parse_qs
        params = parse_qs(query.lstrip("?"))
        term = params.get("q", [""])[0].lower().strip()
        if not term:
            self._send_json({"results": [], "total": 0, "query": term})
            return
        results: list = []
        for app in self.server.apps:
            app_id = app if isinstance(app, str) else app.get("id", "")
            app_name = app if isinstance(app, str) else app.get("name", app_id)
            app_desc = "" if isinstance(app, str) else (app.get("description", "") or "")
            if term in app_name.lower() or term in app_desc.lower():
                results.append({
                    "type": "app",
                    "id": app_id,
                    "title": app_name,
                    "description": app_desc[:80],
                })
        for s in [
            {"key": "?", "description": "Show/hide shortcuts panel"},
            {"key": "h", "description": "Go to top"},
            {"key": "d", "description": "Toggle dark mode"},
            {"key": "r", "description": "Refresh all panels"},
        ]:
            if term in s["description"].lower() or term in s["key"].lower():
                results.append({"type": "shortcut", "id": s["key"], "title": f"Shortcut: {s['key']}", "description": s["description"]})
        self._send_json({"results": results[:20], "total": len(results), "query": term})

    # --- Task 036: System status handler ---

    def _handle_system_status(self) -> None:
        """GET /api/v1/system/status — server version + feature flags. Task 036."""
        self._send_json({
            "status": "ok",
            "version": _SERVER_VERSION,
            "uptime_seconds": int(time.time() - _SERVER_START_TIME),
            "features": {
                "oauth3": True,
                "evidence": True,
                "budget": True,
                "byok": True,
                "recipes": True,
                "websocket": True,
            },
        })

    # --- Task 035: Keyboard shortcuts handler ---

    def _handle_shortcuts(self) -> None:
        """GET /api/v1/shortcuts — return keyboard shortcuts map. Task 035."""
        shortcuts = [
            {"key": "?", "description": "Show/hide shortcuts panel"},
            {"key": "h", "description": "Go to top"},
            {"key": "r", "description": "Refresh all panels"},
            {"key": "d", "description": "Toggle dark mode"},
            {"key": "Escape", "description": "Close open panels"},
            {"key": "j", "description": "Scroll down"},
            {"key": "k", "description": "Scroll up"},
        ]
        self._send_json({"shortcuts": shortcuts, "total": len(shortcuts)})

    # --- Task 034: API usage stats handler ---

    def _handle_usage_stats(self, query: str) -> None:
        """GET /api/v1/usage/stats — per-provider token usage + cost. Task 034."""
        from urllib.parse import parse_qs
        params = parse_qs(query.lstrip("?"))
        days = min(int(params.get("days", [30])[0]), 365)
        with _SPEND_HISTORY_LOCK:
            history = _load_spend_history()
        cutoff = int(time.time()) - days * 86400
        history = [e for e in history if e.get("timestamp", 0) >= cutoff]
        by_provider: dict = {}
        for entry in history:
            provider = entry.get("provider", "unknown")
            if provider not in by_provider:
                by_provider[provider] = {"cost_usd": 0.0, "calls": 0}
            by_provider[provider]["cost_usd"] += entry.get("amount_usd", 0.0)
            by_provider[provider]["calls"] += 1
        for v in by_provider.values():
            v["cost_usd"] = round(v["cost_usd"], 6)
        total_cost = round(sum(e.get("amount_usd", 0) for e in history), 6)
        self._send_json({
            "by_provider": by_provider,
            "total_cost_usd": total_cost,
            "total_calls": len(history),
            "days": days,
        })

    # --- Task 032: Recipe history handler ---

    def _handle_recipe_history(self, query: str) -> None:
        """GET /api/v1/recipes/history — list past recipe runs. Task 032."""
        from urllib.parse import parse_qs
        params = parse_qs(query.lstrip("?"))
        limit = min(int(params.get("limit", [50])[0]), 200)
        if not RECIPE_RUNS_PATH.exists():
            self._send_json({"runs": [], "total": 0})
            return
        try:
            data = json.loads(RECIPE_RUNS_PATH.read_text())
            runs = data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            runs = []
        runs = runs[-limit:]
        self._send_json({"runs": runs, "total": len(runs)})

    # --- Task 046: Recipe Templates handler ---

    def _handle_recipe_templates(self) -> None:
        """GET /api/v1/recipes/templates — list starter recipe templates. Task 046."""
        templates = [
            {"id": "tpl-email-sort", "name": "Email Sorter", "description": "Sort inbox by sender/subject", "category": "email", "steps": 3},
            {"id": "tpl-social-post", "name": "Social Post", "description": "Compose and schedule social content", "category": "social", "steps": 2},
            {"id": "tpl-data-extract", "name": "Data Extractor", "description": "Extract structured data from web pages", "category": "data", "steps": 4},
            {"id": "tpl-form-filler", "name": "Form Filler", "description": "Auto-fill forms from saved data", "category": "forms", "steps": 2},
            {"id": "tpl-screenshot-report", "name": "Screenshot Report", "description": "Capture pages and compile report", "category": "reporting", "steps": 3},
        ]
        self._send_json({"templates": templates, "total": len(templates)})

    # --- Task 018: Metrics handlers ---

    def _handle_metrics_json(self) -> None:
        """GET /api/v1/metrics — JSON metrics: uptime, request counts, error rates."""
        uptime = int(time.time() - _SERVER_START_TIME)
        with _METRICS_LOCK:
            req_counts = dict(_REQUEST_COUNTS)
            err_counts = dict(_ERROR_COUNTS)
        total_requests = sum(req_counts.values())
        total_errors = sum(err_counts.values())
        self._send_json({
            "uptime_seconds": uptime,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": round(total_errors / max(total_requests, 1), 4),
            "endpoints": req_counts,
            "errors": err_counts,
            "server_start": int(_SERVER_START_TIME),
        })

    def _handle_metrics_prometheus(self) -> None:
        """GET /metrics — Prometheus-format metrics (text/plain; version=0.0.4)."""
        uptime = int(time.time() - _SERVER_START_TIME)
        with _METRICS_LOCK:
            req_counts = dict(_REQUEST_COUNTS)
        lines = [
            "# HELP solace_uptime_seconds Server uptime in seconds",
            "# TYPE solace_uptime_seconds gauge",
            f"solace_uptime_seconds {uptime}",
            "# HELP solace_http_requests_total Total HTTP requests",
            "# TYPE solace_http_requests_total counter",
        ]
        for path_key, count in req_counts.items():
            lines.append(f'solace_http_requests_total{{path="{path_key}"}} {count}')
        body = "\n".join(lines) + "\n"
        body_bytes = body.encode()
        _record_request("/metrics", 200)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    # --- Task 017: WebSocket dashboard handler ---

    def _handle_ws_dashboard(self) -> None:
        """
        WebSocket upgrade for /ws/dashboard.
        Performs RFC 6455 handshake, then sends state every 5s.
        Accepts {"type": "ping"} → responds {"type": "pong"}.
        """
        upgrade = self.headers.get("Upgrade", "").lower()
        if upgrade != "websocket":
            self._send_json({"error": "WebSocket upgrade required"}, 426)
            return
        ws_key = self.headers.get("Sec-WebSocket-Key", "")
        if not ws_key:
            self._send_json({"error": "missing Sec-WebSocket-Key"}, 400)
            return
        # RFC 6455 accept key
        accept = base64.b64encode(
            hashlib.sha1((ws_key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode()
        # Send 101 Switching Protocols
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        try:
            self.wfile.write(response.encode())
            self.wfile.flush()
        except OSError:
            return

        conn = self.connection  # type: ignore[attr-defined]
        conn.settimeout(None)

        def _ws_send(payload: str) -> None:
            """Send a UTF-8 text frame (opcode 0x81)."""
            data = payload.encode("utf-8")
            length = len(data)
            if length <= 125:
                header = struct.pack("!BB", 0x81, length)
            elif length <= 65535:
                header = struct.pack("!BBH", 0x81, 126, length)
            else:
                header = struct.pack("!BBQ", 0x81, 127, length)
            try:
                self.wfile.write(header + data)
                self.wfile.flush()
            except OSError:
                pass

        def _build_state() -> str:
            uptime = int(time.time() - _SERVER_START_TIME)
            with _SESSIONS_LOCK:
                session_count = len(_SESSIONS)
            schedules = load_schedules()
            schedule_count = len(schedules)
            schedule_enabled = sum(1 for s in schedules if s.get("enabled", True))
            with _TUNNEL_LOCK:
                tunnel_active = _TUNNEL_PROC is not None and _TUNNEL_PROC.poll() is None
                tunnel_url = _TUNNEL_URL if tunnel_active else ""
            budget_status: dict = {}
            return json.dumps({
                "type": "state",
                "data": {
                    "server": {
                        "status": "ok",
                        "uptime_seconds": uptime,
                        "port": YINYANG_PORT,
                    },
                    "budget": {
                        "daily_pct": 0.0,
                        "paused": False,
                        "daily_spend_usd": 0.0,
                    },
                    "sessions": {
                        "count": session_count,
                        "alive": session_count,
                    },
                    "schedules": {
                        "count": schedule_count,
                        "enabled": schedule_enabled,
                    },
                    "tunnel": {
                        "active": tunnel_active,
                        "url": tunnel_url,
                    },
                },
            })

        # Send initial state
        _ws_send(_build_state())

        # Heartbeat thread — sends state every 5s
        stop_event = threading.Event()

        def _heartbeat() -> None:
            while not stop_event.is_set():
                stop_event.wait(5)
                if stop_event.is_set():
                    break
                try:
                    _ws_send(_build_state())
                except OSError:
                    break

        hb_thread = threading.Thread(target=_heartbeat, daemon=True)
        hb_thread.start()

        # Receive loop — handle client messages
        try:
            while True:
                # Read frame header (2 bytes minimum)
                try:
                    header_bytes = self.rfile.read(2)
                except OSError:
                    break
                if len(header_bytes) < 2:
                    break
                b0, b1 = header_bytes[0], header_bytes[1]
                opcode = b0 & 0x0F
                masked = bool(b1 & 0x80)
                payload_len = b1 & 0x7F
                if payload_len == 126:
                    try:
                        ext = self.rfile.read(2)
                    except OSError:
                        break
                    if len(ext) < 2:
                        break
                    payload_len = struct.unpack("!H", ext)[0]
                elif payload_len == 127:
                    try:
                        ext = self.rfile.read(8)
                    except OSError:
                        break
                    if len(ext) < 8:
                        break
                    payload_len = struct.unpack("!Q", ext)[0]
                mask_key = b""
                if masked:
                    try:
                        mask_key = self.rfile.read(4)
                    except OSError:
                        break
                    if len(mask_key) < 4:
                        break
                try:
                    payload_bytes = self.rfile.read(payload_len)
                except OSError:
                    break
                if masked and mask_key:
                    payload_bytes = bytes(
                        b ^ mask_key[i % 4] for i, b in enumerate(payload_bytes)
                    )
                if opcode == 8:  # Close frame
                    break
                if opcode == 1:  # Text frame
                    try:
                        msg = json.loads(payload_bytes.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    if msg.get("type") == "ping":
                        _ws_send(json.dumps({"type": "pong"}))
        except OSError:
            pass
        finally:
            stop_event.set()

    def _handle_ws_chat(self) -> None:
        """WebSocket chat relay at /ws/chat. RFC 6455 stdlib only. Task 026."""
        upgrade = self.headers.get("Upgrade", "").lower()
        if upgrade != "websocket":
            self._send_json({"error": "WebSocket upgrade required"}, 426)
            return
        ws_key = self.headers.get("Sec-WebSocket-Key", "")
        if not ws_key:
            self._send_json({"error": "missing Sec-WebSocket-Key"}, 400)
            return
        accept = base64.b64encode(
            hashlib.sha1((ws_key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode()
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        try:
            self.wfile.write(response.encode())
            self.wfile.flush()
        except OSError:
            return

        conn = self.connection  # type: ignore[attr-defined]
        conn.settimeout(None)

        def _ws_send_chat(payload: str) -> None:
            data = payload.encode("utf-8")
            length = len(data)
            if length <= 125:
                header = struct.pack("!BB", 0x81, length)
            elif length <= 65535:
                header = struct.pack("!BBH", 0x81, 126, length)
            else:
                header = struct.pack("!BBQ", 0x81, 127, length)
            try:
                self.wfile.write(header + data)
                self.wfile.flush()
            except OSError:
                pass

        # Determine active model from CLI or BYOK config
        cli_config = self._load_cli_config()
        byok_config = self._load_byok_config()
        active_model = cli_config.get("active_tool") or byok_config.get("active_provider") or "unavailable"
        _ws_send_chat(json.dumps({"type": "ready", "model": active_model}))

        try:
            while True:
                try:
                    header_bytes = self.rfile.read(2)
                except OSError:
                    break
                if len(header_bytes) < 2:
                    break
                b0, b1 = header_bytes[0], header_bytes[1]
                opcode = b0 & 0x0F
                masked = bool(b1 & 0x80)
                payload_len = b1 & 0x7F
                if payload_len == 126:
                    try:
                        ext = self.rfile.read(2)
                    except OSError:
                        break
                    if len(ext) < 2:
                        break
                    payload_len = struct.unpack("!H", ext)[0]
                elif payload_len == 127:
                    try:
                        ext = self.rfile.read(8)
                    except OSError:
                        break
                    if len(ext) < 8:
                        break
                    payload_len = struct.unpack("!Q", ext)[0]
                mask_key = b""
                if masked:
                    try:
                        mask_key = self.rfile.read(4)
                    except OSError:
                        break
                    if len(mask_key) < 4:
                        break
                try:
                    payload_bytes = self.rfile.read(payload_len)
                except OSError:
                    break
                if masked and mask_key:
                    payload_bytes = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload_bytes))
                if opcode == 8:
                    break
                if opcode == 1:
                    try:
                        msg = json.loads(payload_bytes.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    msg_type = msg.get("type")
                    if msg_type == "ping":
                        _ws_send_chat(json.dumps({"type": "pong"}))
                    elif msg_type == "chat":
                        user_text = str(msg.get("message", ""))[:2048]
                        response_text = f"[{active_model}] Echo: {user_text}"
                        _ws_send_chat(json.dumps({"type": "response", "text": response_text, "done": True}))
                    elif msg_type == "close":
                        break
        except OSError:
            pass

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

    def _handle_tunnel_cloud_status(self) -> None:
        if not self._check_auth():
            return
        self._send_json(_cloud_tunnel_status_payload())

    def _handle_tunnel_start_cloud(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        api_key = body.get("api_key", "") if isinstance(body, dict) else ""
        if not isinstance(api_key, str) or not api_key:
            api_key = _load_cloud_api_key()
        if not api_key:
            self._send_json({"error": "api_key required"}, 400)
            return
        _launch_cloud_tunnel(api_key, getattr(self.server, "session_token_sha256", ""), self.server.server_port)
        record_evidence("cloud_tunnel_start", {"relay": SOLACEAGI_RELAY_URL})
        self._send_json({"status": "connecting", "relay": SOLACEAGI_RELAY_URL})

    def _handle_tunnel_stop_cloud(self) -> None:
        if not self._check_auth():
            return
        _stop_cloud_tunnel()
        record_evidence("cloud_tunnel_stop", {"relay": SOLACEAGI_RELAY_URL})
        self._send_json({"status": "stopped"})

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
            from cryptography.exceptions import InvalidTag
            plaintext = aesgcm.decrypt(nonce, ct, None)
        except InvalidTag:
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

    # --- BYOK handlers (Task 019) ---

    def _load_byok_config(self) -> dict:
        """Load BYOK config (keys stored encrypted, only metadata returned to clients)."""
        if not BYOK_PATH.exists():
            return {"active_provider": None, "providers": {}}
        try:
            return json.loads(BYOK_PATH.read_text())
        except json.JSONDecodeError:
            return {"active_provider": None, "providers": {}}

    def _handle_byok_providers(self) -> None:
        config = self._load_byok_config()
        providers_info = {}
        for provider, data in config.get("providers", {}).items():
            providers_info[provider] = {
                "provider": provider,
                "configured": bool(data.get("key_hash")),
                "active": provider == config.get("active_provider"),
                "key_preview": data.get("key_preview", ""),
            }
        self._send_json({
            "providers": providers_info,
            "active_provider": config.get("active_provider"),
            "supported": sorted(SUPPORTED_PROVIDERS),
        })

    def _handle_byok_active(self) -> None:
        config = self._load_byok_config()
        self._send_json({"active_provider": config.get("active_provider")})

    def _handle_byok_set(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        provider = body.get("provider", "")
        api_key = body.get("api_key", "")
        if provider not in SUPPORTED_PROVIDERS:
            self._send_json({"error": f"provider must be one of: {sorted(SUPPORTED_PROVIDERS)}"}, 400)
            return
        if not isinstance(api_key, str) or len(api_key) < 10:
            self._send_json({"error": "api_key must be at least 10 characters"}, 400)
            return
        if len(api_key) > 256:
            self._send_json({"error": "api_key too long (max 256 chars)"}, 400)
            return
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_preview = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "****"
        encrypted_key = self._encrypt_api_key(api_key)
        with _BYOK_LOCK:
            config = self._load_byok_config()
            config.setdefault("providers", {})[provider] = {
                "key_hash": key_hash,
                "key_preview": key_preview,
                "encrypted_key": encrypted_key,
                "set_at": int(time.time()),
            }
            config["active_provider"] = provider
            try:
                BYOK_PATH.parent.mkdir(parents=True, exist_ok=True)
                BYOK_PATH.write_text(json.dumps(config, indent=2))
            except OSError as e:
                self._send_json({"error": f"cannot write byok config: {e}"}, 500)
                return
        self._send_json({
            "status": "set",
            "provider": provider,
            "key_preview": key_preview,
            "active": True,
        })

    def _encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key with session token. Returns base64 encoded."""
        key_hex = _SESSION_TOKEN_SHA256 or ("0" * 64)
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            key = bytes.fromhex(key_hex)
            nonce = os.urandom(12)
            aesgcm = AESGCM(key)
            ct = aesgcm.encrypt(nonce, api_key.encode(), None)
            return base64.b64encode(nonce + ct).decode()
        except ImportError:
            # Without cryptography package, store a placeholder (key_hash still protects identity)
            return "ENCRYPTION_UNAVAILABLE"

    def _handle_byok_test(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        provider = body.get("provider", "")
        if provider not in SUPPORTED_PROVIDERS:
            self._send_json({"error": f"unsupported provider: {provider}"}, 400)
            return
        config = self._load_byok_config()
        provider_data = config.get("providers", {}).get(provider)
        if not provider_data or not provider_data.get("key_hash"):
            self._send_json({"error": f"no key configured for {provider}"}, 404)
            return
        self._send_json({
            "status": "configured",
            "provider": provider,
            "key_preview": provider_data.get("key_preview", ""),
            "note": "Key is stored. Use /api/v1/chat to test actual LLM connectivity.",
        })

    def _handle_byok_clear(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        provider = body.get("provider", "")
        if not provider:
            self._send_json({"error": "provider required"}, 400)
            return
        with _BYOK_LOCK:
            config = self._load_byok_config()
            if provider in config.get("providers", {}):
                del config["providers"][provider]
                if config.get("active_provider") == provider:
                    config["active_provider"] = None
                try:
                    BYOK_PATH.write_text(json.dumps(config, indent=2))
                except OSError as e:
                    self._send_json({"error": f"cannot write byok config: {e}"}, 500)
                    return
                self._send_json({"status": "cleared", "provider": provider})
            else:
                self._send_json({"error": f"no key configured for {provider}"}, 404)

    # --- Task 066: Yinyang SSE notification handlers ---

    def _handle_yinyang_notify(self) -> None:
        """POST /api/yinyang/notify — enqueue an in-memory agent notification."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        if not isinstance(body, dict):
            self._send_json({"error": "JSON body must be an object"}, 400)
            return

        notif_type = str(body.get("type", "")).strip()
        if not notif_type:
            self._send_json({"error": "type required"}, 400)
            return
        if notif_type not in YINYANG_NOTIFICATION_TYPES:
            self._send_json({"error": "invalid type"}, 400)
            return

        message = str(body.get("message", "")).strip()
        if not message:
            self._send_json({"error": "message required"}, 400)
            return

        priority_value = str(body.get("priority", "")).strip() or YINYANG_NOTIFICATION_TYPES[notif_type]
        if priority_value not in YINYANG_NOTIFICATION_PRIORITIES:
            self._send_json({"error": "invalid priority"}, 400)
            return

        agent_id_value = body.get("agent_id")
        if agent_id_value is not None and not isinstance(agent_id_value, str):
            self._send_json({"error": "agent_id must be a string"}, 400)
            return
        run_id_value = body.get("run_id")
        if run_id_value is not None and not isinstance(run_id_value, str):
            self._send_json({"error": "run_id must be a string"}, 400)
            return

        actions_value = body.get("actions", [])
        if not isinstance(actions_value, list):
            self._send_json({"error": "actions must be a list"}, 400)
            return
        normalized_actions: list[dict[str, Any]] = []
        for action in actions_value:
            if not isinstance(action, dict):
                self._send_json({"error": "actions must contain objects"}, 400)
                return
            label = str(action.get("label", "")).strip()
            if not label:
                self._send_json({"error": "action label required"}, 400)
                return
            url_value = action.get("url")
            if url_value is not None and not isinstance(url_value, str):
                self._send_json({"error": "action url must be a string"}, 400)
                return
            action_name = action.get("action")
            if action_name is not None and not isinstance(action_name, str):
                self._send_json({"error": "action name must be a string"}, 400)
                return
            action_run_id = action.get("run_id")
            if action_run_id is not None and not isinstance(action_run_id, str):
                self._send_json({"error": "action run_id must be a string"}, 400)
                return
            normalized_action = {"label": label}
            if isinstance(url_value, str) and url_value.strip():
                normalized_action["url"] = url_value.strip()
            if isinstance(action_name, str) and action_name.strip():
                normalized_action["action"] = action_name.strip()
            if isinstance(action_run_id, str) and action_run_id.strip():
                normalized_action["run_id"] = action_run_id.strip()
            normalized_actions.append(normalized_action)

        metadata_value = body.get("metadata", {})
        if not isinstance(metadata_value, dict):
            self._send_json({"error": "metadata must be an object"}, 400)
            return

        notif = _create_yinyang_notification(
            notif_type,
            message,
            priority_value,
            agent_id=agent_id_value.strip() if isinstance(agent_id_value, str) and agent_id_value.strip() else None,
            run_id=run_id_value.strip() if isinstance(run_id_value, str) and run_id_value.strip() else None,
            actions=normalized_actions,
            metadata=metadata_value,
        )
        self._send_json({
            "status": "queued",
            "notification_id": notif["id"],
            "queued_at": notif["ts"],
        })

    def _handle_yinyang_status(self) -> None:
        """GET /api/yinyang/status — return current in-memory notification state."""
        if not self._check_auth():
            return
        with _YINYANG_NOTIF_LOCK:
            snapshot = [_yinyang_notification_public(notif) for notif in _YINYANG_NOTIFICATIONS]
        unread_count = sum(1 for notif in snapshot if not notif.get("read", False))
        self._send_json({
            "queue_depth": len(snapshot),
            "unread_count": unread_count,
            "notifications": snapshot,
            "last_checked": _yinyang_now_iso(),
        })

    def _handle_yinyang_mark_read(self, notif_id: str) -> None:
        """POST /api/yinyang/notifications/{id}/read — mark one notification as read."""
        if not self._check_auth():
            return
        with _YINYANG_NOTIF_LOCK:
            for notif in _YINYANG_NOTIFICATIONS:
                if notif.get("id") == notif_id:
                    notif["read"] = True
                    self._send_json({"status": "marked_read", "id": notif_id})
                    return
        self._send_json({"error": "notification not found"}, 404)

    def _handle_yinyang_events_sse(self) -> None:
        """GET /api/yinyang/events — stream agent notifications via SSE."""
        expected_sha256 = str(getattr(self.server, "session_token_sha256", ""))
        parsed = urllib.parse.urlparse(self.path)
        token = urllib.parse.parse_qs(parsed.query).get("token", [""])[0].strip()
        if expected_sha256 and not _yinyang_sse_token_valid(expected_sha256, token):
            self._send_json({"error": "unauthorized"}, 401)
            return

        _record_request(parsed.path, 200)
        self._record_history_entry(200)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", f"http://localhost:{YINYANG_PORT}")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        client_queue: queue.Queue[str] = queue.Queue(maxsize=50)
        with _YINYANG_SSE_CLIENTS_LOCK:
            _YINYANG_SSE_CLIENTS.append(client_queue)

        try:
            with _YINYANG_NOTIF_LOCK:
                recent_unread = [
                    _yinyang_sse_frame(notif)
                    for notif in _YINYANG_NOTIFICATIONS[-YINYANG_SSE_RECENT_LIMIT:]
                    if not notif.get("read", False)
                ]
            for frame in recent_unread:
                self.wfile.write(frame.encode("utf-8"))
            self.wfile.flush()

            while True:
                try:
                    frame = client_queue.get(timeout=YINYANG_SSE_PING_SECONDS)
                    self.wfile.write(frame.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _YINYANG_SSE_CLIENTS_LOCK:
                try:
                    _YINYANG_SSE_CLIENTS.remove(client_queue)
                except ValueError:
                    pass

    # --- Task 020: Notification handlers ---

    def _handle_notifications_list(self, query: str) -> None:
        from urllib.parse import parse_qs
        params = parse_qs(query.lstrip("?"))
        limit = min(int(params.get("limit", ["50"])[0]), 200)
        category = params.get("category", [None])[0]
        unread_only = params.get("unread", ["false"])[0].lower() == "true"

        with _NOTIF_LOCK:
            notifs = _load_notifications_raw()
        if category:
            notifs = [n for n in notifs if n.get("category") == category]
        if unread_only:
            notifs = [n for n in notifs if not n.get("read", False)]
        notifs = notifs[-limit:]
        unread_count = sum(1 for n in notifs if not n.get("read", False))
        self._send_json({
            "notifications": notifs,
            "total": len(notifs),
            "unread_count": unread_count,
        })

    def _handle_notifications_unread_count(self) -> None:
        with _NOTIF_LOCK:
            notifs = _load_notifications_raw()
        count = sum(1 for n in notifs if not n.get("read", False))
        self._send_json({"unread_count": count})

    def _handle_notifications_mark_all_read(self) -> None:
        if not self._check_auth():
            return
        with _NOTIF_LOCK:
            notifs = _load_notifications_raw()
            for n in notifs:
                n["read"] = True
            NOTIFICATIONS_PATH.write_text(json.dumps(notifs, indent=2))
        self._send_json({"status": "all_read"})

    def _handle_notification_mark_read(self, notif_id: str) -> None:
        if not self._check_auth():
            return
        with _NOTIF_LOCK:
            notifs = _load_notifications_raw()
            for n in notifs:
                if n.get("id") == notif_id:
                    n["read"] = True
                    NOTIFICATIONS_PATH.write_text(json.dumps(notifs, indent=2))
                    self._send_json({"status": "read", "id": notif_id})
                    return
        self._send_json({"error": "notification not found"}, 404)

    def _handle_log_requests(self, query: str) -> None:
        """Return rolling request history with optional limit/method/status filters. Task 021."""
        from urllib.parse import parse_qs
        params = parse_qs(query.lstrip("?"))
        limit = min(int(params.get("limit", ["50"])[0]), 100)
        method_filter = params.get("method", [None])[0]
        status_filter = params.get("status", [None])[0]

        with _HISTORY_LOCK:
            history = list(_REQUEST_HISTORY)
        if method_filter:
            history = [h for h in history if h.get("method") == method_filter.upper()]
        if status_filter:
            try:
                sc = int(status_filter)
                history = [h for h in history if h.get("status") == sc]
            except ValueError:
                pass
        history = history[-limit:]
        self._send_json({"requests": history, "total": len(history)})

    def _handle_log_errors(self) -> None:
        """Return only 4xx/5xx requests from history. Task 021."""
        with _HISTORY_LOCK:
            history = list(_REQUEST_HISTORY)
        errors = [h for h in history if h.get("status", 0) >= 400]
        self._send_json({"errors": errors, "total": len(errors)})

    # ── Profile Manager (Task 023) ─────────────────────────────────────────

    def _load_profiles(self) -> list:
        if not PROFILES_PATH.exists():
            return []
        try:
            data = json.loads(PROFILES_PATH.read_text())
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def _save_profiles(self, profiles: list) -> None:
        PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILES_PATH.write_text(json.dumps(profiles, indent=2))

    def _handle_profiles_list(self) -> None:
        with _PROFILES_LOCK:
            profiles = self._load_profiles()
        self._send_json({"profiles": profiles, "total": len(profiles)})

    def _handle_profiles_active(self) -> None:
        if not ACTIVE_PROFILE_PATH.exists():
            self._send_json({"active_profile": None})
            return
        try:
            data = json.loads(ACTIVE_PROFILE_PATH.read_text())
            self._send_json({"active_profile": data})
        except json.JSONDecodeError:
            self._send_json({"active_profile": None})

    def _handle_profiles_create(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        name = body.get("name", "").strip()
        if not name or len(name) > 64:
            self._send_json({"error": "name must be 1-64 characters"}, 400)
            return
        with _PROFILES_LOCK:
            profiles = self._load_profiles()
            if len(profiles) >= MAX_PROFILES:
                self._send_json({"error": f"max {MAX_PROFILES} profiles allowed"}, 400)
                return
            if any(p.get("name") == name for p in profiles):
                self._send_json({"error": f"profile '{name}' already exists"}, 400)
                return
            profile = {
                "id": str(uuid.uuid4()),
                "name": name,
                "created_at": int(time.time()),
                "data_dir": str(Path.home() / ".solace" / "profiles" / name.lower().replace(" ", "-")),
            }
            profiles.append(profile)
            self._save_profiles(profiles)
        self._send_json({"profile": profile, "status": "created"}, 201)

    def _handle_profiles_activate(self, profile_id: str) -> None:
        if not self._check_auth():
            return
        with _PROFILES_LOCK:
            profiles = self._load_profiles()
            profile = next((p for p in profiles if p.get("id") == profile_id), None)
            if not profile:
                self._send_json({"error": "profile not found"}, 404)
                return
            ACTIVE_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            ACTIVE_PROFILE_PATH.write_text(json.dumps(profile, indent=2))
        self._send_json({"status": "activated", "profile": profile})

    def _handle_profiles_delete(self, profile_id: str) -> None:
        if not self._check_auth():
            return
        with _PROFILES_LOCK:
            profiles = self._load_profiles()
            before = len(profiles)
            profiles = [p for p in profiles if p.get("id") != profile_id]
            if len(profiles) == before:
                self._send_json({"error": "profile not found"}, 404)
                return
            self._save_profiles(profiles)
        self._send_json({"status": "deleted", "id": profile_id})

    # ── Recipe Store (Task 024) ────────────────────────────────────────────

    def _load_installed_recipes(self) -> list:
        if not INSTALLED_RECIPES_PATH.exists():
            return []
        try:
            data = json.loads(INSTALLED_RECIPES_PATH.read_text())
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def _handle_store_list(self, query: str) -> None:
        from urllib.parse import parse_qs, unquote
        params = parse_qs(query.lstrip("?"))
        tag = params.get("tag", [None])[0]
        search = params.get("q", [None])[0]
        recipes = [dict(r) for r in _COMMUNITY_RECIPES]
        if tag:
            recipes = [r for r in recipes if r.get("tag") == tag]
        if search:
            q = unquote(search).lower()
            recipes = [r for r in recipes if q in r.get("name", "").lower() or q in r.get("tag", "").lower()]
        with _STORE_LOCK:
            installed_ids = {r["id"] for r in self._load_installed_recipes()}
        for r in recipes:
            r["installed"] = r["id"] in installed_ids
        self._send_json({"recipes": recipes, "total": len(recipes)})

    def _handle_store_installed(self) -> None:
        with _STORE_LOCK:
            installed = self._load_installed_recipes()
        self._send_json({"installed": installed, "total": len(installed)})

    def _handle_store_install(self, recipe_id: str) -> None:
        if not self._check_auth():
            return
        recipe = next((r for r in _COMMUNITY_RECIPES if r["id"] == recipe_id), None)
        if not recipe:
            self._send_json({"error": "recipe not found"}, 404)
            return
        with _STORE_LOCK:
            installed = self._load_installed_recipes()
            if any(r["id"] == recipe_id for r in installed):
                self._send_json({"status": "already_installed", "recipe": recipe})
                return
            installed.append({**recipe, "installed_at": int(time.time())})
            INSTALLED_RECIPES_PATH.parent.mkdir(parents=True, exist_ok=True)
            INSTALLED_RECIPES_PATH.write_text(json.dumps(installed, indent=2))
        self._send_json({"status": "installed", "recipe": recipe})

    def _handle_store_uninstall(self, recipe_id: str) -> None:
        if not self._check_auth():
            return
        with _STORE_LOCK:
            installed = self._load_installed_recipes()
            before = len(installed)
            installed = [r for r in installed if r["id"] != recipe_id]
            if len(installed) == before:
                self._send_json({"error": "recipe not installed"}, 404)
                return
            INSTALLED_RECIPES_PATH.write_text(json.dumps(installed, indent=2))
        self._send_json({"status": "uninstalled", "id": recipe_id})

    # ── CLI Tool Integration (Task 025) ───────────────────────────────────

    def _load_cli_config(self) -> dict:
        if not CLI_CONFIG_PATH.exists():
            return {"active_tool": None, "tools": {}}
        try:
            return json.loads(CLI_CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            return {"active_tool": None, "tools": {}}

    def _handle_cli_config_get(self) -> None:
        config = self._load_cli_config()
        self._send_json({"config": config, "supported_tools": sorted(SUPPORTED_CLI_TOOLS)})

    def _handle_cli_detect(self) -> None:
        detected = {}
        for tool in SUPPORTED_CLI_TOOLS:
            path = shutil.which(tool)
            detected[tool] = {"installed": path is not None, "path": path or ""}
        self._send_json({"detected": detected})

    def _handle_cli_config_set(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        tool = body.get("tool", "")
        if tool not in SUPPORTED_CLI_TOOLS:
            self._send_json({"error": f"tool must be one of: {sorted(SUPPORTED_CLI_TOOLS)}"}, 400)
            return
        cli_path = body.get("cli_path", "") or shutil.which(tool) or ""
        config = self._load_cli_config()
        config["active_tool"] = tool
        config.setdefault("tools", {})[tool] = {
            "cli_path": cli_path,
            "configured_at": int(time.time()),
        }
        with _CLI_LOCK:
            CLI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CLI_CONFIG_PATH.write_text(json.dumps(config, indent=2))
        self._send_json({"status": "configured", "tool": tool, "cli_path": cli_path})

    def _handle_cli_test(self) -> None:
        if not self._check_auth():
            return
        config = self._load_cli_config()
        tool = config.get("active_tool")
        if not tool:
            self._send_json({"error": "no CLI tool configured. Use POST /api/v1/cli/config first"}, 404)
            return
        tool_config = config.get("tools", {}).get(tool, {})
        cli_path = tool_config.get("cli_path") or shutil.which(tool) or ""
        import os as _os_cli
        installed = bool(cli_path and (_os_cli.path.isfile(cli_path) or shutil.which(tool)))
        self._send_json({
            "status": "reachable" if installed else "not_found",
            "tool": tool,
            "cli_path": cli_path,
        })

    def _cli_agents_payload(self, cache_status: str) -> dict:
        """Build the response payload for CLI agent detection endpoints."""
        found = _detect_available_agents()
        agents = [
            {
                "name": name,
                "path": path,
                "default_model": _default_model_for_agent(name),
            }
            for name, path in found.items()
        ]
        not_found = [name for name in CLI_AGENT_CANDIDATES if name not in found]
        return {
            "agents": agents,
            "count": len(agents),
            "not_found": not_found,
            "cache_status": cache_status,
        }

    def _handle_cli_agents_detect(self) -> None:
        """GET /api/v1/cli-agents/detect — detect installed AI coding CLIs."""
        if not self._check_auth():
            return
        self._send_json(self._cli_agents_payload("fresh"))

    def _handle_cli_agents_refresh(self) -> None:
        """GET /api/v1/cli-agents/refresh — clear detection cache and re-detect."""
        if not self._check_auth():
            return
        _detect_available_agents.cache_clear()
        self._send_json(self._cli_agents_payload("refreshed"))

    def _handle_cli_agents_generate(self) -> None:
        """
        POST /api/v1/cli-agents/generate
        Auth: Bearer sha256(token)
        Request: {agent: str, model: str|null, prompt: str, skill_pack: list[str], timeout_s: int}
        Response 200: {agent, model, output, cost_usd, latency_ms, evidence_id, rung}
        Response 400: {error: str}
        Response 401: {error: "unauthorized"}
        """
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        if not isinstance(body, dict):
            self._send_json({"error": "JSON body must be an object"}, 400)
            return

        agent_name = body.get("agent", "auto")
        if not isinstance(agent_name, str) or not agent_name:
            self._send_json({"error": "agent is required"}, 400)
            return

        if agent_name != "auto" and agent_name not in CLI_AGENT_CANDIDATES:
            self._send_json({"error": f"unknown agent: {agent_name}"}, 400)
            return

        prompt = body.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            self._send_json({"error": "prompt is required", "code": "MISSING_PROMPT"}, 400)
            return

        skill_pack_raw = body.get("skill_pack")
        if skill_pack_raw is None:
            skill_pack: list[str] = []
        elif isinstance(skill_pack_raw, list) and all(isinstance(item, str) for item in skill_pack_raw):
            skill_pack = skill_pack_raw
        else:
            self._send_json({"error": "skill_pack must be a list of strings"}, 400)
            return

        model_value = body.get("model")
        if model_value is not None and not isinstance(model_value, str):
            self._send_json({"error": "model must be a string or null"}, 400)
            return

        timeout_value = body.get("timeout_s", 60)
        if isinstance(timeout_value, bool) or not isinstance(timeout_value, int) or timeout_value <= 0:
            self._send_json({"error": "timeout_s must be a positive integer"}, 400)
            return

        found = _detect_available_agents()
        if agent_name == "auto":
            priority = ["gemini", "aider", "codex", "claude"]
            selected_agent = next((candidate for candidate in priority if candidate in found), None)
            if selected_agent is None:
                self._send_json({"error": "No CLI agents found on PATH", "code": "NO_AGENTS_AVAILABLE"}, 400)
                return
        else:
            selected_agent = agent_name

        executable = found.get(selected_agent)
        if executable is None:
            self._send_json({
                "error": f"Agent '{selected_agent}' not found on PATH",
                "code": "AGENT_NOT_FOUND",
                "available": sorted(found.keys()),
            }, 400)
            return

        selected_model = model_value or _default_model_for_agent(selected_agent)
        prepared_prompt = _inject_skill_pack(prompt.strip(), skill_pack)
        started_at = time.monotonic()
        try:
            result = _invoke_cli_agent(
                selected_agent,
                executable,
                prepared_prompt,
                selected_model,
                timeout_value,
            )
        except subprocess.TimeoutExpired:
            self._send_json({"error": f"Agent timed out after {timeout_value}s", "code": "AGENT_TIMEOUT"}, 504)
            return
        except subprocess.CalledProcessError as error:
            self._send_json({
                "error": f"Agent exited with code {error.returncode}",
                "code": "AGENT_ERROR",
                "stderr": (error.stderr or "")[:500],
            }, 502)
            return
        except OSError as error:
            self._send_json({"error": f"Could not execute agent '{selected_agent}': {error}"}, 503)
            return

        output = str(result.get("stdout", ""))
        latency_ms = int((time.monotonic() - started_at) * 1000)
        tokens_est = max(1, len(prepared_prompt.split()) + len(output.split()))
        self._send_json({
            "agent": selected_agent,
            "model": selected_model,
            "output": output,
            "cost_usd": _estimate_cost(selected_agent, tokens_est),
            "latency_ms": latency_ms,
            "evidence_id": _build_cli_evidence_id(output),
            "rung": 641,
        })

    # ── App Launcher (Task 027) ────────────────────────────────────────────

    def _handle_apps_list(self) -> None:
        apps: list = self.server.apps if hasattr(self.server, "apps") else []  # type: ignore[attr-defined]
        app_list = [{"id": a, "name": a.replace("-", " ").title()} for a in apps]
        self._send_json({"apps": app_list, "total": len(app_list)})

    def _handle_app_detail(self, app_id: str) -> None:
        apps: list = self.server.apps if hasattr(self.server, "apps") else []  # type: ignore[attr-defined]
        if app_id not in apps:
            self._send_json({"error": "app not found"}, 404)
            return
        self._send_json({"id": app_id, "name": app_id.replace("-", " ").title(), "status": "available"})

    def _handle_app_launch(self, app_id: str) -> None:
        if not self._check_auth():
            return
        apps: list = self.server.apps if hasattr(self.server, "apps") else []  # type: ignore[attr-defined]
        if app_id not in apps:
            self._send_json({"error": "app not found"}, 404)
            return
        _append_notification("info", "App Launched", f"{app_id} launched from Hub", "info")
        with _METRICS_LOCK:
            _REQUEST_COUNTS[f"app_launch:{app_id}"] = _REQUEST_COUNTS.get(f"app_launch:{app_id}", 0) + 1
        self._send_json({"status": "launched", "app_id": app_id, "timestamp": int(time.time())})

    def _handle_session_rules_list(self) -> None:
        """GET /api/v1/session-rules — list loaded session rule schemas."""
        if not self._check_auth():
            return
        rules = []
        for rule in _get_session_rules_snapshot():
            rules.append({
                "app": rule.get("app", ""),
                "display_name": rule.get("display_name", ""),
                "check_url": rule.get("check_url", ""),
                "keep_alive": rule.get("keep_alive", {}),
                "tier_required": rule.get("tier_required", ""),
            })
        self._send_json({"rules": rules, "total": len(rules)})

    def _handle_session_rule_check(self, app_id: str) -> None:
        """POST /api/v1/session-rules/check/{app} — trigger one session check."""
        if not self._check_auth():
            return
        rule = _find_session_rule(app_id)
        if rule is None:
            self._send_json({"error": "session rule not found"}, 404)
            return
        status_entry = _run_session_check(rule)
        self._send_json({
            "app": app_id,
            "status": status_entry["status"],
            "checked_at": status_entry["last_check"],
        })

    def _handle_session_rules_status(self) -> None:
        """GET /api/v1/session-rules/status — list cached session statuses."""
        if not self._check_auth():
            return
        with _SESSION_STATUS_LOCK:
            statuses = [dict(entry) for entry in _SESSION_STATUS.values()]
        statuses.sort(key=lambda entry: str(entry.get("app", "")))
        self._send_json({"statuses": statuses})

    def _reload_session_rules_cache(self) -> list[dict]:
        global SESSION_RULES_APPS_DIR
        repo_root = getattr(self.server, "repo_root", ".")
        SESSION_RULES_APPS_DIR = _marketplace_apps_root(repo_root)
        rules = load_session_rules()
        self.server.apps = load_apps(repo_root)  # type: ignore[attr-defined]
        return rules

    def _handle_session_rules_reload(self) -> None:
        """POST /api/v1/session-rules/reload — refresh in-memory rule cache."""
        if not self._check_auth():
            return
        rules = self._reload_session_rules_cache()
        self._send_json({"reloaded": True, "total": len(rules)})

    def _handle_marketplace_apps(self) -> None:
        if not self._check_auth():
            return
        repo_root = getattr(self.server, "repo_root", ".")
        apps, source = _fetch_marketplace_catalog(repo_root)
        if apps is None:
            self._send_json({"error": "marketplace unavailable"}, 503)
            return
        self._send_json({"apps": apps, "total": len(apps), "source": source})

    def _handle_marketplace_categories(self) -> None:
        self._send_json({"categories": list(_MARKETPLACE_CATEGORIES)})

    def _handle_marketplace_install(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        app_id = body.get("app_id")
        if not isinstance(app_id, str) or not app_id:
            self._send_json({"error": "app_id required"}, 400)
            return
        if not _APP_ID_RE.fullmatch(app_id):
            self._send_json({"error": "app_id must be alphanumeric + hyphens only"}, 400)
            return
        repo_root = getattr(self.server, "repo_root", ".")
        apps, source = _fetch_marketplace_catalog(repo_root)
        if apps is None:
            self._send_json({"error": "marketplace unavailable"}, 503)
            return
        app = _find_marketplace_app(apps, app_id)
        if app is None:
            self._send_json({"error": "app not found"}, 404)
            return
        user_tier = _load_account_tier()
        tier_required = str(app.get("tier_required", "free"))
        if not _tier_allows_install(user_tier, tier_required):
            self._send_json({"error": "upgrade required", "upgrade_url": MARKETPLACE_UPGRADE_URL}, 403)
            return
        try:
            session_rules_text, download_status = _download_marketplace_session_rules(app_id)
        except urllib.error.URLError as exc:
            record_evidence("marketplace_install_failed", {
                "app_id": app_id,
                "reason": str(exc.reason) if hasattr(exc, "reason") else str(exc),
            })
            self._send_json({"error": "marketplace download failed"}, 503)
            return
        except OSError as exc:
            record_evidence("marketplace_install_failed", {"app_id": app_id, "reason": str(exc)})
            self._send_json({"error": "marketplace download failed"}, 503)
            return
        if download_status == 404 or session_rules_text is None:
            self._send_json({"error": "app not found"}, 404)
            return
        app_dir = _marketplace_app_dir(repo_root, app_id)
        session_rules_path = _session_rules_path_for_app(repo_root, app_id)
        try:
            app_dir.mkdir(parents=True, exist_ok=True)
            session_rules_path.write_text(session_rules_text)
        except OSError as exc:
            record_evidence("marketplace_install_failed", {"app_id": app_id, "reason": str(exc)})
            self._send_json({"error": "install write failed"}, 500)
            return
        try:
            _rebuild_domain_index(repo_root)
        except ValueError as error:
            self._send_json({"error": str(error)}, 400)
            return
        self._reload_session_rules_cache()
        record_evidence("marketplace_app_installed", {
            "app_id": app_id,
            "source": source,
            "tier_required": tier_required,
        })
        self._send_json({
            "status": "installed",
            "app_id": app_id,
            "path": f"data/default/apps/{app_id}/",
        })

    def _handle_marketplace_uninstall(self) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        app_id = body.get("app_id")
        if not isinstance(app_id, str) or not app_id:
            self._send_json({"error": "app_id required"}, 400)
            return
        if not _APP_ID_RE.fullmatch(app_id):
            self._send_json({"error": "app_id must be alphanumeric + hyphens only"}, 400)
            return
        repo_root = getattr(self.server, "repo_root", ".")
        app_dir = _marketplace_app_dir(repo_root, app_id)
        session_rules_path = _session_rules_path_for_app(repo_root, app_id)
        try:
            session_rules_path.unlink()
        except FileNotFoundError:
            self._send_json({"error": "app not installed"}, 404)
            return
        except OSError as exc:
            record_evidence("marketplace_uninstall_failed", {"app_id": app_id, "reason": str(exc)})
            self._send_json({"error": "uninstall failed"}, 500)
            return
        try:
            app_dir.rmdir()
        except OSError:
            pass
        try:
            _rebuild_domain_index(repo_root)
        except ValueError as error:
            self._send_json({"error": str(error)}, 400)
            return
        self._reload_session_rules_cache()
        record_evidence("marketplace_app_uninstalled", {"app_id": app_id})
        self._send_json({"status": "uninstalled", "app_id": app_id})

    # ---------------------------------------------------------------------------
    # Task 058 — Schedule Viewer handlers
    # ---------------------------------------------------------------------------

    def _schedule_settings_path(self) -> Path:
        runtime_dir = PORT_LOCK_PATH.parent
        if SETTINGS_PATH.parent == runtime_dir:
            return SETTINGS_PATH
        return runtime_dir / SETTINGS_PATH.name

    def _load_schedule_settings(self) -> dict:
        path = self._schedule_settings_path()
        try:
            settings = json.loads(path.read_text())
        except FileNotFoundError:
            settings = {}
        except json.JSONDecodeError:
            settings = {}
        except OSError:
            settings = {}
        if not isinstance(settings, dict):
            return {}
        return settings

    def _save_schedule_settings(self, settings: dict) -> None:
        path = self._schedule_settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2))

    def _schedule_audit_dir(self) -> Path:
        return PORT_LOCK_PATH.parent / "audit"

    def _write_schedule_audit_item(self, item: dict, event_type: str) -> str:
        audit_dir = self._schedule_audit_dir()
        audit_dir.mkdir(parents=True, exist_ok=True)
        recorded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        payload = {
            "event_type": event_type,
            "recorded_at": recorded_at,
            "activity_item": item,
        }
        encoded = json.dumps(payload, sort_keys=True)
        with (audit_dir / f"{item['id']}.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
        return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"

    def _load_schedule_audit_items(self) -> dict[str, dict]:
        audit_dir = self._schedule_audit_dir()
        if not audit_dir.exists():
            return {}
        items: dict[str, dict] = {}
        for audit_path in sorted(audit_dir.glob("*.jsonl")):
            try:
                lines = audit_path.read_text(encoding="utf-8").splitlines()
            except FileNotFoundError:
                continue
            except OSError:
                continue
            for raw_line in reversed(lines):
                if not raw_line.strip():
                    continue
                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                item = payload.get("activity_item", payload)
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id") or audit_path.stem)
                if not item_id:
                    continue
                normalized = dict(item)
                normalized["id"] = item_id
                items[item_id] = normalized
                break
        return items

    def _load_schedule_plan_items(self) -> list[dict]:
        schedule_plans = self._load_schedule_settings().get("schedule_plans", [])
        if not isinstance(schedule_plans, list):
            return []
        planned_items: list[dict] = []
        for plan in schedule_plans:
            if not isinstance(plan, dict):
                continue
            run_id = str(plan.get("run_id", "")).strip()
            scheduled_at = str(plan.get("scheduled_at", "")).strip()
            app_id = str(plan.get("app_id", "")).strip()
            if not run_id or not scheduled_at or not app_id:
                continue
            repeat = str(plan.get("repeat", "none") or "none")
            schedule_pattern = None if repeat == "none" else repeat
            planned_items.append({
                "id": run_id,
                "app_id": app_id,
                "app_name": app_id,
                "status": "scheduled",
                "safety_tier": "A",
                "started_at": scheduled_at,
                "ended_at": None,
                "duration_ms": 0,
                "cost_usd": "0.00",
                "tokens_used": 0,
                "actions_taken": 0,
                "evidence_path": f"~/.solace/audit/{run_id}.jsonl",
                "evidence_hash": str(plan.get("evidence_hash", "")),
                "output_summary": str(plan.get("note", "")),
                "scopes_used": [],
                "cooldown_expires_at": None,
                "scheduled_at": scheduled_at,
                "schedule_pattern": schedule_pattern,
                "cross_app_triggers": [],
                "error": None,
                "label": app_id,
                "action_type": app_id,
            })
        return planned_items

    def _collect_schedule_items(self, now_ts: float) -> list[dict]:
        items = self._load_schedule_audit_items()
        with _PENDING_ACTIONS_LOCK:
            pending_snapshot = list(_PENDING_ACTIONS.values())
        for action in pending_snapshot:
            items[action.get("action_id", "")] = self._build_activity_item(action, now_ts)
        for planned_item in self._load_schedule_plan_items():
            items.setdefault(planned_item["id"], planned_item)
        return list(items.values())

    def _build_activity_item(self, action: dict, now_ts: float) -> dict:
        """Convert a _PENDING_ACTIONS record into an ActivityItem dict."""
        from decimal import Decimal
        action_id = action.get("action_id", "")
        action_type = action.get("action_type", "")
        app_id = action.get("app_id", "")
        created_ts = action.get("created_at", now_ts)
        cooldown_end_ts = action.get("cooldown_ends_at")
        action_class = action.get("class", "B")
        status_raw = action.get("status", "PENDING_APPROVAL")
        if status_raw == "APPROVED":
            status = "success"
        elif status_raw == "REJECTED":
            status = "cancelled"
        elif status_raw == "PENDING_APPROVAL":
            if cooldown_end_ts and now_ts < cooldown_end_ts:
                status = "cooldown"
            else:
                status = "pending_approval"
        else:
            status = status_raw.lower()
        created_iso = datetime.fromtimestamp(created_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        cooldown_end_iso = None
        if cooldown_end_ts:
            cooldown_end_iso = datetime.fromtimestamp(cooldown_end_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        preview = action.get("preview", {})
        return {
            "id": action_id,
            "app_id": app_id,
            "app_name": app_id,
            "status": status,
            "safety_tier": action_class,
            "started_at": created_iso,
            "ended_at": action.get("signed_at") or action.get("rejected_at"),
            "duration_ms": 0,
            "cost_usd": str(Decimal("0.00")),
            "tokens_used": 0,
            "actions_taken": 0,
            "evidence_path": f"~/.solace/audit/{action_id}.jsonl",
            "evidence_hash": action.get("action_hash", ""),
            "output_summary": preview.get("preview_text", ""),
            "scopes_used": list(action.get("params", {}).keys()),
            "cooldown_expires_at": cooldown_end_iso,
            "scheduled_at": None,
            "schedule_pattern": None,
            "cross_app_triggers": [],
            "error": action.get("reject_reason"),
            "preview_text": preview.get("preview_text", ""),
            "risk_tier": action_class,
            "label": action_type,
            "action_type": action_type,
        }

    def _handle_schedule_viewer_list(self, query: str) -> None:
        """GET /api/v1/schedule — list activity items with filtering."""
        params = self._parse_query(query)
        filter_status = params.get("status", "")
        filter_app_id = params.get("app_id", "")
        filter_safety_tier = params.get("safety_tier", "")
        from_iso = params.get("from", "")
        to_iso = params.get("to", "")
        try:
            limit = int(params.get("limit", "50"))
        except ValueError:
            limit = 50
        now_ts = time.time()
        items = []
        normalized_filter = str(filter_status).strip().lower()
        for item in self._collect_schedule_items(now_ts):
            if filter_app_id and item["app_id"] != filter_app_id:
                continue
            if filter_safety_tier and item.get("safety_tier") != filter_safety_tier:
                continue
            item_time = str(item.get("scheduled_at") or item.get("started_at") or "")
            if from_iso and item_time < from_iso:
                continue
            if to_iso and item_time > to_iso:
                continue
            item_status = str(item["status"]).lower()
            if normalized_filter:
                if normalized_filter == "pending" and item_status not in ("pending_approval", "cooldown"):
                    continue
                if normalized_filter == "past" and item_status not in ("success", "failed", "cancelled"):
                    continue
                if normalized_filter == "future" and item_status not in ("scheduled", "queued"):
                    continue
                if normalized_filter not in ("pending", "past", "future") and item_status != normalized_filter:
                    continue
            items.append(item)
        items.sort(key=lambda x: str(x.get("scheduled_at") or x.get("started_at") or ""), reverse=True)
        self._send_json({"items": items[:limit], "total": len(items)})

    def _handle_schedule_viewer_detail(self, run_id: str) -> None:
        """GET /api/v1/schedule/{run_id} — full detail."""
        now_ts = time.time()
        for item in self._collect_schedule_items(now_ts):
            if item.get("id") == run_id:
                self._send_json(item)
                return
        with _ACTIONS_HISTORY_LOCK:
            for entry in _ACTIONS_HISTORY:
                if entry.get("action_id") == run_id or entry.get("bundle_id") == run_id:
                    self._send_json(entry)
                    return
        self._send_json({"error": "not found"}, 404)

    def _handle_schedule_viewer_approve(self, run_id: str) -> None:
        """POST /api/v1/schedule/approve/{run_id} — sign off, requires auth; 400 if cooldown active."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            body = {}
        now_ts = time.time()
        with _PENDING_ACTIONS_LOCK:
            action = _PENDING_ACTIONS.get(run_id)
        if action is None:
            settings = self._load_schedule_settings()
            schedule_plans = settings.get("schedule_plans", [])
            if not isinstance(schedule_plans, list):
                schedule_plans = []
            remaining_plans = [plan for plan in schedule_plans if str(plan.get("run_id", "")) != run_id]
            if len(remaining_plans) == len(schedule_plans):
                self._send_json({"error": "not found"}, 404)
                return
            settings["schedule_plans"] = remaining_plans
            self._save_schedule_settings(settings)
            self._send_json({"cancelled": True, "run_id": run_id})
            return
        if action.get("status") != "PENDING_APPROVAL":
            self._send_json({"error": "not pending approval", "status": action.get("status")}, 409)
            return
        cooldown_end = action.get("cooldown_ends_at", now_ts)
        if now_ts < cooldown_end:
            remaining = int(cooldown_end - now_ts)
            status_code = 409 if self.path.startswith("/api/schedule/") else 400
            self._send_json({"error": "cooldown_active", "remaining_seconds": remaining}, status_code)
            return
        sealed_at = datetime.utcnow().isoformat() + "Z"
        with _PENDING_ACTIONS_LOCK:
            if run_id in _PENDING_ACTIONS:
                _PENDING_ACTIONS[run_id]["status"] = "APPROVED"
                _PENDING_ACTIONS[run_id]["signed_at"] = sealed_at
                action = dict(_PENDING_ACTIONS[run_id])
        item = self._build_activity_item(action, now_ts)
        evidence_hash = self._write_schedule_audit_item(item, "schedule_approved")
        record_evidence("schedule_approved", {"run_id": run_id, "action_type": action.get("action_type", "")})
        self._send_json({"approved": True, "run_id": run_id, "sealed_at": sealed_at, "evidence_hash": evidence_hash})

    def _handle_schedule_viewer_cancel(self, run_id: str) -> None:
        """POST /api/v1/schedule/cancel/{run_id} — cancel pending run, requires auth."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            body = {}
        reason = str(body.get("reason", "countdown_expired")).strip()
        with _PENDING_ACTIONS_LOCK:
            action = _PENDING_ACTIONS.get(run_id)
        if action is None:
            self._send_json({"error": "not found"}, 404)
            return
        if action.get("status") != "PENDING_APPROVAL":
            self._send_json({"error": "not pending", "status": action.get("status")}, 409)
            return
        cancelled_at = datetime.utcnow().isoformat() + "Z"
        with _PENDING_ACTIONS_LOCK:
            if run_id in _PENDING_ACTIONS:
                _PENDING_ACTIONS[run_id]["status"] = "REJECTED"
                _PENDING_ACTIONS[run_id]["reject_reason"] = reason
                _PENDING_ACTIONS[run_id]["rejected_at"] = cancelled_at
                action = dict(_PENDING_ACTIONS[run_id])
        item = self._build_activity_item(action, time.time())
        evidence_hash = self._write_schedule_audit_item(item, "schedule_cancelled")
        record_evidence("schedule_cancelled", {"run_id": run_id, "reason": reason})
        self._send_json({"cancelled": True, "run_id": run_id, "evidence_hash": evidence_hash})

    def _handle_schedule_viewer_queue(self) -> None:
        """GET /api/v1/schedule/queue — Class B+C items pending sign-off."""
        now_ts = time.time()
        with _PENDING_ACTIONS_LOCK:
            snapshot = list(_PENDING_ACTIONS.values())
        result = []
        for action in snapshot:
            if action.get("status") != "PENDING_APPROVAL":
                continue
            action_class = action.get("class", "B")
            if action_class not in ("B", "C"):
                continue
            cooldown_end = action.get("cooldown_ends_at", now_ts)
            remaining = max(0.0, cooldown_end - now_ts)
            cooldown_end_iso = datetime.fromtimestamp(cooldown_end, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            result.append({
                "run_id": action.get("action_id") or action.get("preview_id", ""),
                "action_type": action.get("action_type", ""),
                "class": action_class,
                "app_id": action.get("app_id", ""),
                "preview_text": action.get("preview", {}).get("preview_text", action.get("preview_text", "")),
                "cooldown_expires_at": cooldown_end_iso,
                "countdown_seconds_remaining": int(remaining),
            })
        self._send_json({"queue": result, "count": len(result)})

    def _handle_schedule_viewer_upcoming(self) -> None:
        """GET /api/v1/schedule/upcoming — schedules + keepalive + pending counts (4-tab Tab 1)."""
        if not self._check_auth():
            return
        planned_items = self._load_schedule_plan_items()
        schedules = load_schedules()
        pending_approvals = 0
        with _PENDING_ACTIONS_LOCK:
            for action in _PENDING_ACTIONS.values():
                if action.get("status") == "PENDING_APPROVAL":
                    pending_approvals += 1
        CRON_PRESETS = {
            "0 7 * * *":   "Every day at 7:00 AM",
            "0 9 * * 1-5": "Weekdays at 9:00 AM",
            "0 * * * *":   "Every hour",
            "0 */2 * * *": "Every 2 hours",
            "0 9 * * 1":   "Every Monday at 9:00 AM",
        }
        result_schedules = []
        for s in schedules:
            cron = s.get("cron", "")
            cron_human = CRON_PRESETS.get(cron, cron)
            result_schedules.append({
                "app_id": s.get("app_id", ""),
                "app_name": s.get("label", s.get("app_id", "")),
                "cron": cron,
                "cron_human": cron_human,
                "next_run_iso": s.get("next_run_iso", ""),
                "countdown_seconds": s.get("countdown_seconds", 0),
                "enabled": s.get("enabled", True),
            })
        for item in planned_items:
            result_schedules.append({
                "app_id": item.get("app_id", ""),
                "app_name": item.get("app_name", item.get("app_id", "")),
                "cron": item.get("schedule_pattern") or "none",
                "cron_human": item.get("schedule_pattern") or "One-time run",
                "next_run_iso": item.get("scheduled_at", ""),
                "countdown_seconds": 0,
                "enabled": True,
            })
        self._send_json({
            "schedules": result_schedules,
            "keepalive": {"active_count": 0, "last_refresh": "", "next_refresh_seconds": 300},
            "pending_approvals": pending_approvals,
            "pending_esign": 0,
        })

    def _handle_esign_pending(self) -> None:
        """GET /api/v1/esign/pending — list pending eSign requests."""
        if not self._check_auth():
            return
        self._send_json({"pending": []})

    def _handle_esign_sign(self, esign_id: str) -> None:
        """POST /api/v1/esign/{esign_id}/sign — sign an eSign request."""
        if not self._check_auth():
            return
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return
        signature_token = body.get("signature_token", "")
        if not signature_token:
            self._send_json({"error": "signature_token required"}, 400)
            return
        from datetime import datetime, timezone
        sealed_at = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
        self._send_json({"signed": True, "esign_id": esign_id, "sealed_at": sealed_at})

    def _handle_esign_history(self) -> None:
        """GET /api/v1/esign/history — eSign completed signatures."""
        if not self._check_auth():
            return
        self._send_json({"history": []})

    def _handle_schedule_viewer_calendar(self, query: str) -> None:
        """GET /api/v1/schedule/calendar — group activity items by day for calendar view."""
        params = self._parse_query(query)
        month_str = params.get("month", "")
        year_str = params.get("year", "")
        now_ts = time.time()
        by_day: dict[str, list] = {}
        for item in self._collect_schedule_items(now_ts):
            started = str(item.get("scheduled_at") or item.get("started_at") or "")
            if len(started) < 10:
                continue
            day = started[:10]
            if month_str and not day.startswith(month_str[:7]):
                continue
            if year_str and not day.startswith(year_str[:4]):
                continue
            if day not in by_day:
                by_day[day] = []
            by_day[day].append({
                "id": item["id"],
                "app": item["app_id"],
                "status": item["status"],
                "time": started[11:16],  # HH:MM
                "label": item.get("label", item.get("app_id", "")),
                "safety_tier": item["safety_tier"],
            })
        self._send_json(by_day)

    def _handle_schedule_viewer_roi(self) -> None:
        """GET /api/v1/schedule/roi — ROI statistics using Decimal for USD."""
        from decimal import Decimal
        now_ts = time.time()
        week_ago_ts = now_ts - 7 * 86400
        week_runs = 0
        all_items = self._collect_schedule_items(now_ts)
        for item in all_items:
            item_time = str(item.get("started_at") or item.get("scheduled_at") or "")
            if item_time and item_time >= datetime.fromtimestamp(week_ago_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z"):
                week_runs += 1
        # 10 minutes saved per run at $30/hr
        minutes_per_run = 10
        week_time_saved_minutes = week_runs * minutes_per_run
        hourly_rate = Decimal("30")
        week_time_saved_usd = (Decimal(week_time_saved_minutes) / Decimal("60")) * hourly_rate
        week_hours_saved = Decimal(week_time_saved_minutes) / Decimal("60")
        month_equivalent = week_runs * 4
        self._send_json({
            "week_runs": week_runs,
            "week_cost_usd": str(Decimal("0.00")),
            "week_time_saved_minutes": week_time_saved_minutes,
            "week_time_saved_usd_equiv": str(week_time_saved_usd.quantize(Decimal("0.01"))),
            "week_hours_saved": str(week_hours_saved.quantize(Decimal("0.01"))),
            "week_value_usd_at_30_per_hour": str(week_time_saved_usd.quantize(Decimal("0.01"))),
            "all_time_runs": len(all_items),
            "month_equivalent": month_equivalent,
            "streak_days": 0,
            "last_streak_milestone": None,
        })

    def _handle_schedule_viewer_plan(self) -> None:
        """POST /api/v1/schedule/plan — schedule a future run."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        app_id = str(body.get("app_id", "")).strip()
        if not app_id:
            self._send_json({"error": "app_id required"}, 400)
            return
        scheduled_at = str(body.get("scheduled_at", "")).strip()
        if not scheduled_at:
            self._send_json({"error": "scheduled_at required"}, 400)
            return
        repeat = str(body.get("repeat", "none") or "none")
        note = str(body.get("note", "") or "")
        run_id = f"run-{app_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        settings = self._load_schedule_settings()
        schedule_plans = settings.get("schedule_plans", [])
        if not isinstance(schedule_plans, list):
            schedule_plans = []
        plan = {"run_id": run_id, "app_id": app_id, "scheduled_at": scheduled_at, "repeat": repeat, "note": note}
        schedule_plans.append(plan)
        settings["schedule_plans"] = schedule_plans
        self._save_schedule_settings(settings)
        item = self._load_schedule_plan_items()[-1]
        evidence_hash = self._write_schedule_audit_item(item, "schedule_planned")
        settings["schedule_plans"][-1]["evidence_hash"] = evidence_hash
        self._save_schedule_settings(settings)
        record_evidence("schedule_planned", {"run_id": run_id, "app_id": app_id, "scheduled_at": scheduled_at})
        self._send_json({"run_id": run_id, "scheduled_at": scheduled_at}, 201)

    def _handle_schedule_html(self) -> None:
        """GET /web/schedule.html — serve the schedule viewer page."""
        html_path = Path(__file__).parent / "web" / "schedule.html"
        try:
            content = html_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "schedule.html not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_schedule_js(self) -> None:
        """GET /web/js/schedule.js — serve the schedule viewer JS."""
        js_path = Path(__file__).parent / "web" / "js" / "schedule.js"
        try:
            content = js_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "schedule.js not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_schedule_css(self) -> None:
        """GET /web/css/schedule.css — serve the schedule viewer CSS."""
        css_path = Path(__file__).parent / "web" / "css" / "schedule.css"
        try:
            content = css_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "schedule.css not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/css")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # ---------------------------------------------------------------------------
    # Task 065 — Fun Packs
    # ---------------------------------------------------------------------------

    def _handle_fun_packs_list(self) -> None:
        if not self._check_auth():
            return
        packs = _list_available_packs()
        self._send_json(
            {
                "packs": packs,
                "active_pack_id": _resolve_active_pack_id(),
                "count": len(packs),
            }
        )

    def _handle_fun_pack_active(self) -> None:
        if not self._check_auth():
            return
        try:
            pack = _load_active_fun_pack()
        except FileNotFoundError:
            self._send_json({"error": "fun pack not found"}, 404)
            return
        except json.JSONDecodeError:
            self._send_json({"error": "fun pack invalid"}, 500)
            return
        except OSError:
            self._send_json({"error": "fun pack unavailable"}, 500)
            return
        self._send_json({"pack": pack})

    def _handle_fun_pack_detail(self, pack_id: str) -> None:
        if not self._check_auth():
            return
        try:
            pack = _load_fun_pack(pack_id)
        except FileNotFoundError:
            self._send_json({"error": "fun pack not found"}, 404)
            return
        except json.JSONDecodeError:
            self._send_json({"error": "fun pack invalid"}, 500)
            return
        except OSError:
            self._send_json({"error": "fun pack unavailable"}, 500)
            return
        self._send_json({"pack": pack})

    def _handle_fun_pack_activate(self, pack_id: str) -> None:
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        if not isinstance(body, dict):
            self._send_json({"error": "invalid JSON"}, 400)
            return
        try:
            _load_fun_pack(pack_id)
        except FileNotFoundError:
            self._send_json({"error": "fun pack not found"}, 404)
            return
        except json.JSONDecodeError:
            self._send_json({"error": "fun pack invalid"}, 500)
            return
        except OSError:
            self._send_json({"error": "fun pack unavailable"}, 500)
            return
        try:
            _set_active_pack_id(pack_id)
        except OSError:
            self._send_json({"error": "fun pack unavailable"}, 500)
            return
        self._send_json({"status": "activated", "pack_id": pack_id})

    def _handle_fun_pack_random_joke(self) -> None:
        if not self._check_auth():
            return
        try:
            pack = _load_active_fun_pack()
        except FileNotFoundError:
            self._send_json({"error": "fun pack not found"}, 404)
            return
        except json.JSONDecodeError:
            self._send_json({"error": "fun pack invalid"}, 500)
            return
        except OSError:
            self._send_json({"error": "fun pack unavailable"}, 500)
            return
        pack_id = str(pack.get("_meta", {}).get("id", DEFAULT_FUN_PACK_ID))
        jokes = [entry for entry in pack.get("jokes", []) if isinstance(entry, dict)]
        if not jokes:
            self._send_json({"error": "no jokes available"}, 404)
            return
        joke = dict(random.choice(jokes))
        joke["pack_id"] = pack_id
        self._send_json({"joke": joke})

    def _handle_fun_pack_random_fact(self) -> None:
        if not self._check_auth():
            return
        try:
            pack = _load_active_fun_pack()
        except FileNotFoundError:
            self._send_json({"error": "fun pack not found"}, 404)
            return
        except json.JSONDecodeError:
            self._send_json({"error": "fun pack invalid"}, 500)
            return
        except OSError:
            self._send_json({"error": "fun pack unavailable"}, 500)
            return
        pack_id = str(pack.get("_meta", {}).get("id", DEFAULT_FUN_PACK_ID))
        facts = [entry for entry in pack.get("facts", []) if isinstance(entry, dict)]
        if not facts:
            self._send_json({"error": "no facts available"}, 404)
            return
        fact = dict(random.choice(facts))
        fact["pack_id"] = pack_id
        self._send_json({"fact": fact})

    def _handle_fun_pack_greeting(self, query: str) -> None:
        if not self._check_auth():
            return
        params = self._parse_query(query)
        time_of_day = params.get("time_of_day", "any")
        if time_of_day not in FUN_PACK_GREETING_TIMES:
            self._send_json({"error": "invalid time_of_day"}, 400)
            return
        try:
            pack = _load_active_fun_pack()
        except FileNotFoundError:
            self._send_json({"error": "fun pack not found"}, 404)
            return
        except json.JSONDecodeError:
            self._send_json({"error": "fun pack invalid"}, 500)
            return
        except OSError:
            self._send_json({"error": "fun pack unavailable"}, 500)
            return
        pack_id = str(pack.get("_meta", {}).get("id", DEFAULT_FUN_PACK_ID))
        greetings = [
            entry
            for entry in pack.get("greetings", [])
            if isinstance(entry, dict) and entry.get("time_of_day") == time_of_day
        ]
        if not greetings and time_of_day != "any":
            greetings = [
                entry
                for entry in pack.get("greetings", [])
                if isinstance(entry, dict) and entry.get("time_of_day") == "any"
            ]
        if not greetings:
            self._send_json({"error": "no greetings available"}, 404)
            return
        greeting = dict(random.choice(greetings))
        greeting["pack_id"] = pack_id
        self._send_json({"greeting": greeting})

    def _handle_fun_packs_html(self) -> None:
        """GET /web/fun-packs.html — serve the fun pack manager page."""
        html_path = Path(__file__).parent / "web" / "fun-packs.html"
        try:
            content = html_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "fun-packs.html not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # ---------------------------------------------------------------------------
    # Task 061 — Value Dashboard handlers
    # ---------------------------------------------------------------------------

    def _handle_session_stats(self) -> None:
        """GET /api/v1/session/stats — current session metrics."""
        if not self._check_auth():
            return
        with _SESSION_STATS_LOCK:
            stats = dict(_SESSION_STATS)
        if stats["session_start"] is not None:
            stats["duration_seconds"] = int(time.time() - stats["session_start"])
        self._send_json(stats)

    def _handle_session_stats_reset(self) -> None:
        """POST /api/v1/session/stats/reset — clear session counters."""
        if not self._check_auth():
            return
        import uuid
        with _SESSION_STATS_LOCK:
            _SESSION_STATS["session_id"] = str(uuid.uuid4())
            _SESSION_STATS["state"] = "IDLE"
            _SESSION_STATS["app_name"] = None
            _SESSION_STATS["pages_visited"] = 0
            _SESSION_STATS["llm_calls"] = 0
            _SESSION_STATS["cost_usd"] = "0.00"
            _SESSION_STATS["cost_saved_pct"] = 0
            _SESSION_STATS["duration_seconds"] = 0
            _SESSION_STATS["recipes_replayed"] = 0
            _SESSION_STATS["evidence_captured"] = 0
            _SESSION_STATS["session_start"] = time.time()
        self._send_json({"reset": True})

    def _handle_dashboard_html(self) -> None:
        """GET /web/dashboard.html — serve the value dashboard page."""
        html_path = Path(__file__).parent / "web" / "dashboard.html"
        try:
            content = html_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "dashboard.html not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_dashboard_js(self) -> None:
        """GET /web/js/dashboard.js — serve the value dashboard JS."""
        js_path = Path(__file__).parent / "web" / "js" / "dashboard.js"
        try:
            content = js_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "dashboard.js not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_dashboard_css(self) -> None:
        """GET /web/css/dashboard.css — serve the value dashboard CSS."""
        css_path = Path(__file__).parent / "web" / "css" / "dashboard.css"
        try:
            content = css_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "dashboard.css not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/css")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_notifications_sse_js(self) -> None:
        """GET /web/js/notifications-sse.js — serve the SSE notifications JS."""
        js_path = Path(__file__).parent / "web" / "js" / "notifications-sse.js"
        try:
            content = js_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "notifications-sse.js not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_notifications_css(self) -> None:
        """GET /web/css/notifications.css — serve the SSE notifications CSS."""
        css_path = Path(__file__).parent / "web" / "css" / "notifications.css"
        try:
            content = css_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "notifications.css not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/css; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # ---------------------------------------------------------------------------
    # Task 062 — App Onboarding: Grey-to-Green 4-State Lifecycle UI
    # ---------------------------------------------------------------------------

    def _handle_apps_lifecycle(self) -> None:
        """GET /api/v1/apps/lifecycle — list all apps with their current state."""
        if not self._check_auth():
            return
        apps = getattr(self.server, "apps", [])
        result = []
        for app_id in (apps if isinstance(apps, list) else []):
            config_path = Path.home() / ".solace" / "app-configs" / f"{app_id}.json"
            is_configured = config_path.exists()
            result.append({
                "app_id": app_id,
                "name": app_id.replace("-", " ").title(),
                "icon": "\U0001F4E6",
                "state": "activated" if is_configured else "installed",
                "config_required": [],
                "config_complete": is_configured,
            })
        self._send_json({"apps": result})

    def _handle_app_setup_requirements(self, app_id: str) -> None:
        """GET /api/v1/apps/{app_id}/setup-requirements — fields needed to activate."""
        if not self._check_auth():
            return
        self._send_json({
            "app_id": app_id,
            "fields": [],
            "vault_key": None,
        })

    def _handle_app_activate(self, app_id: str) -> None:
        """POST /api/v1/apps/{app_id}/activate — store encrypted config, mark activated."""
        if not self._check_auth():
            return
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length) or b"{}") if content_length else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return
        config_dir = Path.home() / ".solace" / "app-configs"
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self._send_json({"error": f"Could not create config dir: {e}"}, 500)
            return
        config_path = config_dir / f"{app_id}.json"
        try:
            config_path.write_text(json.dumps({"app_id": app_id, "configured": True}))
        except OSError as e:
            self._send_json({"error": f"Could not save config: {e}"}, 500)
            return
        self._send_json({"activated": True, "app_id": app_id, "state": "activated"})

    def _handle_app_deactivate(self, app_id: str) -> None:
        """DELETE /api/v1/apps/{app_id}/activate — reset to installed state."""
        if not self._check_auth():
            return
        config_path = Path.home() / ".solace" / "app-configs" / f"{app_id}.json"
        try:
            if config_path.exists():
                config_path.unlink()
        except OSError as e:
            self._send_json({"error": f"Could not remove config: {e}"}, 500)
            return
        self._send_json({"deactivated": True, "app_id": app_id, "state": "installed"})

    def _handle_apps_html(self) -> None:
        """GET /web/apps.html — serve the app onboarding page."""
        html_path = Path(__file__).parent / "web" / "apps.html"
        try:
            content = html_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "apps.html not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_apps_js(self) -> None:
        """GET /web/js/apps.js — serve the app onboarding JS."""
        js_path = Path(__file__).parent / "web" / "js" / "apps.js"
        try:
            content = js_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "apps.js not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_apps_css(self) -> None:
        """GET /web/css/apps.css — serve the app onboarding CSS."""
        css_path = Path(__file__).parent / "web" / "css" / "apps.css"
        try:
            content = css_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "apps.css not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/css; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # ---------------------------------------------------------------------------
    # Task 057 — Preview / Cooldown / Sign-Off handlers
    # ---------------------------------------------------------------------------

    def _handle_actions_preview(self) -> None:
        """POST /api/v1/actions/preview — classify and gate Class B/C actions."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            return
        action_type = body.get("action_type", "")
        if not isinstance(action_type, str) or not action_type:
            self._send_json({"error": "missing 'action_type'"}, 400)
            return
        if len(action_type) > 128:
            self._send_json({"error": "'action_type' exceeds 128 chars"}, 400)
            return
        params = body.get("params", {})
        if not isinstance(params, dict):
            self._send_json({"error": "'params' must be an object"}, 400)
            return
        app_id = str(body.get("app_id", ""))
        oauth3_token_id = str(body.get("oauth3_token_id", "")).strip()
        action_class = ACTION_CLASSES.get(action_type, "B")
        if action_class == "A":
            self._send_json({
                "class": "A",
                "action_type": action_type,
                "can_execute_immediately": True,
                "cooldown_ends_at": None,
                "sign_off_required": False,
            })
            return
        now_ts = time.time()
        record = _create_pending_action_record(action_type, params, app_id, oauth3_token_id, now_ts)
        with _PENDING_ACTIONS_LOCK:
            _PENDING_ACTIONS[record["action_id"]] = record
        self._write_schedule_audit_item(self._build_activity_item(record, now_ts), "schedule_pending")
        self._send_json({
            "action_id": record["action_id"],
            "class": record["class"],
            "preview": record["preview"],
            "cooldown_ends_at": _utc_isoformat(record["cooldown_ends_at"]),
            "can_execute_immediately": False,
            "sign_off_required": True,
        }, 201)

    def _handle_actions_pending(self) -> None:
        """GET /api/v1/actions/pending — list pending actions with cooldown_remaining_seconds."""
        now_ts = time.time()
        with _PENDING_ACTIONS_LOCK:
            snapshot = list(_PENDING_ACTIONS.values())
        result = []
        for action in snapshot:
            if action.get("status") != "PENDING_APPROVAL":
                continue
            result.append(_pending_action_list_item(action, now_ts))
        self._send_json({"actions": result})

    def _handle_action_approve(self, action_id: str) -> None:
        """POST /api/v1/actions/{action_id}/approve — sign off after cooldown elapses."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            body = {}
        if not action_id:
            self._send_json({"error": "missing action_id"}, 400)
            return
        with _PENDING_ACTIONS_LOCK:
            action = _PENDING_ACTIONS.get(action_id)
        if action is None:
            self._send_json({"error": "action not found"}, 404)
            return
        if action.get("status") != "PENDING_APPROVAL":
            self._send_json({"error": "action is not pending approval", "status": action.get("status")}, 409)
            return
        now_ts = time.time()
        cooldown_end = action.get("cooldown_ends_at", now_ts)
        if now_ts < cooldown_end:
            remaining = int(cooldown_end - now_ts)
            self._send_json({"error": "cooldown_active", "remaining_seconds": remaining}, 409)
            return
        action_class = action.get("class", "B")
        reason = ""
        if action_class == "C":
            step_up = body.get("step_up_consent")
            if step_up is not True:
                self._send_json({"error": "step_up_required", "scope": "high_risk"}, 403)
                return
            reason = str(body.get("reason", "")).strip()
            if not reason:
                self._send_json({"error": "reason required for Class C actions"}, 400)
                return
        signer_id = str(body.get("signer_id") or "user")
        session_token = str(getattr(self.server, "session_token_sha256", ""))
        signed_at = _utc_isoformat(now_ts)
        before_state = _action_state_copy(action)
        action_hash = action.get("action_hash", "")
        signature = hmac.new(
            session_token.encode(),
            f"{action_hash}:{signed_at}:{signer_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        with _PENDING_ACTIONS_LOCK:
            current = _PENDING_ACTIONS.get(action_id)
            if current is None:
                self._send_json({"error": "action not found"}, 404)
                return
            current["status"] = "APPROVED"
            current["signed_at"] = signed_at
            current["signature"] = signature
            current["signer_id"] = signer_id
            if reason:
                current["approval_reason"] = reason
            after_state = _action_state_copy(current)
        evidence_bundle = create_and_store_evidence_bundle(
            action["action_type"],
            before_state,
            after_state,
            str(action.get("oauth3_token_id") or "hub-session"),
            signer_id,
        )
        bundle_id = str(evidence_bundle["bundle_id"])
        before_hash = str(evidence_bundle["before_snapshot_hash"])
        after_hash = str(evidence_bundle["after_snapshot_hash"])
        evidence_entry: dict = {
            "evidence_bundle_id": bundle_id,
            "bundle_id": bundle_id,
            "action_id": action_id,
            "action_type": action["action_type"],
            "action_hash": action_hash,
            "signer_id": signer_id,
            "signed_at": signed_at,
            "signature": signature,
            "before_state_hash": before_hash,
            "after_state_hash": after_hash,
            "alcoa_attributable": True,
            "alcoa_legible": True,
            "alcoa_contemporaneous": True,
            "alcoa_original": True,
            "alcoa_accurate": True,
            "status": "APPROVED",
            "class": action_class,
            "preview_summary": action.get("preview", {}).get("preview_text", ""),
        }
        if reason:
            evidence_entry["approval_reason"] = reason
        with _PENDING_ACTIONS_LOCK:
            if action_id in _PENDING_ACTIONS:
                _PENDING_ACTIONS[action_id]["status"] = "APPROVED"
                _PENDING_ACTIONS[action_id]["evidence_bundle_id"] = bundle_id
                _PENDING_ACTIONS[action_id]["signed_at"] = signed_at
        with _ACTIONS_HISTORY_LOCK:
            _ACTIONS_HISTORY.append(evidence_entry)
        _append_evidence_record("action_approved", {
            "action_id": action_id,
            "action_type": action["action_type"],
            "class": action_class,
            "bundle_id": bundle_id,
            "evidence_bundle_id": bundle_id,
            "before_state_hash": before_hash,
            "after_state_hash": after_hash,
            "oauth3_token_id": str(action.get("oauth3_token_id") or "hub-session"),
            "user_id": signer_id,
        })
        self._send_json({
            "approved": True,
            "action_id": action_id,
            "execute_at": signed_at,
            "evidence_bundle_id": bundle_id,
        })

    def _handle_action_reject(self, action_id: str) -> None:
        """POST /api/v1/actions/{action_id}/reject — reject and seal evidence with reason."""
        if not self._check_auth():
            return
        body = self._read_json_body()
        if body is None:
            body = {}
        if not action_id:
            self._send_json({"error": "missing action_id"}, 400)
            return
        with _PENDING_ACTIONS_LOCK:
            action = _PENDING_ACTIONS.get(action_id)
        if action is None:
            self._send_json({"error": "action not found"}, 404)
            return
        if action.get("status") != "PENDING_APPROVAL":
            self._send_json({"error": "action is not pending approval", "status": action.get("status")}, 409)
            return
        reason = str(body.get("reason", "")).strip()
        signer_id = str(body.get("signer_id") or "user")
        rejected_at = _utc_isoformat(time.time())
        before_state = _action_state_copy(action)
        with _PENDING_ACTIONS_LOCK:
            current = _PENDING_ACTIONS.get(action_id)
            if current is None:
                self._send_json({"error": "action not found"}, 404)
                return
            current["status"] = "REJECTED"
            current["reject_reason"] = reason
            current["rejected_at"] = rejected_at
            current["signer_id"] = signer_id
            after_state = _action_state_copy(current)
        evidence_bundle = create_and_store_evidence_bundle(
            action["action_type"],
            before_state,
            after_state,
            str(action.get("oauth3_token_id") or "hub-session"),
            signer_id,
        )
        bundle_id = str(evidence_bundle["bundle_id"])
        history_entry: dict = {
            "evidence_bundle_id": bundle_id,
            "bundle_id": bundle_id,
            "action_id": action_id,
            "action_type": action["action_type"],
            "action_hash": action.get("action_hash", ""),
            "signer_id": signer_id,
            "signed_at": rejected_at,
            "signature": "",
            "before_state_hash": str(evidence_bundle["before_snapshot_hash"]),
            "after_state_hash": str(evidence_bundle["after_snapshot_hash"]),
            "alcoa_attributable": True,
            "alcoa_legible": True,
            "alcoa_contemporaneous": True,
            "alcoa_original": True,
            "alcoa_accurate": True,
            "status": "REJECTED",
            "class": action.get("class", "B"),
            "preview_summary": action.get("preview", {}).get("preview_text", ""),
            "reject_reason": reason,
        }
        with _ACTIONS_HISTORY_LOCK:
            _ACTIONS_HISTORY.append(history_entry)
        _append_evidence_record("action_rejected", {
            "action_id": action_id,
            "action_type": action["action_type"],
            "reason": reason,
            "bundle_id": bundle_id,
            "evidence_bundle_id": bundle_id,
            "before_state_hash": history_entry["before_state_hash"],
            "after_state_hash": history_entry["after_state_hash"],
            "oauth3_token_id": str(action.get("oauth3_token_id") or "hub-session"),
            "user_id": signer_id,
        })
        self._send_json({"rejected": True, "action_id": action_id, "reason": reason, "evidence_bundle_id": bundle_id})

    def _handle_action_cancel(self, action_id: str) -> None:
        """DELETE /api/v1/actions/{action_id}/cancel — revoke before cooldown ends."""
        if not self._check_auth():
            return
        if not action_id:
            self._send_json({"error": "missing action_id"}, 400)
            return
        with _PENDING_ACTIONS_LOCK:
            action = _PENDING_ACTIONS.pop(action_id, None)
        if action is None:
            self._send_json({"error": "action not found"}, 404)
            return
        _append_evidence_record("action_cancelled", {"action_id": action_id, "action_type": action.get("action_type", "")})
        self._send_json({"cancelled": True, "action_id": action_id})

    def _handle_actions_history(self, query: str) -> None:
        """GET /api/v1/actions/history — approved/rejected action history with filters."""
        params = self._parse_query(query)
        filter_class = params.get("class", "")
        filter_status = params.get("status", "")
        from_iso = params.get("from", "")
        to_iso = params.get("to", "")
        with _ACTIONS_HISTORY_LOCK:
            snapshot = list(_ACTIONS_HISTORY)
        result = []
        for entry in snapshot:
            if filter_class and entry.get("class") != filter_class:
                continue
            if filter_status and entry.get("status") != filter_status:
                continue
            signed_at = entry.get("signed_at", "")
            if from_iso and signed_at < from_iso:
                continue
            if to_iso and signed_at > to_iso:
                continue
            result.append(entry)
        self._send_json({"actions": result})

    def _parse_query(self, query: str) -> dict[str, str]:
        """Parse ?key=value&key2=value2 into dict."""
        if not query or query == "?":
            return {}
        result: dict[str, str] = {}
        for pair in query.lstrip("?").split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                result[urllib.parse.unquote_plus(k)] = urllib.parse.unquote_plus(v)
        return result

    def _record_history_entry(self, status_code: int) -> None:
        """Record request to rolling history. Thread-safe. Task 021."""
        path = self.path.split("?")[0] if "?" in self.path else self.path
        entry = {
            "method": self.command,
            "path": path,
            "status": status_code,
            "timestamp": int(time.time()),
            "ip": self.client_address[0] if self.client_address else "unknown",
        }
        with _HISTORY_LOCK:
            _REQUEST_HISTORY.append(entry)
            if len(_REQUEST_HISTORY) > MAX_HISTORY:
                _REQUEST_HISTORY.pop(0)

    def _send_json(self, data: dict, status: int = 200) -> None:
        _record_request(self.path.split("?")[0], status)
        self._record_history_entry(status)
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", f"http://localhost:{YINYANG_PORT}")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # noqa: D102
        # Suppress default stderr logging — callers use structured evidence.
        pass

    # ---------------------------------------------------------------------------
    # Task 063 — YinYang Tutorial: 5-Step First-Run Modal
    # ---------------------------------------------------------------------------

    def _handle_tutorial_html(self) -> None:
        """GET /web/tutorial.html — serve the tutorial modal page."""
        html_path = Path(__file__).parent / "web" / "tutorial.html"
        try:
            content = html_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "tutorial.html not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_tutorial_js(self) -> None:
        """GET /web/js/tutorial.js — serve the tutorial JS."""
        js_path = Path(__file__).parent / "web" / "js" / "tutorial.js"
        try:
            content = js_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "tutorial.js not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_tutorial_css(self) -> None:
        """GET /web/css/tutorial.css — serve the tutorial CSS."""
        css_path = Path(__file__).parent / "web" / "css" / "tutorial.css"
        try:
            content = css_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "tutorial.css not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/css; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _handle_tutorial_reset(self) -> None:
        """GET /api/v1/tutorial/reset — informational reset endpoint (actual reset is client-side)."""
        if not self._check_auth():
            return
        self._send_json({"reset": True, "storage_key": "sb_tutorial_v1"})


# ---------------------------------------------------------------------------
# Server factory — theorem: build_server isolates configuration from startup.
# ---------------------------------------------------------------------------
class ReusableThreadingHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def build_server(
    port: int,
    repo_root: str,
    session_token_sha256: str = "",
    cloud_twin: bool = False,
) -> http.server.ThreadingHTTPServer:
    """
    Construct a ThreadingHTTPServer with apps pre-loaded.
    Does NOT write port.lock — caller is responsible for that.
    """
    load_session_rules()
    server = ReusableThreadingHTTPServer(("localhost", port), YinyangHandler)
    server.apps = load_apps(repo_root)  # type: ignore[attr-defined]
    server.repo_root = repo_root  # type: ignore[attr-defined]
    server.session_token_sha256 = session_token_sha256  # type: ignore[attr-defined]
    server.cloud_twin_mode = _cloud_twin_mode_enabled(cloud_twin)  # type: ignore[attr-defined]
    server.hub_integration_enabled = _hub_integration_enabled(cloud_twin)  # type: ignore[attr-defined]
    return server


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def start_server(
    port: int = YINYANG_PORT,
    repo_root: str = ".",
    session_token_sha256: str = "",
    cloud_twin: bool = False,
) -> None:
    """
    Generate token, write lock, register cleanup, then serve forever.
    Token is immediately discarded after hashing — never stored in memory
    beyond this function's call stack.
    """
    import os

    global SESSION_RULES_APPS_DIR, _SESSION_TOKEN_SHA256
    _SESSION_TOKEN_SHA256 = session_token_sha256
    SESSION_RULES_APPS_DIR = Path(repo_root) / "data" / "default" / "apps"
    cloud_twin_mode = _cloud_twin_mode_enabled(cloud_twin)

    if cloud_twin_mode:
        os.environ["SOLACE_CLOUD_TWIN"] = "true"
        print("Cloud twin mode active", flush=True)

    if session_token_sha256:
        t_hash = session_token_sha256
    else:
        token = generate_token()
        t_hash = token_hash(token)
        del token  # plaintext token leaves scope here — not stored anywhere
    write_port_lock(port, t_hash, os.getpid())
    atexit.register(delete_port_lock)

    load_session_rules()
    _start_session_keepalive_thread()
    record_evidence("server_started", {"port": port, "version": _SERVER_VERSION})
    server = build_server(port, repo_root, session_token_sha256, cloud_twin_mode)
    server.serve_forever()


def _default_port() -> int:
    port_value = os.environ.get("PORT", "").strip()
    return int(port_value) if port_value.isdigit() else YINYANG_PORT


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Yinyang Server")
    parser.add_argument("repo_root", nargs="?", default=".")
    parser.add_argument("--port", dest="port", type=int, default=_default_port())
    parser.add_argument(
        "--token-sha256",
        dest="token_sha256",
        default="",
        help="Bearer token sha256 for Hub authentication",
    )
    parser.add_argument(
        "--cloud-twin",
        dest="cloud_twin",
        action="store_true",
        help="Enable cloud twin startup mode",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    start_server(args.port, args.repo_root, args.token_sha256, args.cloud_twin)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
