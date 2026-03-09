diff --git a/yinyang_server.py b/yinyang_server.py
index 50d612f6..dc25b6c5 100644
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
@@ -73,6 +79,8 @@ import argparse
 import asyncio
 import atexit
 import base64
+import binascii
+import gzip
 import hashlib
 import http.server
 import json
@@ -89,11 +97,22 @@ import urllib.error
 import urllib.parse
 import urllib.request
 import uuid
+from datetime import datetime, timezone
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
@@ -101,10 +120,15 @@ from hub_tunnel_client import HubTunnelClient, SOLACEAGI_RELAY_URL
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
@@ -129,11 +153,30 @@ DEFAULT_CLOUD_TWIN_SETTINGS: dict = {
 _SERVER_VERSION = "1.1"
 YINYANG_PORT = 8888
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
@@ -224,6 +267,12 @@ _SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
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
@@ -315,6 +364,109 @@ def delete_port_lock() -> None:
 # ---------------------------------------------------------------------------
 # Evidence storage — append-only JSONL log
 # ---------------------------------------------------------------------------
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
 def record_evidence(event_type: str, data: dict) -> dict:
     """Append one evidence event to ~/.solace/evidence.jsonl. Returns the record."""
     record = {
@@ -324,11 +476,330 @@ def record_evidence(event_type: str, data: dict) -> dict:
         "data": data,
     }
     EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
-    with EVIDENCE_PATH.open("a") as fh:
+    with EVIDENCE_PATH.open("a", encoding="utf-8") as fh:
         fh.write(json.dumps(record) + "\n")
+    create_and_store_evidence_bundle(
+        action_type=event_type,
+        before_state=data.get("before_state_hash", {}),
+        after_state=data.get("after_state_hash", data),
+        oauth3_token_id=str(data.get("oauth3_token_id") or "system"),
+        user_id=str(data.get("user_id") or "system"),
+    )
     return record
 
 
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
@@ -388,6 +859,470 @@ def _load_user_tier_payload() -> dict:
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
 
@@ -633,6 +1568,53 @@ def _cloud_twin_status_payload() -> dict:
     }
 
 
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
 def _forward_cloud_twin_session(cloud_twin_url: str, payload: dict, timeout: float = 10.0) -> dict:
     body = json.dumps(payload).encode()
     request = urllib.request.Request(
@@ -930,23 +1912,31 @@ def load_apps(repo_root: str) -> list[str]:
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
@@ -1019,9 +2009,73 @@ def _find_session_rule(app_id: str) -> Optional[dict]:
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
@@ -1049,68 +2103,426 @@ def _normalize_domain(value: str) -> str:
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
+
+    if not host_matches:
+        return False
+    if not path_pattern:
+        return True
 
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
             continue
         manifest = _load_manifest_for_app(repo_root, app_id)
-        tier_required = str(manifest.get("tier") or session_rules.get("tier_required") or "free")
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
+            continue
+        manifest = _load_manifest_for_app(repo_root, app_id)
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
 
@@ -1128,6 +2540,8 @@ def _custom_app_manifest(app_id: str, display_name: str, description: str, domai
         'status: "installed"\n'
         'safety: "B"\n'
         'tier: "free"\n'
+        'domains:\n'
+        f'  - {json.dumps(domain)}\n'
         f"site: {domain}\n"
         'type: "custom"\n'
         'custom: true\n'
@@ -1159,6 +2573,40 @@ def _custom_app_session_rules(app_id: str, display_name: str, description: str,
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
@@ -1293,10 +2741,16 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
@@ -1309,6 +2763,16 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
@@ -1372,6 +2836,8 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_recipes_search(query)
         elif path == "/api/v1/oauth3/scopes":
             self._handle_oauth3_scopes()
+        elif path == "/api/v1/oauth3/token/validate":
+            self._handle_oauth3_validate(query)
         elif path == "/api/v1/schedules/next":
             self._handle_schedules_next()
         elif path == "/api/v1/capabilities":
@@ -1386,6 +2852,8 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
         elif path.startswith("/api/v1/oauth3/tokens/") and path.count("/") == 5:
             token_id = path.split("/")[-1]
             self._handle_oauth3_token_detail(token_id)
+        elif path == "/api/v1/oauth3/evidence":
+            self._handle_oauth3_evidence(query)
         elif path == "/api/v1/oauth3/audit":
             self._handle_oauth3_audit()
         elif path == "/api/v1/cli/available":
@@ -1523,6 +2991,10 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
@@ -1536,6 +3008,12 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
@@ -1613,6 +3091,8 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
             self._handle_pinned_set()
         elif path == "/api/v1/apps/favorites":
             self._handle_apps_favorites_post()
+        elif path == "/api/v1/apps/rebuild-domain-index":
+            self._handle_rebuild_domain_index()
         elif path == "/api/v1/apps/custom/create":
             self._handle_custom_app_create()
         elif path == "/api/v1/apps/sync":
@@ -1690,15 +3170,8 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
@@ -1798,6 +3271,177 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
+                "alcoa_status": ALCOABundle.check_compliance(bundle),
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
+                    "alcoa_status": ALCOABundle.check_compliance(bundle),
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
 
@@ -2512,53 +4156,53 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
@@ -2708,12 +4352,22 @@ class YinyangHandler(http.server.BaseHTTPRequestHandler):
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
@@ -3320,6 +4974,9 @@ function choose(mode) {
         self._send_json({"status": "terminated", "session_id": session_id})
 
     def _spawn_browser_session(self, url: str, profile: str) -> int:
+        if bool(getattr(self.server, "cloud_twin_mode", False)):
+            proc = _launch_chrome_cloud_twin(url)
+            return proc.pid
         browser = os.environ.get("SOLACE_BROWSER", "")
         if not browser:
             candidates = [
@@ -5182,6 +6839,11 @@ function choose(mode) {
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
@@ -5223,6 +6885,11 @@ function choose(mode) {
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
@@ -5272,20 +6939,28 @@ function choose(mode) {
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
 
 
@@ -5296,6 +6971,7 @@ def start_server(
     port: int = 8888,
     repo_root: str = ".",
     session_token_sha256: str = "",
+    cloud_twin: bool = False,
 ) -> None:
     """
     Generate token, write lock, register cleanup, then serve forever.
@@ -5307,6 +6983,11 @@ def start_server(
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
@@ -5320,18 +7001,39 @@ def start_server(
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
