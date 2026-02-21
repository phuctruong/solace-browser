"""
OAuth3 Step-Up Authorization — Acceptance Tests
Phase 1.5 BUILD 3

Tests (8 required):
  1.  test_step_up_required_for_delete_returns_402
  2.  test_step_up_page_renders_with_warning
  3.  test_step_up_post_issues_nonce
  4.  test_step_up_nonce_allows_execution
  5.  test_step_up_expired_nonce_rejected
  6.  test_step_up_nonce_single_use
  7.  test_non_destructive_scope_no_step_up_needed
  8.  test_step_up_evidence_recorded

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_step_up.py -v

Rung: 641
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from oauth3.token import AgencyToken
from oauth3.scopes import STEP_UP_REQUIRED_SCOPES
from oauth3.enforcement import enforce_oauth3
from oauth3.step_up import (
    create_step_up_nonce,
    validate_and_consume_nonce,
    clear_all_nonces,
    peek_nonce,
)
from oauth3.consent_ui import build_step_up_page

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_nonce_store():
    """Clear nonce store before each test to prevent cross-test pollution."""
    clear_all_nonces()
    yield
    clear_all_nonces()


@pytest.fixture
def token_dir(tmp_path):
    """Temporary token store directory."""
    td = tmp_path / "tokens"
    td.mkdir()
    return td


@pytest.fixture
def delete_token(token_dir):
    """Active token with linkedin.delete_post scope."""
    token = AgencyToken.create(
        user_id="test-user",
        scopes=["linkedin.delete_post"],
    )
    token.save_to_file(token_dir)
    return token, token_dir


@pytest.fixture
def create_token(token_dir):
    """Active token with non-destructive scope (linkedin.create_post)."""
    token = AgencyToken.create(
        user_id="test-user",
        scopes=["linkedin.create_post"],
    )
    token.save_to_file(token_dir)
    return token, token_dir


# ---------------------------------------------------------------------------
# Test app factory (inline — no real server or browser needed)
# ---------------------------------------------------------------------------


def _build_test_app(token_dir: Path, recipe_dir: Path) -> web.Application:
    """
    Minimal aiohttp app with:
      - POST /run-recipe  (OAuth3-enforced, step-up nonce aware)
      - GET  /step-up     (step-up confirmation page)
      - POST /oauth3/step-up (issue nonce)
    """
    app = web.Application()

    # -------------------------------------------------------------------------
    # POST /run-recipe
    # -------------------------------------------------------------------------
    async def run_recipe(request):
        from oauth3 import enforce_oauth3
        from oauth3.enforcement import build_evidence_token_entry
        from oauth3.step_up import validate_and_consume_nonce
        from oauth3.scopes import STEP_UP_REQUIRED_SCOPES

        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid_json"}, status=400)

        recipe_id = data.get("recipe_id")
        if not recipe_id:
            return web.json_response({"error": "missing_recipe_id"}, status=400)

        # Load recipe
        recipe_path = recipe_dir / f"{recipe_id}.recipe.json"
        if not recipe_path.exists():
            return web.json_response({"error": "recipe_not_found", "recipe_id": recipe_id}, status=404)

        recipe = json.loads(recipe_path.read_text(encoding="utf-8"))

        # Extract token
        token_id = data.get("agency_token") or request.headers.get("X-Agency-Token")
        if not token_id:
            required_scope = recipe.get("required_scope", "unknown.action")
            return web.json_response(
                {
                    "error": "missing_agency_token",
                    "required_scope": required_scope,
                    "consent_url": f"/consent?scopes={required_scope}",
                },
                status=403,
            )

        required_scope = recipe.get("required_scope", "unknown.action")
        step_up_nonce = data.get("step_up_nonce") or None

        # Validate step-up nonce if provided
        step_up_performed = False
        step_up_performed_at = None
        if step_up_nonce:
            nonce_valid, nonce_action = validate_and_consume_nonce(step_up_nonce)
            if not nonce_valid:
                return web.json_response(
                    {
                        "error": "step_up_nonce_invalid",
                        "detail": "Step-up nonce is expired, invalid, or already used.",
                        "token_id": token_id,
                        "required_scope": required_scope,
                        "confirm_url": (
                            f"/step-up?token_id={token_id}"
                            f"&action={required_scope}"
                            f"&recipe_id={recipe_id}"
                            f"&error=Nonce+expired+or+already+used"
                        ),
                    },
                    status=402,
                )
            if nonce_action != required_scope:
                return web.json_response(
                    {
                        "error": "step_up_nonce_scope_mismatch",
                        "detail": (
                            f"Nonce was issued for '{nonce_action}' "
                            f"but recipe requires '{required_scope}'."
                        ),
                    },
                    status=403,
                )
            step_up_performed = True
            step_up_performed_at = datetime.now(timezone.utc).isoformat()

        # Enforce OAuth3
        passes, details = enforce_oauth3(
            token_id,
            required_scope,
            token_dir=token_dir,
            step_up_confirmed=step_up_performed,
        )

        if not passes:
            error_code = details.get("error", "enforcement_failed")
            if error_code in ("token_expired", "token_revoked", "token_not_found", "token_load_error"):
                status_code = 401
            elif error_code == "step_up_required":
                status_code = 402
            else:
                status_code = 403

            body = {
                "error": error_code,
                "detail": details.get("error_detail", ""),
                "token_id": token_id,
                "required_scope": required_scope,
            }
            if "consent_url" in details:
                body["consent_url"] = details["consent_url"]
            if error_code == "step_up_required":
                body["action"] = details.get("action", required_scope)
                body["confirm_url"] = (
                    f"/step-up?token_id={token_id}"
                    f"&action={required_scope}"
                    f"&recipe_id={recipe_id}"
                )
            return web.json_response(body, status=status_code)

        # Build evidence
        agency_token_evidence = build_evidence_token_entry(
            token_id=details["token_id"],
            scope_used=details["scope"],
            step_up_performed=step_up_performed,
            token_expires_at=details.get("expires_at"),
        )

        started_at = datetime.now(timezone.utc).isoformat()
        evidence = {
            "recipe_id": recipe_id,
            "status": "oauth3_verified",
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "agency_token": agency_token_evidence,
            "recipe_metadata": {
                "description": recipe.get("description", ""),
                "version": recipe.get("version", "1.0"),
                "required_scope": required_scope,
            },
            "rung": 641,
        }

        if step_up_performed:
            evidence["step_up"] = {
                "required": True,
                "performed": True,
                "performed_at": step_up_performed_at,
                "action": required_scope,
            }

        return web.json_response(
            {"success": True, "recipe_id": recipe_id, "status": "oauth3_verified", "evidence": evidence},
            status=200,
        )

    # -------------------------------------------------------------------------
    # GET /step-up
    # -------------------------------------------------------------------------
    async def step_up_get(request):
        from oauth3.consent_ui import handle_step_up_get
        return await handle_step_up_get(request)

    # -------------------------------------------------------------------------
    # POST /oauth3/step-up  (token_dir injected via closure)
    # -------------------------------------------------------------------------
    async def step_up_post(request):
        from oauth3.token import AgencyToken
        from oauth3.scopes import STEP_UP_REQUIRED_SCOPES
        from oauth3.step_up import create_step_up_nonce

        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid_json"}, status=400)

        tid = data.get("token_id", "")
        action = data.get("action", "")

        if not tid or not action:
            return web.json_response(
                {"error": "missing_fields", "detail": "token_id and action are required"},
                status=400,
            )

        if action not in STEP_UP_REQUIRED_SCOPES:
            return web.json_response(
                {"error": "not_step_up_scope", "detail": f"'{action}' is not a step-up required scope"},
                status=422,
            )

        try:
            token = AgencyToken.load_from_file(tid, token_dir=token_dir)
        except FileNotFoundError:
            return web.json_response({"error": "token_not_found", "token_id": tid}, status=401)
        except Exception as e:
            return web.json_response({"error": "token_load_error", "detail": str(e)}, status=401)

        is_valid, validity_error = token.validate()
        if not is_valid:
            error_code = "token_revoked" if token.revoked else "token_expired"
            return web.json_response(
                {"error": error_code, "detail": validity_error, "token_id": tid},
                status=401,
            )

        if not token.has_scope(action):
            return web.json_response(
                {"error": "insufficient_scope", "detail": f"Token does not have scope '{action}'"},
                status=403,
            )

        nonce = create_step_up_nonce(token_id=tid, action=action)
        return web.json_response({"nonce": nonce, "expires_in": 300, "action": action, "token_id": tid}, status=200)

    app.router.add_post("/run-recipe", run_recipe)
    app.router.add_get("/step-up", step_up_get)
    app.router.add_post("/oauth3/step-up", step_up_post)
    return app


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_delete_recipe(recipe_dir: Path) -> Path:
    """Write a minimal linkedin-delete-post recipe with explicit required_scope."""
    recipe = {
        "recipe_id": "linkedin-delete-post",
        "version": "1.0",
        "description": "Delete a LinkedIn post — IRREVERSIBLE",
        "required_scope": "linkedin.delete_post",
        "metadata": {"tags": ["linkedin"]},
    }
    path = recipe_dir / "linkedin-delete-post.recipe.json"
    path.write_text(json.dumps(recipe), encoding="utf-8")
    return path


def _make_create_recipe(recipe_dir: Path) -> Path:
    """Write a minimal linkedin-create-post recipe."""
    recipe = {
        "recipe_id": "linkedin-create-post",
        "version": "1.0",
        "description": "Create a LinkedIn post",
        "required_scope": "linkedin.create_post",
        "metadata": {"tags": ["linkedin"]},
    }
    path = recipe_dir / "linkedin-create-post.recipe.json"
    path.write_text(json.dumps(recipe), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Test 1: step_up_required_for_delete_returns_402
# ---------------------------------------------------------------------------

class TestStepUpRequired:
    """Destructive scope → 402 with confirm_url when no nonce provided."""

    def test_step_up_required_for_delete_returns_402(self, tmp_path):
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()
        _make_delete_recipe(recipe_dir)

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.delete_post"])
        token.save_to_file(token_dir)

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/run-recipe",
                    json={
                        "recipe_id": "linkedin-delete-post",
                        "agency_token": token.token_id,
                    },
                )
                assert resp.status == 402
                data = await resp.json()
                assert data["error"] == "step_up_required"
                assert "confirm_url" in data
                assert "/step-up" in data["confirm_url"]

        _run(run())


# ---------------------------------------------------------------------------
# Test 2: step_up_page_renders_with_warning
# ---------------------------------------------------------------------------

class TestStepUpPageRenders:
    """GET /step-up renders a red warning banner for destructive scopes."""

    def test_step_up_page_renders_with_warning(self, tmp_path):
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.delete_post"])
        token.save_to_file(token_dir)

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.get(
                    "/step-up",
                    params={
                        "token_id": token.token_id,
                        "action": "linkedin.delete_post",
                        "recipe_id": "linkedin-delete-post",
                    },
                )
                assert resp.status == 200
                text = await resp.text()
                assert "Permanent Action" in text
                assert "cannot be undone" in text.lower() or "cannot be undone" in text
                assert "linkedin.delete_post" in text

        _run(run())

    def test_step_up_page_warns_high_risk(self, tmp_path):
        """Page includes HIGH RISK badge text for the destructive scope."""
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        token = AgencyToken.create(user_id="alice", scopes=["gmail.delete_email"])
        token.save_to_file(token_dir)

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.get(
                    "/step-up",
                    params={
                        "token_id": token.token_id,
                        "action": "gmail.delete_email",
                    },
                )
                assert resp.status == 200
                text = await resp.text()
                assert "HIGH RISK" in text
                assert "gmail.delete_email" in text

        _run(run())

    def test_step_up_page_unknown_action_returns_400(self, tmp_path):
        """Non-step-up scope → 400 on the step-up page."""
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        token.save_to_file(token_dir)

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.get(
                    "/step-up",
                    params={
                        "token_id": token.token_id,
                        "action": "linkedin.create_post",  # NOT a step-up scope
                    },
                )
                assert resp.status == 400

        _run(run())


# ---------------------------------------------------------------------------
# Test 3: step_up_post_issues_nonce
# ---------------------------------------------------------------------------

class TestStepUpPostIssuesNonce:
    """POST /oauth3/step-up issues a UUID4 nonce."""

    def test_step_up_post_issues_nonce(self, tmp_path):
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.delete_post"])
        token.save_to_file(token_dir)

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/step-up",
                    json={"token_id": token.token_id, "action": "linkedin.delete_post"},
                )
                assert resp.status == 200
                data = await resp.json()
                assert "nonce" in data
                assert len(data["nonce"]) == 36  # UUID4 format
                assert data["expires_in"] == 300
                assert data["action"] == "linkedin.delete_post"

        _run(run())

    def test_step_up_post_rejects_non_step_up_scope(self, tmp_path):
        """POST /oauth3/step-up with a non-destructive scope → 422."""
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        token.save_to_file(token_dir)

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/step-up",
                    json={"token_id": token.token_id, "action": "linkedin.create_post"},
                )
                assert resp.status == 422
                data = await resp.json()
                assert data["error"] == "not_step_up_scope"

        _run(run())

    def test_step_up_post_rejects_token_without_scope(self, tmp_path):
        """POST /oauth3/step-up with token lacking the scope → 403."""
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()

        # Token does NOT have delete_post scope
        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        token.save_to_file(token_dir)

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/step-up",
                    json={"token_id": token.token_id, "action": "linkedin.delete_post"},
                )
                assert resp.status == 403
                data = await resp.json()
                assert data["error"] == "insufficient_scope"

        _run(run())


# ---------------------------------------------------------------------------
# Test 4: step_up_nonce_allows_execution
# ---------------------------------------------------------------------------

class TestStepUpNonceAllowsExecution:
    """Valid nonce + destructive scope → 200 (execution proceeds)."""

    def test_step_up_nonce_allows_execution(self, tmp_path):
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()
        _make_delete_recipe(recipe_dir)

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.delete_post"])
        token.save_to_file(token_dir)

        # Create nonce directly (simulates UI confirm step)
        nonce = create_step_up_nonce(token.token_id, "linkedin.delete_post")

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/run-recipe",
                    json={
                        "recipe_id": "linkedin-delete-post",
                        "agency_token": token.token_id,
                        "step_up_nonce": nonce,
                    },
                )
                assert resp.status == 200
                data = await resp.json()
                assert data["success"] is True
                assert data["status"] == "oauth3_verified"

        _run(run())

    def test_step_up_nonce_flow_full_round_trip(self, tmp_path):
        """Full flow: POST /oauth3/step-up → nonce → POST /run-recipe with nonce → 200."""
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()
        _make_delete_recipe(recipe_dir)

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.delete_post"])
        token.save_to_file(token_dir)

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                # Step 1: confirm step-up, get nonce
                resp1 = await client.post(
                    "/oauth3/step-up",
                    json={"token_id": token.token_id, "action": "linkedin.delete_post"},
                )
                assert resp1.status == 200
                nonce = (await resp1.json())["nonce"]
                assert nonce

                # Step 2: use nonce to run recipe
                resp2 = await client.post(
                    "/run-recipe",
                    json={
                        "recipe_id": "linkedin-delete-post",
                        "agency_token": token.token_id,
                        "step_up_nonce": nonce,
                    },
                )
                assert resp2.status == 200
                data = await resp2.json()
                assert data["success"] is True

        _run(run())


# ---------------------------------------------------------------------------
# Test 5: step_up_expired_nonce_rejected
# ---------------------------------------------------------------------------

class TestStepUpExpiredNonce:
    """Expired nonce → 402 (not 200)."""

    def test_step_up_expired_nonce_rejected(self, tmp_path):
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()
        _make_delete_recipe(recipe_dir)

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.delete_post"])
        token.save_to_file(token_dir)

        # Create a nonce with TTL = 0 (already expired)
        nonce = create_step_up_nonce(token.token_id, "linkedin.delete_post", ttl=0)
        # Ensure time passes so monotonic clock registers expiry
        time.sleep(0.01)

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/run-recipe",
                    json={
                        "recipe_id": "linkedin-delete-post",
                        "agency_token": token.token_id,
                        "step_up_nonce": nonce,
                    },
                )
                # Expired nonce → 402 (step-up required again)
                assert resp.status == 402
                data = await resp.json()
                assert data["error"] == "step_up_nonce_invalid"

        _run(run())

    def test_expired_nonce_validate_and_consume_returns_false(self):
        """validate_and_consume_nonce returns (False, '') for expired nonce."""
        nonce = create_step_up_nonce("fake-token-id", "linkedin.delete_post", ttl=0)
        time.sleep(0.01)
        valid, action = validate_and_consume_nonce(nonce)
        assert valid is False
        assert action == ""

    def test_expired_nonce_removed_from_store(self):
        """Expired nonce is removed from the store after validate_and_consume_nonce."""
        nonce = create_step_up_nonce("fake-token-id", "linkedin.delete_post", ttl=0)
        time.sleep(0.01)
        validate_and_consume_nonce(nonce)
        # Calling again must also return False (nonce gone)
        valid2, _ = validate_and_consume_nonce(nonce)
        assert valid2 is False


# ---------------------------------------------------------------------------
# Test 6: step_up_nonce_single_use
# ---------------------------------------------------------------------------

class TestStepUpNonceSingleUse:
    """Nonce is consumed on first use — second use fails."""

    def test_step_up_nonce_single_use(self, tmp_path):
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()
        _make_delete_recipe(recipe_dir)

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.delete_post"])
        token.save_to_file(token_dir)

        nonce = create_step_up_nonce(token.token_id, "linkedin.delete_post")

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                # First use → succeeds
                resp1 = await client.post(
                    "/run-recipe",
                    json={
                        "recipe_id": "linkedin-delete-post",
                        "agency_token": token.token_id,
                        "step_up_nonce": nonce,
                    },
                )
                assert resp1.status == 200

                # Second use — same nonce → fails
                # Need a new nonce from step-up for next attempt
                resp2 = await client.post(
                    "/run-recipe",
                    json={
                        "recipe_id": "linkedin-delete-post",
                        "agency_token": token.token_id,
                        "step_up_nonce": nonce,
                    },
                )
                assert resp2.status == 402
                data2 = await resp2.json()
                assert data2["error"] == "step_up_nonce_invalid"

        _run(run())

    def test_nonce_validate_and_consume_single_use(self):
        """validate_and_consume_nonce is single-use at module level."""
        nonce = create_step_up_nonce("tok-123", "linkedin.delete_post")

        valid1, action1 = validate_and_consume_nonce(nonce)
        assert valid1 is True
        assert action1 == "linkedin.delete_post"

        valid2, action2 = validate_and_consume_nonce(nonce)
        assert valid2 is False
        assert action2 == ""

    def test_peek_nonce_does_not_consume(self):
        """peek_nonce() returns metadata without consuming the nonce."""
        nonce = create_step_up_nonce("tok-456", "reddit.delete_post")
        meta = peek_nonce(nonce)
        assert meta is not None
        assert meta["action"] == "reddit.delete_post"

        # Peek again — still there
        meta2 = peek_nonce(nonce)
        assert meta2 is not None

        # Now consume
        valid, action = validate_and_consume_nonce(nonce)
        assert valid is True
        assert action == "reddit.delete_post"

        # After consume — gone
        assert peek_nonce(nonce) is None


# ---------------------------------------------------------------------------
# Test 7: non_destructive_scope_no_step_up_needed
# ---------------------------------------------------------------------------

class TestNonDestructiveScopeNoStepUp:
    """Non-destructive scopes pass enforcement without any nonce."""

    def test_non_destructive_scope_no_step_up_needed(self, tmp_path):
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()
        _make_create_recipe(recipe_dir)

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        token.save_to_file(token_dir)

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/run-recipe",
                    json={
                        "recipe_id": "linkedin-create-post",
                        "agency_token": token.token_id,
                        # No step_up_nonce provided
                    },
                )
                assert resp.status == 200
                data = await resp.json()
                assert data["success"] is True
                # Non-destructive → no step_up key in evidence
                assert "step_up" not in data["evidence"]

        _run(run())

    def test_all_step_up_required_scopes_listed(self):
        """STEP_UP_REQUIRED_SCOPES contains the canonical 3 destructive scopes."""
        assert "linkedin.delete_post" in STEP_UP_REQUIRED_SCOPES
        assert "gmail.delete_email" in STEP_UP_REQUIRED_SCOPES
        assert "reddit.delete_post" in STEP_UP_REQUIRED_SCOPES

    def test_enforce_oauth3_non_destructive_passes_directly(self, tmp_path):
        """enforce_oauth3 passes without step_up_confirmed for non-destructive scope."""
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        token.save_to_file(token_dir)

        passes, details = enforce_oauth3(
            token.token_id,
            "linkedin.create_post",
            token_dir=token_dir,
        )
        assert passes is True
        assert details["scope"] == "linkedin.create_post"


# ---------------------------------------------------------------------------
# Test 8: step_up_evidence_recorded
# ---------------------------------------------------------------------------

class TestStepUpEvidenceRecorded:
    """When step-up is performed, evidence["step_up"] is included in response."""

    def test_step_up_evidence_recorded(self, tmp_path):
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()
        _make_delete_recipe(recipe_dir)

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.delete_post"])
        token.save_to_file(token_dir)

        nonce = create_step_up_nonce(token.token_id, "linkedin.delete_post")

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/run-recipe",
                    json={
                        "recipe_id": "linkedin-delete-post",
                        "agency_token": token.token_id,
                        "step_up_nonce": nonce,
                    },
                )
                assert resp.status == 200
                data = await resp.json()
                evidence = data["evidence"]

                # step_up evidence block must be present
                assert "step_up" in evidence
                su = evidence["step_up"]
                assert su["required"] is True
                assert su["performed"] is True
                assert su["performed_at"] is not None
                assert su["action"] == "linkedin.delete_post"

        _run(run())

    def test_step_up_evidence_agency_token_records_step_up_performed(self, tmp_path):
        """agency_token evidence block has step_up_performed=True when nonce used."""
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()
        _make_delete_recipe(recipe_dir)

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.delete_post"])
        token.save_to_file(token_dir)

        nonce = create_step_up_nonce(token.token_id, "linkedin.delete_post")

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/run-recipe",
                    json={
                        "recipe_id": "linkedin-delete-post",
                        "agency_token": token.token_id,
                        "step_up_nonce": nonce,
                    },
                )
                assert resp.status == 200
                data = await resp.json()
                at_evidence = data["evidence"]["agency_token"]
                assert at_evidence["step_up_performed"] is True
                assert at_evidence["scope_used"] == "linkedin.delete_post"
                assert at_evidence["token_id"] == token.token_id

        _run(run())

    def test_no_step_up_no_evidence_block(self, tmp_path):
        """Non-destructive recipe execution does NOT include step_up evidence block."""
        token_dir = tmp_path / "tokens"
        token_dir.mkdir()
        recipe_dir = tmp_path / "recipes"
        recipe_dir.mkdir()
        _make_create_recipe(recipe_dir)

        token = AgencyToken.create(user_id="alice", scopes=["linkedin.create_post"])
        token.save_to_file(token_dir)

        app = _build_test_app(token_dir, recipe_dir)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/run-recipe",
                    json={
                        "recipe_id": "linkedin-create-post",
                        "agency_token": token.token_id,
                    },
                )
                assert resp.status == 200
                data = await resp.json()
                # No step_up key when none was performed
                assert "step_up" not in data["evidence"]

        _run(run())


# ---------------------------------------------------------------------------
# Unit tests: step_up module directly
# ---------------------------------------------------------------------------


class TestStepUpModule:
    """Direct unit tests for the step_up.py nonce manager."""

    def test_create_nonce_returns_uuid4(self):
        nonce = create_step_up_nonce("tok-1", "linkedin.delete_post")
        assert len(nonce) == 36
        parts = nonce.split("-")
        assert len(parts) == 5

    def test_validate_valid_nonce(self):
        nonce = create_step_up_nonce("tok-2", "gmail.delete_email")
        valid, action = validate_and_consume_nonce(nonce)
        assert valid is True
        assert action == "gmail.delete_email"

    def test_validate_unknown_nonce_returns_false(self):
        valid, action = validate_and_consume_nonce("not-a-real-nonce")
        assert valid is False
        assert action == ""

    def test_clear_all_nonces_empties_store(self):
        create_step_up_nonce("tok-3", "reddit.delete_post")
        create_step_up_nonce("tok-4", "linkedin.delete_post")
        clear_all_nonces()
        valid, _ = validate_and_consume_nonce("any-nonce")
        assert valid is False

    def test_build_step_up_page_200_for_valid_scope(self):
        html, status = build_step_up_page(
            token_id="tok-abc",
            action="linkedin.delete_post",
        )
        assert status == 200
        assert "Permanent Action" in html
        assert "linkedin.delete_post" in html

    def test_build_step_up_page_400_for_invalid_scope(self):
        html, status = build_step_up_page(
            token_id="tok-abc",
            action="linkedin.create_post",  # not a step-up scope
        )
        assert status == 400
        assert "Unknown or non-destructive" in html

    def test_build_step_up_page_shows_recipe_id(self):
        html, status = build_step_up_page(
            token_id="tok-abc",
            action="linkedin.delete_post",
            recipe_id="linkedin-delete-post",
        )
        assert status == 200
        assert "linkedin-delete-post" in html

    def test_build_step_up_page_shows_error_flash(self):
        html, status = build_step_up_page(
            token_id="tok-abc",
            action="gmail.delete_email",
            error="Nonce expired",
        )
        assert status == 200
        assert "Nonce expired" in html
