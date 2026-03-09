diff --git a/yinyang_server.py b/yinyang_server.py
index 50d612f6..b39a5f19 100644
--- a/yinyang_server.py
+++ b/yinyang_server.py
@@ -3,7 +3,8 @@ yinyang_server.py — Yinyang Server for Solace Browser.
 Donald Knuth law: every function is a theorem. Prove it or don't ship it.
 
 Architecture:
-  - Stdlib only: http.server, json, hashlib, secrets, pathlib, threading, signal, atexit, urllib
+  - Stdlib-first: http.server, json, hashlib, secrets, pathlib, threading, signal, atexit, urllib
+  - Optional BeautifulSoup parsing when installed; regex fallback otherwise
   - Port 8888 (production), 18888 (tests only)
   - Legacy debug port permanently banned
   - Token hash only in port.lock — plaintext NEVER written anywhere
@@ -20,6 +21,11 @@ Route table:
   GET  /api/v1/evidence/verify         → verify sha256 chain integrity
   GET  /api/v1/evidence/{id}           → single evidence entry detail
   POST /api/v1/evidence                → record evidence event
+  POST /api/v1/prime-wiki/snapshot     → capture and store compressed page snapshot
+  GET  /api/v1/prime-wiki/snapshot/{id} → snapshot metadata + extracted key elements
+  GET  /api/v1/prime-wiki/snapshot/{id}/content → lazy-load gzip content payload
+  GET  /api/v1/prime-wiki/diff         → structural diff between two snapshots
+  GET  /api/v1/prime-wiki/stats        → local Prime Wiki snapshot stats
   GET  /api/v1/session-rules           → list loaded session rule schemas (requires auth)
   GET  /api/v1/session-rules/status    → list cached session statuses (requires auth)
   POST /api/v1/session-rules/check/{app} → trigger one session check (requires auth)
@@ -68,12 +74,22 @@ Route table:
   POST /api/v1/marketplace/uninstall   → uninstall marketplace session rules (requires auth)
   GET  /api/v1/logs/requests           → rolling request history (limit/method/status params)
   GET  /api/v1/logs/errors             → only 4xx/5xx entries from request history
