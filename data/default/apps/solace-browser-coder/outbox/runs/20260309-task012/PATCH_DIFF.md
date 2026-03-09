diff --git a/yinyang_server.py b/yinyang_server.py
index b2b0dd0f..73f075c0 100644
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
@@ -58,10 +62,15 @@ Route table:
   POST /api/v1/byok/set                → {"provider": str, "api_key": str} → store encrypted (requires auth)
   POST /api/v1/byok/test               → {"provider": str} → verify key is configured (requires auth)
   POST /api/v1/byok/clear              → {"provider": str} → remove key (requires auth)
+  GET  /api/v1/marketplace/apps        → marketplace app catalog (requires auth)
+  GET  /api/v1/marketplace/categories  → marketplace categories
+  POST /api/v1/marketplace/install     → install marketplace session rules (requires auth)
+  POST /api/v1/marketplace/uninstall   → uninstall marketplace session rules (requires auth)
   GET  /api/v1/logs/requests           → rolling request history (limit/method/status params)
   GET  /api/v1/logs/errors             → only 4xx/5xx entries from request history
 """
 import argparse
+import asyncio
 import atexit
 import base64
 import hashlib
@@ -76,11 +85,17 @@ import struct
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
@@ -89,7 +104,10 @@ EVIDENCE_PATH: Path = Path.home() / ".solace" / "evidence.jsonl"
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
@@ -101,6 +119,12 @@ DEFAULT_BUDGET: dict = {
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
@@ -132,6 +156,7 @@ FAVORITES_PATH: Path = Path.home() / ".solace" / "favorites.json"
 _FAVORITES_LOCK = threading.Lock()
 SUPPORTED_CLI_TOOLS: frozenset = frozenset(["claude", "openai", "ollama", "aider", "continue"])
 _CLI_LOCK = threading.Lock()
+_MARKETPLACE_LOCK = threading.Lock()
 _COMMUNITY_RECIPES: list = [
     {"id": "r001", "name": "Gmail Unsubscribe", "tag": "email", "author": "solace", "version": "1.0", "rating": 4.8, "installs": 1240},
     {"id": "r002", "name": "LinkedIn Auto-Connect", "tag": "social", "author": "community", "version": "1.2", "rating": 4.5, "installs": 890},
@@ -142,10 +167,21 @@ _COMMUNITY_RECIPES: list = [
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
@@ -186,7 +222,30 @@ VAULT_PATH = Path.home() / ".solace" / "oauth3_tokens.json"
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
+MARKETPLACE_APP_SYNC_URL = "https://solaceagi.com/api/v1/apps/sync"
+MARKETPLACE_CACHE_TTL_SECONDS = 3600
+MARKETPLACE_TIMEOUT_SECONDS = 5
+_marketplace_urlopen = urllib.request.urlopen
 ALLOWED_SCOPES = frozenset([
     "browse", "run_recipe", "read_evidence", "write_evidence",
     "create_schedule", "delete_schedule", "cli_run", "detect_apps"
@@ -270,6 +329,404 @@ def record_evidence(event_type: str, data: dict) -> dict:
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
+def _load_account_tier() -> str:
+    try:
+        settings = json.loads(SETTINGS_PATH.read_text())
+    except FileNotFoundError:
+        return "free"
+    except json.JSONDecodeError:
+        return "free"
+    except OSError:
+        return "free"
+    if not isinstance(settings, dict):
+        return "free"
+    user = settings.get("user", {})
+    if isinstance(user, dict):
+        tier = user.get("tier")
+        if isinstance(tier, str):
+            normalized = tier.strip().lower()
+            if normalized in _MARKETPLACE_TIER_RANKS:
+                return normalized
+    account = settings.get("account", {})
+    if not isinstance(account, dict):
+        return "free"
+    tier = account.get("tier", "free")
+    if not isinstance(tier, str):
+        return "free"
+    normalized = tier.strip().lower()
+    if normalized not in _MARKETPLACE_TIER_RANKS:
+        return "free"
+    return normalized
+
+
+def _load_user_tier_payload() -> dict:
+    tier = _load_account_tier()
+    tier_rank = _MARKETPLACE_TIER_RANKS.get(tier, 0)
+    pro_rank = _MARKETPLACE_TIER_RANKS["pro"]
+    return {
+        "tier": tier,
+        "can_sync": tier_rank >= pro_rank,
+        "can_submit": tier_rank >= pro_rank,
+    }
+
+
+def _marketplace_apps_root(repo_root: str) -> Path:
+    return Path(repo_root) / "data" / "default" / "apps"
+
+
+def _marketplace_app_dir(repo_root: str, app_id: str) -> Path:
+    return _marketplace_apps_root(repo_root) / app_id
+
+
+def _session_rules_path_for_app(repo_root: str, app_id: str) -> Path:
+    return _marketplace_app_dir(repo_root, app_id) / "session-rules.yaml"
+
+
+def _is_marketplace_app_installed(repo_root: str, app_id: str) -> bool:
+    return _session_rules_path_for_app(repo_root, app_id).is_file()
+
+
+def _normalize_marketplace_app(raw_app: dict, repo_root: str) -> Optional[dict]:
+    app_id = raw_app.get("app_id")
+    if not isinstance(app_id, str) or not _APP_ID_RE.fullmatch(app_id):
+        return None
+    display_name = raw_app.get("display_name", app_id.replace("-", " ").title())
+    description = raw_app.get("description", "")
+    category = raw_app.get("category", "solace")
+    tier_required = raw_app.get("tier_required", "free")
+    version = raw_app.get("version", "")
+    icon_url = raw_app.get("icon_url", "")
+    if not isinstance(display_name, str):
+        display_name = app_id.replace("-", " ").title()
+    if not isinstance(description, str):
+        description = ""
+    if not isinstance(category, str) or not category:
+        category = "solace"
+    if not isinstance(tier_required, str):
+        tier_required = "free"
+    normalized_tier = tier_required.strip().lower()
+    if normalized_tier not in _MARKETPLACE_TIER_RANKS:
+        normalized_tier = "free"
+    if not isinstance(version, str):
+        version = ""
+    if not isinstance(icon_url, str):
+        icon_url = ""
+    return {
+        "app_id": app_id,
+        "display_name": display_name,
+        "description": description,
+        "category": category,
+        "tier_required": normalized_tier,
+        "installed": _is_marketplace_app_installed(repo_root, app_id),
+        "version": version,
+        "icon_url": icon_url,
+    }
+
+
+def _normalize_marketplace_apps(raw_apps: list, repo_root: str) -> list[dict]:
+    apps: list[dict] = []
+    for raw_app in raw_apps:
+        if not isinstance(raw_app, dict):
+            continue
+        normalized = _normalize_marketplace_app(raw_app, repo_root)
+        if normalized is not None:
+            apps.append(normalized)
+    return apps
+
+
+def _write_marketplace_cache(raw_apps: list) -> None:
+    payload = {
+        "apps": raw_apps,
+        "total": len(raw_apps),
+        "fetched_at": int(time.time()),
+    }
+    MARKETPLACE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
+    MARKETPLACE_CACHE_PATH.write_text(json.dumps(payload, indent=2))
+
+
+def _load_marketplace_cache(repo_root: str) -> tuple[Optional[list[dict]], str]:
+    if not MARKETPLACE_CACHE_PATH.exists():
+        return None, ""
+    try:
+        payload = json.loads(MARKETPLACE_CACHE_PATH.read_text())
+    except json.JSONDecodeError:
+        return None, ""
+    except OSError:
+        return None, ""
+    if not isinstance(payload, dict):
+        return None, ""
+    raw_apps = payload.get("apps", [])
+    if not isinstance(raw_apps, list):
+        return None, ""
+    fetched_at = payload.get("fetched_at")
+    if not isinstance(fetched_at, (int, float)):
+        try:
+            fetched_at = MARKETPLACE_CACHE_PATH.stat().st_mtime
+        except OSError:
+            fetched_at = 0
+    age_seconds = time.time() - float(fetched_at)
+    source = "cache" if age_seconds <= MARKETPLACE_CACHE_TTL_SECONDS else "stale_cache"
+    return _normalize_marketplace_apps(raw_apps, repo_root), source
+
+
+def _fetch_marketplace_catalog(repo_root: str) -> tuple[Optional[list[dict]], str]:
+    with _MARKETPLACE_LOCK:
+        try:
+            with _marketplace_urlopen(MARKETPLACE_CATALOG_URL, timeout=MARKETPLACE_TIMEOUT_SECONDS) as response:
+                payload = json.loads(response.read().decode())
+        except urllib.error.URLError as exc:
+            record_evidence("marketplace_catalog_fetch_failed", {
+                "url": MARKETPLACE_CATALOG_URL,
+                "reason": str(exc.reason) if hasattr(exc, "reason") else str(exc),
+            })
+            return _load_marketplace_cache(repo_root)
+        except json.JSONDecodeError as exc:
+            record_evidence("marketplace_catalog_fetch_failed", {
+                "url": MARKETPLACE_CATALOG_URL,
+                "reason": str(exc),
+            })
+            return _load_marketplace_cache(repo_root)
+        except OSError as exc:
+            record_evidence("marketplace_catalog_fetch_failed", {
+                "url": MARKETPLACE_CATALOG_URL,
+                "reason": str(exc),
+            })
+            return _load_marketplace_cache(repo_root)
+        raw_apps = payload.get("apps", []) if isinstance(payload, dict) else []
+        if not isinstance(raw_apps, list):
+            raw_apps = []
+        try:
+            _write_marketplace_cache(raw_apps)
+        except OSError as exc:
+            record_evidence("marketplace_cache_write_failed", {
+                "path": str(MARKETPLACE_CACHE_PATH),
+                "reason": str(exc),
+            })
+        return _normalize_marketplace_apps(raw_apps, repo_root), "remote"
+
+
+def _find_marketplace_app(apps: list[dict], app_id: str) -> Optional[dict]:
+    for app in apps:
+        if app.get("app_id") == app_id:
+            return app
+    return None
+
+
+def _tier_allows_install(user_tier: str, tier_required: str) -> bool:
+    return _MARKETPLACE_TIER_RANKS[user_tier] >= _MARKETPLACE_TIER_RANKS[tier_required]
+
+
+def _download_marketplace_session_rules(app_id: str) -> tuple[Optional[str], Optional[int]]:
+    url = MARKETPLACE_APP_RULES_URL_TEMPLATE.format(app_id=app_id)
+    try:
+        with _marketplace_urlopen(url, timeout=MARKETPLACE_TIMEOUT_SECONDS) as response:
+            return response.read().decode(), None
+    except urllib.error.URLError as exc:
+        if getattr(exc, "code", None) == 404:
+            return None, 404
+        raise
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
@@ -485,6 +942,230 @@ def load_apps(repo_root: str) -> list[str]:
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
+def _load_manifest_for_app(app_id: str) -> dict:
+    """Load one app manifest from the default apps directory."""
+    manifest_path = SESSION_RULES_APPS_DIR / app_id / "manifest.yaml"
+    try:
+        raw_manifest = yaml.safe_load(manifest_path.read_text())
+    except FileNotFoundError:
+        return {}
+    except OSError:
+        return {}
+    except yaml.YAMLError:
+        return {}
+    if isinstance(raw_manifest, dict):
+        return raw_manifest
+    return {}
+
+
+def _normalize_domain(value: str) -> str:
+    """Normalize a hostname or URL to a lowercase bare domain."""
+    candidate = value.strip().lower()
+    if not candidate:
+        return ""
+    parsed = urllib.parse.urlparse(candidate if "://" in candidate else f"//{candidate}")
+    host = parsed.netloc or parsed.path
+    host = host.split("/", 1)[0]
+    host = host.split(":", 1)[0]
+    if host.startswith("www."):
+        host = host[4:]
+    return host
+
+
+def _domain_matches(site: str, query_domain: str) -> bool:
+    """Match app site against queried domain."""
+    site_clean = _normalize_domain(site)
+    domain_clean = _normalize_domain(query_domain)
+    if not site_clean or not domain_clean:
+        return False
+    return (
+        site_clean == domain_clean
+        or domain_clean.endswith("." + site_clean)
+        or site_clean.endswith("." + domain_clean)
+    )
+
+
+def _apps_for_domain(query_domain: str) -> list[dict]:
+    """Return domain-matched app metadata from loaded session rules."""
+    matched: list[dict] = []
+    for session_rules in _get_session_rules_snapshot():
+        site = str(session_rules.get("site", "")).strip()
+        if not _domain_matches(site, query_domain):
+            continue
+        app_id = str(session_rules.get("app", "")).strip()
+        if not app_id:
+            continue
+        manifest = _load_manifest_for_app(app_id)
+        category = str(manifest.get("category") or session_rules.get("category") or "").strip().lower()
+        if category != "messaging":
+            continue
+        tier_required = str(manifest.get("tier") or session_rules.get("tier_required") or "unknown")
+        if tier_required == "enterprise":
+            continue
+        display_name = str(
+            manifest.get("name")
+            or session_rules.get("display_name")
+            or app_id.replace("-", " ").title()
+        )
+        matched.append({
+            "app_id": app_id,
+            "display_name": display_name,
+            "installed": False,
+            "tier_required": tier_required,
+            "session_rules": dict(session_rules),
+        })
+    matched.sort(key=lambda entry: str(entry.get("app_id", "")))
+    return matched
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
@@ -534,6 +1215,10 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
@@ -624,8 +1309,12 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
@@ -685,6 +1374,8 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_apps_favorites_get()
         elif path == "/api/v1/apps/tags":
             self._handle_apps_tags()
+        elif path == "/api/v1/apps/by-domain":
+            self._handle_apps_by_domain(query)
         elif path == "/api/v1/broadcast":
             self._handle_broadcast_get()
         elif path == "/api/v1/rate-limit/status":
@@ -715,6 +1406,10 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_store_list(query)
         elif path == "/api/v1/store/installed":
             self._handle_store_installed()
+        elif path == "/api/v1/marketplace/apps":
+            self._handle_marketplace_apps()
+        elif path == "/api/v1/marketplace/categories":
+            self._handle_marketplace_categories()
         elif path == "/api/v1/cli/config":
             self._handle_cli_config_get()
         elif path == "/api/v1/cli/detect":
@@ -736,6 +1431,11 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
@@ -757,10 +1457,18 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
@@ -827,6 +1535,10 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_app_install()
         elif path == "/api/v1/apps/uninstall":
             self._handle_app_uninstall()
+        elif path == "/api/v1/marketplace/install":
+            self._handle_marketplace_install()
+        elif path == "/api/v1/marketplace/uninstall":
+            self._handle_marketplace_uninstall()
         elif re.match(r"^/api/v1/notifications/[^/]+/read$", path):
             notif_id = path.split("/")[-2]
             self._handle_notification_mark_read(notif_id)
@@ -1789,6 +2501,19 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         categories = [{"name": k, "count": v} for k, v in sorted(category_counts.items())]
         self._send_json({"categories": categories, "total": len(categories)})
 
+    def _handle_apps_by_domain(self, query: str) -> None:
+        """GET /api/v1/apps/by-domain?domain=X — list apps matching a browser domain."""
+        if not self._check_auth():
+            return
+        params = self._parse_query(query)
+        requested_domain = urllib.parse.unquote_plus(params.get("domain", "")).strip()
+        normalized_domain = _normalize_domain(requested_domain)
+        if not normalized_domain:
+            self._send_json({"error": "domain required"}, 400)
+            return
+        apps = _apps_for_domain(normalized_domain)
+        self._send_json({"domain": normalized_domain, "apps": apps, "total": len(apps)})
+
     def _handle_server_config(self) -> None:
         """GET /api/v1/server/config — server configuration + feature flags. Task 049."""
         self._send_json({
@@ -2249,6 +2974,73 @@ function choose(mode) {
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
@@ -2266,20 +3058,34 @@ function choose(mode) {
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
@@ -2664,10 +3470,13 @@ function choose(mode) {
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
@@ -3374,6 +4183,34 @@ function choose(mode) {
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
@@ -4019,6 +4856,170 @@ function choose(mode) {
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
+    def _reload_session_rules_cache(self) -> list[dict]:
+        global SESSION_RULES_APPS_DIR
+        repo_root = getattr(self.server, "repo_root", ".")
+        SESSION_RULES_APPS_DIR = _marketplace_apps_root(repo_root)
+        rules = load_session_rules()
+        self.server.apps = load_apps(repo_root)  # type: ignore[attr-defined]
+        return rules
+
+    def _handle_session_rules_reload(self) -> None:
+        """POST /api/v1/session-rules/reload — refresh in-memory rule cache."""
+        if not self._check_auth():
+            return
+        rules = self._reload_session_rules_cache()
+        self._send_json({"reloaded": True, "total": len(rules)})
+
+    def _handle_marketplace_apps(self) -> None:
+        if not self._check_auth():
+            return
+        repo_root = getattr(self.server, "repo_root", ".")
+        apps, source = _fetch_marketplace_catalog(repo_root)
+        if apps is None:
+            self._send_json({"error": "marketplace unavailable"}, 503)
+            return
+        self._send_json({"apps": apps, "total": len(apps), "source": source})
+
+    def _handle_marketplace_categories(self) -> None:
+        self._send_json({"categories": list(_MARKETPLACE_CATEGORIES)})
+
+    def _handle_marketplace_install(self) -> None:
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            return
+        app_id = body.get("app_id")
+        if not isinstance(app_id, str) or not app_id:
+            self._send_json({"error": "app_id required"}, 400)
+            return
+        if not _APP_ID_RE.fullmatch(app_id):
+            self._send_json({"error": "app_id must be alphanumeric + hyphens only"}, 400)
+            return
+        repo_root = getattr(self.server, "repo_root", ".")
+        apps, source = _fetch_marketplace_catalog(repo_root)
+        if apps is None:
+            self._send_json({"error": "marketplace unavailable"}, 503)
+            return
+        app = _find_marketplace_app(apps, app_id)
+        if app is None:
+            self._send_json({"error": "app not found"}, 404)
+            return
+        user_tier = _load_account_tier()
+        tier_required = str(app.get("tier_required", "free"))
+        if not _tier_allows_install(user_tier, tier_required):
+            self._send_json({"error": "upgrade required", "upgrade_url": MARKETPLACE_UPGRADE_URL}, 403)
+            return
+        try:
+            session_rules_text, download_status = _download_marketplace_session_rules(app_id)
+        except urllib.error.URLError as exc:
+            record_evidence("marketplace_install_failed", {
+                "app_id": app_id,
+                "reason": str(exc.reason) if hasattr(exc, "reason") else str(exc),
+            })
+            self._send_json({"error": "marketplace download failed"}, 503)
+            return
+        except OSError as exc:
+            record_evidence("marketplace_install_failed", {"app_id": app_id, "reason": str(exc)})
+            self._send_json({"error": "marketplace download failed"}, 503)
+            return
+        if download_status == 404 or session_rules_text is None:
+            self._send_json({"error": "app not found"}, 404)
+            return
+        app_dir = _marketplace_app_dir(repo_root, app_id)
+        session_rules_path = _session_rules_path_for_app(repo_root, app_id)
+        try:
+            app_dir.mkdir(parents=True, exist_ok=True)
+            session_rules_path.write_text(session_rules_text)
+        except OSError as exc:
+            record_evidence("marketplace_install_failed", {"app_id": app_id, "reason": str(exc)})
+            self._send_json({"error": "install write failed"}, 500)
+            return
+        self._reload_session_rules_cache()
+        record_evidence("marketplace_app_installed", {
+            "app_id": app_id,
+            "source": source,
+            "tier_required": tier_required,
+        })
+        self._send_json({
+            "status": "installed",
+            "app_id": app_id,
+            "path": f"data/default/apps/{app_id}/",
+        })
+
+    def _handle_marketplace_uninstall(self) -> None:
+        if not self._check_auth():
+            return
+        body = self._read_json_body()
+        if body is None:
+            return
+        app_id = body.get("app_id")
+        if not isinstance(app_id, str) or not app_id:
+            self._send_json({"error": "app_id required"}, 400)
+            return
+        if not _APP_ID_RE.fullmatch(app_id):
+            self._send_json({"error": "app_id must be alphanumeric + hyphens only"}, 400)
+            return
+        repo_root = getattr(self.server, "repo_root", ".")
+        app_dir = _marketplace_app_dir(repo_root, app_id)
+        session_rules_path = _session_rules_path_for_app(repo_root, app_id)
+        try:
+            session_rules_path.unlink()
+        except FileNotFoundError:
+            self._send_json({"error": "app not installed"}, 404)
+            return
+        except OSError as exc:
+            record_evidence("marketplace_uninstall_failed", {"app_id": app_id, "reason": str(exc)})
+            self._send_json({"error": "uninstall failed"}, 500)
+            return
+        try:
+            app_dir.rmdir()
+        except OSError:
+            pass
+        self._reload_session_rules_cache()
+        record_evidence("marketplace_app_uninstalled", {"app_id": app_id})
+        self._send_json({"status": "uninstalled", "app_id": app_id})
+
     def _parse_query(self, query: str) -> dict[str, str]:
         """Parse ?key=value&key2=value2 into dict."""
         if not query or query == "?":
@@ -4073,6 +5074,7 @@ def build_server(
     Construct a ThreadingHTTPServer with apps pre-loaded.
     Does NOT write port.lock — caller is responsible for that.
     """
