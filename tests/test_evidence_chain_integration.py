"""
Evidence Chain Integration — Acceptance Tests (B9 / T11)
Rung: 641

Test groups:
  1. Execution logging      — log events, chain valid
  2. Auth logging           — log auth events, separate chain valid
  3. Shared run_id          — both chains share the same run_id
  4. Tamper detection       — tampered entry detected
  5. Broken hash link       — broken prev_hash detected
  6. Seal                   — seal prevents further writes
  7. E-signing              — correct hash computation
  8. Cross-app merge        — combines entries from multiple sources
  9. Realm origin           — realm_origin field present on every entry
  10. Empty chain           — validates as valid with 0 entries

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_evidence_chain_integration.py -v -p no:httpbin

Rung: 641 (local correctness)
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Ensure src/ is on sys.path for local imports
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from audit.chain import (
    EvidenceChainManager,
    EvidenceEntry,
    ChainBreakError,
    ChainSealedError,
    GENESIS_HASH,
)


# ===========================================================================
# Fixtures
# ===========================================================================

class _FakeClock:
    """Deterministic clock for testing — advances 1 second per call."""

    def __init__(self, start: datetime | None = None) -> None:
        self._time = start or datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        now = self._time
        self._time += timedelta(seconds=1)
        return now


@pytest.fixture
def evidence_dir(tmp_path):
    """Provide a fresh temporary directory for evidence storage."""
    d = tmp_path / "evidence"
    d.mkdir()
    return d


@pytest.fixture
def clock():
    """Deterministic clock fixture."""
    return _FakeClock()


@pytest.fixture
def manager(evidence_dir, clock):
    """EvidenceChainManager with a deterministic clock."""
    return EvidenceChainManager(
        evidence_dir=evidence_dir,
        run_id="testapp-20260301120000",
        now_fn=clock,
    )


@pytest.fixture
def populated_manager(manager):
    """Manager with 3 execution events and 2 auth events logged."""
    manager.log_execution("TRIGGER", {"trigger": "daily-post"})
    manager.log_execution("PREVIEW", {"mode": "llm_once"})
    manager.log_execution("DONE", {"actions_summary": "posted"})
    manager.log_auth("token_issued", {"user_id": "alice", "scopes": ["write"]})
    manager.log_auth("token_validated", {"user_id": "alice"})
    return manager


# ===========================================================================
# Group 1: Execution logging — log events, chain valid
# ===========================================================================

class TestExecutionLogging:
    """Log execution events and verify the chain is valid."""

    def test_log_execution_returns_hash(self, manager):
        """log_execution returns a 64-char hex hash."""
        h = manager.log_execution("TRIGGER", {"trigger": "test"})
        assert isinstance(h, str)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_execution_chain_valid_after_multiple_events(self, populated_manager):
        """Execution chain validates as intact after multiple events."""
        result = populated_manager.validate_chain(
            populated_manager.execution_chain_path
        )
        assert result["valid"] is True
        assert result["entries"] == 3
        assert result["breaks"] == []

    def test_execution_chain_file_is_jsonl(self, populated_manager):
        """Each line in the execution chain is valid JSON."""
        path = populated_manager.execution_chain_path
        lines = [l for l in path.read_text().splitlines() if l.strip()]
        assert len(lines) == 3
        for line in lines:
            data = json.loads(line)
            assert "entry_id" in data
            assert "entry_hash" in data
            assert "event" in data

    def test_execution_chain_first_entry_has_genesis_prev_hash(self, populated_manager):
        """First entry's prev_hash is GENESIS_HASH."""
        path = populated_manager.execution_chain_path
        first_line = path.read_text().splitlines()[0]
        entry = json.loads(first_line)
        assert entry["prev_hash"] == GENESIS_HASH

    def test_execution_chain_links_are_sequential(self, populated_manager):
        """Each entry's prev_hash equals the previous entry's entry_hash."""
        path = populated_manager.execution_chain_path
        lines = path.read_text().splitlines()
        entries = [json.loads(l) for l in lines if l.strip()]
        for i in range(1, len(entries)):
            assert entries[i]["prev_hash"] == entries[i - 1]["entry_hash"]


