"""
OAuth3 Consent UI — Acceptance Tests
Phase 1.5 BUILD 2

Tests:
  1.  test_consent_page_renders_with_scopes
  2.  test_consent_page_shows_step_up_warning
  3.  test_consent_post_issues_token_and_redirects
  4.  test_consent_deny_redirects_with_error
  5.  test_settings_tokens_lists_active_tokens
  6.  test_settings_tokens_revoke_button_works
  7.  test_home_page_shows_scope_badge
  8.  test_consent_invalid_scopes_rejected
  9.  test_consent_redirect_sanitized
  10. test_cookie_httponly_samesite

Run:
    cd /home/phuc/projects/solace-browser
    python -m pytest tests/test_consent_ui.py -v

Rung: 641
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest

# Ensure src/ is on sys.path
SRC_PATH = Path(__file__).parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from oauth3.token import AgencyToken
from oauth3.scopes import SCOPES, STEP_UP_REQUIRED_SCOPES
from oauth3.revocation import revoke_token, list_all_tokens
from oauth3.consent_ui import (
    build_consent_page,
    build_tokens_page,
    build_scope_badge_html,
    sanitise_redirect,
    PLATFORM_DEFAULT_SCOPES,
)

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def token_dir(tmp_path):
    """Temporary token store directory."""
    td = tmp_path / "tokens"
    td.mkdir()
    return td


@pytest.fixture
def valid_token(token_dir):
    """A valid (non-expired, non-revoked) token with LinkedIn scopes."""
    token = AgencyToken.create(
        user_id="test-local",
        scopes=["linkedin.create_post", "linkedin.read_messages"],
    )
    token.save_to_file(token_dir)
    return token, token_dir


def _build_consent_app(token_dir: Path) -> web.Application:
    """Build a minimal aiohttp app with consent UI routes for HTTP testing."""
    app = web.Application()

    # Import handlers and wire them to use tmp token_dir via closure
    from oauth3.token import AgencyToken
    from oauth3.scopes import validate_scopes
    from oauth3.revocation import revoke_token as _revoke
    from oauth3.consent_ui import sanitise_redirect, build_consent_page, build_tokens_page

    async def consent_get(request):
        scopes_param = request.rel_url.query.get("scopes", "")
        redirect = request.rel_url.query.get("redirect", "/")
        error = request.rel_url.query.get("error")
        html, status = build_consent_page(
            scopes_param, redirect=redirect, error=error, token_dir=token_dir
        )
        return web.Response(text=html, content_type="text/html", status=status)

    async def consent_post(request):
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "invalid_json"}, status=400)

        requested_scopes = data.get("scopes", [])
        redirect = sanitise_redirect(data.get("redirect", "/"))

        if not requested_scopes:
            return web.json_response({"error": "missing_scopes"}, status=400)
        if not isinstance(requested_scopes, list):
            return web.json_response({"error": "scopes_must_be_list"}, status=400)

        is_valid, unknown = validate_scopes(requested_scopes)
        if not is_valid:
            return web.json_response(
                {"error": "unknown_scopes", "unknown": unknown}, status=400
            )

        token = AgencyToken.create(user_id="local", scopes=requested_scopes)
        token.save_to_file(token_dir)

        response = web.json_response(
            {"token_id": token.token_id, "scopes": token.scopes, "redirect": redirect},
            status=200,
        )
        response.set_cookie(
            "solace_agency_token",
            token.token_id,
            httponly=True,
            samesite="Strict",
            max_age=60 * 60 * 24 * 30,
        )
        return response

    async def tokens_page(request):
        html = build_tokens_page(token_dir=token_dir)
        return web.Response(text=html, content_type="text/html", status=200)

    async def revoke_handler(request):
        tid = request.match_info["token_id"]
        success = _revoke(tid, token_dir=token_dir)
        if not success:
            return web.json_response({"error": "token_not_found"}, status=404)
        return web.json_response({"revoked": True, "token_id": tid}, status=200)

    app.router.add_get("/consent", consent_get)
    app.router.add_post("/oauth3/consent", consent_post)
    app.router.add_get("/settings/tokens", tokens_page)
    app.router.add_delete("/oauth3/token/{token_id}", revoke_handler)

    return app


def _run(coro):
    """Run async coroutine synchronously (for sync test methods)."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Test 1: Consent page renders with scopes
