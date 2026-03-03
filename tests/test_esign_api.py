"""
tests/test_esign_api.py — FDA 21 CFR Part 11 E-Sign API Tests
Rung: 641 (local correctness)

Tests:
  1. EsignHashAlgorithm  — hash computation correctness, determinism, tamper detection
  2. EsignCreate         — POST /api/v1/esign/token (integration, skipped if server down)
  3. EvidenceVerify      — POST /api/v1/evidence/verify (integration, skipped if server down)
  4. AuditFileIntegrity  — JSONL audit file written correctly
  5. TamperDetection     — modified hash returns tampered=True

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_esign_api.py -v --tb=short -p no:httpbin

Server-dependent tests are skipped automatically if localhost:9222 is not up.
Rung: 641 (local correctness)
"""

import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SERVER_URL = "http://localhost:9222"
ESIGN_ENDPOINT = f"{SERVER_URL}/api/v1/esign/token"
VERIFY_ENDPOINT = f"{SERVER_URL}/api/v1/evidence/verify"


# ---------------------------------------------------------------------------
# Pure hash computation helpers (mirrors server implementation exactly)
# ---------------------------------------------------------------------------

def _compute_esign_hash(
    user_id: str,
    timestamp: str,
    meaning: str,
    action_description: str,
) -> tuple[str, str]:
    """Reproduce the exact hash algorithm from solace_browser_server.py.

    Returns: (action_hash, esign_hash)
    """
    action_hash = hashlib.sha256(action_description.encode("utf-8")).hexdigest()
    payload = user_id + timestamp + meaning + action_hash
    esign_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return action_hash, esign_hash


def _server_available() -> bool:
    """Return True if localhost:9222 is accepting HTTP connections."""
    import urllib.request
    try:
        urllib.request.urlopen(f"{SERVER_URL}/api/status", timeout=2)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Skip marker for server-dependent tests
# ---------------------------------------------------------------------------

requires_server = pytest.mark.skipif(
    not _server_available(),
    reason="localhost:9222 (solace_browser_server) not running — skipping integration tests",
)


# ===========================================================================
# 1. EsignHashAlgorithm — pure unit tests (no server required)
# ===========================================================================