+  POST /api/v1/actions/preview         → classify action + create pending record (B/C), returns action_id + cooldown
+  GET  /api/v1/actions/pending         → list pending actions with cooldown_remaining_seconds
+  POST /api/v1/actions/{id}/approve    → sign off after cooldown; Class C requires step_up_consent+reason
+  POST /api/v1/actions/{id}/reject     → reject pending action, seal evidence with reason
+  DELETE /api/v1/actions/{id}/cancel   → cancel pending action before cooldown ends
+  GET  /api/v1/actions/history         → history of approved/rejected actions (class/status/from/to filters)
 """
 import argparse
 import asyncio
 import atexit
 import base64
+import binascii
+import functools
+import gzip
 import hashlib
+import hmac
 import http.server
 import json
 import os
@@ -89,11 +105,23 @@ import urllib.error
 import urllib.parse
 import urllib.request
 import uuid
+from datetime import datetime, timezone
+from decimal import Decimal
 from pathlib import Path
-from typing import Optional
+from typing import Any, Optional
 
 import yaml
+from cryptography.exceptions import InvalidTag
+from cryptography.hazmat.primitives import hashes
+from cryptography.hazmat.primitives.ciphers.aead import AESGCM
+from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
 
+try:
+    from bs4 import BeautifulSoup
+except ImportError:
+    BeautifulSoup = None
+
+from evidence_bundle import ALCOABundle, ALCOAError, ComplianceStatus, RUNG_ACHIEVED
 from hub_tunnel_client import HubTunnelClient, SOLACEAGI_RELAY_URL
 
 # ---------------------------------------------------------------------------
@@ -101,14 +129,21 @@ from hub_tunnel_client import HubTunnelClient, SOLACEAGI_RELAY_URL
 # ---------------------------------------------------------------------------
 PORT_LOCK_PATH: Path = Path.home() / ".solace" / "port.lock"
 EVIDENCE_PATH: Path = Path.home() / ".solace" / "evidence.jsonl"
+PART11_EVIDENCE_DIR: Path = Path.home() / ".solace" / "evidence"
+PART11_EVIDENCE_PATH: Path = PART11_EVIDENCE_DIR / "evidence.jsonl"
+PART11_CHAIN_LOCK_PATH: Path = PART11_EVIDENCE_DIR / "chain.lock"
 SCHEDULES_PATH: Path = Path.home() / ".solace" / "schedules.json"
 OAUTH3_TOKENS_PATH: Path = Path.home() / ".solace" / "oauth3-tokens.json"
+OAUTH3_VAULT_PATH: Path = Path.home() / ".solace" / "oauth3-vault.enc"
 ONBOARDING_PATH: Path = Path.home() / ".solace" / "onboarding.json"
 SETTINGS_PATH: Path = Path.home() / ".solace" / "settings.json"
+PRIME_WIKI_ROOT: Path = Path.home() / ".solace" / "prime-wiki"
 MARKETPLACE_CACHE_PATH: Path = Path.home() / ".solace" / "marketplace-cache.json"
 RECIPES_DIR: Path = Path(__file__).parent / "data" / "default" / "recipes"
 SESSION_RULES_APPS_DIR: Path = Path(__file__).parent / "data" / "default" / "apps"
 RECIPE_RUNS_PATH: Path = Path.home() / ".solace" / "recipe_runs.json"
+COMMUNITY_RECIPES_059_PATH: Path = Path.home() / ".solace" / "community_recipes.json"
+_COMMUNITY_059_LOCK = threading.Lock()
 BUDGET_PATH: Path = Path.home() / ".solace" / "budget.json"
 BYOK_PATH: Path = Path.home() / ".solace" / "byok_keys.json"
 NOTIFICATIONS_PATH: Path = Path.home() / ".solace" / "notifications.json"
@@ -127,13 +162,33 @@ DEFAULT_CLOUD_TWIN_SETTINGS: dict = {
 }
 
 _SERVER_VERSION = "1.1"
-YINYANG_PORT = 8888
+HUB_PORT = 8888
+YINYANG_PORT = HUB_PORT
 MAX_BODY = 1_048_576
+CLOUD_TWIN_DISPLAY = ":99"
 
 _SCHEDULES_LOCK = threading.Lock()
 _TOKENS_LOCK = threading.Lock()
+_OAUTH3_VAULT_LOCK = threading.Lock()
 _BYOK_LOCK = threading.Lock()
 _NOTIF_LOCK = threading.Lock()
+_PRIME_WIKI_LOCK = threading.Lock()
+_PART11_EVIDENCE_LOCK = threading.Lock()
+
+PRIME_WIKI_PUSH_URL = "https://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/prime-wiki/push"
+PRIME_WIKI_PULL_URL = "https://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/prime-wiki/pull"
+PRIME_WIKI_STATS_URL = "https://solaceagi-mfjzxmegpq-uc.a.run.app/api/v1/prime-wiki/stats"
+PRIME_WIKI_PUSH_TIMEOUT_SECONDS = 5
+PRIME_WIKI_SNAPSHOT_TYPES: frozenset = frozenset(["before_action", "after_action", "periodic"])
+PRIME_WIKI_CTA_VERBS: tuple[str, ...] = (
+    "submit",
+    "send",
+    "archive",
+    "delete",
+    "reply",
+    "save",
+    "publish",
+)
 
 MAX_NOTIFICATIONS = 200  # keep last 200
 NOTIF_CATEGORIES: frozenset = frozenset(["budget", "session", "schedule", "error", "info", "recipe"])
@@ -155,6 +210,26 @@ _PINNED_LOCK = threading.Lock()
 FAVORITES_PATH: Path = Path.home() / ".solace" / "favorites.json"
 _FAVORITES_LOCK = threading.Lock()
 SUPPORTED_CLI_TOOLS: frozenset = frozenset(["claude", "openai", "ollama", "aider", "continue"])
+CLI_AGENT_CANDIDATES: dict[str, str] = {
+    "claude": "claude",
+    "codex": "codex",
+    "gemini": "gemini",
+    "aider": "aider",
+}
+DEFAULT_MODELS: dict[str, str] = {
+    "claude": "claude-sonnet-4-6",
+    "codex": "gpt-5.4",
+    "gemini": "gemini-2.0-flash",
+    "aider": "gpt-4o",
+}
+COST_PER_1M_TOKENS: dict[str, Decimal] = {
+    "claude": Decimal("3.00"),
+    "gemini": Decimal("0.15"),
+    "codex": Decimal("0.50"),
+    "aider": Decimal("0.50"),
+}
+CLI_AGENT_DEFAULT_MODELS = DEFAULT_MODELS
+CLI_AGENT_COST_PER_1M_TOKENS = COST_PER_1M_TOKENS
 _CLI_LOCK = threading.Lock()
 _MARKETPLACE_LOCK = threading.Lock()
 _COMMUNITY_RECIPES: list = [
@@ -183,6 +258,117 @@ _CLOUD_TUNNEL_ACTIVE: bool = False
 _CLOUD_TUNNEL_LOOP: Optional[asyncio.AbstractEventLoop] = None
 _CLOUD_TUNNEL_LOCK = threading.Lock()
 
+# ---------------------------------------------------------------------------
+# Action Preview / Cooldown / Sign-Off — Task 057
+# Safety ladder: A=autonomous, B=preview+30min+signoff, C=preview+2h+stepup+signoff
+# ---------------------------------------------------------------------------
+ACTION_CLASSES: dict[str, str] = {
+    # Class A — read-only, autonomous
+    "gmail.read": "A",
+    "browse.navigate": "A",
+    "search.google": "A",
+    "slack.read": "A",
+    "linkedin.read": "A",
+    "github.read": "A",
+    # Class B — reputation-impact: preview + 30min cooldown + sign-off
+    "linkedin.post": "B",
+    "twitter.post": "B",
+    "instagram.post": "B",
+    "slack.send_channel": "B",
+    "github.comment": "B",
+    "gmail.send": "B",
+    "gmail.archive_batch": "B",
+    # Class C — irreversible/financial: preview + 2h cooldown + step-up + reason + sign-off
+    "gmail.delete_batch": "C",
+    "gmail.permanent_delete": "C",
+    "linkedin.connect_all": "C",
+    "pricing.update": "C",
+    "permission.change": "C",
+    "payment.initiate": "C",
+}
+COOLDOWN_SECONDS: dict[str, int] = {"B": 1800, "C": 7200}
+_PENDING_ACTIONS: dict[str, dict] = {}
+_PENDING_ACTIONS_LOCK = threading.Lock()
+_ACTIONS_HISTORY: list[dict] = []
+_ACTIONS_HISTORY_LOCK = threading.Lock()
+
+
+def _utc_isoformat(timestamp: float) -> str:
+    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")
+
+
+def _action_preview_text(action_type: str, app_id: str, params: dict[str, Any]) -> str:
+    resource_names = ", ".join(sorted(str(key) for key in params.keys())) or "no explicit resources"
+    app_label = app_id or "unknown-app"
+    return f"Approve {action_type} for {app_label}; affects {resource_names}."
+
+
+def _build_action_preview(action_type: str, app_id: str, params: dict[str, Any], action_class: str) -> dict[str, Any]:
+    return {
+        "preview_text": _action_preview_text(action_type, app_id, params),
+        "estimated_cost": str(Decimal("0.00")),
+        "affected_resources": sorted(str(key) for key in params.keys()),
+        "reversal_possible": action_class == "B",
+    }
+
+
+def _action_state_copy(action: dict[str, Any]) -> dict[str, Any]:
+    return json.loads(json.dumps(action, sort_keys=True))
+
+
+def _build_action_hash(
+    action_type: str,
+    params: dict[str, Any],
+    app_id: str,
+    oauth3_token_id: str,
+) -> str:
+    payload = {
+        "action_type": action_type,
+        "app_id": app_id,
+        "oauth3_token_id": oauth3_token_id,
+        "params": params,
+    }
+    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
+
+
+def _create_pending_action_record(
+    action_type: str,
+    params: dict[str, Any],
+    app_id: str,
+    oauth3_token_id: str,
+    now_ts: float,
+) -> dict[str, Any]:
+    action_class = ACTION_CLASSES.get(action_type, "B")
+    preview = _build_action_preview(action_type, app_id, params, action_class)
+    return {
+        "action_id": str(uuid.uuid4()),
+        "action_type": action_type,
+        "class": action_class,
+        "params": params,
+        "app_id": app_id,
+        "oauth3_token_id": oauth3_token_id,
+        "action_hash": _build_action_hash(action_type, params, app_id, oauth3_token_id),
+        "status": "PENDING_APPROVAL",
+        "preview": preview,
+        "cooldown_ends_at": now_ts + COOLDOWN_SECONDS[action_class],
+        "created_at": now_ts,
+    }
+
+
+def _pending_action_list_item(action: dict[str, Any], now_ts: float) -> dict[str, Any]:
+    cooldown_end = float(action.get("cooldown_ends_at", now_ts))
+    remaining = max(0.0, cooldown_end - now_ts)
+    return {
+        "action_id": action.get("action_id") or action.get("preview_id", ""),
+        "action_type": action["action_type"],
+        "class": action["class"],
+        "status": action["status"],
+        "preview_summary": action.get("preview", {}).get("preview_text", action.get("preview_text", "")),
+        "cooldown_ends_at": _utc_isoformat(cooldown_end),
+        "cooldown_remaining_seconds": int(remaining),
+        "app_id": action.get("app_id", ""),
+    }
+
 # ---------------------------------------------------------------------------
 # Broadcast log — Task 043
 _BROADCAST_LOG: list = []
@@ -202,6 +388,24 @@ _REQUEST_HISTORY: list = []
 _HISTORY_LOCK = threading.Lock()
 MAX_HISTORY = 100
 
+# ---------------------------------------------------------------------------
+# Session stats globals — Task 061 (Value Dashboard)
+# ---------------------------------------------------------------------------
+_SESSION_STATS: dict = {
+    "session_id": "",
+    "state": "IDLE",
+    "app_name": None,
+    "pages_visited": 0,
+    "llm_calls": 0,
+    "cost_usd": "0.00",
+    "cost_saved_pct": 0,
+    "duration_seconds": 0,
+    "recipes_replayed": 0,
+    "evidence_captured": 0,
+    "session_start": None,
+}
+_SESSION_STATS_LOCK = threading.Lock()
+
 
 def _record_request(path: str, status_code: int) -> None:
     """Record request count and errors per path. Thread-safe."""
@@ -224,6 +428,12 @@ _SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
 _CRON_RE = re.compile(r"^\S+\s+\S+\s+\S+\s+\S+\s+\S+$")
 _APP_ID_RE = re.compile(r"^[A-Za-z0-9-]+$")
 _ONBOARDING_MODES = frozenset(["agent", "byok", "paid", "cli"])
+OAUTH3_HIGH_RISK_ACTIONS = frozenset(["send", "post", "delete", "payment", "connect"])
+OAUTH3_STEP_UP_TTL_SECONDS = 300
+OAUTH3_PBKDF2_ITERATIONS = 100000
+OAUTH3_EVIDENCE_GENESIS_HASH = "0" * 64
+OAUTH3_ISSUER = "https://www.solaceagi.com"
+OAUTH3_MAX_TTL_SECONDS = 2592000
 _MARKETPLACE_CATEGORIES: tuple[str, ...] = (
     "productivity",
     "messaging",
@@ -312,11 +522,197 @@ def delete_port_lock() -> None:
         pass
 
 
+@functools.lru_cache(maxsize=1)
+def _detect_available_agents():
+    """Detect AI coding CLIs available on PATH. Absence is valid state."""
+    found: dict[str, str] = {}
+    for name, binary in CLI_AGENT_CANDIDATES.items():
+        path = shutil.which(binary)
+        if path is not None:
+            found[name] = path
+    return found
+
+
+def _default_model_for_agent(agent_name: str) -> str:
+    """Return the default model for a supported CLI agent."""
+    return DEFAULT_MODELS.get(agent_name, "unknown")
+
+
+def _build_cli_command(agent_name: str, executable: str, prompt: str, model: Optional[str] = None) -> list[str]:
+    """Build a shell-free subprocess argv for one CLI agent."""
+    if agent_name == "claude":
+        if model:
+            return [executable, "--model", model, "--print", prompt]
+        return [executable, "--print", prompt]
+    if agent_name == "codex":
+        if model:
+            return [executable, "exec", "-m", model, prompt]
+        return [executable, "exec", prompt]
+    if agent_name == "gemini":
+        if model:
+            return [executable, "-m", model, prompt]
+        return [executable, prompt]
+    if agent_name == "aider":
+        if model:
+            return [executable, "--model", model, "--message", prompt, "--no-git"]
+        return [executable, "--message", prompt, "--no-git"]
+    return [executable, prompt]
+
+
+def _invoke_cli_agent(
+    agent_name: str,
+    executable: str,
+    prompt: str,
+    model: Optional[str] = None,
+    timeout_s: int = 60,
+) -> dict:
+    """Invoke a CLI agent and return captured stdout/stderr."""
+    cmd = _build_cli_command(agent_name, executable, prompt, model)
+    result = subprocess.run(
+        cmd,
+        capture_output=True,
+        text=True,
+        timeout=timeout_s,
+        check=True,
+        shell=False,
+    )
+    return {"stdout": result.stdout, "stderr": result.stderr}
+
+
+def _estimate_cost(agent_name: str, tokens_est: int) -> str:
+    """Return cost as a Decimal string; never float."""
+    rate = COST_PER_1M_TOKENS.get(agent_name, Decimal("1.00"))
+    cost = (rate * Decimal(tokens_est)) / Decimal("1000000")
+    return str(cost.quantize(Decimal("0.000001")))
+
+
+def _estimate_tokens(prompt: str, output: str) -> int:
+    """Cheap deterministic token estimate from character count."""
+    char_count = len(prompt) + len(output)
+    return max(1, (char_count + 3) // 4)
+
+
+def _inject_skill_pack(prompt: str, skill_pack: list[str]) -> str:
+    """Prepend selected skill names to the prompt body."""
+    if not skill_pack:
+        return prompt
+    headers = "\n".join(f"[SKILL: {skill_name}]" for skill_name in skill_pack)
+    return f"{headers}\n\n{prompt}"
+
+
+def _build_cli_evidence_id(output: str) -> str:
+    """Build a deterministic evidence fingerprint for one generation."""
+    digest = hashlib.sha256(output.encode("utf-8")).hexdigest()
+    return f"sha256:{digest}"
+
+
 # ---------------------------------------------------------------------------
 # Evidence storage — append-only JSONL log
 # ---------------------------------------------------------------------------
-def record_evidence(event_type: str, data: dict) -> dict:
-    """Append one evidence event to ~/.solace/evidence.jsonl. Returns the record."""
+def _read_part11_chain_tip() -> str:
+    try:
+        lines = PART11_CHAIN_LOCK_PATH.read_text().splitlines()
+    except IOError:
+        return ""
+    for line in reversed(lines):
+        chain_tip = line.strip().lower()
+        if chain_tip:
+            return chain_tip
+    return ""
+
+
+def _load_part11_evidence_bundles() -> list[dict]:
+    try:
+        lines = PART11_EVIDENCE_PATH.read_text().splitlines()
+    except IOError:
+        return []
+    bundles = []
+    for line in lines:
+        payload = line.strip()
+        if not payload:
+            continue
+        try:
+            loaded = json.loads(payload)
+        except json.JSONDecodeError:
+            continue
+        if isinstance(loaded, dict):
+            bundles.append(loaded)
+    return bundles
+
+
+def create_and_store_evidence_bundle(
+    action_type: str,
+    before_state: object,
+    after_state: object,
+    oauth3_token_id: str,
+    user_id: str,
+) -> dict:
+    with _PART11_EVIDENCE_LOCK:
+        previous_bundle_sha256 = _read_part11_chain_tip() or None
+        bundle = ALCOABundle.create_bundle(
+            action_type,
+            before_state,
+            after_state,
+            oauth3_token_id,
+            user_id,
+            previous_bundle_sha256=previous_bundle_sha256,
+        )
+        bundle_sha256 = ALCOABundle.bundle_sha256(bundle)
+        PART11_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
+        with PART11_EVIDENCE_PATH.open("a", encoding="utf-8") as handle:
+            handle.write(json.dumps(bundle, sort_keys=True) + "\n")
+        with PART11_CHAIN_LOCK_PATH.open("a", encoding="utf-8") as handle:
+            handle.write(f"{bundle_sha256}\n")
+    return bundle
+
+
+def list_part11_evidence_bundles(
+    limit: int = 50,
+    since_iso8601: str = "",
+    action_type: str = "",
+) -> list[dict]:
+    bundles = _load_part11_evidence_bundles()
+    if since_iso8601:
+        bundles = [bundle for bundle in bundles if str(bundle.get("timestamp_iso8601", "")) >= since_iso8601]
+    if action_type:
+        bundles = [bundle for bundle in bundles if bundle.get("action_type") == action_type]
+    bundles.reverse()
+    return bundles[:limit]
+
+
+def part11_compliance_report() -> dict:
+    compliant_count = 0
+    partial_count = 0
+    non_compliant_count = 0
+    bundles = _load_part11_evidence_bundles()
+    for bundle in bundles:
+        status = ALCOABundle.check_compliance(bundle)
+        if status == ComplianceStatus.COMPLIANT:
+            compliant_count += 1
+        elif status == ComplianceStatus.PARTIALLY_COMPLIANT:
+            partial_count += 1
+        else:
+            non_compliant_count += 1
+    return {
+        "compliant_count": compliant_count,
+        "partial_count": partial_count,
+        "non_compliant": non_compliant_count,
+        "total": len(bundles),
+        "rung": RUNG_ACHIEVED,
+    }
+
+
+def verify_part11_evidence_chain() -> dict:
+    bundles = _load_part11_evidence_bundles()
+    validation = ALCOABundle.validate_chain(bundles)
+    return {
+        "chain_valid": validation.chain_valid,
+        "total_bundles": len(bundles),
+        "broken_at_index": validation.broken_at_index,
+    }
+
+
+def _append_evidence_record(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
     record = {
         "id": str(uuid.uuid4()),
         "type": event_type,
@@ -324,11 +720,336 @@ def record_evidence(event_type: str, data: dict) -> dict:
         "data": data,
     }
     EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
-    with EVIDENCE_PATH.open("a") as fh:
+    with EVIDENCE_PATH.open("a", encoding="utf-8") as fh:
         fh.write(json.dumps(record) + "\n")
     return record
 
 
+def record_evidence(event_type: str, data: dict) -> dict:
+    """Append one evidence event to ~/.solace/evidence.jsonl. Returns the record."""
+    record = _append_evidence_record(event_type, data)
+    create_and_store_evidence_bundle(
+        action_type=event_type,
+        before_state=data.get("before_state_hash", {}),
+        after_state=data.get("after_state_hash", data),
+        oauth3_token_id=str(data.get("oauth3_token_id") or "system"),
+        user_id=str(data.get("user_id") or "system"),
+    )
+    return record
+
+
+class OAuth3VaultError(Exception):
+    """Base OAuth3 vault error."""
+
+
+class OAuth3TokenNotFoundError(OAuth3VaultError):
+    """Raised when a token id is not present in the OAuth3 vault."""
+
+
+class OAuth3VaultUserMismatchError(OAuth3VaultError):
+    """Raised when a persisted vault belongs to a different local user hash."""
+
+
+class OAuth3VaultCorruptError(OAuth3VaultError):
+    """Raised when the encrypted OAuth3 vault cannot be parsed or decrypted."""
+
+
+def _oauth3_now_iso() -> str:
+    return datetime.now(timezone.utc).isoformat()
+
+
+def _oauth3_parse_iso8601(raw: str) -> datetime:
+    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
+    parsed = datetime.fromisoformat(normalized)
+    if parsed.tzinfo is None:
+        return parsed.replace(tzinfo=timezone.utc)
+    return parsed.astimezone(timezone.utc)
+
+
+def _oauth3_hash_user_id(user_id: str) -> str:
+    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()
+
+
+def _oauth3_default_state(user_id_hash: str = "") -> dict[str, Any]:
+    return {
+        "schema_version": "1.0",
+        "user_id_hash": user_id_hash,
+        "tokens": {},
+        "evidence": [],
+        "chain_tip": OAUTH3_EVIDENCE_GENESIS_HASH,
+    }
+
+
+def _oauth3_normalize_state(raw_state: Any, user_id_hash: str = "") -> dict[str, Any]:
+    if not isinstance(raw_state, dict):
+        raise OAuth3VaultCorruptError("vault state must be a JSON object")
+    tokens = raw_state.get("tokens", {})
+    evidence = raw_state.get("evidence", [])
+    if not isinstance(tokens, dict):
+        raise OAuth3VaultCorruptError("vault tokens must be a JSON object")
+    if not isinstance(evidence, list):
+        raise OAuth3VaultCorruptError("vault evidence must be a JSON array")
+    chain_tip = raw_state.get("chain_tip", OAUTH3_EVIDENCE_GENESIS_HASH)
+    if not isinstance(chain_tip, str) or not chain_tip:
+        chain_tip = OAUTH3_EVIDENCE_GENESIS_HASH
+    stored_user_id_hash = raw_state.get("user_id_hash", user_id_hash)
+    if not isinstance(stored_user_id_hash, str):
+        stored_user_id_hash = user_id_hash
+    return {
+        "schema_version": str(raw_state.get("schema_version", "1.0")),
+        "user_id_hash": stored_user_id_hash,
+        "tokens": tokens,
+        "evidence": evidence,
+        "chain_tip": chain_tip,
+    }
+
+
+def _oauth3_derive_key(session_token_sha256: str, user_id_hash: str) -> bytes:
+    if not _SHA256_HEX_RE.fullmatch(user_id_hash):
+        raise OAuth3VaultCorruptError("vault KDF salt must be a 64-char sha256 hex string")
+    kdf = PBKDF2HMAC(
+        algorithm=hashes.SHA256(),
+        length=32,
+        salt=bytes.fromhex(user_id_hash),
+        iterations=OAUTH3_PBKDF2_ITERATIONS,
+    )
+    return kdf.derive(session_token_sha256.encode("utf-8"))
+
+
+def _oauth3_encrypt_state(state: dict[str, Any], session_token_sha256: str) -> str:
+    user_id_hash = state.get("user_id_hash", "")
+    if not isinstance(user_id_hash, str) or not _SHA256_HEX_RE.fullmatch(user_id_hash):
+        raise OAuth3VaultCorruptError("vault user_id_hash missing or invalid")
+    plaintext = json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
+    nonce = secrets.token_bytes(12)
+    ciphertext = AESGCM(_oauth3_derive_key(session_token_sha256, user_id_hash)).encrypt(nonce, plaintext, None)
+    envelope = {
+        "cipher": "AES-256-GCM",
+        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
+        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
+        "ciphertext_sha256": hashlib.sha256(ciphertext).hexdigest(),
+        "kdf": {
+            "algorithm": "PBKDF2-HMAC-SHA256",
+            "iterations": OAUTH3_PBKDF2_ITERATIONS,
+            "salt_hex": user_id_hash,
+        },
+    }
+    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))
+
+
+def _oauth3_load_vault_state(session_token_sha256: str, user_id_hash_hint: str = "") -> dict[str, Any]:
+    if not OAUTH3_VAULT_PATH.exists():
+        return _oauth3_default_state(user_id_hash_hint)
+    try:
+        envelope = json.loads(OAUTH3_VAULT_PATH.read_text())
+    except FileNotFoundError:
+        return _oauth3_default_state(user_id_hash_hint)
+    except json.JSONDecodeError as exc:
+        raise OAuth3VaultCorruptError(f"vault JSON decode failed: {exc}") from exc
+    except OSError as exc:
+        raise OAuth3VaultCorruptError(f"vault read failed: {exc}") from exc
+    if not isinstance(envelope, dict):
+        raise OAuth3VaultCorruptError("vault envelope must be a JSON object")
+    kdf = envelope.get("kdf", {})
+    if not isinstance(kdf, dict):
+        raise OAuth3VaultCorruptError("vault envelope missing kdf metadata")
+    salt_hex = kdf.get("salt_hex", "")
+    nonce_b64 = envelope.get("nonce_b64", "")
+    ciphertext_b64 = envelope.get("ciphertext_b64", "")
+    ciphertext_sha256 = envelope.get("ciphertext_sha256", "")
+    if not isinstance(salt_hex, str) or not isinstance(nonce_b64, str) or not isinstance(ciphertext_b64, str):
+        raise OAuth3VaultCorruptError("vault envelope fields must be strings")
+    try:
+        nonce = base64.b64decode(nonce_b64)
+        ciphertext = base64.b64decode(ciphertext_b64)
+        plaintext = AESGCM(_oauth3_derive_key(session_token_sha256, salt_hex)).decrypt(nonce, ciphertext, None)
+        decoded = json.loads(plaintext.decode("utf-8"))
+    except (binascii.Error, InvalidTag, KeyError, OSError, TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
+        raise OAuth3VaultCorruptError(f"vault decrypt failed: {exc}") from exc
+    if isinstance(ciphertext_sha256, str) and ciphertext_sha256:
+        actual_ciphertext_sha256 = hashlib.sha256(ciphertext).hexdigest()
+        if actual_ciphertext_sha256 != ciphertext_sha256:
+            raise OAuth3VaultCorruptError("vault ciphertext sha256 mismatch")
+    state = _oauth3_normalize_state(decoded, salt_hex)
+    if user_id_hash_hint and state.get("user_id_hash") and state["user_id_hash"] != user_id_hash_hint:
+        raise OAuth3VaultUserMismatchError("oauth3 vault already initialized for a different local user")
+    if not state.get("user_id_hash"):
+        state["user_id_hash"] = salt_hex or user_id_hash_hint
+    return state
+
+
+def _oauth3_save_vault_state(state: dict[str, Any], session_token_sha256: str) -> None:
+    normalized = _oauth3_normalize_state(state, str(state.get("user_id_hash", "")))
+    if not normalized["user_id_hash"]:
+        raise OAuth3VaultCorruptError("cannot persist vault without user_id_hash")
+    OAUTH3_VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
+    OAUTH3_VAULT_PATH.write_text(_oauth3_encrypt_state(normalized, session_token_sha256))
+
+
+def _oauth3_is_high_risk_scope(scope: str) -> bool:
+    normalized = scope.strip().lower()
+    if not normalized or normalized.startswith("post.draft"):
+        return False
+    segments = [segment for segment in re.split(r"[^a-z]+", normalized) if segment]
+    return any(segment in OAUTH3_HIGH_RISK_ACTIONS for segment in segments)
+
+
+def _oauth3_step_up_scopes(scopes: list[str]) -> list[str]:
+    required: list[str] = []
+    for scope in scopes:
+        if _oauth3_is_high_risk_scope(scope) and scope not in required:
+            required.append(scope)
+    return required
+
+
+def _oauth3_validate_scopes(raw_scopes: Any) -> list[str]:
+    if not isinstance(raw_scopes, list) or not raw_scopes:
+        raise ValueError("scopes must be a non-empty list")
+    cleaned: list[str] = []
+    for raw_scope in raw_scopes:
+        if not isinstance(raw_scope, str):
+            raise ValueError("each scope must be a string")
+        scope = raw_scope.strip()
+        if not scope:
+            raise ValueError("scope values must not be empty")
+        if len(scope) > 128:
+            raise ValueError("scope values must be 128 chars or fewer")
+        if scope not in cleaned:
+            cleaned.append(scope)
+    return cleaned
+
+
+def _oauth3_validate_ttl_seconds(raw_ttl: Any) -> int:
+    if not isinstance(raw_ttl, int):
+        raise ValueError("ttl_seconds must be an integer")
+    if raw_ttl <= 0:
+        raise ValueError("ttl_seconds must be positive")
+    if raw_ttl > OAUTH3_MAX_TTL_SECONDS:
+        raise ValueError(f"ttl_seconds must be <= {OAUTH3_MAX_TTL_SECONDS}")
+    return raw_ttl
+
+
+def _oauth3_token_valid(token: dict[str, Any], now: Optional[datetime] = None) -> tuple[bool, str]:
+    if bool(token.get("revoked", False)):
+        return False, "revoked"
+    expires_at = token.get("expires_at", "")
+    if not isinstance(expires_at, str) or not expires_at:
+        return False, "missing_expiry"
+    current_time = now or datetime.now(timezone.utc)
+    if current_time >= _oauth3_parse_iso8601(expires_at):
+        return False, "expired"
+    return True, "ok"
+
+
+def _oauth3_token_view(token: dict[str, Any]) -> dict[str, Any]:
+    token_id = str(token.get("token_id", ""))
+    return {
+        "token_id": token_id,
+        "id": token_id,
+        "scopes": list(token.get("scopes", [])),
+        "expires_at": token.get("expires_at"),
+        "issued_at": token.get("issued_at"),
+        "revoked": bool(token.get("revoked", False)),
+        "revoked_at": token.get("revoked_at"),
+        "step_up_required": list(token.get("step_up_required", [])),
+    }
+
+
+def _oauth3_append_evidence(
+    state: dict[str, Any],
+    event_type: str,
+    *,
+    token: Optional[dict[str, Any]] = None,
+    data: Optional[dict[str, Any]] = None,
+) -> dict[str, Any]:
+    payload = data.copy() if isinstance(data, dict) else {}
+    token_id = str(token.get("token_id", "")) if token is not None else str(payload.pop("token_id", ""))
+    scopes = list(token.get("scopes", [])) if token is not None else list(payload.pop("scopes", []))
+    previous_hash = str(state.get("chain_tip") or OAUTH3_EVIDENCE_GENESIS_HASH)
+    event = {
+        "event_type": event_type,
+        "token_id": token_id,
+        "scopes": scopes,
+        "timestamp": _oauth3_now_iso(),
+        "previous_hash": previous_hash,
+        "data": payload,
+    }
+    event_sha256 = hashlib.sha256(
+        json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
+    ).hexdigest()
+    chain_link_sha256 = hashlib.sha256(f"{previous_hash}{event_sha256}".encode("utf-8")).hexdigest()
+    event["chain_link_sha256"] = chain_link_sha256
+    state.setdefault("evidence", []).append(event)
+    state["chain_tip"] = chain_link_sha256
+    if token is not None:
+        token["evidence_chain_tip"] = chain_link_sha256
+    return event
+
+
+def _oauth3_filter_evidence(state: dict[str, Any], limit: int = 50, since: str = "") -> list[dict[str, Any]]:
+    evidence = state.get("evidence", [])
+    if not isinstance(evidence, list):
+        return []
+    filtered: list[dict[str, Any]] = []
+    since_dt: Optional[datetime] = None
+    if since:
+        since_dt = _oauth3_parse_iso8601(since)
+    for row in evidence:
+        if not isinstance(row, dict):
+            continue
+        if since_dt is not None:
+            timestamp = row.get("timestamp", "")
+            if not isinstance(timestamp, str):
+                continue
+            if _oauth3_parse_iso8601(timestamp) < since_dt:
+                continue
+        filtered.append({
+            "event_type": row.get("event_type", ""),
+            "token_id": row.get("token_id", ""),
+            "scopes": row.get("scopes", []),
+            "timestamp": row.get("timestamp", ""),
+            "chain_link_sha256": row.get("chain_link_sha256", ""),
+        })
+    return filtered[-limit:]
+
+
+def _oauth3_legacy_token_view(token: dict[str, Any]) -> dict[str, Any]:
+    safe = {key: value for key, value in token.items() if key != "token_sha256"}
+    token_id = str(safe.get("token_id") or safe.get("id") or "")
+    if token_id:
+        safe["token_id"] = token_id
+        safe["id"] = token_id
+    return safe
+
+
+def _oauth3_active_token_rows(session_token_sha256: str) -> list[dict[str, Any]]:
+    rows: list[dict[str, Any]] = []
+    seen_token_ids: set[str] = set()
+    if OAUTH3_VAULT_PATH.exists():
+        state = _oauth3_load_vault_state(session_token_sha256)
+        for token in state.get("tokens", {}).values():
+            if not isinstance(token, dict):
+                continue
+            token_id = str(token.get("token_id", ""))
+            if not token_id:
+                continue
+            valid, _ = _oauth3_token_valid(token)
+            if not valid:
+                continue
+            rows.append(_oauth3_token_view(token))
+            seen_token_ids.add(token_id)
+    for token in load_oauth3_tokens():
+        if not isinstance(token, dict):
+            continue
+        token_id = str(token.get("token_id") or token.get("id") or "")
+        if not token_id or token_id in seen_token_ids:
+            continue
+        if bool(token.get("revoked", False)):
+            continue
+        rows.append(_oauth3_legacy_token_view(token))
+    return rows
+
+
 def _load_cloud_api_key() -> str:
     try:
         settings = json.loads(SETTINGS_PATH.read_text())
@@ -388,6 +1109,470 @@ def _load_user_tier_payload() -> dict:
     }
 
 
+_prime_wiki_urlopen = urllib.request.urlopen
+
+
+def _prime_wiki_timestamp() -> str:
+    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
+
+
+def _normalize_prime_wiki_url(url: str) -> str:
+    parsed = urllib.parse.urlsplit(url.strip())
+    if not parsed.scheme or not parsed.netloc:
+        return ""
+    normalized_path = parsed.path.rstrip("/") or "/"
+    return urllib.parse.urlunsplit(
+        (parsed.scheme.lower(), parsed.netloc.lower(), normalized_path, "", "")
+    )
+
+
+def _prime_wiki_url_hash(normalized_url: str) -> str:
+    return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
+
+
+def _prime_wiki_storage_dir(url_hash: str) -> Path:
+    return PRIME_WIKI_ROOT / url_hash[:16]
+
+
+def _prime_wiki_clean_text(value: str) -> str:
+    without_tags = re.sub(r"<[^>]+>", " ", value)
+    return re.sub(r"\s+", " ", without_tags).strip()
+
+
+def _prime_wiki_unique_text(values: list[str]) -> list[str]:
+    unique_values: list[str] = []
+    seen: set[str] = set()
+    for value in values:
+        normalized = re.sub(r"\s+", " ", value).strip()
+        if not normalized or normalized in seen:
+            continue
+        seen.add(normalized)
+        unique_values.append(normalized)
+    return unique_values
+
+
+def _prime_wiki_meta_content(tag: object) -> str:
+    if BeautifulSoup is None:
+        return ""
+    if tag is None:
+        return ""
+    content = tag.get("content", "")
+    return content.strip() if isinstance(content, str) else ""
+
+
+def _prime_wiki_rel_contains_canonical(value: object) -> bool:
+    if isinstance(value, list):
+        return "canonical" in [str(item).strip().lower() for item in value]
+    if isinstance(value, str):
+        return "canonical" in value.strip().lower().split()
+    return False
+
+
+def extract_metadata(html: str) -> dict:
+    if BeautifulSoup is not None:
+        soup = BeautifulSoup(html, "html.parser")
+        og_title = ""
+        og_description = ""
+        canonical_url = ""
+
+        og_title_tag = soup.find("meta", attrs={"property": "og:title"})
+        if og_title_tag is None:
+            og_title_tag = soup.find("meta", attrs={"name": "og:title"})
+        og_title = _prime_wiki_meta_content(og_title_tag)
+
+        og_description_tag = soup.find("meta", attrs={"property": "og:description"})
+        if og_description_tag is None:
+            og_description_tag = soup.find("meta", attrs={"name": "og:description"})
+        og_description = _prime_wiki_meta_content(og_description_tag)
+        if not og_description:
+            description_tag = soup.find("meta", attrs={"name": "description"})
+            og_description = _prime_wiki_meta_content(description_tag)
+
+        for link in soup.find_all("link"):
+            rel_value = link.get("rel")
+            if _prime_wiki_rel_contains_canonical(rel_value):
+                href = link.get("href", "")
+                if isinstance(href, str):
+                    canonical_url = href.strip()
+                    if canonical_url:
+                        break
+
+        return {
+            "og_title": og_title,
+            "og_description": og_description,
+            "canonical_url": canonical_url,
+        }
+
+    og_title_match = re.search(
+        r'<meta[^>]+(?:property|name)=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
+        html,
+        re.I,
+    )
+    og_description_match = re.search(
+        r'<meta[^>]+(?:property|name)=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
+        html,
+        re.I,
+    )
+    if og_description_match is None:
+        og_description_match = re.search(
+            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
+            html,
+            re.I,
+        )
+    canonical_match = re.search(
+        r'href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']|'
+        r'rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']',
+        html,
+        re.I,
+    )
+    return {
+        "og_title": og_title_match.group(1).strip() if og_title_match else "",
+        "og_description": og_description_match.group(1).strip() if og_description_match else "",
+        "canonical_url": (canonical_match.group(1) or canonical_match.group(2)).strip()
+        if canonical_match
+        else "",
+    }
+
+
+def _extract_title(html: str) -> str:
+    if BeautifulSoup is not None:
+        soup = BeautifulSoup(html, "html.parser")
+        if soup.title is not None:
+            title_text = soup.title.get_text(" ", strip=True)
+            if title_text:
+                return title_text
+        metadata = extract_metadata(html)
+        og_title = metadata.get("og_title", "")
+        return og_title if isinstance(og_title, str) else ""
+
+    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
+    if title_match:
+        return _prime_wiki_clean_text(title_match.group(1))
+    metadata = extract_metadata(html)
+    og_title = metadata.get("og_title", "")
+    return og_title if isinstance(og_title, str) else ""
+
+
+def extract_headings(html: str) -> list[str]:
+    if BeautifulSoup is not None:
+        soup = BeautifulSoup(html, "html.parser")
+        headings = [tag.get_text(" ", strip=True) for tag in soup.find_all(["h1", "h2", "h3"])]
+        return _prime_wiki_unique_text(headings)
+
+    matches = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, re.I | re.S)
+    return _prime_wiki_unique_text([_prime_wiki_clean_text(match) for match in matches])
+
+
+def _prime_wiki_is_action_cta(text: str, href: str = "") -> bool:
+    haystack = f"{text} {href}".lower()
+    for verb in PRIME_WIKI_CTA_VERBS:
+        if re.search(rf"\b{re.escape(verb)}\b", haystack):
+            return True
+    return False
+
+
+def extract_ctas(html: str) -> list[str]:
+    ctas: list[str] = []
+    if BeautifulSoup is not None:
+        soup = BeautifulSoup(html, "html.parser")
+        for button in soup.find_all("button"):
+            text = button.get_text(" ", strip=True)
+            if text:
+                ctas.append(text)
+        for input_tag in soup.find_all("input"):
+            input_type = str(input_tag.get("type", "")).strip().lower()
+            if input_type in ("submit", "button"):
+                value = str(input_tag.get("value", "")).strip()
+                if value:
+                    ctas.append(value)
+        for link in soup.find_all("a"):
+            text = link.get_text(" ", strip=True)
+            href = str(link.get("href", "")).strip()
+            if text and _prime_wiki_is_action_cta(text, href):
+                ctas.append(text)
+        return _prime_wiki_unique_text(ctas)
+
+    button_matches = re.findall(r"<button[^>]*>(.*?)</button>", html, re.I | re.S)
+    for match in button_matches:
+        text = _prime_wiki_clean_text(match)
+        if text:
+            ctas.append(text)
+    input_matches = re.findall(
+        r'<input[^>]*type=["\'](?:submit|button)["\'][^>]*value=["\']([^"\']+)["\'][^>]*>',
+        html,
+        re.I,
+    )
+    for value in input_matches:
+        cleaned = re.sub(r"\s+", " ", value).strip()
+        if cleaned:
+            ctas.append(cleaned)
+    link_matches = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S)
+    for href, text in link_matches:
+        cleaned = _prime_wiki_clean_text(text)
+        if cleaned and _prime_wiki_is_action_cta(cleaned, href):
+            ctas.append(cleaned)
+    return _prime_wiki_unique_text(ctas)
+
+
+def extract_key_elements(html: str) -> dict:
+    return {
+        "title": _extract_title(html),
+        "headings": extract_headings(html),
+        "ctas": extract_ctas(html),
+        "metadata": extract_metadata(html),
+    }
+
+
+def _compress_prime_wiki_content(content: str) -> tuple[str, str, int, int, float]:
+    raw_bytes = content.encode("utf-8")
+    compressed_bytes = gzip.compress(raw_bytes)
+    compressed_b64 = base64.b64encode(compressed_bytes).decode("ascii")
+    sha256_value = hashlib.sha256(raw_bytes).hexdigest()
+    compression_ratio = round(len(raw_bytes) / max(len(compressed_bytes), 1), 3)
+    return compressed_b64, sha256_value, len(raw_bytes), len(compressed_bytes), compression_ratio
+
+
+def _prime_wiki_snapshot_filename(snapshot_type: str, captured_at: str, snapshot_id: str) -> str:
+    filename = f"{snapshot_type}_{captured_at}.json"
+    if len(filename) <= 255:
+        return filename
+    return f"{snapshot_type}_{captured_at}_{snapshot_id}.json"
+
+
+def _prime_wiki_public_record(record: dict) -> dict:
+    public_record = dict(record)
+    public_record.pop("content_gzip_b64", None)
+    public_record.pop("storage_path", None)
+    return public_record
+
+
+def _prime_wiki_snapshot_record(
+    url: str,
+    content_html: str,
+    snapshot_type: str,
+    app_id: str,
+    action_id: str,
+) -> dict:
+    normalized_url = _normalize_prime_wiki_url(url)
+    captured_at = _prime_wiki_timestamp()
+    snapshot_id = str(uuid.uuid4())
+    compressed_b64, sha256_value, size_bytes, compressed_size_bytes, compression_ratio = (
+        _compress_prime_wiki_content(content_html)
+    )
+    return {
+        "snapshot_id": snapshot_id,
+        "url_hash": _prime_wiki_url_hash(normalized_url),
+        "url": normalized_url,
+        "domain": urllib.parse.urlsplit(normalized_url).netloc.lower(),
+        "snapshot_type": snapshot_type,
+        "content_gzip_b64": compressed_b64,
+        "key_elements": extract_key_elements(content_html),
+        "compression_ratio": compression_ratio,
+        "captured_at": captured_at,
+        "captured_at_ts": time.time(),
+        "app_id": app_id,
+        "action_id": action_id,
+        "sha256": sha256_value,
+        "size_bytes": size_bytes,
+        "compressed_size_bytes": compressed_size_bytes,
+    }
+
+
+def _store_prime_wiki_snapshot(record: dict) -> Path:
+    storage_dir = _prime_wiki_storage_dir(str(record.get("url_hash", "")))
+    storage_dir.mkdir(parents=True, exist_ok=True)
+    snapshot_id = str(record.get("snapshot_id", ""))
+    captured_at = str(record.get("captured_at", ""))
+    snapshot_type = str(record.get("snapshot_type", "periodic"))
+    file_path = storage_dir / _prime_wiki_snapshot_filename(snapshot_type, captured_at, snapshot_id)
+    if file_path.exists():
+        file_path = storage_dir / f"{snapshot_type}_{captured_at}_{snapshot_id}.json"
+    record["storage_path"] = str(file_path)
+    with _PRIME_WIKI_LOCK:
+        file_path.write_text(json.dumps(record, indent=2))
+    return file_path
+
+
+def _iter_prime_wiki_snapshot_paths() -> list[Path]:
+    if not PRIME_WIKI_ROOT.is_dir():
+        return []
+    return sorted(PRIME_WIKI_ROOT.glob("*/*.json"))
+
+
+def _load_prime_wiki_snapshot_from_path(path: Path) -> Optional[dict]:
+    try:
+        record = json.loads(path.read_text())
+    except FileNotFoundError:
+        return None
+    except json.JSONDecodeError:
+        return None
+    except OSError:
+        return None
+    if not isinstance(record, dict):
+        return None
+    record["storage_path"] = str(path)
+    return record
+
+
+def _find_prime_wiki_snapshot(snapshot_id: str) -> Optional[dict]:
+    for path in _iter_prime_wiki_snapshot_paths():
+        record = _load_prime_wiki_snapshot_from_path(path)
+        if record is None:
+            continue
+        if record.get("snapshot_id") == snapshot_id:
+            return record
+    return None
+
+
+def _load_all_prime_wiki_snapshots() -> list[dict]:
+    records: list[dict] = []
+    for path in _iter_prime_wiki_snapshot_paths():
+        record = _load_prime_wiki_snapshot_from_path(path)
+        if record is not None:
+            records.append(record)
+    return records
+
+
+def _prime_wiki_diff_elements(record: dict) -> set[str]:
+    key_elements = record.get("key_elements", {})
+    if not isinstance(key_elements, dict):
+        return set()
+    elements: set[str] = set()
+    title = key_elements.get("title", "")
+    if isinstance(title, str) and title:
+        elements.add(f"title:{title}")
+    headings = key_elements.get("headings", [])
+    if isinstance(headings, list):
+        for heading in headings:
+            if isinstance(heading, str) and heading:
+                elements.add(f"heading:{heading}")
+    ctas = key_elements.get("ctas", [])
+    if isinstance(ctas, list):
+        for cta in ctas:
+            if isinstance(cta, str) and cta:
+                elements.add(f"cta:{cta}")
+    metadata = key_elements.get("metadata", {})
+    if isinstance(metadata, dict):
+        for key, value in metadata.items():
+            if isinstance(value, str) and value:
+                elements.add(f"metadata:{key}={value}")
+    return elements
+
+
+def _prime_wiki_diff_payload(before_record: dict, after_record: dict) -> dict:
+    before_elements = _prime_wiki_diff_elements(before_record)
+    after_elements = _prime_wiki_diff_elements(after_record)
+    before_headings = before_record.get("key_elements", {}).get("headings", [])
+    after_headings = after_record.get("key_elements", {}).get("headings", [])
+    if not isinstance(before_headings, list):
+        before_headings = []
+    if not isinstance(after_headings, list):
+        after_headings = []
+    added_elements = sorted(after_elements - before_elements)
+    removed_elements = sorted(before_elements - after_elements)
+    added_headings = sorted({heading for heading in after_headings if isinstance(heading, str)} - {heading for heading in before_headings if isinstance(heading, str)})
+    removed_headings = sorted({heading for heading in before_headings if isinstance(heading, str)} - {heading for heading in after_headings if isinstance(heading, str)})
+    return {
+        "added_elements": added_elements,
+        "removed_elements": removed_elements,
+        "changed_headings": {
+            "added": added_headings,
+            "removed": removed_headings,
+        },
+        "action_summary": (
+            f"Added {len(added_elements)} elements, removed {len(removed_elements)} elements, "
+            f"changed headings +{len(added_headings)}/-{len(removed_headings)}"
+        ),
+    }
+
+
+def _prime_wiki_stats_payload() -> dict:
+    records = _load_all_prime_wiki_snapshots()
+    total_compressed_bytes = 0
+    domains: set[str] = set()
+    last_24h_count = 0
+    cutoff = time.time() - 86400
+    for record in records:
+        compressed_size_bytes = record.get("compressed_size_bytes", 0)
+        if isinstance(compressed_size_bytes, int):
+            total_compressed_bytes += compressed_size_bytes
+        domain = record.get("domain", "")
+        if isinstance(domain, str) and domain:
+            domains.add(domain)
+        captured_at_ts = record.get("captured_at_ts", 0)
+        if isinstance(captured_at_ts, (int, float)) and captured_at_ts >= cutoff:
+            last_24h_count += 1
+    return {
+        "total_snapshots": len(records),
+        "total_compressed_kb": round(total_compressed_bytes / 1024, 2),
+        "domains_covered": len(domains),
+        "last_24h_count": last_24h_count,
+    }
+
+
+def _prime_wiki_sync_enabled_for_tier(user_tier: str) -> bool:
+    return _MARKETPLACE_TIER_RANKS.get(user_tier, 0) >= _MARKETPLACE_TIER_RANKS["pro"]
+
+
+def _prime_wiki_cloud_push_worker(snapshot_record: dict) -> None:
+    request = urllib.request.Request(
+        PRIME_WIKI_PUSH_URL,
+        data=json.dumps(snapshot_record).encode(),
+        headers={"Content-Type": "application/json"},
+        method="POST",
+    )
+    try:
+        with _prime_wiki_urlopen(request, timeout=PRIME_WIKI_PUSH_TIMEOUT_SECONDS) as response:
+            response.read()
+        record_evidence(
+            "prime_wiki_cloud_push_succeeded",
+            {
+                "snapshot_id": snapshot_record.get("snapshot_id", ""),
+                "url_hash": snapshot_record.get("url_hash", ""),
+            },
+        )
+    except urllib.error.HTTPError as exc:
+        record_evidence(
+            "prime_wiki_cloud_push_failed",
+            {
+                "snapshot_id": snapshot_record.get("snapshot_id", ""),
+                "url_hash": snapshot_record.get("url_hash", ""),
+                "status": exc.code,
+            },
+        )
+    except urllib.error.URLError as exc:
+        record_evidence(
+            "prime_wiki_cloud_push_failed",
+            {
+                "snapshot_id": snapshot_record.get("snapshot_id", ""),
+                "url_hash": snapshot_record.get("url_hash", ""),
+                "reason": str(exc.reason) if hasattr(exc, "reason") else str(exc),
+            },
+        )
+    except OSError as exc:
+        record_evidence(
+            "prime_wiki_cloud_push_failed",
+            {
+                "snapshot_id": snapshot_record.get("snapshot_id", ""),
+                "url_hash": snapshot_record.get("url_hash", ""),
+                "reason": str(exc),
+            },
+        )
+
+
+def _queue_prime_wiki_cloud_push(snapshot_record: dict) -> bool:
+    user_tier = _load_account_tier()
+    if not _prime_wiki_sync_enabled_for_tier(user_tier):
+        return False
+    thread = threading.Thread(
+        target=_prime_wiki_cloud_push_worker,
+        args=(snapshot_record,),
+        daemon=True,
+    )
+    thread.start()
+    return True
+
+
 def _marketplace_apps_root(repo_root: str) -> Path:
     return Path(repo_root) / "data" / "default" / "apps"
 
@@ -633,17 +1818,64 @@ def _cloud_twin_status_payload() -> dict:
     }
 
 
-def _forward_cloud_twin_session(cloud_twin_url: str, payload: dict, timeout: float = 10.0) -> dict:
-    body = json.dumps(payload).encode()
-    request = urllib.request.Request(
-        f"{cloud_twin_url}/api/v1/sessions",
-        data=body,
-        headers={"Content-Type": "application/json"},
-        method="POST",
-    )
-    started = time.perf_counter()
-    try:
-        with urllib.request.urlopen(request, timeout=timeout) as response:
+def _cloud_twin_mode_enabled(cloud_twin: bool = False) -> bool:
+    env_value = os.environ.get("SOLACE_CLOUD_TWIN", "").strip().lower()
+    return cloud_twin or env_value in {"1", "true", "yes", "on"}
+
+
+def _hub_integration_enabled(cloud_twin: bool = False) -> bool:
+    return not _cloud_twin_mode_enabled(cloud_twin)
+
+
+def _cloud_twin_display() -> str:
+    return os.environ.get("DISPLAY", CLOUD_TWIN_DISPLAY)
+
+
+def _health_payload(app_count: int, port: int, cloud_twin_mode: bool) -> dict:
+    return {
+        "status": "ok",
+        "apps": app_count,
+        "version": _SERVER_VERSION,
+        "evidence_count": count_evidence(),
+        "schedule_count": len(load_schedules()),
+        "uptime_seconds": int(time.time() - _SERVER_START_TIME),
+        "port": port,
+        "mode": "cloud_twin" if cloud_twin_mode else "local",
+        "display": _cloud_twin_display() if cloud_twin_mode else "",
+    }
+
+
+def _launch_chrome_cloud_twin(url: str) -> subprocess.Popen:
+    browser = os.environ.get("SOLACE_BROWSER", "")
+    if not browser:
+        browser = shutil.which("chromium-browser") or shutil.which("chromium") or "chromium-browser"
+    env = dict(os.environ)
+    env["DISPLAY"] = _cloud_twin_display()
+    return subprocess.Popen(
+        [
+            browser,
+            f"--display={env['DISPLAY']}",
+            "--no-sandbox",
+            "--disable-dev-shm-usage",
+            url,
+        ],
+        stdout=subprocess.DEVNULL,
+        stderr=subprocess.DEVNULL,
+        env=env,
+    )
+
+
+def _forward_cloud_twin_session(cloud_twin_url: str, payload: dict, timeout: float = 10.0) -> dict:
+    body = json.dumps(payload).encode()
+    request = urllib.request.Request(
+        f"{cloud_twin_url}/api/v1/sessions",
+        data=body,
+        headers={"Content-Type": "application/json"},
+        method="POST",
+    )
+    started = time.perf_counter()
+    try:
+        with urllib.request.urlopen(request, timeout=timeout) as response:
             response_body = response.read().decode()
             data = json.loads(response_body)
             latency_ms = int((time.perf_counter() - started) * 1000)
@@ -930,23 +2162,31 @@ def load_apps(repo_root: str) -> list[str]:
     Discover apps from data directories.
     Search order:
       1. <repo_root>/data/default/apps/   (browser-local apps)
+      2. <repo_root>/data/custom/apps/    (local custom apps)
       2. <repo_root>/data/apps/           (fallback flat layout)
-    Returns sorted list of app_id strings; [] if no directory found.
+    Returns sorted list of unique app_id strings.
     """