# ===========================================================================
# Group 2: Auth logging — separate chain valid
# ===========================================================================

class TestAuthLogging:
    """Log auth events and verify the auth chain is valid."""

    def test_log_auth_returns_hash(self, manager):
        """log_auth returns a 64-char hex hash."""
        h = manager.log_auth("token_issued", {"user_id": "bob"})
        assert isinstance(h, str)
        assert len(h) == 64

    def test_auth_chain_valid_after_events(self, populated_manager):
        """Auth chain validates as intact after events."""
        result = populated_manager.validate_chain(
            populated_manager.auth_chain_path
        )
        assert result["valid"] is True
        assert result["entries"] == 2
        assert result["breaks"] == []

    def test_auth_chain_separate_from_execution(self, populated_manager):
        """Auth chain file is distinct from execution chain file."""
        assert populated_manager.execution_chain_path != populated_manager.auth_chain_path
        assert populated_manager.execution_chain_path.name == "evidence_chain.jsonl"
        assert populated_manager.auth_chain_path.name == "oauth3_audit.jsonl"

    def test_auth_chain_entries_have_auth_events(self, populated_manager):
        """Auth chain entries have auth-specific event names."""
        path = populated_manager.auth_chain_path
        lines = path.read_text().splitlines()
        entries = [json.loads(l) for l in lines if l.strip()]
        events = [e["event"] for e in entries]
        assert "token_issued" in events
        assert "token_validated" in events


# ===========================================================================
# Group 3: Shared run_id
# ===========================================================================

class TestSharedRunId:
    """Both chains share the same run_id."""

    def test_run_id_matches_on_manager(self, populated_manager):
        """Manager's run_id property returns the configured run_id."""
        assert populated_manager.run_id == "testapp-20260301120000"

    def test_execution_entries_have_run_id(self, populated_manager):
        """Every execution chain entry has the shared run_id."""
        path = populated_manager.execution_chain_path
        lines = path.read_text().splitlines()
        for line in lines:
            if line.strip():
                entry = json.loads(line)
                assert entry["run_id"] == "testapp-20260301120000"

    def test_auth_entries_have_run_id(self, populated_manager):
        """Every auth chain entry has the shared run_id."""
        path = populated_manager.auth_chain_path
        lines = path.read_text().splitlines()
        for line in lines:
            if line.strip():
                entry = json.loads(line)
                assert entry["run_id"] == "testapp-20260301120000"

    def test_validate_all_returns_run_id(self, populated_manager):
        """validate_all includes the run_id in its result."""
        result = populated_manager.validate_all()
        assert result["run_id"] == "testapp-20260301120000"

    def test_validate_all_reports_both_chains(self, populated_manager):
        """validate_all reports status for both chains."""
        result = populated_manager.validate_all()
        assert result["execution"]["valid"] is True
        assert result["execution"]["entries"] == 3
        assert result["auth"]["valid"] is True
        assert result["auth"]["entries"] == 2


# ===========================================================================
# Group 4: Tamper detection — tampered entry detected
# ===========================================================================

