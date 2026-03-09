"""
test_preview_cooldown_signoff.py — Preview → Cooldown → Sign-Off pipeline tests.
Donald Knuth law: every test is a proof. RED → GREEN gate.

Task 057 — Preview Mode + Cooldown + Sign-Off Orchestration
Port: 18888 (test-only)

Safety ladder:
  Class A — autonomous (read-only), no gate
  Class B — preview + 30min cooldown + sign-off
  Class C — preview + 2h cooldown + step-up + reason + sign-off
"""
import pathlib
import sys
import time

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yinyang_server as ys

TEST_PORT = 18889  # distinct from other test modules using 18888

_TOKEN = "test-token-preview-cooldown-057"


# ---------------------------------------------------------------------------
# Server fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("solace_preview")
    original_lock = ys.PORT_LOCK_PATH
    original_evidence = ys.EVIDENCE_PATH
    original_part11_dir = ys.PART11_EVIDENCE_DIR
    original_part11_path = ys.PART11_EVIDENCE_PATH
    original_chain_path = ys.PART11_CHAIN_LOCK_PATH
    original_pending = dict(ys._PENDING_ACTIONS)
    original_history = list(ys._ACTIONS_HISTORY)

    ys.PORT_LOCK_PATH = tmp / "port.lock"
    ys.EVIDENCE_PATH = tmp / "evidence.jsonl"
    ys.PART11_EVIDENCE_DIR = tmp / "part11"
    ys.PART11_EVIDENCE_PATH = ys.PART11_EVIDENCE_DIR / "evidence.jsonl"
    ys.PART11_CHAIN_LOCK_PATH = ys.PART11_EVIDENCE_DIR / "chain.lock"
    ys._PENDING_ACTIONS.clear()
    ys._ACTIONS_HISTORY.clear()

    token = _TOKEN
    t_hash = ys.token_hash(token)
    ys.write_port_lock(TEST_PORT, t_hash, 99999)

    yield {"token": token, "token_hash": t_hash}

    ys.PORT_LOCK_PATH = original_lock
    ys.EVIDENCE_PATH = original_evidence
    ys.PART11_EVIDENCE_DIR = original_part11_dir
    ys.PART11_EVIDENCE_PATH = original_part11_path
    ys.PART11_CHAIN_LOCK_PATH = original_chain_path
    ys._PENDING_ACTIONS.clear()
    ys._PENDING_ACTIONS.update(original_pending)
    ys._ACTIONS_HISTORY.clear()
    ys._ACTIONS_HISTORY.extend(original_history)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def token_hash_of(token: str) -> str:
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def _make_handler(path: str, method: str, payload: dict | None = None, token: str = _TOKEN):
    handler = object.__new__(ys.YinyangHandler)
    captured: dict = {"status": None, "data": None}
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token_hash_of(token)}"
    handler.headers = headers
    handler.path = path
    handler.command = method
    handler.client_address = ("127.0.0.1", TEST_PORT)
    handler.server = type("DummyServer", (), {"session_token_sha256": token_hash_of(token)})()
    handler._send_json = lambda data, status=200: captured.update({"status": status, "data": data})
    handler._read_json_body = lambda: payload
    return handler, captured


def post_json(path: str, payload: dict, token: str = _TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "POST", payload, token)
    handler.do_POST()
    return int(captured["status"]), dict(captured["data"])


def get_json(path: str, token: str = _TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "GET", None, token)
    handler.do_GET()
    return int(captured["status"]), dict(captured["data"])


def delete_json(path: str, token: str = _TOKEN) -> tuple[int, dict]:
    handler, captured = _make_handler(path, "DELETE", None, token)
    handler.do_DELETE()
    return int(captured["status"]), dict(captured["data"])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_class_a_action_executes_immediately(server):
    """Class A actions return can_execute_immediately=True, no cooldown."""
    status, data = post_json(
        "/api/v1/actions/preview",
        {"action_type": "gmail.read", "params": {}, "app_id": "gmail"},
        token=_TOKEN,
    )
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert data.get("class") == "A"
    assert data.get("can_execute_immediately") is True
    assert "cooldown_ends_at" not in data or data.get("cooldown_ends_at") is None


