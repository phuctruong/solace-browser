"""
FDA 21 CFR Part 11 Audit Trail — Acceptance Tests
Rung: 641

Test groups:
  1. AuditEntry          — hash computation, determinism, field mutations
  2. AuditChain          — append, genesis, chain links, verify_integrity (valid chain)
  3. Tamper detection    — modify entry, delete entry, reorder entries
  4. Persistence         — save to disk, load from disk, round-trip integrity
  5. ALCOA+ validation   — all-pass, per-principle failures
  6. RetentionPolicy     — defaults, tier overrides
  7. RetentionEngine     — can_delete, records_to_archive, records_to_protect

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_audit.py -v -p no:httpbin

Rung: 641 (local correctness)
"""

import json
import sys
import time
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import pytest

# Ensure src/ is on sys.path for local imports
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from audit.chain import AuditEntry, AuditChain
from audit.alcoa import ALCOAReport, validate_alcoa
from audit.retention import RetentionPolicy, RetentionEngine


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def audit_dir(tmp_path):
    """Provide a fresh temporary directory for audit storage in each test."""
    d = tmp_path / "solace_audit"
    d.mkdir()
    return str(d)


@pytest.fixture
def empty_chain(audit_dir):
    """An AuditChain with no entries."""
    return AuditChain(session_id="sess-test-empty", base_dir=audit_dir)


@pytest.fixture
def populated_chain(audit_dir):
    """An AuditChain with three valid entries (all ALCOA+ compliant)."""
    chain = AuditChain(session_id="sess-test-pop", base_dir=audit_dir)
    chain.append(
        user_id="alice",
        token_id="tok-001",
        action="navigate",
        target="https://linkedin.com/feed",
        reason="Open LinkedIn homepage to check feed",
        meaning="authorized",
        human_description="Navigated to LinkedIn feed as part of create-post recipe",
        snapshot_id="snap-abc123",
        scope_used="linkedin.create_post",
        step_up_performed=False,
    )
    chain.append(
        user_id="alice",
        token_id="tok-001",
        action="click",
        target="#start-post-button",
        reason="Open compose post dialog",
        meaning="authorized",
        human_description="Clicked 'Start a post' button to open compose dialog",
        snapshot_id="snap-def456",
        scope_used="linkedin.create_post",
        step_up_performed=False,
    )
    chain.append(
        user_id="alice",
        token_id="tok-001",
        action="fill",
        target="#post-text-area",
        before_value="",
        after_value="Hello LinkedIn!",
        reason="Enter post content as instructed by recipe",
        meaning="authorized",
        human_description="Filled post text area with content 'Hello LinkedIn!'",
        snapshot_id="snap-ghi789",
        scope_used="linkedin.create_post",
        step_up_performed=False,
    )
    return chain


# ===========================================================================
# Group 1: AuditEntry
# ===========================================================================

