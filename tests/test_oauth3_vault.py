"""OAuth3 vault API tests for Yinyang Server."""

import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TEST_PORT = 18891
BASE_URL = f"http://localhost:{TEST_PORT}"
VALID_TOKEN = "b" * 64


@pytest.fixture()
def oauth3_server(tmp_path):
    import yinyang_server as ys

    original_lock = ys.PORT_LOCK_PATH
    original_tokens = ys.OAUTH3_TOKENS_PATH
    original_vault = ys.OAUTH3_VAULT_PATH

    ys.PORT_LOCK_PATH = tmp_path / "port.lock"
    ys.OAUTH3_TOKENS_PATH = tmp_path / "oauth3-tokens.json"
    ys.OAUTH3_VAULT_PATH = tmp_path / "oauth3-vault.enc"

    httpd = ys.build_server(TEST_PORT, str(REPO_ROOT), session_token_sha256=VALID_TOKEN)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    for _ in range(30):
        try:
            urllib.request.urlopen(f"{BASE_URL}/health", timeout=1)
            break
        except urllib.error.URLError:
            time.sleep(0.1)

    yield {"httpd": httpd, "vault_path": ys.OAUTH3_VAULT_PATH, "module": ys}

    httpd.shutdown()
    httpd.server_close()
    ys.PORT_LOCK_PATH = original_lock
    ys.OAUTH3_TOKENS_PATH = original_tokens
    ys.OAUTH3_VAULT_PATH = original_vault


def _get_auth(path: str) -> tuple[int, object]:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _post_auth(path: str, payload: dict) -> tuple[int, object]:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {VALID_TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def test_issue_token_returns_token_id_not_raw_token(oauth3_server):
    status, data = _post_auth(
        "/api/v1/oauth3/token/issue",
        {"user_id": "alice@example.com", "scopes": ["gmail.read"], "ttl_seconds": 60},
    )
    assert status == 201
    assert "token_id" in data
    assert "raw_token" not in data
    assert data["scopes"] == ["gmail.read"]


def test_validate_token_checks_ttl(oauth3_server):
    _, issued = _post_auth(
        "/api/v1/oauth3/token/issue",
        {"user_id": "alice@example.com", "scopes": ["gmail.read"], "ttl_seconds": 1},
    )
    time.sleep(1.2)
    status, data = _get_auth(f"/api/v1/oauth3/token/validate?token_id={issued['token_id']}")
    assert status == 200
    assert data["valid"] is False


def test_revoke_token_is_immediate(oauth3_server):
    _, issued = _post_auth(
        "/api/v1/oauth3/token/issue",
        {"user_id": "alice@example.com", "scopes": ["gmail.read"], "ttl_seconds": 60},
    )
    status, revoked = _post_auth("/api/v1/oauth3/token/revoke", {"token_id": issued["token_id"]})
    assert status == 200
    assert revoked["revoked"] is True

    status, validated = _get_auth(f"/api/v1/oauth3/token/validate?token_id={issued['token_id']}")
    assert status == 200
    assert validated["valid"] is False
    assert validated["revoked"] is True


def test_high_risk_scope_triggers_step_up(oauth3_server):
    _, issued = _post_auth(
        "/api/v1/oauth3/token/issue",
        {"user_id": "alice@example.com", "scopes": ["linkedin.post"], "ttl_seconds": 60},
    )
    assert issued["step_up_required"] == ["linkedin.post"]

    status, step_up = _post_auth(
        "/api/v1/oauth3/step-up/request",
        {"token_id": issued["token_id"], "scope_needed": "linkedin.post"},
    )
    assert status == 200
    assert step_up["expires_in"] == 300
    assert "step_up_id" in step_up
    assert "consent_url" in step_up


def test_evidence_chain_is_hash_chained(oauth3_server):
    ys = oauth3_server["module"]

    _, issued = _post_auth(
        "/api/v1/oauth3/token/issue",
        {"user_id": "alice@example.com", "scopes": ["gmail.read", "linkedin.post"], "ttl_seconds": 60},
    )
    _get_auth(f"/api/v1/oauth3/token/validate?token_id={issued['token_id']}")
    _post_auth(
        "/api/v1/oauth3/step-up/request",
        {"token_id": issued["token_id"], "scope_needed": "linkedin.post"},
    )

    status, evidence = _get_auth("/api/v1/oauth3/evidence?limit=10")
    assert status == 200
    assert len(evidence) >= 3

    state = ys._oauth3_load_vault_state(VALID_TOKEN)
    previous_hash = ys.OAUTH3_EVIDENCE_GENESIS_HASH
    for entry in state["evidence"]:
        payload = {
            "event_type": entry["event_type"],
            "token_id": entry["token_id"],
            "scopes": entry["scopes"],
            "timestamp": entry["timestamp"],
            "previous_hash": entry["previous_hash"],
            "data": entry["data"],
        }
        event_sha256 = ys.hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        expected_link = ys.hashlib.sha256(f"{previous_hash}{event_sha256}".encode("utf-8")).hexdigest()
        assert entry["previous_hash"] == previous_hash
        assert entry["chain_link_sha256"] == expected_link
        previous_hash = expected_link
    assert state["chain_tip"] == previous_hash


def test_token_validate_after_revocation_returns_false(oauth3_server):
    _, issued = _post_auth(
        "/api/v1/oauth3/token/issue",
        {"user_id": "alice@example.com", "scopes": ["gmail.read"], "ttl_seconds": 60},
    )
    _post_auth("/api/v1/oauth3/token/revoke", {"token_id": issued["token_id"]})
    status, data = _get_auth(f"/api/v1/oauth3/token/validate?token_id={issued['token_id']}")
    assert status == 200
    assert data == {
        "valid": False,
        "scopes": ["gmail.read"],
        "expires_at": issued["expires_at"],
        "revoked": True,
    }


def test_vault_encrypted_at_rest(oauth3_server):
    status, issued = _post_auth(
        "/api/v1/oauth3/token/issue",
        {"user_id": "alice@example.com", "scopes": ["gmail.read"], "ttl_seconds": 60},
    )
    assert status == 201
    vault_text = oauth3_server["vault_path"].read_text()
    assert "gmail.read" not in vault_text
    assert issued["token_id"] not in vault_text
    assert "alice@example.com" not in vault_text


def test_tokens_list_no_raw_token_in_response(oauth3_server):
    _, issued = _post_auth(
        "/api/v1/oauth3/token/issue",
        {"user_id": "alice@example.com", "scopes": ["gmail.read"], "ttl_seconds": 60},
    )
    status, data = _get_auth("/api/v1/oauth3/tokens")
    assert status == 200
    assert isinstance(data, list)
    assert any(row["token_id"] == issued["token_id"] for row in data)
    for row in data:
        assert "raw_token" not in row
        assert "token_sha256" not in row