def test_class_b_requires_cooldown_30min(server):
    """Class B preview returns cooldown_ends_at = now + 1800s (30min)."""
    import time as _time

    before = _time.time()
    status, data = post_json(
        "/api/v1/actions/preview",
        {"action_type": "gmail.send", "params": {"to": "test@example.com"}, "app_id": "gmail"},
        token=_TOKEN,
    )
    assert status == 201, f"Expected 201, got {status}: {data}"
    assert data.get("class") == "B"
    assert data.get("can_execute_immediately") is False
    assert data.get("sign_off_required") is True
    assert "cooldown_ends_at" in data
    assert "action_id" in data
    assert data["preview"]["affected_resources"] == ["to"]
    assert data["preview"]["reversal_possible"] is True

    # cooldown must be ~30min from now (1800 seconds ± 5 seconds tolerance)
    cooldown_ts = data["cooldown_ends_at"]
    # parse ISO8601 — ends with Z
    import datetime
    dt = datetime.datetime.fromisoformat(cooldown_ts.replace("Z", "+00:00"))
    elapsed = dt.timestamp() - before
    assert 1795 <= elapsed <= 1810, f"Expected ~1800s cooldown, got {elapsed:.1f}s"


def test_class_c_requires_step_up_and_reason(server):
    """Class C approve without step_up_consent=True → 403 (after cooldown bypassed)."""
    import yinyang_server as ys
    import time as _time

    # First create a Class C preview
    status, preview = post_json(
        "/api/v1/actions/preview",
        {"action_type": "gmail.delete_batch", "params": {"count": 100}, "app_id": "gmail"},
        token=_TOKEN,
    )
    assert status == 201, f"Preview failed: {status}: {preview}"
    action_id = preview["action_id"]

    # Bypass cooldown so we can test the step-up gate
    with ys._PENDING_ACTIONS_LOCK:
        if action_id in ys._PENDING_ACTIONS:
            ys._PENDING_ACTIONS[action_id]["cooldown_ends_at"] = _time.time() - 1

    # Try approve WITHOUT step_up_consent → should be 403
    status, data = post_json(
        f"/api/v1/actions/{action_id}/approve",
        {"reason": "I intend to delete these emails"},
        token=_TOKEN,
    )
    assert status == 403, f"Expected 403, got {status}: {data}"
    assert data.get("error") == "step_up_required"


def test_approve_before_cooldown_returns_409(server):
    """Approve immediately after preview → 409 cooldown_active."""
    status, preview = post_json(
        "/api/v1/actions/preview",
        {"action_type": "linkedin.post", "params": {"text": "Hello world"}, "app_id": "linkedin"},
        token=_TOKEN,
    )
    assert status == 201, f"Preview failed: {status}: {preview}"
    action_id = preview["action_id"]

    # Immediately try to approve — cooldown not elapsed
    status, data = post_json(
        f"/api/v1/actions/{action_id}/approve",
        {},
        token=_TOKEN,
    )
    assert status == 409, f"Expected 409, got {status}: {data}"
    assert data.get("error") == "cooldown_active"
    assert "remaining_seconds" in data
    assert data["remaining_seconds"] > 0


def test_sign_off_creates_alcoa_evidence(server):
    """Approve after mocked cooldown creates evidence bundle with ALCOA+ fields."""
    import yinyang_server as ys
    import time as _time

    # Create Class B preview
    status, preview = post_json(
        "/api/v1/actions/preview",
        {"action_type": "twitter.post", "params": {"text": "Test tweet"}, "app_id": "twitter"},
        token=_TOKEN,
    )
    assert status == 201, f"Preview failed: {status}: {preview}"
    action_id = preview["action_id"]

    # Manually override cooldown_ends_at to now - 1 second (bypass cooldown for test)
    with ys._PENDING_ACTIONS_LOCK:
        if action_id in ys._PENDING_ACTIONS:
            ys._PENDING_ACTIONS[action_id]["cooldown_ends_at"] = _time.time() - 1

    # Now approve
    status, data = post_json(
        f"/api/v1/actions/{action_id}/approve",
        {},
        token=_TOKEN,
    )
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert data.get("approved") is True
    assert "evidence_bundle_id" in data

    # Verify evidence has ALCOA+ fields
    bundle_id = data["evidence_bundle_id"]
    # Check action history for the ALCOA record
    status, history = get_json("/api/v1/actions/history", token=_TOKEN)
    assert status == 200
    entries = history.get("actions", [])
    matching = [e for e in entries if e.get("action_id") == action_id]
    assert len(matching) == 1, f"Expected 1 history entry for action {action_id}, got {len(matching)}"
    entry = matching[0]
    assert entry.get("status") == "APPROVED"
    assert entry.get("evidence_bundle_id") == bundle_id
    assert entry.get("signature")
    assert entry.get("before_state_hash")
    assert entry.get("after_state_hash")
    assert entry.get("alcoa_attributable") is True
    assert entry.get("alcoa_contemporaneous") is True
    assert ys.PART11_EVIDENCE_PATH.exists() is True
    assert ys.EVIDENCE_PATH.exists() is True


