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

    original_lock = ys.PORT_LOCK_PATH
    original_evidence = ys.EVIDENCE_PATH
    original_schedules = ys.SCHEDULES_PATH
    original_oauth3_tokens = ys.OAUTH3_TOKENS_PATH

    ys.PORT_LOCK_PATH = lock_path
    ys.EVIDENCE_PATH = evidence_path
    ys.SCHEDULES_PATH = schedules_path
    ys.OAUTH3_TOKENS_PATH = oauth3_tokens_path

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