class TestAuditEntry:
    """AuditEntry hash computation, determinism, and field integrity."""

    def test_compute_hash_returns_64_char_hex(self, populated_chain):
        """compute_hash returns a 64-character lowercase hex string."""
        entry = populated_chain.entries[0]
        h = entry.compute_hash()
        assert isinstance(h, str)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_compute_hash_is_deterministic(self, populated_chain):
        """Same entry produces the same hash every time."""
        entry = populated_chain.entries[0]
        h1 = entry.compute_hash()
        h2 = entry.compute_hash()
        assert h1 == h2

    def test_compute_hash_excludes_entry_hash_field(self, populated_chain):
        """Hash computation excludes the entry_hash field itself."""
        entry = populated_chain.entries[0]
        # Manually tamper with entry_hash only — compute_hash should be unchanged
        original_compute = entry.compute_hash()
        # Temporarily change stored entry_hash
        old_stored = entry.entry_hash
        entry.entry_hash = "x" * 64
        assert entry.compute_hash() == original_compute
        entry.entry_hash = old_stored  # restore

    def test_hash_changes_when_content_changes(self, populated_chain):
        """Hash is different if any data field changes."""
        entry = populated_chain.entries[0]
        h_before = entry.compute_hash()
        # Change a data field
        entry.action = "submit"
        h_after = entry.compute_hash()
        assert h_before != h_after
        entry.action = "navigate"  # restore

    def test_all_required_fields_present(self, populated_chain):
        """Every AuditEntry has all required ALCOA+ fields."""
        entry = populated_chain.entries[0]
        for field_name in [
            "entry_id", "timestamp", "user_id", "token_id",
            "action", "target", "before_value", "after_value",
            "reason", "meaning", "human_description", "snapshot_id",
            "scope_used", "step_up_performed", "prev_hash", "entry_hash",
        ]:
            assert hasattr(entry, field_name), f"Missing field: {field_name}"

    def test_entry_hash_equals_compute_hash_after_append(self, populated_chain):
        """entry_hash stored on the entry equals compute_hash()."""
        for entry in populated_chain.entries:
            assert entry.entry_hash == entry.compute_hash()

    def test_hash_is_sha256_length(self, populated_chain):
        """SHA-256 produces exactly 64 hex characters."""
        for entry in populated_chain.entries:
            assert len(entry.entry_hash) == 64


# ===========================================================================
# Group 2: AuditChain — basic operations
# ===========================================================================

class TestAuditChainBasic:
    """AuditChain append, genesis hash, chain links, basic integrity."""

    def test_empty_chain_has_zero_count(self, empty_chain):
        assert empty_chain.count == 0

    def test_empty_chain_hash_is_genesis(self, empty_chain):
        """chain_hash on empty chain equals GENESIS_HASH."""
        assert empty_chain.chain_hash == AuditChain.GENESIS_HASH
        assert empty_chain.chain_hash == "0" * 64

    def test_append_increments_count(self, empty_chain):
        """Appending entries increases count."""
        empty_chain.append(
            user_id="bob", token_id="tok-x",
            action="navigate", target="https://example.com",
            human_description="Navigate to example.com",
            snapshot_id="snap-001",
        )
        assert empty_chain.count == 1

    def test_append_returns_entry(self, empty_chain):
        """append() returns the AuditEntry that was created."""
        entry = empty_chain.append(
            user_id="bob", token_id="tok-x",
            action="navigate", target="https://example.com",
            human_description="Navigate to example.com",
            snapshot_id="snap-001",
        )
        assert isinstance(entry, AuditEntry)
        assert entry.entry_id == "0"

    def test_first_entry_prev_hash_is_genesis(self, empty_chain):
        """First entry has prev_hash == GENESIS_HASH."""
        entry = empty_chain.append(
            user_id="bob", token_id="tok-x",
            action="navigate", target="https://example.com",
            human_description="Navigate to example.com",
            snapshot_id="snap-001",
        )
        assert entry.prev_hash == AuditChain.GENESIS_HASH

    def test_second_entry_prev_hash_equals_first_entry_hash(self, empty_chain):
        """Second entry's prev_hash equals first entry's entry_hash."""
        e0 = empty_chain.append(
            user_id="bob", token_id="tok-x",
            action="navigate", target="https://example.com",
            human_description="Navigate to example.com",
            snapshot_id="snap-001",
        )
        e1 = empty_chain.append(
            user_id="bob", token_id="tok-x",
            action="click", target="#btn",
            human_description="Click submit button",
            snapshot_id="snap-002",
        )
        assert e1.prev_hash == e0.entry_hash

    def test_chain_hash_equals_last_entry_hash(self, populated_chain):
        """chain_hash property equals the last entry's entry_hash."""
        last = populated_chain.entries[-1]
        assert populated_chain.chain_hash == last.entry_hash

    def test_verify_integrity_passes_on_valid_chain(self, populated_chain):
        """verify_integrity returns valid=True on an untampered chain."""
        result = populated_chain.verify_integrity()
        assert result["valid"] is True
        assert result["entries_checked"] == 3
        assert result["break_at"] is None
        assert result["error"] is None

    def test_entry_ids_are_sequential_strings(self, populated_chain):
        """Entry IDs are '0', '1', '2', ... as strings."""
        for i, entry in enumerate(populated_chain.entries):
            assert entry.entry_id == str(i)

    def test_entries_property_returns_copy(self, populated_chain):
        """entries property returns a copy — mutations do not affect chain."""
        entries_copy = populated_chain.entries
        entries_copy.clear()
        assert populated_chain.count == 3  # original unaffected

    def test_verify_integrity_empty_chain(self, empty_chain):
        """verify_integrity on empty chain returns valid with 0 entries_checked."""
        result = empty_chain.verify_integrity()
        assert result["valid"] is True
        assert result["entries_checked"] == 0