class TestTamperDetection:
    """Validate detects tampered entries."""

    def test_tampered_event_field_detected(self, populated_manager):
        """Modifying an event field in the JSONL causes validation failure."""
        path = populated_manager.execution_chain_path
        lines = path.read_text().splitlines()
        # Tamper with the second entry's event field
        entry = json.loads(lines[1])
        entry["event"] = "HACKED"
        lines[1] = json.dumps(entry, sort_keys=True)
        path.write_text("\n".join(lines) + "\n")

        result = populated_manager.validate_chain(path)
        assert result["valid"] is False
        assert len(result["breaks"]) > 0

    def test_tampered_detail_field_detected(self, populated_manager):
        """Modifying a detail field causes validation failure."""
        path = populated_manager.execution_chain_path
        lines = path.read_text().splitlines()
        entry = json.loads(lines[0])
        entry["detail"]["trigger"] = "evil-trigger"
        lines[0] = json.dumps(entry, sort_keys=True)
        path.write_text("\n".join(lines) + "\n")

        result = populated_manager.validate_chain(path)
        assert result["valid"] is False
        # The break should be a hash_mismatch
        assert any(b["type"] == "hash_mismatch" for b in result["breaks"])

    def test_tampered_entry_hash_detected(self, populated_manager):
        """Forging entry_hash causes validation failure."""
        path = populated_manager.execution_chain_path
        lines = path.read_text().splitlines()
        entry = json.loads(lines[0])
        entry["entry_hash"] = "a" * 64
        lines[0] = json.dumps(entry, sort_keys=True)
        path.write_text("\n".join(lines) + "\n")

        result = populated_manager.validate_chain(path)
        assert result["valid"] is False


# ===========================================================================
# Group 5: Broken hash link
# ===========================================================================

