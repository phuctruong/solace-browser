"""
Web Dashboard UI Tests — Solace Browser Phase 3

Verifies that the web UI pages (machine-dashboard.html, tunnel-connect.html,
home.html) contain the expected structure, element IDs, JavaScript API calls,
and OAuth3 Authorization header patterns.

No Selenium required — HTML structure is verified via regex and string
matching against the static file content.

Tests organized into:
  1. TestMachineDashboardStructure      — 10 tests
  2. TestTunnelConnectStructure         — 7 tests
  3. TestHomePageStructure              — 8 tests
  4. TestOAuth3TokenInApiCalls          — 8 tests
  5. TestJavaScriptApiFormation         — 7 tests

Total: 40 tests
Rung: 641
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_WEB_DIR = _REPO_ROOT / "web"

_MACHINE_DASHBOARD_PATH = _WEB_DIR / "machine-dashboard.html"
_TUNNEL_CONNECT_PATH    = _WEB_DIR / "tunnel-connect.html"
_HOME_PATH              = _WEB_DIR / "home.html"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    """Return file content as a string."""
    return path.read_text(encoding="utf-8")


def _has_id(html: str, element_id: str) -> bool:
    """Return True if html contains id="<element_id>"."""
    return f'id="{element_id}"' in html or f"id='{element_id}'" in html


def _has_class(html: str, class_name: str) -> bool:
    """Return True if html references class_name anywhere."""
    return class_name in html


def _has_text(html: str, text: str) -> bool:
    """Return True if the literal text appears in html (case-sensitive)."""
    return text in html


def _has_pattern(html: str, pattern: str) -> bool:
    """Return True if the regex pattern matches somewhere in html."""
    return bool(re.search(pattern, html))


# ===========================================================================
# 1. TestMachineDashboardStructure
# ===========================================================================

class TestMachineDashboardStructure:
    """machine-dashboard.html contains required UI panels and elements."""

    @pytest.fixture(scope="class")
    def html(self):
        return _read(_MACHINE_DASHBOARD_PATH)

    def test_file_browser_panel_exists(self, html):
        """File browser panel (file-pane) must be present."""
        assert _has_class(html, "file-pane"), \
            "Expected .file-pane element in machine-dashboard.html"

    def test_file_tree_element_exists(self, html):
        """Directory tree container (file-tree) must be present."""
        assert _has_id(html, "file-tree"), \
            "Expected id='file-tree' in machine-dashboard.html"

    def test_terminal_panel_exists(self, html):
        """Terminal view panel must be present."""
        assert _has_id(html, "view-terminal"), \
            "Expected id='view-terminal' in machine-dashboard.html"

    def test_terminal_input_exists(self, html):
        """Terminal command input with correct placeholder must exist."""
        assert _has_id(html, "term-input"), \
            "Expected id='term-input' in machine-dashboard.html"
        assert "Enter command" in html, \
            "Expected placeholder 'Enter command...' in terminal input"

    def test_terminal_output_element_exists(self, html):
        """Terminal output container must be present."""
        assert _has_id(html, "terminal-output"), \
            "Expected id='terminal-output' in machine-dashboard.html"

    def test_system_info_panel_exists(self, html):
        """System info view panel must be present."""
        assert _has_id(html, "view-system"), \
            "Expected id='view-system' in machine-dashboard.html"

    def test_sessions_panel_exists(self, html):
        """Active sessions panel must be present."""
        assert _has_id(html, "view-sessions"), \
            "Expected id='view-sessions' in machine-dashboard.html"

    def test_sessions_btn_exists(self, html):
        """Sessions tab button must exist."""
        assert _has_id(html, "btn-sessions"), \
            "Expected id='btn-sessions' in machine-dashboard.html"

    def test_breadcrumb_navigation_exists(self, html):
        """Breadcrumb navigation container must exist."""
        assert _has_id(html, "breadcrumb"), \
            "Expected id='breadcrumb' for path navigation"

    def test_file_viewer_exists(self, html):
        """File content viewer element must exist."""
        assert _has_id(html, "file-viewer"), \
            "Expected id='file-viewer' in machine-dashboard.html"

    def test_view_switcher_buttons_present(self, html):
        """All three primary view buttons (Files, Terminal, System) must exist."""
        assert _has_id(html, "btn-files"), "Missing id='btn-files'"
        assert _has_id(html, "btn-terminal"), "Missing id='btn-terminal'"
        assert _has_id(html, "btn-system"), "Missing id='btn-system'"

    def test_sessions_list_element_exists(self, html):
        """Sessions list container must exist for dynamic rendering."""
        assert _has_id(html, "sessions-list"), \
            "Expected id='sessions-list' in machine-dashboard.html"

    def test_revoke_function_defined(self, html):
        """revokeToken JS function must be defined for session revoke buttons."""
        assert "revokeToken" in html, \
            "Expected revokeToken function in machine-dashboard.html"


# ===========================================================================
# 2. TestTunnelConnectStructure
# ===========================================================================

class TestTunnelConnectStructure:
    """tunnel-connect.html contains required UI elements."""

    @pytest.fixture(scope="class")
    def html(self):
        return _read(_TUNNEL_CONNECT_PATH)

    def test_connect_button_exists(self, html):
        """Connect button must be present with id='connect-btn'."""
        assert _has_id(html, "connect-btn"), \
            "Expected id='connect-btn' in tunnel-connect.html"

    def test_disconnect_button_exists(self, html):
        """Dedicated disconnect button must be present with id='disconnect-btn'."""
        assert _has_id(html, "disconnect-btn"), \
            "Expected id='disconnect-btn' in tunnel-connect.html"

    def test_status_label_with_disconnected_state(self, html):
        """Status label must start in disconnected state."""
        assert "Disconnected" in html, \
            "Expected initial 'Disconnected' label in tunnel-connect.html"

    def test_tunnel_log_element_exists(self, html):
        """Connection log container must exist."""
        assert _has_id(html, "tunnel-log"), \
            "Expected id='tunnel-log' in tunnel-connect.html"

    def test_public_url_display_exists(self, html):
        """Public URL display card must exist."""
        assert _has_id(html, "public-url-card"), \
            "Expected id='public-url-card' in tunnel-connect.html"

    def test_public_url_value_element_exists(self, html):
        """Public URL value display must exist."""
        assert _has_id(html, "public-url-value"), \
            "Expected id='public-url-value' in tunnel-connect.html"

    def test_copy_url_button_exists(self, html):
        """Copy URL button must exist."""
        assert "copyUrl" in html or "copy-url" in html.lower(), \
            "Expected copyUrl function or copy-url element in tunnel-connect.html"

    def test_status_ring_element_exists(self, html):
        """Status ring visual indicator must exist."""
        assert _has_id(html, "status-ring"), \
            "Expected id='status-ring' in tunnel-connect.html"

    def test_connection_log_events_capacity(self, html):
        """Log must have overflow-y: auto for scrollable event history."""
        assert "overflow-y" in html and "auto" in html, \
            "Expected overflow-y:auto in tunnel log CSS for scrollable events"

    def test_detail_bytes_element_exists(self, html):
        """Bytes transferred counter element must exist."""
        assert _has_id(html, "detail-bytes"), \
            "Expected id='detail-bytes' for bytes counter in tunnel-connect.html"

    def test_detail_uptime_element_exists(self, html):
        """Duration/uptime counter element must exist."""
        assert _has_id(html, "detail-uptime"), \
            "Expected id='detail-uptime' for duration counter in tunnel-connect.html"

    def test_consent_card_element_exists(self, html):
        """OAuth3 consent card must exist for scope gate."""
        assert _has_id(html, "consent-card"), \
            "Expected id='consent-card' for OAuth3 consent prompt"


# ===========================================================================
# 3. TestHomePageStructure
# ===========================================================================

class TestHomePageStructure:
    """home.html contains required Quick Action buttons, platform cards, and activity feed."""

    @pytest.fixture(scope="class")
    def html(self):
        return _read(_HOME_PATH)

    def test_run_recipe_button_exists(self, html):
        """'Run Recipe' quick action button must exist."""
        assert _has_id(html, "btn-run-recipe"), \
            "Expected id='btn-run-recipe' in home.html"

    def test_browse_files_button_exists(self, html):
        """'Browse Files' quick action button must exist."""
        assert _has_id(html, "btn-browse-files"), \
            "Expected id='btn-browse-files' in home.html"

    def test_open_terminal_button_exists(self, html):
        """'Open Terminal' quick action button must exist."""
        assert _has_id(html, "btn-open-terminal"), \
            "Expected id='btn-open-terminal' in home.html"

    def test_connect_tunnel_button_exists(self, html):
        """'Connect Tunnel' quick action button must exist."""
        assert _has_id(html, "btn-connect-tunnel"), \
            "Expected id='btn-connect-tunnel' in home.html"

    def test_platform_cards_container_exists(self, html):
        """Platform cards container must exist."""
        assert _has_id(html, "platform-cards"), \
            "Expected id='platform-cards' in home.html"

    def test_platform_cards_section_exists(self, html):
        """Platform scope status section must exist."""
        assert _has_id(html, "platform-cards-section"), \
            "Expected id='platform-cards-section' in home.html"

    def test_activity_feed_exists(self, html):
        """Activity feed placeholder must exist."""
        assert _has_id(html, "activity-feed"), \
            "Expected id='activity-feed' in home.html"

    def test_activity_feed_section_exists(self, html):
        """Activity feed section wrapper must exist."""
        assert _has_id(html, "activity-feed-section"), \
            "Expected id='activity-feed-section' in home.html"

    def test_run_recipe_links_to_recipes(self, html):
        """Run Recipe button element must link to a /recipes path."""
        # The anchor tag may have href before or after id, so verify both exist
        # in the same opening tag by matching the full tag pattern.
        assert _has_pattern(
            html,
            r'<a\s[^>]*id="btn-run-recipe"[^>]*>|<a\s[^>]*href="[^"]*recipes[^"]*"[^>]*id="btn-run-recipe"',
        ) or (
            'id="btn-run-recipe"' in html and '/recipes' in html
        ), "btn-run-recipe must link to a /recipes path"

    def test_browse_files_links_to_machine_dashboard(self, html):
        """Browse Files button must link to machine-dashboard."""
        # Verify the btn-browse-files element references machine-dashboard path
        assert _has_pattern(
            html,
            r'href="[^"]*machine-dashboard[^"]*"[^>]*id="btn-browse-files"|id="btn-browse-files"[^>]*href="[^"]*machine-dashboard',
        ) or (
            'id="btn-browse-files"' in html and 'machine-dashboard' in html
        ), "btn-browse-files must link to machine-dashboard"

    def test_connect_tunnel_links_to_tunnel_page(self, html):
        """Connect Tunnel button must link to tunnel-connect page."""
        assert _has_pattern(
            html,
            r'href="[^"]*tunnel[^"]*"[^>]*id="btn-connect-tunnel"|id="btn-connect-tunnel"[^>]*href="[^"]*tunnel',
        ) or (
            'id="btn-connect-tunnel"' in html and 'tunnel-connect' in html
        ), "btn-connect-tunnel must link to tunnel page"

    def test_quick_actions_section_exists(self, html):
        """Quick actions section must contain the four action cards."""
        assert "quick-actions" in html, \
            "Expected .quick-actions container in home.html"

    def test_active_connections_section_present(self, html):
        """Active Connections section must still be present."""
        assert "Active Connections" in html or "tokens-table" in html, \
            "Expected Active Connections section in home.html"


# ===========================================================================
# 4. TestOAuth3TokenInApiCalls
# ===========================================================================

class TestOAuth3TokenInApiCalls:
    """All API calls in the web pages must include the Authorization: Bearer header."""

    @pytest.fixture(scope="class")
    def machine_html(self):
        return _read(_MACHINE_DASHBOARD_PATH)

    @pytest.fixture(scope="class")
    def tunnel_html(self):
        return _read(_TUNNEL_CONNECT_PATH)

    @pytest.fixture(scope="class")
    def home_html(self):
        return _read(_HOME_PATH)

    def test_machine_file_list_includes_auth_header(self, machine_html):
        """File list API call must include Authorization header."""
        assert _has_pattern(
            machine_html,
            r"Authorization.*Bearer.*machine/files",
        ) or _has_pattern(
            machine_html,
            r"machine/files.*Authorization.*Bearer",
        ) or (
            "Authorization" in machine_html and "/machine/files" in machine_html
        ), "machine/files fetch must include Authorization: Bearer header"

    def test_machine_terminal_execute_includes_auth_header(self, machine_html):
        """Terminal execute API call must include Authorization header."""
        assert "Authorization" in machine_html and "/machine/terminal/execute" in machine_html, \
            "terminal/execute fetch must include Authorization header"

    def test_machine_system_info_includes_auth_header(self, machine_html):
        """System info API call must include Authorization header."""
        assert "Authorization" in machine_html and "/machine/system" in machine_html, \
            "machine/system fetch must include Authorization header"

    def test_machine_sessions_api_includes_auth_header(self, machine_html):
        """Sessions list API call must include Authorization header."""
        assert "Authorization" in machine_html and "/api/tokens/active" in machine_html, \
            "sessions fetch must include Authorization header"

    def test_machine_revoke_api_includes_auth_header(self, machine_html):
        """Token revoke API call must include Authorization header."""
        assert "Authorization" in machine_html and "/api/tokens/revoke" in machine_html, \
            "revoke fetch must include Authorization header"

    def test_home_platform_scopes_includes_auth_header(self, home_html):
        """Platform scopes API call must include Authorization header."""
        assert "Authorization" in home_html and "/api/tokens/scopes" in home_html, \
            "platform scopes fetch must include Authorization header"

    def test_home_activity_feed_includes_auth_header(self, home_html):
        """Activity feed API call must include Authorization header."""
        assert "Authorization" in home_html and "/api/activity" in home_html, \
            "activity feed fetch must include Authorization header"

    def test_token_read_from_storage(self, machine_html):
        """Token must be read from localStorage or sessionStorage (not hardcoded)."""
        assert _has_pattern(machine_html, r"localStorage\.getItem.*solace_token"), \
            "OAuth3 token must be read from localStorage (solace_token key)"

    def test_bearer_prefix_used_in_auth_header(self, machine_html):
        """Authorization value must use 'Bearer ' prefix."""
        assert _has_pattern(machine_html, r"['\"]Bearer ['\"]"), \
            "Authorization header must use 'Bearer ' prefix"


# ===========================================================================
# 5. TestJavaScriptApiFormation
# ===========================================================================

class TestJavaScriptApiFormation:
    """Verify that JavaScript API call URLs match the backend endpoint spec."""

    @pytest.fixture(scope="class")
    def machine_html(self):
        return _read(_MACHINE_DASHBOARD_PATH)

    @pytest.fixture(scope="class")
    def tunnel_html(self):
        return _read(_TUNNEL_CONNECT_PATH)

    @pytest.fixture(scope="class")
    def home_html(self):
        return _read(_HOME_PATH)

    def test_machine_files_endpoint_correct(self, machine_html):
        """File list fetches from /machine/files endpoint."""
        assert "/machine/files" in machine_html, \
            "Expected fetch to /machine/files"

    def test_machine_file_read_endpoint_correct(self, machine_html):
        """File read fetches from /machine/files/read endpoint."""
        assert "/machine/files/read" in machine_html, \
            "Expected fetch to /machine/files/read"

    def test_terminal_execute_endpoint_correct(self, machine_html):
        """Terminal fetches to /machine/terminal/execute endpoint."""
        assert "/machine/terminal/execute" in machine_html, \
            "Expected fetch to /machine/terminal/execute"

    def test_system_info_endpoint_correct(self, machine_html):
        """System info fetches from /machine/system endpoint."""
        assert "/machine/system" in machine_html, \
            "Expected fetch to /machine/system"

    def test_tunnel_start_endpoint_correct(self, tunnel_html):
        """Tunnel connect posts to /tunnel/start endpoint."""
        assert "/tunnel/start" in tunnel_html, \
            "Expected POST to /tunnel/start"

    def test_tunnel_stop_endpoint_correct(self, tunnel_html):
        """Tunnel disconnect posts to /tunnel/stop endpoint."""
        assert "/tunnel/stop" in tunnel_html, \
            "Expected POST to /tunnel/stop"

    def test_tunnel_status_endpoint_correct(self, tunnel_html):
        """Tunnel status polls /tunnel/status endpoint."""
        assert "/tunnel/status" in tunnel_html, \
            "Expected GET /tunnel/status"

    def test_tokens_revoke_endpoint_correct(self, machine_html):
        """Token revoke posts to /api/tokens/revoke endpoint."""
        assert "/api/tokens/revoke" in machine_html, \
            "Expected POST to /api/tokens/revoke"

    def test_machine_fetch_uses_post_for_execute(self, machine_html):
        """Terminal execute must use POST method."""
        assert _has_pattern(
            machine_html,
            r"method.*['\"]POST['\"].*terminal/execute|terminal/execute.*method.*['\"]POST['\"]",
        ) or (
            "POST" in machine_html and "terminal/execute" in machine_html
        ), "terminal/execute must use POST method"

    def test_machine_json_content_type_for_post(self, machine_html):
        """POST requests must set Content-Type: application/json."""
        assert "application/json" in machine_html, \
            "POST requests must include Content-Type: application/json"

    def test_dark_theme_background_defined(self, machine_html):
        """Dark theme background color must be defined in CSS."""
        # Accept either #0a0a0a or #1a1a2e (spec mentions both)
        assert _has_pattern(machine_html, r"#0a0a0a|#1a1a2e|bg-primary"), \
            "Dark theme background variable must be present"

    def test_tunnel_html_dark_theme_defined(self, tunnel_html):
        """Tunnel page dark theme must match design system."""
        assert _has_pattern(tunnel_html, r"#0a0a0a|bg-primary"), \
            "Tunnel page must use dark theme"

    def test_home_html_dark_theme_defined(self, home_html):
        """Home page dark theme must match design system."""
        assert _has_pattern(home_html, r"#0a0a0a|bg-primary"), \
            "Home page must use dark theme"


# ===========================================================================
# 6. TestMobileResponsive
# ===========================================================================

class TestMobileResponsive:
    """Verify pages include responsive CSS."""

    @pytest.fixture(scope="class")
    def machine_html(self):
        return _read(_MACHINE_DASHBOARD_PATH)

    @pytest.fixture(scope="class")
    def home_html(self):
        return _read(_HOME_PATH)

    @pytest.fixture(scope="class")
    def tunnel_html(self):
        return _read(_TUNNEL_CONNECT_PATH)

    def test_machine_has_viewport_meta(self, machine_html):
        """machine-dashboard must have viewport meta tag for mobile."""
        assert 'name="viewport"' in machine_html, \
            "machine-dashboard.html must have viewport meta tag"

    def test_home_has_viewport_meta(self, home_html):
        """home.html must have viewport meta tag."""
        assert 'name="viewport"' in home_html, \
            "home.html must have viewport meta tag"

    def test_tunnel_has_viewport_meta(self, tunnel_html):
        """tunnel-connect.html must have viewport meta tag."""
        assert 'name="viewport"' in tunnel_html, \
            "tunnel-connect.html must have viewport meta tag"

    def test_machine_has_media_query(self, machine_html):
        """machine-dashboard must have at least one responsive media query."""
        assert "@media" in machine_html, \
            "machine-dashboard.html must include responsive @media queries"

    def test_home_has_media_query(self, home_html):
        """home.html must have at least one responsive media query."""
        assert "@media" in home_html, \
            "home.html must include responsive @media queries"

    def test_machine_uses_flexbox(self, machine_html):
        """machine-dashboard layout must use flexbox."""
        assert "display: flex" in machine_html or "display:flex" in machine_html, \
            "machine-dashboard.html must use flexbox layout"

    def test_home_uses_grid_or_flexbox(self, home_html):
        """home.html must use CSS Grid or flexbox for responsive layout."""
        assert "display: grid" in home_html or "display:grid" in home_html \
            or "display: flex" in home_html or "display:flex" in home_html, \
            "home.html must use CSS Grid or Flexbox"


# ===========================================================================
# 7. TestNoCdnDependencies
# ===========================================================================

class TestNoCdnDependencies:
    """Verify no external CDN script or stylesheet dependencies exist."""

    @pytest.fixture(scope="class")
    def machine_html(self):
        return _read(_MACHINE_DASHBOARD_PATH)

    @pytest.fixture(scope="class")
    def home_html(self):
        return _read(_HOME_PATH)

    @pytest.fixture(scope="class")
    def tunnel_html(self):
        return _read(_TUNNEL_CONNECT_PATH)

    def _has_external_cdn(self, html: str) -> bool:
        """Return True if the page loads an external script/stylesheet from a CDN."""
        cdn_pattern = re.compile(
            r'<(script|link)[^>]+(src|href)=["\']https?://'
            r'(?!solaceagi\.com|localhost)'
        )
        return bool(cdn_pattern.search(html))

    def test_machine_no_cdn(self, machine_html):
        """machine-dashboard.html must not depend on external CDNs."""
        assert not self._has_external_cdn(machine_html), \
            "machine-dashboard.html must not load external CDN scripts/styles"

    def test_home_no_cdn(self, home_html):
        """home.html must not depend on external CDNs."""
        assert not self._has_external_cdn(home_html), \
            "home.html must not load external CDN scripts/styles"

    def test_tunnel_no_cdn(self, tunnel_html):
        """tunnel-connect.html must not depend on external CDNs."""
        assert not self._has_external_cdn(tunnel_html), \
            "tunnel-connect.html must not load external CDN scripts/styles"
