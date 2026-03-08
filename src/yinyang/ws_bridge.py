"""WebSocket bridge — relays messages between browser JS and cloud/local chat."""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("solace-browser.yinyang")

# ── Content filter (COPPA + safety baseline) ──
# Patterns that must be blocked in user-generated content.
# Kept minimal and deterministic — no external deps.
_BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in [
        # Profanity / slurs (compact list — extend as needed)
        r"\b(?:f+u+c+k+|s+h+i+t+|a+s+s+h+o+l+e+|b+i+t+c+h+|d+a+m+n+|c+u+n+t+)\b",
        # Threats / violence
        r"\b(?:kill\s+(?:you|her|him|them|myself)|bomb\s+threat|shoot\s+up)\b",
        # Self-harm
        r"\b(?:how\s+to\s+(?:kill|harm)\s+(?:myself|yourself))\b",
        # PII solicitation targeting minors
        r"\b(?:what\s+is\s+your\s+(?:address|phone|school))\b",
    ]
]

# Age-gate: if user identifies as under 13, block data collection
_MINOR_PATTERN = re.compile(
    r"\b(?:i\s+am|i'm|im)\s+(\d{1,2})\s*(?:years?\s*old|yo|y\.?o\.?)\b", re.IGNORECASE
)


# ── Structured Error Taxonomy ──
# Every error response includes a machine-readable code from this taxonomy.
# Clients can switch on `code` for localized messages and retry logic.
ERROR_CODES = {
    "INVALID_JSON": {"http": 400, "retryable": False, "description": "Message is not valid JSON"},
    "INVALID_MESSAGE": {"http": 400, "retryable": False, "description": "Message fails IPC schema validation"},
    "UNKNOWN_TYPE": {"http": 400, "retryable": False, "description": "Message type not recognized"},
    "RATE_LIMITED": {"http": 429, "retryable": True, "description": "Too many messages per window"},
    "ORIGIN_REJECTED": {"http": 403, "retryable": False, "description": "WebSocket origin not in allowlist"},
    "VERSION_MISMATCH": {"http": 400, "retryable": False, "description": "Protocol version not supported"},
    "NOT_FOUND": {"http": 404, "retryable": False, "description": "Resource (run_id, schedule_id) not found"},
    "INVALID_STATE": {"http": 409, "retryable": False, "description": "Action not valid for current resource state"},
    "MISSING_FIELD": {"http": 400, "retryable": False, "description": "Required field missing from payload"},
    "INTERNAL_ERROR": {"http": 500, "retryable": True, "description": "Unexpected server error"},
}


class _RateLimiter:
    """Simple sliding-window rate limiter per WS connection."""

    def __init__(self, max_calls: int = 60, period: float = 60.0):
        self._calls: deque[float] = deque()
        self._max = max_calls
        self._period = period

    def is_allowed(self) -> bool:
        now = time.monotonic()
        while self._calls and self._calls[0] < now - self._period:
            self._calls.popleft()
        if len(self._calls) >= self._max:
            return False
        self._calls.append(now)
        return True


def _check_content(text: str) -> str | None:
    """Return a rejection reason if content violates filters, else None."""
    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(text):
            return "Your message was filtered. Please keep the conversation respectful and safe."
    match = _MINOR_PATTERN.search(text)
    if match:
        age = int(match.group(1))
        if age < 13:
            return (
                "For your safety, users under 13 cannot share personal information. "
                "Please use Solace Browser with a parent or guardian."
            )
    return None