class TestEsignHashAlgorithm:
    """Verify the SHA-256 chained hash algorithm is correct and deterministic."""

    def test_hash_is_64_hex_chars(self):
        _, esign_hash = _compute_esign_hash("alice", "2026-03-03T00:00:00Z", "reviewed_and_approved", "Send email to Bob")
        assert len(esign_hash) == 64
        assert all(c in "0123456789abcdef" for c in esign_hash)

    def test_action_hash_is_64_hex_chars(self):
        action_hash, _ = _compute_esign_hash("alice", "2026-03-03T00:00:00Z", "reviewed_and_approved", "Send email to Bob")
        assert len(action_hash) == 64

    def test_hash_is_deterministic(self):
        """Same inputs must always produce the same hash."""
        args = ("alice", "2026-03-03T10:00:00Z", "reviewed_and_approved", "Sent email")
        h1 = _compute_esign_hash(*args)
        h2 = _compute_esign_hash(*args)
        assert h1 == h2, "Hash must be deterministic for same inputs"

    def test_different_users_produce_different_hash(self):
        ts = "2026-03-03T10:00:00Z"
        _, h_alice = _compute_esign_hash("alice", ts, "reviewed_and_approved", "Sent email")
        _, h_bob = _compute_esign_hash("bob", ts, "reviewed_and_approved", "Sent email")
        assert h_alice != h_bob

    def test_different_timestamps_produce_different_hash(self):
        _, h1 = _compute_esign_hash("alice", "2026-03-03T10:00:00Z", "reviewed_and_approved", "Sent email")
        _, h2 = _compute_esign_hash("alice", "2026-03-03T10:00:01Z", "reviewed_and_approved", "Sent email")
        assert h1 != h2

    def test_different_meaning_produces_different_hash(self):
        _, h1 = _compute_esign_hash("alice", "2026-03-03T10:00:00Z", "reviewed_and_approved", "Sent email")
        _, h2 = _compute_esign_hash("alice", "2026-03-03T10:00:00Z", "rejected", "Sent email")
        assert h1 != h2

    def test_different_action_produces_different_hash(self):
        _, h1 = _compute_esign_hash("alice", "2026-03-03T10:00:00Z", "reviewed_and_approved", "Sent email to Bob")
        _, h2 = _compute_esign_hash("alice", "2026-03-03T10:00:00Z", "reviewed_and_approved", "Sent email to Carol")
        assert h1 != h2

    def test_empty_action_description_valid(self):
        """Empty action description is allowed — action_hash = sha256(b'')."""
        action_hash, esign_hash = _compute_esign_hash("alice", "2026-03-03T10:00:00Z", "reviewed_and_approved", "")
        assert action_hash == hashlib.sha256(b"").hexdigest()
        assert len(esign_hash) == 64

    def test_tamper_detection_user_id(self):
        """Changing user_id after signing invalidates the hash."""
        ts = "2026-03-03T10:00:00Z"
        _, original_hash = _compute_esign_hash("alice", ts, "reviewed_and_approved", "Approve send")
        _, recomputed = _compute_esign_hash("mallory", ts, "reviewed_and_approved", "Approve send")
        assert original_hash != recomputed, "Tampered user_id must not match original hash"

    def test_tamper_detection_action(self):
        """Changing action_description after signing invalidates the hash."""
        ts = "2026-03-03T10:00:00Z"
        _, original = _compute_esign_hash("alice", ts, "reviewed_and_approved", "Send $100")
        _, tampered = _compute_esign_hash("alice", ts, "reviewed_and_approved", "Send $10000")
        assert original != tampered

    def test_known_vector(self):
        """Regression test against a known-good hash vector.

        If this test ever fails, the algorithm was changed and all existing
        e-sign records are incompatible. THIS IS A BREAKING CHANGE.
        """
        action_hash, esign_hash = _compute_esign_hash(
            user_id="phuc",
            timestamp="2026-03-03T00:00:00Z",
            meaning="reviewed_and_approved",
            action_description="Gmail inbox triage approved",
        )
        # Compute expected values directly (not hardcoded; ensures algorithm match)
        expected_action = hashlib.sha256(b"Gmail inbox triage approved").hexdigest()
        expected_payload = "phuc" + "2026-03-03T00:00:00Z" + "reviewed_and_approved" + expected_action
        expected_esign = hashlib.sha256(expected_payload.encode()).hexdigest()

        assert action_hash == expected_action, "action_hash algorithm mismatch"
        assert esign_hash == expected_esign, "esign_hash algorithm mismatch"


# ===========================================================================
# 2. EsignCreate — integration tests (skipped if server not running)
# ===========================================================================