+    load_session_rules()
     server = http.server.ThreadingHTTPServer(("localhost", port), YinyangHandler)
     server.apps = load_apps(repo_root)  # type: ignore[attr-defined]
     server.repo_root = repo_root  # type: ignore[attr-defined]
@@ -4095,8 +5097,9 @@ def start_server(
     """
     import os
 
-    global _SESSION_TOKEN_SHA256
+    global SESSION_RULES_APPS_DIR, _SESSION_TOKEN_SHA256
     _SESSION_TOKEN_SHA256 = session_token_sha256
+    SESSION_RULES_APPS_DIR = Path(repo_root) / "data" / "default" / "apps"
 
     if session_token_sha256:
         t_hash = session_token_sha256
@@ -4107,6 +5110,8 @@ def start_server(
     write_port_lock(port, t_hash, os.getpid())
     atexit.register(delete_port_lock)
 
+    load_session_rules()
+    _start_session_keepalive_thread()
     record_evidence("server_started", {"port": port, "version": _SERVER_VERSION})
     server = build_server(port, repo_root, session_token_sha256)
     server.serve_forever()
diff --git a/data/default/apps/gmail/session-rules.yaml b/data/default/apps/gmail/session-rules.yaml
new file mode 100644
index 00000000..b20983b1
--- /dev/null
+++ b/data/default/apps/gmail/session-rules.yaml
@@ -0,0 +1,18 @@
+app: gmail
+display_name: "Gmail"
+version: "1.0.0"
+login_url: "https://accounts.google.com/signin"
+check_url: "https://mail.google.com/mail/u/0/#inbox"
+success_signals:
+  - "Inbox"
+  - "Compose"
+failure_signals:
+  - "Sign in"
+  - "accounts.google.com/v3/signin"
+keep_alive:
+  interval_minutes: 15
+  action: "navigate"
+  url: "https://mail.google.com/mail/u/0/#inbox"
+oauth3_scope: "gmail.read"
+tier_required: "free"
+evidence_on_check: true
diff --git a/data/default/apps/linkedin-web/session-rules.yaml b/data/default/apps/linkedin-web/session-rules.yaml
new file mode 100644
index 00000000..4e55c405
--- /dev/null
+++ b/data/default/apps/linkedin-web/session-rules.yaml
@@ -0,0 +1,18 @@
+app: linkedin-web
+display_name: "LinkedIn Web"
+version: "1.0.0"
+login_url: "https://www.linkedin.com/login"
+check_url: "https://www.linkedin.com/feed/"
+success_signals:
+  - "Start a post"
+  - "Feed"
+failure_signals:
+  - "Sign in"
+  - "Forgot password"
+keep_alive:
+  interval_minutes: 20
+  action: "navigate"
+  url: "https://www.linkedin.com/feed/"
+oauth3_scope: "linkedin.read"
+tier_required: "free"
+evidence_on_check: true
diff --git a/tests/test_session_rules.py b/tests/test_session_rules.py
new file mode 100644
index 00000000..cd701bcd
--- /dev/null
+++ b/tests/test_session_rules.py
@@ -0,0 +1,150 @@
+"""RED → GREEN proofs for session rules and keep-alive endpoints."""
+
+import json
+import pathlib
+import shutil
+import sys
+
+import pytest
+
+REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
+sys.path.insert(0, str(REPO_ROOT))
+
+import yinyang_server as ys
+
+TEST_PORT = 18888
+VALID_TOKEN = "a" * 64
+BUILTIN_APPS = [
+    "gmail",
+    "whatsapp-web",
+    "slack-web",
+    "telegram-web",
+    "linkedin-web",
+]
+
+
+def _copy_session_rule(app_id: str, destination_root: pathlib.Path) -> None:
+    source = REPO_ROOT / "data" / "default" / "apps" / app_id / "session-rules.yaml"
+    destination = destination_root / app_id / "session-rules.yaml"
+    destination.parent.mkdir(parents=True, exist_ok=True)
+    shutil.copyfile(source, destination)
+
+
+@pytest.fixture(scope="module")
+def session_rules_env(tmp_path_factory):
+    temp_root = tmp_path_factory.mktemp("session-rules")
+    apps_root = temp_root / "data" / "default" / "apps"
+    evidence_path = temp_root / "evidence.jsonl"
+
+    for app_id in BUILTIN_APPS:
+        _copy_session_rule(app_id, apps_root)
+
+    original_apps_dir = ys.SESSION_RULES_APPS_DIR
+    original_evidence = ys.EVIDENCE_PATH
+    original_rules = list(ys._SESSION_RULES)
+    original_status = dict(ys._SESSION_STATUS)
+
+    ys.SESSION_RULES_APPS_DIR = apps_root
+    ys.EVIDENCE_PATH = evidence_path
+    ys._SESSION_RULES = []
+    ys._SESSION_STATUS = {}
+    ys.load_session_rules()
+
+    yield {
+        "apps_root": apps_root,
+        "evidence_path": evidence_path,
+    }
+
+    ys.SESSION_RULES_APPS_DIR = original_apps_dir
+    ys.EVIDENCE_PATH = original_evidence
+    ys._SESSION_RULES = original_rules
+    ys._SESSION_STATUS = original_status
+
+
+def _make_handler(path: str, method: str, auth_header: str | None = None):
+    handler = object.__new__(ys.YinyangHandler)
+    captured: dict = {"status": None, "data": None}
+    headers: dict[str, str] = {}
+    if auth_header is not None:
+        headers["Authorization"] = auth_header
+    handler.headers = headers
+    handler.path = path
+    handler.command = method
+    handler.client_address = ("127.0.0.1", TEST_PORT)
+    handler.server = type("DummyServer", (), {"session_token_sha256": VALID_TOKEN})()
+    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
+    return handler, captured
+
+
+def test_load_session_rules_finds_gmail(session_rules_env):
+    rules = ys.load_session_rules()
+    gmail_rule = next(rule for rule in rules if rule["app"] == "gmail")
+    assert gmail_rule["display_name"] == "Gmail"
+    assert gmail_rule["check_url"] == "https://mail.google.com/mail/u/0/#inbox"
+
+
+def test_load_session_rules_finds_all_5(session_rules_env):
+    rules = ys.load_session_rules()
+    assert len(rules) == 5
+    assert {rule["app"] for rule in rules} == set(BUILTIN_APPS)
+
+
+def test_get_session_rules_requires_auth(session_rules_env):
+    handler, captured = _make_handler("/api/v1/session-rules", "GET")
+    handler._handle_session_rules_list()
+    assert captured["status"] == 401
+    assert captured["data"]["error"] == "unauthorized"
+
+
+def test_get_session_rules_returns_all(session_rules_env):
+    handler, captured = _make_handler(
+        "/api/v1/session-rules",
+        "GET",
+        auth_header=f"Bearer {VALID_TOKEN}",
+    )
+    handler._handle_session_rules_list()
+    assert captured["status"] == 200
+    assert captured["data"]["total"] == 5
+    assert {rule["app"] for rule in captured["data"]["rules"]} == set(BUILTIN_APPS)
+
+
+def test_check_app_returns_status(session_rules_env):
+    handler, captured = _make_handler(
+        "/api/v1/session-rules/check/gmail",
+        "POST",
+        auth_header=f"Bearer {VALID_TOKEN}",
+    )
+    handler._handle_session_rule_check("gmail")
+    assert captured["status"] == 200
+    assert captured["data"]["app"] == "gmail"
+    assert captured["data"]["status"] == "unknown"
+    assert isinstance(captured["data"]["checked_at"], int)
+
+
+def test_session_status_endpoint(session_rules_env):
+    handler, captured = _make_handler(
+        "/api/v1/session-rules/status",
+        "GET",
+        auth_header=f"Bearer {VALID_TOKEN}",
+    )
+    handler._handle_session_rules_status()
+    assert captured["status"] == 200
+    assert {entry["app"] for entry in captured["data"]["statuses"]} == set(BUILTIN_APPS)
+
+
+def test_session_check_records_evidence(session_rules_env):
+    evidence_path = ys.EVIDENCE_PATH
+    before_lines = evidence_path.read_text().splitlines() if evidence_path.exists() else []
+    handler, captured = _make_handler(
+        "/api/v1/session-rules/check/gmail",
+        "POST",
+        auth_header=f"Bearer {VALID_TOKEN}",
+    )
+    handler._handle_session_rule_check("gmail")
+    assert captured["status"] == 200
+    after_lines = evidence_path.read_text().splitlines()
+    assert len(after_lines) == len(before_lines) + 1
+    evidence_record = json.loads(after_lines[-1])
+    assert evidence_record["type"] == "session_check"
+    assert evidence_record["data"]["app"] == "gmail"
+    assert evidence_record["data"]["status"] == captured["data"]["status"]