class YinyangWSBridge:
    """Local WebSocket handler for Yinyang chat relay.

    Handles message types:
      - chat: Natural language interaction
      - heartbeat: Keep-alive ping
      - detect: URL-based app matching
      - run: Trigger app execution (preview → approve flow)
      - state: Request current sidebar state
      - approve / reject: Approval queue actions
      - schedule: Schedule CRUD via WebSocket
      - credits: Query user credit balance

    Protocol versioning:
      Clients send {"type": "heartbeat", "payload": {"protocol_version": "1.0"}}
      on first connect. Server validates and includes version in heartbeat response.
      Incompatible versions get {"type": "error", "code": "VERSION_MISMATCH"}.
    """

    # Supported protocol versions (major.minor). Minor bumps are backward-compatible.
    PROTOCOL_VERSION = "1.0"
    _SUPPORTED_MAJOR_VERSIONS = frozenset({1})

    def __init__(self, cloud_url: str = "https://www.solaceagi.com", llm_client: Any = None):
        self.cloud_url = cloud_url
        self.llm_client = llm_client
        self.sessions: dict[str, dict[str, Any]] = {}
        self._pending_runs: dict[str, dict[str, Any]] = {}  # run_id → run state
        # Per-IP rate limiters — persists across reconnections from the same IP.
        # Prevents rate limit bypass by disconnect/reconnect.
        self._ip_rate_limiters: dict[str, _RateLimiter] = {}

    # Allowed WebSocket origins — extension + localhost server + Tauri
    _ALLOWED_WS_ORIGINS = frozenset({
        "http://localhost:8888",
        "http://127.0.0.1:8888",
    })

    async def handle_ws(self, request):
        """Handle WebSocket connection from browser JS."""
        from aiohttp import web, WSMsgType

        # P0 Security: Validate Origin header to prevent cross-site WS attacks
        # (DNS rebinding, cross-origin WS forgery)
        origin = request.headers.get("Origin", "")
        if origin and not origin.startswith("chrome-extension://") and origin not in self._ALLOWED_WS_ORIGINS:
            logger.warning(f"[YY] WebSocket rejected: unauthorized origin '{origin}'")
            raise web.HTTPForbidden(reason="WebSocket origin not allowed")

        ws = web.WebSocketResponse()
        await ws.prepare(request)

        session_id = request.match_info.get("session_id", "default")
        self.sessions[session_id] = {"ws": ws, "messages": []}

        # Per-IP rate limiting: same IP gets same limiter across reconnections.
        # Prevents bypass by disconnect/reconnect from exhausting the limit.
        peer_ip = request.remote or "unknown"
        if peer_ip not in self._ip_rate_limiters:
            self._ip_rate_limiters[peer_ip] = _RateLimiter(max_calls=60, period=60.0)
        rate_limiter = self._ip_rate_limiters[peer_ip]

        logger.info(f"[YY] WebSocket connected: {session_id}")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    if not rate_limiter.is_allowed():
                        await ws.send_json({"type": "error", "code": "RATE_LIMITED", "payload": {"message": "Rate limit exceeded — max 60 messages per 60s"}})
                        continue
                    try:
                        data = json.loads(msg.data)
                        response = await self._handle_message(session_id, data)
                        if response:
                            await ws.send_json(response)
                    except json.JSONDecodeError:
                        await ws.send_json({"type": "error", "code": "INVALID_JSON", "payload": {"message": "Invalid JSON"}})
                elif msg.type == WSMsgType.ERROR:
                    logger.warning(f"[YY] WS error: {ws.exception()}")
        finally:
            self.sessions.pop(session_id, None)
            logger.info(f"[YY] WebSocket disconnected: {session_id}")

        return ws

    # IPC wire format schema — validates incoming WebSocket messages
    _MESSAGE_SCHEMAS: dict[str, dict[str, Any]] = {
        "chat": {"required": [], "payload_fields": {"content": str}},
        "heartbeat": {"required": [], "payload_fields": {}},
        "detect": {"required": [], "payload_fields": {"url": str}},
        "run": {"required": [], "payload_fields": {"app_id": str}},
        "state": {"required": [], "payload_fields": {}},
        "approve": {"required": [], "payload_fields": {"run_id": str}},
        "reject": {"required": [], "payload_fields": {"run_id": str}},
        "schedule": {"required": [], "payload_fields": {"action": str}},
        "credits": {"required": [], "payload_fields": {}},
    }

    @classmethod
    def _validate_message(cls, data: dict) -> Optional[str]:
        """Validate a WebSocket message against the IPC schema.

        Returns None if valid, or an error string if invalid.
        """
        if not isinstance(data, dict):
            return "Message must be a JSON object"
        msg_type = data.get("type")
        if not msg_type or not isinstance(msg_type, str):
            return "Missing or invalid 'type' field"
        if msg_type not in cls._MESSAGE_SCHEMAS:
            return None  # Unknown types handled by dispatch (returns error)
        schema = cls._MESSAGE_SCHEMAS[msg_type]
        payload = data.get("payload", {})
        if not isinstance(payload, dict):
            # Some messages send fields at top level (e.g., detect with url)
            payload = data
        for field in schema.get("required", []):
            if field not in payload:
                return f"Missing required field '{field}' for type '{msg_type}'"
        return None

    async def _handle_message(self, session_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        # Validate IPC wire format
        validation_error = self._validate_message(data)
        if validation_error:
            return {"type": "error", "code": "INVALID_MESSAGE", "payload": {"message": validation_error}}

        msg_type = data.get("type", "")
        payload = data.get("payload", {})

        handler = {
            "chat": self._handle_chat,
            "heartbeat": self._handle_heartbeat,
            "detect": self._handle_detect,
            "run": self._handle_run,
            "state": self._handle_state,
            "approve": self._handle_approve,
            "reject": self._handle_reject,
            "schedule": self._handle_schedule,
            "credits": self._handle_credits,
        }.get(msg_type)

        if handler is None:
            return {"type": "error", "code": "UNKNOWN_TYPE", "payload": {"message": f"Unknown type: {msg_type}"}}

        return await handler(session_id, payload)

    # ── chat ──

    async def _handle_chat(self, session_id: str, payload: dict) -> dict:
        content = payload.get("content", "")
        rejection = _check_content(content)
        if rejection is not None:
            return {
                "type": "chat",
                "payload": {"content": rejection, "role": "assistant", "filtered": True},
            }
        # Redact PII before sending to local/external LLM processing.
        # Original content is kept in chat history for the user.
        redacted_content = self._redact_pii(content)
        response_text = self._local_response(redacted_content)
        return {
            "type": "chat",
            "payload": {"content": response_text, "role": "assistant"},
        }

    # ── heartbeat ──

    async def _handle_heartbeat(self, session_id: str, payload: dict) -> dict:
        # Protocol version negotiation — client sends version on first heartbeat
        client_version = payload.get("protocol_version", "")
        response_payload: dict[str, Any] = {
            "status": "ok",
            "server_version": self.PROTOCOL_VERSION,
        }
        if client_version:
            try:
                major = int(client_version.split(".")[0])
                if major not in self._SUPPORTED_MAJOR_VERSIONS:
                    return {
                        "type": "error",
                        "code": "VERSION_MISMATCH",
                        "payload": {
                            "message": f"Unsupported protocol version {client_version}. Server supports: {self.PROTOCOL_VERSION}",
                            "server_version": self.PROTOCOL_VERSION,
                            "client_version": client_version,
                        },
                    }
            except (ValueError, IndexError):
                pass  # Malformed version — ignore, just return heartbeat
            response_payload["client_version"] = client_version
        return {"type": "heartbeat", "payload": response_payload}

    # ── detect: URL-based app matching ──

    async def _handle_detect(self, session_id: str, payload: dict) -> dict:
        """Match installed apps against the given URL."""
        url = str(payload.get("url", "")).strip()
        if not url:
            return {"type": "detected", "payload": {"apps": [], "url": ""}}

        # Redact PII from the URL before any logging (query params may contain PII).
        safe_url = self._redact_pii(url)
        logger.debug(f"[YY] detect URL: {safe_url}")

        from urllib.parse import urlparse
        try:
            page_host = urlparse(url).hostname or ""
        except ValueError:
            return {"type": "detected", "payload": {"apps": [], "url": url}}

        page_path = urlparse(url).path or "/"

        apps = self._load_installed_apps()
        matched = []
        for app in apps:
            site = app.get("site", "")
            if not site:
                continue
            sites = site if isinstance(site, list) else [site]
            for s in sites:
                s = str(s).strip()
                domain_match = False
                if s.startswith("*."):
                    base = s[2:]
                    if page_host == base or page_host.endswith(f".{base}"):
                        domain_match = True
                else:
                    try:
                        app_host = urlparse(s if "://" in s else f"https://{s}").hostname or ""
                    except ValueError:
                        continue
                    if page_host == app_host or page_host.endswith(f".{app_host}"):
                        domain_match = True

                if not domain_match:
                    continue

                # Path prefix filter: if set, URL path must start with it
                path_prefix = app.get("path_prefix", "")
                if path_prefix and not page_path.startswith(str(path_prefix)):
                    continue

                matched.append(app)
                break

        return {"type": "detected", "payload": {"apps": matched, "url": url}}

    # ── run: trigger app execution (preview flow) ──

    async def _handle_run(self, session_id: str, payload: dict) -> dict:
        """Start an app run — loads recipe and puts it in preview_ready state."""
        app_id = str(payload.get("app_id", "")).strip()
        if not app_id:
            return {"type": "error", "code": "MISSING_FIELD", "payload": {"message": "missing app_id", "field": "app_id"}}

        apps_dir = Path(__file__).resolve().parent.parent.parent / "data" / "default" / "apps"
        recipe_path = apps_dir / app_id / "recipe.json"

        if not recipe_path.exists():
            return {"type": "state", "payload": {
                "status": "error",
                "app_id": app_id,
                "message": f"No recipe found for {app_id}",
            }}

        try:
            recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            return {"type": "state", "payload": {
                "status": "error",
                "app_id": app_id,
                "message": f"Failed to load recipe: {e}",
            }}

        run_id = str(uuid.uuid4())
        self._pending_runs[run_id] = {
            "run_id": run_id,
            "app_id": app_id,
            "status": "preview_ready",
            "recipe": recipe,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        return {"type": "state", "payload": {
            "status": "preview_ready",
            "run_id": run_id,
            "app_id": app_id,
            "recipe": recipe,
            "message": f"Recipe loaded for {app_id}. Approve to execute.",
        }}

    # ── state: return current sidebar state ──

    async def _handle_state(self, session_id: str, payload: dict) -> dict:
        """Return aggregated sidebar state."""
        pending_count = sum(
            1 for r in self._pending_runs.values() if r["status"] == "preview_ready"
        )
        return {"type": "state", "payload": {
            "connected": True,
            "pending_approvals": pending_count,
            "active_runs": [
                r for r in self._pending_runs.values() if r["status"] == "running"
            ],
        }}

    # ── approve / reject: approval queue actions ──

    async def _handle_approve(self, session_id: str, payload: dict) -> dict:
        run_id = str(payload.get("run_id", ""))
        run = self._pending_runs.get(run_id)
        if run is None:
            return {"type": "error", "code": "NOT_FOUND", "payload": {"message": f"Unknown run_id: {run_id}"}}
        if run["status"] != "preview_ready":
            return {"type": "error", "code": "INVALID_STATE", "payload": {"message": f"Run {run_id} not in preview_ready state", "current_state": run["status"]}}

        run["status"] = "running"
        run["approved_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"[YY] Run approved: {run_id} (app={run['app_id']})")

        # Actual execution would be dispatched here via the recipe engine.
        # For now, mark as sealed (deterministic replay placeholder).
        run["status"] = "sealed"
        run["sealed_at"] = datetime.now(timezone.utc).isoformat()

        return {"type": "state", "payload": {
            "status": "sealed",
            "run_id": run_id,
            "app_id": run["app_id"],
            "message": "Run approved and sealed.",
        }}

    async def _handle_reject(self, session_id: str, payload: dict) -> dict:
        run_id = str(payload.get("run_id", ""))
        run = self._pending_runs.get(run_id)
        if run is None:
            return {"type": "error", "code": "NOT_FOUND", "payload": {"message": f"Unknown run_id: {run_id}"}}

        run["status"] = "rejected"
        run["rejected_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"[YY] Run rejected: {run_id} (app={run['app_id']})")

        return {"type": "state", "payload": {
            "status": "rejected",
            "run_id": run_id,
            "app_id": run["app_id"],
            "message": "Run rejected.",
        }}

    # ── schedule: CRUD via WebSocket ──

    async def _handle_schedule(self, session_id: str, payload: dict) -> dict:
        """Thin WebSocket proxy for schedule CRUD (file-backed via REST handlers)."""
        action = str(payload.get("action", "list"))
        schedules_dir = Path.home() / ".solace" / "schedules"
        schedules_dir.mkdir(parents=True, exist_ok=True)

        if action == "list":
            schedules = []
            for path in sorted(schedules_dir.glob("*.json")):
                try:
                    s = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(s, dict):
                        schedules.append(s)
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    continue
            return {"type": "scheduled", "payload": {"action": "list", "schedules": schedules}}

        if action == "create":
            app_id = str(payload.get("app_id", "")).strip()
            cron_expr = str(payload.get("cron", "")).strip()
            if not app_id or not cron_expr:
                return {"type": "error", "code": "MISSING_FIELD", "payload": {"message": "schedule create requires app_id and cron"}}
            schedule = {
                "id": str(uuid.uuid4()),
                "app_id": app_id,
                "cron": cron_expr,
                "enabled": bool(payload.get("enabled", True)),
                "label": str(payload.get("label", "")),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "last_run": None,
                "next_run": None,
                "run_count": 0,
            }
            (schedules_dir / f"{schedule['id']}.json").write_text(
                json.dumps(schedule, indent=2), encoding="utf-8"
            )
            return {"type": "scheduled", "payload": {"action": "created", "schedule": schedule}}

        if action == "delete":
            sched_id = str(payload.get("schedule_id", ""))
            path = schedules_dir / f"{sched_id}.json"
            if path.exists():
                path.unlink()
                return {"type": "scheduled", "payload": {"action": "deleted", "schedule_id": sched_id}}
            return {"type": "error", "code": "NOT_FOUND", "payload": {"message": f"Schedule not found: {sched_id}"}}

        return {"type": "error", "code": "UNKNOWN_TYPE", "payload": {"message": f"Unknown schedule action: {action}"}}

    # ── credits: query user balance ──

    async def _handle_credits(self, session_id: str, payload: dict) -> dict:
        """Return credit balance info. Local-first = unlimited free tier."""
        return {"type": "credits", "payload": {
            "tier": "free",
            "balance": None,  # None = unlimited (local mode)
            "used_today": 0,
            "daily_limit": None,
            "message": "Local mode — no credit limits",
        }}

    # ── PII redaction ──

    @staticmethod
    def _redact_pii(text: str) -> str:
        """Redact PII patterns from text. Uses regex only (no external deps).

        Redacts:
          - Email addresses → [EMAIL]
          - SSN-like patterns (XXX-XX-XXXX) → [SSN]  (checked before phone)
          - Phone numbers (US/international) → [PHONE]
          - Credit card numbers (16 digits, optional separators) → [CARD]
          - IPv4 addresses → [IP]
          - JWTs (3 base64url segments) → [JWT]
          - API keys (sk-*, pk-*, key-*, api-* prefixed) → [API_KEY]
          - Bearer tokens in Authorization-like contexts → [BEARER]
          - Query-string secrets (?key=, ?token=, ?secret=, ?password=) → [QUERY_SECRET]
        """
        # JWT (three base64url segments separated by dots, each ≥10 chars)
        text = re.sub(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
            "[JWT]",
            text,
        )
        # API keys (common prefixes: sk-, pk-, key-, api-, AKIA for AWS)
        text = re.sub(
            r"\b(?:sk|pk|key|api|AKIA)[_\-][A-Za-z0-9_\-]{16,}\b",
            "[API_KEY]",
            text,
        )
        # Bearer tokens (Bearer <token> pattern)
        text = re.sub(
            r"(?i)\bBearer\s+[A-Za-z0-9_\-.~+/]{20,}\b",
            "[BEARER]",
            text,
        )
        # Email
        text = re.sub(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", "[EMAIL]", text)
        # SSN (must precede phone to avoid partial match)
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", text)
        # Phone — international (+1 234 567 8901) and US ((123) 456-7890 / 123-456-7890)
        text = re.sub(
            r"(?:\+\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b",
            "[PHONE]",
            text,
        )
        # Credit card (16 digits with optional spaces/dashes)
        text = re.sub(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b", "[CARD]", text)
        # IPv4
        text = re.sub(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b",
            "[IP]",
            text,
        )
        # Query-string secrets (?key=value, &token=value, etc.)
        text = re.sub(
            r"(?<=[?&])(?:key|token|secret|password|api_key|access_token|auth)=[^&\s]{4,}",
            lambda m: m.group(0).split("=")[0] + "=[QUERY_SECRET]",
            text,
            flags=re.IGNORECASE,
        )
        return text

    # ── helpers ──

    def _local_response(self, content: str) -> str:
        """Generate local response using keyword routing."""
        lower = content.lower()
        if any(w in lower for w in ["help", "what", "how"]):
            return "I'm Yinyang, your AI assistant. I can help you browse apps, install recipes, and automate tasks."
        if any(w in lower for w in ["app", "store", "install"]):
            return "Visit the App Store to browse available apps. Free tier includes Gmail Triage and Morning Brief."
        if any(w in lower for w in ["credit", "balance"]):
            return "Check your credits at /billing. Current balance shown in the credits panel above."
        return "I'm here to help! Ask me about apps, recipes, or automation."

    @staticmethod
    def _load_installed_apps() -> list[dict]:
        """Load app manifests from data/default/apps/."""
        apps_dir = Path(__file__).resolve().parent.parent.parent / "data" / "default" / "apps"
        apps = []
        if not apps_dir.is_dir():
            return apps
        for app_dir in sorted(apps_dir.iterdir()):
            manifest_path = app_dir / "manifest.yaml"
            if not manifest_path.exists():
                continue
            try:
                import yaml
                manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            except ImportError:
                manifest = _parse_yaml_basic(manifest_path)
            except (OSError, UnicodeDecodeError):
                continue
            if manifest and isinstance(manifest, dict):
                app_entry = {
                    "id": manifest.get("id", app_dir.name),
                    "name": manifest.get("name", app_dir.name),
                    "description": manifest.get("description", ""),
                    "site": manifest.get("site", ""),
                    "status": manifest.get("status", "available"),
                    "tier": manifest.get("tier", "free"),
                }
                if manifest.get("path_prefix"):
                    app_entry["path_prefix"] = manifest["path_prefix"]
                apps.append(app_entry)
        return apps


def _parse_yaml_basic(path: Path) -> dict:
    """Minimal YAML parser for flat key-value manifests."""
    result = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and not key.startswith(" "):
                    result[key] = value
    except (OSError, UnicodeDecodeError):
        pass
    return result