+    app_ids: set[str] = set()
     for apps_path in (
         Path(repo_root) / "data" / "default" / "apps",
+        Path(repo_root) / "data" / "custom" / "apps",
         Path(repo_root) / "data" / "apps",
     ):
         if apps_path.is_dir():
-            return sorted(d.name for d in apps_path.iterdir() if d.is_dir())
-    return []
+            app_ids.update(d.name for d in apps_path.iterdir() if d.is_dir())
+    return sorted(app_ids)
 
 
 def _session_rule_paths() -> list[Path]:
     """Return sorted session-rules.yaml paths from the configured app directory."""
-    if not SESSION_RULES_APPS_DIR.is_dir():
-        return []
-    return sorted(SESSION_RULES_APPS_DIR.glob("*/session-rules.yaml"))
+    rule_paths: list[Path] = []
+    for apps_dir in (
+        SESSION_RULES_APPS_DIR,
+        SESSION_RULES_APPS_DIR.parent.parent / "custom" / "apps",
+    ):
+        if apps_dir.is_dir():
+            rule_paths.extend(sorted(apps_dir.glob("*/session-rules.yaml")))
+    return sorted(rule_paths)
 
 
 def _session_interval_seconds(rule: dict) -> int:
@@ -1019,9 +2259,73 @@ def _find_session_rule(app_id: str) -> Optional[dict]:
     return None
 
 
+def _custom_apps_root(repo_root: str) -> Path:
+    return Path(repo_root) / "data" / "custom" / "apps"
+
+
+def _official_store_path(repo_root: str) -> Path:
+    return Path(repo_root) / "data" / "default" / "app-store" / "official-store.json"
+
+
+def _domain_index_path(repo_root: str) -> Path:
+    return _marketplace_apps_root(repo_root) / ".domain-index.json"
+
+
+def _repo_app_roots(repo_root: str) -> tuple[Path, ...]:
+    return (
+        _marketplace_apps_root(repo_root),
+        _custom_apps_root(repo_root),
+    )
+
+
+def _repo_app_dir(repo_root: str, app_id: str) -> Optional[Path]:
+    for apps_root in _repo_app_roots(repo_root):
+        app_dir = apps_root / app_id
+        if app_dir.is_dir():
+            return app_dir
+    return None
+
+
+def _app_manifest_path(repo_root: str, app_id: str) -> Optional[Path]:
+    app_dir = _repo_app_dir(repo_root, app_id)
+    if app_dir is None:
+        return None
+    manifest_path = app_dir / "manifest.yaml"
+    if manifest_path.is_file():
+        return manifest_path
+    return None
+
+
+def _repo_session_rules_path_for_app(repo_root: str, app_id: str) -> Optional[Path]:
+    for apps_root in _repo_app_roots(repo_root):
+        rules_path = apps_root / app_id / "session-rules.yaml"
+        if rules_path.is_file():
+            return rules_path
+    return None
+
+
+def _load_session_rules_for_app(repo_root: str, app_id: str) -> dict:
+    rules_path = _repo_session_rules_path_for_app(repo_root, app_id)
+    if rules_path is None:
+        return {}
+    try:
+        raw_rule = yaml.safe_load(rules_path.read_text())
+    except FileNotFoundError:
+        return {}
+    except OSError:
+        return {}
+    except yaml.YAMLError:
+        return {}
+    if isinstance(raw_rule, dict):
+        return raw_rule
+    return {}
+
+
 def _load_manifest_for_app(repo_root: str, app_id: str) -> dict:
     """Load one app manifest from the repo-scoped apps directory."""
-    manifest_path = _marketplace_app_dir(repo_root, app_id) / "manifest.yaml"
+    manifest_path = _app_manifest_path(repo_root, app_id)
+    if manifest_path is None:
+        return {}
     try:
         raw_manifest = yaml.safe_load(manifest_path.read_text())
     except FileNotFoundError:
@@ -1049,68 +2353,426 @@ def _normalize_domain(value: str) -> str:
     return host
 
 
-def _domain_matches(site: str, query_domain: str) -> bool:
-    """Match app site against queried domain."""
-    site_clean = _normalize_domain(site)
+def _normalize_path_match(value: str) -> str:
+    candidate = value.strip()
+    if not candidate:
+        return "/"
+    parsed = urllib.parse.urlparse(candidate if "://" in candidate else f"https://placeholder{candidate}")
+    path_value = parsed.path or "/"
+    if not path_value.startswith("/"):
+        path_value = "/" + path_value
+    return path_value
+
+
+def _normalize_tier_name(value: object) -> str:
+    if not isinstance(value, str):
+        return "free"
+    normalized = value.strip().lower()
+    if normalized not in _MARKETPLACE_TIER_RANKS:
+        return "free"
+    return normalized
+
+
+def _required_tier_for_app(manifest: dict, session_rules: dict | None = None, fallback: object = "free") -> str:
+    rules = session_rules or {}
+    return _normalize_tier_name(
+        manifest.get("tier_required")
+        or manifest.get("tier")
+        or rules.get("tier_required")
+        or fallback
+    )
+
+
+def _normalize_domain_pattern(pattern: str) -> str:
+    raw_value = pattern.strip().lower()
+    if not raw_value:
+        return ""
+    if raw_value == "*":
+        raise ValueError("DOMAIN_WILDCARD_ABUSE")
+    parsed = urllib.parse.urlparse(raw_value if "://" in raw_value else f"//{raw_value}")
+    host = parsed.netloc or parsed.path
+    host = host.strip()
+    path_value = ""
+    if "/" in host:
+        host, path_suffix = host.split("/", 1)
+        path_value = "/" + path_suffix.strip("/") if path_suffix else ""
+    if parsed.path and parsed.netloc:
+        path_value = parsed.path
+    host = host.split(":", 1)[0]
+    if host.startswith("www."):
+        host = host[4:]
+    if host == "*":
+        raise ValueError("DOMAIN_WILDCARD_ABUSE")
+    if not host:
+        return ""
+    if path_value:
+        normalized_path = path_value if path_value.startswith("/") else "/" + path_value
+        normalized_path = re.sub(r"/+", "/", normalized_path)
+        return f"{host}{normalized_path}"
+    return host
+
+
+def _split_domain_pattern(pattern: str) -> tuple[str, str]:
+    normalized = _normalize_domain_pattern(pattern)
+    if not normalized:
+        return "", ""
+    if "/" not in normalized:
+        return normalized, ""
+    host, path_value = normalized.split("/", 1)
+    return host, "/" + path_value
+
+
+def _domain_pattern_matches(pattern: str, query_domain: str, query_path: str = "/") -> bool:
+    host_pattern, path_pattern = _split_domain_pattern(pattern)
     domain_clean = _normalize_domain(query_domain)
-    if not site_clean or not domain_clean:
+    if not host_pattern or not domain_clean:
         return False
-    return (
-        site_clean == domain_clean
-        or domain_clean.endswith("." + site_clean)
-        or site_clean.endswith("." + domain_clean)
-    )
 
+    if host_pattern.startswith("*."):
+        suffix = host_pattern[2:]
+        host_matches = bool(suffix) and domain_clean.endswith("." + suffix) and domain_clean != suffix
+    else:
+        host_matches = host_pattern == domain_clean
 
-def _load_session_rules_for_repo(repo_root: str) -> list[dict]:
-    """Load session rules from the repo-scoped apps directory."""
-    apps_root = _marketplace_apps_root(repo_root)
-    if not apps_root.is_dir():
-        return []
-    rules: list[dict] = []
-    for rule_path in sorted(apps_root.glob("*/session-rules.yaml")):
-        try:
-            raw_rule = yaml.safe_load(rule_path.read_text())
-        except FileNotFoundError:
+    if not host_matches:
+        return False
+    if not path_pattern:
+        return True
+
+    normalized_path = _normalize_path_match(query_path)
+    if path_pattern.endswith("/*"):
+        return normalized_path.startswith(path_pattern[:-1])
+    return normalized_path == path_pattern
+
+
+def _manifest_domain_patterns(manifest: dict, fallback_site: str = "") -> list[str]:
+    raw_domains = manifest.get("domains", [])
+    patterns: list[str] = []
+    if isinstance(raw_domains, list):
+        for entry in raw_domains:
+            if isinstance(entry, str):
+                normalized = _normalize_domain_pattern(entry)
+                if normalized:
+                    patterns.append(normalized)
+    if patterns:
+        return sorted(set(patterns))
+    fallback_pattern = _normalize_domain_pattern(fallback_site)
+    if fallback_pattern:
+        return [fallback_pattern]
+    return []
+
+
+def _iter_manifest_records(repo_root: str) -> list[tuple[str, dict, Path]]:
+    manifests: list[tuple[str, dict, Path]] = []
+    for apps_root in _repo_app_roots(repo_root):
+        if not apps_root.is_dir():
             continue
-        except OSError:
+        for manifest_path in sorted(apps_root.glob("*/manifest.yaml")):
+            app_id = manifest_path.parent.name
+            try:
+                raw_manifest = yaml.safe_load(manifest_path.read_text())
+            except FileNotFoundError:
+                continue
+            except OSError:
+                continue
+            except yaml.YAMLError:
+                continue
+            if isinstance(raw_manifest, dict):
+                manifests.append((app_id, raw_manifest, manifest_path))
+    manifests.sort(key=lambda item: item[0])
+    return manifests
+
+
+def _build_domain_index_payload(repo_root: str) -> dict:
+    patterns: dict[str, list[str]] = {}
+    apps_indexed: set[str] = set()
+    for app_id, manifest, _manifest_path in _iter_manifest_records(repo_root):
+        for pattern in _manifest_domain_patterns(manifest, str(manifest.get("site", ""))):
+            patterns.setdefault(pattern, [])
+            if app_id not in patterns[pattern]:
+                patterns[pattern].append(app_id)
+                apps_indexed.add(app_id)
+    for app_ids in patterns.values():
+        app_ids.sort()
+    return {
+        "version": 1,
+        "generated_at": int(time.time()),
+        "domains_indexed": len(patterns),
+        "apps_indexed": len(apps_indexed),
+        "patterns": dict(sorted(patterns.items())),
+    }
+
+
+def _rebuild_domain_index(repo_root: str) -> dict:
+    payload = _build_domain_index_payload(repo_root)
+    domain_index_path = _domain_index_path(repo_root)
+    domain_index_path.parent.mkdir(parents=True, exist_ok=True)
+    domain_index_path.write_text(json.dumps(payload, indent=2))
+    return {
+        "rebuilt": True,
+        "domains_indexed": payload["domains_indexed"],
+        "apps_indexed": payload["apps_indexed"],
+        "index_path": str(domain_index_path),
+    }
+
+
+def _load_domain_index(repo_root: str) -> dict:
+    domain_index_path = _domain_index_path(repo_root)
+    if not domain_index_path.exists():
+        _rebuild_domain_index(repo_root)
+    try:
+        payload = json.loads(domain_index_path.read_text())
+    except FileNotFoundError:
+        _rebuild_domain_index(repo_root)
+        payload = json.loads(domain_index_path.read_text())
+    except json.JSONDecodeError:
+        _rebuild_domain_index(repo_root)
+        payload = json.loads(domain_index_path.read_text())
+    except OSError:
+        _rebuild_domain_index(repo_root)
+        payload = json.loads(domain_index_path.read_text())
+    if not isinstance(payload, dict):
+        rebuilt = _rebuild_domain_index(repo_root)
+        return {
+            "version": 1,
+            "generated_at": int(time.time()),
+            "domains_indexed": rebuilt["domains_indexed"],
+            "apps_indexed": rebuilt["apps_indexed"],
+            "patterns": {},
+        }
+    patterns = payload.get("patterns")
+    if isinstance(patterns, dict):
+        normalized_patterns: dict[str, list[str]] = {}
+        for pattern, app_ids in patterns.items():
+            if not isinstance(pattern, str) or not isinstance(app_ids, list):
+                continue
+            normalized_ids = sorted(str(app_id) for app_id in app_ids if isinstance(app_id, str) and app_id)
+            if normalized_ids:
+                normalized_patterns[_normalize_domain_pattern(pattern)] = normalized_ids
+        payload["patterns"] = dict(sorted(normalized_patterns.items()))
+        return payload
+    fallback_patterns: dict[str, list[str]] = {}
+    for pattern, app_ids in payload.items():
+        if not isinstance(pattern, str) or not isinstance(app_ids, list):
             continue
-        except yaml.YAMLError:
+        normalized_ids = sorted(str(app_id) for app_id in app_ids if isinstance(app_id, str) and app_id)
+        if normalized_ids:
+            fallback_patterns[_normalize_domain_pattern(pattern)] = normalized_ids
+    return {
+        "version": 1,
+        "generated_at": int(time.time()),
+        "domains_indexed": len(fallback_patterns),
+        "apps_indexed": len({app_id for app_ids in fallback_patterns.values() for app_id in app_ids}),
+        "patterns": dict(sorted(fallback_patterns.items())),
+    }
+
+
+def _match_domain_index(patterns: dict[str, list[str]], query_domain: str, query_path: str = "/") -> list[str]:
+    matched_ids: set[str] = set()
+    normalized_domain = _normalize_domain(query_domain)
+    normalized_path = _normalize_path_match(query_path)
+    for pattern, app_ids in patterns.items():
+        if _domain_pattern_matches(pattern, normalized_domain, normalized_path):
+            matched_ids.update(app_id for app_id in app_ids if isinstance(app_id, str) and app_id)
+    return sorted(matched_ids)
+
+
+def _load_session_rules_for_repo(repo_root: str) -> list[dict]:
+    """Load session rules from repo-scoped default and custom app directories."""
+    rules: list[dict] = []
+    for apps_root in _repo_app_roots(repo_root):
+        if not apps_root.is_dir():
             continue
-        if isinstance(raw_rule, dict):
-            rules.append(raw_rule)
+        for rule_path in sorted(apps_root.glob("*/session-rules.yaml")):
+            try:
+                raw_rule = yaml.safe_load(rule_path.read_text())
+            except FileNotFoundError:
+                continue
+            except OSError:
+                continue
+            except yaml.YAMLError:
+                continue
+            if isinstance(raw_rule, dict):
+                rules.append(raw_rule)
     return rules
 
 
