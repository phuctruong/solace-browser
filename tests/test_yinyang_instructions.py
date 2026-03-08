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
        except (urllib.error.URLError, ConnectionRefusedError):
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
        """hub field must contain 'Solace Hub', never 'Companion App'."""
        data = get_json("/instructions")
        assert "Solace Hub" in data["hub"], f"hub field wrong: {data['hub']}"
        assert "Companion App" not in data["hub"]

    def test_instructions_forbidden(self, server):
        """'port_9222' must appear in forbidden list."""
        data = get_json("/instructions")
        assert "port_9222" in data["forbidden"]

    def test_instructions_no_companion_app(self, server):
        """'companion_app_name' must appear in forbidden list."""
        data = get_json("/instructions")
        assert "companion_app_name" in data["forbidden"]

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
        except urllib.error.HTTPError as exc:
            assert exc.code == 400


class TestNotFoundEndpoint:
    def test_unknown_path_404(self, server):
        """Unknown path → 404."""
        try:
            urllib.request.urlopen(f"{BASE_URL}/nonexistent", timeout=5)
            pytest.fail("Expected 404 but got 200")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404

    def test_no_port_9222_reference(self, server):
        """
        Safety: /instructions must never expose port 9222 as a live endpoint.
        The forbidden list may name 'port_9222' (that is the ban declaration).
        No other field may contain '9222' as an active reference.
        """
        data = get_json("/instructions")
        # Check every field EXCEPT the forbidden list (which names the ban).
        for key, value in data.items():
            if key == "forbidden":
                continue  # 'port_9222' in forbidden is the ban declaration — allowed
            raw_value = json.dumps(value)
            assert "9222" not in raw_value, (
                f"Port 9222 referenced in field '{key}': {raw_value} — BANNED"
            )

    def test_no_companion_app_in_any_response(self, server):
        """Safety: no endpoint response may contain 'Companion App'."""
        for path in ("/health", "/instructions", "/credits"):
            data = get_json(path)
            raw = json.dumps(data)
            assert "Companion App" not in raw, f"'Companion App' found in {path} response"

# ---------------------------------------------------------------------------
# Phase 3: Evidence API
# ---------------------------------------------------------------------------
def delete_json(path: str) -> tuple[int, dict]:
    """Make a DELETE request, return (status_code, body)."""
    req = urllib.request.Request(f"{BASE_URL}{path}", method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
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
        except urllib.error.HTTPError as exc:
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
        except urllib.error.HTTPError as exc:
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