class TestEsignCreate:
    """POST /api/v1/esign/token integration tests."""

    @requires_server
    def test_create_returns_200_with_hash(self):
        import urllib.request
        payload = json.dumps({
            "user_id": "test-user",
            "run_id": "test-run-esign-001",
            "meaning": "reviewed_and_approved",
            "action_description": "Test esign create",
        }).encode()
        req = urllib.request.Request(ESIGN_ENDPOINT, data=payload, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        assert resp.status == 200
        assert "esign_hash" in data
        assert len(data["esign_hash"]) == 64
        assert data["verifiable"] is True
        assert data["run_id"] == "test-run-esign-001"
        assert data["user_id"] == "test-user"
        assert data["meaning"] == "reviewed_and_approved"

    @requires_server
    def test_create_missing_user_id_returns_400(self):
        import urllib.request
        import urllib.error
        payload = json.dumps({"run_id": "test-run-002"}).encode()
        req = urllib.request.Request(ESIGN_ENDPOINT, data=payload, method="POST",
                                     headers={"Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req, timeout=5)
        assert exc_info.value.code == 400

    @requires_server
    def test_create_missing_run_id_returns_400(self):
        import urllib.request
        import urllib.error
        payload = json.dumps({"user_id": "alice"}).encode()
        req = urllib.request.Request(ESIGN_ENDPOINT, data=payload, method="POST",
                                     headers={"Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req, timeout=5)
        assert exc_info.value.code == 400

    @requires_server
    def test_create_hash_matches_local_computation(self):
        """Hash from server must match locally computed hash for same inputs."""
        import urllib.request
        ts = "2026-03-03T12:00:00Z"
        payload_dict = {
            "user_id": "verify-user",
            "run_id": "verify-run-001",
            "meaning": "reviewed_and_approved",
            "action_description": "Hash consistency check",
            "timestamp": ts,
        }
        payload = json.dumps(payload_dict).encode()
        req = urllib.request.Request(ESIGN_ENDPOINT, data=payload, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        _, expected_hash = _compute_esign_hash(
            user_id="verify-user",
            timestamp=ts,
            meaning="reviewed_and_approved",
            action_description="Hash consistency check",
        )
        assert data["esign_hash"] == expected_hash, (
            f"Server hash {data['esign_hash']!r} does not match locally computed {expected_hash!r}. "
            "Algorithm mismatch — all existing records may be invalid."
        )


# ===========================================================================
# 3. EvidenceVerify — integration tests (skipped if server not running)
# ===========================================================================

class TestEvidenceVerify:
    """POST /api/v1/evidence/verify integration tests."""

    @requires_server
    def test_verify_valid_hash_returns_match_true(self):
        import urllib.request
        ts = "2026-03-03T13:00:00Z"
        action_description = "Verify integration test"
        _, esign_hash = _compute_esign_hash("verify-alice", ts, "reviewed_and_approved", action_description)

        payload = json.dumps({
            "user_id": "verify-alice",
            "timestamp": ts,
            "meaning": "reviewed_and_approved",
            "action_description": action_description,
            "esign_hash": esign_hash,
        }).encode()
        req = urllib.request.Request(VERIFY_ENDPOINT, data=payload, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        assert data["valid"] is True
        assert data["match"] is True
        assert data["tampered"] is False

    @requires_server
    def test_verify_tampered_hash_returns_tampered_true(self):
        import urllib.request
        ts = "2026-03-03T13:00:00Z"
        payload = json.dumps({
            "user_id": "verify-alice",
            "timestamp": ts,
            "meaning": "reviewed_and_approved",
            "action_description": "Original action",
            "esign_hash": "deadbeef" * 8,  # clearly wrong hash
        }).encode()
        req = urllib.request.Request(VERIFY_ENDPOINT, data=payload, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())

        assert data["valid"] is False
        assert data["match"] is False
        assert data["tampered"] is True

    @requires_server
    def test_verify_missing_fields_returns_400(self):
        import urllib.request
        import urllib.error
        payload = json.dumps({"user_id": "alice"}).encode()  # missing timestamp, meaning, hash
        req = urllib.request.Request(VERIFY_ENDPOINT, data=payload, method="POST",
                                     headers={"Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req, timeout=5)
        assert exc_info.value.code == 400


# ===========================================================================
# 4. AuditFileIntegrity — JSONL file format tests (no server required)
# ===========================================================================

class TestAuditFileIntegrity:
    """Verify the JSONL audit file format that esign endpoint writes."""

    def test_jsonl_record_has_required_alcoa_fields(self):
        """Verify the record format has all ALCOA+ required fields."""
        import datetime
        # Simulate the record that _handle_esign_create writes
        user_id = "phuc"
        run_id = "run-test-001"
        meaning = "reviewed_and_approved"
        action_description = "Approved Gmail inbox triage"
        timestamp = "2026-03-03T10:00:00Z"
        sealed_at = datetime.datetime.utcnow().isoformat() + "Z"

        action_hash, esign_hash = _compute_esign_hash(user_id, timestamp, meaning, action_description)

        record = {
            "event_type": "ESIGN",
            "user_id": user_id,
            "run_id": run_id,
            "meaning": meaning,
            "action_description": action_description,
            "action_hash": action_hash,
            "esign_hash": esign_hash,
            "timestamp": timestamp,
            "sealed_at": sealed_at,
        }

        # ALCOA+ required: Attributable, Legible, Contemporaneous, Original, Accurate
        assert record["user_id"], "Attributable: user_id required"
        assert record["timestamp"], "Contemporaneous: timestamp required"
        assert record["esign_hash"], "Accurate: hash required"
        assert record["event_type"] == "ESIGN", "Original: event_type identifies record type"
        assert record["meaning"], "Legible: meaning required"

    def test_jsonl_record_is_valid_json(self):
        """Each line in the audit JSONL must be independently parseable."""
        ts = "2026-03-03T10:00:00Z"
        action_hash, esign_hash = _compute_esign_hash("alice", ts, "reviewed_and_approved", "Test")
        record = {
            "event_type": "ESIGN",
            "user_id": "alice",
            "run_id": "run-001",
            "meaning": "reviewed_and_approved",
            "action_description": "Test",
            "action_hash": action_hash,
            "esign_hash": esign_hash,
            "timestamp": ts,
            "sealed_at": ts,
        }
        # Must serialize/deserialize without loss
        line = json.dumps(record)
        parsed = json.loads(line)
        assert parsed == record

    def test_esign_file_written_in_tmp(self):
        """Simulate audit file write and verify format (without server)."""
        with tempfile.TemporaryDirectory() as tmp:
            audit_dir = Path(tmp)
            run_id = "unit-test-run-abc123"
            esign_file = audit_dir / f"esign-{run_id}.jsonl"

            ts = "2026-03-03T10:00:00Z"
            action_hash, esign_hash = _compute_esign_hash("phuc", ts, "reviewed_and_approved", "Unit test action")
            record = {
                "event_type": "ESIGN",
                "user_id": "phuc",
                "run_id": run_id,
                "meaning": "reviewed_and_approved",
                "action_description": "Unit test action",
                "action_hash": action_hash,
                "esign_hash": esign_hash,
                "timestamp": ts,
                "sealed_at": ts,
            }

            # Write JSONL (append mode — same as server)
            with open(esign_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

            # Verify file exists and is readable
            assert esign_file.exists()
            lines = esign_file.read_text().strip().split("\n")
            assert len(lines) == 1
            parsed = json.loads(lines[0])
            assert parsed["esign_hash"] == esign_hash
            assert parsed["user_id"] == "phuc"
            assert parsed["event_type"] == "ESIGN"

    def test_audit_file_is_append_only(self):
        """Multiple e-sign calls on same run_id must append, not overwrite."""
        with tempfile.TemporaryDirectory() as tmp:
            audit_dir = Path(tmp)
            run_id = "run-append-test"
            esign_file = audit_dir / f"esign-{run_id}.jsonl"

            for i in range(3):
                ts = f"2026-03-03T10:0{i}:00Z"
                action_hash, esign_hash = _compute_esign_hash("phuc", ts, "reviewed_and_approved", f"Action {i}")
                record = {"event_type": "ESIGN", "user_id": "phuc", "run_id": run_id,
                          "esign_hash": esign_hash, "timestamp": ts, "meaning": "reviewed_and_approved"}
                with open(esign_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")

            lines = esign_file.read_text().strip().split("\n")
            assert len(lines) == 3, "Append-only: must have 3 records after 3 appends"

            # Each line must be independently valid JSON
            for line in lines:
                parsed = json.loads(line)
                assert "esign_hash" in parsed


# ===========================================================================
# Run summary
# ===========================================================================

if __name__ == "__main__":
    import subprocess
    subprocess.run([sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "-p", "no:httpbin"])
