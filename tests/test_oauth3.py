"""
OAuth3 Acceptance Tests — Rung 641

All 10 acceptance tests from the Phase 1.5 build prompt.
Tests are pure-Python, no server required (unit tests for the module itself).

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_oauth3.py -v

Rung: 641 (local correctness — all tests must pass before shipping)
"""

import json
import sys
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Ensure src/ is on sys.path for local imports
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from oauth3.token import AgencyToken
from oauth3.scopes import (
    SCOPES,
    STEP_UP_REQUIRED_SCOPES,
    validate_scopes,
    get_scope_description,
    is_step_up_required,
)
from oauth3.enforcement import (
    check_token_valid,
    check_scope,
    check_step_up,
    enforce_oauth3,
    build_evidence_token_entry,
)
from oauth3.revocation import (
    revoke_token,
    revoke_all_tokens_for_scope,
    is_revoked,
    list_all_tokens,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def token_dir(tmp_path):
    """Provide a temporary directory for token storage in each test."""
    td = tmp_path / "tokens"
    td.mkdir()
    return td


@pytest.fixture
def valid_token(token_dir):
    """A fresh, non-expired, non-revoked token with linkedin.create_post scope."""
    token = AgencyToken.create(
        user_id="test-user",
        scopes=["linkedin.create_post", "linkedin.read_messages"],
    )
    token.save_to_file(token_dir)
    return token, token_dir


@pytest.fixture
def expired_token(token_dir):
    """A token with expires_at in the past."""
    token = AgencyToken.create(
        user_id="test-user",
        scopes=["linkedin.create_post"],
        expires_hours=-1,  # already expired
    )
    token.save_to_file(token_dir)
    return token, token_dir


@pytest.fixture
def revoked_token_fixture(token_dir):
    """A token that has been revoked after creation."""
    token = AgencyToken.create(
        user_id="test-user",
        scopes=["linkedin.create_post"],
    )
    token.save_to_file(token_dir)
    revoke_token(token.token_id, token_dir=token_dir)
    # Reload to get updated state
    updated = AgencyToken.load_from_file(token.token_id, token_dir=token_dir)
    return updated, token_dir


# ---------------------------------------------------------------------------
# Test 1: Token creation
# ---------------------------------------------------------------------------

class TestTokenCreation:
    """test_token_creation: Create a token with scopes — returns valid JSON with token_id."""

    def test_token_has_token_id(self):
        token = AgencyToken.create(
            user_id="test-user",
            scopes=["linkedin.create_post"],
        )
        assert token.token_id
        assert len(token.token_id) == 36  # UUID4 format: 8-4-4-4-12

    def test_token_has_all_required_fields(self):
        token = AgencyToken.create(
            user_id="alice",
            scopes=["linkedin.create_post", "gmail.read_inbox"],
        )
        d = token.to_dict()
        assert "token_id" in d
        assert "user_id" in d
        assert "issued_at" in d
        assert "expires_at" in d
        assert "scopes" in d
        assert "revoked" in d
        assert "revoked_at" in d
        assert "step_up_required_for" in d

    def test_token_scopes_match_requested(self):
        requested = ["linkedin.create_post", "gmail.read_inbox"]
        token = AgencyToken.create(user_id="alice", scopes=requested)
        assert set(token.scopes) == set(requested)

    def test_token_not_revoked_on_creation(self):
        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        assert token.revoked is False
        assert token.revoked_at is None

    def test_token_default_expiry_is_30_days(self):
        before = datetime.now(timezone.utc)
        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        after = datetime.now(timezone.utc)

        # Parse expires_at
        expires = datetime.fromisoformat(token.expires_at.replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        # Should be roughly 30 days from now
        expected_min = before + timedelta(days=29, hours=23)
        expected_max = after + timedelta(days=30, hours=1)
        assert expected_min <= expires <= expected_max

    def test_token_to_json_round_trip(self):
        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        json_str = token.to_json()
        restored = AgencyToken.from_json(json_str)
        assert restored.token_id == token.token_id
        assert restored.scopes == token.scopes
        assert restored.user_id == token.user_id

    def test_token_save_and_load(self, token_dir):
        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        path = token.save_to_file(token_dir)
        assert path.exists()

        loaded = AgencyToken.load_from_file(token.token_id, token_dir=token_dir)
        assert loaded.token_id == token.token_id
        assert loaded.scopes == token.scopes
        assert loaded.user_id == token.user_id


# ---------------------------------------------------------------------------
# Test 2: Token validation — non-expired, non-revoked
# ---------------------------------------------------------------------------

class TestTokenValidation:
    """test_token_validation: load token, validate() passes for valid token."""

    def test_valid_token_passes_validation(self, valid_token):
        token, _ = valid_token
        is_valid, error = token.validate()
        assert is_valid is True
        assert error == ""

    def test_valid_token_check_token_valid_passes(self, valid_token):
        token, _ = valid_token
        is_valid, error = check_token_valid(token)
        assert is_valid is True
        assert error == ""


# ---------------------------------------------------------------------------
# Test 3: Token expiry
# ---------------------------------------------------------------------------

class TestTokenExpiry:
    """test_token_expiry: set expires_at to past → validate() returns False."""

    def test_expired_token_fails_validation(self, expired_token):
        token, _ = expired_token
        is_valid, error = token.validate()
        assert is_valid is False
        assert "expired" in error.lower()

    def test_expired_token_check_token_valid_fails(self, expired_token):
        token, _ = expired_token
        is_valid, error = check_token_valid(token)
        assert is_valid is False
        assert "expired" in error.lower()

    def test_expired_token_enforce_fails_with_correct_error(self, expired_token):
        token, token_dir = expired_token
        passes, details = enforce_oauth3(
            token.token_id, "linkedin.create_post", token_dir=token_dir
        )
        assert passes is False
        assert details["error"] == "token_expired"


# ---------------------------------------------------------------------------
# Test 4: Token revocation
# ---------------------------------------------------------------------------

class TestTokenRevocation:
    """test_token_revocation: revoke token → is_revoked() returns True."""

    def test_revoke_token_marks_revoked(self, token_dir):
        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        token.save_to_file(token_dir)

        success = revoke_token(token.token_id, token_dir=token_dir)
        assert success is True

        loaded = AgencyToken.load_from_file(token.token_id, token_dir=token_dir)
        assert loaded.revoked is True
        assert loaded.revoked_at is not None

    def test_is_revoked_returns_true_after_revocation(self, token_dir):
        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        token.save_to_file(token_dir)

        assert is_revoked(token.token_id, token_dir=token_dir) is False

        revoke_token(token.token_id, token_dir=token_dir)
        assert is_revoked(token.token_id, token_dir=token_dir) is True

    def test_revoke_nonexistent_token_returns_false(self, token_dir):
        result = revoke_token("nonexistent-id", token_dir=token_dir)
        assert result is False

    def test_revoke_idempotent(self, token_dir):
        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        token.save_to_file(token_dir)

        revoke_token(token.token_id, token_dir=token_dir)
        result = revoke_token(token.token_id, token_dir=token_dir)
        assert result is True  # idempotent — second call also returns True

    def test_revoked_token_fails_validate(self, revoked_token_fixture):
        token, _ = revoked_token_fixture
        is_valid, error = token.validate()
        assert is_valid is False
        assert "revoked" in error.lower()

    def test_is_revoked_returns_true_for_missing_token(self, token_dir):
        # Fail-closed: missing token treated as revoked
        assert is_revoked("does-not-exist", token_dir=token_dir) is True


# ---------------------------------------------------------------------------
# Test 5: Scope check
# ---------------------------------------------------------------------------

class TestScopeCheck:
    """test_scope_check: token with scope X → check_scope(X) passes; check_scope(Y) fails."""

    def test_token_with_scope_passes(self, valid_token):
        token, _ = valid_token
        has_scope, error = check_scope(token, "linkedin.create_post")
        assert has_scope is True
        assert error == ""

    def test_token_without_scope_fails(self, valid_token):
        token, _ = valid_token
        has_scope, error = check_scope(token, "gmail.send_email")
        assert has_scope is False
        assert "insufficient_scope" in error

    def test_token_has_scope_method(self, valid_token):
        token, _ = valid_token
        assert token.has_scope("linkedin.create_post") is True
        assert token.has_scope("gmail.send_email") is False

    def test_validate_scopes_all_valid(self):
        is_valid, unknown = validate_scopes(["linkedin.create_post", "gmail.read_inbox"])
        assert is_valid is True
        assert unknown == []

    def test_validate_scopes_with_unknown(self):
        is_valid, unknown = validate_scopes(["linkedin.create_post", "fake.scope"])
        assert is_valid is False
        assert "fake.scope" in unknown

    def test_get_scope_description_returns_string(self):
        desc = get_scope_description("linkedin.create_post")
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_get_scope_description_unknown_returns_none(self):
        desc = get_scope_description("nonexistent.scope")
        assert desc is None


# ---------------------------------------------------------------------------
# Test 6: Step-up check
# ---------------------------------------------------------------------------

class TestStepUpCheck:
    """test_step_up_check: check_step_up for linkedin.delete_post → step_up_required."""

    def test_delete_post_requires_step_up(self, valid_token):
        token, _ = valid_token
        # Add delete_post to token scopes for this test
        token.scopes.append("linkedin.delete_post")
        can_proceed, error = check_step_up(token, "linkedin.delete_post")
        assert can_proceed is False
        assert "step_up_required" in error

    def test_create_post_does_not_require_step_up(self, valid_token):
        token, _ = valid_token
        can_proceed, error = check_step_up(token, "linkedin.create_post")
        assert can_proceed is True
        assert error == ""

    def test_gmail_delete_email_requires_step_up(self, token_dir):
        token = AgencyToken.create(
            user_id="alice",
            scopes=["gmail.delete_email"],
        )
        can_proceed, error = check_step_up(token, "gmail.delete_email")
        assert can_proceed is False
        assert "step_up_required" in error

    def test_step_up_required_scopes_list_not_empty(self):
        assert len(STEP_UP_REQUIRED_SCOPES) > 0
        assert "linkedin.delete_post" in STEP_UP_REQUIRED_SCOPES

    def test_is_step_up_required_function(self):
        assert is_step_up_required("linkedin.delete_post") is True
        assert is_step_up_required("linkedin.create_post") is False

    def test_enforce_oauth3_returns_step_up_for_delete(self, token_dir):
        # Token has the delete scope but step-up blocks execution
        token = AgencyToken.create(
            user_id="alice",
            scopes=["linkedin.delete_post"],
        )
        token.save_to_file(token_dir)

        passes, details = enforce_oauth3(
            token.token_id,
            "linkedin.delete_post",
            token_dir=token_dir,
        )
        assert passes is False
        assert details["error"] == "step_up_required"


# ---------------------------------------------------------------------------
# Tests 7–10: enforce_oauth3 pipeline (without HTTP server)
# ---------------------------------------------------------------------------

class TestEnforceOAuth3:
    """Full pipeline tests using enforce_oauth3()."""

    def test_missing_token_returns_not_found(self, token_dir):
        """test_run_recipe_without_token: enforce fails with token_not_found."""
        passes, details = enforce_oauth3(
            "nonexistent-uuid",
            "linkedin.create_post",
            token_dir=token_dir,
        )
        assert passes is False
        assert details["error"] == "token_not_found"

    def test_valid_token_with_correct_scope_passes(self, valid_token):
        """test_run_recipe_with_valid_token: valid token + matching scope → passes."""
        token, token_dir = valid_token
        passes, details = enforce_oauth3(
            token.token_id,
            "linkedin.create_post",
            token_dir=token_dir,
        )
        assert passes is True
        assert details["token_id"] == token.token_id
        assert details["scope"] == "linkedin.create_post"

    def test_valid_token_wrong_scope_fails(self, valid_token):
        """test_run_recipe_with_wrong_scope: valid token, missing scope → insufficient_scope."""
        token, token_dir = valid_token
        passes, details = enforce_oauth3(
            token.token_id,
            "gmail.send_email",  # not in token's scopes
            token_dir=token_dir,
        )
        assert passes is False
        assert details["error"] == "insufficient_scope"
        assert "consent_url" in details

    def test_revoked_token_fails(self, token_dir):
        """test_run_recipe_after_revocation: revoke → enforce → fails with token_revoked."""
        token = AgencyToken.create(
            user_id="alice",
            scopes=["linkedin.create_post"],
        )
        token.save_to_file(token_dir)

        # Confirm it passes before revocation
        passes_before, _ = enforce_oauth3(
            token.token_id,
            "linkedin.create_post",
            token_dir=token_dir,
        )
        assert passes_before is True

        # Revoke it
        revoke_token(token.token_id, token_dir=token_dir)

        # Confirm it fails after revocation
        passes_after, details = enforce_oauth3(
            token.token_id,
            "linkedin.create_post",
            token_dir=token_dir,
        )
        assert passes_after is False
        assert details["error"] == "token_revoked"

    def test_evidence_entry_built_correctly(self):
        """Evidence bundle entry has all required fields."""
        entry = build_evidence_token_entry(
            token_id="test-uuid-1234",
            scope_used="linkedin.create_post",
            step_up_performed=False,
            token_expires_at="2026-03-21T00:00:00+00:00",
        )
        assert entry["token_id"] == "test-uuid-1234"
        assert entry["scope_used"] == "linkedin.create_post"
        assert entry["step_up_performed"] is False
        assert entry["token_expires_at"] == "2026-03-21T00:00:00+00:00"


# ---------------------------------------------------------------------------
# Test: Bulk revocation
# ---------------------------------------------------------------------------

class TestBulkRevocation:
    """revoke_all_tokens_for_scope: revoke all tokens with a specific scope."""

    def test_revoke_all_tokens_for_scope(self, token_dir):
        # Create 3 tokens, 2 with the target scope
        t1 = AgencyToken.create(user_id="a", scopes=["linkedin.create_post"])
        t2 = AgencyToken.create(user_id="b", scopes=["linkedin.create_post", "gmail.read_inbox"])
        t3 = AgencyToken.create(user_id="c", scopes=["gmail.read_inbox"])  # no target scope
        for t in (t1, t2, t3):
            t.save_to_file(token_dir)

        revoked_count = revoke_all_tokens_for_scope(
            "linkedin.create_post",
            token_dir=token_dir,
        )
        assert revoked_count == 2

        assert is_revoked(t1.token_id, token_dir=token_dir) is True
        assert is_revoked(t2.token_id, token_dir=token_dir) is True
        assert is_revoked(t3.token_id, token_dir=token_dir) is False

    def test_revoke_scope_empty_dir(self, token_dir):
        # No tokens in dir — should return 0 without error
        count = revoke_all_tokens_for_scope("linkedin.create_post", token_dir=token_dir)
        assert count == 0

    def test_list_all_tokens(self, token_dir):
        t1 = AgencyToken.create(user_id="a", scopes=["linkedin.create_post"])
        t2 = AgencyToken.create(user_id="b", scopes=["gmail.read_inbox"])
        for t in (t1, t2):
            t.save_to_file(token_dir)

        tokens = list_all_tokens(token_dir=token_dir)
        assert len(tokens) == 2
        token_ids = {t.token_id for t in tokens}
        assert t1.token_id in token_ids
        assert t2.token_id in token_ids


# ---------------------------------------------------------------------------
# Test: Scopes module
# ---------------------------------------------------------------------------

class TestScopesModule:
    """Scopes registry is correctly populated."""

    def test_scopes_dict_not_empty(self):
        assert len(SCOPES) > 0

    def test_linkedin_scopes_present(self):
        expected = [
            "linkedin.read_messages",
            "linkedin.create_post",
            "linkedin.edit_post",
            "linkedin.delete_post",
            "linkedin.react",
            "linkedin.comment",
        ]
        for scope in expected:
            assert scope in SCOPES, f"Missing scope: {scope}"

    def test_gmail_scopes_present(self):
        expected = [
            "gmail.read_inbox",
            "gmail.send_email",
            "gmail.search",
            "gmail.label",
        ]
        for scope in expected:
            assert scope in SCOPES, f"Missing scope: {scope}"

    def test_all_scopes_have_non_empty_descriptions(self):
        for scope, desc in SCOPES.items():
            assert isinstance(desc, str), f"Scope '{scope}' description is not a string"
            assert len(desc) > 0, f"Scope '{scope}' has empty description"

    def test_step_up_scopes_subset_of_all_scopes(self):
        for scope in STEP_UP_REQUIRED_SCOPES:
            assert scope in SCOPES, f"Step-up scope '{scope}' not in SCOPES registry"

    def test_step_up_auto_populated_in_token(self):
        token = AgencyToken.create(
            user_id="alice",
            scopes=["linkedin.delete_post", "linkedin.create_post"],
        )
        assert "linkedin.delete_post" in token.step_up_required_for
        assert "linkedin.create_post" not in token.step_up_required_for


# ---------------------------------------------------------------------------
# Tests for QA fixes: F1, F2, F6
# ---------------------------------------------------------------------------

class TestF1NullScopesFromDict:
    """F1 — from_dict() with null scopes or step_up_required_for raises ValueError (null != zero)."""

    def test_null_scopes_raises_value_error(self):
        """JSON scopes: null must raise ValueError, not silently create a broken token."""
        data = {
            "token_id": str(uuid.uuid4()),
            "user_id": "alice",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "scopes": None,
            "revoked": False,
            "revoked_at": None,
            "step_up_required_for": [],
        }
        with pytest.raises(ValueError, match="scopes must be a list"):
            AgencyToken.from_dict(data)

    def test_null_step_up_required_for_raises_value_error(self):
        """JSON step_up_required_for: null must raise ValueError, not silently set None."""
        data = {
            "token_id": str(uuid.uuid4()),
            "user_id": "alice",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "scopes": ["linkedin.create_post"],
            "revoked": False,
            "revoked_at": None,
            "step_up_required_for": None,
        }
        with pytest.raises(ValueError, match="step_up_required_for must be a list"):
            AgencyToken.from_dict(data)

    def test_valid_scopes_list_still_works(self):
        """Non-null scopes list continues to deserialize correctly."""
        data = {
            "token_id": str(uuid.uuid4()),
            "user_id": "alice",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "scopes": ["linkedin.create_post"],
            "revoked": False,
            "revoked_at": None,
            "step_up_required_for": [],
        }
        token = AgencyToken.from_dict(data)
        assert token.scopes == ["linkedin.create_post"]
        assert token.step_up_required_for == []


class TestF2StepUpConfirmed:
    """F2 — enforce_oauth3() with step_up_confirmed=True allows destructive scopes."""

    def test_step_up_confirmed_true_allows_destructive_scope(self, token_dir):
        """After step-up has been performed, destructive action must pass enforcement."""
        token = AgencyToken.create(
            user_id="alice",
            scopes=["linkedin.delete_post"],
        )
        token.save_to_file(token_dir)

        passes, details = enforce_oauth3(
            token.token_id,
            "linkedin.delete_post",
            token_dir=token_dir,
            step_up_confirmed=True,
        )
        assert passes is True
        assert details["scope"] == "linkedin.delete_post"

    def test_step_up_confirmed_false_still_blocks_destructive_scope(self, token_dir):
        """Default behaviour (step_up_confirmed=False) must still block destructive scopes."""
        token = AgencyToken.create(
            user_id="alice",
            scopes=["linkedin.delete_post"],
        )
        token.save_to_file(token_dir)

        passes, details = enforce_oauth3(
            token.token_id,
            "linkedin.delete_post",
            token_dir=token_dir,
            step_up_confirmed=False,
        )
        assert passes is False
        assert details["error"] == "step_up_required"

    def test_step_up_confirmed_default_is_false(self, token_dir):
        """Calling enforce_oauth3 without step_up_confirmed still blocks (default=False)."""
        token = AgencyToken.create(
            user_id="alice",
            scopes=["linkedin.delete_post"],
        )
        token.save_to_file(token_dir)

        passes, details = enforce_oauth3(
            token.token_id,
            "linkedin.delete_post",
            token_dir=token_dir,
        )
        assert passes is False
        assert details["error"] == "step_up_required"

    def test_step_up_confirmed_non_destructive_scope_still_passes(self, token_dir):
        """step_up_confirmed=True on a non-destructive scope has no adverse effect."""
        token = AgencyToken.create(
            user_id="alice",
            scopes=["linkedin.create_post"],
        )
        token.save_to_file(token_dir)

        passes, details = enforce_oauth3(
            token.token_id,
            "linkedin.create_post",
            token_dir=token_dir,
            step_up_confirmed=True,
        )
        assert passes is True


class TestF6UnknownScopeAtCreation:
    """F6 — AgencyToken.create() rejects unregistered scopes immediately."""

    def test_unknown_scope_raises_value_error(self):
        """Creating a token with an unregistered scope must raise ValueError."""
        with pytest.raises(ValueError, match="Unknown scope"):
            AgencyToken.create(
                user_id="alice",
                scopes=["fake.nonexistent_scope"],
            )

    def test_mixed_known_unknown_scopes_raises_value_error(self):
        """Even one unknown scope in a list must raise ValueError."""
        with pytest.raises(ValueError, match="Unknown scope"):
            AgencyToken.create(
                user_id="alice",
                scopes=["linkedin.create_post", "fake.nonexistent_scope"],
            )

    def test_all_known_scopes_create_successfully(self):
        """Token with only registered scopes continues to create without error."""
        token = AgencyToken.create(
            user_id="alice",
            scopes=["linkedin.create_post", "gmail.read_inbox"],
        )
        assert set(token.scopes) == {"linkedin.create_post", "gmail.read_inbox"}


# ---------------------------------------------------------------------------
# HTTP endpoint tests (aiohttp TestClient)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# HTTP endpoint tests using aiohttp.test_utils (no pytest-aiohttp needed)
# ---------------------------------------------------------------------------

import asyncio
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


def _build_test_app(token_dir: Path) -> web.Application:
    """Build a minimal aiohttp app with OAuth3 routes for HTTP testing."""
    app = web.Application()

    async def issue_token(request):
        data = await request.json()
        scopes = data.get("scopes", [])
        if not scopes:
            return web.json_response({"error": "missing_scopes"}, status=400)
        is_valid, unknown = validate_scopes(scopes)
        if not is_valid:
            return web.json_response({"error": "unknown_scopes", "unknown": unknown}, status=400)
        token = AgencyToken.create(
            user_id=data.get("user_id", "local"),
            scopes=scopes,
            expires_hours=int(data.get("expires_hours", 720)),
        )
        token.save_to_file(token_dir)
        return web.json_response(token.to_dict(), status=200)

    async def get_token(request):
        tid = request.match_info["token_id"]
        try:
            token = AgencyToken.load_from_file(tid, token_dir=token_dir)
            return web.json_response(token.to_dict(), status=200)
        except FileNotFoundError:
            return web.json_response({"error": "token_not_found"}, status=404)

    async def revoke_token_handler(request):
        tid = request.match_info["token_id"]
        success = revoke_token(tid, token_dir=token_dir)
        if not success:
            return web.json_response({"error": "token_not_found"}, status=404)
        return web.json_response({"revoked": True, "token_id": tid}, status=200)

    async def get_scopes(request):
        return web.json_response({"scopes": SCOPES}, status=200)

    app.router.add_post("/oauth3/token", issue_token)
    app.router.add_get("/oauth3/token/{token_id}", get_token)
    app.router.add_delete("/oauth3/token/{token_id}", revoke_token_handler)
    app.router.add_get("/oauth3/scopes", get_scopes)

    return app


def _run(coro):
    """Run an async coroutine synchronously for use in sync test methods."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestHTTPEndpoints:
    """
    HTTP endpoint tests using aiohttp.test_utils.TestClient.

    Tests the /oauth3/* routes without needing a running server or pytest-aiohttp.
    """

    def test_issue_token_endpoint(self, tmp_path):
        """test_token_creation via HTTP: POST /oauth3/token returns valid token JSON."""
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_test_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/token",
                    json={"scopes": ["linkedin.create_post"], "expires_hours": 720},
                )
                assert resp.status == 200
                data = await resp.json()
                assert "token_id" in data
                assert "linkedin.create_post" in data["scopes"]
                return data

        _run(run())

    def test_issue_token_unknown_scope(self, tmp_path):
        """Unknown scope → 400 with error=unknown_scopes."""
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_test_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/token",
                    json={"scopes": ["invalid.scope"]},
                )
                assert resp.status == 400
                data = await resp.json()
                assert data["error"] == "unknown_scopes"

        _run(run())

    def test_get_token_endpoint(self, tmp_path):
        """GET /oauth3/token/{id} returns token after issuance."""
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_test_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/token",
                    json={"scopes": ["linkedin.create_post"]},
                )
                assert resp.status == 200
                token_id = (await resp.json())["token_id"]

                resp2 = await client.get(f"/oauth3/token/{token_id}")
                assert resp2.status == 200
                data2 = await resp2.json()
                assert data2["token_id"] == token_id

        _run(run())

    def test_get_token_not_found(self, tmp_path):
        """GET /oauth3/token/{id} returns 404 for nonexistent token."""
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_test_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/oauth3/token/nonexistent-id")
                assert resp.status == 404

        _run(run())

    def test_revoke_token_endpoint(self, tmp_path):
        """DELETE /oauth3/token/{id} marks token revoked."""
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_test_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/token",
                    json={"scopes": ["linkedin.create_post"]},
                )
                token_id = (await resp.json())["token_id"]

                resp2 = await client.delete(f"/oauth3/token/{token_id}")
                assert resp2.status == 200
                data2 = await resp2.json()
                assert data2["revoked"] is True

        _run(run())

    def test_get_scopes_endpoint(self, tmp_path):
        """GET /oauth3/scopes returns scope registry."""
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_test_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/oauth3/scopes")
                assert resp.status == 200
                data = await resp.json()
                assert "scopes" in data
                assert "linkedin.create_post" in data["scopes"]

        _run(run())