class TestBrokenHashLink:
    """Validate detects broken prev_hash links."""

    def test_broken_prev_hash_detected(self, populated_manager):
        """Changing prev_hash on an entry causes chain_break detection."""
        path = populated_manager.execution_chain_path
        lines = path.read_text().splitlines()
        # Break the chain link on entry 2 (index 2)
        entry = json.loads(lines[2])
        entry["prev_hash"] = "b" * 64
        # Recompute entry_hash to avoid hash_mismatch (only break the link)
        record_without_hash = {k: v for k, v in entry.items() if k != "entry_hash"}
        import hashlib
        canonical = json.dumps(record_without_hash, sort_keys=True, separators=(",", ":"))
        entry["entry_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        lines[2] = json.dumps(entry, sort_keys=True)
        path.write_text("\n".join(lines) + "\n")

        result = populated_manager.validate_chain(path)
        assert result["valid"] is False
        chain_breaks = [b for b in result["breaks"] if b["type"] == "chain_break"]
        assert len(chain_breaks) >= 1

    def test_broken_genesis_prev_hash_detected(self, populated_manager):
        """Changing the genesis entry's prev_hash causes a break."""
        path = populated_manager.execution_chain_path
        lines = path.read_text().splitlines()
        entry = json.loads(lines[0])
        entry["prev_hash"] = "c" * 64
        # Recompute entry_hash
        record_without_hash = {k: v for k, v in entry.items() if k != "entry_hash"}
        import hashlib
        canonical = json.dumps(record_without_hash, sort_keys=True, separators=(",", ":"))
        entry["entry_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        lines[0] = json.dumps(entry, sort_keys=True)
        path.write_text("\n".join(lines) + "\n")

        result = populated_manager.validate_chain(path)
        assert result["valid"] is False
        genesis_breaks = [
            b for b in result["breaks"]
            if b["type"] == "chain_break" and b["entry_id"] == 0
        ]
        assert len(genesis_breaks) >= 1

    def test_deleted_entry_causes_chain_break(self, populated_manager):
        """Removing an entry from the JSONL causes chain_break detection."""
        path = populated_manager.execution_chain_path
        lines = path.read_text().splitlines()
        # Remove middle entry
        del lines[1]
        path.write_text("\n".join(lines) + "\n")

        result = populated_manager.validate_chain(path)
        assert result["valid"] is False


# ===========================================================================
# Group 6: Seal prevents further writes
# ===========================================================================

class TestSeal:
    """seal() prevents further writes to both chains."""

    def test_seal_returns_hashes_and_timestamp(self, populated_manager):
        """seal() returns execution_hash, auth_hash, and sealed_at."""
        result = populated_manager.seal()
        assert "execution_hash" in result
        assert "auth_hash" in result
        assert "sealed_at" in result
        assert len(result["execution_hash"]) == 64
        assert len(result["auth_hash"]) == 64

    def test_seal_writes_seal_entries(self, populated_manager):
        """seal() writes SEAL events to both chain files."""
        populated_manager.seal()

        # Check execution chain
        exec_lines = populated_manager.execution_chain_path.read_text().splitlines()
        last_exec = json.loads(exec_lines[-1])
        assert last_exec["event"] == "SEAL"

        # Check auth chain
        auth_lines = populated_manager.auth_chain_path.read_text().splitlines()
        last_auth = json.loads(auth_lines[-1])
        assert last_auth["event"] == "SEAL"

    def test_log_execution_after_seal_raises(self, populated_manager):
        """Logging to execution chain after seal raises ChainSealedError."""
        populated_manager.seal()
        with pytest.raises(ChainSealedError):
            populated_manager.log_execution("LATE_EVENT", {"should": "fail"})

    def test_log_auth_after_seal_raises(self, populated_manager):
        """Logging to auth chain after seal raises ChainSealedError."""
        populated_manager.seal()
        with pytest.raises(ChainSealedError):
            populated_manager.log_auth("late_token", {"should": "fail"})

    def test_is_sealed_property(self, populated_manager):
        """is_sealed is False before seal, True after."""
        assert populated_manager.is_sealed is False
        populated_manager.seal()
        assert populated_manager.is_sealed is True

    def test_sealed_chains_still_validate(self, populated_manager):
        """Sealed chains validate as intact (SEAL is a valid entry)."""
        populated_manager.seal()
        result = populated_manager.validate_all()
        assert result["execution"]["valid"] is True
        assert result["auth"]["valid"] is True
        # Execution: 3 original + 1 SEAL = 4
        assert result["execution"]["entries"] == 4
        # Auth: 2 original + 1 SEAL = 3
        assert result["auth"]["entries"] == 3


# ===========================================================================
# Group 7: E-signing
# ===========================================================================

class TestESigning:
    """E-signing produces correct hash."""

    def test_e_sign_returns_64_char_hex(self):
        """e_sign returns a 64-character lowercase hex string."""
        sig = EvidenceChainManager.e_sign(
            user_id="alice",
            timestamp="2026-03-01T12:00:00+00:00",
            meaning="approved",
            record_hash="a" * 64,
        )
        assert isinstance(sig, str)
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_e_sign_is_deterministic(self):
        """Same inputs produce the same e-signature."""
        sig1 = EvidenceChainManager.e_sign(
            "alice", "2026-03-01T12:00:00+00:00", "approved", "a" * 64
        )
        sig2 = EvidenceChainManager.e_sign(
            "alice", "2026-03-01T12:00:00+00:00", "approved", "a" * 64
        )
        assert sig1 == sig2

    def test_e_sign_changes_with_different_user(self):
        """Different user_id produces different signature."""
        sig_alice = EvidenceChainManager.e_sign(
            "alice", "2026-03-01T12:00:00+00:00", "approved", "a" * 64
        )
        sig_bob = EvidenceChainManager.e_sign(
            "bob", "2026-03-01T12:00:00+00:00", "approved", "a" * 64
        )
        assert sig_alice != sig_bob

    def test_e_sign_changes_with_different_meaning(self):
        """Different meaning produces different signature."""
        sig_approved = EvidenceChainManager.e_sign(
            "alice", "2026-03-01T12:00:00+00:00", "approved", "a" * 64
        )
        sig_reviewed = EvidenceChainManager.e_sign(
            "alice", "2026-03-01T12:00:00+00:00", "reviewed", "a" * 64
        )
        assert sig_approved != sig_reviewed

    def test_e_sign_changes_with_different_timestamp(self):
        """Different timestamp produces different signature."""
        sig1 = EvidenceChainManager.e_sign(
            "alice", "2026-03-01T12:00:00+00:00", "approved", "a" * 64
        )
        sig2 = EvidenceChainManager.e_sign(
            "alice", "2026-03-01T13:00:00+00:00", "approved", "a" * 64
        )
        assert sig1 != sig2

    def test_e_sign_changes_with_different_record_hash(self):
        """Different record_hash produces different signature."""
        sig1 = EvidenceChainManager.e_sign(
            "alice", "2026-03-01T12:00:00+00:00", "approved", "a" * 64
        )
        sig2 = EvidenceChainManager.e_sign(
            "alice", "2026-03-01T12:00:00+00:00", "approved", "b" * 64
        )
        assert sig1 != sig2

    def test_e_sign_formula_matches_spec(self):
        """E-signature matches sha256(user_id + timestamp + meaning + record_hash)."""
        import hashlib
        user_id = "alice"
        timestamp = "2026-03-01T12:00:00+00:00"
        meaning = "approved"
        record_hash = "abc123" + "0" * 58  # 64 chars
        expected = hashlib.sha256(
            (user_id + timestamp + meaning + record_hash).encode("utf-8")
        ).hexdigest()
        actual = EvidenceChainManager.e_sign(user_id, timestamp, meaning, record_hash)
        assert actual == expected


# ===========================================================================
# Group 8: Cross-app merge
# ===========================================================================

class TestCrossAppMerge:
    """Cross-app merge combines entries from multiple sources."""

    def test_merge_combines_entries(self, populated_manager, evidence_dir, clock):
        """merge_cross_app combines entries from two chains."""
        # Create another manager simulating a different app
        other_dir = evidence_dir / "other_app"
        other_dir.mkdir()
        other_mgr = EvidenceChainManager(
            evidence_dir=other_dir,
            run_id="otherapp-20260301120000",
            now_fn=clock,
        )
        other_mgr.log_execution("TRIGGER", {"trigger": "other-task"})
        other_mgr.log_execution("DONE", {"status": "success"})

        result = populated_manager.merge_cross_app(
            other_mgr.execution_chain_path
        )
        assert result["merged_entries"] == 5  # 3 from us + 2 from other
        assert len(result["sources"]) >= 2

    def test_merge_creates_merged_file(self, populated_manager, evidence_dir, clock):
        """merge_cross_app creates cross_app_merged.jsonl."""
        other_dir = evidence_dir / "other_app"
        other_dir.mkdir()
        other_mgr = EvidenceChainManager(
            evidence_dir=other_dir,
            run_id="otherapp-20260301130000",
            now_fn=clock,
        )
        other_mgr.log_execution("TRIGGER", {"trigger": "merge-test"})

        populated_manager.merge_cross_app(other_mgr.execution_chain_path)
        merged_path = evidence_dir / "cross_app_merged.jsonl"
        assert merged_path.exists()
        lines = [l for l in merged_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 4  # 3 + 1

    def test_merge_sorted_by_timestamp(self, populated_manager, evidence_dir):
        """Merged entries are sorted by timestamp."""
        other_dir = evidence_dir / "other_app"
        other_dir.mkdir()
        # Use a clock that starts before the populated_manager's events
        early_clock = _FakeClock(datetime(2026, 2, 28, 10, 0, 0, tzinfo=timezone.utc))
        other_mgr = EvidenceChainManager(
            evidence_dir=other_dir,
            run_id="earlyapp-20260228100000",
            now_fn=early_clock,
        )
        other_mgr.log_execution("EARLY_EVENT", {"note": "before main events"})

        populated_manager.merge_cross_app(other_mgr.execution_chain_path)
        merged_path = evidence_dir / "cross_app_merged.jsonl"
        lines = [l for l in merged_path.read_text().splitlines() if l.strip()]
        entries = [json.loads(l) for l in lines]
        timestamps = [e["timestamp"] for e in entries]
        assert timestamps == sorted(timestamps)

    def test_merge_missing_other_chain_raises(self, populated_manager, evidence_dir):
        """merge_cross_app raises FileNotFoundError for missing chain."""
        with pytest.raises(FileNotFoundError):
            populated_manager.merge_cross_app(evidence_dir / "nonexistent.jsonl")

    def test_merge_returns_source_ids(self, populated_manager, evidence_dir, clock):
        """merge_cross_app returns distinct source app IDs."""
        other_dir = evidence_dir / "other_app"
        other_dir.mkdir()
        other_mgr = EvidenceChainManager(
            evidence_dir=other_dir,
            run_id="gmail-20260301140000",
            now_fn=clock,
        )
        other_mgr.log_execution("TRIGGER", {"trigger": "gmail-task"})

        result = populated_manager.merge_cross_app(other_mgr.execution_chain_path)
        assert "testapp" in result["sources"]
        assert "gmail" in result["sources"]


# ===========================================================================
# Group 9: Realm origin
# ===========================================================================

class TestRealmOrigin:
    """realm_origin field present on every entry."""

    def test_default_realm_is_local(self, manager):
        """Default realm_origin is 'local'."""
        manager.log_execution("TEST", {"data": "test"})
        path = manager.execution_chain_path
        entry = json.loads(path.read_text().splitlines()[0])
        assert entry["realm_origin"] == "local"

    def test_cloud_realm(self, manager):
        """realm_origin can be set to 'cloud'."""
        manager.log_execution("CLOUD_EVENT", {"data": "test"}, realm="cloud")
        path = manager.execution_chain_path
        entry = json.loads(path.read_text().splitlines()[0])
        assert entry["realm_origin"] == "cloud"

    def test_browser_realm(self, manager):
        """realm_origin can be set to 'browser'."""
        manager.log_auth("browser_auth", {"user": "alice"}, realm="browser")
        path = manager.auth_chain_path
        entry = json.loads(path.read_text().splitlines()[0])
        assert entry["realm_origin"] == "browser"

    def test_invalid_realm_raises(self, manager):
        """Invalid realm_origin raises ValueError."""
        with pytest.raises(ValueError, match="Invalid realm_origin"):
            manager.log_execution("BAD", {"data": "test"}, realm="invalid")

    def test_all_entries_have_realm_origin(self, populated_manager):
        """Every entry in both chains has a realm_origin field."""
        for chain_path in [
            populated_manager.execution_chain_path,
            populated_manager.auth_chain_path,
        ]:
            lines = chain_path.read_text().splitlines()
            for line in lines:
                if line.strip():
                    entry = json.loads(line)
                    assert "realm_origin" in entry
                    assert entry["realm_origin"] in {"local", "cloud", "browser"}


# ===========================================================================
# Group 10: Empty chain validates as valid
# ===========================================================================

class TestEmptyChain:
    """Empty chain validates as valid (0 entries)."""

    def test_empty_execution_chain_validates(self, manager):
        """Execution chain with no entries validates as valid."""
        result = manager.validate_chain(manager.execution_chain_path)
        assert result["valid"] is True
        assert result["entries"] == 0
        assert result["first_hash"] == ""
        assert result["last_hash"] == ""
        assert result["breaks"] == []

    def test_empty_auth_chain_validates(self, manager):
        """Auth chain with no entries validates as valid."""
        result = manager.validate_chain(manager.auth_chain_path)
        assert result["valid"] is True
        assert result["entries"] == 0

    def test_validate_all_empty(self, manager):
        """validate_all on fresh manager reports 0 entries, both valid."""
        result = manager.validate_all()
        assert result["execution"]["valid"] is True
        assert result["execution"]["entries"] == 0
        assert result["auth"]["valid"] is True
        assert result["auth"]["entries"] == 0

    def test_is_sealed_false_on_fresh_manager(self, manager):
        """Fresh manager is not sealed."""
        assert manager.is_sealed is False

    def test_seal_empty_chains(self, manager):
        """Sealing empty chains writes SEAL entries (1 each)."""
        result = manager.seal()
        assert len(result["execution_hash"]) == 64
        assert len(result["auth_hash"]) == 64
        validation = manager.validate_all()
        assert validation["execution"]["entries"] == 1
        assert validation["auth"]["entries"] == 1