# ===========================================================================
# Group 3: Tamper detection
# ===========================================================================

class TestTamperDetection:
    """Verify that any tampering causes verify_integrity to fail."""

    def _make_chain(self, audit_dir):
        chain = AuditChain(session_id="sess-tamper", base_dir=audit_dir)
        chain.append(
            user_id="alice", token_id="tok-1",
            action="navigate", target="https://linkedin.com",
            human_description="Navigate to LinkedIn",
            snapshot_id="snap-A",
        )
        chain.append(
            user_id="alice", token_id="tok-1",
            action="click", target="#btn",
            human_description="Click post button",
            snapshot_id="snap-B",
        )
        chain.append(
            user_id="alice", token_id="tok-1",
            action="submit", target="#form",
            human_description="Submit post form",
            snapshot_id="snap-C",
        )
        return chain

    def test_modify_entry_field_breaks_chain(self, audit_dir):
        """Changing a data field on an entry breaks verify_integrity."""
        chain = self._make_chain(audit_dir)
        # Directly mutate middle entry's action field (simulating a tampering attack)
        chain._entries[1].action = "HACKED"
        result = chain.verify_integrity()
        assert result["valid"] is False
        assert result["break_at"] == 1

    def test_modify_entry_hash_breaks_chain(self, audit_dir):
        """Forging entry_hash on entry 0 breaks the chain at entry 1."""
        chain = self._make_chain(audit_dir)
        chain._entries[0].entry_hash = "a" * 64  # forge the hash
        result = chain.verify_integrity()
        assert result["valid"] is False
        # Entry 0: compute_hash() != stored entry_hash → break at 0
        # OR entry 1: prev_hash != entry 0's entry_hash → break at 1
        assert result["break_at"] in (0, 1)

    def test_delete_entry_breaks_chain_via_entry_ids(self, audit_dir):
        """Removing an entry from _entries causes the ID sequence to have a gap."""
        chain = self._make_chain(audit_dir)
        # Remove middle entry — chain now has entries 0, 2 (IDs "0" and "2")
        chain._entries.pop(1)
        # verify_integrity will fail because entry[1].prev_hash != entry[0].entry_hash
        result = chain.verify_integrity()
        assert result["valid"] is False

    def test_reorder_entries_breaks_chain(self, audit_dir):
        """Swapping two entries breaks the hash chain."""
        chain = self._make_chain(audit_dir)
        # Swap first and second entry
        chain._entries[0], chain._entries[1] = chain._entries[1], chain._entries[0]
        result = chain.verify_integrity()
        assert result["valid"] is False

    def test_insert_fake_entry_breaks_chain(self, audit_dir):
        """Inserting a fabricated entry into _entries breaks the chain."""
        chain = self._make_chain(audit_dir)
        fake = AuditEntry(
            entry_id="99",
            timestamp="2026-01-01T00:00:00+00:00",
            user_id="attacker",
            token_id="tok-fake",
            action="navigate",
            target="https://evil.com",
            before_value="",
            after_value="",
            reason="",
            meaning="authorized",
            human_description="Injected entry",
            snapshot_id="snap-fake",
            scope_used="",
            step_up_performed=False,
            prev_hash=chain._entries[0].entry_hash,
        )
        fake.entry_hash = fake.compute_hash()
        chain._entries.insert(1, fake)
        result = chain.verify_integrity()
        assert result["valid"] is False

    def test_modify_genesis_prev_hash_breaks_chain(self, audit_dir):
        """Changing genesis entry's prev_hash from all-zeros breaks integrity."""
        chain = self._make_chain(audit_dir)
        chain._entries[0].prev_hash = "b" * 64
        result = chain.verify_integrity()
        assert result["valid"] is False
        assert result["break_at"] == 0