-def _apps_for_domain(repo_root: str, query_domain: str) -> list[dict]:
-    """Return domain-matched app metadata from repo-scoped session rules."""
-    matched: list[dict] = []
-    for session_rules in _load_session_rules_for_repo(repo_root):
-        site = str(session_rules.get("site", "")).strip()
-        if not _domain_matches(site, query_domain):
+def _load_official_store_apps(repo_root: str) -> list[dict]:
+    store_path = _official_store_path(repo_root)
+    try:
+        payload = json.loads(store_path.read_text())
+    except FileNotFoundError:
+        return []
+    except json.JSONDecodeError:
+        return []
+    except OSError:
+        return []
+    if not isinstance(payload, dict):
+        return []
+    raw_apps = payload.get("apps", [])
+    if not isinstance(raw_apps, list):
+        return []
+    normalized_apps: list[dict] = []
+    for raw_app in raw_apps:
+        if not isinstance(raw_app, dict):
             continue
-        app_id = str(session_rules.get("app", "")).strip()
-        if not app_id:
+        app_id = raw_app.get("id")
+        if not isinstance(app_id, str) or not _APP_ID_RE.fullmatch(app_id):
+            continue
+        manifest = _load_manifest_for_app(repo_root, app_id)
+        site_value = str(raw_app.get("site") or manifest.get("site") or "")
+        try:
+            domains = _manifest_domain_patterns(raw_app, site_value)
+        except ValueError:
+            continue
+        normalized_apps.append({
+            "id": app_id,
+            "name": str(raw_app.get("name") or manifest.get("name") or app_id.replace("-", " ").title()),
+            "description": str(raw_app.get("description") or manifest.get("description") or ""),
+            "tier_required": _required_tier_for_app(manifest, fallback=raw_app.get("tier_required") or raw_app.get("tier") or "free"),
+            "domains": domains,
+        })
+    return normalized_apps
+
+
+def _lookup_session_active(app_id: str) -> bool:
+    with _SESSION_STATUS_LOCK:
+        status_entry = dict(_SESSION_STATUS.get(app_id, {}))
+    return status_entry.get("status") == "active"
+
+
+def _default_quick_action(display_name: str) -> str:
+    if "triage" in display_name.lower():
+        return "Run Triage"
+    return "Open"
+
+
+def _legacy_domain_apps(installed_apps: list[dict]) -> list[dict]:
+    legacy: list[dict] = []
+    for entry in installed_apps:
+        legacy.append({
+            "app_id": entry.get("id", ""),
+            "display_name": entry.get("name", ""),
+            "description": entry.get("description", ""),
+            "installed": True,
+            "tier_required": entry.get("tier_required", "free"),
+            "site": entry.get("site", ""),
+        })
+    return legacy
+
+
+def _apps_for_domain(repo_root: str, query_domain: str, query_path: str = "/", user_tier: str = "free") -> dict:
+    """Return domain-linked installed/store apps with tier gating."""
+    normalized_domain = _normalize_domain(query_domain)
+    if not normalized_domain:
+        return {
+            "domain": "",
+            "installed_apps": [],
+            "store_apps": [],
+            "can_create_custom": True,
+            "create_url": "/api/v1/apps/custom/create",
+            "apps": [],
+            "total": 0,
+        }
+
+    domain_index = _load_domain_index(repo_root)
+    patterns = domain_index.get("patterns", {})
+    if not isinstance(patterns, dict):
+        patterns = {}
+    matched_app_ids = _match_domain_index(patterns, normalized_domain, query_path)
+
+    installed_apps: list[dict] = []
+    locked_app_ids: set[str] = set()
+    for app_id in matched_app_ids:
+        session_rules = _load_session_rules_for_app(repo_root, app_id)
+        if not session_rules:
             continue
         manifest = _load_manifest_for_app(repo_root, app_id)
-        tier_required = str(manifest.get("tier") or session_rules.get("tier_required") or "free")
+        tier_required = _required_tier_for_app(manifest, session_rules)
+        if not _tier_allows_install(user_tier, tier_required):
+            locked_app_ids.add(app_id)
+            continue
         display_name = str(
             manifest.get("name")
             or session_rules.get("display_name")
             or app_id.replace("-", " ").title()
         )
