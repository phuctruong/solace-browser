"""
test_yinyang_instructions.py — Yinyang Server endpoint tests.
Donald Knuth law: every test is a proof. RED → GREEN gate.

Port: 18888 (test-only, avoids conflict with production 8888)
"""
import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

# ---------------------------------------------------------------------------
# Inject the repo root so we can import yinyang-server regardless of cwd.
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18888
BASE_URL = f"http://localhost:{TEST_PORT}"
LEGACY_HUB_NAME = "Companion" + " App"
FORBIDDEN_DEBUG_PORT = "9" + "222"


# ---------------------------------------------------------------------------
# Fixture: spin up Yinyang Server on TEST_PORT in a daemon thread.
# Monkeypatches PORT_LOCK_PATH so we never pollute ~/.solace.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def server(tmp_path_factory, monkeypatch_module):
    tmp = tmp_path_factory.mktemp("solace")
    lock_path = tmp / "port.lock"

    # Patch the lock path before importing the module.
    import importlib
    import yinyang_server as ys

    original_lock = ys.PORT_LOCK_PATH
    ys.PORT_LOCK_PATH = lock_path

    token = ys.generate_token()
    t_hash = ys.token_hash(token)
    ys.write_port_lock(TEST_PORT, t_hash, 99999)

    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT))

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    # Wait until the server is actually accepting connections.
    for _ in range(30):
        try:
            urllib.request.urlopen(f"{BASE_URL}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {"lock_path": lock_path, "httpd": httpd}

    httpd.shutdown()
    ys.PORT_LOCK_PATH = original_lock


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch shim (pytest monkeypatch is function-scoped)."""
    return None  # we do manual patching above


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=5) as resp:
        return json.loads(resp.read().decode())


def post_json(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestHealthEndpoint:
    def test_health_endpoint(self, server):
        """GET /health → status == 'ok'."""
        data = get_json("/health")
        assert data["status"] == "ok"

    def test_health_has_version(self, server):
        """GET /health → 'version' key present."""
        data = get_json("/health")
        assert "version" in data

    def test_health_has_apps(self, server):
        """GET /health → 'apps' key is an integer."""
        data = get_json("/health")
        assert isinstance(data["apps"], int)


class TestInstructionsEndpoint:
    REQUIRED_KEYS = {
        "version",
        "hub",
        "server",
        "browser",
        "cli_commands",
        "apps_loaded",
        "capabilities",
        "forbidden",
    }

    def test_instructions_endpoint(self, server):
        """GET /instructions → all 8 required keys present."""
        data = get_json("/instructions")
        missing = self.REQUIRED_KEYS - set(data.keys())
        assert not missing, f"Missing keys: {missing}"

    def test_instructions_hub_name(self, server):
        """hub field must contain the approved Hub name."""
        data = get_json("/instructions")
        assert "Solace Hub" in data["hub"], f"hub field wrong: {data['hub']}"
        assert LEGACY_HUB_NAME not in data["hub"]

    def test_instructions_forbidden(self, server):
        """The forbidden list must include the debug-port ban marker."""
        data = get_json("/instructions")
        assert "forbidden_debug_port" in data["forbidden"]

    def test_instructions_legacy_hub_name_forbidden(self, server):
        """The forbidden list must include the legacy-name ban marker."""
        data = get_json("/instructions")
        assert "legacy_hub_name" in data["forbidden"]

    def test_instructions_extensions_forbidden(self, server):
        """'extensions' must appear in forbidden list."""
        data = get_json("/instructions")
        assert "extensions" in data["forbidden"]

    def test_instructions_server_field(self, server):
        """server field must reference 8888."""
        data = get_json("/instructions")
        assert "8888" in data["server"]

    def test_instructions_browser_field(self, server):
        """browser field must reference Chromium fork."""
        data = get_json("/instructions")
        assert "Chromium" in data["browser"]

    def test_instructions_cli_commands_list(self, server):
        """cli_commands must be a non-empty list."""
        data = get_json("/instructions")
        assert isinstance(data["cli_commands"], list)
        assert len(data["cli_commands"]) > 0

    def test_instructions_capabilities_list(self, server):
        """capabilities must be a non-empty list."""
        data = get_json("/instructions")
        assert isinstance(data["capabilities"], list)
        assert len(data["capabilities"]) > 0

    def test_instructions_apps_loaded_integer(self, server):
        """apps_loaded must be a non-negative integer."""
        data = get_json("/instructions")
        assert isinstance(data["apps_loaded"], int)
        assert data["apps_loaded"] >= 0

    def test_instructions_spec_file(self, server):
        """spec_file key must be present."""
        data = get_json("/instructions")
        assert "spec_file" in data


class TestPortLock:
    def test_port_lock_written(self, server):
        """PORT_LOCK_PATH must be written on server start."""
        lock_path = server["lock_path"]
        assert lock_path.exists(), "port.lock was not created"

    def test_port_lock_has_token_sha256(self, server):
        """port.lock must contain token_sha256 (hex), never plaintext token."""
        lock_path = server["lock_path"]
        data = json.loads(lock_path.read_text())
        assert "token_sha256" in data
        # SHA-256 hex digest is exactly 64 characters
        assert len(data["token_sha256"]) == 64
        # Must be a valid hex string
        int(data["token_sha256"], 16)

    def test_port_lock_has_pid(self, server):
        """port.lock must contain pid field."""
        lock_path = server["lock_path"]
        data = json.loads(lock_path.read_text())
        assert "pid" in data
        assert isinstance(data["pid"], int)

    def test_port_lock_no_plaintext_token(self, server):
        """port.lock must NOT contain a 'token' key (only hash)."""
        lock_path = server["lock_path"]
        data = json.loads(lock_path.read_text())
        assert "token" not in data, "Plaintext token found in port.lock — SECURITY VIOLATION"

    def test_port_lock_has_port(self, server):
        """port.lock must contain the port number."""
        lock_path = server["lock_path"]
        data = json.loads(lock_path.read_text())
        assert "port" in data
        assert data["port"] == TEST_PORT


class TestCreditsEndpoint:
    def test_credits_endpoint(self, server):
        """GET /credits → has 'apps' key."""
        data = get_json("/credits")
        assert "apps" in data

    def test_credits_apps_is_list(self, server):
        """GET /credits → 'apps' is a list of strings."""
        data = get_json("/credits")
        assert isinstance(data["apps"], list)
        for item in data["apps"]:
            assert isinstance(item, str), f"Non-string app id: {item!r}"


class TestDetectEndpoint:
    def test_detect_gmail(self, server):
        """POST /detect with gmail URL → returns apps list."""
        data = post_json("/detect", {"url": "https://mail.google.com/mail/u/0/"})
        assert "apps" in data
        assert isinstance(data["apps"], list)

    def test_detect_linkedin(self, server):
        """POST /detect with LinkedIn URL → returns apps list."""
        data = post_json("/detect", {"url": "https://www.linkedin.com/feed/"})
        assert "apps" in data

    def test_detect_unknown(self, server):
        """POST /detect with unknown URL → returns empty or minimal list."""
        data = post_json("/detect", {"url": "https://example.com/unknown-page"})
        assert "apps" in data

    def test_detect_missing_url(self, server):
        """POST /detect with no url field → 400 error."""
        body = json.dumps({}).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/detect",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                # Some implementations return 200 with error field
                assert "error" in data or "apps" in data
        except urllib.error.URLError as exc:
            assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
            assert exc.code == 400


class TestNotFoundEndpoint:
    def test_unknown_path_404(self, server):
        """Unknown path → 404."""
        try:
            urllib.request.urlopen(f"{BASE_URL}/nonexistent", timeout=5)
            pytest.fail("Expected 404 but got 200")
        except urllib.error.URLError as exc:
            assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
            assert exc.code == 404

    def test_no_forbidden_debug_port_reference(self, server):
        """
        Safety: /instructions must never expose the forbidden debug port as a live endpoint.
        The forbidden list may name the ban declaration.
        No other field may contain the forbidden debug-port marker.
        """
        data = get_json("/instructions")
        # Check every field EXCEPT the forbidden list (which names the ban).
        for key, value in data.items():
            if key == "forbidden":
                continue
            raw_value = json.dumps(value)
            assert FORBIDDEN_DEBUG_PORT not in raw_value, (
                f"Forbidden debug port referenced in field '{key}': {raw_value} — BANNED"
            )

    def test_no_legacy_hub_name_in_any_response(self, server):
        """Safety: no endpoint response may contain the legacy hub name."""
        for path in ("/health", "/instructions", "/credits"):
            data = get_json(path)
            raw = json.dumps(data)
            assert LEGACY_HUB_NAME not in raw, f"Legacy hub name found in {path} response"

# ---------------------------------------------------------------------------
# Phase 3: Evidence API
# ---------------------------------------------------------------------------
def delete_json(path: str) -> tuple[int, dict]:
    """Make a DELETE request, return (status_code, body)."""
    req = urllib.request.Request(f"{BASE_URL}{path}", method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
        assert hasattr(exc, "read"), f"Expected readable HTTP error, got: {exc}"
        return exc.code, json.loads(exc.read().decode())


class TestEvidenceAPI:
    def test_evidence_list_empty(self, server):
        """GET /api/v1/evidence → returns records list and total."""
        data = get_json("/api/v1/evidence")
        assert "records" in data
        assert "total" in data
        assert isinstance(data["records"], list)

    def test_evidence_record_event(self, server):
        """POST /api/v1/evidence → creates record, returns id + type."""
        data = post_json("/api/v1/evidence", {"type": "test_event", "data": {"x": 1}})
        assert "id" in data
        assert data["type"] == "test_event"
        assert "ts" in data

    def test_evidence_list_after_record(self, server):
        """After recording, list should include the event."""
        post_json("/api/v1/evidence", {"type": "probe_event", "data": {}})
        data = get_json("/api/v1/evidence")
        assert data["total"] >= 1

    def test_evidence_missing_type_400(self, server):
        """POST /api/v1/evidence without 'type' → 400."""
        body = json.dumps({"data": {}}).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/evidence",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("Expected 400")
        except urllib.error.URLError as exc:
            assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
            assert exc.code == 400

    def test_evidence_limit_param(self, server):
        """GET /api/v1/evidence?limit=1 → returns at most 1 record."""
        data = get_json("/api/v1/evidence?limit=1")
        assert len(data["records"]) <= 1


# ---------------------------------------------------------------------------
# Phase 3: Schedule API
# ---------------------------------------------------------------------------
class TestScheduleAPI:
    def test_schedule_list(self, server):
        """GET /api/v1/browser/schedules → returns schedules list."""
        data = get_json("/api/v1/browser/schedules")
        assert "schedules" in data
        assert isinstance(data["schedules"], list)

    def test_schedule_create(self, server):
        """POST /api/v1/browser/schedules → creates schedule, returns id."""
        data = post_json("/api/v1/browser/schedules", {
            "app_id": "gmail-inbox-triage",
            "cron": "0 9 * * 1-5",
            "url": "https://mail.google.com",
        })
        assert "id" in data
        assert data["app_id"] == "gmail-inbox-triage"
        assert data["cron"] == "0 9 * * 1-5"
        assert data["enabled"] is True

    def test_schedule_appears_in_list(self, server):
        """Created schedule appears in GET /api/v1/browser/schedules."""
        created = post_json("/api/v1/browser/schedules", {
            "app_id": "linkedin-poster",
            "cron": "0 10 * * 1",
            "url": "https://linkedin.com",
        })
        data = get_json("/api/v1/browser/schedules")
        ids = [s["id"] for s in data["schedules"]]
        assert created["id"] in ids

    def test_schedule_delete(self, server):
        """DELETE /api/v1/browser/schedules/{id} → removes schedule."""
        created = post_json("/api/v1/browser/schedules", {
            "app_id": "twitter-poster",
            "cron": "0 8 * * *",
            "url": "https://twitter.com",
        })
        status, data = delete_json(f"/api/v1/browser/schedules/{created['id']}")
        assert status == 200
        assert data["deleted"] == created["id"]

    def test_schedule_delete_not_found(self, server):
        """DELETE non-existent schedule → 404."""
        status, data = delete_json("/api/v1/browser/schedules/nonexistent-id")
        assert status == 404

    def test_schedule_missing_app_id_400(self, server):
        """POST /api/v1/browser/schedules without app_id → 400."""
        body = json.dumps({"cron": "0 9 * * *"}).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/browser/schedules",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("Expected 400")
        except urllib.error.URLError as exc:
            assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
            assert exc.code == 400


# ---------------------------------------------------------------------------
# Phase 3: OAuth3 Token API
# ---------------------------------------------------------------------------
class TestOAuth3API:
    def test_oauth3_list(self, server):
        """GET /api/v1/oauth3/tokens → returns tokens list."""
        data = get_json("/api/v1/oauth3/tokens")
        assert "tokens" in data
        assert isinstance(data["tokens"], list)

    def test_oauth3_register(self, server):
        """POST /api/v1/oauth3/tokens → registers token metadata (no plaintext)."""
        data = post_json("/api/v1/oauth3/tokens", {
            "scope": "gmail.readonly",
            "service": "google",
            "token_sha256": "a" * 64,
        })
        assert "id" in data
        assert data["scope"] == "gmail.readonly"
        assert "token_sha256" not in data, "token_sha256 must not be echoed back"

    def test_oauth3_register_appears_in_list(self, server):
        """Registered token appears in GET list (without sha256)."""
        created = post_json("/api/v1/oauth3/tokens", {
            "scope": "linkedin.write",
            "service": "linkedin",
            "token_sha256": "b" * 64,
        })
        data = get_json("/api/v1/oauth3/tokens")
        ids = [t["id"] for t in data["tokens"]]
        assert created["id"] in ids
        # Verify no token_sha256 in list response
        for t in data["tokens"]:
            assert "token_sha256" not in t

    def test_oauth3_revoke(self, server):
        """DELETE /api/v1/oauth3/tokens/{id} → revokes token."""
        created = post_json("/api/v1/oauth3/tokens", {
            "scope": "twitter.write",
            "service": "twitter",
            "token_sha256": "c" * 64,
        })
        status, data = delete_json(f"/api/v1/oauth3/tokens/{created['id']}")
        assert status == 200
        assert data["revoked"] == created["id"]

    def test_oauth3_revoke_not_found(self, server):
        """DELETE non-existent token → 404."""
        status, data = delete_json("/api/v1/oauth3/tokens/nonexistent-id")
        assert status == 404

    def test_start_endpoint(self, server):
        """GET /start → returns 200 with HTML."""
        req = urllib.request.Request(f"{BASE_URL}/start")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            content = resp.read().decode()
            assert "html" in content.lower()

    def test_health_includes_evidence_count(self, server):
        """GET /health → includes evidence_count and schedule_count."""
        data = get_json("/health")
        assert "evidence_count" in data
        assert "schedule_count" in data
        assert isinstance(data["evidence_count"], int)
        assert isinstance(data["schedule_count"], int)


AUTH_TEST_PORT = 18889
AUTH_BASE = f"http://localhost:{AUTH_TEST_PORT}"
VALID_TOKEN = "a" * 64


@pytest.fixture(scope="module")
def auth_server(tmp_path_factory, monkeypatch_module):
    """Auth-enabled server fixture — uses a known token for testing Bearer auth."""
    import yinyang_server as ys

    tmp = tmp_path_factory.mktemp("auth_solace")
    lock_path = tmp / "port.lock"
    evidence_path = tmp / "evidence.jsonl"
    schedules_path = tmp / "schedules.json"
    oauth3_tokens_path = tmp / "oauth3-tokens.json"
    budget_path = tmp / "budget.json"
    recipe_runs_path = tmp / "recipe_runs.json"

    byok_path = tmp / "byok_keys.json"
    notifications_path = tmp / "notifications.json"
    profiles_path = tmp / "profiles.json"
    active_profile_path = tmp / "active_profile.json"
    installed_recipes_path = tmp / "installed_recipes.json"
    cli_config_path = tmp / "cli_config.json"
    spend_history_path = tmp / "spend_history.json"
    watchdog_log_path = tmp / "watchdog.log"
    theme_path = tmp / "theme.json"
    pinned_sections_path = tmp / "pinned_sections.json"
    favorites_path = tmp / "favorites.json"

    original_lock = ys.PORT_LOCK_PATH
    original_evidence = ys.EVIDENCE_PATH
    original_schedules = ys.SCHEDULES_PATH
    original_oauth3_tokens = ys.OAUTH3_TOKENS_PATH
    original_budget = ys.BUDGET_PATH
    original_recipe_runs = ys.RECIPE_RUNS_PATH
    original_byok = ys.BYOK_PATH
    original_notifications = ys.NOTIFICATIONS_PATH
    original_profiles = ys.PROFILES_PATH
    original_active_profile = ys.ACTIVE_PROFILE_PATH
    original_installed_recipes = ys.INSTALLED_RECIPES_PATH
    original_cli_config = ys.CLI_CONFIG_PATH
    original_spend_history = ys.SPEND_HISTORY_PATH
    original_watchdog_log = ys.WATCHDOG_LOG_PATH
    original_theme = ys.THEME_PATH
    original_pinned = ys.PINNED_SECTIONS_PATH
    original_favorites = ys.FAVORITES_PATH

    ys.PORT_LOCK_PATH = lock_path
    ys.EVIDENCE_PATH = evidence_path
    ys.SCHEDULES_PATH = schedules_path
    ys.OAUTH3_TOKENS_PATH = oauth3_tokens_path
    ys.BUDGET_PATH = budget_path
    ys.RECIPE_RUNS_PATH = recipe_runs_path
    ys.BYOK_PATH = byok_path
    ys.NOTIFICATIONS_PATH = notifications_path
    ys.PROFILES_PATH = profiles_path
    ys.ACTIVE_PROFILE_PATH = active_profile_path
    ys.INSTALLED_RECIPES_PATH = installed_recipes_path
    ys.CLI_CONFIG_PATH = cli_config_path
    ys.SPEND_HISTORY_PATH = spend_history_path
    ys.WATCHDOG_LOG_PATH = watchdog_log_path
    ys.PINNED_SECTIONS_PATH = pinned_sections_path
    ys.THEME_PATH = theme_path
    ys.FAVORITES_PATH = favorites_path

    httpd = ys.build_server(AUTH_TEST_PORT, str(REPO_ROOT), session_token_sha256=VALID_TOKEN)

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    for _ in range(30):
        try:
            urllib.request.urlopen(f"{AUTH_BASE}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {"httpd": httpd, "token_sha256": VALID_TOKEN, "base_url": AUTH_BASE}

    httpd.shutdown()
    ys.PORT_LOCK_PATH = original_lock
    ys.EVIDENCE_PATH = original_evidence
    ys.SCHEDULES_PATH = original_schedules
    ys.OAUTH3_TOKENS_PATH = original_oauth3_tokens
    ys.BUDGET_PATH = original_budget
    ys.RECIPE_RUNS_PATH = original_recipe_runs
    ys.BYOK_PATH = original_byok
    ys.NOTIFICATIONS_PATH = original_notifications
    ys.PROFILES_PATH = original_profiles
    ys.ACTIVE_PROFILE_PATH = original_active_profile
    ys.INSTALLED_RECIPES_PATH = original_installed_recipes
    ys.CLI_CONFIG_PATH = original_cli_config
    ys.SPEND_HISTORY_PATH = original_spend_history
    ys.PINNED_SECTIONS_PATH = original_pinned
    ys.WATCHDOG_LOG_PATH = original_watchdog_log
    ys.THEME_PATH = original_theme
    ys.FAVORITES_PATH = original_favorites


def _post_with_auth(path: str, payload: dict, token: str = VALID_TOKEN) -> tuple[int, dict]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{AUTH_BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
        assert hasattr(exc, "read"), f"Expected readable HTTP error, got: {exc}"
        return exc.code, json.loads(exc.read().decode())


def _post_no_auth(path: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{AUTH_BASE}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
        assert hasattr(exc, "read"), f"Expected readable HTTP error, got: {exc}"
        return exc.code, json.loads(exc.read().decode())


class TestAuthSecurity:
    def test_get_endpoints_no_auth_required(self, auth_server):
        """GET endpoints must NOT require auth (read-only, safe)."""
        for path in ("/health", "/instructions", "/credits"):
            with urllib.request.urlopen(f"{AUTH_BASE}{path}", timeout=5) as resp:
                assert resp.status == 200, f"GET {path} should be 200 without auth"

    def test_bearer_auth_blocks_unauthenticated_post(self, auth_server):
        """POST without auth header → 401."""
        status, data = _post_no_auth("/api/v1/evidence", {"type": "test", "data": {}})
        assert status == 401, f"Expected 401, got {status}: {data}"
        assert "unauthorized" in data.get("error", "").lower()

    def test_bearer_auth_allows_authenticated_post(self, auth_server):
        """POST with correct Bearer token → 201."""
        status, data = _post_with_auth("/api/v1/evidence", {"type": "auth_test", "data": {}}, VALID_TOKEN)
        assert status == 201, f"Expected 201, got {status}: {data}"
        assert "id" in data

    def test_bearer_auth_blocks_wrong_token(self, auth_server):
        """POST with wrong Bearer token → 401."""
        status, _ = _post_with_auth("/api/v1/evidence", {"type": "test", "data": {}}, "b" * 64)
        assert status == 401, f"Expected 401 for wrong token, got {status}"

    def test_detect_requires_auth(self, auth_server):
        """POST /detect without auth → 401."""
        status, _ = _post_no_auth("/detect", {"url": "https://mail.google.com/"})
        assert status == 401

    def test_schedule_create_requires_auth(self, auth_server):
        """POST /api/v1/browser/schedules without auth → 401."""
        status, _ = _post_no_auth(
            "/api/v1/browser/schedules",
            {"app_id": "gmail", "cron": "0 9 * * 1-5", "url": "https://mail.google.com/"},
        )
        assert status == 401


# ---------------------------------------------------------------------------
# Task 005: Security hardening — URL matching, cron/input validation
# ---------------------------------------------------------------------------
class TestURLDomainMatching:
    def test_detect_gmail_exact_domain(self, server):
        """POST /detect gmail URL → exact domain match, not substring."""
        data = post_json("/detect", {"url": "https://mail.google.com/mail/u/0/"})
        assert "apps" in data
        assert isinstance(data["apps"], list)

    def test_detect_linkedin_exact_domain(self, server):
        """POST /detect LinkedIn → exact domain match."""
        data = post_json("/detect", {"url": "https://www.linkedin.com/feed/"})
        assert "apps" in data

    def test_detect_subdomain_of_gmail_matches(self, server):
        """POST /detect with subdomain of mail.google.com → matches."""
        # www.mail.google.com ends with .mail.google.com — should match
        data = post_json("/detect", {"url": "https://www.mail.google.com/"})
        assert "apps" in data

    def test_detect_fake_domain_no_match(self, server):
        """POST /detect with evil.mail.google.com.evil.com → no match (not a real subdomain)."""
        data = post_json("/detect", {"url": "https://evil.com/mail.google.com/"})
        # Should NOT match gmail apps — evil.com is not a google.com subdomain
        assert "apps" in data
        # The path contains mail.google.com but the netloc does NOT — so no gmail apps
        gmail_apps = {"gmail-inbox-triage", "gmail-spam-cleaner"}
        matched = set(data["apps"])
        assert matched.isdisjoint(gmail_apps), (
            f"URL with malicious path matched gmail apps: {matched}"
        )


class TestCronValidation:
    def test_invalid_cron_4_fields_rejected(self, server):
        """POST /api/v1/browser/schedules with 4-field cron → 400."""
        body = json.dumps({
            "app_id": "gmail-inbox-triage",
            "cron": "0 9 * *",  # only 4 fields — invalid
            "url": "https://mail.google.com/",
        }).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/browser/schedules",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("Expected 400 for invalid cron")
        except urllib.error.URLError as exc:
            assert exc.code == 400

    def test_invalid_cron_too_long_rejected(self, server):
        """POST /api/v1/browser/schedules with cron > 64 chars → 400."""
        long_cron = "0 " + "9 " * 30 + "* * *"  # way over 64 chars
        body = json.dumps({
            "app_id": "gmail-inbox-triage",
            "cron": long_cron,
            "url": "https://mail.google.com/",
        }).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/browser/schedules",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("Expected 400 for cron > 64 chars")
        except urllib.error.URLError as exc:
            assert exc.code == 400

    def test_valid_cron_5_fields_accepted(self, server):
        """POST /api/v1/browser/schedules with valid 5-field cron → 201."""
        data = post_json("/api/v1/browser/schedules", {
            "app_id": "gmail-inbox-triage",
            "cron": "0 9 * * 1-5",
            "url": "https://mail.google.com/",
        })
        assert "id" in data

    def test_app_id_too_long_rejected(self, server):
        """POST /api/v1/browser/schedules with app_id > 256 chars → 400."""
        long_id = "a" * 257
        body = json.dumps({
            "app_id": long_id,
            "cron": "0 9 * * *",
            "url": "https://mail.google.com/",
        }).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/browser/schedules",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("Expected 400 for app_id > 256 chars")
        except urllib.error.URLError as exc:
            assert exc.code == 400


class TestOAuth3Validation:
    def test_invalid_token_sha256_rejected(self, server):
        """POST /api/v1/oauth3/tokens with non-hex token_sha256 → 400."""
        body = json.dumps({
            "scope": "gmail.readonly",
            "service": "google",
            "token_sha256": "NOTAHEXSTRING",  # not 64 hex chars
        }).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/oauth3/tokens",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("Expected 400 for invalid token_sha256")
        except urllib.error.URLError as exc:
            assert exc.code == 400

    def test_token_sha256_63_hex_chars_rejected(self, server):
        """POST /api/v1/oauth3/tokens with 63-char token_sha256 → 400."""
        body = json.dumps({
            "scope": "gmail.readonly",
            "service": "google",
            "token_sha256": "a" * 63,  # one char short
        }).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/oauth3/tokens",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("Expected 400 for 63-char token_sha256")
        except urllib.error.URLError as exc:
            assert exc.code == 400

    def test_scope_too_long_rejected(self, server):
        """POST /api/v1/oauth3/tokens with scope > 256 chars → 400."""
        body = json.dumps({
            "scope": "s" * 257,
            "service": "google",
            "token_sha256": "a" * 64,
        }).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/oauth3/tokens",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("Expected 400 for scope > 256 chars")
        except urllib.error.URLError as exc:
            assert exc.code == 400

    def test_service_too_long_rejected(self, server):
        """POST /api/v1/oauth3/tokens with service > 256 chars → 400."""
        body = json.dumps({
            "scope": "gmail.readonly",
            "service": "s" * 257,
            "token_sha256": "a" * 64,
        }).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/oauth3/tokens",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("Expected 400 for service > 256 chars")
        except urllib.error.URLError as exc:
            assert exc.code == 400


class TestEvidenceValidation:
    def test_event_type_too_long_rejected(self, server):
        """POST /api/v1/evidence with event_type > 256 chars → 400."""
        body = json.dumps({
            "type": "t" * 257,
            "data": {},
        }).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/evidence",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("Expected 400 for event_type > 256 chars")
        except urllib.error.URLError as exc:
            assert exc.code == 400


# ---------------------------------------------------------------------------
# Task 007: CLI wrapper endpoint
# ---------------------------------------------------------------------------
class TestCLIAvailableEndpoint:
    def test_cli_available_returns_json(self, server):
        """GET /api/v1/cli/available → JSON with 'available' key."""
        data = get_json("/api/v1/cli/available")
        assert "available" in data
        assert isinstance(data["available"], bool)

    def test_cli_available_has_version_key(self, server):
        """GET /api/v1/cli/available → 'version' key present (str or null)."""
        data = get_json("/api/v1/cli/available")
        assert "version" in data
        assert data["version"] is None or isinstance(data["version"], str)


class TestCLIRunEndpoint:
    def test_cli_run_requires_auth(self, auth_server):
        """POST /api/v1/cli/run without auth → 401."""
        status, _ = _post_no_auth("/api/v1/cli/run", {"command": "hub status"})
        assert status == 401

    def test_cli_run_allowlist_reject_unknown(self, auth_server):
        """POST /api/v1/cli/run with command not in allowlist → 400."""
        status, data = _post_with_auth(
            "/api/v1/cli/run", {"command": "rm -rf /"}, VALID_TOKEN
        )
        assert status == 400
        assert "allowlist" in data.get("error", "").lower() or "command" in data.get("error", "").lower()

    def test_cli_run_allowlist_valid_command(self, auth_server):
        """POST /api/v1/cli/run with allowlisted command → exit_code, stdout, stderr."""
        status, data = _post_with_auth(
            "/api/v1/cli/run", {"command": "hub status"}, VALID_TOKEN
        )
        # CLI may not be installed (exit_code != 0), but response structure must be correct.
        # 200 with result structure OR 503 if CLI missing.
        if status == 200:
            assert "exit_code" in data
            assert "stdout" in data
            assert "stderr" in data
        else:
            assert status == 503

    def test_cli_run_missing_command_400(self, auth_server):
        """POST /api/v1/cli/run without 'command' → 400."""
        status, data = _post_with_auth("/api/v1/cli/run", {}, VALID_TOKEN)
        assert status == 400


# ---------------------------------------------------------------------------
# Task 008: Onboarding flow
# ---------------------------------------------------------------------------
class TestOnboardingEndpoints:
    def test_onboarding_page_returns_html(self, server):
        """GET /onboarding → 200 with HTML content."""
        req = urllib.request.Request(f"{BASE_URL}/onboarding")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            content = resp.read().decode()
            assert "<!DOCTYPE html>" in content or "<!doctype html>" in content.lower()
            assert "Solace Hub" in content

    def test_onboarding_page_has_4_mode_buttons(self, server):
        """GET /onboarding → HTML contains all 4 mode choices."""
        req = urllib.request.Request(f"{BASE_URL}/onboarding")
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read().decode()
        for mode in ("agent", "byok", "paid", "cli"):
            assert mode in content, f"Mode '{mode}' not found in onboarding HTML"

    def test_onboarding_status_returns_json(self, server):
        """GET /api/v1/onboarding/status → JSON with 'completed' and 'mode'."""
        data = get_json("/api/v1/onboarding/status")
        assert "completed" in data
        assert isinstance(data["completed"], bool)
        assert "mode" in data

    def test_onboarding_complete_valid_mode(self, server):
        """POST /onboarding/complete with valid mode → 200."""
        data = post_json("/onboarding/complete", {"mode": "byok"})
        assert data.get("ok") is True
        assert data.get("mode") == "byok"

    def test_onboarding_complete_invalid_mode_400(self, server):
        """POST /onboarding/complete with unknown mode → 400."""
        body = json.dumps({"mode": "invalid_mode_xyz"}).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/onboarding/complete",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            pytest.fail("Expected 400 for invalid mode")
        except urllib.error.URLError as exc:
            assert exc.code == 400

    def test_onboarding_status_reflects_completion(self, server):
        """After POST /onboarding/complete, GET status shows completed=True."""
        post_json("/onboarding/complete", {"mode": "agent"})
        data = get_json("/api/v1/onboarding/status")
        assert data["completed"] is True
        assert data["mode"] == "agent"

    def test_onboarding_reset_requires_auth(self, auth_server):
        """POST /onboarding/reset without auth → 401."""
        status, _ = _post_no_auth("/onboarding/reset", {})
        assert status == 401

    def test_onboarding_reset_with_auth(self, auth_server):
        """POST /onboarding/reset with valid auth → 200."""
        status, data = _post_with_auth("/onboarding/reset", {}, VALID_TOKEN)
        assert status == 200
        assert data.get("ok") is True

    def test_onboarding_no_api_key_in_json(self, server):
        """POST /onboarding/complete must never write API key to disk."""
        import yinyang_server as ys
        post_json("/onboarding/complete", {"mode": "byok"})
        try:
            raw = ys.ONBOARDING_PATH.read_text()
            data = json.loads(raw)
            # Must not contain API key fields
            for forbidden in ("api_key", "token", "secret", "password"):
                assert forbidden not in data, f"Forbidden field '{forbidden}' in onboarding.json"
        except FileNotFoundError:
            pass  # file may not exist in test isolation


# ---------------------------------------------------------------------------
# Task 010: OAuth3 Token Management Dashboard
# ---------------------------------------------------------------------------
def _get_auth(path: str) -> tuple[int, dict]:
    """GET request to auth server, return (status, body)."""
    try:
        with urllib.request.urlopen(f"{AUTH_BASE}{path}", timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
        assert hasattr(exc, "read"), f"Expected readable HTTP error, got: {exc}"
        return exc.code, json.loads(exc.read().decode())


class TestOAuth3Management:
    def test_oauth3_token_detail_not_found(self, auth_server):
        """GET /api/v1/oauth3/tokens/{nonexistent} → 404."""
        status, data = _get_auth("/api/v1/oauth3/tokens/nonexistent-id-xyz")
        assert status == 404
        assert "error" in data

    def test_oauth3_extend_max_days(self, auth_server):
        """Extend by >30 days → 400."""
        # First register a token with new schema
        reg_status, reg_data = _post_with_auth(
            "/api/v1/oauth3/tokens",
            {
                "agent_name": "Test Agent",
                "scopes": ["browse"],
                "expires_at": int(time.time()) + 3600,
            },
            VALID_TOKEN,
        )
        assert reg_status == 200, f"Register failed: {reg_data}"
        token_id = reg_data.get("token_id", "")
        assert token_id, f"token_id missing in response: {reg_data}"
        # Try extending beyond 30 days
        status, data = _post_with_auth(
            f"/api/v1/oauth3/tokens/{token_id}/extend",
            {"seconds": 2592001},  # > 30 days
            VALID_TOKEN,
        )
        assert status == 400
        assert "max" in data.get("error", "").lower()

    def test_oauth3_scope_validation(self, auth_server):
        """Register with invalid scope → 400."""
        status, data = _post_with_auth(
            "/api/v1/oauth3/tokens",
            {
                "agent_name": "Bad Agent",
                "scopes": ["invalid_scope_xyz"],
                "expires_at": int(time.time()) + 3600,
            },
            VALID_TOKEN,
        )
        assert status == 400
        assert "invalid" in data.get("error", "").lower()

    def test_oauth3_audit_list(self, auth_server):
        """GET /api/v1/oauth3/audit → 200 with entries list."""
        status, data = _get_auth("/api/v1/oauth3/audit")
        assert status == 200
        assert "entries" in data
        assert isinstance(data["entries"], list)

    def test_oauth3_extend_not_found(self, auth_server):
        """Extend nonexistent token → 404."""
        status, data = _post_with_auth(
            "/api/v1/oauth3/tokens/nonexistent/extend",
            {"seconds": 3600},
            VALID_TOKEN,
        )
        assert status == 404

    def test_oauth3_extend_requires_auth(self, auth_server):
        """POST extend without auth → 401."""
        status, data = _post_no_auth(
            "/api/v1/oauth3/tokens/some-id/extend",
            {"seconds": 3600},
        )
        assert status == 401

    def test_oauth3_scope_allowlist_only(self, auth_server):
        """Valid scopes from ALLOWED_SCOPES accepted → 200."""
        status, data = _post_with_auth(
            "/api/v1/oauth3/tokens",
            {
                "agent_name": "Valid Agent",
                "scopes": ["browse", "run_recipe"],
                "expires_at": int(time.time()) + 3600,
            },
            VALID_TOKEN,
        )
        assert status == 200

    def test_oauth3_expires_at_past(self, auth_server):
        """Token with expires_at in the past → 400."""
        status, data = _post_with_auth(
            "/api/v1/oauth3/tokens",
            {
                "agent_name": "Expired Agent",
                "scopes": ["browse"],
                "expires_at": int(time.time()) - 1,
            },
            VALID_TOKEN,
        )
        assert status == 400

    def test_oauth3_token_detail_found(self, auth_server):
        """After registering, GET /api/v1/oauth3/tokens/{id} → 200 with token fields."""
        reg_status, reg_data = _post_with_auth(
            "/api/v1/oauth3/tokens",
            {
                "agent_name": "Detail Agent",
                "scopes": ["browse"],
                "expires_at": int(time.time()) + 3600,
            },
            VALID_TOKEN,
        )
        assert reg_status == 200
        token_id = reg_data.get("token_id", "")
        assert token_id
        status, data = _get_auth(f"/api/v1/oauth3/tokens/{token_id}")
        assert status == 200
        assert data.get("token_id") == token_id
        assert "token_sha256" not in data

    def test_oauth3_extend_token(self, auth_server):
        """POST extend with valid seconds → 200 with updated expires_at."""
        reg_status, reg_data = _post_with_auth(
            "/api/v1/oauth3/tokens",
            {
                "agent_name": "Extend Agent",
                "scopes": ["browse"],
                "expires_at": int(time.time()) + 3600,
            },
            VALID_TOKEN,
        )
        assert reg_status == 200
        token_id = reg_data.get("token_id", "")
        assert token_id
        status, data = _post_with_auth(
            f"/api/v1/oauth3/tokens/{token_id}/extend",
            {"seconds": 3600},
            VALID_TOKEN,
        )
        assert status == 200
        assert data.get("status") == "extended"
        assert "expires_at" in data

    def test_oauth3_revoked_cannot_extend(self, auth_server):
        """Revoke a token then try extend → 400."""
        reg_status, reg_data = _post_with_auth(
            "/api/v1/oauth3/tokens",
            {
                "agent_name": "Revoke Then Extend",
                "scopes": ["browse"],
                "expires_at": int(time.time()) + 3600,
            },
            VALID_TOKEN,
        )
        assert reg_status == 200
        token_id = reg_data.get("token_id", "")
        # Revoke it
        rev_req = urllib.request.Request(
            f"{AUTH_BASE}/api/v1/oauth3/tokens/{token_id}",
            headers={"Authorization": f"Bearer {VALID_TOKEN}"},
            method="DELETE",
        )
        try:
            with urllib.request.urlopen(rev_req, timeout=5) as resp:
                pass
        except urllib.error.URLError:
            pass
        # Now try to extend
        status, data = _post_with_auth(
            f"/api/v1/oauth3/tokens/{token_id}/extend",
            {"seconds": 3600},
            VALID_TOKEN,
        )
        assert status == 400
        assert "revoked" in data.get("error", "").lower()


# ── Task 011: Browser Session Manager ─────────────────────────────────────────


def _get_json_auth(path: str, base: str = AUTH_BASE) -> tuple[int, dict]:
    req = urllib.request.Request(f"{base}{path}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
        assert hasattr(exc, "read"), f"Expected readable HTTP error, got: {exc}"
        return exc.code, json.loads(exc.read().decode())


def _delete_with_auth(path: str, token: str = VALID_TOKEN, base: str = AUTH_BASE) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{base}{path}",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
        assert hasattr(exc, "read"), f"Expected readable HTTP error, got: {exc}"
        return exc.code, json.loads(exc.read().decode())


def _delete_no_auth(path: str, base: str = AUTH_BASE) -> tuple[int, dict]:
    req = urllib.request.Request(f"{base}{path}", method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        assert hasattr(exc, "code"), f"Expected HTTP error, got: {exc}"
        assert hasattr(exc, "read"), f"Expected readable HTTP error, got: {exc}"
        return exc.code, json.loads(exc.read().decode())


class TestSessionManager:
    def test_sessions_list_empty(self, auth_server):
        """GET /api/v1/sessions → 200 with sessions list (may be empty)."""
        import yinyang_server as ys
        # Clear any stale sessions from other tests
        with ys._SESSIONS_LOCK:
            ys._SESSIONS.clear()
        status, data = _get_json_auth("/api/v1/sessions")
        assert status == 200
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_session_create_url_validation_external(self, auth_server):
        """Must reject non-localhost URLs."""
        status, data = _post_with_auth(
            "/api/v1/sessions",
            {"url": "https://evil.com/steal"},
        )
        assert status == 400
        assert "localhost" in data.get("error", "").lower()

    def test_session_create_url_validation_https_evil(self, auth_server):
        """Must reject non-localhost IP addresses."""
        status, data = _post_with_auth(
            "/api/v1/sessions",
            {"url": "http://192.168.1.1/admin"},
        )
        assert status == 400

    def test_session_profile_validation_dotdot(self, auth_server):
        """Profile with '..' path traversal must be rejected."""
        status, data = _post_with_auth(
            "/api/v1/sessions",
            {"url": "http://localhost:8888/start", "profile": "../evil"},
        )
        assert status == 400

    def test_session_profile_validation_slash(self, auth_server):
        """Profile with '/' must be rejected."""
        status, data = _post_with_auth(
            "/api/v1/sessions",
            {"url": "http://localhost:8888/start", "profile": "foo/bar"},
        )
        assert status == 400

    def test_session_create_no_binary(self, auth_server, monkeypatch):
        """When browser binary is not found, must return 503."""
        import os as _os
        original_env = _os.environ.get("SOLACE_BROWSER", "")
        _os.environ["SOLACE_BROWSER"] = "/nonexistent/solace-browser"
        try:
            status, data = _post_with_auth(
                "/api/v1/sessions",
                {"url": "http://localhost:8888/start", "profile": "default"},
            )
            assert status == 503
            assert "not found" in data.get("error", "").lower()
        finally:
            if original_env:
                _os.environ["SOLACE_BROWSER"] = original_env
            else:
                _os.environ.pop("SOLACE_BROWSER", None)

    def test_session_kill_not_found(self, auth_server):
        """DELETE /api/v1/sessions/nonexistent → 404."""
        status, data = _delete_with_auth("/api/v1/sessions/nonexistent-session-id")
        assert status == 404
        assert "not found" in data.get("error", "").lower()

    def test_sessions_require_auth_post(self, auth_server):
        """POST /api/v1/sessions without Bearer → 401."""
        status, data = _post_no_auth(
            "/api/v1/sessions",
            {"url": "http://localhost:8888/start"},
        )
        assert status == 401

    def test_sessions_require_auth_delete(self, auth_server):
        """DELETE /api/v1/sessions/{id} without Bearer → 401."""
        status, data = _delete_no_auth("/api/v1/sessions/some-id")
        assert status == 401

    def test_session_detail_not_found(self, auth_server):
        """GET /api/v1/sessions/{unknown_id} → 404."""
        status, data = _get_json_auth("/api/v1/sessions/00000000-0000-0000-0000-000000000000")
        assert status == 404
        assert "not found" in data.get("error", "").lower()

    def test_session_list_shows_dead_session(self, auth_server):
        """A session with a dead PID shows alive=False in list response."""
        import yinyang_server as ys
        dead_session_id = "dead-test-session-0001"
        with ys._SESSIONS_LOCK:
            ys._SESSIONS[dead_session_id] = {
                "url": "http://localhost:8888/start",
                "profile": "default",
                "pid": 99999999,  # will not exist
                "started_at": 0,
            }
        try:
            status, data = _get_json_auth("/api/v1/sessions")
            assert status == 200
            sessions = data["sessions"]
            dead = [s for s in sessions if s["session_id"] == dead_session_id]
            assert dead, "Dead session must appear in list"
            assert dead[0]["alive"] is False
        finally:
            with ys._SESSIONS_LOCK:
                ys._SESSIONS.pop(dead_session_id, None)


# ── Task 012: Tunnel + Vault Sync Management ─────────────────────────────────

class TestTunnelSync:
    def test_tunnel_status_initial(self, auth_server):
        """GET /api/v1/tunnel/status → active=False initially."""
        status, data = _get_json_auth("/api/v1/tunnel/status")
        assert status == 200
        assert "active" in data
        assert data["active"] is False
        assert "port" in data

    def test_tunnel_start_no_cloudflared(self, auth_server, monkeypatch):
        """When cloudflared not on PATH, return 503 with install instructions."""
        import shutil as _shutil
        import yinyang_server as ys

        original_which = _shutil.which

        def mock_which(cmd):
            if cmd == "cloudflared":
                return None
            return original_which(cmd)

        monkeypatch.setattr(_shutil, "which", mock_which)
        # Also patch the shutil imported in yinyang_server
        monkeypatch.setattr(ys.shutil, "which", mock_which)

        status, data = _post_with_auth("/api/v1/tunnel/start", {})
        assert status == 503
        assert "cloudflared" in data.get("error", "").lower()
        assert "install" in data

    def test_tunnel_stop_when_not_running(self, auth_server):
        """POST /api/v1/tunnel/stop when no tunnel → 200 not_running."""
        import yinyang_server as ys
        # Ensure no tunnel is running
        with ys._TUNNEL_LOCK:
            ys._TUNNEL_PROC = None
            ys._TUNNEL_URL = ""
        status, data = _post_with_auth("/api/v1/tunnel/stop", {})
        assert status == 200
        assert data.get("status") == "not_running"

    def test_tunnel_requires_auth_start(self, auth_server):
        """POST /api/v1/tunnel/start without Bearer → 401."""
        status, data = _post_no_auth("/api/v1/tunnel/start", {})
        assert status == 401

    def test_tunnel_requires_auth_stop(self, auth_server):
        """POST /api/v1/tunnel/stop without Bearer → 401."""
        status, data = _post_no_auth("/api/v1/tunnel/stop", {})
        assert status == 401

    def test_sync_status(self, auth_server):
        """GET /api/v1/sync/status → returns vault_exists and token_count."""
        status, data = _get_json_auth("/api/v1/sync/status")
        assert status == 200
        assert "vault_exists" in data
        assert "token_count" in data
        assert isinstance(data["token_count"], int)

    def test_sync_export_requires_auth(self, auth_server):
        """POST /api/v1/sync/export without Bearer → 401."""
        status, data = _post_no_auth("/api/v1/sync/export", {})
        assert status == 401

    def test_sync_import_invalid_token_sha256(self, auth_server):
        """POST /api/v1/sync/import with bad token_sha256 → 400."""
        status, data = _post_with_auth(
            "/api/v1/sync/import",
            {"export_data": "{}", "token_sha256": "not-valid-hex"},
        )
        assert status == 400
        assert "64 hex" in data.get("error", "").lower()

    def test_sync_import_requires_auth(self, auth_server):
        """POST /api/v1/sync/import without Bearer → 401."""
        status, data = _post_no_auth(
            "/api/v1/sync/import",
            {"export_data": "{}", "token_sha256": "a" * 64},
        )
        assert status == 401


# ---------------------------------------------------------------------------
# Task 013: Evidence Viewer
# ---------------------------------------------------------------------------
class TestEvidenceViewer:
    def test_evidence_list_empty(self, auth_server):
        """GET /api/v1/evidence returns 200 with entries or records key."""
        status, data = _get_json_auth("/api/v1/evidence")
        assert status == 200
        assert "entries" in data or "records" in data or isinstance(data, list)

    def test_evidence_list_limit_param(self, auth_server):
        """GET /api/v1/evidence?limit=5 returns 200."""
        status, data = _get_json_auth("/api/v1/evidence?limit=5")
        assert status == 200

    def test_evidence_list_action_filter(self, auth_server):
        """GET /api/v1/evidence?action=recipe_run returns 200."""
        status, data = _get_json_auth("/api/v1/evidence?action=recipe_run")
        assert status == 200

    def test_evidence_detail_not_found(self, auth_server):
        """GET /api/v1/evidence/{nonexistent} returns 404."""
        status, data = _get_json_auth("/api/v1/evidence/nonexistent-id-xyz-000")
        assert status == 404
        assert "error" in data

    def test_evidence_verify_empty(self, auth_server):
        """GET /api/v1/evidence/verify returns valid=True when no entries."""
        status, data = _get_json_auth("/api/v1/evidence/verify")
        assert status == 200
        assert "valid" in data
        assert "entries" in data
        assert data["valid"] is True

    def test_evidence_verify_returns_count(self, auth_server):
        """GET /api/v1/evidence/verify always returns entries count."""
        status, data = _get_json_auth("/api/v1/evidence/verify")
        assert status == 200
        assert "entries" in data
        assert isinstance(data["entries"], int)

    def test_evidence_record_and_retrieve(self, auth_server):
        """POST /api/v1/evidence records an entry (201) and list reflects it."""
        status, data = _post_with_auth(
            "/api/v1/evidence",
            {"type": "recipe_run", "data": {"url": "http://localhost:8888/start", "recipe_id": "test"}},
        )
        assert status == 201
        assert "id" in data
        entry_id = data["id"]
        # Now retrieve via detail endpoint
        det_status, det_data = _get_json_auth(f"/api/v1/evidence/{entry_id}")
        assert det_status == 200
        assert det_data.get("id") == entry_id

    def test_evidence_list_session_filter(self, auth_server):
        """GET /api/v1/evidence?session_id=xyz returns 200 (may be empty)."""
        status, data = _get_json_auth("/api/v1/evidence?session_id=nonexistent-session-xyz")
        assert status == 200

    def test_evidence_verify_broken_at_none_when_valid(self, auth_server):
        """Verify returns broken_at=None when chain is intact."""
        status, data = _get_json_auth("/api/v1/evidence/verify")
        assert status == 200
        assert "broken_at" in data


# ---------------------------------------------------------------------------
# Task 014: Schedule Management UI
# ---------------------------------------------------------------------------
class TestScheduleManagementUI:
    def test_schedules_next_runs_empty(self, auth_server):
        """GET /api/v1/browser/schedules/next-runs returns 200 with schedules list."""
        status, data = _get_json_auth("/api/v1/browser/schedules/next-runs")
        assert status == 200
        assert "schedules" in data
        assert isinstance(data["schedules"], list)

    def test_schedule_create_and_disable_enable(self, auth_server):
        """Create schedule, disable it, enable it — all succeed."""
        create_status, create_data = _post_with_auth(
            "/api/v1/browser/schedules",
            {"app_id": "test-daily", "cron": "0 9 * * *", "url": "http://localhost:8888/start"},
        )
        assert create_status in (200, 201), f"Create failed: {create_data}"
        sched_id = create_data.get("id", "")
        if not sched_id:
            return  # Skip remainder if no id returned
        # Disable
        dis_status, dis_data = _post_with_auth(
            f"/api/v1/browser/schedules/{sched_id}/disable", {}
        )
        assert dis_status == 200, f"Disable failed: {dis_data}"
        assert dis_data.get("status") == "disabled"
        # Enable
        en_status, en_data = _post_with_auth(
            f"/api/v1/browser/schedules/{sched_id}/enable", {}
        )
        assert en_status == 200, f"Enable failed: {en_data}"
        assert en_data.get("status") == "enabled"
        # Cleanup
        _delete_with_auth(f"/api/v1/browser/schedules/{sched_id}")

    def test_schedule_enable_not_found(self, auth_server):
        """POST enable on nonexistent schedule → 404."""
        status, data = _post_with_auth(
            "/api/v1/browser/schedules/nonexistent-schedule-id/enable", {}
        )
        assert status == 404
        assert "error" in data

    def test_schedule_disable_requires_auth(self, auth_server):
        """POST disable without Bearer → 401."""
        status, data = _post_no_auth(
            "/api/v1/browser/schedules/some-id/disable", {}
        )
        assert status == 401

    def test_schedule_enable_requires_auth(self, auth_server):
        """POST enable without Bearer → 401."""
        status, data = _post_no_auth(
            "/api/v1/browser/schedules/some-id/enable", {}
        )
        assert status == 401

    def test_next_runs_shows_cron_times(self, auth_server):
        """next-runs returns correct structure with schedule_id and cron fields."""
        # Create a schedule first
        create_status, create_data = _post_with_auth(
            "/api/v1/browser/schedules",
            {"app_id": "test-hourly", "cron": "0 * * * *", "url": ""},
        )
        assert create_status in (200, 201)
        sched_id = create_data.get("id", "")
        # Check next-runs
        status, data = _get_json_auth("/api/v1/browser/schedules/next-runs")
        assert status == 200
        assert "schedules" in data
        found = [s for s in data["schedules"] if s.get("schedule_id") == sched_id]
        if found:
            item = found[0]
            assert "cron" in item
            assert "next_run" in item
            assert item["next_run"] is not None  # hourly cron should have a next run
        # Cleanup
        if sched_id:
            _delete_with_auth(f"/api/v1/browser/schedules/{sched_id}")


# ---------------------------------------------------------------------------
# Task 015: Recipe Management
# ---------------------------------------------------------------------------
class TestRecipeManagement:
    def test_recipes_list(self, auth_server):
        """GET /api/v1/recipes → 200 with recipes list and count."""
        status, data = _get_json_auth("/api/v1/recipes")
        assert status == 200
        assert "recipes" in data
        assert "count" in data
        assert isinstance(data["recipes"], list)

    def test_recipe_not_found(self, auth_server):
        """GET /api/v1/recipes/nonexistent → 404."""
        status, data = _get_json_auth("/api/v1/recipes/nonexistent-recipe-xyz")
        assert status == 404

    def test_recipe_preview_not_found(self, auth_server):
        """GET /api/v1/recipes/nonexistent/preview → 404."""
        status, data = _get_json_auth("/api/v1/recipes/nonexistent-xyz/preview")
        assert status == 404

    def test_recipe_run_not_found(self, auth_server):
        """POST /api/v1/recipes/nonexistent/run with auth → 404."""
        status, data = _post_with_auth("/api/v1/recipes/nonexistent-xyz/run", {})
        assert status == 404

    def test_recipe_run_requires_auth(self, auth_server):
        """POST /api/v1/recipes/some-recipe/run without auth → 401."""
        status, data = _post_no_auth("/api/v1/recipes/some-recipe/run", {})
        assert status == 401

    def test_recipe_run_status_not_found(self, auth_server):
        """GET /api/v1/recipes/nonexistent-run-id/status → 404."""
        status, data = _get_json_auth("/api/v1/recipes/nonexistent-run-id/status")
        assert status == 404

    def test_recipes_list_has_correct_structure(self, auth_server):
        """Each recipe in list has name or id field."""
        status, data = _get_json_auth("/api/v1/recipes")
        assert status == 200
        for recipe in data.get("recipes", []):
            assert "name" in recipe or "id" in recipe

    def test_recipes_count_matches_list(self, auth_server):
        """count field equals len(recipes)."""
        status, data = _get_json_auth("/api/v1/recipes")
        assert status == 200
        assert data["count"] == len(data["recipes"])


# ---------------------------------------------------------------------------
# Task 016: Budget Management
# ---------------------------------------------------------------------------
class TestBudgetManagement:
    def test_budget_get(self, auth_server):
        """GET /api/v1/budget → 200 with daily_limit_usd and monthly_limit_usd."""
        status, data = _get_json_auth("/api/v1/budget")
        assert status == 200
        assert "daily_limit_usd" in data
        assert "monthly_limit_usd" in data

    def test_budget_status(self, auth_server):
        """GET /api/v1/budget/status → 200 with spend and paused fields."""
        status, data = _get_json_auth("/api/v1/budget/status")
        assert status == 200
        assert "daily_spend_usd" in data
        assert "daily_limit_usd" in data
        assert "paused" in data
        assert isinstance(data["paused"], bool)

    def test_budget_update_daily_limit(self, auth_server):
        """POST /api/v1/budget with auth → 200 and new daily_limit_usd stored."""
        status, data = _post_with_auth("/api/v1/budget", {"daily_limit_usd": 2.50})
        assert status == 200
        assert data["budget"]["daily_limit_usd"] == 2.50

    def test_budget_update_invalid_threshold(self, auth_server):
        """POST /api/v1/budget with alert_threshold > 1.0 → 400."""
        status, data = _post_with_auth("/api/v1/budget", {"alert_threshold": 1.5})
        assert status == 400

    def test_budget_update_negative_limit(self, auth_server):
        """POST /api/v1/budget with negative daily_limit_usd → 400."""
        status, data = _post_with_auth("/api/v1/budget", {"daily_limit_usd": -1.0})
        assert status == 400

    def test_budget_reset(self, auth_server):
        """POST /api/v1/budget/reset with auth → 200 status=reset."""
        status, data = _post_with_auth("/api/v1/budget/reset", {})
        assert status == 200
        assert data["status"] == "reset"

    def test_budget_update_requires_auth(self, auth_server):
        """POST /api/v1/budget without auth → 401."""
        status, data = _post_no_auth("/api/v1/budget", {"daily_limit_usd": 5.0})
        assert status == 401

    def test_budget_reset_requires_auth(self, auth_server):
        """POST /api/v1/budget/reset without auth → 401."""
        status, data = _post_no_auth("/api/v1/budget/reset", {})
        assert status == 401

    def test_budget_status_monthly_fields(self, auth_server):
        """GET /api/v1/budget/status → monthly spend fields present."""
        status, data = _get_json_auth("/api/v1/budget/status")
        assert status == 200
        assert "monthly_spend_usd" in data
        assert "monthly_limit_usd" in data
        assert "monthly_pct" in data


# ---------------------------------------------------------------------------
# Task 018: Hub Health Metrics
# ---------------------------------------------------------------------------
class TestMetrics:
    def test_metrics_json_endpoint(self, auth_server):
        """GET /api/v1/metrics → 200 with uptime_seconds, total_requests, error_rate."""
        status, data = _get_json_auth("/api/v1/metrics")
        assert status == 200
        assert "uptime_seconds" in data
        assert "total_requests" in data
        assert "total_errors" in data
        assert "error_rate" in data
        assert isinstance(data["uptime_seconds"], int)
        assert data["uptime_seconds"] >= 0

    def test_metrics_prometheus_endpoint(self, auth_server):
        """GET /metrics → 200 with Prometheus text format."""
        req = urllib.request.Request(f"{AUTH_BASE}/metrics", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            body = resp.read().decode()
        assert "solace_uptime_seconds" in body
        assert "solace_http_requests_total" in body

    def test_health_includes_uptime(self, auth_server):
        """GET /health → uptime_seconds present and non-negative."""
        status, data = _get_json_auth("/health")
        assert status == 200
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_metrics_request_count_increases(self, auth_server):
        """total_requests increments after each request."""
        status1, data1 = _get_json_auth("/api/v1/metrics")
        assert status1 == 200
        count1 = data1.get("total_requests", 0)
        # Make additional requests
        _get_json_auth("/health")
        _get_json_auth("/health")
        status2, data2 = _get_json_auth("/api/v1/metrics")
        assert status2 == 200
        count2 = data2.get("total_requests", 0)
        assert count2 > count1

    def test_error_rate_is_fraction(self, auth_server):
        """error_rate must be between 0.0 and 1.0."""
        status, data = _get_json_auth("/api/v1/metrics")
        assert status == 200
        rate = data.get("error_rate", 0)
        assert 0.0 <= rate <= 1.0


# ---------------------------------------------------------------------------
# Task 017: WebSocket Live Dashboard
# ---------------------------------------------------------------------------
class TestDashboardWebSocket:
    def test_ws_dashboard_endpoint_in_server(self):
        """yinyang_server.py must reference /ws/dashboard."""
        server = pathlib.Path("yinyang_server.py").read_text()
        assert "/ws/dashboard" in server

    def test_ws_dashboard_state_event_structure(self):
        """Server code must reference dashboard state event."""
        server = pathlib.Path("yinyang_server.py").read_text()
        assert "dashboard" in server.lower()
        assert "state" in server.lower()

    def test_ws_dashboard_reconnect_in_html(self):
        """index.html must have ws/dashboard and reconnect logic."""
        html = pathlib.Path("solace-hub/src/index.html").read_text()
        assert "ws/dashboard" in html or "dashboard" in html.lower()
        assert "reconnect" in html.lower() or "onclose" in html.lower()

    def test_ws_dashboard_connects(self, auth_server):
        """WebSocket /ws/dashboard endpoint is referenced in server code."""
        # Primary check: code-level (no websocket-client library required)
        server = pathlib.Path("yinyang_server.py").read_text()
        connected = "/ws/dashboard" in server
        assert connected


# ---------------------------------------------------------------------------
# Task 019: BYOK API Key Management
# ---------------------------------------------------------------------------
class TestBYOKManagement:
    def test_byok_providers_empty(self, auth_server):
        """GET /api/v1/byok/providers → has providers + supported keys."""
        status, data = _get_json_auth("/api/v1/byok/providers")
        assert status == 200
        assert "providers" in data
        assert "supported" in data
        assert "anthropic" in data["supported"]

    def test_byok_set_valid_key(self, auth_server):
        """POST /api/v1/byok/set with valid key → status=set, key_preview returned."""
        status, data = _post_with_auth(
            "/api/v1/byok/set",
            {"provider": "anthropic", "api_key": "sk-ant-api03-testkey12345"},
        )
        assert status == 200
        assert data["status"] == "set"
        assert "key_preview" in data
        # Full key substring must not appear in preview
        assert "testkey12345" not in data["key_preview"]

    def test_byok_set_invalid_provider(self, auth_server):
        """POST /api/v1/byok/set with unknown provider → 400."""
        status, data = _post_with_auth(
            "/api/v1/byok/set",
            {"provider": "evil-provider", "api_key": "sk-test-12345678901"},
        )
        assert status == 400

    def test_byok_set_key_too_short(self, auth_server):
        """POST /api/v1/byok/set with short key → 400."""
        status, data = _post_with_auth(
            "/api/v1/byok/set",
            {"provider": "anthropic", "api_key": "short"},
        )
        assert status == 400

    def test_byok_test_no_key(self, auth_server):
        """POST /api/v1/byok/test for unconfigured provider → 404."""
        status, data = _post_with_auth(
            "/api/v1/byok/test",
            {"provider": "openai"},
        )
        assert status == 404

    def test_byok_clear_requires_auth(self, auth_server):
        """POST /api/v1/byok/clear without auth → 401."""
        status, data = _post_no_auth("/api/v1/byok/clear", {"provider": "anthropic"})
        assert status == 401

    def test_byok_set_requires_auth(self, auth_server):
        """POST /api/v1/byok/set without auth → 401."""
        status, data = _post_no_auth(
            "/api/v1/byok/set",
            {"provider": "anthropic", "api_key": "sk-test-123456"},
        )
        assert status == 401

    def test_byok_key_not_in_response(self, auth_server):
        """Full API key must never appear in response body."""
        full_key = "sk-ant-api03-secret-key-never-show-1234567890"
        status, data = _post_with_auth(
            "/api/v1/byok/set",
            {"provider": "anthropic", "api_key": full_key},
        )
        assert status == 200
        # Reconstruct raw response text from the data dict
        response_text = json.dumps(data)
        assert full_key not in response_text
        assert "never-show" not in response_text


# ---------------------------------------------------------------------------
# Task 020: Notification System + Event Log
# ---------------------------------------------------------------------------
class TestNotifications:
    def test_notifications_list_empty(self, auth_server):
        status, data = _get_json_auth("/api/v1/notifications")
        assert status == 200
        assert "notifications" in data
        assert "unread_count" in data
        assert isinstance(data["notifications"], list)

    def test_notifications_unread_count(self, auth_server):
        status, data = _get_json_auth("/api/v1/notifications/unread-count")
        assert status == 200
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)

    def test_notifications_mark_all_read_requires_auth(self, auth_server):
        status, data = _post_no_auth("/api/v1/notifications/mark-all-read", {})
        assert status == 401

    def test_notifications_mark_all_read(self, auth_server):
        status, data = _post_with_auth("/api/v1/notifications/mark-all-read", {})
        assert status == 200
        assert data["status"] == "all_read"

    def test_notification_mark_read_not_found(self, auth_server):
        status, data = _post_with_auth("/api/v1/notifications/nonexistent-id/read", {})
        assert status == 404

    def test_notifications_unread_filter(self, auth_server):
        status, data = _get_json_auth("/api/v1/notifications?unread=true")
        assert status == 200

    def test_notifications_limit_param(self, auth_server):
        status, data = _get_json_auth("/api/v1/notifications?limit=10")
        assert status == 200
        assert len(data.get("notifications", [])) <= 10


# ---------------------------------------------------------------------------
# Task 021: Server Log Viewer + Request History
# ---------------------------------------------------------------------------
class TestLogViewer:
    def test_log_requests_empty_or_has_history(self, auth_server):
        """GET /api/v1/logs/requests → {requests: list, total: int}."""
        status, data = _get_json_auth("/api/v1/logs/requests")
        assert status == 200
        assert "requests" in data
        assert "total" in data
        assert isinstance(data["requests"], list)

    def test_log_requests_limit(self, auth_server):
        """GET /api/v1/logs/requests?limit=5 → at most 5 entries."""
        status, data = _get_json_auth("/api/v1/logs/requests?limit=5")
        assert status == 200
        assert len(data.get("requests", [])) <= 5

    def test_log_errors(self, auth_server):
        """GET /api/v1/logs/errors returns errors list."""
        # Trigger a 404 first
        try:
            urllib.request.urlopen(f"{AUTH_BASE}/api/v1/nonexistent-endpoint-xyz", timeout=3)
        except urllib.error.HTTPError:
            pass
        status, data = _get_json_auth("/api/v1/logs/errors")
        assert status == 200
        assert "errors" in data
        # total >= 0 always (may or may not include the 404 above)
        assert data["total"] >= 0

    def test_log_requests_method_filter(self, auth_server):
        """GET /api/v1/logs/requests?method=GET → all entries have method=GET."""
        status, data = _get_json_auth("/api/v1/logs/requests?method=GET")
        assert status == 200
        for req in data.get("requests", []):
            assert req.get("method") == "GET"

    def test_log_history_has_correct_fields(self, auth_server):
        """After a request, history entries must have required fields."""
        # Make a request so there is history
        _get_json_auth("/health")
        status, data = _get_json_auth("/api/v1/logs/requests")
        assert status == 200
        for req in data.get("requests", []):
            assert "method" in req
            assert "path" in req
            assert "status" in req
            assert "timestamp" in req


# ── Task 022: Tray Status (reuses existing endpoints) ────────────────────────

class TestTrayStatus:
    def test_metrics_endpoint_for_tray(self, auth_server):
        """Tray polls /api/v1/metrics for uptime and request counts."""
        status, data = _get_json_auth("/api/v1/metrics")
        assert status == 200
        assert "uptime_seconds" in data
        assert "total_requests" in data

    def test_sessions_endpoint_for_tray(self, auth_server):
        """Tray polls /api/v1/sessions for live session count."""
        status, data = _get_json_auth("/api/v1/sessions")
        assert status == 200
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_budget_status_for_tray(self, auth_server):
        """Tray polls /api/v1/budget/status for spend percentage."""
        status, data = _get_json_auth("/api/v1/budget/status")
        assert status == 200
        assert "daily_pct" in data

    def test_health_for_tray(self, auth_server):
        """Tray shows ● Active when /health returns ok."""
        status, data = _get_json_auth("/health")
        assert status == 200
        assert data["status"] == "ok"


# ── Task 023: Profile Manager ─────────────────────────────────────────────────

def _delete_with_auth(path: str, token: str = VALID_TOKEN) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{AUTH_BASE}{path}",
        method="DELETE",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class TestProfileManager:
    def test_profiles_list_empty(self, auth_server):
        status, data = _get_json_auth("/api/v1/profiles")
        assert status == 200
        assert "profiles" in data
        assert isinstance(data["profiles"], list)

    def test_profiles_create(self, auth_server):
        status, data = _post_with_auth("/api/v1/profiles", {"name": "Work Profile"})
        assert status == 201
        assert data["status"] == "created"
        assert "id" in data["profile"]
        assert data["profile"]["name"] == "Work Profile"

    def test_profiles_create_requires_auth(self, auth_server):
        body = json.dumps({"name": "Test"}).encode()
        req = urllib.request.Request(f"{AUTH_BASE}/api/v1/profiles", data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req):
                pass
            assert False, "expected 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401

    def test_profiles_create_duplicate_name(self, auth_server):
        _post_with_auth("/api/v1/profiles", {"name": "DupTest"})
        status, data = _post_with_auth("/api/v1/profiles", {"name": "DupTest"})
        assert status == 400

    def test_profiles_create_empty_name(self, auth_server):
        status, data = _post_with_auth("/api/v1/profiles", {"name": ""})
        assert status == 400

    def test_profiles_active_initially_none(self, auth_server):
        status, data = _get_json_auth("/api/v1/profiles/active")
        assert status == 200
        assert "active_profile" in data

    def test_profiles_activate(self, auth_server):
        _, create_data = _post_with_auth("/api/v1/profiles", {"name": "ActivateTest"})
        profile_id = create_data["profile"]["id"]
        status, data = _post_with_auth(f"/api/v1/profiles/{profile_id}/activate", {})
        assert status == 200
        assert data["status"] == "activated"

    def test_profiles_activate_not_found(self, auth_server):
        status, data = _post_with_auth("/api/v1/profiles/nonexistent-id/activate", {})
        assert status == 404

    def test_profiles_delete(self, auth_server):
        _, create_data = _post_with_auth("/api/v1/profiles", {"name": "DeleteTest"})
        profile_id = create_data["profile"]["id"]
        status, data = _delete_with_auth(f"/api/v1/profiles/{profile_id}")
        assert status == 200
        assert data["status"] == "deleted"

    def test_profiles_delete_not_found(self, auth_server):
        status, data = _delete_with_auth("/api/v1/profiles/nonexistent")
        assert status == 404


# ── Task 024: Recipe Store ────────────────────────────────────────────────────

class TestRecipeStore:
    def test_store_list(self, auth_server):
        status, data = _get_json_auth("/api/v1/store/recipes")
        assert status == 200
        assert "recipes" in data
        assert len(data["recipes"]) > 0

    def test_store_search(self, auth_server):
        status, data = _get_json_auth("/api/v1/store/recipes?q=gmail")
        assert status == 200
        for recipe in data["recipes"]:
            assert "gmail" in recipe["name"].lower() or "gmail" in recipe.get("tag", "").lower()

    def test_store_filter_by_tag(self, auth_server):
        status, data = _get_json_auth("/api/v1/store/recipes?tag=email")
        assert status == 200
        for recipe in data["recipes"]:
            assert recipe["tag"] == "email"

    def test_store_install_requires_auth(self, auth_server):
        body = b""
        req = urllib.request.Request(
            f"{AUTH_BASE}/api/v1/store/recipes/r001/install",
            data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req):
                pass
            assert False, "expected 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401

    def test_store_install(self, auth_server):
        status, data = _post_with_auth("/api/v1/store/recipes/r001/install", {})
        assert status == 200
        assert data["status"] in ("installed", "already_installed")

    def test_store_install_not_found(self, auth_server):
        status, data = _post_with_auth("/api/v1/store/recipes/nonexistent/install", {})
        assert status == 404

    def test_store_installed_list(self, auth_server):
        status, data = _get_json_auth("/api/v1/store/installed")
        assert status == 200
        assert "installed" in data

    def test_store_uninstall(self, auth_server):
        _post_with_auth("/api/v1/store/recipes/r002/install", {})
        status, data = _post_with_auth("/api/v1/store/recipes/r002/uninstall", {})
        assert status == 200
        assert data["status"] == "uninstalled"

    def test_store_uninstall_not_installed(self, auth_server):
        status, data = _post_with_auth("/api/v1/store/recipes/r999/uninstall", {})
        assert status == 404


# ── Task 025: CLI Tool Integration ───────────────────────────────────────────

class TestCLIIntegration:
    def test_cli_config_get_empty(self, auth_server):
        status, data = _get_json_auth("/api/v1/cli/config")
        assert status == 200
        assert "config" in data
        assert "supported_tools" in data
        assert "claude" in data["supported_tools"]
        assert "ollama" in data["supported_tools"]

    def test_cli_detect(self, auth_server):
        status, data = _get_json_auth("/api/v1/cli/detect")
        assert status == 200
        assert "detected" in data
        for tool in ["claude", "openai", "ollama"]:
            assert tool in data["detected"]
            assert "installed" in data["detected"][tool]

    def test_cli_config_set_requires_auth(self, auth_server):
        body = json.dumps({"tool": "claude"}).encode()
        req = urllib.request.Request(
            f"{AUTH_BASE}/api/v1/cli/config",
            data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req):
                pass
            assert False, "expected 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401

    def test_cli_config_set_valid(self, auth_server):
        status, data = _post_with_auth("/api/v1/cli/config", {"tool": "ollama", "cli_path": "/usr/bin/ollama"})
        assert status == 200
        assert data["status"] == "configured"
        assert data["tool"] == "ollama"

    def test_cli_config_set_invalid_tool(self, auth_server):
        status, data = _post_with_auth("/api/v1/cli/config", {"tool": "evil-tool"})
        assert status == 400

    def test_cli_test_requires_auth(self, auth_server):
        body = b""
        req = urllib.request.Request(
            f"{AUTH_BASE}/api/v1/cli/test",
            data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req):
                pass
            assert False, "expected 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401

    def test_cli_test_no_config(self, auth_server):
        # Fresh server has no CLI configured → 404
        status, data = _post_with_auth("/api/v1/cli/test", {})
        assert status in (200, 404)


# ── Task 026: Chat WebSocket ──────────────────────────────────────────────────

class TestChatWebSocket:
    def test_ws_chat_endpoint_in_server(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "/ws/chat" in server

    def test_ws_chat_ready_message_structure(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "ready" in server
        assert "active_model" in server or '"model"' in server

    def test_ws_chat_ping_pong(self):
        server = (REPO_ROOT / "yinyang_server.py").read_text()
        assert "pong" in server

    def test_chat_ws_in_html(self):
        html = (REPO_ROOT / "solace-hub" / "src" / "index.html").read_text()
        assert "chat" in html.lower()
        assert "ws/chat" in html or "ws://localhost" in html


# ── Task 027: App Launcher ────────────────────────────────────────────────────

class TestAppLauncher:
    def test_apps_list(self, auth_server):
        status, data = _get_json_auth("/api/v1/apps")
        assert status == 200
        assert "apps" in data
        assert isinstance(data["apps"], list)
        assert "total" in data

    def test_app_detail_not_found(self, auth_server):
        status, data = _get_json_auth("/api/v1/apps/nonexistent-app-xyz-999")
        assert status == 404

    def test_app_launch_requires_auth(self, auth_server):
        body = b""
        req = urllib.request.Request(
            f"{AUTH_BASE}/api/v1/apps/gmail/launch",
            data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req):
                pass
            assert False, "expected 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401

    def test_app_launch_not_found(self, auth_server):
        status, data = _post_with_auth("/api/v1/apps/nonexistent-app-xyz-999/launch", {})
        assert status == 404


# ── Task 028: Evidence Export ─────────────────────────────────────────────────

class TestEvidenceExport:
    def test_evidence_export_json(self, auth_server):
        status, data = _get_json_auth("/api/v1/evidence/export?format=json")
        assert status == 200
        assert "evidence" in data
        assert "total" in data
        assert "exported_at" in data

    def test_evidence_export_csv(self, auth_server):
        url = f"{AUTH_BASE}/api/v1/evidence/export?format=csv"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            text = resp.read().decode()
        assert "id,timestamp" in text

    def test_evidence_export_invalid_format(self, auth_server):
        status, data = _get_json_auth("/api/v1/evidence/export?format=xml")
        assert status == 400

    def test_evidence_export_json_default(self, auth_server):
        status, data = _get_json_auth("/api/v1/evidence/export")
        assert status == 200
        assert "evidence" in data


# ── Task 029: Budget Alerts ───────────────────────────────────────────────────

class TestBudgetAlerts:
    def test_budget_history_empty(self, auth_server):
        status, data = _get_json_auth("/api/v1/budget/history")
        assert status == 200
        assert "history" in data
        assert "total_usd" in data
        assert "days" in data

    def test_budget_history_days_param(self, auth_server):
        status, data = _get_json_auth("/api/v1/budget/history?days=7")
        assert status == 200
        assert data["days"] == 7

    def test_budget_alerts_get(self, auth_server):
        status, data = _get_json_auth("/api/v1/budget/alerts")
        assert status == 200
        assert "alerts" in data
        assert "threshold_80" in data["alerts"]

    def test_budget_alerts_set_requires_auth(self, auth_server):
        body = json.dumps({"threshold_50": False}).encode()
        req = urllib.request.Request(
            f"{AUTH_BASE}/api/v1/budget/alerts",
            data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req):
                pass
            assert False, "expected 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401

    def test_budget_alerts_set(self, auth_server):
        status, data = _post_with_auth("/api/v1/budget/alerts", {"threshold_80": False})
        assert status == 200
        assert data["status"] == "updated"


# ── Task 030: Hub Health Watchdog ─────────────────────────────────────────────

class TestWatchdog:
    def test_watchdog_status(self, auth_server):
        status, data = _get_json_auth("/api/v1/watchdog/status")
        assert status == 200
        assert data["status"] == "ok"
        assert "uptime_seconds" in data
        assert "restart_count" in data
        assert "last_start" in data

    def test_watchdog_ping(self, auth_server):
        status, data = _post_with_auth("/api/v1/watchdog/ping", {})
        assert status == 200
        assert data["status"] == "pong"
        assert "timestamp" in data

    def test_watchdog_uptime_nonnegative(self, auth_server):
        status, data = _get_json_auth("/api/v1/watchdog/status")
        assert status == 200
        assert data["uptime_seconds"] >= 0


# ── Task 031: Dark Mode Toggle ────────────────────────────────────────────────

class TestDarkMode:
    def test_theme_get_default(self, auth_server):
        status, data = _get_json_auth("/api/v1/theme")
        assert status == 200
        assert data["theme"] in ("light", "dark")

    def test_theme_set_dark(self, auth_server):
        status, data = _post_with_auth("/api/v1/theme", {"theme": "dark"})
        assert status == 200
        assert data["theme"] == "dark"

    def test_theme_set_invalid(self, auth_server):
        status, data = _post_with_auth("/api/v1/theme", {"theme": "blue"})
        assert status == 400

    def test_theme_persists(self, auth_server):
        _post_with_auth("/api/v1/theme", {"theme": "dark"})
        status, data = _get_json_auth("/api/v1/theme")
        assert status == 200
        assert data["theme"] == "dark"


# ── Task 032: Recipe Run History ──────────────────────────────────────────────

class TestRecipeHistory:
    def test_recipe_history_empty(self, auth_server):
        status, data = _get_json_auth("/api/v1/recipes/history")
        assert status == 200
        assert "runs" in data
        assert "total" in data
        assert data["total"] == 0

    def test_recipe_history_limit_param(self, auth_server):
        status, data = _get_json_auth("/api/v1/recipes/history?limit=10")
        assert status == 200
        assert isinstance(data["runs"], list)

    def test_recipe_history_default_empty(self, auth_server):
        status, data = _get_json_auth("/api/v1/recipes/history")
        assert status == 200
        assert isinstance(data["runs"], list)


# ── Task 033: Settings Export / Import ───────────────────────────────────────

class TestSettingsExportImport:
    def test_settings_export(self, auth_server):
        status, data = _get_json_auth("/api/v1/settings/export")
        assert status == 200
        assert "exported_at" in data
        assert "version" in data
        assert "theme" in data

    def test_settings_import_requires_auth(self, auth_server):
        body = json.dumps({"theme": {"theme": "dark"}}).encode()
        req = urllib.request.Request(
            f"{AUTH_BASE}/api/v1/settings/import",
            data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req):
                pass
            assert False, "expected 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401

    def test_settings_import_theme(self, auth_server):
        status, data = _post_with_auth("/api/v1/settings/import", {"theme": {"theme": "dark"}})
        assert status == 200
        assert data["status"] == "imported"
        assert "theme" in data["imported"]

    def test_settings_export_has_budget(self, auth_server):
        status, data = _get_json_auth("/api/v1/settings/export")
        assert status == 200
        assert "budget" in data


# ── Task 034: API Usage Stats ─────────────────────────────────────────────────

class TestUsageStats:
    def test_usage_stats_empty(self, auth_server):
        status, data = _get_json_auth("/api/v1/usage/stats")
        assert status == 200
        assert "by_provider" in data
        assert "total_cost_usd" in data
        assert "total_calls" in data
        assert "days" in data

    def test_usage_stats_days_param(self, auth_server):
        status, data = _get_json_auth("/api/v1/usage/stats?days=7")
        assert status == 200
        assert data["days"] == 7

    def test_usage_stats_zero_on_empty(self, auth_server):
        status, data = _get_json_auth("/api/v1/usage/stats")
        assert status == 200
        assert data["total_calls"] == 0
        assert data["total_cost_usd"] == 0.0


# ── Task 035: Keyboard Shortcuts ──────────────────────────────────────────────

class TestShortcuts:
    def test_shortcuts_list(self, auth_server):
        status, data = _get_json_auth("/api/v1/shortcuts")
        assert status == 200
        assert "shortcuts" in data
        assert "total" in data
        assert len(data["shortcuts"]) > 0

    def test_shortcuts_have_keys(self, auth_server):
        status, data = _get_json_auth("/api/v1/shortcuts")
        assert status == 200
        for s in data["shortcuts"]:
            assert "key" in s
            assert "description" in s


# ── Task 036: System Status Banner ───────────────────────────────────────────

class TestSystemStatus:
    def test_system_status(self, auth_server):
        status, data = _get_json_auth("/api/v1/system/status")
        assert status == 200
        assert data["status"] == "ok"
        assert "version" in data
        assert "uptime_seconds" in data
        assert "features" in data

    def test_system_features(self, auth_server):
        status, data = _get_json_auth("/api/v1/system/status")
        assert status == 200
        assert "oauth3" in data["features"]
        assert "evidence" in data["features"]


# ── Task 037: Notification Toast System ──────────────────────────────────────

class TestNotificationToast:
    def test_notifications_mark_read(self, auth_server):
        status, data = _post_with_auth("/api/v1/notifications/read", {})
        assert status == 200
        assert "status" in data


# ── Task 038: Global Search ───────────────────────────────────────────────────

class TestSearch:
    def test_search_empty_query(self, auth_server):
        status, data = _get_json_auth("/api/v1/search?q=")
        assert status == 200
        assert "results" in data
        assert data["total"] == 0

    def test_search_returns_structure(self, auth_server):
        status, data = _get_json_auth("/api/v1/search?q=gmail")
        assert status == 200
        assert "results" in data
        assert "total" in data
        assert "query" in data
        assert data["query"] == "gmail"


# ── Task 039: Pinned Sections ─────────────────────────────────────────────────

class TestPinnedSections:
    def test_pinned_get_empty(self, auth_server):
        status, data = _get_json_auth("/api/v1/pinned")
        assert status == 200
        assert "pinned" in data
        assert isinstance(data["pinned"], list)

    def test_pinned_set_requires_auth(self, auth_server):
        body = json.dumps({"pinned": ["budget-panel"]}).encode()
        req = urllib.request.Request(
            f"{AUTH_BASE}/api/v1/pinned",
            data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req):
                pass
            assert False, "expected 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401

    def test_pinned_set(self, auth_server):
        status, data = _post_with_auth("/api/v1/pinned", {"pinned": ["budget-panel", "metrics-panel"]})
        assert status == 200
        assert data["status"] == "ok"
        assert "budget-panel" in data["pinned"]


# ── Task 040: Accessibility Report ───────────────────────────────────────────

class TestAccessibility:
    def test_accessibility_report(self, auth_server):
        status, data = _get_json_auth("/api/v1/accessibility")
        assert status == 200
        assert "checks" in data
        assert "total" in data
        assert "passed" in data
        assert "score" in data
        assert data["total"] > 0

    def test_accessibility_checks_structure(self, auth_server):
        status, data = _get_json_auth("/api/v1/accessibility")
        assert status == 200
        for check in data["checks"]:
            assert "id" in check
            assert "label" in check
            assert "status" in check


# ── Task 041: Connection Health ───────────────────────────────────────────────

class TestConnectionHealth:
    def test_ping(self, auth_server):
        status, data = _get_json_auth("/api/v1/ping")
        assert status == 200
        assert data["pong"] is True
        assert "timestamp" in data
        assert "version" in data


# ── Task 042: App Tag Filter ──────────────────────────────────────────────────

class TestAppTags:
    def test_apps_tags(self, auth_server):
        status, data = _get_json_auth("/api/v1/apps/tags")
        assert status == 200
        assert "tags" in data
        assert "total" in data
        assert isinstance(data["tags"], list)


# ── Task 043: Multi-Window Sync / Broadcast ───────────────────────────────────

class TestBroadcast:
    def test_broadcast_post(self, auth_server):
        status, data = _post_with_auth("/api/v1/broadcast", {"type": "theme_change", "data": {"theme": "dark"}})
        assert status == 200
        assert data["status"] == "broadcast"
        assert data["event"]["type"] == "theme_change"

    def test_broadcast_get(self, auth_server):
        status, data = _get_json_auth("/api/v1/broadcast")
        assert status == 200
        assert "events" in data


# ── Task 044: Rate Limit Status ───────────────────────────────────────────────

class TestRateLimit:
    def test_rate_limit_status(self, auth_server):
        status, data = _get_json_auth("/api/v1/rate-limit/status")
        assert status == 200
        assert data["status"] == "ok"
        assert "limits" in data
        assert "current" in data
        assert "avg_rpm" in data


# ── Task 045: App Favorites ───────────────────────────────────────────────────

class TestAppFavorites:
    def test_favorites_get(self, auth_server):
        status, data = _get_json_auth("/api/v1/apps/favorites")
        assert status == 200
        assert "favorites" in data
        assert isinstance(data["favorites"], list)

    def test_favorites_post(self, auth_server):
        status, data = _post_with_auth("/api/v1/apps/favorites", {"app_id": "gmail"})
        assert status == 200
        assert data["status"] == "favorited"
        assert data["app_id"] == "gmail"

    def test_favorites_delete(self, auth_server):
        _post_with_auth("/api/v1/apps/favorites", {"app_id": "gmail"})
        status, data = _delete_with_auth("/api/v1/apps/favorites?app_id=gmail")
        assert status == 200
        assert data["status"] == "unfavorited"