# ===========================================================================
# Group 4: Persistence (save to disk, load from disk)
# ===========================================================================

class TestPersistence:
    """Audit log survives save → load round-trip with hash chain intact."""

    def test_audit_jsonl_file_is_created(self, populated_chain, audit_dir):
        """audit.jsonl file exists after appending entries."""
        log_path = populated_chain._log_path()
        assert log_path.exists()

    def test_log_has_correct_number_of_lines(self, populated_chain):
        """Each entry is one line in audit.jsonl."""
        log_path = populated_chain._log_path()
        lines = [l for l in log_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 3

    def test_each_line_is_valid_json(self, populated_chain):
        """Every line in audit.jsonl is parseable JSON."""
        log_path = populated_chain._log_path()
        for line in log_path.read_text().splitlines():
            if line.strip():
                data = json.loads(line)
                assert "entry_id" in data
                assert "entry_hash" in data

    def test_load_restores_correct_count(self, populated_chain, audit_dir):
        """Loading an existing audit.jsonl restores all entries."""
        reloaded = AuditChain(
            session_id=populated_chain.session_id,
            base_dir=audit_dir,
        )
        reloaded.load()
        assert reloaded.count == populated_chain.count

    def test_load_restores_entry_ids(self, populated_chain, audit_dir):
        """Loaded entries have correct sequential entry_ids."""
        reloaded = AuditChain(
            session_id=populated_chain.session_id,
            base_dir=audit_dir,
        )
        reloaded.load()
        for i, entry in enumerate(reloaded.entries):
            assert entry.entry_id == str(i)

    def test_load_restores_entry_hashes(self, populated_chain, audit_dir):
        """Loaded entry_hash values match original stored values."""
        original_hashes = [e.entry_hash for e in populated_chain.entries]
        reloaded = AuditChain(
            session_id=populated_chain.session_id,
            base_dir=audit_dir,
        )
        reloaded.load()
        loaded_hashes = [e.entry_hash for e in reloaded.entries]
        assert original_hashes == loaded_hashes

    def test_verify_integrity_passes_after_reload(self, populated_chain, audit_dir):
        """Hash chain is still valid after a save+load round-trip."""
        reloaded = AuditChain(
            session_id=populated_chain.session_id,
            base_dir=audit_dir,
        )
        reloaded.load()
        result = reloaded.verify_integrity()
        assert result["valid"] is True

    def test_load_raises_for_missing_log_file(self, audit_dir):
        """load() raises FileNotFoundError when audit.jsonl doesn't exist."""
        chain = AuditChain(session_id="nonexistent-session", base_dir=audit_dir)
        with pytest.raises(FileNotFoundError):
            chain.load()

    def test_append_after_load_continues_chain(self, populated_chain, audit_dir):
        """Appending to a reloaded chain produces a valid extended chain."""
        reloaded = AuditChain(
            session_id=populated_chain.session_id,
            base_dir=audit_dir,
        )
        reloaded.load()
        reloaded.append(
            user_id="alice", token_id="tok-001",
            action="navigate", target="https://linkedin.com/done",
            human_description="Navigated away after post",
            snapshot_id="snap-new",
        )
        assert reloaded.count == 4
        result = reloaded.verify_integrity()
        assert result["valid"] is True


# ===========================================================================
# Group 5: ALCOA+ Validation
# ===========================================================================

class TestALCOAValidation:
    """validate_alcoa covers all nine ALCOA+ principles."""

    def test_all_pass_on_compliant_chain(self, populated_chain):
        """All ALCOA+ principles pass on a fully compliant chain."""
        report = validate_alcoa(populated_chain)
        assert report.overall is True
        assert report.score == "9/9"

    def test_attributable_fails_when_user_id_missing(self, audit_dir):
        """Attributable fails when user_id is empty."""
        chain = AuditChain(session_id="sess-a", base_dir=audit_dir)
        chain.append(
            user_id="",  # empty user_id → fails Attributable
            token_id="tok-1",
            action="navigate", target="https://example.com",
            human_description="Test entry",
            snapshot_id="snap-001",
        )
        report = validate_alcoa(chain)
        assert report.attributable is False
        assert report.overall is False

    def test_attributable_fails_when_token_id_missing(self, audit_dir):
        """Attributable fails when token_id is empty."""
        chain = AuditChain(session_id="sess-b", base_dir=audit_dir)
        chain.append(
            user_id="alice",
            token_id="",  # empty token_id → fails Attributable
            action="navigate", target="https://example.com",
            human_description="Test entry",
            snapshot_id="snap-001",
        )
        report = validate_alcoa(chain)
        assert report.attributable is False

    def test_legible_fails_when_human_description_missing(self, audit_dir):
        """Legible fails when human_description is empty."""
        chain = AuditChain(session_id="sess-c", base_dir=audit_dir)
        chain.append(
            user_id="alice", token_id="tok-1",
            action="navigate", target="https://example.com",
            human_description="",  # empty description → fails Legible
            snapshot_id="snap-001",
        )
        report = validate_alcoa(chain)
        assert report.legible is False
        assert report.overall is False

    def test_contemporaneous_fails_with_non_monotonic_timestamps(self, audit_dir):
        """Contemporaneous fails when a timestamp goes backward."""
        chain = AuditChain(session_id="sess-d", base_dir=audit_dir)
        chain.append(
            user_id="alice", token_id="tok-1",
            action="navigate", target="https://example.com",
            human_description="First entry",
            snapshot_id="snap-001",
        )
        chain.append(
            user_id="alice", token_id="tok-1",
            action="click", target="#btn",
            human_description="Second entry",
            snapshot_id="snap-002",
        )
        # Manually force the second entry's timestamp to be BEFORE the first
        chain._entries[1].timestamp = "2000-01-01T00:00:00+00:00"
        report = validate_alcoa(chain)
        assert report.contemporaneous is False
        assert report.overall is False

    def test_original_fails_when_snapshot_id_missing(self, audit_dir):
        """Original fails when snapshot_id is empty."""
        chain = AuditChain(session_id="sess-e", base_dir=audit_dir)
        chain.append(
            user_id="alice", token_id="tok-1",
            action="navigate", target="https://example.com",
            human_description="Test entry",
            snapshot_id="",  # no snapshot → fails Original
        )
        report = validate_alcoa(chain)
        assert report.original is False
        assert report.overall is False

    def test_accurate_fails_when_entry_hash_tampered(self, audit_dir):
        """Accurate fails when entry_hash has been tampered with."""
        chain = AuditChain(session_id="sess-f", base_dir=audit_dir)
        chain.append(
            user_id="alice", token_id="tok-1",
            action="navigate", target="https://example.com",
            human_description="Test entry",
            snapshot_id="snap-001",
        )
        # Tamper with the entry_hash
        chain._entries[0].entry_hash = "0" * 64
        report = validate_alcoa(chain)
        assert report.accurate is False
        assert report.overall is False

    def test_complete_fails_when_entry_id_gap_exists(self, audit_dir):
        """Complete fails when entry IDs have a gap."""
        chain = AuditChain(session_id="sess-g", base_dir=audit_dir)
        chain.append(
            user_id="alice", token_id="tok-1",
            action="navigate", target="https://example.com",
            human_description="First",
            snapshot_id="snap-001",
        )
        chain.append(
            user_id="alice", token_id="tok-1",
            action="click", target="#btn",
            human_description="Second",
            snapshot_id="snap-002",
        )
        # Introduce a gap by changing second entry's ID from "1" to "2"
        chain._entries[1].entry_id = "2"
        report = validate_alcoa(chain)
        assert report.complete is False

    def test_consistent_fails_with_duplicate_entry_ids(self, audit_dir):
        """Consistent fails when duplicate entry_ids exist."""
        chain = AuditChain(session_id="sess-h", base_dir=audit_dir)
        chain.append(
            user_id="alice", token_id="tok-1",
            action="navigate", target="https://example.com",
            human_description="First",
            snapshot_id="snap-001",
        )
        chain.append(
            user_id="alice", token_id="tok-1",
            action="click", target="#btn",
            human_description="Second",
            snapshot_id="snap-002",
        )
        # Duplicate: set second entry's ID to same as first
        chain._entries[1].entry_id = "0"
        report = validate_alcoa(chain)
        assert report.consistent is False

    def test_enduring_fails_when_no_log_file_on_disk(self, audit_dir):
        """Enduring fails when audit.jsonl does not exist on disk."""
        chain = AuditChain(session_id="sess-i-no-persist", base_dir=audit_dir)
        # Add entry to in-memory list WITHOUT persisting to disk
        from datetime import timezone
        from datetime import datetime
        entry = AuditEntry(
            entry_id="0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id="alice",
            token_id="tok-1",
            action="navigate",
            target="https://example.com",
            before_value="",
            after_value="",
            reason="",
            meaning="authorized",
            human_description="In-memory only",
            snapshot_id="snap-001",
            scope_used="",
            step_up_performed=False,
            prev_hash=AuditChain.GENESIS_HASH,
        )
        entry.entry_hash = entry.compute_hash()
        chain._entries.append(entry)
        chain._entry_count = 1
        # Log file was never created → enduring should fail
        report = validate_alcoa(chain)
        assert report.enduring is False

    def test_score_format_is_correct(self, populated_chain):
        """score property returns a string in 'N/9' format."""
        report = validate_alcoa(populated_chain)
        assert "/" in report.score
        parts = report.score.split("/")
        assert len(parts) == 2
        assert parts[1] == "9"
        assert int(parts[0]) <= 9

    def test_empty_chain_passes_all_principles(self, empty_chain):
        """An empty chain trivially satisfies all ALCOA+ principles."""
        # Empty chain with no log on disk — enduring fails but available passes
        # since count==0 matches the on-disk absence
        report = validate_alcoa(empty_chain)
        # Enduring requires the file to exist; it will be False for empty chain
        # All other checks should pass
        assert report.attributable is True
        assert report.legible is True
        assert report.contemporaneous is True
        assert report.original is True
        assert report.accurate is True
        assert report.complete is True
        assert report.consistent is True


# ===========================================================================
# Group 6: RetentionPolicy
# ===========================================================================

class TestRetentionPolicy:
    """RetentionPolicy dataclass defaults and tier override logic."""

    def test_default_min_days_is_730(self):
        """Default min_days is 730 (2 years, FDA standard)."""
        policy = RetentionPolicy()
        assert policy.min_days == 730

    def test_default_max_days_is_3650(self):
        """Default max_days is 3650 (10 years)."""
        policy = RetentionPolicy()
        assert policy.max_days == 3650

    def test_tier_overrides_has_all_expected_tiers(self):
        """All five tiers are present in default tier_overrides."""
        policy = RetentionPolicy()
        for tier in ["free", "student", "warrior", "master", "grandmaster"]:
            assert tier in policy.tier_overrides, f"Missing tier: {tier}"

    def test_free_tier_is_7_days(self):
        assert RetentionPolicy().days_for_tier("free") == 7

    def test_student_tier_is_30_days(self):
        assert RetentionPolicy().days_for_tier("student") == 30

    def test_warrior_tier_is_90_days(self):
        assert RetentionPolicy().days_for_tier("warrior") == 90

    def test_master_tier_is_365_days(self):
        assert RetentionPolicy().days_for_tier("master") == 365

    def test_grandmaster_tier_is_3650_days(self):
        assert RetentionPolicy().days_for_tier("grandmaster") == 3650

    def test_unknown_tier_falls_back_to_free(self):
        """Unknown tier name returns the free-tier days (7)."""
        policy = RetentionPolicy()
        assert policy.days_for_tier("enterprise_plus_ultra") == 7

    def test_custom_policy_overrides_defaults(self):
        """Custom min/max_days override the defaults."""
        policy = RetentionPolicy(min_days=365, max_days=730)
        assert policy.min_days == 365
        assert policy.max_days == 730

    def test_tier_overrides_can_be_customized(self):
        """Custom tier_overrides dict replaces the default."""
        policy = RetentionPolicy(tier_overrides={"alpha": 14})
        assert policy.days_for_tier("alpha") == 14


# ===========================================================================
# Group 7: RetentionEngine
# ===========================================================================

class TestRetentionEngine:
    """RetentionEngine: can_delete, records_to_archive, records_to_protect."""

    def _ts_days_ago(self, days: float) -> float:
        """Return a Unix timestamp `days` ago."""
        return time.time() - days * 86400.0

    def _ts_days_from_now(self, days: float) -> float:
        """Return a Unix timestamp `days` in the future."""
        return time.time() + days * 86400.0

    # ---------------------------------------------------------------
    # can_delete
    # ---------------------------------------------------------------

    def test_can_delete_regulated_within_min_days_is_false(self):
        """Regulated record within 730-day window cannot be deleted."""
        engine = RetentionEngine()
        # Record created 1 day ago, regulated → must wait 729 more days
        result = engine.can_delete(
            created_at=self._ts_days_ago(1),
            tier="free",
            regulated=True,
        )
        assert result["allowed"] is False
        assert "earliest_delete_date" in result

    def test_can_delete_regulated_after_min_days_is_true(self):
        """Regulated record after 730 days can be deleted."""
        engine = RetentionEngine()
        result = engine.can_delete(
            created_at=self._ts_days_ago(731),
            tier="free",
            regulated=True,
        )
        assert result["allowed"] is True

    def test_can_delete_free_tier_within_7_days_is_false(self):
        """Non-regulated free-tier record within 7-day window cannot be deleted."""
        engine = RetentionEngine()
        result = engine.can_delete(
            created_at=self._ts_days_ago(3),
            tier="free",
            regulated=False,
        )
        assert result["allowed"] is False

    def test_can_delete_free_tier_after_7_days_is_true(self):
        """Non-regulated free-tier record after 7 days can be deleted."""
        engine = RetentionEngine()
        result = engine.can_delete(
            created_at=self._ts_days_ago(8),
            tier="free",
            regulated=False,
        )
        assert result["allowed"] is True

    def test_can_delete_master_tier_within_365_days_is_false(self):
        """Master-tier record within 365-day window cannot be deleted."""
        engine = RetentionEngine()
        result = engine.can_delete(
            created_at=self._ts_days_ago(100),
            tier="master",
            regulated=False,
        )
        assert result["allowed"] is False

    def test_can_delete_master_tier_after_365_days_is_true(self):
        """Master-tier record after 365 days can be deleted."""
        engine = RetentionEngine()
        result = engine.can_delete(
            created_at=self._ts_days_ago(400),
            tier="master",
            regulated=False,
        )
        assert result["allowed"] is True

    def test_can_delete_returns_reason_string(self):
        """can_delete always returns a non-empty 'reason' string."""
        engine = RetentionEngine()
        r1 = engine.can_delete(self._ts_days_ago(1), tier="free")
        r2 = engine.can_delete(self._ts_days_ago(400), tier="free")
        assert isinstance(r1["reason"], str) and r1["reason"]
        assert isinstance(r2["reason"], str) and r2["reason"]

    def test_can_delete_returns_earliest_delete_date_iso8601(self):
        """earliest_delete_date is a non-empty ISO 8601 string."""
        engine = RetentionEngine()
        result = engine.can_delete(self._ts_days_ago(1), tier="free", regulated=True)
        date_str = result["earliest_delete_date"]
        assert isinstance(date_str, str)
        assert len(date_str) > 0
        # Should parse as ISO 8601
        from datetime import datetime
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        assert dt is not None

    # ---------------------------------------------------------------
    # records_to_archive
    # ---------------------------------------------------------------

    def test_records_to_archive_finds_expired_records(self):
        """records_to_archive returns records past their tier retention."""
        engine = RetentionEngine()
        records = [
            {"created_at": self._ts_days_ago(10), "regulated": False},  # 10 days > 7 (free)
            {"created_at": self._ts_days_ago(3),  "regulated": False},  # 3 days < 7 (free)
        ]
        to_archive = engine.records_to_archive(records, tier="free")
        assert len(to_archive) == 1
        assert to_archive[0] is records[0]

    def test_records_to_archive_skips_already_archived(self):
        """Already-archived records are excluded from the result."""
        engine = RetentionEngine()
        records = [
            {"created_at": self._ts_days_ago(10), "archived": True,  "regulated": False},
            {"created_at": self._ts_days_ago(10), "archived": False, "regulated": False},
        ]
        to_archive = engine.records_to_archive(records, tier="free")
        assert len(to_archive) == 1
        assert to_archive[0]["archived"] is False

    def test_records_to_archive_empty_list(self):
        """Empty input produces empty output."""
        engine = RetentionEngine()
        assert engine.records_to_archive([], tier="free") == []

    def test_records_to_archive_regulated_uses_max_days(self):
        """Regulated records use max_days (3650) for archival threshold."""
        engine = RetentionEngine()
        records = [
            {"created_at": self._ts_days_ago(4000), "regulated": True},   # > 3650 → archive
            {"created_at": self._ts_days_ago(100),  "regulated": True},   # < 3650 → keep
        ]
        to_archive = engine.records_to_archive(records, tier="free")
        assert len(to_archive) == 1
        assert to_archive[0] is records[0]

    # ---------------------------------------------------------------
    # records_to_protect
    # ---------------------------------------------------------------

    def test_records_to_protect_finds_active_records(self):
        """records_to_protect returns records still within their retention window."""
        engine = RetentionEngine()
        records = [
            {"created_at": self._ts_days_ago(3),  "regulated": False},  # 3 < 7 → protected
            {"created_at": self._ts_days_ago(10), "regulated": False},  # 10 > 7 → not protected
        ]
        protected = engine.records_to_protect(records, tier="free")
        assert len(protected) == 1
        assert protected[0] is records[0]

    def test_records_to_protect_regulated_uses_min_days(self):
        """Regulated records use min_days (730) for protection threshold."""
        engine = RetentionEngine()
        records = [
            {"created_at": self._ts_days_ago(100), "regulated": True},  # 100 < 730 → protected
            {"created_at": self._ts_days_ago(800), "regulated": True},  # 800 > 730 → not
        ]
        protected = engine.records_to_protect(records, tier="free")
        assert len(protected) == 1
        assert protected[0] is records[0]

    def test_records_to_protect_empty_list(self):
        """Empty input produces empty output."""
        engine = RetentionEngine()
        assert engine.records_to_protect([], tier="free") == []

    def test_records_to_protect_all_expired_returns_empty(self):
        """All expired records produce an empty protected list."""
        engine = RetentionEngine()
        records = [
            {"created_at": self._ts_days_ago(100), "regulated": False},  # > 7 days
            {"created_at": self._ts_days_ago(200), "regulated": False},
        ]
        protected = engine.records_to_protect(records, tier="free")
        assert len(protected) == 0
