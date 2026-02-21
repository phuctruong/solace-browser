"""
OAuth3 Core Module — Comprehensive Test Suite
Target: 80+ tests
Rung: 641 (local correctness)

Tests cover:
  - Token creation, validation, expiry, SHA-256 hash
  - Scope validation (valid, invalid, well-formed, mixed)
  - High-risk scope detection
  - Enforcement gate checks (all 4 gates via ScopeGate)
  - Token revocation (single, all-for-subject, cleanup)
  - Edge cases: empty scopes, expired tokens, revoked tokens
  - Platform grouping
  - Step-up requirement detection
  - enforce_scopes() standalone function
  - TokenStore CRUD
  - Frozen dataclass immutability

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_oauth3_core.py -v

Reference: oauth3-spec-v0.1.md
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import uuid

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from oauth3.token import (
    AgencyToken,
    create_token,
    validate_token,
    is_expired,
    parse_iso8601,
    _compute_signature_stub,
    DEFAULT_TTL_SECONDS,
    MAX_TTL_SECONDS,
)
from oauth3.scopes import (
    SCOPE_REGISTRY,
    ALL_SCOPES,
    HIGH_RISK_SCOPES,
    DESTRUCTIVE_SCOPES,
    STEP_UP_REQUIRED_SCOPES,
    SCOPES,
    validate_scopes,
    get_high_risk_scopes,
    group_by_platform,
    get_scope_description,
    get_scope_risk_level,
    is_step_up_required,
    _scope_is_well_formed,
)
from oauth3.enforcement import (
    ScopeGate,
    ScopeGateResult,
    GateResult,
    enforce_scopes,
    require_step_up,
    check_token_valid,
    check_scope,
    check_step_up,
    build_evidence_token_entry,
    GATE_PASS,
    GATE_BLOCKED,
)
from oauth3.revocation import (
    TokenStore,
    revoke_token,
    revoke_all_for_subject,
    get_active_tokens,
    cleanup_expired,
)


# ---------------------------------------------------------------------------
# Constants for test data
# ---------------------------------------------------------------------------

ISSUER = "https://solaceagi.com"
SUBJECT = "user:phuc@example.com"
LOW_SCOPE = "linkedin.read.feed"
HIGH_SCOPE = "linkedin.post.text"
GMAIL_LOW = "gmail.read.inbox"
GMAIL_HIGH = "gmail.send.email"
REDDIT_LOW = "reddit.read.feed"
REDDIT_HIGH = "reddit.post.text"
GITHUB_MED = "github.create.issue"
HN_LOW = "hackernews.read.feed"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_token():
    """A fresh, non-expired, non-revoked token."""
    return create_token(
        issuer=ISSUER,
        subject=SUBJECT,
        scopes=[LOW_SCOPE, GMAIL_LOW],
        intent="Read LinkedIn feed and Gmail for daily digest",
        ttl_seconds=3600,
    )


@pytest.fixture
def expired_token():
    """A token that is already expired."""
    # Manually build with past expires_at
    now = datetime.now(timezone.utc)
    past = (now - timedelta(hours=2)).isoformat()
    token_id = str(uuid.uuid4())
    stub = _compute_signature_stub(
        token_id=token_id,
        issuer=ISSUER,
        subject=SUBJECT,
        scopes=[LOW_SCOPE],
        intent="Test expired",
        issued_at=(now - timedelta(hours=3)).isoformat(),
        expires_at=past,
    )
    return AgencyToken(
        token_id=token_id,
        issuer=ISSUER,
        subject=SUBJECT,
        scopes=(LOW_SCOPE,),
        intent="Test expired",
        issued_at=(now - timedelta(hours=3)).isoformat(),
        expires_at=past,
        revoked=False,
        revoked_at=None,
        signature_stub=stub,
    )


@pytest.fixture
def revoked_token():
    """A token that has been revoked."""
    token = create_token(
        issuer=ISSUER,
        subject=SUBJECT,
        scopes=[LOW_SCOPE],
        intent="Test revocation",
    )
    import dataclasses
    return dataclasses.replace(
        token,
        revoked=True,
        revoked_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def store():
    """A fresh in-memory TokenStore."""
    return TokenStore()


@pytest.fixture
def store_with_token(store, valid_token):
    """A TokenStore with one active token."""
    store.add(valid_token)
    return store, valid_token


# ===========================================================================
# Section 1: Token Creation
# ===========================================================================

class TestTokenCreation:
    """Tests for AgencyToken creation and field correctness."""

    def test_create_token_returns_agency_token(self, valid_token):
        assert isinstance(valid_token, AgencyToken)

    def test_token_id_is_uuid4(self, valid_token):
        # UUID4 format: 8-4-4-4-12 (36 chars with hyphens)
        token_id = valid_token.token_id
        assert len(token_id) == 36
        parts = token_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_token_issuer_matches(self, valid_token):
        assert valid_token.issuer == ISSUER

    def test_token_subject_matches(self, valid_token):
        assert valid_token.subject == SUBJECT

    def test_token_scopes_correct(self, valid_token):
        assert LOW_SCOPE in valid_token.scopes
        assert GMAIL_LOW in valid_token.scopes

    def test_token_intent_matches(self, valid_token):
        assert "LinkedIn" in valid_token.intent or "digest" in valid_token.intent.lower()

    def test_token_not_revoked_on_creation(self, valid_token):
        assert valid_token.revoked is False
        assert valid_token.revoked_at is None

    def test_token_issued_at_is_utc_iso8601(self, valid_token):
        dt = parse_iso8601(valid_token.issued_at)
        assert dt.tzinfo is not None

    def test_token_expires_at_is_utc_iso8601(self, valid_token):
        dt = parse_iso8601(valid_token.expires_at)
        assert dt.tzinfo is not None

    def test_token_expires_after_issued(self, valid_token):
        issued = parse_iso8601(valid_token.issued_at)
        expires = parse_iso8601(valid_token.expires_at)
        assert expires > issued

    def test_token_ttl_approximately_correct(self):
        before = datetime.now(timezone.utc)
        token = create_token(ISSUER, SUBJECT, [LOW_SCOPE], "test", ttl_seconds=3600)
        after = datetime.now(timezone.utc)
        expires = parse_iso8601(token.expires_at)
        assert expires >= before + timedelta(seconds=3598)
        assert expires <= after + timedelta(seconds=3602)

    def test_token_signature_stub_present(self, valid_token):
        assert valid_token.signature_stub.startswith("sha256:")
        assert len(valid_token.signature_stub) > 10

    def test_token_is_frozen_dataclass(self, valid_token):
        """Frozen dataclass: mutation raises FrozenInstanceError."""
        with pytest.raises(Exception):  # FrozenInstanceError
            valid_token.revoked = True

    def test_create_token_convenience_function(self):
        token = create_token(ISSUER, SUBJECT, [LOW_SCOPE], "test convenience")
        assert isinstance(token, AgencyToken)
        assert LOW_SCOPE in token.scopes

    def test_create_rejects_unknown_scope(self):
        with pytest.raises(ValueError, match="Unknown scope"):
            create_token(ISSUER, SUBJECT, ["fake.scope.unknown"], "test")

    def test_create_rejects_two_segment_scope(self):
        """Two-segment scope not in registry → rejected."""
        with pytest.raises(ValueError, match="Unknown scope"):
            create_token(ISSUER, SUBJECT, ["linkedin.create_post"], "test")

    def test_create_rejects_empty_scopes(self):
        with pytest.raises(ValueError, match="scopes must not be empty"):
            create_token(ISSUER, SUBJECT, [], "test")

    def test_create_rejects_ttl_over_max(self):
        with pytest.raises(ValueError, match="ttl_seconds"):
            create_token(ISSUER, SUBJECT, [LOW_SCOPE], "test", ttl_seconds=86401)

    def test_create_rejects_zero_ttl(self):
        with pytest.raises(ValueError):
            create_token(ISSUER, SUBJECT, [LOW_SCOPE], "test", ttl_seconds=0)

    def test_scopes_stored_as_tuple(self, valid_token):
        """Frozen dataclass uses tuple for immutability."""
        assert isinstance(valid_token.scopes, tuple)


# ===========================================================================
# Section 2: Token Validation and Expiry
# ===========================================================================

class TestTokenValidation:
    """Tests for validate_token() and is_expired()."""

    def test_valid_token_passes(self, valid_token):
        assert validate_token(valid_token) is True

    def test_validate_returns_true_for_fresh_token(self, valid_token):
        is_valid, error = valid_token.validate()
        assert is_valid is True
        assert error == ""

    def test_expired_token_fails(self, expired_token):
        assert validate_token(expired_token) is False

    def test_expired_token_error_message(self, expired_token):
        is_valid, error = expired_token.validate()
        assert is_valid is False
        assert "expired" in error.lower()

    def test_revoked_token_fails(self, revoked_token):
        assert validate_token(revoked_token) is False

    def test_revoked_token_error_message(self, revoked_token):
        is_valid, error = revoked_token.validate()
        assert is_valid is False
        assert "revoked" in error.lower()

    def test_is_expired_false_for_fresh_token(self, valid_token):
        assert is_expired(valid_token) is False

    def test_is_expired_true_for_expired_token(self, expired_token):
        assert is_expired(expired_token) is True

    def test_validate_token_standalone_expired(self, expired_token):
        assert validate_token(expired_token) is False

    def test_has_scope_returns_true(self, valid_token):
        assert valid_token.has_scope(LOW_SCOPE) is True

    def test_has_scope_returns_false(self, valid_token):
        assert valid_token.has_scope(HIGH_SCOPE) is False


# ===========================================================================
# Section 3: SHA-256 Hash and Signature Stub
# ===========================================================================

class TestSignatureStub:
    """Tests for SHA-256 audit trail hash."""

    def test_signature_stub_is_sha256_prefixed(self, valid_token):
        assert valid_token.signature_stub.startswith("sha256:")

    def test_sha256_hash_method_matches_stub(self, valid_token):
        assert valid_token.sha256_hash() == valid_token.signature_stub

    def test_sha256_hash_is_deterministic(self, valid_token):
        h1 = valid_token.sha256_hash()
        h2 = valid_token.sha256_hash()
        assert h1 == h2

    def test_different_tokens_have_different_stubs(self):
        t1 = create_token(ISSUER, SUBJECT, [LOW_SCOPE], "intent A")
        t2 = create_token(ISSUER, SUBJECT, [LOW_SCOPE], "intent B")
        assert t1.signature_stub != t2.signature_stub

    def test_sha256_hex_length(self, valid_token):
        # "sha256:" (7 chars) + 64 hex chars = 71
        assert len(valid_token.signature_stub) == 71

    def test_compute_signature_stub_internal(self):
        stub = _compute_signature_stub(
            token_id="test-id",
            issuer=ISSUER,
            subject=SUBJECT,
            scopes=[LOW_SCOPE],
            intent="test intent",
            issued_at="2026-02-21T10:00:00+00:00",
            expires_at="2026-02-21T11:00:00+00:00",
        )
        assert stub.startswith("sha256:")
        assert len(stub) == 71


# ===========================================================================
# Section 4: Scope Validation
# ===========================================================================

class TestScopeValidation:
    """Tests for validate_scopes() and scope registry."""

    def test_scope_registry_has_30_plus_entries(self):
        assert len(SCOPE_REGISTRY) >= 30

    def test_all_registered_scopes_valid(self):
        for scope in SCOPE_REGISTRY:
            assert _scope_is_well_formed(scope), f"Malformed scope: {scope}"

    def test_validate_single_valid_scope(self):
        is_valid, invalid = validate_scopes([LOW_SCOPE])
        assert is_valid is True
        assert invalid == []

    def test_validate_multiple_valid_scopes(self):
        is_valid, invalid = validate_scopes([LOW_SCOPE, GMAIL_LOW, REDDIT_LOW, HN_LOW])
        assert is_valid is True
        assert invalid == []

    def test_validate_unknown_scope_fails(self):
        """Truly unknown scopes (not in registry or legacy aliases) are rejected."""
        is_valid, invalid = validate_scopes(["totally.fake.scope"])
        assert is_valid is False
        assert "totally.fake.scope" in invalid

    def test_validate_fake_scope_fails(self):
        is_valid, invalid = validate_scopes(["fake.scope.xyz"])
        assert is_valid is False
        assert "fake.scope.xyz" in invalid

    def test_validate_two_segment_scope_fails(self):
        """Two-segment scopes (old format) are rejected."""
        is_valid, invalid = validate_scopes(["linkedin.read"])
        assert is_valid is False
        assert "linkedin.read" in invalid

    def test_validate_wildcard_scope_fails(self):
        """Wildcards not supported in v0.1."""
        is_valid, invalid = validate_scopes(["linkedin.*.feed"])
        assert is_valid is False

    def test_validate_mixed_valid_invalid(self):
        is_valid, invalid = validate_scopes([LOW_SCOPE, "fake.scope.xyz"])
        assert is_valid is False
        assert "fake.scope.xyz" in invalid
        assert LOW_SCOPE not in invalid

    def test_validate_empty_list_returns_valid(self):
        """Empty list: no invalid scopes, vacuously valid."""
        is_valid, invalid = validate_scopes([])
        assert is_valid is True
        assert invalid == []

    def test_scope_registry_platforms_covered(self):
        platforms = {meta["platform"] for meta in SCOPE_REGISTRY.values()}
        assert "linkedin" in platforms
        assert "gmail" in platforms
        assert "reddit" in platforms
        assert "github" in platforms
        assert "hackernews" in platforms

    def test_all_scopes_have_description(self):
        for scope, meta in SCOPE_REGISTRY.items():
            assert "description" in meta, f"Missing description for {scope}"
            assert isinstance(meta["description"], str)
            assert len(meta["description"]) > 0

    def test_all_scopes_have_risk_level(self):
        for scope, meta in SCOPE_REGISTRY.items():
            assert meta["risk_level"] in ("low", "medium", "high"), (
                f"Invalid risk_level for {scope}: {meta['risk_level']}"
            )

    def test_all_scopes_have_destructive_flag(self):
        for scope, meta in SCOPE_REGISTRY.items():
            assert isinstance(meta["destructive"], bool), (
                f"destructive must be bool for {scope}"
            )

    def test_scopes_compat_alias_populated(self):
        """SCOPES dict (backward compat alias) includes all registry scopes."""
        # SCOPES includes both triple-segment and legacy two-segment scopes
        assert len(SCOPES) >= len(SCOPE_REGISTRY)
        for scope in SCOPE_REGISTRY:
            assert scope in SCOPES


# ===========================================================================
# Section 5: High-Risk Scope Detection
# ===========================================================================

class TestHighRiskScopeDetection:
    """Tests for high-risk scope identification."""

    def test_high_risk_scopes_not_empty(self):
        assert len(HIGH_RISK_SCOPES) > 0

    def test_linkedin_post_text_is_high_risk(self):
        assert HIGH_SCOPE in HIGH_RISK_SCOPES

    def test_gmail_send_email_is_high_risk(self):
        assert GMAIL_HIGH in HIGH_RISK_SCOPES

    def test_linkedin_read_feed_is_not_high_risk(self):
        assert LOW_SCOPE not in HIGH_RISK_SCOPES

    def test_gmail_read_inbox_is_not_high_risk(self):
        assert GMAIL_LOW not in HIGH_RISK_SCOPES

    def test_get_high_risk_scopes_returns_subset(self):
        mixed = [LOW_SCOPE, HIGH_SCOPE, GMAIL_LOW, GMAIL_HIGH]
        high = get_high_risk_scopes(mixed)
        assert HIGH_SCOPE in high
        assert GMAIL_HIGH in high
        assert LOW_SCOPE not in high
        assert GMAIL_LOW not in high

    def test_get_high_risk_scopes_empty_list(self):
        assert get_high_risk_scopes([]) == []

    def test_get_high_risk_scopes_all_low(self):
        lows = [LOW_SCOPE, GMAIL_LOW, REDDIT_LOW, HN_LOW]
        assert get_high_risk_scopes(lows) == []

    def test_is_step_up_required_true_for_destructive(self):
        assert is_step_up_required(HIGH_SCOPE) is True
        assert is_step_up_required(GMAIL_HIGH) is True
        assert is_step_up_required("linkedin.delete.post") is True

    def test_is_step_up_required_false_for_read(self):
        assert is_step_up_required(LOW_SCOPE) is False
        assert is_step_up_required(GMAIL_LOW) is False

    def test_step_up_required_scopes_alias_populated(self):
        """STEP_UP_REQUIRED_SCOPES backward compat alias."""
        assert len(STEP_UP_REQUIRED_SCOPES) > 0
        for scope in STEP_UP_REQUIRED_SCOPES:
            assert scope in HIGH_RISK_SCOPES

    def test_get_scope_description_low_risk(self):
        desc = get_scope_description(LOW_SCOPE)
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_get_scope_description_unknown_returns_none(self):
        assert get_scope_description("fake.scope.xyz") is None

    def test_get_scope_risk_level_low(self):
        assert get_scope_risk_level(LOW_SCOPE) == "low"

    def test_get_scope_risk_level_high(self):
        assert get_scope_risk_level(HIGH_SCOPE) == "high"

    def test_get_scope_risk_level_unknown_is_high(self):
        """Fail-closed: unknown scope → high risk."""
        assert get_scope_risk_level("completely.fake.scope") == "high"


# ===========================================================================
# Section 6: Platform Grouping
# ===========================================================================

class TestPlatformGrouping:
    """Tests for group_by_platform()."""

    def test_group_by_platform_basic(self):
        scopes = [LOW_SCOPE, HIGH_SCOPE, GMAIL_LOW, REDDIT_LOW]
        grouped = group_by_platform(scopes)
        assert "linkedin" in grouped
        assert "gmail" in grouped
        assert "reddit" in grouped

    def test_group_by_platform_linkedin_scopes(self):
        scopes = [LOW_SCOPE, HIGH_SCOPE]
        grouped = group_by_platform(scopes)
        assert LOW_SCOPE in grouped["linkedin"]
        assert HIGH_SCOPE in grouped["linkedin"]

    def test_group_by_platform_gmail_scopes(self):
        scopes = [GMAIL_LOW, GMAIL_HIGH]
        grouped = group_by_platform(scopes)
        assert GMAIL_LOW in grouped["gmail"]
        assert GMAIL_HIGH in grouped["gmail"]

    def test_group_by_platform_empty_list(self):
        grouped = group_by_platform([])
        assert grouped == {}

    def test_group_by_platform_mixed_platforms(self):
        scopes = [LOW_SCOPE, GMAIL_LOW, REDDIT_LOW, HN_LOW, GITHUB_MED]
        grouped = group_by_platform(scopes)
        assert len(grouped) == 5

    def test_group_by_platform_single_scope(self):
        grouped = group_by_platform([GMAIL_LOW])
        assert grouped == {"gmail": [GMAIL_LOW]}


# ===========================================================================
# Section 7: ScopeGate — G1 through G4
# ===========================================================================

class TestScopeGateG1Schema:
    """G1: Schema check."""

    def test_g1_passes_valid_token(self, valid_token):
        gate = ScopeGate(valid_token, [LOW_SCOPE])
        result = gate.g1_schema()
        assert result.passed is True
        assert result.gate == "G1"

    def test_g1_blocked_when_token_is_none(self):
        # ScopeGate with None token (should fail gracefully)
        gate = ScopeGate(None, [LOW_SCOPE])  # type: ignore
        result = gate.g1_schema()
        assert result.passed is False
        assert result.error_code == "OAUTH3_MALFORMED_TOKEN"


class TestScopeGateG2Expiry:
    """G2: Expiry check."""

    def test_g2_passes_fresh_token(self, valid_token):
        gate = ScopeGate(valid_token, [LOW_SCOPE])
        result = gate.g2_expiry()
        assert result.passed is True
        assert result.gate == "G2"

    def test_g2_blocked_expired_token(self, expired_token):
        gate = ScopeGate(expired_token, [LOW_SCOPE])
        result = gate.g2_expiry()
        assert result.passed is False
        assert result.error_code == "OAUTH3_TOKEN_EXPIRED"
        assert "G2" == result.gate

    def test_g2_error_detail_mentions_expiry(self, expired_token):
        gate = ScopeGate(expired_token, [LOW_SCOPE])
        result = gate.g2_expiry()
        assert "expired" in result.error_detail.lower()


class TestScopeGateG3Scope:
    """G3: Scope check."""

    def test_g3_passes_when_scope_in_token(self, valid_token):
        gate = ScopeGate(valid_token, [LOW_SCOPE])
        result, missing = gate.g3_scope()
        assert result.passed is True
        assert missing == []

    def test_g3_blocked_when_scope_missing(self, valid_token):
        gate = ScopeGate(valid_token, [HIGH_SCOPE])  # HIGH_SCOPE not in token
        result, missing = gate.g3_scope()
        assert result.passed is False
        assert HIGH_SCOPE in missing
        assert result.error_code == "OAUTH3_SCOPE_DENIED"

    def test_g3_multiple_scopes_all_present(self, valid_token):
        gate = ScopeGate(valid_token, [LOW_SCOPE, GMAIL_LOW])
        result, missing = gate.g3_scope()
        assert result.passed is True
        assert missing == []

    def test_g3_partial_missing_scopes(self, valid_token):
        gate = ScopeGate(valid_token, [LOW_SCOPE, HIGH_SCOPE])
        result, missing = gate.g3_scope()
        assert result.passed is False
        assert HIGH_SCOPE in missing
        assert LOW_SCOPE not in missing

    def test_g3_empty_required_scopes_passes(self, valid_token):
        gate = ScopeGate(valid_token, [])
        result, missing = gate.g3_scope()
        assert result.passed is True
        assert missing == []


class TestScopeGateG4Revocation:
    """G4: Revocation check."""

    def test_g4_passes_non_revoked_token(self, valid_token):
        gate = ScopeGate(valid_token, [LOW_SCOPE])
        result = gate.g4_revocation()
        assert result.passed is True
        assert result.gate == "G4"

    def test_g4_blocked_revoked_token(self, revoked_token):
        gate = ScopeGate(revoked_token, [LOW_SCOPE])
        result = gate.g4_revocation()
        assert result.passed is False
        assert result.error_code == "OAUTH3_TOKEN_REVOKED"

    def test_g4_error_detail_mentions_revocation(self, revoked_token):
        gate = ScopeGate(revoked_token, [LOW_SCOPE])
        result = gate.g4_revocation()
        assert "revoked" in result.error_detail.lower()


class TestScopeGateCheckAll:
    """ScopeGate.check_all() — composite gate check."""

    def test_check_all_passes_valid_token_valid_scope(self, valid_token):
        gate = ScopeGate(valid_token, [LOW_SCOPE])
        result = gate.check_all()
        assert result.allowed is True
        assert result.blocking_gate is None
        assert result.error_code is None

    def test_check_all_blocked_by_g2_expired(self, expired_token):
        gate = ScopeGate(expired_token, [LOW_SCOPE])
        result = gate.check_all()
        assert result.allowed is False
        assert result.blocking_gate == "G2"
        assert result.error_code == "OAUTH3_TOKEN_EXPIRED"

    def test_check_all_blocked_by_g3_missing_scope(self, valid_token):
        gate = ScopeGate(valid_token, [HIGH_SCOPE])
        result = gate.check_all()
        assert result.allowed is False
        assert result.blocking_gate == "G3"
        assert HIGH_SCOPE in result.missing_scopes

    def test_check_all_blocked_by_g4_revoked(self, revoked_token):
        gate = ScopeGate(revoked_token, [LOW_SCOPE])
        result = gate.check_all()
        assert result.allowed is False
        assert result.blocking_gate == "G4"
        assert result.error_code == "OAUTH3_TOKEN_REVOKED"

    def test_check_all_returns_gate_results_list(self, valid_token):
        gate = ScopeGate(valid_token, [LOW_SCOPE])
        result = gate.check_all()
        assert isinstance(result.gate_results, list)
        assert len(result.gate_results) == 4  # all gates ran

    def test_check_all_short_circuits_on_g2_failure(self, expired_token):
        """When G2 fails, G3/G4 results should not be appended."""
        gate = ScopeGate(expired_token, [LOW_SCOPE])
        result = gate.check_all()
        # Only G1 and G2 should be in gate_results
        gate_ids = [r.gate for r in result.gate_results]
        assert "G1" in gate_ids
        assert "G2" in gate_ids
        assert "G3" not in gate_ids
        assert "G4" not in gate_ids

    def test_scope_gate_result_is_dataclass(self, valid_token):
        gate = ScopeGate(valid_token, [LOW_SCOPE])
        result = gate.check_all()
        assert isinstance(result, ScopeGateResult)


# ===========================================================================
# Section 8: enforce_scopes() standalone
# ===========================================================================

class TestEnforceScopes:
    """Tests for the enforce_scopes() convenience function."""

    def test_enforce_all_scopes_present(self, valid_token):
        allowed, missing = enforce_scopes(valid_token, [LOW_SCOPE])
        assert allowed is True
        assert missing == []

    def test_enforce_scope_missing(self, valid_token):
        allowed, missing = enforce_scopes(valid_token, [HIGH_SCOPE])
        assert allowed is False
        assert HIGH_SCOPE in missing

    def test_enforce_multiple_scopes_all_present(self, valid_token):
        allowed, missing = enforce_scopes(valid_token, [LOW_SCOPE, GMAIL_LOW])
        assert allowed is True
        assert missing == []

    def test_enforce_partial_missing(self, valid_token):
        allowed, missing = enforce_scopes(valid_token, [LOW_SCOPE, HIGH_SCOPE])
        assert allowed is False
        assert HIGH_SCOPE in missing
        assert LOW_SCOPE not in missing

    def test_enforce_empty_required_scopes(self, valid_token):
        allowed, missing = enforce_scopes(valid_token, [])
        assert allowed is True
        assert missing == []


# ===========================================================================
# Section 9: require_step_up()
# ===========================================================================

class TestRequireStepUp:
    """Tests for the require_step_up() function."""

    def test_require_step_up_true_for_high_risk(self, valid_token):
        assert require_step_up(valid_token, HIGH_SCOPE) is True

    def test_require_step_up_false_for_low_risk(self, valid_token):
        assert require_step_up(valid_token, LOW_SCOPE) is False

    def test_require_step_up_gmail_send(self, valid_token):
        assert require_step_up(valid_token, GMAIL_HIGH) is True

    def test_require_step_up_reddit_post(self, valid_token):
        assert require_step_up(valid_token, REDDIT_HIGH) is True

    def test_require_step_up_reddit_read(self, valid_token):
        assert require_step_up(valid_token, REDDIT_LOW) is False


# ===========================================================================
# Section 10: TokenStore — CRUD
# ===========================================================================

class TestTokenStoreCRUD:
    """Tests for TokenStore add/get/remove."""

    def test_add_and_get_token(self, store, valid_token):
        store.add(valid_token)
        retrieved = store.get(valid_token.token_id)
        assert retrieved is not None
        assert retrieved.token_id == valid_token.token_id

    def test_get_missing_token_returns_none(self, store):
        assert store.get("nonexistent-id") is None

    def test_remove_token(self, store, valid_token):
        store.add(valid_token)
        result = store.remove(valid_token.token_id)
        assert result is True
        assert store.get(valid_token.token_id) is None

    def test_remove_nonexistent_returns_false(self, store):
        result = store.remove("nonexistent-id")
        assert result is False

    def test_all_tokens_empty_store(self, store):
        assert store.all_tokens() == []

    def test_all_tokens_multiple(self, store):
        t1 = create_token(ISSUER, SUBJECT, [LOW_SCOPE], "t1")
        t2 = create_token(ISSUER, SUBJECT, [GMAIL_LOW], "t2")
        store.add(t1)
        store.add(t2)
        all_t = store.all_tokens()
        assert len(all_t) == 2

    def test_store_len(self, store):
        assert len(store) == 0
        store.add(create_token(ISSUER, SUBJECT, [LOW_SCOPE], "test"))
        assert len(store) == 1

    def test_add_overwrites_same_id(self, store, valid_token):
        store.add(valid_token)
        import dataclasses
        updated = dataclasses.replace(valid_token, intent="updated intent")
        store.add(updated)
        assert store.get(valid_token.token_id).intent == "updated intent"


# ===========================================================================
# Section 11: Token Revocation
# ===========================================================================

class TestTokenRevocation:
    """Tests for revocation in TokenStore."""

    def test_revoke_token_marks_revoked(self, store, valid_token):
        store.add(valid_token)
        result = store.revoke(valid_token.token_id)
        assert result is True
        updated = store.get(valid_token.token_id)
        assert updated.revoked is True

    def test_revoke_sets_revoked_at(self, store, valid_token):
        store.add(valid_token)
        store.revoke(valid_token.token_id)
        updated = store.get(valid_token.token_id)
        assert updated.revoked_at is not None
        # revoked_at should parse as a valid ISO 8601 date
        dt = parse_iso8601(updated.revoked_at)
        assert dt is not None

    def test_revoke_nonexistent_returns_false(self, store):
        result = store.revoke("nonexistent-id")
        assert result is False

    def test_revoke_idempotent(self, store, valid_token):
        store.add(valid_token)
        store.revoke(valid_token.token_id)
        result = store.revoke(valid_token.token_id)
        assert result is True  # idempotent — second call also True

    def test_is_revoked_false_before_revocation(self, store, valid_token):
        store.add(valid_token)
        assert store.is_revoked(valid_token.token_id) is False

    def test_is_revoked_true_after_revocation(self, store, valid_token):
        store.add(valid_token)
        store.revoke(valid_token.token_id)
        assert store.is_revoked(valid_token.token_id) is True

    def test_is_revoked_true_for_missing_token(self, store):
        """Fail-closed: missing token treated as revoked."""
        assert store.is_revoked("does-not-exist") is True

    def test_revoke_convenience_function(self, store, valid_token):
        store.add(valid_token)
        result = revoke_token(valid_token.token_id, store=store)
        assert result is True

    def test_revoke_convenience_no_store_returns_false(self, valid_token):
        result = revoke_token(valid_token.token_id, store=None)
        assert result is False


# ===========================================================================
# Section 12: Revoke All for Subject
# ===========================================================================

class TestRevokeAllForSubject:
    """Tests for revoke_all_for_subject()."""

    def test_revoke_all_for_subject_count(self, store):
        subject_a = "user:alice@example.com"
        subject_b = "user:bob@example.com"
        t1 = create_token(ISSUER, subject_a, [LOW_SCOPE], "t1")
        t2 = create_token(ISSUER, subject_a, [GMAIL_LOW], "t2")
        t3 = create_token(ISSUER, subject_b, [LOW_SCOPE], "t3")
        store.add(t1)
        store.add(t2)
        store.add(t3)

        count = store.revoke_all_for_subject(subject_a)
        assert count == 2

    def test_revoke_all_only_targets_subject(self, store):
        subject_a = "user:alice@example.com"
        subject_b = "user:bob@example.com"
        t1 = create_token(ISSUER, subject_a, [LOW_SCOPE], "t1")
        t2 = create_token(ISSUER, subject_b, [LOW_SCOPE], "t2")
        store.add(t1)
        store.add(t2)

        store.revoke_all_for_subject(subject_a)
        assert store.get(t1.token_id).revoked is True
        assert store.get(t2.token_id).revoked is False

    def test_revoke_all_excludes_already_revoked(self, store):
        t1 = create_token(ISSUER, SUBJECT, [LOW_SCOPE], "t1")
        store.add(t1)
        store.revoke(t1.token_id)  # pre-revoke

        count = store.revoke_all_for_subject(SUBJECT)
        assert count == 0  # already revoked — not counted again

    def test_revoke_all_empty_store_returns_zero(self, store):
        count = store.revoke_all_for_subject(SUBJECT)
        assert count == 0

    def test_revoke_all_convenience_function(self, store):
        t1 = create_token(ISSUER, SUBJECT, [LOW_SCOPE], "t1")
        store.add(t1)
        count = revoke_all_for_subject(SUBJECT, store=store)
        assert count == 1


# ===========================================================================
# Section 13: get_active_tokens()
# ===========================================================================

class TestGetActiveTokens:
    """Tests for TokenStore.get_active_tokens()."""

    def test_active_token_returned(self, store, valid_token):
        store.add(valid_token)
        active = store.get_active_tokens(SUBJECT)
        assert len(active) == 1
        assert active[0].token_id == valid_token.token_id

    def test_revoked_token_excluded(self, store, valid_token):
        store.add(valid_token)
        store.revoke(valid_token.token_id)
        active = store.get_active_tokens(SUBJECT)
        assert active == []

    def test_expired_token_excluded(self, store, expired_token):
        store.add(expired_token)
        active = store.get_active_tokens(SUBJECT)
        assert active == []

    def test_only_matching_subject_returned(self, store):
        t1 = create_token(ISSUER, "user:alice@example.com", [LOW_SCOPE], "alice")
        t2 = create_token(ISSUER, "user:bob@example.com", [LOW_SCOPE], "bob")
        store.add(t1)
        store.add(t2)
        alice_tokens = store.get_active_tokens("user:alice@example.com")
        assert len(alice_tokens) == 1
        assert alice_tokens[0].subject == "user:alice@example.com"

    def test_convenience_function_get_active_tokens(self, store, valid_token):
        store.add(valid_token)
        active = get_active_tokens(SUBJECT, store=store)
        assert len(active) == 1


# ===========================================================================
# Section 14: cleanup_expired()
# ===========================================================================

class TestCleanupExpired:
    """Tests for TokenStore.cleanup_expired()."""

    def test_cleanup_removes_expired(self, store, expired_token):
        store.add(expired_token)
        assert len(store) == 1
        count = store.cleanup_expired()
        assert count == 1
        assert len(store) == 0

    def test_cleanup_keeps_fresh_tokens(self, store, valid_token):
        store.add(valid_token)
        count = store.cleanup_expired()
        assert count == 0
        assert len(store) == 1

    def test_cleanup_mixed_tokens(self, store, valid_token, expired_token):
        store.add(valid_token)
        store.add(expired_token)
        count = store.cleanup_expired()
        assert count == 1
        assert len(store) == 1

    def test_cleanup_empty_store(self, store):
        count = store.cleanup_expired()
        assert count == 0

    def test_cleanup_convenience_function(self, store, expired_token):
        store.add(expired_token)
        count = cleanup_expired(store=store)
        assert count == 1


# ===========================================================================
# Section 15: Backward-compat API (check_token_valid, check_scope, check_step_up)
# ===========================================================================

class TestBackwardCompatAPI:
    """Tests for backward-compatible functions used by existing code."""

    def test_check_token_valid_passes_fresh(self, valid_token):
        is_valid, error = check_token_valid(valid_token)
        assert is_valid is True
        assert error == ""

    def test_check_token_valid_fails_expired(self, expired_token):
        is_valid, error = check_token_valid(expired_token)
        assert is_valid is False
        assert "expired" in error.lower()

    def test_check_token_valid_fails_revoked(self, revoked_token):
        is_valid, error = check_token_valid(revoked_token)
        assert is_valid is False
        assert "revoked" in error.lower()

    def test_check_scope_passes(self, valid_token):
        has_scope, error = check_scope(valid_token, LOW_SCOPE)
        assert has_scope is True
        assert error == ""

    def test_check_scope_fails(self, valid_token):
        has_scope, error = check_scope(valid_token, HIGH_SCOPE)
        assert has_scope is False
        assert "insufficient_scope" in error

    def test_check_step_up_returns_false_for_high_risk(self, valid_token):
        can_proceed, error = check_step_up(valid_token, HIGH_SCOPE)
        assert can_proceed is False
        assert "step_up_required" in error

    def test_check_step_up_returns_true_for_low_risk(self, valid_token):
        can_proceed, error = check_step_up(valid_token, LOW_SCOPE)
        assert can_proceed is True
        assert error == ""

    def test_build_evidence_entry(self):
        entry = build_evidence_token_entry(
            token_id="test-uuid",
            scope_used=LOW_SCOPE,
            step_up_performed=False,
            token_expires_at="2026-02-21T11:00:00+00:00",
        )
        assert entry["token_id"] == "test-uuid"
        assert entry["scope_used"] == LOW_SCOPE
        assert entry["step_up_performed"] is False
        assert entry["token_expires_at"] == "2026-02-21T11:00:00+00:00"


# ===========================================================================
# Section 16: Edge Cases
# ===========================================================================

class TestEdgeCases:
    """Edge cases and adversarial inputs."""

    def test_token_with_single_scope(self):
        token = create_token(ISSUER, SUBJECT, [LOW_SCOPE], "single scope test")
        assert len(token.scopes) == 1

    def test_token_with_all_supported_scopes(self):
        """Create token with every registered scope."""
        all_scopes = list(ALL_SCOPES)
        token = create_token(ISSUER, SUBJECT, all_scopes, "all scopes")
        assert len(token.scopes) == len(all_scopes)

    def test_token_to_dict_and_from_dict_round_trip(self, valid_token):
        d = valid_token.to_dict()
        restored = AgencyToken.from_dict(d)
        assert restored.token_id == valid_token.token_id
        assert restored.issuer == valid_token.issuer
        assert restored.subject == valid_token.subject
        assert set(restored.scopes) == set(valid_token.scopes)
        assert restored.intent == valid_token.intent
        assert restored.signature_stub == valid_token.signature_stub

    def test_token_to_json_and_from_json_round_trip(self, valid_token):
        json_str = valid_token.to_json()
        restored = AgencyToken.from_json(json_str)
        assert restored.token_id == valid_token.token_id

    def test_from_dict_null_scopes_raises_value_error(self):
        """null scopes must raise ValueError (null != zero)."""
        data = {
            "token_id": str(uuid.uuid4()),
            "issuer": ISSUER,
            "subject": SUBJECT,
            "scopes": None,
            "intent": "test",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        with pytest.raises(ValueError, match="scopes must be a list"):
            AgencyToken.from_dict(data)

    def test_scope_gate_with_empty_token_scopes(self):
        """Token with no scopes fails G1 (spec §1.2: scopes minItems=1)."""
        # Build a token manually with empty scopes (bypass create validation)
        now = datetime.now(timezone.utc)
        token = AgencyToken(
            token_id=str(uuid.uuid4()),
            issuer=ISSUER,
            subject=SUBJECT,
            scopes=(),   # empty — malformed per spec (minItems: 1)
            intent="empty scopes test",
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
        )
        gate = ScopeGate(token, [LOW_SCOPE])
        result = gate.check_all()
        assert result.allowed is False
        # G1 catches empty scopes (malformed token — spec §1.2 requires minItems: 1)
        assert result.blocking_gate == "G1"

    def test_parse_iso8601_z_suffix(self):
        dt = parse_iso8601("2026-02-21T10:00:00Z")
        assert dt.tzinfo is not None

    def test_parse_iso8601_plus_offset(self):
        dt = parse_iso8601("2026-02-21T10:00:00+00:00")
        assert dt.tzinfo is not None

    def test_token_repr_contains_id(self, valid_token):
        r = repr(valid_token)
        assert valid_token.token_id[:8] in r

    def test_token_store_repr(self, store):
        r = repr(store)
        assert "TokenStore" in r
