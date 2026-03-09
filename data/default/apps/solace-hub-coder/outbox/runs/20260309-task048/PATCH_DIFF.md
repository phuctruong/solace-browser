diff --git a/yinyang_server.py b/yinyang_server.py
index b2b0dd0f..75cdce77 100644
--- a/yinyang_server.py
+++ b/yinyang_server.py
@@ -20,6 +20,10 @@ Route table:
   GET  /api/v1/evidence/verify         → verify sha256 chain integrity
   GET  /api/v1/evidence/{id}           → single evidence entry detail
   POST /api/v1/evidence                → record evidence event
+  GET  /api/v1/session-rules           → list loaded session rule schemas (requires auth)
+  GET  /api/v1/session-rules/status    → list cached session statuses (requires auth)
+  POST /api/v1/session-rules/check/{app} → trigger one session check (requires auth)
+  POST /api/v1/session-rules/reload    → reload session rule YAML files (requires auth)
   GET  /api/v1/browser/schedules       → list schedules
   GET  /api/v1/browser/schedules/next-runs → preview next run timestamps per schedule
   POST /api/v1/browser/schedules       → create schedule
@@ -62,6 +66,7 @@ Route table:
   GET  /api/v1/logs/errors             → only 4xx/5xx entries from request history
 """
 import argparse
+import asyncio
 import atexit
 import base64
 import hashlib
@@ -76,11 +81,17 @@ import struct
 import subprocess
 import threading
 import time
+import urllib.error
 import urllib.parse
+import urllib.request
 import uuid
 from pathlib import Path
 from typing import Optional
 
+import yaml
+
+from hub_tunnel_client import HubTunnelClient, SOLACEAGI_RELAY_URL
+
 # ---------------------------------------------------------------------------
 # Constants
 # ---------------------------------------------------------------------------
@@ -89,7 +100,10 @@ EVIDENCE_PATH: Path = Path.home() / ".solace" / "evidence.jsonl"
 SCHEDULES_PATH: Path = Path.home() / ".solace" / "schedules.json"
 OAUTH3_TOKENS_PATH: Path = Path.home() / ".solace" / "oauth3-tokens.json"
 ONBOARDING_PATH: Path = Path.home() / ".solace" / "onboarding.json"
+SETTINGS_PATH: Path = Path.home() / ".solace" / "settings.json"
+MARKETPLACE_CACHE_PATH: Path = Path.home() / ".solace" / "marketplace-cache.json"
 RECIPES_DIR: Path = Path(__file__).parent / "data" / "default" / "recipes"
+SESSION_RULES_APPS_DIR: Path = Path(__file__).parent / "data" / "default" / "apps"
 RECIPE_RUNS_PATH: Path = Path.home() / ".solace" / "recipe_runs.json"
 BUDGET_PATH: Path = Path.home() / ".solace" / "budget.json"
 BYOK_PATH: Path = Path.home() / ".solace" / "byok_keys.json"
@@ -101,6 +115,12 @@ DEFAULT_BUDGET: dict = {
     "alert_threshold": 0.80,
     "pause_on_exceeded": True,
 }
+DEFAULT_CLOUD_TWIN_SETTINGS: dict = {
+    "url": "",
+    "enabled": False,
+    "prefer_cloud": False,
+    "fallback_to_local": True,
+}
 
 _SERVER_VERSION = "1.1"
 YINYANG_PORT = 8888
@@ -132,6 +152,7 @@ FAVORITES_PATH: Path = Path.home() / ".solace" / "favorites.json"
 _FAVORITES_LOCK = threading.Lock()
 SUPPORTED_CLI_TOOLS: frozenset = frozenset(["claude", "openai", "ollama", "aider", "continue"])
 _CLI_LOCK = threading.Lock()
+_MARKETPLACE_LOCK = threading.Lock()
 _COMMUNITY_RECIPES: list = [
     {"id": "r001", "name": "Gmail Unsubscribe", "tag": "email", "author": "solace", "version": "1.0", "rating": 4.8, "installs": 1240},
     {"id": "r002", "name": "LinkedIn Auto-Connect", "tag": "social", "author": "community", "version": "1.2", "rating": 4.5, "installs": 890},
@@ -142,10 +163,21 @@ _COMMUNITY_RECIPES: list = [
 _SESSIONS: dict[str, dict] = {}
 _SESSIONS_LOCK = threading.Lock()
 _SESSION_TOKEN_SHA256: str = ""
+_SESSION_RULES: list[dict] = []
+_SESSION_RULES_LOCK = threading.Lock()
+_SESSION_STATUS: dict[str, dict] = {}
+_SESSION_STATUS_LOCK = threading.Lock()
+_SESSION_KEEPALIVE_THREAD: threading.Thread | None = None
+_SESSION_KEEPALIVE_STOP = threading.Event()
 
 _TUNNEL_PROC: Optional[subprocess.Popen] = None
 _TUNNEL_LOCK = threading.Lock()
 _TUNNEL_URL: str = ""
+_CLOUD_TUNNEL_THREAD: threading.Thread | None = None
+_CLOUD_TUNNEL_CLIENT: Optional[HubTunnelClient] = None
+_CLOUD_TUNNEL_ACTIVE: bool = False
+_CLOUD_TUNNEL_LOOP: Optional[asyncio.AbstractEventLoop] = None
+_CLOUD_TUNNEL_LOCK = threading.Lock()
 
 # ---------------------------------------------------------------------------
 # Broadcast log — Task 043
@@ -186,7 +218,29 @@ VAULT_PATH = Path.home() / ".solace" / "oauth3_tokens.json"
 VAULT_EXPORT_PATH = Path.home() / ".solace" / "vault_export.json"
 _SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
 _CRON_RE = re.compile(r"^\S+\s+\S+\s+\S+\s+\S+\s+\S+$")
+_APP_ID_RE = re.compile(r"^[A-Za-z0-9-]+$")
 _ONBOARDING_MODES = frozenset(["agent", "byok", "paid", "cli"])
+_MARKETPLACE_CATEGORIES: tuple[str, ...] = (
+    "productivity",
+    "messaging",
+    "social",
+    "finance",
+    "developer",
+    "solace",
+)
+_MARKETPLACE_TIER_RANKS: dict[str, int] = {
+    "free": 0,
+    "starter": 1,
+    "pro": 2,
+    "team": 3,
+    "enterprise": 4,
+}
+MARKETPLACE_CATALOG_URL = "https://solaceagi.com/api/v1/store/apps"
+MARKETPLACE_APP_RULES_URL_TEMPLATE = "https://solaceagi.com/api/v1/store/apps/{app_id}/session-rules.yaml"
+MARKETPLACE_UPGRADE_URL = "https://solaceagi.com/upgrade"
+MARKETPLACE_CACHE_TTL_SECONDS = 3600
+MARKETPLACE_TIMEOUT_SECONDS = 5
+_marketplace_urlopen = urllib.request.urlopen
 ALLOWED_SCOPES = frozenset([
     "browse", "run_recipe", "read_evidence", "write_evidence",
     "create_schedule", "delete_schedule", "cli_run", "detect_apps"
@@ -270,6 +324,206 @@ def record_evidence(event_type: str, data: dict) -> dict:
     return record
 
 
+def _load_cloud_api_key() -> str:
+    try:
+        settings = json.loads(SETTINGS_PATH.read_text())
+    except FileNotFoundError:
+        return ""
+    except json.JSONDecodeError:
+        return ""
+    except OSError:
+        return ""
+    if not isinstance(settings, dict):
+        return ""
+    account = settings.get("account", {})
+    if not isinstance(account, dict):
+        return ""
+    api_key = account.get("api_key", "")
+    return api_key if isinstance(api_key, str) else ""
+
+
+def _normalized_cloud_twin_settings(raw_value: object) -> dict:
+    settings = dict(DEFAULT_CLOUD_TWIN_SETTINGS)
+    if not isinstance(raw_value, dict):
+        return settings
+    url = raw_value.get("url", "")
+    enabled = raw_value.get("enabled", settings["enabled"])
+    prefer_cloud = raw_value.get("prefer_cloud", settings["prefer_cloud"])
+    fallback_to_local = raw_value.get("fallback_to_local", settings["fallback_to_local"])
+    settings["url"] = url if isinstance(url, str) else ""
+    settings["enabled"] = enabled if isinstance(enabled, bool) else DEFAULT_CLOUD_TWIN_SETTINGS["enabled"]
+    settings["prefer_cloud"] = prefer_cloud if isinstance(prefer_cloud, bool) else DEFAULT_CLOUD_TWIN_SETTINGS["prefer_cloud"]
+    settings["fallback_to_local"] = (
+        fallback_to_local
+        if isinstance(fallback_to_local, bool)
+        else DEFAULT_CLOUD_TWIN_SETTINGS["fallback_to_local"]
+    )
+    return settings
+
+
+def _load_settings() -> dict:
+    try:
+        settings = json.loads(SETTINGS_PATH.read_text())
+    except FileNotFoundError:
+        settings = {}
+    except json.JSONDecodeError:
+        settings = {}
+    except OSError:
+        settings = {}
+    if not isinstance(settings, dict):
+        settings = {}
+    merged = dict(settings)
+    merged["cloud_twin"] = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
+    return merged
+
+
+def _save_settings(settings: dict) -> None:
+    persisted = dict(settings)
+    persisted["cloud_twin"] = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
+    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
+    SETTINGS_PATH.write_text(json.dumps(persisted, indent=2))
+
+
+def _normalize_cloud_twin_url(url: str) -> str:
+    candidate = url.strip()
+    if not candidate:
+        raise ValueError("cloud twin url is required")
+    parsed = urllib.parse.urlparse(candidate)
+    if parsed.scheme not in ("http", "https"):
+        raise ValueError("cloud twin url must start with http:// or https://")
+    if not parsed.hostname:
+        raise ValueError("cloud twin url must include a hostname")
+    if parsed.username or parsed.password:
+        raise ValueError("cloud twin url must not include embedded credentials")
+    if parsed.query or parsed.fragment:
+        raise ValueError("cloud twin url must not include query or fragment")
+    clean_path = parsed.path.rstrip("/")
+    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, clean_path, "", "", ""))
+
+
+def _ping_cloud_twin(url: str, timeout: float = 5.0) -> dict:
+    if not url:
+        return {"reachable": False, "latency_ms": None}
+    started = time.perf_counter()
+    request = urllib.request.Request(f"{url}/health", method="GET")
+    try:
+        with urllib.request.urlopen(request, timeout=timeout) as response:
+            response.read(64 * 1024)
+    except urllib.error.URLError:
+        return {"reachable": False, "latency_ms": None}
+    except OSError:
+        return {"reachable": False, "latency_ms": None}
+    latency_ms = int((time.perf_counter() - started) * 1000)
+    return {"reachable": True, "latency_ms": latency_ms}
+
+
+def _cloud_twin_status_payload() -> dict:
+    settings = _load_settings()
+    cloud_twin = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
+    url = cloud_twin["url"]
+    ping = _ping_cloud_twin(url) if url else {"reachable": False, "latency_ms": None}
+    return {
+        "configured": bool(url),
+        "url": url,
+        "reachable": ping["reachable"],
+        "last_ping_ms": ping["latency_ms"],
+    }
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
+            response_body = response.read().decode()
+            data = json.loads(response_body)
+            latency_ms = int((time.perf_counter() - started) * 1000)
+            return {
+                "ok": True,
+                "status": response.status,
+                "data": data if isinstance(data, dict) else {},
+                "latency_ms": latency_ms,
+            }
+    except urllib.error.HTTPError as exc:
+        try:
+            error_data = json.loads(exc.read().decode())
+        except json.JSONDecodeError:
+            error_data = {"error": f"cloud twin returned HTTP {exc.code}"}
+        return {"ok": False, "status": exc.code, "data": error_data, "latency_ms": None}
+    except urllib.error.URLError:
+        return {"ok": False, "status": 503, "data": {"error": "cloud twin unreachable"}, "latency_ms": None}
+    except json.JSONDecodeError:
+        return {"ok": False, "status": 502, "data": {"error": "cloud twin returned invalid JSON"}, "latency_ms": None}
+    except OSError:
+        return {"ok": False, "status": 503, "data": {"error": "cloud twin unreachable"}, "latency_ms": None}
+
+
+def _cloud_tunnel_worker(api_key: str, yinyang_bearer: str, yinyang_port: int) -> None:
+    global _CLOUD_TUNNEL_ACTIVE, _CLOUD_TUNNEL_CLIENT, _CLOUD_TUNNEL_LOOP
+    loop = asyncio.new_event_loop()
+    client = HubTunnelClient(api_key, yinyang_bearer, yinyang_port=yinyang_port)
+    with _CLOUD_TUNNEL_LOCK:
+        _CLOUD_TUNNEL_CLIENT = client
+        _CLOUD_TUNNEL_LOOP = loop
+        _CLOUD_TUNNEL_ACTIVE = True
+    asyncio.set_event_loop(loop)
+    try:
+        loop.run_until_complete(client.run())
+    finally:
+        with _CLOUD_TUNNEL_LOCK:
+            _CLOUD_TUNNEL_ACTIVE = False
+            _CLOUD_TUNNEL_LOOP = None
+        loop.close()
+
+
+def _launch_cloud_tunnel(api_key: str, yinyang_bearer: str, yinyang_port: int) -> None:
+    global _CLOUD_TUNNEL_ACTIVE, _CLOUD_TUNNEL_THREAD
+    with _CLOUD_TUNNEL_LOCK:
+        if _CLOUD_TUNNEL_THREAD is not None and _CLOUD_TUNNEL_THREAD.is_alive() and _CLOUD_TUNNEL_ACTIVE:
+            return
+        _CLOUD_TUNNEL_ACTIVE = True
+        _CLOUD_TUNNEL_THREAD = threading.Thread(
+            target=_cloud_tunnel_worker,
+            args=(api_key, yinyang_bearer, yinyang_port),
+            daemon=True,
+        )
+        thread = _CLOUD_TUNNEL_THREAD
+    thread.start()
+
+
+def _stop_cloud_tunnel() -> None:
+    global _CLOUD_TUNNEL_ACTIVE, _CLOUD_TUNNEL_CLIENT, _CLOUD_TUNNEL_LOOP, _CLOUD_TUNNEL_THREAD
+    with _CLOUD_TUNNEL_LOCK:
+        client = _CLOUD_TUNNEL_CLIENT
+        loop = _CLOUD_TUNNEL_LOOP
+        thread = _CLOUD_TUNNEL_THREAD
+        _CLOUD_TUNNEL_ACTIVE = False
+    if client is not None and loop is not None and loop.is_running():
+        asyncio.run_coroutine_threadsafe(client.stop(), loop)
+    if thread is not None and thread.is_alive():
+        thread.join(timeout=2)
+    with _CLOUD_TUNNEL_LOCK:
+        _CLOUD_TUNNEL_THREAD = None
+        _CLOUD_TUNNEL_LOOP = None
+
+
+def _cloud_tunnel_status_payload() -> dict:
+    with _CLOUD_TUNNEL_LOCK:
+        retries = _CLOUD_TUNNEL_CLIENT.retries if _CLOUD_TUNNEL_CLIENT is not None else 0
+        active = _CLOUD_TUNNEL_ACTIVE
+    return {
+        "active": active,
+        "relay": SOLACEAGI_RELAY_URL if active else None,
+        "retries": retries,
+    }
+
+
 def load_evidence(limit: int = 50, offset: int = 0) -> list[dict]:
     """Load evidence records from JSONL file. Returns list in reverse-chronological order."""
     try:
@@ -485,6 +739,154 @@ def load_apps(repo_root: str) -> list[str]:
     return []
 
 
+def _session_rule_paths() -> list[Path]:
+    """Return sorted session-rules.yaml paths from the configured app directory."""
+    if not SESSION_RULES_APPS_DIR.is_dir():
+        return []
+    return sorted(SESSION_RULES_APPS_DIR.glob("*/session-rules.yaml"))
+
+
+def _session_interval_seconds(rule: dict) -> int:
+    """Return keep-alive interval in seconds, defaulting to 15 minutes."""
+    keep_alive = rule.get("keep_alive", {})
+    interval_minutes = keep_alive.get("interval_minutes", 15)
+    if not isinstance(interval_minutes, int) or interval_minutes < 1:
+        return 15 * 60
+    return interval_minutes * 60
+
+
+def load_session_rules() -> list[dict]:
+    """Load session rule YAML files and refresh the in-memory cache."""
+    global _SESSION_RULES, _SESSION_STATUS
+
+    loaded_rules: list[dict] = []
+    for rule_path in _session_rule_paths():
+        try:
+            raw_rule = yaml.safe_load(rule_path.read_text())
+        except FileNotFoundError:
+            continue
+        except OSError:
+            continue
+        except yaml.YAMLError:
+            continue
+        if not isinstance(raw_rule, dict):
+            continue
+        app_id = raw_rule.get("app", "")
+        if not isinstance(app_id, str) or not app_id:
+            continue
+        loaded_rules.append(raw_rule)
+
+    loaded_rules.sort(key=lambda rule: str(rule.get("app", "")))
+    with _SESSION_RULES_LOCK:
+        _SESSION_RULES = loaded_rules
+
+    now = int(time.time())
+    with _SESSION_STATUS_LOCK:
+        previous_status = dict(_SESSION_STATUS)
+        refreshed_status: dict[str, dict] = {}
+        for rule in loaded_rules:
+            app_id = str(rule.get("app", ""))
+            previous_entry = previous_status.get(app_id, {})
+            next_check = previous_entry.get("next_check")
+            if not isinstance(next_check, int):
+                next_check = now + _session_interval_seconds(rule)
+            refreshed_status[app_id] = {
+                "app": app_id,
+                "status": previous_entry.get("status", "unknown"),
+                "last_check": previous_entry.get("last_check"),
+                "next_check": next_check,
+            }
+        _SESSION_STATUS = refreshed_status
+
+    return list(loaded_rules)
+
+
+def _get_session_rules_snapshot() -> list[dict]:
+    """Return a shallow copy of loaded session rules."""
+    with _SESSION_RULES_LOCK:
+        return list(_SESSION_RULES)
+
+
+def _find_session_rule(app_id: str) -> Optional[dict]:
+    """Return one loaded session rule by app id."""
+    with _SESSION_RULES_LOCK:
+        for rule in _SESSION_RULES:
+            if rule.get("app") == app_id:
+                return dict(rule)
+    return None
+
+
+def _check_session(rule: dict) -> str:
+    """Return session status without browser automation for this task."""
+    return "unknown"
+
+
+def _record_session_status(rule: dict, status: str, checked_at: int) -> dict:
+    """Update the status cache for one app and return the cached entry."""
+    app_id = str(rule.get("app", ""))
+    entry = {
+        "app": app_id,
+        "status": status,
+        "last_check": checked_at,
+        "next_check": checked_at + _session_interval_seconds(rule),
+    }
+    with _SESSION_STATUS_LOCK:
+        _SESSION_STATUS[app_id] = entry
+    return entry
+
+
+def _run_session_check(rule: dict) -> dict:
+    """Check one session rule, record evidence, and update cached status."""
+    checked_at = int(time.time())
+    status = _check_session(rule)
+    status_entry = _record_session_status(rule, status, checked_at)
+    record_evidence(
+        "session_check",
+        {
+            "app": rule.get("app", ""),
+            "status": status,
+            "check_url": rule.get("check_url", ""),
+        },
+    )
+    return status_entry
+
+
+def time_since_last_check(app_id: str) -> int:
+    """Return seconds since the last check, or a large number if never checked."""
+    with _SESSION_STATUS_LOCK:
+        status_entry = _SESSION_STATUS.get(app_id, {})
+    last_check = status_entry.get("last_check")
+    if not isinstance(last_check, int):
+        return 10**9
+    return max(0, int(time.time()) - last_check)
+
+
+def _session_keepalive_loop() -> None:
+    """Check due session rules on a daemon thread and record evidence."""
+    while not _SESSION_KEEPALIVE_STOP.is_set():
+        for rule in _get_session_rules_snapshot():
+            app_id = str(rule.get("app", ""))
+            if not app_id:
+                continue
+            if time_since_last_check(app_id) >= _session_interval_seconds(rule):
+                _run_session_check(rule)
+        _SESSION_KEEPALIVE_STOP.wait(60)
+
+
+def _start_session_keepalive_thread() -> None:
+    """Start the keep-alive daemon thread once per process."""
+    global _SESSION_KEEPALIVE_THREAD
+    if _SESSION_KEEPALIVE_THREAD is not None and _SESSION_KEEPALIVE_THREAD.is_alive():
+        return
+    _SESSION_KEEPALIVE_STOP.clear()
+    _SESSION_KEEPALIVE_THREAD = threading.Thread(
+        target=_session_keepalive_loop,
+        name="session-keepalive",
+        daemon=True,
+    )
+    _SESSION_KEEPALIVE_THREAD.start()
+
+
 # ---------------------------------------------------------------------------
 # HTTP Handler — theorem: every route returns JSON, every error is specific.
 # ---------------------------------------------------------------------------
@@ -534,6 +936,10 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_evidence_stats()
         elif path == "/api/v1/evidence/export":
             self._handle_evidence_export(query)
+        elif path == "/api/v1/session-rules":
+            self._handle_session_rules_list()
+        elif path == "/api/v1/session-rules/status":
+            self._handle_session_rules_status()
         elif re.match(r"^/api/v1/evidence/[^/]+$", path):
             entry_id = path.split("/")[-1]
             self._handle_evidence_detail(entry_id)
@@ -624,8 +1030,12 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         elif re.match(r"^/api/v1/sessions/[^/]+$", path):
             session_id = path.split("/")[-1]
             self._handle_session_detail(session_id)
+        elif path == "/api/v1/cloud-twin/status":
+            self._handle_cloud_twin_status()
         elif path == "/api/v1/tunnel/status":
             self._handle_tunnel_status()
+        elif path == "/api/v1/tunnel/cloud-status":
+            self._handle_tunnel_cloud_status()
         elif path == "/api/v1/sync/status":
             self._handle_sync_status()
         elif path == "/api/v1/recipes":
@@ -736,6 +1146,11 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_detect()
         elif path == "/api/v1/evidence":
             self._handle_evidence_record()
+        elif path == "/api/v1/session-rules/reload":
+            self._handle_session_rules_reload()
+        elif re.match(r"^/api/v1/session-rules/check/[^/]+$", path):
+            app_id = path.split("/")[-1]
+            self._handle_session_rule_check(app_id)
         elif path == "/api/v1/browser/schedules":
             self._handle_schedule_create()
         elif re.match(r"^/api/v1/browser/schedules/[^/]+/enable$", path):
@@ -757,10 +1172,18 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_onboarding_reset()
         elif path == "/api/v1/sessions":
             self._handle_session_create()
+        elif path == "/api/v1/cloud-twin/set":
+            self._handle_cloud_twin_set()
+        elif path == "/api/v1/cloud-twin/ping":
+            self._handle_cloud_twin_ping()
         elif path == "/api/v1/tunnel/start":
             self._handle_tunnel_start()
+        elif path == "/api/v1/tunnel/start-cloud":
+            self._handle_tunnel_start_cloud()
         elif path == "/api/v1/tunnel/stop":
             self._handle_tunnel_stop()
+        elif path == "/api/v1/tunnel/stop-cloud":
+            self._handle_tunnel_stop_cloud()
         elif path == "/api/v1/sync/export":
             self._handle_sync_export()
         elif path == "/api/v1/sync/import":
@@ -2249,6 +2672,73 @@ function choose(mode) {
             "alive": self._is_session_alive(sess["pid"]),
         })
 
+    def _create_local_session(self, url: str, profile: str) -> tuple[int, dict]:
+        try:
+            pid = self._spawn_browser_session(url, profile)
+        except FileNotFoundError as exc:
+            return 503, {"error": str(exc)}
+        session_id = str(uuid.uuid4())
+        with _SESSIONS_LOCK:
+            _SESSIONS[session_id] = {
+                "url": url,
+                "profile": profile,
+                "pid": pid,
+                "started_at": int(time.time()),
+            }
+        return 201, {"session_id": session_id, "pid": pid, "url": url}
+
+    def _handle_cloud_twin_status(self) -> None:
+        if not self._check_auth():
+            return
+        self._send_json(_cloud_twin_status_payload())
+
+    def _handle_cloud_twin_set(self) -> None:
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            return
+        url = body.get("url", "")
+        if not isinstance(url, str):
+            self._send_json({"error": "url must be a string"}, 400)
+            return
+        try:
+            normalized_url = _normalize_cloud_twin_url(url)
+        except ValueError as exc:
+            self._send_json({"error": str(exc)}, 400)
+            return
+        settings = _load_settings()
+        cloud_twin = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
+        cloud_twin["url"] = normalized_url
+        settings["cloud_twin"] = cloud_twin
+        try:
+            _save_settings(settings)
+        except OSError as exc:
+            self._send_json({"error": f"cannot save settings: {exc}"}, 500)
+            return
+        record_evidence("cloud_twin_set", {"url": normalized_url})
+        self._send_json({"status": "saved", "url": normalized_url})
+
+    def _handle_cloud_twin_ping(self) -> None:
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            return
+        settings = _load_settings()
+        cloud_twin = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
+        result = _ping_cloud_twin(cloud_twin["url"])
+        if cloud_twin["url"]:
+            record_evidence(
+                "cloud_twin_ping",
+                {
+                    "url": cloud_twin["url"],
+                    "reachable": result["reachable"],
+                    "latency_ms": result["latency_ms"],
+                },
+            )
+        self._send_json({"reachable": result["reachable"], "latency_ms": result["latency_ms"]})
+
     def _handle_session_create(self) -> None:
         if not self._check_auth():
             return
@@ -2266,20 +2756,34 @@ function choose(mode) {
         if not re.match(r'^[a-zA-Z0-9-]{1,32}$', profile):
             self._send_json({"error": "profile must be alphanumeric + hyphens, max 32 chars"}, 400)
             return
-        try:
-            pid = self._spawn_browser_session(url, profile)
-        except FileNotFoundError as exc:
-            self._send_json({"error": str(exc)}, 503)
+        target = body.get("target", "local")
+        if target not in ("local", "cloud"):
+            self._send_json({"error": "target must be local or cloud"}, 400)
             return
-        session_id = str(uuid.uuid4())
-        with _SESSIONS_LOCK:
-            _SESSIONS[session_id] = {
-                "url": url,
-                "profile": profile,
-                "pid": pid,
-                "started_at": int(time.time()),
-            }
-        self._send_json({"session_id": session_id, "pid": pid, "url": url}, 201)
+        if target == "cloud":
+            settings = _load_settings()
+            cloud_twin = _normalized_cloud_twin_settings(settings.get("cloud_twin", {}))
+            cloud_twin_url = cloud_twin["url"]
+            if not cloud_twin_url:
+                self._send_json({"error": "cloud twin is not configured"}, 503)
+                return
+            forwarded = _forward_cloud_twin_session(cloud_twin_url, {"url": url, "profile": profile})
+            if forwarded["ok"]:
+                record_evidence(
+                    "cloud_twin_session_forwarded",
+                    {"url": cloud_twin_url, "latency_ms": forwarded["latency_ms"]},
+                )
+                self._send_json(forwarded["data"], forwarded["status"])
+                return
+            if not cloud_twin["fallback_to_local"]:
+                self._send_json(forwarded["data"], forwarded["status"])
+                return
+            record_evidence(
+                "cloud_twin_fallback_local",
+                {"url": cloud_twin_url, "reason": forwarded["data"].get("error", "cloud twin unreachable")},
+            )
+        status, payload = self._create_local_session(url, profile)
+        self._send_json(payload, status)
 
     def _handle_session_delete(self, session_id: str) -> None:
         if not self._check_auth():
@@ -2664,10 +3168,13 @@ function choose(mode) {
             "exported_at": int(time.time()),
             "version": "1.0",
             "budget": self._load_budget_config(),
+            "cloud_twin": dict(DEFAULT_CLOUD_TWIN_SETTINGS),
             "theme": {"theme": "light"},
             "cli_config": {},
             "profiles": [],
         }
+        exported_settings = _load_settings()
+        settings["cloud_twin"] = _normalized_cloud_twin_settings(exported_settings.get("cloud_twin", {}))
         if THEME_PATH.exists():
             try:
                 settings["theme"] = json.loads(THEME_PATH.read_text())
@@ -3374,6 +3881,34 @@ function choose(mode) {
             url = _TUNNEL_URL if active else ""
         self._send_json({"active": active, "url": url, "port": YINYANG_PORT})
 
+    def _handle_tunnel_cloud_status(self) -> None:
+        if not self._check_auth():
+            return
+        self._send_json(_cloud_tunnel_status_payload())
+
+    def _handle_tunnel_start_cloud(self) -> None:
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            return
+        api_key = body.get("api_key", "") if isinstance(body, dict) else ""
+        if not isinstance(api_key, str) or not api_key:
+            api_key = _load_cloud_api_key()
+        if not api_key:
+            self._send_json({"error": "api_key required"}, 400)
+            return
+        _launch_cloud_tunnel(api_key, getattr(self.server, "session_token_sha256", ""), self.server.server_port)
+        record_evidence("cloud_tunnel_start", {"relay": SOLACEAGI_RELAY_URL})
+        self._send_json({"status": "connecting", "relay": SOLACEAGI_RELAY_URL})
+
+    def _handle_tunnel_stop_cloud(self) -> None:
+        if not self._check_auth():
+            return
+        _stop_cloud_tunnel()
+        record_evidence("cloud_tunnel_stop", {"relay": SOLACEAGI_RELAY_URL})
+        self._send_json({"status": "stopped"})
+
     def _handle_tunnel_start(self) -> None:
         if not self._check_auth():
             return
@@ -4019,6 +4554,52 @@ function choose(mode) {
             _REQUEST_COUNTS[f"app_launch:{app_id}"] = _REQUEST_COUNTS.get(f"app_launch:{app_id}", 0) + 1
         self._send_json({"status": "launched", "app_id": app_id, "timestamp": int(time.time())})
 
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
+        """POST /api/v1/session-rules/check/{app} — trigger one session check."""
+        if not self._check_auth():
+            return
+        rule = _find_session_rule(app_id)
+        if rule is None:
+            self._send_json({"error": "session rule not found"}, 404)
+            return
+        status_entry = _run_session_check(rule)
+        self._send_json({
+            "app": app_id,
+            "status": status_entry["status"],
+            "checked_at": status_entry["last_check"],
+        })
+
+    def _handle_session_rules_status(self) -> None:
+        """GET /api/v1/session-rules/status — list cached session statuses."""
+        if not self._check_auth():
+            return
+        with _SESSION_STATUS_LOCK:
+            statuses = [dict(entry) for entry in _SESSION_STATUS.values()]
+        statuses.sort(key=lambda entry: str(entry.get("app", "")))
+        self._send_json({"statuses": statuses})
+
+    def _handle_session_rules_reload(self) -> None:
+        """POST /api/v1/session-rules/reload — refresh in-memory rule cache."""
+        if not self._check_auth():
+            return
+        rules = load_session_rules()
+        self._send_json({"reloaded": True, "total": len(rules)})
+
     def _parse_query(self, query: str) -> dict[str, str]:
         """Parse ?key=value&key2=value2 into dict."""
         if not query or query == "?":
@@ -4073,6 +4654,7 @@ def build_server(
     Construct a ThreadingHTTPServer with apps pre-loaded.
     Does NOT write port.lock — caller is responsible for that.
     """
+    load_session_rules()
     server = http.server.ThreadingHTTPServer(("localhost", port), YinyangHandler)
     server.apps = load_apps(repo_root)  # type: ignore[attr-defined]
     server.repo_root = repo_root  # type: ignore[attr-defined]
@@ -4095,8 +4677,9 @@ def start_server(
     """
     import os
 
-    global _SESSION_TOKEN_SHA256
+    global SESSION_RULES_APPS_DIR, _SESSION_TOKEN_SHA256
     _SESSION_TOKEN_SHA256 = session_token_sha256
+    SESSION_RULES_APPS_DIR = Path(repo_root) / "data" / "default" / "apps"
 
     if session_token_sha256:
         t_hash = session_token_sha256
@@ -4107,6 +4690,8 @@ def start_server(
     write_port_lock(port, t_hash, os.getpid())
     atexit.register(delete_port_lock)
 
+    load_session_rules()
+    _start_session_keepalive_thread()
     record_evidence("server_started", {"port": port, "version": _SERVER_VERSION})
     server = build_server(port, repo_root, session_token_sha256)
     server.serve_forever()