def test_reject_seals_evidence_with_reason(server):
    """Reject stores reason in evidence and seals the action."""
    import yinyang_server as ys

    # Create Class B preview
    status, preview = post_json(
        "/api/v1/actions/preview",
        {"action_type": "slack.send_channel", "params": {"channel": "#general", "message": "Hi"}, "app_id": "slack"},
        token=_TOKEN,
    )
    assert status == 201, f"Preview failed: {status}: {preview}"
    action_id = preview["action_id"]

    # Reject it
    status, data = post_json(
        f"/api/v1/actions/{action_id}/reject",
        {"reason": "Not ready yet"},
        token=_TOKEN,
    )
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert data.get("rejected") is True
    assert data.get("evidence_bundle_id")

    # Verify it's no longer in pending
    status, pending = get_json("/api/v1/actions/pending", token=_TOKEN)
    assert status == 200
    pending_ids = [a["action_id"] for a in pending.get("actions", [])]
    assert action_id not in pending_ids

    # Verify history records the rejection with reason
    status, history = get_json("/api/v1/actions/history", token=_TOKEN)
    assert status == 200
    entries = history.get("actions", [])
    matching = [e for e in entries if e.get("action_id") == action_id]
    assert len(matching) == 1
    assert matching[0].get("status") == "REJECTED"
    assert matching[0].get("reject_reason") == "Not ready yet"
    assert matching[0].get("evidence_bundle_id") == data.get("evidence_bundle_id")


def test_pending_list_shows_cooldown_remaining(server):
    """GET /api/v1/actions/pending includes cooldown_remaining_seconds per action."""
    # Create a fresh Class B preview
    status, preview = post_json(
        "/api/v1/actions/preview",
        {"action_type": "github.comment", "params": {"pr": 42, "body": "LGTM"}, "app_id": "github"},
        token=_TOKEN,
    )
    assert status == 201, f"Preview failed: {status}: {preview}"
    action_id = preview["action_id"]

    status, data = get_json("/api/v1/actions/pending", token=_TOKEN)
    assert status == 200, f"Expected 200, got {status}: {data}"
    actions = data.get("actions", [])
    matching = [a for a in actions if a.get("action_id") == action_id]
    assert len(matching) == 1, f"action {action_id} not found in pending list"
    entry = matching[0]
    assert "cooldown_remaining_seconds" in entry
    assert entry.get("preview_summary")
    # Cooldown remaining should be close to 1800s
    remaining = entry["cooldown_remaining_seconds"]
    assert 1790 <= remaining <= 1805, f"Expected ~1800s remaining, got {remaining}"


def test_class_c_missing_reason_returns_400(server):
    """Class C approve with empty reason → 400."""
    import yinyang_server as ys
    import time as _time

    # Create Class C preview
    status, preview = post_json(
        "/api/v1/actions/preview",
        {"action_type": "payment.initiate", "params": {"amount": "100.00"}, "app_id": "payments"},
        token=_TOKEN,
    )
    assert status == 201, f"Preview failed: {status}: {preview}"
    action_id = preview["action_id"]

    # Manually bypass cooldown
    with ys._PENDING_ACTIONS_LOCK:
        if action_id in ys._PENDING_ACTIONS:
            ys._PENDING_ACTIONS[action_id]["cooldown_ends_at"] = _time.time() - 1

    # Try approve with step_up but empty reason → 400
    status, data = post_json(
        f"/api/v1/actions/{action_id}/approve",
        {"step_up_consent": True, "reason": ""},
        token=_TOKEN,
    )
    assert status == 400, f"Expected 400, got {status}: {data}"
    assert "reason" in data.get("error", "").lower()