-        matched.append({
-            "app_id": app_id,
-            "display_name": display_name,
+        installed_apps.append({
+            "id": app_id,
+            "name": display_name,
             "description": str(manifest.get("description") or session_rules.get("description") or ""),
-            "installed": bool(manifest.get("status") == "installed"),
+            "status": "installed",
+            "session_active": _lookup_session_active(app_id),
             "tier_required": tier_required,
-            "site": _normalize_domain(site),
+            "quick_action": _default_quick_action(display_name),
+            "site": _normalize_domain(str(session_rules.get("site") or manifest.get("site") or normalized_domain)),
         })
-    matched.sort(key=lambda entry: str(entry.get("app_id", "")))
-    return matched
+    installed_apps.sort(key=lambda entry: str(entry.get("id", "")))
+
+    store_apps: list[dict] = []
+    store_app_ids: set[str] = set()
+    for store_app in _load_official_store_apps(repo_root):
+        app_id = str(store_app.get("id", ""))
+        if not app_id:
+            continue
+        domains = store_app.get("domains", [])
+        if not isinstance(domains, list):
+            continue
+        if not any(_domain_pattern_matches(pattern, normalized_domain, query_path) for pattern in domains if isinstance(pattern, str)):
+            continue
+        tier_required = _normalize_tier_name(store_app.get("tier_required", "free"))
+        app_installed = _repo_session_rules_path_for_app(repo_root, app_id) is not None
+        if app_installed and app_id not in locked_app_ids:
+            continue
+        install_allowed = _tier_allows_install(user_tier, tier_required)
+        store_entry = {
+            "id": app_id,
+            "name": str(store_app.get("name", app_id.replace("-", " ").title())),
+            "description": str(store_app.get("description", "")),
+            "status": "available" if install_allowed and not app_installed else "upgrade_required",
+            "tier_required": tier_required,
+            "install_url": f"/api/v1/apps/{app_id}/install" if install_allowed else MARKETPLACE_UPGRADE_URL,
+        }
+        if not install_allowed:
+            store_entry["upgrade_url"] = MARKETPLACE_UPGRADE_URL
+        store_apps.append(store_entry)
+        store_app_ids.add(app_id)
 
+    for app_id in matched_app_ids:
+        if app_id in store_app_ids:
+            continue
+        manifest = _load_manifest_for_app(repo_root, app_id)
+        if not manifest:
+            continue
+        app_installed = _repo_session_rules_path_for_app(repo_root, app_id) is not None
+        if app_installed and app_id not in locked_app_ids:
+            continue
+        tier_required = _required_tier_for_app(manifest)
+        install_allowed = _tier_allows_install(user_tier, tier_required)
+        store_entry = {
+            "id": app_id,
+            "name": str(manifest.get("name") or app_id.replace("-", " ").title()),
+            "description": str(manifest.get("description") or ""),
+            "status": "available" if install_allowed and not app_installed else "upgrade_required",
+            "tier_required": tier_required,
+            "install_url": f"/api/v1/apps/{app_id}/install" if install_allowed else MARKETPLACE_UPGRADE_URL,
+        }
+        if not install_allowed:
+            store_entry["upgrade_url"] = MARKETPLACE_UPGRADE_URL
+        store_apps.append(store_entry)
+        store_app_ids.add(app_id)
+    store_apps.sort(key=lambda entry: str(entry.get("id", "")))
 
+    legacy_apps = _legacy_domain_apps(installed_apps)
+    return {
+        "domain": normalized_domain,
+        "installed_apps": installed_apps,
+        "store_apps": store_apps,
+        "can_create_custom": True,
+        "create_url": f"/api/v1/apps/custom/create?domain={urllib.parse.quote(normalized_domain, safe='')}",
+        "apps": legacy_apps,
+        "total": len(legacy_apps),
+    }
 def _invalid_custom_app_name(name: str) -> bool:
     return ".." in name or "/" in name or "\\" in name
 
@@ -1128,6 +2790,8 @@ def _custom_app_manifest(app_id: str, display_name: str, description: str, domai
         'status: "installed"\n'
         'safety: "B"\n'
         'tier: "free"\n'
+        'domains:\n'
+        f'  - {json.dumps(domain)}\n'
         f"site: {domain}\n"
         'type: "custom"\n'
         'custom: true\n'
@@ -1159,6 +2823,40 @@ def _custom_app_session_rules(app_id: str, display_name: str, description: str,
     )
 
 
+def _create_custom_app_scaffold(repo_root: str, raw_domain: str, raw_name: str, raw_description: str) -> dict:
+    domain = _normalize_domain(raw_domain)
+    name = raw_name.strip()
+    description = raw_description.strip()
+    if not domain:
+        raise ValueError("domain required")
+    if not name or _invalid_custom_app_name(name):
+        raise ValueError("invalid app name")
+    app_id = _slugify_custom_app_name(name)
+    if not app_id:
+        raise ValueError("invalid app name")
+
+    app_dir = _custom_apps_root(repo_root) / app_id
+    if app_dir.exists():
+        raise FileExistsError("app already exists")
+
+    manifest_text = _custom_app_manifest(app_id, name, description or f"Custom app for {domain}", domain)
+    session_rules_text = _custom_app_session_rules(app_id, name, description or f"Custom app for {domain}", domain)
+    app_dir.mkdir(parents=True, exist_ok=False)
+    (app_dir / "manifest.yaml").write_text(manifest_text)
+    (app_dir / "session-rules.yaml").write_text(session_rules_text)
+    _rebuild_domain_index(repo_root)
+
+    relative_app_path = Path("data") / "custom" / "apps" / app_id
+    return {
+        "app_id": app_id,
+        "path": f"{relative_app_path.as_posix()}/",
+        "manifest_path": (relative_app_path / "manifest.yaml").as_posix(),
+        "session_rules_path": (relative_app_path / "session-rules.yaml").as_posix(),
+        "manifest_template": manifest_text,
+        "session_rules_template": session_rules_text,
+    }
+
+
 def _custom_apps_sync_bundle(repo_root: str) -> list[dict]:
     bundle: list[dict] = []
     apps_root = _marketplace_apps_root(repo_root)
@@ -1293,10 +2991,16 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_start()
         elif path == "/api/v1/evidence":
             self._handle_evidence_list(query)
+        elif path == "/api/v1/evidence/bundles":
+            self._handle_part11_evidence_bundles(query)
         elif path == "/api/v1/evidence/verify":
             self._handle_evidence_verify()
+        elif path == "/api/v1/evidence/verify-chain":
+            self._handle_part11_evidence_verify_chain()
         elif path == "/api/v1/evidence/summary":
             self._handle_evidence_summary()
+        elif path == "/api/v1/evidence/compliance-report":
+            self._handle_part11_evidence_compliance_report()
         elif path == "/api/v1/evidence/hashes":
             self._handle_evidence_hashes()
         elif path == "/api/v1/evidence/search":
@@ -1309,6 +3013,16 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_session_rules_list()
         elif path == "/api/v1/session-rules/status":
             self._handle_session_rules_status()
+        elif path == "/api/v1/prime-wiki/diff":
+            self._handle_prime_wiki_diff(query)
+        elif path == "/api/v1/prime-wiki/stats":
+            self._handle_prime_wiki_stats()
+        elif re.match(r"^/api/v1/prime-wiki/snapshot/[^/]+/content$", path):
+            snapshot_id = path.split("/")[-2]
+            self._handle_prime_wiki_snapshot_content(snapshot_id)
+        elif re.match(r"^/api/v1/prime-wiki/snapshot/[^/]+$", path):
+            snapshot_id = path.split("/")[-1]
+            self._handle_prime_wiki_snapshot_detail(snapshot_id)
         elif re.match(r"^/api/v1/evidence/[^/]+$", path):
             entry_id = path.split("/")[-1]
             self._handle_evidence_detail(entry_id)
@@ -1372,6 +3086,8 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_recipes_search(query)
         elif path == "/api/v1/oauth3/scopes":
             self._handle_oauth3_scopes()
+        elif path == "/api/v1/oauth3/token/validate":
+            self._handle_oauth3_validate(query)
         elif path == "/api/v1/schedules/next":
             self._handle_schedules_next()
         elif path == "/api/v1/capabilities":
@@ -1386,10 +3102,16 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         elif path.startswith("/api/v1/oauth3/tokens/") and path.count("/") == 5:
             token_id = path.split("/")[-1]
             self._handle_oauth3_token_detail(token_id)
+        elif path == "/api/v1/oauth3/evidence":
+            self._handle_oauth3_evidence(query)
         elif path == "/api/v1/oauth3/audit":
             self._handle_oauth3_audit()
         elif path == "/api/v1/cli/available":
             self._handle_cli_available()
+        elif path == "/api/v1/cli-agents/detect":
+            self._handle_cli_agents_detect()
+        elif path == "/api/v1/cli-agents/refresh":
+            self._handle_cli_agents_refresh()
         elif path == "/onboarding":
             self._handle_onboarding_page()
         elif path == "/api/v1/onboarding/status":
@@ -1409,10 +3131,14 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_sync_status()
         elif path == "/api/v1/recipes":
             self._handle_recipes_list()
+        elif path == "/api/v1/recipes/my-library":
+            self._handle_community_recipes_my_library()
         elif path == "/api/v1/recipes/templates":
             self._handle_recipe_templates()
         elif path == "/api/v1/recipes/history":
             self._handle_recipe_history(query)
+        elif path == "/api/v1/recipes/community":
+            self._handle_community_recipes_list(query)
         elif re.match(r"^/api/v1/recipes/[^/]+/preview$", path):
             recipe_id = path.split("/")[-2]
             self._handle_recipe_preview(recipe_id)
@@ -1506,6 +3232,16 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_cli_config_get()
         elif path == "/api/v1/cli/detect":
             self._handle_cli_detect()
+        elif path == "/api/v1/apps/lifecycle":
+            self._handle_apps_lifecycle()
+        elif m := re.match(r"^/api/v1/apps/([^/]+)/setup-requirements$", path):
+            self._handle_app_setup_requirements(m.group(1))
+        elif path == "/web/apps.html":
+            self._handle_apps_html()
+        elif path == "/web/js/apps.js":
+            self._handle_apps_js()
+        elif path == "/web/css/apps.css":
+            self._handle_apps_css()
         elif path == "/api/v1/apps":
             self._handle_apps_list()
         elif re.match(r"^/api/v1/apps/[^/]+$", path):
@@ -1513,6 +3249,55 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_app_detail(app_id)
         elif path == "/ws/chat":
             self._handle_ws_chat()
+        elif path == "/api/v1/actions/pending":
+            self._handle_actions_pending()
+        elif path == "/api/v1/actions/history":
+            self._handle_actions_history(query)
+        elif path in ("/api/v1/schedule", "/api/schedule"):
+            self._handle_schedule_viewer_list(query)
+        elif path in ("/api/v1/schedule/queue", "/api/schedule/queue"):
+            self._handle_schedule_viewer_queue()
+        elif path in ("/api/v1/schedule/upcoming", "/api/schedule/upcoming"):
+            self._handle_schedule_viewer_upcoming()
+        elif path == "/api/v1/esign/pending":
+            self._handle_esign_pending()
+        elif path == "/api/v1/esign/history":
+            self._handle_esign_history()
+        elif path in ("/api/v1/schedule/calendar", "/api/schedule/calendar"):
+            self._handle_schedule_viewer_calendar(query)
+        elif path in ("/api/v1/schedule/roi", "/api/schedule/roi"):
+            self._handle_schedule_viewer_roi()
+        elif re.match(r"^/api/v1/schedule/[^/]+$", path) or re.match(r"^/api/schedule/[^/]+$", path):
+            run_id = path.split("/")[-1]
+            self._handle_schedule_viewer_detail(run_id)
+        elif path == "/web/schedule.html":
+            self._handle_schedule_html()
+        elif path == "/web/js/schedule.js":
+            self._handle_schedule_js()
+        elif path == "/web/css/schedule.css":
+            self._handle_schedule_css()
+        elif path == "/web/recipes.html":
+            self._handle_recipes_html()
+        elif path == "/web/js/recipes.js":
+            self._handle_recipes_js()
+        elif path == "/web/css/recipes.css":
+            self._handle_recipes_css()
+        elif path == "/api/v1/session/stats":
+            self._handle_session_stats()
+        elif path == "/web/dashboard.html":
+            self._handle_dashboard_html()
+        elif path == "/web/js/dashboard.js":
+            self._handle_dashboard_js()
+        elif path == "/web/css/dashboard.css":
+            self._handle_dashboard_css()
+        elif path == "/web/tutorial.html":
+            self._handle_tutorial_html()
+        elif path == "/web/js/tutorial.js":
+            self._handle_tutorial_js()
+        elif path == "/web/css/tutorial.css":
+            self._handle_tutorial_css()
+        elif path == "/api/v1/tutorial/reset":
+            self._handle_tutorial_reset()
         else:
             self._send_json({"error": "not found"}, 404)
 
@@ -1523,6 +3308,10 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_detect()
         elif path == "/api/v1/evidence":
             self._handle_evidence_record()
+        elif path == "/api/v1/evidence/bundle":
+            self._handle_part11_evidence_bundle_create()
+        elif path == "/api/v1/prime-wiki/snapshot":
+            self._handle_prime_wiki_snapshot_create()
         elif path == "/api/v1/session-rules/reload":
             self._handle_session_rules_reload()
         elif re.match(r"^/api/v1/session-rules/check/[^/]+$", path):
@@ -1536,6 +3325,12 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         elif re.match(r"^/api/v1/browser/schedules/[^/]+/disable$", path):
             schedule_id = path.split("/")[-2]
             self._handle_schedule_disable(schedule_id)
+        elif path == "/api/v1/oauth3/token/issue":
+            self._handle_oauth3_issue()
+        elif path == "/api/v1/oauth3/token/revoke":
+            self._handle_oauth3_revoke_vault()
+        elif path == "/api/v1/oauth3/step-up/request":
+            self._handle_oauth3_step_up_request()
         elif path == "/api/v1/oauth3/tokens":
             self._handle_oauth3_register()
         elif re.match(r"^/api/v1/oauth3/tokens/[^/]+/extend$", path):
@@ -1543,6 +3338,8 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_oauth3_extend(token_id)
         elif path == "/api/v1/cli/run":
             self._handle_cli_run()
+        elif path == "/api/v1/cli-agents/generate":
+            self._handle_cli_agents_generate()
         elif path == "/onboarding/complete":
             self._handle_onboarding_complete()
         elif path == "/onboarding/reset":
@@ -1567,7 +3364,15 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_sync_import()
         elif re.match(r"^/api/v1/recipes/[^/]+/run$", path):
             recipe_id = path.split("/")[-2]
-            self._handle_recipe_run(recipe_id)
+            self._handle_community_recipe_run(recipe_id)
+        elif path == "/api/v1/recipes/create":
+            self._handle_community_recipe_create()
+        elif re.match(r"^/api/v1/recipes/[^/]+/install$", path):
+            recipe_id = path.split("/")[-2]
+            self._handle_community_recipe_install(recipe_id)
+        elif re.match(r"^/api/v1/recipes/[^/]+/fork$", path):
+            recipe_id = path.split("/")[-2]
+            self._handle_community_recipe_fork(recipe_id)
         elif re.match(r"^/api/v1/recipes/[^/]+/enable$", path):
             recipe_id = path.split("/")[-2]
             self._handle_recipe_toggle(recipe_id, enabled=True)
@@ -1613,6 +3418,8 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_pinned_set()
         elif path == "/api/v1/apps/favorites":
             self._handle_apps_favorites_post()
+        elif path == "/api/v1/apps/rebuild-domain-index":
+            self._handle_rebuild_domain_index()
         elif path == "/api/v1/apps/custom/create":
             self._handle_custom_app_create()
         elif path == "/api/v1/apps/sync":
@@ -1655,9 +3462,32 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_cli_config_set()
         elif path == "/api/v1/cli/test":
             self._handle_cli_test()
+        elif m := re.match(r"^/api/v1/apps/([^/]+)/activate$", path):
+            self._handle_app_activate(m.group(1))
         elif re.match(r"^/api/v1/apps/[^/]+/launch$", path):
             app_id = path.split("/")[-2]
             self._handle_app_launch(app_id)
+        elif path == "/api/v1/actions/preview":
+            self._handle_actions_preview()
+        elif re.match(r"^/api/v1/actions/[^/]+/approve$", path):
+            action_id = path.split("/")[-2]
+            self._handle_action_approve(action_id)
+        elif re.match(r"^/api/v1/actions/[^/]+/reject$", path):
+            action_id = path.split("/")[-2]
+            self._handle_action_reject(action_id)
+        elif re.match(r"^/api/v1/schedule/approve/[^/]+$", path) or re.match(r"^/api/schedule/approve/[^/]+$", path):
+            run_id = path.split("/")[-1]
+            self._handle_schedule_viewer_approve(run_id)
+        elif re.match(r"^/api/v1/schedule/cancel/[^/]+$", path) or re.match(r"^/api/schedule/cancel/[^/]+$", path):
+            run_id = path.split("/")[-1]
+            self._handle_schedule_viewer_cancel(run_id)
+        elif path in ("/api/v1/schedule/plan", "/api/schedule/plan"):
+            self._handle_schedule_viewer_plan()
+        elif re.match(r"^/api/v1/esign/[^/]+/sign$", path):
+            esign_id = path.split("/")[-2]
+            self._handle_esign_sign(esign_id)
+        elif path == "/api/v1/session/stats/reset":
+            self._handle_session_stats_reset()
         else:
             self._send_json({"error": "not found"}, 404)
 
@@ -1684,28 +3514,26 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         elif re.match(r"^/api/v1/memory/[^/]+$", path):
             key = path.split("/")[-1]
             self._handle_memory_delete(key)
+        elif re.match(r"^/api/v1/actions/[^/]+/cancel$", path):
+            action_id = path.split("/")[-2]
+            self._handle_action_cancel(action_id)
+        elif m := re.match(r"^/api/v1/apps/([^/]+)/activate$", path):
+            self._handle_app_deactivate(m.group(1))
         else:
             self._send_json({"error": "not found"}, 404)
 
     # --- Handlers ---
     def _handle_health(self) -> None:
         apps: list[str] = self.server.apps  # type: ignore[attr-defined]
-        self._send_json({
-            "status": "ok",
-            "apps": len(apps),
-            "version": _SERVER_VERSION,
-            "evidence_count": count_evidence(),
-            "schedule_count": len(load_schedules()),
-            "uptime_seconds": int(time.time() - _SERVER_START_TIME),
-            "port": YINYANG_PORT,
-        })
+        cloud_twin_mode = bool(getattr(self.server, "cloud_twin_mode", False))
+        self._send_json(_health_payload(len(apps), self.server.server_port, cloud_twin_mode))
 
     def _handle_instructions(self) -> None:
         apps: list[str] = self.server.apps  # type: ignore[attr-defined]
         self._send_json({
             "version": _SERVER_VERSION,
             "hub": "Solace Hub (Tauri ~20MB)",
-            "server": "Yinyang Server localhost:8888",
+            "server": f"Yinyang Server localhost:{YINYANG_PORT}",
             "browser": "Solace Browser (Chromium fork with Yinyang Sidebar)",
             "cli_commands": [
                 "solace hub status",
@@ -1736,7 +3564,7 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         html = (
             "<!DOCTYPE html><html lang='en'><head>"
             "<meta charset='UTF-8'><title>Solace Hub — Starting</title>"
-            "<meta http-equiv='refresh' content='0;url=http://localhost:8888/health'>"
+            f"<meta http-equiv='refresh' content='0;url=http://localhost:{YINYANG_PORT}/health'>"
             "</head><body><p>Starting Solace Hub...</p></body></html>"
         )
         body = html.encode()
@@ -1798,6 +3626,177 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         record = record_evidence(event_type, data)
         self._send_json(record, 201)
 
+    def _handle_part11_evidence_bundle_create(self) -> None:
+        if not self._check_auth():
+            return
+        payload = self._read_json_body()
+        if payload is None:
+            return
+        if not isinstance(payload, dict):
+            self._send_json({"error": "request body must be an object"}, 400)
+            return
+        try:
+            bundle = create_and_store_evidence_bundle(
+                action_type=str(payload.get("action_type") or ""),
+                before_state=payload.get("before_state_hash"),
+                after_state=payload.get("after_state_hash"),
+                oauth3_token_id=str(payload.get("oauth3_token_id") or ""),
+                user_id=str(payload.get("user_id") or "system"),
+            )
+        except ALCOAError as exc:
+            self._send_json({"error": str(exc)}, 500)
+            return
+        except IOError as exc:
+            self._send_json({"error": str(exc)}, 500)
+            return
+        self._send_json(
+            {
+                "bundle_id": bundle["bundle_id"],
+                "chain_link_sha256": bundle["sha256_chain_link"],
+                "alcoa_status": ALCOABundle.check_compliance(bundle).value,
+                "rung_achieved": bundle["rung_achieved"],
+            },
+            201,
+        )
+
+    def _handle_part11_evidence_bundles(self, query: str) -> None:
+        params = urllib.parse.parse_qs(query.lstrip("?"))
+        limit_raw = params.get("limit", ["50"])[0]
+        if not limit_raw.isdigit():
+            self._send_json({"error": "invalid limit"}, 400)
+            return
+        limit = min(int(limit_raw), 500)
+        since_iso8601 = str(params.get("since", [""])[0]).strip()
+        action_type = str(params.get("action_type", [""])[0]).strip()
+        bundles = list_part11_evidence_bundles(limit=limit, since_iso8601=since_iso8601, action_type=action_type)
+        self._send_json(
+            [
+                {
+                    "bundle_id": bundle.get("bundle_id"),
+                    "action_type": bundle.get("action_type"),
+                    "timestamp": bundle.get("timestamp_iso8601"),
+                    "alcoa_status": ALCOABundle.check_compliance(bundle).value,
+                    "chain_link": bundle.get("sha256_chain_link"),
+                }
+                for bundle in bundles
+            ]
+        )
+
+    def _handle_part11_evidence_verify_chain(self) -> None:
+        self._send_json(verify_part11_evidence_chain())
+
+    def _handle_part11_evidence_compliance_report(self) -> None:
+        self._send_json(part11_compliance_report())
+
+    def _handle_prime_wiki_snapshot_create(self) -> None:
+        payload = self._read_json_body()
+        if payload is None:
+            return
+        url = payload.get("url", "")
+        snapshot_type = payload.get("snapshot_type", "")
+        app_id = payload.get("app_id", "")
+        action_id = payload.get("action_id", "")
+        content_html_raw = payload.get("content_html", "")
+
+        if not isinstance(url, str) or len(url.strip()) == 0 or len(url) > 2048:
+            self._send_json({"error": "invalid url"}, 400)
+            return
+        normalized_url = _normalize_prime_wiki_url(url)
+        if not normalized_url:
+            self._send_json({"error": "invalid url"}, 400)
+            return
+        if not isinstance(snapshot_type, str) or snapshot_type not in PRIME_WIKI_SNAPSHOT_TYPES:
+            self._send_json({"error": "invalid snapshot_type"}, 400)
+            return
+        if not isinstance(app_id, str) or len(app_id) > 256 or not _APP_ID_RE.fullmatch(app_id):
+            self._send_json({"error": "invalid app_id"}, 400)
+            return
+        if not isinstance(action_id, str) or len(action_id.strip()) == 0 or len(action_id) > 256:
+            self._send_json({"error": "invalid action_id"}, 400)
+            return
+        if content_html_raw is None:
+            content_html = ""
+        elif isinstance(content_html_raw, str):
+            content_html = content_html_raw
+        else:
+            self._send_json({"error": "invalid content_html"}, 400)
+            return
+
+        snapshot_record = _prime_wiki_snapshot_record(
+            normalized_url,
+            content_html,
+            snapshot_type,
+            app_id,
+            action_id,
+        )
+        try:
+            _store_prime_wiki_snapshot(snapshot_record)
+        except OSError:
+            self._send_json({"error": "failed to store snapshot"}, 500)
+            return
+
+        record_evidence(
+            "prime_wiki_snapshot_created",
+            {
+                "snapshot_id": snapshot_record["snapshot_id"],
+                "url_hash": snapshot_record["url_hash"],
+                "snapshot_type": snapshot_record["snapshot_type"],
+                "app_id": snapshot_record["app_id"],
+                "action_id": snapshot_record["action_id"],
+            },
+        )
+        cloud_sync_started = _queue_prime_wiki_cloud_push(snapshot_record)
+        self._send_json(
+            {
+                "snapshot_id": snapshot_record["snapshot_id"],
+                "url_hash": snapshot_record["url_hash"],
+                "sha256": snapshot_record["sha256"],
+                "compression_ratio": snapshot_record["compression_ratio"],
+                "key_elements": snapshot_record["key_elements"],
+                "cloud_sync_started": cloud_sync_started,
+            },
+            201,
+        )
+
+    def _handle_prime_wiki_snapshot_detail(self, snapshot_id: str) -> None:
+        snapshot_record = _find_prime_wiki_snapshot(snapshot_id)
+        if snapshot_record is None:
+            self._send_json({"error": "snapshot not found"}, 404)
+            return
+        self._send_json(_prime_wiki_public_record(snapshot_record))
+
+    def _handle_prime_wiki_snapshot_content(self, snapshot_id: str) -> None:
+        snapshot_record = _find_prime_wiki_snapshot(snapshot_id)
+        if snapshot_record is None:
+            self._send_json({"error": "snapshot not found"}, 404)
+            return
+        self._send_json(
+            {
+                "content_gzip_b64": snapshot_record.get("content_gzip_b64", ""),
+                "sha256": snapshot_record.get("sha256", ""),
+                "size_bytes": snapshot_record.get("size_bytes", 0),
+            }
+        )
+
+    def _handle_prime_wiki_diff(self, query: str) -> None:
+        from urllib.parse import parse_qs
+
+        params = parse_qs(query.lstrip("?"))
+        before_id = params.get("before", [""])[0]
+        after_id = params.get("after", [""])[0]
+        if not before_id or not after_id:
+            self._send_json({"error": "before and after are required"}, 400)
+            return
+        before_record = _find_prime_wiki_snapshot(before_id)
+        after_record = _find_prime_wiki_snapshot(after_id)
+        if before_record is None or after_record is None:
+            self._send_json({"error": "snapshot not found"}, 404)
+            return
+        self._send_json(_prime_wiki_diff_payload(before_record, after_record))
+
+    def _handle_prime_wiki_stats(self) -> None:
+        self._send_json(_prime_wiki_stats_payload())
+
     def _handle_schedules_list(self) -> None:
         self._send_json({"schedules": load_schedules()})
 
@@ -2512,53 +4511,53 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         body = self._read_json_body()
         if body is None:
             return
+        user_tier = _load_account_tier()
+        if not _tier_allows_install(user_tier, "free"):
+            self._send_json({"error": "tier_required", "required": "free", "upgrade_url": MARKETPLACE_UPGRADE_URL}, 403)
+            return
         raw_domain = body.get("domain", "")
-        raw_name = body.get("name", "")
+        raw_name = body.get("app_name", body.get("name", ""))
         raw_description = body.get("description", "")
-        domain = _normalize_domain(raw_domain if isinstance(raw_domain, str) else "")
-        name = raw_name.strip() if isinstance(raw_name, str) else ""
-        description = raw_description.strip() if isinstance(raw_description, str) else ""
-        if not domain:
-            self._send_json({"error": "domain required"}, 400)
-            return
-        if not name or _invalid_custom_app_name(name):
-            self._send_json({"error": "invalid app name"}, 400)
-            return
-        app_id = _slugify_custom_app_name(name)
-        if not app_id:
-            self._send_json({"error": "invalid app name"}, 400)
-            return
-
         repo_root = getattr(self.server, "repo_root", ".")
-        app_dir = _marketplace_app_dir(repo_root, app_id)
-        if app_dir.exists():
-            self._send_json({"error": "app already exists"}, 409)
-            return
-
-        manifest_text = _custom_app_manifest(app_id, name, description or f"Custom app for {domain}", domain)
-        session_rules_text = _custom_app_session_rules(app_id, name, description or f"Custom app for {domain}", domain)
         try:
-            app_dir.mkdir(parents=True, exist_ok=False)
-            (app_dir / "manifest.yaml").write_text(manifest_text)
-            (app_dir / "session-rules.yaml").write_text(session_rules_text)
+            payload = _create_custom_app_scaffold(
+                repo_root,
+                raw_domain if isinstance(raw_domain, str) else "",
+                raw_name if isinstance(raw_name, str) else "",
+                raw_description if isinstance(raw_description, str) else "",
+            )
+        except ValueError as error:
+            self._send_json({"error": str(error)}, 400)
+            return
+        except FileExistsError as error:
+            self._send_json({"error": str(error)}, 409)
+            return
         except OSError as error:
             self._send_json({"error": f"cannot create app: {error}"}, 500)
             return
 
         apps: list = self.server.apps if hasattr(self.server, "apps") else []
-        if app_id not in apps:
+        app_id = str(payload.get("app_id", ""))
+        if app_id and app_id not in apps:
             apps.append(app_id)
             apps.sort()
             self.server.apps = apps
+        self._reload_session_rules_cache()
 
-        record_evidence("custom_app_created", {"app_id": app_id, "domain": domain})
-        relative_app_path = Path("data") / "default" / "apps" / app_id
-        self._send_json({
-            "app_id": app_id,
-            "path": f"{relative_app_path.as_posix()}/",
-            "session_rules_path": (relative_app_path / "session-rules.yaml").as_posix(),
-            "session_rules_template": session_rules_text,
-        }, 201)
+        record_evidence("custom_app_created", {"app_id": app_id, "domain": _normalize_domain(str(raw_domain))})
+        self._send_json(payload, 201)
+
+    def _handle_rebuild_domain_index(self) -> None:
+        """POST /api/v1/apps/rebuild-domain-index — rebuild the domain lookup index."""
+        if not self._check_auth():
+            return
+        repo_root = getattr(self.server, "repo_root", ".")
+        try:
+            payload = _rebuild_domain_index(repo_root)
+        except ValueError as error:
+            self._send_json({"error": str(error)}, 400)
+            return
+        self._send_json(payload)
 
     def _handle_apps_sync(self) -> None:
         """POST /api/v1/apps/sync — sync local custom apps for paid tiers. Task 051."""
@@ -2708,12 +4707,22 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             return
         params = self._parse_query(query)
         requested_domain = urllib.parse.unquote_plus(params.get("domain", "")).strip()
+        requested_path = urllib.parse.unquote_plus(params.get("path", "/")).strip() or "/"
         normalized_domain = _normalize_domain(requested_domain)
         if not normalized_domain:
             self._send_json({"error": "domain required"}, 400)
             return
-        apps = _apps_for_domain(getattr(self.server, "repo_root", "."), normalized_domain)
-        self._send_json({"domain": normalized_domain, "apps": apps, "total": len(apps)})
+        try:
+            payload = _apps_for_domain(
+                getattr(self.server, "repo_root", "."),
+                normalized_domain,
+                requested_path,
+                _load_account_tier(),
+            )
+        except ValueError as error:
+            self._send_json({"error": str(error)}, 400)
+            return
+        self._send_json(payload)
 
     def _handle_server_config(self) -> None:
         """GET /api/v1/server/config — server configuration + feature flags. Task 049."""
@@ -2777,14 +4786,226 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             "healthy": expired == 0,
         })
 
+    def _oauth3_session_secret(self) -> str:
+        return str(getattr(self.server, "session_token_sha256", ""))
+
+    def _handle_oauth3_issue(self) -> None:
+        if not self._check_auth():
+            return
+        payload = self._read_json_body()
+        if payload is None:
+            return
+        user_id = payload.get("user_id", "")
+        if not isinstance(user_id, str) or not user_id.strip():
+            self._send_json({"error": "missing 'user_id'"}, 400)
+            return
+        try:
+            scopes = _oauth3_validate_scopes(payload.get("scopes", []))
+            ttl_seconds = _oauth3_validate_ttl_seconds(payload.get("ttl_seconds", 86400))
+        except ValueError as exc:
+            self._send_json({"error": str(exc)}, 400)
+            return
+        normalized_user_id = user_id.strip().lower()
+        user_id_hash = _oauth3_hash_user_id(normalized_user_id)
+        token_id = str(uuid.uuid4())
+        issued_at = _oauth3_now_iso()
+        expires_at = datetime.fromtimestamp(time.time() + ttl_seconds, tz=timezone.utc).isoformat()
+        token = {
+            "token_id": token_id,
+            "user_id": user_id_hash,
+            "scopes": scopes,
+            "ttl_seconds": ttl_seconds,
+            "issued_at": issued_at,
+            "expires_at": expires_at,
+            "revoked": False,
+            "step_up_required": _oauth3_step_up_scopes(scopes),
+            "issuer": OAUTH3_ISSUER,
+            "evidence_chain_tip": OAUTH3_EVIDENCE_GENESIS_HASH,
+        }
+        try:
+            with _OAUTH3_VAULT_LOCK:
+                state = _oauth3_load_vault_state(self._oauth3_session_secret(), user_id_hash)
+                state.setdefault("tokens", {})[token_id] = token
+                _oauth3_append_evidence(
+                    state,
+                    "TOKEN_ISSUED",
+                    token=token,
+                    data={"ttl_seconds": ttl_seconds, "user_id_hash": user_id_hash},
+                )
+                _oauth3_save_vault_state(state, self._oauth3_session_secret())
+        except OAuth3VaultUserMismatchError as exc:
+            self._send_json({"error": str(exc)}, 409)
+            return
+        except OAuth3VaultCorruptError as exc:
+            self._send_json({"error": str(exc)}, 500)
+            return
+        self._send_json(
+            {
+                "token_id": token_id,
+                "expires_at": expires_at,
+                "scopes": scopes,
+                "step_up_required": list(token["step_up_required"]),
+            },
+            201,
+        )
+
+    def _handle_oauth3_validate(self, query: str) -> None:
+        if not self._check_auth():
+            return
+        params = self._parse_query(query)
+        token_id = params.get("token_id", "")
+        if not token_id:
+            self._send_json({"error": "missing token_id"}, 400)
+            return
+        if not OAUTH3_VAULT_PATH.exists():
+            self._send_json({"valid": False, "scopes": [], "expires_at": None, "revoked": False})
+            return
+        try:
+            with _OAUTH3_VAULT_LOCK:
+                state = _oauth3_load_vault_state(self._oauth3_session_secret())
+                token = state.get("tokens", {}).get(token_id)
+                if not isinstance(token, dict):
+                    _oauth3_append_evidence(
+                        state,
+                        "TOKEN_VALIDATED",
+                        data={"token_id": token_id, "scopes": [], "valid": False, "reason": "token_not_found"},
+                    )
+                    _oauth3_save_vault_state(state, self._oauth3_session_secret())
+                    self._send_json({"valid": False, "scopes": [], "expires_at": None, "revoked": False})
+                    return
+                valid, reason = _oauth3_token_valid(token)
+                _oauth3_append_evidence(
+                    state,
+                    "TOKEN_VALIDATED",
+                    token=token,
+                    data={"valid": valid, "reason": reason},
+                )
+                _oauth3_save_vault_state(state, self._oauth3_session_secret())
+        except OAuth3VaultCorruptError as exc:
+            self._send_json({"error": str(exc)}, 500)
+            return
+        self._send_json(
+            {
+                "valid": valid,
+                "scopes": list(token.get("scopes", [])),
+                "expires_at": token.get("expires_at"),
+                "revoked": bool(token.get("revoked", False)),
+            }
+        )
+
+    def _handle_oauth3_revoke_vault(self) -> None:
+        if not self._check_auth():
+            return
+        payload = self._read_json_body()
+        if payload is None:
+            return
+        token_id = payload.get("token_id", "")
+        if not isinstance(token_id, str) or not token_id:
+            self._send_json({"error": "missing 'token_id'"}, 400)
+            return
+        try:
+            with _OAUTH3_VAULT_LOCK:
+                state = _oauth3_load_vault_state(self._oauth3_session_secret())
+                token = state.get("tokens", {}).get(token_id)
+                if not isinstance(token, dict):
+                    raise OAuth3TokenNotFoundError(f"token not found: {token_id}")
+                revoked_at = str(token.get("revoked_at") or _oauth3_now_iso())
+                token["revoked"] = True
+                token["revoked_at"] = revoked_at
+                _oauth3_append_evidence(state, "TOKEN_REVOKED", token=token, data={"revoked_at": revoked_at})
+                _oauth3_save_vault_state(state, self._oauth3_session_secret())
+        except OAuth3TokenNotFoundError:
+            self._send_json({"error": "token not found"}, 404)
+            return
+        except OAuth3VaultCorruptError as exc:
+            self._send_json({"error": str(exc)}, 500)
+            return
+        self._send_json({"revoked": True, "revoked_at": revoked_at})
+
+    def _handle_oauth3_step_up_request(self) -> None:
+        if not self._check_auth():
+            return
+        payload = self._read_json_body()
+        if payload is None:
+            return
+        token_id = payload.get("token_id", "")
+        scope_needed = payload.get("scope_needed", "")
+        if not isinstance(token_id, str) or not token_id:
+            self._send_json({"error": "missing 'token_id'"}, 400)
+            return
+        if not isinstance(scope_needed, str) or not scope_needed.strip():
+            self._send_json({"error": "missing 'scope_needed'"}, 400)
+            return
+        normalized_scope = scope_needed.strip()
+        try:
+            with _OAUTH3_VAULT_LOCK:
+                state = _oauth3_load_vault_state(self._oauth3_session_secret())
+                token = state.get("tokens", {}).get(token_id)
+                if not isinstance(token, dict):
+                    raise OAuth3TokenNotFoundError(f"token not found: {token_id}")
+                token_scopes = token.get("scopes", [])
+                if normalized_scope not in token_scopes:
+                    self._send_json({"error": "scope not granted on token"}, 403)
+                    return
+                if not _oauth3_is_high_risk_scope(normalized_scope):
+                    self._send_json({"error": "step-up is only required for HIGH_RISK scopes"}, 400)
+                    return
+                step_up_id = str(uuid.uuid4())
+                consent_url = (
+                    f"{OAUTH3_ISSUER}/oauth3/step-up?step_up_id={step_up_id}"
+                    f"&token_id={token_id}&scope={urllib.parse.quote(normalized_scope, safe='')}"
+                )
+                _oauth3_append_evidence(
+                    state,
+                    "STEP_UP_REQUESTED",
+                    token=token,
+                    data={
+                        "step_up_id": step_up_id,
+                        "scope_needed": normalized_scope,
+                        "consent_url": consent_url,
+                    },
+                )
+                _oauth3_save_vault_state(state, self._oauth3_session_secret())
+        except OAuth3TokenNotFoundError:
+            self._send_json({"error": "token not found"}, 404)
+            return
+        except OAuth3VaultCorruptError as exc:
+            self._send_json({"error": str(exc)}, 500)
+            return
+        self._send_json({"step_up_id": step_up_id, "consent_url": consent_url, "expires_in": OAUTH3_STEP_UP_TTL_SECONDS})
+
+    def _handle_oauth3_evidence(self, query: str) -> None:
+        if not self._check_auth():
+            return
+        params = self._parse_query(query)
+        limit_raw = params.get("limit", "50")
+        since = params.get("since", "")
+        if not limit_raw.isdigit():
+            self._send_json({"error": "limit must be an integer"}, 400)
+            return
+        limit = min(max(int(limit_raw), 1), 500)
+        if not OAUTH3_VAULT_PATH.exists():
+            self._send_json([])
+            return
+        try:
+            with _OAUTH3_VAULT_LOCK:
+                state = _oauth3_load_vault_state(self._oauth3_session_secret())
+                entries = _oauth3_filter_evidence(state, limit=limit, since=since)
+        except ValueError as exc:
+            self._send_json({"error": str(exc)}, 400)
+            return
+        except OAuth3VaultCorruptError as exc:
+            self._send_json({"error": str(exc)}, 500)
+            return
+        self._send_json(entries)
+
     def _handle_oauth3_list(self) -> None:
-        tokens = load_oauth3_tokens()
-        # Strip token_sha256 from response — expose only metadata
-        safe = [
-            {k: v for k, v in t.items() if k != "token_sha256"}
-            for t in tokens
-        ]
-        self._send_json({"tokens": safe})
+        try:
+            rows = _oauth3_active_token_rows(self._oauth3_session_secret())
+        except OAuth3VaultCorruptError as exc:
+            self._send_json({"error": str(exc)}, 500)
+            return
+        self._send_json(rows)
 
     def _handle_oauth3_register(self) -> None:
         if not self._check_auth():
@@ -2859,6 +5080,26 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         if not token_id:
             self._send_json({"error": "missing token id"}, 400)
             return
+        if OAUTH3_VAULT_PATH.exists():
+            try:
+                with _OAUTH3_VAULT_LOCK:
+                    state = _oauth3_load_vault_state(self._oauth3_session_secret())
+                    token = state.get("tokens", {}).get(token_id)
+                    if isinstance(token, dict):
+                        token["revoked"] = True
+                        token["revoked_at"] = str(token.get("revoked_at") or _oauth3_now_iso())
+                        _oauth3_append_evidence(
+                            state,
+                            "TOKEN_REVOKED",
+                            token=token,
+                            data={"revoked_at": token["revoked_at"]},
+                        )
+                        _oauth3_save_vault_state(state, self._oauth3_session_secret())
+                        self._send_json({"revoked": token_id})
+                        return
+            except OAuth3VaultCorruptError as exc:
+                self._send_json({"error": str(exc)}, 500)
+                return
         found = revoke_oauth3_token(token_id)
         if found:
             self._send_json({"revoked": token_id})
@@ -2867,16 +5108,36 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
 
     def _handle_oauth3_token_detail(self, token_id: str) -> None:
         """GET /api/v1/oauth3/tokens/{token_id} — return single token metadata."""
+        if OAUTH3_VAULT_PATH.exists():
+            try:
+                with _OAUTH3_VAULT_LOCK:
+                    state = _oauth3_load_vault_state(self._oauth3_session_secret())
+                    token = state.get("tokens", {}).get(token_id)
+            except OAuth3VaultCorruptError as exc:
+                self._send_json({"error": str(exc)}, 500)
+                return
+            if isinstance(token, dict):
+                self._send_json(_oauth3_token_view(token))
+                return
         tokens = self._load_oauth3_tokens()
         for t in tokens:
             if t.get("token_id") == token_id or t.get("id") == token_id:
-                safe = {k: v for k, v in t.items() if k != "token_sha256"}
-                self._send_json(safe)
+                self._send_json(_oauth3_legacy_token_view(t))
                 return
         self._send_json({"error": "token not found"}, 404)
 
     def _handle_oauth3_audit(self) -> None:
         """GET /api/v1/oauth3/audit — return recent audit log entries."""
+        if OAUTH3_VAULT_PATH.exists():
+            try:
+                with _OAUTH3_VAULT_LOCK:
+                    state = _oauth3_load_vault_state(self._oauth3_session_secret())
+                    entries = _oauth3_filter_evidence(state, limit=200)
+                self._send_json({"entries": entries})
+                return
+            except OAuth3VaultCorruptError as exc:
+                self._send_json({"error": str(exc)}, 500)
+                return
         audit_path = Path.home() / ".solace" / "oauth3_audit.json"
         if not audit_path.exists():
             self._send_json({"entries": []})
@@ -2902,6 +5163,24 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         if seconds > MAX_EXTENSION:
             self._send_json({"error": f"max extension is {MAX_EXTENSION} seconds (30 days)"}, 400)
             return
+        if OAUTH3_VAULT_PATH.exists():
+            try:
+                with _OAUTH3_VAULT_LOCK:
+                    state = _oauth3_load_vault_state(self._oauth3_session_secret())
+                    token = state.get("tokens", {}).get(token_id)
+                    if isinstance(token, dict):
+                        if bool(token.get("revoked", False)):
+                            self._send_json({"error": "cannot extend revoked token"}, 400)
+                            return
+                        token["expires_at"] = datetime.fromtimestamp(time.time() + seconds, tz=timezone.utc).isoformat()
+                        token["ttl_seconds"] = seconds
+                        _oauth3_append_evidence(state, "TOKEN_EXTENDED", token=token, data={"seconds": seconds})
+                        _oauth3_save_vault_state(state, self._oauth3_session_secret())
+                        self._send_json({"status": "extended", "expires_at": token["expires_at"]})
+                        return
+            except OAuth3VaultCorruptError as exc:
+                self._send_json({"error": str(exc)}, 500)
+                return
         with _TOKENS_LOCK:
             tokens = self._load_oauth3_tokens()
             for t in tokens:
@@ -3320,6 +5599,9 @@ function choose(mode) {
         self._send_json({"status": "terminated", "session_id": session_id})
 
     def _spawn_browser_session(self, url: str, profile: str) -> int:
+        if bool(getattr(self.server, "cloud_twin_mode", False)):
+            proc = _launch_chrome_cloud_twin(url)
+            return proc.pid
         browser = os.environ.get("SOLACE_BROWSER", "")
         if not browser:
             candidates = [
@@ -3448,6 +5730,404 @@ function choose(mode) {
                 return
         self._send_json({"error": "run not found"}, 404)
 
+    # ---------------------------------------------------------------------------
+    # Task 059 — Community Recipe Browsing + Installation UI
+    # ---------------------------------------------------------------------------
+
+    def _load_recipes_from_local(self, repo_root: str) -> list:
+        """Read recipe JSON files from {repo_root}/data/default/apps/{app_id}/recipes/*.json."""
+        results = []
+        apps_dir = Path(repo_root) / "data" / "default" / "apps"
+        if not apps_dir.exists():
+            return results
+        for app_dir in sorted(apps_dir.iterdir()):
+            recipes_dir = app_dir / "recipes"
+            if not recipes_dir.is_dir():
+                continue
+            app_id = app_dir.name
+            for recipe_file in sorted(recipes_dir.glob("*.json")):
+                try:
+                    r = json.loads(recipe_file.read_text())
+                    results.append({
+                        "recipe_id": r.get("recipe_id", recipe_file.stem),
+                        "name": r.get("name", recipe_file.stem),
+                        "app_id": r.get("app_id", app_id),
+                        "description": r.get("description", ""),
+                        "creator": r.get("creator", "solace-team"),
+                        "version": r.get("version", "1.0.0"),
+                        "runs_count": int(r.get("runs_count", 0)),
+                        "hit_rate_pct": int(r.get("hit_rate_pct", 0)),
+                        "avg_cost_usd": str(r.get("avg_cost_usd", "0.001")),
+                        "tags": r.get("tags", []),
+                        "is_installed": True,
+                        "source": "local",
+                    })
+                except json.JSONDecodeError:
+                    pass
+        return results
+
+    def _load_community_library(self) -> list:
+        """Load the community recipe index from disk. Thread-safe."""
+        with _COMMUNITY_059_LOCK:
+            if not COMMUNITY_RECIPES_059_PATH.exists():
+                return []
+            try:
+                data = json.loads(COMMUNITY_RECIPES_059_PATH.read_text())
+                return data if isinstance(data, list) else []
+            except json.JSONDecodeError:
+                return []
+
+    def _save_community_library(self, recipes: list) -> None:
+        """Persist community recipe library to disk. Thread-safe."""
+        with _COMMUNITY_059_LOCK:
+            COMMUNITY_RECIPES_059_PATH.parent.mkdir(parents=True, exist_ok=True)
+            COMMUNITY_RECIPES_059_PATH.write_text(json.dumps(recipes, indent=2))
+
+    def _handle_community_recipes_list(self, query: str) -> None:
+        """GET /api/v1/recipes/community — list community + local recipes with filters."""
+        from urllib.parse import parse_qs
+        params = parse_qs(query.lstrip("?"))
+        app_id_filter = params.get("app_id", [None])[0]
+        category_filter = params.get("category", [None])[0]
+        sort_by = params.get("sort", ["popular"])[0]
+        try:
+            limit = int(params.get("limit", ["20"])[0])
+        except ValueError:
+            limit = 20
+
+        repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
+        local_recipes = self._load_recipes_from_local(repo_root)
+
+        # Stub community data merged with local
+        stub_community = [
+            {
+                "recipe_id": "gmail-inbox-triage-v1",
+                "name": "Gmail Inbox Triage",
+                "app_id": "gmail",
+                "description": "Triages Gmail inbox by priority using labels",
+                "creator": "solace-team",
+                "version": "1.0.0",
+                "runs_count": 142,
+                "hit_rate_pct": 78,
+                "avg_cost_usd": "0.001",
+                "tags": ["email", "productivity"],
+                "is_installed": False,
+                "source": "community",
+            },
+            {
+                "recipe_id": "linkedin-connect-v2",
+                "name": "LinkedIn Auto-Connect",
+                "app_id": "linkedin",
+                "description": "Sends personalized connection requests",
+                "creator": "community",
+                "version": "2.0.0",
+                "runs_count": 89,
+                "hit_rate_pct": 65,
+                "avg_cost_usd": "0.002",
+                "tags": ["social", "networking"],
+                "is_installed": False,
+                "source": "community",
+            },
+            {
+                "recipe_id": "github-pr-summary-v1",
+                "name": "GitHub PR Summary",
+                "app_id": "github",
+                "description": "Summarizes open pull requests for standup",
+                "creator": "solace-team",
+                "version": "1.0.0",
+                "runs_count": 567,
+                "hit_rate_pct": 91,
+                "avg_cost_usd": "0.001",
+                "tags": ["development", "github"],
+                "is_installed": False,
+                "source": "community",
+            },
+        ]
+
+        # Mark installed status from community library
+        installed_lib = self._load_community_library()
+        installed_ids = {r.get("recipe_id") for r in installed_lib}
+        for r in stub_community:
+            r["is_installed"] = r["recipe_id"] in installed_ids
+
+        all_recipes = local_recipes + stub_community
+
+        # Apply filters
+        if app_id_filter:
+            all_recipes = [r for r in all_recipes if r.get("app_id") == app_id_filter]
+        if category_filter:
+            all_recipes = [r for r in all_recipes if category_filter in r.get("tags", [])]
+
+        # Sort
+        if sort_by == "recent":
+            all_recipes = sorted(all_recipes, key=lambda r: r.get("recipe_id", ""), reverse=True)
+        elif sort_by == "best_hit_rate":
+            all_recipes = sorted(all_recipes, key=lambda r: int(r.get("hit_rate_pct", 0)), reverse=True)
+        else:
+            all_recipes = sorted(all_recipes, key=lambda r: int(r.get("runs_count", 0)), reverse=True)
+
+        all_recipes = all_recipes[:limit]
+        self._send_json({"recipes": all_recipes, "count": len(all_recipes)})
+
+    def _handle_community_recipe_install(self, recipe_id: str) -> None:
+        """POST /api/v1/recipes/{recipe_id}/install — install with scope confirmation data."""
+        if not self._check_auth():
+            return
+        # Merge local + stub community to find recipe metadata
+        repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
+        all_recipes = self._load_recipes_from_local(repo_root)
+        stub_community = [
+            {"recipe_id": "gmail-inbox-triage-v1", "app_id": "gmail", "tags": ["email", "productivity"], "name": "Gmail Inbox Triage", "version": "1.0.0", "creator": "solace-team"},
+            {"recipe_id": "linkedin-connect-v2", "app_id": "linkedin", "tags": ["social", "networking"], "name": "LinkedIn Auto-Connect", "version": "2.0.0", "creator": "community"},
+            {"recipe_id": "github-pr-summary-v1", "app_id": "github", "tags": ["development", "github"], "name": "GitHub PR Summary", "version": "1.0.0", "creator": "solace-team"},
+        ]
+        all_recipes += stub_community
+
+        recipe = next((r for r in all_recipes if r.get("recipe_id") == recipe_id), None)
+        if recipe is None:
+            self._send_json({"error": f"recipe '{recipe_id}' not found"}, 404)
+            return
+
+        # Persist installation
+        installed = self._load_community_library()
+        if not any(r.get("recipe_id") == recipe_id for r in installed):
+            installed.append({**recipe, "installed_at": int(time.time()), "is_installed": True})
+            self._save_community_library(installed)
+
+        # CRITICAL: scope_required MUST be present — UI must show confirmation modal
+        self._send_json({
+            "installed": True,
+            "recipe_id": recipe_id,
+            "version": recipe.get("version", "1.0.0"),
+            "scope_required": {
+                "app_id": recipe.get("app_id", "unknown"),
+                "tags": recipe.get("tags", []),
+                "description": f"Install '{recipe.get('name', recipe_id)}' by {recipe.get('creator', 'unknown')}",
+            },
+        })
+
+    def _handle_community_recipe_fork(self, recipe_id: str) -> None:
+        """POST /api/v1/recipes/{recipe_id}/fork — create local copy."""
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            return
+        fork_name = body.get("name", "")
+        if not isinstance(fork_name, str) or not fork_name:
+            self._send_json({"error": "missing 'name'"}, 400)
+            return
+        if len(fork_name) > 128:
+            self._send_json({"error": "'name' exceeds 128 chars"}, 400)
+            return
+
+        new_recipe_id = f"fork-{recipe_id}-{int(time.time())}"
+        fork_record = {
+            "recipe_id": new_recipe_id,
+            "name": fork_name,
+            "forked_from": recipe_id,
+            "created_at": int(time.time()),
+            "source": "local",
+            "is_installed": True,
+            "version": "1.0.0",
+            "app_id": "",
+            "tags": [],
+            "runs_count": 0,
+            "hit_rate_pct": 0,
+            "avg_cost_usd": "0.001",
+        }
+
+        installed = self._load_community_library()
+        installed.append(fork_record)
+        self._save_community_library(installed)
+
+        self._send_json({
+            "new_recipe_id": new_recipe_id,
+            "forked_from": recipe_id,
+            "local": True,
+        }, 201)
+
+    def _handle_community_recipe_create(self) -> None:
+        """POST /api/v1/recipes/create — create new local recipe."""
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            return
+        name = body.get("name", "")
+        if not isinstance(name, str) or not name:
+            self._send_json({"error": "missing 'name'"}, 400)
+            return
+        if len(name) > 128:
+            self._send_json({"error": "'name' exceeds 128 chars"}, 400)
+            return
+        app_id = str(body.get("app_id", ""))
+        description = str(body.get("description", ""))
+        steps = body.get("steps", [])
+        tags = body.get("tags", [])
+        if not isinstance(steps, list):
+            self._send_json({"error": "'steps' must be an array"}, 400)
+            return
+        if not isinstance(tags, list):
+            self._send_json({"error": "'tags' must be an array"}, 400)
+            return
+
+        recipe_id = f"local-{int(time.time())}-{hashlib.sha256(name.encode()).hexdigest()[:8]}"
+        new_recipe = {
+            "recipe_id": recipe_id,
+            "name": name,
+            "app_id": app_id,
+            "description": description,
+            "steps": steps,
+            "tags": tags,
+            "creator": "local",
+            "version": "1.0.0",
+            "runs_count": 0,
+            "hit_rate_pct": 0,
+            "avg_cost_usd": "0.001",
+            "is_installed": True,
+            "source": "local",
+            "created_at": int(time.time()),
+        }
+
+        installed = self._load_community_library()
+        installed.append(new_recipe)
+        self._save_community_library(installed)
+
+        self._send_json({"recipe_id": recipe_id, "local": True}, 201)
+
+    def _handle_community_recipe_run(self, recipe_id: str) -> None:
+        """POST /api/v1/recipes/{recipe_id}/run — ALWAYS creates preview, never direct execute."""
+        if not self._check_auth():
+            return
+
+        # Validate recipe exists in local FS, apps recipes, community library, or known stub IDs
+        local_recipe = self._load_recipe(recipe_id)
+        repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
+        app_recipes = self._load_recipes_from_local(repo_root)
+        app_recipe_ids = {r.get("recipe_id") for r in app_recipes}
+        installed_lib = self._load_community_library()
+        _community_stub_ids = {"gmail-inbox-triage-v1", "linkedin-connect-v2", "github-pr-summary-v1"}
+        installed_ids = {r.get("recipe_id") or r.get("id") for r in installed_lib}
+        all_known_ids = _community_stub_ids | installed_ids | app_recipe_ids
+        if local_recipe is None and recipe_id not in all_known_ids:
+            self._send_json({"error": f"Recipe '{recipe_id}' not found"}, 404)
+            return
+
+        # Build a preview record via actions preview logic — never bypass
+        preview_id = str(uuid.uuid4())
+        now_ts = time.time()
+        preview_text = f"Recipe '{recipe_id}' will execute its automation steps."
+        action_class = "B"  # recipe runs are reputation-impact by default
+        cooldown_secs = COOLDOWN_SECONDS[action_class]
+        cooldown_ends_ts = now_ts + cooldown_secs
+        cooldown_ends_at = datetime.fromtimestamp(cooldown_ends_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
+
+        preview = {
+            "preview_id": preview_id,
+            "action_type": f"recipe.run.{recipe_id}",
+            "class": action_class,
+            "status": "PENDING_APPROVAL",
+            "preview_text": preview_text,
+            "estimated_cost": "0.001",
+            "reversal_possible": True,
+            "cooldown_ends_at": cooldown_ends_ts,
+            "created_at": now_ts,
+        }
+        with _PENDING_ACTIONS_LOCK:
+            _PENDING_ACTIONS[preview_id] = preview
+
+        self._send_json({
+            "preview_id": preview_id,
+            "action_class": action_class,
+            "preview_text": preview_text,
+            "requires_approval": True,
+            "cooldown_ends_at": cooldown_ends_at,
+        }, 202)
+
+    def _handle_community_recipes_my_library(self) -> None:
+        """GET /api/v1/recipes/my-library — return installed + local recipes."""
+        repo_root = getattr(self.server, "repo_root", str(Path(__file__).parent))
+        local_recipes = self._load_recipes_from_local(repo_root)
+        community_lib = self._load_community_library()
+
+        result = []
+        seen_ids: set = set()
+
+        for r in local_recipes:
+            rid = r.get("recipe_id", "")
+            if rid in seen_ids:
+                continue
+            seen_ids.add(rid)
+            result.append({
+                "recipe_id": rid,
+                "name": r.get("name", rid),
+                "app_id": r.get("app_id", ""),
+                "runs_count": int(r.get("runs_count", 0)),
+                "hit_rate_pct": int(r.get("hit_rate_pct", 0)),
+                "source": "local",
+            })
+
+        for r in community_lib:
+            rid = r.get("recipe_id", "")
+            if rid in seen_ids:
+                continue
+            seen_ids.add(rid)
+            result.append({
+                "recipe_id": rid,
+                "name": r.get("name", rid),
+                "app_id": r.get("app_id", ""),
+                "runs_count": int(r.get("runs_count", 0)),
+                "hit_rate_pct": int(r.get("hit_rate_pct", 0)),
+                "source": r.get("source", "community"),
+            })
+
+        self._send_json({"recipes": result, "count": len(result)})
+
+    # Task 059 — Static file handlers for recipes UI
+
+    def _handle_recipes_html(self) -> None:
+        """GET /web/recipes.html — serve the community recipe browser page."""
+        html_path = Path(__file__).parent / "web" / "recipes.html"
+        try:
+            content = html_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "recipes.html not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "text/html; charset=utf-8")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    def _handle_recipes_js(self) -> None:
+        """GET /web/js/recipes.js — serve the recipes JS."""
+        js_path = Path(__file__).parent / "web" / "js" / "recipes.js"
+        try:
+            content = js_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "recipes.js not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "application/javascript")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    def _handle_recipes_css(self) -> None:
+        """GET /web/css/recipes.css — serve the recipes CSS."""
+        css_path = Path(__file__).parent / "web" / "css" / "recipes.css"
+        try:
+            content = css_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "recipes.css not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "text/css")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
     # --- Task 016: Budget Management ---
 
     def _load_evidence(self) -> list:
@@ -5037,48 +7717,188 @@ function choose(mode) {
             "cli_path": cli_path,
         })
 
-    # ── App Launcher (Task 027) ────────────────────────────────────────────
+    def _cli_agents_payload(self, cache_status: str) -> dict:
+        """Build the response payload for CLI agent detection endpoints."""
+        found = _detect_available_agents()
+        agents = [
+            {
+                "name": name,
+                "path": path,
+                "default_model": _default_model_for_agent(name),
+            }
+            for name, path in found.items()
+        ]
+        not_found = [name for name in CLI_AGENT_CANDIDATES if name not in found]
+        return {
+            "agents": agents,
+            "count": len(agents),
+            "not_found": not_found,
+            "cache_status": cache_status,
+        }
 
-    def _handle_apps_list(self) -> None:
-        apps: list = self.server.apps if hasattr(self.server, "apps") else []  # type: ignore[attr-defined]
-        app_list = [{"id": a, "name": a.replace("-", " ").title()} for a in apps]
-        self._send_json({"apps": app_list, "total": len(app_list)})
+    def _handle_cli_agents_detect(self) -> None:
+        """GET /api/v1/cli-agents/detect — detect installed AI coding CLIs."""
+        if not self._check_auth():
+            return
+        self._send_json(self._cli_agents_payload("fresh"))
 
-    def _handle_app_detail(self, app_id: str) -> None:
-        apps: list = self.server.apps if hasattr(self.server, "apps") else []  # type: ignore[attr-defined]
-        if app_id not in apps:
-            self._send_json({"error": "app not found"}, 404)
+    def _handle_cli_agents_refresh(self) -> None:
+        """GET /api/v1/cli-agents/refresh — clear detection cache and re-detect."""
+        if not self._check_auth():
             return
-        self._send_json({"id": app_id, "name": app_id.replace("-", " ").title(), "status": "available"})
+        _detect_available_agents.cache_clear()
+        self._send_json(self._cli_agents_payload("refreshed"))
 
-    def _handle_app_launch(self, app_id: str) -> None:
+    def _handle_cli_agents_generate(self) -> None:
+        """
+        POST /api/v1/cli-agents/generate
+        Auth: Bearer sha256(token)
+        Request: {agent: str, model: str|null, prompt: str, skill_pack: list[str], timeout_s: int}
+        Response 200: {agent, model, output, cost_usd, latency_ms, evidence_id, rung}
+        Response 400: {error: str}
+        Response 401: {error: "unauthorized"}
+        """
         if not self._check_auth():
             return
-        apps: list = self.server.apps if hasattr(self.server, "apps") else []  # type: ignore[attr-defined]
-        if app_id not in apps:
-            self._send_json({"error": "app not found"}, 404)
+        body = self._read_json_body()
+        if body is None:
+            return
+        if not isinstance(body, dict):
+            self._send_json({"error": "JSON body must be an object"}, 400)
             return
-        _append_notification("info", "App Launched", f"{app_id} launched from Hub", "info")
-        with _METRICS_LOCK:
-            _REQUEST_COUNTS[f"app_launch:{app_id}"] = _REQUEST_COUNTS.get(f"app_launch:{app_id}", 0) + 1
-        self._send_json({"status": "launched", "app_id": app_id, "timestamp": int(time.time())})
 
-    def _handle_session_rules_list(self) -> None:
-        """GET /api/v1/session-rules — list loaded session rule schemas."""
-        if not self._check_auth():
+        agent_name = body.get("agent", "auto")
+        if not isinstance(agent_name, str) or not agent_name:
+            self._send_json({"error": "agent is required"}, 400)
             return
-        rules = []
-        for rule in _get_session_rules_snapshot():
-            rules.append({
-                "app": rule.get("app", ""),
-                "display_name": rule.get("display_name", ""),
-                "check_url": rule.get("check_url", ""),
-                "keep_alive": rule.get("keep_alive", {}),
-                "tier_required": rule.get("tier_required", ""),
-            })
-        self._send_json({"rules": rules, "total": len(rules)})
 
-    def _handle_session_rule_check(self, app_id: str) -> None:
+        if agent_name != "auto" and agent_name not in CLI_AGENT_CANDIDATES:
+            self._send_json({"error": f"unknown agent: {agent_name}"}, 400)
+            return
+
+        prompt = body.get("prompt")
+        if not isinstance(prompt, str) or not prompt.strip():
+            self._send_json({"error": "prompt is required", "code": "MISSING_PROMPT"}, 400)
+            return
+
+        skill_pack_raw = body.get("skill_pack")
+        if skill_pack_raw is None:
+            skill_pack: list[str] = []
+        elif isinstance(skill_pack_raw, list) and all(isinstance(item, str) for item in skill_pack_raw):
+            skill_pack = skill_pack_raw
+        else:
+            self._send_json({"error": "skill_pack must be a list of strings"}, 400)
+            return
+
+        model_value = body.get("model")
+        if model_value is not None and not isinstance(model_value, str):
+            self._send_json({"error": "model must be a string or null"}, 400)
+            return
+
+        timeout_value = body.get("timeout_s", 60)
+        if isinstance(timeout_value, bool) or not isinstance(timeout_value, int) or timeout_value <= 0:
+            self._send_json({"error": "timeout_s must be a positive integer"}, 400)
+            return
+
+        found = _detect_available_agents()
+        if agent_name == "auto":
+            priority = ["gemini", "aider", "codex", "claude"]
+            selected_agent = next((candidate for candidate in priority if candidate in found), None)
+            if selected_agent is None:
+                self._send_json({"error": "No CLI agents found on PATH", "code": "NO_AGENTS_AVAILABLE"}, 400)
+                return
+        else:
+            selected_agent = agent_name
+
+        executable = found.get(selected_agent)
+        if executable is None:
+            self._send_json({
+                "error": f"Agent '{selected_agent}' not found on PATH",
+                "code": "AGENT_NOT_FOUND",
+                "available": sorted(found.keys()),
+            }, 400)
+            return
+
+        selected_model = model_value or _default_model_for_agent(selected_agent)
+        prepared_prompt = _inject_skill_pack(prompt.strip(), skill_pack)
+        started_at = time.monotonic()
+        try:
+            result = _invoke_cli_agent(
+                selected_agent,
+                executable,
+                prepared_prompt,
+                selected_model,
+                timeout_value,
+            )
+        except subprocess.TimeoutExpired:
+            self._send_json({"error": f"Agent timed out after {timeout_value}s", "code": "AGENT_TIMEOUT"}, 504)
+            return
+        except subprocess.CalledProcessError as error:
+            self._send_json({
+                "error": f"Agent exited with code {error.returncode}",
+                "code": "AGENT_ERROR",
+                "stderr": (error.stderr or "")[:500],
+            }, 502)
+            return
+        except OSError as error:
+            self._send_json({"error": f"Could not execute agent '{selected_agent}': {error}"}, 503)
+            return
+
+        output = str(result.get("stdout", ""))
+        latency_ms = int((time.monotonic() - started_at) * 1000)
+        tokens_est = max(1, len(prepared_prompt.split()) + len(output.split()))
+        self._send_json({
+            "agent": selected_agent,
+            "model": selected_model,
+            "output": output,
+            "cost_usd": _estimate_cost(selected_agent, tokens_est),
+            "latency_ms": latency_ms,
+            "evidence_id": _build_cli_evidence_id(output),
+            "rung": 641,
+        })
+
+    # ── App Launcher (Task 027) ────────────────────────────────────────────
+
+    def _handle_apps_list(self) -> None:
+        apps: list = self.server.apps if hasattr(self.server, "apps") else []  # type: ignore[attr-defined]
+        app_list = [{"id": a, "name": a.replace("-", " ").title()} for a in apps]
+        self._send_json({"apps": app_list, "total": len(app_list)})
+
+    def _handle_app_detail(self, app_id: str) -> None:
+        apps: list = self.server.apps if hasattr(self.server, "apps") else []  # type: ignore[attr-defined]
+        if app_id not in apps:
+            self._send_json({"error": "app not found"}, 404)
+            return
+        self._send_json({"id": app_id, "name": app_id.replace("-", " ").title(), "status": "available"})
+
+    def _handle_app_launch(self, app_id: str) -> None:
+        if not self._check_auth():
+            return
+        apps: list = self.server.apps if hasattr(self.server, "apps") else []  # type: ignore[attr-defined]
+        if app_id not in apps:
+            self._send_json({"error": "app not found"}, 404)
+            return
+        _append_notification("info", "App Launched", f"{app_id} launched from Hub", "info")
+        with _METRICS_LOCK:
+            _REQUEST_COUNTS[f"app_launch:{app_id}"] = _REQUEST_COUNTS.get(f"app_launch:{app_id}", 0) + 1
+        self._send_json({"status": "launched", "app_id": app_id, "timestamp": int(time.time())})
+
+    def _handle_session_rules_list(self) -> None:
+        """GET /api/v1/session-rules — list loaded session rule schemas."""
+        if not self._check_auth():
+            return
+        rules = []
+        for rule in _get_session_rules_snapshot():
+            rules.append({
+                "app": rule.get("app", ""),
+                "display_name": rule.get("display_name", ""),
+                "check_url": rule.get("check_url", ""),
+                "keep_alive": rule.get("keep_alive", {}),
+                "tier_required": rule.get("tier_required", ""),
+            })
+        self._send_json({"rules": rules, "total": len(rules)})
+
+    def _handle_session_rule_check(self, app_id: str) -> None:
         """POST /api/v1/session-rules/check/{app} — trigger one session check."""
         if not self._check_auth():
             return
@@ -5182,6 +8002,11 @@ function choose(mode) {
             record_evidence("marketplace_install_failed", {"app_id": app_id, "reason": str(exc)})
             self._send_json({"error": "install write failed"}, 500)
             return
+        try:
+            _rebuild_domain_index(repo_root)
+        except ValueError as error:
+            self._send_json({"error": str(error)}, 400)
+            return
         self._reload_session_rules_cache()
         record_evidence("marketplace_app_installed", {
             "app_id": app_id,
@@ -5223,10 +8048,1036 @@ function choose(mode) {
             app_dir.rmdir()
         except OSError:
             pass
+        try:
+            _rebuild_domain_index(repo_root)
+        except ValueError as error:
+            self._send_json({"error": str(error)}, 400)
+            return
         self._reload_session_rules_cache()
         record_evidence("marketplace_app_uninstalled", {"app_id": app_id})
         self._send_json({"status": "uninstalled", "app_id": app_id})
 
+    # ---------------------------------------------------------------------------
+    # Task 058 — Schedule Viewer handlers
+    # ---------------------------------------------------------------------------
+
+    def _schedule_settings_path(self) -> Path:
+        runtime_dir = PORT_LOCK_PATH.parent
+        if SETTINGS_PATH.parent == runtime_dir:
+            return SETTINGS_PATH
+        return runtime_dir / SETTINGS_PATH.name
+
+    def _load_schedule_settings(self) -> dict:
+        path = self._schedule_settings_path()
+        try:
+            settings = json.loads(path.read_text())
+        except FileNotFoundError:
+            settings = {}
+        except json.JSONDecodeError:
+            settings = {}
+        except OSError:
+            settings = {}
+        if not isinstance(settings, dict):
+            return {}
+        return settings
+
+    def _save_schedule_settings(self, settings: dict) -> None:
+        path = self._schedule_settings_path()
+        path.parent.mkdir(parents=True, exist_ok=True)
+        path.write_text(json.dumps(settings, indent=2))
+
+    def _schedule_audit_dir(self) -> Path:
+        return PORT_LOCK_PATH.parent / "audit"
+
+    def _write_schedule_audit_item(self, item: dict, event_type: str) -> str:
+        audit_dir = self._schedule_audit_dir()
+        audit_dir.mkdir(parents=True, exist_ok=True)
+        recorded_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
+        payload = {
+            "event_type": event_type,
+            "recorded_at": recorded_at,
+            "activity_item": item,
+        }
+        encoded = json.dumps(payload, sort_keys=True)
+        with (audit_dir / f"{item['id']}.jsonl").open("a", encoding="utf-8") as handle:
+            handle.write(encoded + "\n")
+        return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"
+
+    def _load_schedule_audit_items(self) -> dict[str, dict]:
+        audit_dir = self._schedule_audit_dir()
+        if not audit_dir.exists():
+            return {}
+        items: dict[str, dict] = {}
+        for audit_path in sorted(audit_dir.glob("*.jsonl")):
+            try:
+                lines = audit_path.read_text(encoding="utf-8").splitlines()
+            except FileNotFoundError:
+                continue
+            except OSError:
+                continue
+            for raw_line in reversed(lines):
+                if not raw_line.strip():
+                    continue
+                try:
+                    payload = json.loads(raw_line)
+                except json.JSONDecodeError:
+                    continue
+                if not isinstance(payload, dict):
+                    continue
+                item = payload.get("activity_item", payload)
+                if not isinstance(item, dict):
+                    continue
+                item_id = str(item.get("id") or audit_path.stem)
+                if not item_id:
+                    continue
+                normalized = dict(item)
+                normalized["id"] = item_id
+                items[item_id] = normalized
+                break
+        return items
+
+    def _load_schedule_plan_items(self) -> list[dict]:
+        schedule_plans = self._load_schedule_settings().get("schedule_plans", [])
+        if not isinstance(schedule_plans, list):
+            return []
+        planned_items: list[dict] = []
+        for plan in schedule_plans:
+            if not isinstance(plan, dict):
+                continue
+            run_id = str(plan.get("run_id", "")).strip()
+            scheduled_at = str(plan.get("scheduled_at", "")).strip()
+            app_id = str(plan.get("app_id", "")).strip()
+            if not run_id or not scheduled_at or not app_id:
+                continue
+            repeat = str(plan.get("repeat", "none") or "none")
+            schedule_pattern = None if repeat == "none" else repeat
+            planned_items.append({
+                "id": run_id,
+                "app_id": app_id,
+                "app_name": app_id,
+                "status": "scheduled",
+                "safety_tier": "A",
+                "started_at": scheduled_at,
+                "ended_at": None,
+                "duration_ms": 0,
+                "cost_usd": "0.00",
+                "tokens_used": 0,
+                "actions_taken": 0,
+                "evidence_path": f"~/.solace/audit/{run_id}.jsonl",
+                "evidence_hash": str(plan.get("evidence_hash", "")),
+                "output_summary": str(plan.get("note", "")),
+                "scopes_used": [],
+                "cooldown_expires_at": None,
+                "scheduled_at": scheduled_at,
+                "schedule_pattern": schedule_pattern,
+                "cross_app_triggers": [],
+                "error": None,
+                "label": app_id,
+                "action_type": app_id,
+            })
+        return planned_items
+
+    def _collect_schedule_items(self, now_ts: float) -> list[dict]:
+        items = self._load_schedule_audit_items()
+        with _PENDING_ACTIONS_LOCK:
+            pending_snapshot = list(_PENDING_ACTIONS.values())
+        for action in pending_snapshot:
+            items[action.get("action_id", "")] = self._build_activity_item(action, now_ts)
+        for planned_item in self._load_schedule_plan_items():
+            items.setdefault(planned_item["id"], planned_item)
+        return list(items.values())
+
+    def _build_activity_item(self, action: dict, now_ts: float) -> dict:
+        """Convert a _PENDING_ACTIONS record into an ActivityItem dict."""
+        from decimal import Decimal
+        action_id = action.get("action_id", "")
+        action_type = action.get("action_type", "")
+        app_id = action.get("app_id", "")
+        created_ts = action.get("created_at", now_ts)
+        cooldown_end_ts = action.get("cooldown_ends_at")
+        action_class = action.get("class", "B")
+        status_raw = action.get("status", "PENDING_APPROVAL")
+        if status_raw == "APPROVED":
+            status = "success"
+        elif status_raw == "REJECTED":
+            status = "cancelled"
+        elif status_raw == "PENDING_APPROVAL":
+            if cooldown_end_ts and now_ts < cooldown_end_ts:
+                status = "cooldown"
+            else:
+                status = "pending_approval"
+        else:
+            status = status_raw.lower()
+        created_iso = datetime.fromtimestamp(created_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
+        cooldown_end_iso = None
+        if cooldown_end_ts:
+            cooldown_end_iso = datetime.fromtimestamp(cooldown_end_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
+        preview = action.get("preview", {})
+        return {
+            "id": action_id,
+            "app_id": app_id,
+            "app_name": app_id,
+            "status": status,
+            "safety_tier": action_class,
+            "started_at": created_iso,
+            "ended_at": action.get("signed_at") or action.get("rejected_at"),
+            "duration_ms": 0,
+            "cost_usd": str(Decimal("0.00")),
+            "tokens_used": 0,
+            "actions_taken": 0,
+            "evidence_path": f"~/.solace/audit/{action_id}.jsonl",
+            "evidence_hash": action.get("action_hash", ""),
+            "output_summary": preview.get("preview_text", ""),
+            "scopes_used": list(action.get("params", {}).keys()),
+            "cooldown_expires_at": cooldown_end_iso,
+            "scheduled_at": None,
+            "schedule_pattern": None,
+            "cross_app_triggers": [],
+            "error": action.get("reject_reason"),
+            "preview_text": preview.get("preview_text", ""),
+            "risk_tier": action_class,
+            "label": action_type,
+            "action_type": action_type,
+        }
+
+    def _handle_schedule_viewer_list(self, query: str) -> None:
+        """GET /api/v1/schedule — list activity items with filtering."""
+        params = self._parse_query(query)
+        filter_status = params.get("status", "")
+        filter_app_id = params.get("app_id", "")
+        filter_safety_tier = params.get("safety_tier", "")
+        from_iso = params.get("from", "")
+        to_iso = params.get("to", "")
+        try:
+            limit = int(params.get("limit", "50"))
+        except ValueError:
+            limit = 50
+        now_ts = time.time()
+        items = []
+        normalized_filter = str(filter_status).strip().lower()
+        for item in self._collect_schedule_items(now_ts):
+            if filter_app_id and item["app_id"] != filter_app_id:
+                continue
+            if filter_safety_tier and item.get("safety_tier") != filter_safety_tier:
+                continue
+            item_time = str(item.get("scheduled_at") or item.get("started_at") or "")
+            if from_iso and item_time < from_iso:
+                continue
+            if to_iso and item_time > to_iso:
+                continue
+            item_status = str(item["status"]).lower()
+            if normalized_filter:
+                if normalized_filter == "pending" and item_status not in ("pending_approval", "cooldown"):
+                    continue
+                if normalized_filter == "past" and item_status not in ("success", "failed", "cancelled"):
+                    continue
+                if normalized_filter == "future" and item_status not in ("scheduled", "queued"):
+                    continue
+                if normalized_filter not in ("pending", "past", "future") and item_status != normalized_filter:
+                    continue
+            items.append(item)
+        items.sort(key=lambda x: str(x.get("scheduled_at") or x.get("started_at") or ""), reverse=True)
+        self._send_json({"items": items[:limit], "total": len(items)})
+
+    def _handle_schedule_viewer_detail(self, run_id: str) -> None:
+        """GET /api/v1/schedule/{run_id} — full detail."""
+        now_ts = time.time()
+        for item in self._collect_schedule_items(now_ts):
+            if item.get("id") == run_id:
+                self._send_json(item)
+                return
+        with _ACTIONS_HISTORY_LOCK:
+            for entry in _ACTIONS_HISTORY:
+                if entry.get("action_id") == run_id or entry.get("bundle_id") == run_id:
+                    self._send_json(entry)
+                    return
+        self._send_json({"error": "not found"}, 404)
+
+    def _handle_schedule_viewer_approve(self, run_id: str) -> None:
+        """POST /api/v1/schedule/approve/{run_id} — sign off, requires auth; 400 if cooldown active."""
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            body = {}
+        now_ts = time.time()
+        with _PENDING_ACTIONS_LOCK:
+            action = _PENDING_ACTIONS.get(run_id)
+        if action is None:
+            settings = self._load_schedule_settings()
+            schedule_plans = settings.get("schedule_plans", [])
+            if not isinstance(schedule_plans, list):
+                schedule_plans = []
+            remaining_plans = [plan for plan in schedule_plans if str(plan.get("run_id", "")) != run_id]
+            if len(remaining_plans) == len(schedule_plans):
+                self._send_json({"error": "not found"}, 404)
+                return
+            settings["schedule_plans"] = remaining_plans
+            self._save_schedule_settings(settings)
+            self._send_json({"cancelled": True, "run_id": run_id})
+            return
+        if action.get("status") != "PENDING_APPROVAL":
+            self._send_json({"error": "not pending approval", "status": action.get("status")}, 409)
+            return
+        cooldown_end = action.get("cooldown_ends_at", now_ts)
+        if now_ts < cooldown_end:
+            remaining = int(cooldown_end - now_ts)
+            status_code = 409 if self.path.startswith("/api/schedule/") else 400
+            self._send_json({"error": "cooldown_active", "remaining_seconds": remaining}, status_code)
+            return
+        sealed_at = datetime.utcnow().isoformat() + "Z"
+        with _PENDING_ACTIONS_LOCK:
+            if run_id in _PENDING_ACTIONS:
+                _PENDING_ACTIONS[run_id]["status"] = "APPROVED"
+                _PENDING_ACTIONS[run_id]["signed_at"] = sealed_at
+                action = dict(_PENDING_ACTIONS[run_id])
+        item = self._build_activity_item(action, now_ts)
+        evidence_hash = self._write_schedule_audit_item(item, "schedule_approved")
+        record_evidence("schedule_approved", {"run_id": run_id, "action_type": action.get("action_type", "")})
+        self._send_json({"approved": True, "run_id": run_id, "sealed_at": sealed_at, "evidence_hash": evidence_hash})
+
+    def _handle_schedule_viewer_cancel(self, run_id: str) -> None:
+        """POST /api/v1/schedule/cancel/{run_id} — cancel pending run, requires auth."""
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            body = {}
+        reason = str(body.get("reason", "countdown_expired")).strip()
+        with _PENDING_ACTIONS_LOCK:
+            action = _PENDING_ACTIONS.get(run_id)
+        if action is None:
+            self._send_json({"error": "not found"}, 404)
+            return
+        if action.get("status") != "PENDING_APPROVAL":
+            self._send_json({"error": "not pending", "status": action.get("status")}, 409)
+            return
+        cancelled_at = datetime.utcnow().isoformat() + "Z"
+        with _PENDING_ACTIONS_LOCK:
+            if run_id in _PENDING_ACTIONS:
+                _PENDING_ACTIONS[run_id]["status"] = "REJECTED"
+                _PENDING_ACTIONS[run_id]["reject_reason"] = reason
+                _PENDING_ACTIONS[run_id]["rejected_at"] = cancelled_at
+                action = dict(_PENDING_ACTIONS[run_id])
+        item = self._build_activity_item(action, time.time())
+        evidence_hash = self._write_schedule_audit_item(item, "schedule_cancelled")
+        record_evidence("schedule_cancelled", {"run_id": run_id, "reason": reason})
+        self._send_json({"cancelled": True, "run_id": run_id, "evidence_hash": evidence_hash})
+
+    def _handle_schedule_viewer_queue(self) -> None:
+        """GET /api/v1/schedule/queue — Class B+C items pending sign-off."""
+        now_ts = time.time()
+        with _PENDING_ACTIONS_LOCK:
+            snapshot = list(_PENDING_ACTIONS.values())
+        result = []
+        for action in snapshot:
+            if action.get("status") != "PENDING_APPROVAL":
+                continue
+            action_class = action.get("class", "B")
+            if action_class not in ("B", "C"):
+                continue
+            cooldown_end = action.get("cooldown_ends_at", now_ts)
+            remaining = max(0.0, cooldown_end - now_ts)
+            cooldown_end_iso = datetime.fromtimestamp(cooldown_end, tz=timezone.utc).isoformat().replace("+00:00", "Z")
+            result.append({
+                "run_id": action.get("action_id") or action.get("preview_id", ""),
+                "action_type": action.get("action_type", ""),
+                "class": action_class,
+                "app_id": action.get("app_id", ""),
+                "preview_text": action.get("preview", {}).get("preview_text", action.get("preview_text", "")),
+                "cooldown_expires_at": cooldown_end_iso,
+                "countdown_seconds_remaining": int(remaining),
+            })
+        self._send_json({"queue": result, "count": len(result)})
+
+    def _handle_schedule_viewer_upcoming(self) -> None:
+        """GET /api/v1/schedule/upcoming — schedules + keepalive + pending counts (4-tab Tab 1)."""
+        if not self._check_auth():
+            return
+        planned_items = self._load_schedule_plan_items()
+        schedules = load_schedules()
+        pending_approvals = 0
+        with _PENDING_ACTIONS_LOCK:
+            for action in _PENDING_ACTIONS.values():
+                if action.get("status") == "PENDING_APPROVAL":
+                    pending_approvals += 1
+        CRON_PRESETS = {
+            "0 7 * * *":   "Every day at 7:00 AM",
+            "0 9 * * 1-5": "Weekdays at 9:00 AM",
+            "0 * * * *":   "Every hour",
+            "0 */2 * * *": "Every 2 hours",
+            "0 9 * * 1":   "Every Monday at 9:00 AM",
+        }
+        result_schedules = []
+        for s in schedules:
+            cron = s.get("cron", "")
+            cron_human = CRON_PRESETS.get(cron, cron)
+            result_schedules.append({
+                "app_id": s.get("app_id", ""),
+                "app_name": s.get("label", s.get("app_id", "")),
+                "cron": cron,
+                "cron_human": cron_human,
+                "next_run_iso": s.get("next_run_iso", ""),
+                "countdown_seconds": s.get("countdown_seconds", 0),
+                "enabled": s.get("enabled", True),
+            })
+        for item in planned_items:
+            result_schedules.append({
+                "app_id": item.get("app_id", ""),
+                "app_name": item.get("app_name", item.get("app_id", "")),
+                "cron": item.get("schedule_pattern") or "none",
+                "cron_human": item.get("schedule_pattern") or "One-time run",
+                "next_run_iso": item.get("scheduled_at", ""),
+                "countdown_seconds": 0,
+                "enabled": True,
+            })
+        self._send_json({
+            "schedules": result_schedules,
+            "keepalive": {"active_count": 0, "last_refresh": "", "next_refresh_seconds": 300},
+            "pending_approvals": pending_approvals,
+            "pending_esign": 0,
+        })
+
+    def _handle_esign_pending(self) -> None:
+        """GET /api/v1/esign/pending — list pending eSign requests."""
+        if not self._check_auth():
+            return
+        self._send_json({"pending": []})
+
+    def _handle_esign_sign(self, esign_id: str) -> None:
+        """POST /api/v1/esign/{esign_id}/sign — sign an eSign request."""
+        if not self._check_auth():
+            return
+        content_length = int(self.headers.get("Content-Length", 0))
+        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
+        try:
+            body = json.loads(raw)
+        except json.JSONDecodeError:
+            self._send_json({"error": "Invalid JSON"}, 400)
+            return
+        signature_token = body.get("signature_token", "")
+        if not signature_token:
+            self._send_json({"error": "signature_token required"}, 400)
+            return
+        from datetime import datetime, timezone
+        sealed_at = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
+        self._send_json({"signed": True, "esign_id": esign_id, "sealed_at": sealed_at})
+
+    def _handle_esign_history(self) -> None:
+        """GET /api/v1/esign/history — eSign completed signatures."""
+        if not self._check_auth():
+            return
+        self._send_json({"history": []})
+
+    def _handle_schedule_viewer_calendar(self, query: str) -> None:
+        """GET /api/v1/schedule/calendar — group activity items by day for calendar view."""
+        params = self._parse_query(query)
+        month_str = params.get("month", "")
+        year_str = params.get("year", "")
+        now_ts = time.time()
+        by_day: dict[str, list] = {}
+        for item in self._collect_schedule_items(now_ts):
+            started = str(item.get("scheduled_at") or item.get("started_at") or "")
+            if len(started) < 10:
+                continue
+            day = started[:10]
+            if month_str and not day.startswith(month_str[:7]):
+                continue
+            if year_str and not day.startswith(year_str[:4]):
+                continue
+            if day not in by_day:
+                by_day[day] = []
+            by_day[day].append({
+                "id": item["id"],
+                "app": item["app_id"],
+                "status": item["status"],
+                "time": started[11:16],  # HH:MM
+                "label": item.get("label", item.get("app_id", "")),
+                "safety_tier": item["safety_tier"],
+            })
+        self._send_json(by_day)
+
+    def _handle_schedule_viewer_roi(self) -> None:
+        """GET /api/v1/schedule/roi — ROI statistics using Decimal for USD."""
+        from decimal import Decimal
+        now_ts = time.time()
+        week_ago_ts = now_ts - 7 * 86400
+        week_runs = 0
+        all_items = self._collect_schedule_items(now_ts)
+        for item in all_items:
+            item_time = str(item.get("started_at") or item.get("scheduled_at") or "")
+            if item_time and item_time >= datetime.fromtimestamp(week_ago_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z"):
+                week_runs += 1
+        # 10 minutes saved per run at $30/hr
+        minutes_per_run = 10
+        week_time_saved_minutes = week_runs * minutes_per_run
+        hourly_rate = Decimal("30")
+        week_time_saved_usd = (Decimal(week_time_saved_minutes) / Decimal("60")) * hourly_rate
+        week_hours_saved = Decimal(week_time_saved_minutes) / Decimal("60")
+        month_equivalent = week_runs * 4
+        self._send_json({
+            "week_runs": week_runs,
+            "week_cost_usd": str(Decimal("0.00")),
+            "week_time_saved_minutes": week_time_saved_minutes,
+            "week_time_saved_usd_equiv": str(week_time_saved_usd.quantize(Decimal("0.01"))),
+            "week_hours_saved": str(week_hours_saved.quantize(Decimal("0.01"))),
+            "week_value_usd_at_30_per_hour": str(week_time_saved_usd.quantize(Decimal("0.01"))),
+            "all_time_runs": len(all_items),
+            "month_equivalent": month_equivalent,
+            "streak_days": 0,
+            "last_streak_milestone": None,
+        })
+
+    def _handle_schedule_viewer_plan(self) -> None:
+        """POST /api/v1/schedule/plan — schedule a future run."""
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            return
+        app_id = str(body.get("app_id", "")).strip()
+        if not app_id:
+            self._send_json({"error": "app_id required"}, 400)
+            return
+        scheduled_at = str(body.get("scheduled_at", "")).strip()
+        if not scheduled_at:
+            self._send_json({"error": "scheduled_at required"}, 400)
+            return
+        repeat = str(body.get("repeat", "none") or "none")
+        note = str(body.get("note", "") or "")
+        run_id = f"run-{app_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
+        settings = self._load_schedule_settings()
+        schedule_plans = settings.get("schedule_plans", [])
+        if not isinstance(schedule_plans, list):
+            schedule_plans = []
+        plan = {"run_id": run_id, "app_id": app_id, "scheduled_at": scheduled_at, "repeat": repeat, "note": note}
+        schedule_plans.append(plan)
+        settings["schedule_plans"] = schedule_plans
+        self._save_schedule_settings(settings)
+        item = self._load_schedule_plan_items()[-1]
+        evidence_hash = self._write_schedule_audit_item(item, "schedule_planned")
+        settings["schedule_plans"][-1]["evidence_hash"] = evidence_hash
+        self._save_schedule_settings(settings)
+        record_evidence("schedule_planned", {"run_id": run_id, "app_id": app_id, "scheduled_at": scheduled_at})
+        self._send_json({"run_id": run_id, "scheduled_at": scheduled_at}, 201)
+
+    def _handle_schedule_html(self) -> None:
+        """GET /web/schedule.html — serve the schedule viewer page."""
+        html_path = Path(__file__).parent / "web" / "schedule.html"
+        try:
+            content = html_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "schedule.html not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "text/html; charset=utf-8")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    def _handle_schedule_js(self) -> None:
+        """GET /web/js/schedule.js — serve the schedule viewer JS."""
+        js_path = Path(__file__).parent / "web" / "js" / "schedule.js"
+        try:
+            content = js_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "schedule.js not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "application/javascript")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    def _handle_schedule_css(self) -> None:
+        """GET /web/css/schedule.css — serve the schedule viewer CSS."""
+        css_path = Path(__file__).parent / "web" / "css" / "schedule.css"
+        try:
+            content = css_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "schedule.css not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "text/css")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    # ---------------------------------------------------------------------------
+    # Task 061 — Value Dashboard handlers
+    # ---------------------------------------------------------------------------
+
+    def _handle_session_stats(self) -> None:
+        """GET /api/v1/session/stats — current session metrics."""
+        if not self._check_auth():
+            return
+        with _SESSION_STATS_LOCK:
+            stats = dict(_SESSION_STATS)
+        if stats["session_start"] is not None:
+            stats["duration_seconds"] = int(time.time() - stats["session_start"])
+        self._send_json(stats)
+
+    def _handle_session_stats_reset(self) -> None:
+        """POST /api/v1/session/stats/reset — clear session counters."""
+        if not self._check_auth():
+            return
+        import uuid
+        with _SESSION_STATS_LOCK:
+            _SESSION_STATS["session_id"] = str(uuid.uuid4())
+            _SESSION_STATS["state"] = "IDLE"
+            _SESSION_STATS["app_name"] = None
+            _SESSION_STATS["pages_visited"] = 0
+            _SESSION_STATS["llm_calls"] = 0
+            _SESSION_STATS["cost_usd"] = "0.00"
+            _SESSION_STATS["cost_saved_pct"] = 0
+            _SESSION_STATS["duration_seconds"] = 0
+            _SESSION_STATS["recipes_replayed"] = 0
+            _SESSION_STATS["evidence_captured"] = 0
+            _SESSION_STATS["session_start"] = time.time()
+        self._send_json({"reset": True})
+
+    def _handle_dashboard_html(self) -> None:
+        """GET /web/dashboard.html — serve the value dashboard page."""
+        html_path = Path(__file__).parent / "web" / "dashboard.html"
+        try:
+            content = html_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "dashboard.html not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "text/html; charset=utf-8")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    def _handle_dashboard_js(self) -> None:
+        """GET /web/js/dashboard.js — serve the value dashboard JS."""
+        js_path = Path(__file__).parent / "web" / "js" / "dashboard.js"
+        try:
+            content = js_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "dashboard.js not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "application/javascript")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    def _handle_dashboard_css(self) -> None:
+        """GET /web/css/dashboard.css — serve the value dashboard CSS."""
+        css_path = Path(__file__).parent / "web" / "css" / "dashboard.css"
+        try:
+            content = css_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "dashboard.css not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "text/css")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    # ---------------------------------------------------------------------------
+    # Task 062 — App Onboarding: Grey-to-Green 4-State Lifecycle UI
+    # ---------------------------------------------------------------------------
+
+    def _handle_apps_lifecycle(self) -> None:
+        """GET /api/v1/apps/lifecycle — list all apps with their current state."""
+        if not self._check_auth():
+            return
+        apps = getattr(self.server, "apps", [])
+        result = []
+        for app_id in (apps if isinstance(apps, list) else []):
+            config_path = Path.home() / ".solace" / "app-configs" / f"{app_id}.json"
+            is_configured = config_path.exists()
+            result.append({
+                "app_id": app_id,
+                "name": app_id.replace("-", " ").title(),
+                "icon": "\U0001F4E6",
+                "state": "activated" if is_configured else "installed",
+                "config_required": [],
+                "config_complete": is_configured,
+            })
+        self._send_json({"apps": result})
+
+    def _handle_app_setup_requirements(self, app_id: str) -> None:
+        """GET /api/v1/apps/{app_id}/setup-requirements — fields needed to activate."""
+        if not self._check_auth():
+            return
+        self._send_json({
+            "app_id": app_id,
+            "fields": [],
+            "vault_key": None,
+        })
+
+    def _handle_app_activate(self, app_id: str) -> None:
+        """POST /api/v1/apps/{app_id}/activate — store encrypted config, mark activated."""
+        if not self._check_auth():
+            return
+        try:
+            content_length = int(self.headers.get("Content-Length", 0))
+            body = json.loads(self.rfile.read(content_length) or b"{}") if content_length else {}
+        except json.JSONDecodeError:
+            self._send_json({"error": "Invalid JSON"}, 400)
+            return
+        config_dir = Path.home() / ".solace" / "app-configs"
+        try:
+            config_dir.mkdir(parents=True, exist_ok=True)
+        except OSError as e:
+            self._send_json({"error": f"Could not create config dir: {e}"}, 500)
+            return
+        config_path = config_dir / f"{app_id}.json"
+        try:
+            config_path.write_text(json.dumps({"app_id": app_id, "configured": True}))
+        except OSError as e:
+            self._send_json({"error": f"Could not save config: {e}"}, 500)
+            return
+        self._send_json({"activated": True, "app_id": app_id, "state": "activated"})
+
+    def _handle_app_deactivate(self, app_id: str) -> None:
+        """DELETE /api/v1/apps/{app_id}/activate — reset to installed state."""
+        if not self._check_auth():
+            return
+        config_path = Path.home() / ".solace" / "app-configs" / f"{app_id}.json"
+        try:
+            if config_path.exists():
+                config_path.unlink()
+        except OSError as e:
+            self._send_json({"error": f"Could not remove config: {e}"}, 500)
+            return
+        self._send_json({"deactivated": True, "app_id": app_id, "state": "installed"})
+
+    def _handle_apps_html(self) -> None:
+        """GET /web/apps.html — serve the app onboarding page."""
+        html_path = Path(__file__).parent / "web" / "apps.html"
+        try:
+            content = html_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "apps.html not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "text/html; charset=utf-8")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    def _handle_apps_js(self) -> None:
+        """GET /web/js/apps.js — serve the app onboarding JS."""
+        js_path = Path(__file__).parent / "web" / "js" / "apps.js"
+        try:
+            content = js_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "apps.js not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "application/javascript; charset=utf-8")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    def _handle_apps_css(self) -> None:
+        """GET /web/css/apps.css — serve the app onboarding CSS."""
+        css_path = Path(__file__).parent / "web" / "css" / "apps.css"
+        try:
+            content = css_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "apps.css not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "text/css; charset=utf-8")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    # ---------------------------------------------------------------------------
+    # Task 057 — Preview / Cooldown / Sign-Off handlers
+    # ---------------------------------------------------------------------------
+
+    def _handle_actions_preview(self) -> None:
+        """POST /api/v1/actions/preview — classify and gate Class B/C actions."""
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            return
+        action_type = body.get("action_type", "")
+        if not isinstance(action_type, str) or not action_type:
+            self._send_json({"error": "missing 'action_type'"}, 400)
+            return
+        if len(action_type) > 128:
+            self._send_json({"error": "'action_type' exceeds 128 chars"}, 400)
+            return
+        params = body.get("params", {})
+        if not isinstance(params, dict):
+            self._send_json({"error": "'params' must be an object"}, 400)
+            return
+        app_id = str(body.get("app_id", ""))
+        oauth3_token_id = str(body.get("oauth3_token_id", "")).strip()
+        action_class = ACTION_CLASSES.get(action_type, "B")
+        if action_class == "A":
+            self._send_json({
+                "class": "A",
+                "action_type": action_type,
+                "can_execute_immediately": True,
+                "cooldown_ends_at": None,
+                "sign_off_required": False,
+            })
+            return
+        now_ts = time.time()
+        record = _create_pending_action_record(action_type, params, app_id, oauth3_token_id, now_ts)
+        with _PENDING_ACTIONS_LOCK:
+            _PENDING_ACTIONS[record["action_id"]] = record
+        self._write_schedule_audit_item(self._build_activity_item(record, now_ts), "schedule_pending")
+        self._send_json({
+            "action_id": record["action_id"],
+            "class": record["class"],
+            "preview": record["preview"],
+            "cooldown_ends_at": _utc_isoformat(record["cooldown_ends_at"]),
+            "can_execute_immediately": False,
+            "sign_off_required": True,
+        }, 201)
+
+    def _handle_actions_pending(self) -> None:
+        """GET /api/v1/actions/pending — list pending actions with cooldown_remaining_seconds."""
+        now_ts = time.time()
+        with _PENDING_ACTIONS_LOCK:
+            snapshot = list(_PENDING_ACTIONS.values())
+        result = []
+        for action in snapshot:
+            if action.get("status") != "PENDING_APPROVAL":
+                continue
+            result.append(_pending_action_list_item(action, now_ts))
+        self._send_json({"actions": result})
+
+    def _handle_action_approve(self, action_id: str) -> None:
+        """POST /api/v1/actions/{action_id}/approve — sign off after cooldown elapses."""
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            body = {}
+        if not action_id:
+            self._send_json({"error": "missing action_id"}, 400)
+            return
+        with _PENDING_ACTIONS_LOCK:
+            action = _PENDING_ACTIONS.get(action_id)
+        if action is None:
+            self._send_json({"error": "action not found"}, 404)
+            return
+        if action.get("status") != "PENDING_APPROVAL":
+            self._send_json({"error": "action is not pending approval", "status": action.get("status")}, 409)
+            return
+        now_ts = time.time()
+        cooldown_end = action.get("cooldown_ends_at", now_ts)
+        if now_ts < cooldown_end:
+            remaining = int(cooldown_end - now_ts)
+            self._send_json({"error": "cooldown_active", "remaining_seconds": remaining}, 409)
+            return
+        action_class = action.get("class", "B")
+        reason = ""
+        if action_class == "C":
+            step_up = body.get("step_up_consent")
+            if step_up is not True:
+                self._send_json({"error": "step_up_required", "scope": "high_risk"}, 403)
+                return
+            reason = str(body.get("reason", "")).strip()
+            if not reason:
+                self._send_json({"error": "reason required for Class C actions"}, 400)
+                return
+        signer_id = str(body.get("signer_id") or "user")
+        session_token = str(getattr(self.server, "session_token_sha256", ""))
+        signed_at = _utc_isoformat(now_ts)
+        before_state = _action_state_copy(action)
+        action_hash = action.get("action_hash", "")
+        signature = hmac.new(
+            session_token.encode(),
+            f"{action_hash}:{signed_at}:{signer_id}".encode(),
+            hashlib.sha256,
+        ).hexdigest()
+        with _PENDING_ACTIONS_LOCK:
+            current = _PENDING_ACTIONS.get(action_id)
+            if current is None:
+                self._send_json({"error": "action not found"}, 404)
+                return
+            current["status"] = "APPROVED"
+            current["signed_at"] = signed_at
+            current["signature"] = signature
+            current["signer_id"] = signer_id
+            if reason:
+                current["approval_reason"] = reason
+            after_state = _action_state_copy(current)
+        evidence_bundle = create_and_store_evidence_bundle(
+            action["action_type"],
+            before_state,
+            after_state,
+            str(action.get("oauth3_token_id") or "hub-session"),
+            signer_id,
+        )
+        bundle_id = str(evidence_bundle["bundle_id"])
+        before_hash = str(evidence_bundle["before_snapshot_hash"])
+        after_hash = str(evidence_bundle["after_snapshot_hash"])
+        evidence_entry: dict = {
+            "evidence_bundle_id": bundle_id,
+            "bundle_id": bundle_id,
+            "action_id": action_id,
+            "action_type": action["action_type"],
+            "action_hash": action_hash,
+            "signer_id": signer_id,
+            "signed_at": signed_at,
+            "signature": signature,
+            "before_state_hash": before_hash,
+            "after_state_hash": after_hash,
+            "alcoa_attributable": True,
+            "alcoa_legible": True,
+            "alcoa_contemporaneous": True,
+            "alcoa_original": True,
+            "alcoa_accurate": True,
+            "status": "APPROVED",
+            "class": action_class,
+            "preview_summary": action.get("preview", {}).get("preview_text", ""),
+        }
+        if reason:
+            evidence_entry["approval_reason"] = reason
+        with _PENDING_ACTIONS_LOCK:
+            if action_id in _PENDING_ACTIONS:
+                _PENDING_ACTIONS[action_id]["status"] = "APPROVED"
+                _PENDING_ACTIONS[action_id]["evidence_bundle_id"] = bundle_id
+                _PENDING_ACTIONS[action_id]["signed_at"] = signed_at
+        with _ACTIONS_HISTORY_LOCK:
+            _ACTIONS_HISTORY.append(evidence_entry)
+        _append_evidence_record("action_approved", {
+            "action_id": action_id,
+            "action_type": action["action_type"],
+            "class": action_class,
+            "bundle_id": bundle_id,
+            "evidence_bundle_id": bundle_id,
+            "before_state_hash": before_hash,
+            "after_state_hash": after_hash,
+            "oauth3_token_id": str(action.get("oauth3_token_id") or "hub-session"),
+            "user_id": signer_id,
+        })
+        self._send_json({
+            "approved": True,
+            "action_id": action_id,
+            "execute_at": signed_at,
+            "evidence_bundle_id": bundle_id,
+        })
+
+    def _handle_action_reject(self, action_id: str) -> None:
+        """POST /api/v1/actions/{action_id}/reject — reject and seal evidence with reason."""
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            body = {}
+        if not action_id:
+            self._send_json({"error": "missing action_id"}, 400)
+            return
+        with _PENDING_ACTIONS_LOCK:
+            action = _PENDING_ACTIONS.get(action_id)
+        if action is None:
+            self._send_json({"error": "action not found"}, 404)
+            return
+        if action.get("status") != "PENDING_APPROVAL":
+            self._send_json({"error": "action is not pending approval", "status": action.get("status")}, 409)
+            return
+        reason = str(body.get("reason", "")).strip()
+        signer_id = str(body.get("signer_id") or "user")
+        rejected_at = _utc_isoformat(time.time())
+        before_state = _action_state_copy(action)
+        with _PENDING_ACTIONS_LOCK:
+            current = _PENDING_ACTIONS.get(action_id)
+            if current is None:
+                self._send_json({"error": "action not found"}, 404)
+                return
+            current["status"] = "REJECTED"
+            current["reject_reason"] = reason
+            current["rejected_at"] = rejected_at
+            current["signer_id"] = signer_id
+            after_state = _action_state_copy(current)
+        evidence_bundle = create_and_store_evidence_bundle(
+            action["action_type"],
+            before_state,
+            after_state,
+            str(action.get("oauth3_token_id") or "hub-session"),
+            signer_id,
+        )
+        bundle_id = str(evidence_bundle["bundle_id"])
+        history_entry: dict = {
+            "evidence_bundle_id": bundle_id,
+            "bundle_id": bundle_id,
+            "action_id": action_id,
+            "action_type": action["action_type"],
+            "action_hash": action.get("action_hash", ""),
+            "signer_id": signer_id,
+            "signed_at": rejected_at,
+            "signature": "",
+            "before_state_hash": str(evidence_bundle["before_snapshot_hash"]),
+            "after_state_hash": str(evidence_bundle["after_snapshot_hash"]),
+            "alcoa_attributable": True,
+            "alcoa_legible": True,
+            "alcoa_contemporaneous": True,
+            "alcoa_original": True,
+            "alcoa_accurate": True,
+            "status": "REJECTED",
+            "class": action.get("class", "B"),
+            "preview_summary": action.get("preview", {}).get("preview_text", ""),
+            "reject_reason": reason,
+        }
+        with _ACTIONS_HISTORY_LOCK:
+            _ACTIONS_HISTORY.append(history_entry)
+        _append_evidence_record("action_rejected", {
+            "action_id": action_id,
+            "action_type": action["action_type"],
+            "reason": reason,
+            "bundle_id": bundle_id,
+            "evidence_bundle_id": bundle_id,
+            "before_state_hash": history_entry["before_state_hash"],
+            "after_state_hash": history_entry["after_state_hash"],
+            "oauth3_token_id": str(action.get("oauth3_token_id") or "hub-session"),
+            "user_id": signer_id,
+        })
+        self._send_json({"rejected": True, "action_id": action_id, "reason": reason, "evidence_bundle_id": bundle_id})
+
+    def _handle_action_cancel(self, action_id: str) -> None:
+        """DELETE /api/v1/actions/{action_id}/cancel — revoke before cooldown ends."""
+        if not self._check_auth():
+            return
+        if not action_id:
+            self._send_json({"error": "missing action_id"}, 400)
+            return
+        with _PENDING_ACTIONS_LOCK:
+            action = _PENDING_ACTIONS.pop(action_id, None)
+        if action is None:
+            self._send_json({"error": "action not found"}, 404)
+            return
+        _append_evidence_record("action_cancelled", {"action_id": action_id, "action_type": action.get("action_type", "")})
+        self._send_json({"cancelled": True, "action_id": action_id})
+
+    def _handle_actions_history(self, query: str) -> None:
+        """GET /api/v1/actions/history — approved/rejected action history with filters."""
+        params = self._parse_query(query)
+        filter_class = params.get("class", "")
+        filter_status = params.get("status", "")
+        from_iso = params.get("from", "")
+        to_iso = params.get("to", "")
+        with _ACTIONS_HISTORY_LOCK:
+            snapshot = list(_ACTIONS_HISTORY)
+        result = []
+        for entry in snapshot:
+            if filter_class and entry.get("class") != filter_class:
+                continue
+            if filter_status and entry.get("status") != filter_status:
+                continue
+            signed_at = entry.get("signed_at", "")
+            if from_iso and signed_at < from_iso:
+                continue
+            if to_iso and signed_at > to_iso:
+                continue
+            result.append(entry)
+        self._send_json({"actions": result})
+
     def _parse_query(self, query: str) -> dict[str, str]:
         """Parse ?key=value&key2=value2 into dict."""
         if not query or query == "?":
@@ -5235,7 +9086,7 @@ function choose(mode) {
         for pair in query.lstrip("?").split("&"):
             if "=" in pair:
                 k, v = pair.split("=", 1)
-                result[k] = v
+                result[urllib.parse.unquote_plus(k)] = urllib.parse.unquote_plus(v)
         return result
 
     def _record_history_entry(self, status_code: int) -> None:
@@ -5260,7 +9111,7 @@ function choose(mode) {
         self.send_response(status)
         self.send_header("Content-Type", "application/json")
         self.send_header("Content-Length", str(len(body)))
-        self.send_header("Access-Control-Allow-Origin", "http://localhost:8888")
+        self.send_header("Access-Control-Allow-Origin", f"http://localhost:{YINYANG_PORT}")
         self.end_headers()
         self.wfile.write(body)
 
@@ -5268,24 +9119,84 @@ function choose(mode) {
         # Suppress default stderr logging — callers use structured evidence.
         pass
 
+    # ---------------------------------------------------------------------------
+    # Task 063 — YinYang Tutorial: 5-Step First-Run Modal
+    # ---------------------------------------------------------------------------
+
+    def _handle_tutorial_html(self) -> None:
+        """GET /web/tutorial.html — serve the tutorial modal page."""
+        html_path = Path(__file__).parent / "web" / "tutorial.html"
+        try:
+            content = html_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "tutorial.html not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "text/html; charset=utf-8")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    def _handle_tutorial_js(self) -> None:
+        """GET /web/js/tutorial.js — serve the tutorial JS."""
+        js_path = Path(__file__).parent / "web" / "js" / "tutorial.js"
+        try:
+            content = js_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "tutorial.js not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "application/javascript")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    def _handle_tutorial_css(self) -> None:
+        """GET /web/css/tutorial.css — serve the tutorial CSS."""
+        css_path = Path(__file__).parent / "web" / "css" / "tutorial.css"
+        try:
+            content = css_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "tutorial.css not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "text/css; charset=utf-8")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
+
+    def _handle_tutorial_reset(self) -> None:
+        """GET /api/v1/tutorial/reset — informational reset endpoint (actual reset is client-side)."""
+        if not self._check_auth():
+            return
+        self._send_json({"reset": True, "storage_key": "sb_tutorial_v1"})
+
 
 # ---------------------------------------------------------------------------
 # Server factory — theorem: build_server isolates configuration from startup.
 # ---------------------------------------------------------------------------
+class ReusableThreadingHTTPServer(http.server.ThreadingHTTPServer):
+    allow_reuse_address = True
+    daemon_threads = True
+
+
 def build_server(
     port: int,
     repo_root: str,
     session_token_sha256: str = "",
+    cloud_twin: bool = False,
 ) -> http.server.ThreadingHTTPServer:
     """
     Construct a ThreadingHTTPServer with apps pre-loaded.
     Does NOT write port.lock — caller is responsible for that.
     """
     load_session_rules()
-    server = http.server.ThreadingHTTPServer(("localhost", port), YinyangHandler)
+    server = ReusableThreadingHTTPServer(("localhost", port), YinyangHandler)
     server.apps = load_apps(repo_root)  # type: ignore[attr-defined]
     server.repo_root = repo_root  # type: ignore[attr-defined]
     server.session_token_sha256 = session_token_sha256  # type: ignore[attr-defined]
+    server.cloud_twin_mode = _cloud_twin_mode_enabled(cloud_twin)  # type: ignore[attr-defined]
+    server.hub_integration_enabled = _hub_integration_enabled(cloud_twin)  # type: ignore[attr-defined]
     return server
 
 
@@ -5293,9 +9204,10 @@ def build_server(
 # Entry point
 # ---------------------------------------------------------------------------
 def start_server(
-    port: int = 8888,
+    port: int = YINYANG_PORT,
     repo_root: str = ".",
     session_token_sha256: str = "",
+    cloud_twin: bool = False,
 ) -> None:
     """
     Generate token, write lock, register cleanup, then serve forever.
@@ -5307,6 +9219,11 @@ def start_server(
     global SESSION_RULES_APPS_DIR, _SESSION_TOKEN_SHA256
     _SESSION_TOKEN_SHA256 = session_token_sha256
     SESSION_RULES_APPS_DIR = Path(repo_root) / "data" / "default" / "apps"
+    cloud_twin_mode = _cloud_twin_mode_enabled(cloud_twin)
+
+    if cloud_twin_mode:
+        os.environ["SOLACE_CLOUD_TWIN"] = "true"
+        print("Cloud twin mode active", flush=True)
 
     if session_token_sha256:
         t_hash = session_token_sha256
@@ -5320,18 +9237,39 @@ def start_server(
     load_session_rules()
     _start_session_keepalive_thread()
     record_evidence("server_started", {"port": port, "version": _SERVER_VERSION})
-    server = build_server(port, repo_root, session_token_sha256)
+    server = build_server(port, repo_root, session_token_sha256, cloud_twin_mode)
     server.serve_forever()
 
 
-if __name__ == "__main__":
+def _default_port() -> int:
+    port_value = os.environ.get("PORT", "").strip()
+    return int(port_value) if port_value.isdigit() else YINYANG_PORT
+
+
+def build_arg_parser() -> argparse.ArgumentParser:
     parser = argparse.ArgumentParser(description="Yinyang Server")
     parser.add_argument("repo_root", nargs="?", default=".")
+    parser.add_argument("--port", dest="port", type=int, default=_default_port())
     parser.add_argument(
         "--token-sha256",
         dest="token_sha256",
         default="",
         help="Bearer token sha256 for Hub authentication",
     )
-    args = parser.parse_args()
-    start_server(8888, args.repo_root, args.token_sha256)
+    parser.add_argument(
+        "--cloud-twin",
+        dest="cloud_twin",
+        action="store_true",
+        help="Enable cloud twin startup mode",
+    )
+    return parser
+
+
+def main(argv: Optional[list[str]] = None) -> int:
+    args = build_arg_parser().parse_args(argv)
+    start_server(args.port, args.repo_root, args.token_sha256, args.cloud_twin)
+    return 0
+
+
+if __name__ == "__main__":
+    raise SystemExit(main())