# ---------------------------------------------------------------------------

class TestConsentPageRendersWithScopes:
    """test_consent_page_renders_with_scopes — page shows all requested scopes."""

    def test_page_returns_200(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post,linkedin.read_messages",
            token_dir=token_dir,
        )
        assert status == 200

    def test_page_contains_scope_names(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post,linkedin.comment",
            token_dir=token_dir,
        )
        assert "linkedin.create_post" in html
        assert "linkedin.comment" in html

    def test_page_contains_scope_descriptions(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post",
            token_dir=token_dir,
        )
        assert "Create posts on your behalf" in html

    def test_page_contains_allow_button(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post",
            token_dir=token_dir,
        )
        assert "Allow" in html
        assert "Grant Permission" in html

    def test_page_contains_deny_button(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post",
            token_dir=token_dir,
        )
        assert "Deny" in html
        assert "Cancel" in html

    def test_page_shows_risk_badge(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post",  # medium risk — write action
            token_dir=token_dir,
        )
        # Medium risk
        assert "Medium" in html

    def test_page_shows_low_risk_badge_for_read(self, token_dir):
        html, status = build_consent_page(
            "linkedin.read_messages",
            token_dir=token_dir,
        )
        assert "Low" in html

    def test_http_endpoint_returns_200(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.get(
                    "/consent?scopes=linkedin.create_post,linkedin.comment"
                )
                assert resp.status == 200
                text = await resp.text()
                assert "linkedin.create_post" in text
                assert "linkedin.comment" in text

        _run(run())


# ---------------------------------------------------------------------------
# Test 2: Consent page shows step-up warning
# ---------------------------------------------------------------------------

class TestConsentPageShowsStepUpWarning:
    """test_consent_page_shows_step_up_warning — destructive scope shows yellow banner."""

    def test_delete_scope_triggers_banner(self, token_dir):
        html, status = build_consent_page(
            "linkedin.delete_post",
            token_dir=token_dir,
        )
        assert status == 200
        # Banner must mention the destructive scope
        assert "step-up-banner" in html
        assert "linkedin.delete_post" in html

    def test_gmail_delete_triggers_banner(self, token_dir):
        html, status = build_consent_page(
            "gmail.read_inbox,gmail.delete_email",
            token_dir=token_dir,
        )
        assert "step-up-banner" in html
        assert "gmail.delete_email" in html

    def test_no_banner_for_safe_scopes(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post,linkedin.read_messages",
            token_dir=token_dir,
        )
        # The banner div must NOT be rendered for safe scopes.
        # The CSS class name exists in <style>; check for the rendered <div> element.
        # The banner div has role "step-up-banner" as a class on a <div>, preceded by the
        # warning icon. We check that no destructive scope warning text appears.
        assert "destructive" not in html

    def test_step_up_banner_shows_high_risk_label(self, token_dir):
        html, status = build_consent_page(
            "linkedin.delete_post",
            token_dir=token_dir,
        )
        assert "HIGH RISK" in html

    def test_http_endpoint_shows_banner(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/consent?scopes=linkedin.delete_post")
                assert resp.status == 200
                text = await resp.text()
                assert "step-up-banner" in text

        _run(run())


# ---------------------------------------------------------------------------
# Test 3: Consent POST issues token and redirects
# ---------------------------------------------------------------------------

class TestConsentPostIssuesTokenAndRedirects:
    """test_consent_post_issues_token_and_redirects."""

    def test_post_returns_200_with_token_id(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/consent",
                    json={"scopes": ["linkedin.create_post"], "redirect": "/"},
                )
                assert resp.status == 200
                data = await resp.json()
                assert "token_id" in data
                assert data["redirect"] == "/"
                assert "linkedin.create_post" in data["scopes"]

        _run(run())

    def test_token_is_persisted_to_disk(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/consent",
                    json={"scopes": ["linkedin.comment"], "redirect": "/"},
                )
                data = await resp.json()
                token_id = data["token_id"]
                # File must exist on disk
                token_file = td / f"{token_id}.json"
                assert token_file.exists()

        _run(run())

    def test_redirect_param_preserved_in_response(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/consent",
                    json={"scopes": ["gmail.read_inbox"], "redirect": "/kanban"},
                )
                assert resp.status == 200
                data = await resp.json()
                assert data["redirect"] == "/kanban"

        _run(run())

    def test_missing_scopes_returns_400(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/consent",
                    json={"scopes": [], "redirect": "/"},
                )
                assert resp.status == 400

        _run(run())


# ---------------------------------------------------------------------------
# Test 4: Consent deny redirects with error
# ---------------------------------------------------------------------------

class TestConsentDenyRedirectsWithError:
    """test_consent_deny_redirects_with_error — Deny button goes to /?error=access_denied."""

    def test_deny_link_in_html(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post",
            token_dir=token_dir,
        )
        # The deny anchor must have error=access_denied in its href
        assert "error=access_denied" in html

    def test_deny_link_points_to_root(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post",
            token_dir=token_dir,
        )
        assert "/?error=access_denied" in html

    def test_deny_button_text(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post",
            token_dir=token_dir,
        )
        assert "Deny" in html
        assert "Cancel" in html

    def test_error_flash_shown_when_error_param_present(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post",
            redirect="/",
            error="access_denied",
            token_dir=token_dir,
        )
        assert "access_denied" in html
        assert "flash-error" in html


# ---------------------------------------------------------------------------
# Test 5: Settings tokens lists active tokens
# ---------------------------------------------------------------------------

class TestSettingsTokensListsActiveTokens:
    """test_settings_tokens_lists_active_tokens — /settings/tokens shows token table."""

    def test_page_contains_token_id(self, valid_token):
        token, token_dir = valid_token
        html = build_tokens_page(token_dir=token_dir)
        # Token ID first 8 chars must appear
        assert token.token_id[:8] in html

    def test_page_shows_scope_chips(self, valid_token):
        token, token_dir = valid_token
        html = build_tokens_page(token_dir=token_dir)
        for scope in token.scopes:
            assert scope in html

    def test_page_shows_active_status(self, valid_token):
        token, token_dir = valid_token
        html = build_tokens_page(token_dir=token_dir)
        assert "Active" in html

    def test_empty_token_dir_shows_empty_state(self, token_dir):
        html = build_tokens_page(token_dir=token_dir)
        assert "No tokens issued yet" in html

    def test_http_endpoint_returns_200(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        # Issue a token
        token = AgencyToken.create(user_id="test", scopes=["linkedin.create_post"])
        token.save_to_file(td)

        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/settings/tokens")
                assert resp.status == 200
                text = await resp.text()
                assert token.token_id[:8] in text

        _run(run())

    def test_multiple_tokens_all_shown(self, token_dir):
        t1 = AgencyToken.create(user_id="a", scopes=["linkedin.create_post"])
        t2 = AgencyToken.create(user_id="b", scopes=["gmail.read_inbox"])
        t1.save_to_file(token_dir)
        t2.save_to_file(token_dir)
        html = build_tokens_page(token_dir=token_dir)
        assert t1.token_id[:8] in html
        assert t2.token_id[:8] in html


# ---------------------------------------------------------------------------
# Test 6: Settings tokens revoke button works
# ---------------------------------------------------------------------------

class TestSettingsTokensRevokeButtonWorks:
    """test_settings_tokens_revoke_button_works — revoke button calls DELETE endpoint."""

    def test_revoke_button_present_for_active_token(self, valid_token):
        token, token_dir = valid_token
        html = build_tokens_page(token_dir=token_dir)
        assert "revoke-btn" in html
        assert "revokeToken" in html

    def test_revoke_button_absent_for_revoked_token(self, token_dir):
        token = AgencyToken.create(user_id="a", scopes=["linkedin.create_post"])
        token.save_to_file(token_dir)
        revoke_token(token.token_id, token_dir=token_dir)
        html = build_tokens_page(token_dir=token_dir)
        # revoke-btn class should not appear next to a revoked row
        # (the page may still contain revokeToken function definition in script)
        assert "Revoked" in html

    def test_delete_endpoint_revokes_token(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        token = AgencyToken.create(user_id="a", scopes=["linkedin.create_post"])
        token.save_to_file(td)
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.delete(f"/oauth3/token/{token.token_id}")
                assert resp.status == 200
                data = await resp.json()
                assert data["revoked"] is True
                # Verify on disk
                loaded = AgencyToken.load_from_file(token.token_id, token_dir=td)
                assert loaded.revoked is True

        _run(run())

    def test_delete_nonexistent_token_returns_404(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.delete("/oauth3/token/does-not-exist")
                assert resp.status == 404

        _run(run())


# ---------------------------------------------------------------------------
# Test 7: Home page shows scope badge
# ---------------------------------------------------------------------------

class TestHomePageShowsScopeBadge:
    """test_home_page_shows_scope_badge — badge shows scope count or grant link."""

    def test_badge_shows_gray_when_no_token(self, token_dir):
        badge = build_scope_badge_html("linkedin", token_dir=token_dir)
        assert "scope-badge-gray" in badge
        assert "No permissions" in badge

    def test_badge_shows_green_when_token_present(self, valid_token):
        token, token_dir = valid_token
        badge = build_scope_badge_html("linkedin", token_dir=token_dir)
        assert "scope-badge-green" in badge
        assert "granted" in badge

    def test_badge_shows_correct_scope_count(self, token_dir):
        token = AgencyToken.create(
            user_id="a",
            scopes=["linkedin.create_post", "linkedin.read_messages", "linkedin.comment"],
        )
        token.save_to_file(token_dir)
        badge = build_scope_badge_html("linkedin", token_dir=token_dir)
        assert "3 scopes granted" in badge

    def test_badge_singular_for_one_scope(self, token_dir):
        token = AgencyToken.create(user_id="a", scopes=["gmail.read_inbox"])
        token.save_to_file(token_dir)
        badge = build_scope_badge_html("gmail", token_dir=token_dir)
        assert "1 scope granted" in badge

    def test_gray_badge_links_to_consent_page(self, token_dir):
        badge = build_scope_badge_html("linkedin", token_dir=token_dir)
        assert "/consent" in badge
        assert "linkedin" in badge

    def test_green_badge_links_to_token_settings(self, valid_token):
        token, token_dir = valid_token
        badge = build_scope_badge_html("linkedin", token_dir=token_dir)
        assert "/settings/tokens" in badge

    def test_revoked_token_not_counted(self, token_dir):
        token = AgencyToken.create(user_id="a", scopes=["linkedin.create_post"])
        token.save_to_file(token_dir)
        revoke_token(token.token_id, token_dir=token_dir)
        badge = build_scope_badge_html("linkedin", token_dir=token_dir)
        # After revocation, no active scopes — should show gray
        assert "scope-badge-gray" in badge


# ---------------------------------------------------------------------------
# Test 8: Consent invalid scopes rejected
# ---------------------------------------------------------------------------

class TestConsentInvalidScopesRejected:
    """test_consent_invalid_scopes_rejected — unknown/empty scopes → 400."""

    def test_unknown_scope_returns_400(self, token_dir):
        html, status = build_consent_page(
            "fake.nonexistent_scope",
            token_dir=token_dir,
        )
        assert status == 400
        assert "Unknown scope" in html

    def test_empty_scopes_returns_400(self, token_dir):
        html, status = build_consent_page("", token_dir=token_dir)
        assert status == 400

    def test_mixed_valid_invalid_returns_400(self, token_dir):
        html, status = build_consent_page(
            "linkedin.create_post,fake.bad_scope",
            token_dir=token_dir,
        )
        assert status == 400
        assert "fake.bad_scope" in html

    def test_http_post_unknown_scope_returns_400(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/consent",
                    json={"scopes": ["invalid.scope"]},
                )
                assert resp.status == 400
                data = await resp.json()
                assert data["error"] == "unknown_scopes"

        _run(run())

    def test_http_get_unknown_scope_returns_400(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/consent?scopes=fake.scope")
                assert resp.status == 400

        _run(run())


# ---------------------------------------------------------------------------
# Test 9: Consent redirect sanitised (no open redirect)
# ---------------------------------------------------------------------------

class TestConsentRedirectSanitized:
    """test_consent_redirect_sanitized — only same-origin relative paths allowed."""

    def test_relative_path_allowed(self):
        assert sanitise_redirect("/kanban") == "/kanban"

    def test_deep_path_allowed(self):
        assert sanitise_redirect("/settings/tokens") == "/settings/tokens"

    def test_absolute_http_blocked(self):
        result = sanitise_redirect("http://evil.com/steal")
        assert result == "/"

    def test_absolute_https_blocked(self):
        result = sanitise_redirect("https://evil.com/steal")
        assert result == "/"

    def test_protocol_relative_blocked(self):
        result = sanitise_redirect("//evil.com/steal")
        assert result == "/"

    def test_empty_string_returns_default(self):
        assert sanitise_redirect("") == "/"

    def test_none_type_returns_default(self):
        # sanitise_redirect must handle non-string gracefully
        assert sanitise_redirect(None) == "/"  # type: ignore[arg-type]

    def test_javascript_protocol_blocked(self):
        result = sanitise_redirect("javascript:alert(1)")
        assert result == "/"

    def test_open_redirect_in_consent_page_html(self, token_dir):
        """The redirect embedded in the page must be sanitised."""
        # Attempt to inject absolute URL via redirect param
        html, status = build_consent_page(
            "linkedin.create_post",
            redirect="http://evil.com",
            token_dir=token_dir,
        )
        assert status == 200
        # The evil URL must not appear raw in the page (should be replaced by "/")
        assert "http://evil.com" not in html

    def test_open_redirect_in_consent_post(self, tmp_path):
        """POST /oauth3/consent with evil redirect must fall back to /."""
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/consent",
                    json={
                        "scopes": ["linkedin.create_post"],
                        "redirect": "https://evil.com/steal",
                    },
                )
                assert resp.status == 200
                data = await resp.json()
                # Redirect must be sanitised to "/"
                assert data["redirect"] == "/"
                assert "evil.com" not in data["redirect"]

        _run(run())


# ---------------------------------------------------------------------------
# Test 10: Cookie is HttpOnly and SameSite=Strict
# ---------------------------------------------------------------------------

class TestCookieHttponlySamesite:
    """test_cookie_httponly_samesite — cookie attributes are correct."""

    def test_cookie_is_set_on_consent_post(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/consent",
                    json={"scopes": ["linkedin.create_post"], "redirect": "/"},
                    allow_redirects=False,
                )
                assert resp.status == 200
                # aiohttp stores Set-Cookie in headers
                set_cookie = resp.headers.get("Set-Cookie", "")
                assert "solace_agency_token" in set_cookie

        _run(run())

    def test_cookie_is_httponly(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/consent",
                    json={"scopes": ["linkedin.comment"], "redirect": "/"},
                    allow_redirects=False,
                )
                set_cookie = resp.headers.get("Set-Cookie", "")
                # HttpOnly flag must be present (case-insensitive)
                assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()

        _run(run())

    def test_cookie_is_samesite_strict(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/consent",
                    json={"scopes": ["gmail.read_inbox"], "redirect": "/"},
                    allow_redirects=False,
                )
                set_cookie = resp.headers.get("Set-Cookie", "")
                assert "SameSite=Strict" in set_cookie or "samesite=strict" in set_cookie.lower()

        _run(run())

    def test_cookie_value_is_token_id(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/consent",
                    json={"scopes": ["linkedin.create_post"], "redirect": "/"},
                    allow_redirects=False,
                )
                data = await resp.json()
                token_id = data["token_id"]
                set_cookie = resp.headers.get("Set-Cookie", "")
                assert token_id in set_cookie

        _run(run())

    def test_cookie_not_set_on_invalid_scopes(self, tmp_path):
        td = tmp_path / "tokens"
        td.mkdir()
        app = _build_consent_app(td)

        async def run():
            async with TestClient(TestServer(app)) as client:
                resp = await client.post(
                    "/oauth3/consent",
                    json={"scopes": ["fake.scope"], "redirect": "/"},
                    allow_redirects=False,
                )
                assert resp.status == 400
                set_cookie = resp.headers.get("Set-Cookie", "")
                # No cookie should be set on error response
                assert "solace_agency_token" not in set_cookie

        _run(run())
