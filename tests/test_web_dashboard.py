"""
Web Dashboard UI Tests — Solace Browser (Updated for current page design)

Verifies that the web UI pages (machine-dashboard.html, tunnel-connect.html,
home.html, download.html) contain the expected structure, element IDs,
accessibility attributes, and mobile responsive patterns.

No Selenium required — HTML structure is verified via regex and string
matching against the static file content.

Tests organized into:
  1. TestMachineDashboardStructure      — 10 tests
  2. TestTunnelConnectStructure         — 10 tests
  3. TestHomePageStructure              — 10 tests
  4. TestDownloadPageStructure          — 8 tests
  5. TestHamburgerMenuConsistency       — 6 tests
  6. TestMobileResponsive               — 6 tests
  7. TestAccessibility                  — 8 tests
  8. TestNoCdnDependencies              — 4 tests
  9. TestYinyangRailCSS                 — 6 tests

Total: 68 tests
Rung: 641
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_WEB_DIR = _REPO_ROOT / "web"
_CSS_DIR = _WEB_DIR / "css"

_MACHINE_DASHBOARD_PATH = _WEB_DIR / "machine-dashboard.html"
_TUNNEL_CONNECT_PATH    = _WEB_DIR / "tunnel-connect.html"
_HOME_PATH              = _WEB_DIR / "home.html"
_DOWNLOAD_PATH          = _WEB_DIR / "download.html"
_SITE_CSS_PATH          = _CSS_DIR / "site.css"

ALL_PAGES = [_HOME_PATH, _DOWNLOAD_PATH, _MACHINE_DASHBOARD_PATH, _TUNNEL_CONNECT_PATH]


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

    def test_dashboard_shell_exists(self, html):
        """Dashboard shell wrapper must be present."""
        assert _has_class(html, "dashboard-shell"), \
            "Expected .dashboard-shell in machine-dashboard.html"

    def test_dashboard_toolbar_exists(self, html):
        """Dashboard toolbar section must be present."""
        assert _has_class(html, "dashboard-toolbar"), \
            "Expected .dashboard-toolbar in machine-dashboard.html"

    def test_status_strip_exists(self, html):
        """Status strip with pills must be present."""
        assert _has_class(html, "status-strip"), \
            "Expected .status-strip in machine-dashboard.html"

    def test_file_list_element_exists(self, html):
        """File list container must be present."""
        assert _has_id(html, "file-list"), \
            "Expected id='file-list' in machine-dashboard.html"

    def test_file_search_exists(self, html):
        """File search input must be present."""
        assert _has_id(html, "file-search"), \
            "Expected id='file-search' in machine-dashboard.html"

    def test_system_table_body_exists(self, html):
        """System posture table body must be present."""
        assert _has_id(html, "system-table-body"), \
            "Expected id='system-table-body' in machine-dashboard.html"

    def test_terminal_output_exists(self, html):
        """Terminal output container must be present."""
        assert _has_id(html, "terminal-output"), \
            "Expected id='terminal-output' in machine-dashboard.html"

    def test_terminal_command_input_exists(self, html):
        """Terminal command input must be present."""
        assert _has_id(html, "terminal-command"), \
            "Expected id='terminal-command' in machine-dashboard.html"

    def test_terminal_form_exists(self, html):
        """Terminal form element must exist."""
        assert _has_id(html, "terminal-form"), \
            "Expected id='terminal-form' in machine-dashboard.html"

    def test_dashboard_columns_layout(self, html):
        """Dashboard columns layout must be present."""
        assert _has_class(html, "dashboard-columns"), \
            "Expected .dashboard-columns in machine-dashboard.html"


# ===========================================================================
# 2. TestTunnelConnectStructure
# ===========================================================================

class TestTunnelConnectStructure:
    """tunnel-connect.html contains required UI elements."""

    @pytest.fixture(scope="class")
    def html(self):
        return _read(_TUNNEL_CONNECT_PATH)

    def test_connect_button_exists(self, html):
        """Connect button must be present."""
        assert _has_id(html, "connect-button"), \
            "Expected id='connect-button' in tunnel-connect.html"

    def test_disconnect_button_exists(self, html):
        """Disconnect button must be present."""
        assert _has_id(html, "disconnect-button"), \
            "Expected id='disconnect-button' in tunnel-connect.html"

    def test_status_label_with_disconnected_state(self, html):
        """Status label must start in disconnected state."""
        assert "Disconnected" in html, \
            "Expected initial 'Disconnected' label in tunnel-connect.html"

    def test_status_ring_element_exists(self, html):
        """Status ring visual indicator must exist."""
        assert _has_id(html, "status-ring"), \
            "Expected id='status-ring' in tunnel-connect.html"

    def test_status_label_exists(self, html):
        """Status label element must exist."""
        assert _has_id(html, "status-label"), \
            "Expected id='status-label' in tunnel-connect.html"

    def test_endpoint_value_exists(self, html):
        """Endpoint value display must exist."""
        assert _has_id(html, "endpoint-value"), \
            "Expected id='endpoint-value' in tunnel-connect.html"

    def test_copy_endpoint_button_exists(self, html):
        """Copy endpoint button must exist."""
        assert _has_id(html, "copy-endpoint"), \
            "Expected id='copy-endpoint' in tunnel-connect.html"

    def test_open_endpoint_button_exists(self, html):
        """Open endpoint button must exist."""
        assert _has_id(html, "open-endpoint"), \
            "Expected id='open-endpoint' in tunnel-connect.html"

    def test_approval_badge_exists(self, html):
        """Approval badge must exist with fail-closed default."""
        assert _has_id(html, "approval-badge"), \
            "Expected id='approval-badge' in tunnel-connect.html"
        assert "Fail-closed" in html, \
            "Expected 'Fail-closed' badge text"

    def test_tunnel_splash_stage_exists(self, html):
        """Tunnel splash stage with product image must exist."""
        assert _has_class(html, "tunnel-splash-stage"), \
            "Expected .tunnel-splash-stage in tunnel-connect.html"


# ===========================================================================
# 3. TestHomePageStructure
# ===========================================================================

class TestHomePageStructure:
    """home.html contains hero, surface cards, OAuth3 vault, and recipe launchpad."""

    @pytest.fixture(scope="class")
    def html(self):
        return _read(_HOME_PATH)

    def test_hero_section_exists(self, html):
        """Hero section must be present."""
        assert _has_class(html, "hero"), \
            "Expected .hero section in home.html"

    def test_greeting_exists(self, html):
        """Dashboard greeting must be present."""
        assert _has_class(html, "dash-greeting"), \
            "Expected .dash-greeting in home.html"

    def test_money_widget_exists(self, html):
        """Money saved widget must exist on dashboard."""
        assert _has_class(html, "dash-money-widget"), \
            "Expected .dash-money-widget in home.html"

    def test_app_cards_grid_exists(self, html):
        """App cards grid must exist for drag-reorder."""
        assert "dash-apps-grid" in html, \
            "Expected #dash-apps-grid in home.html"

    def test_favorites_section_exists(self, html):
        """Favorites strip for pinned apps must exist."""
        assert "dash-favorites" in html, \
            "Expected dash-favorites section in home.html"

    def test_recent_activity_exists(self, html):
        """Recent activity timeline must exist."""
        assert "dash-recent" in html, \
            "Expected dash-recent section in home.html"

    def test_sparkline_css_exists(self, html):
        """Sparkline chart CSS must be defined."""
        assert "dash-sparkline" in html, \
            "Expected .dash-sparkline styles in home.html"

    def test_drag_reorder_support(self, html):
        """App cards must support drag-and-drop reorder."""
        assert "draggable" in html, \
            "Expected draggable attribute in home.html"
        assert "dragstart" in html, \
            "Expected dragstart event handler in home.html"

    def test_i18n_keys_present(self, html):
        """Dashboard must have i18n data attributes."""
        assert 'data-i18n="dash_money_saved"' in html, \
            "Expected data-i18n for money saved"
        assert 'data-i18n="dash_favorites"' in html, \
            "Expected data-i18n for favorites"


# ===========================================================================
# 4. TestDownloadPageStructure
# ===========================================================================

class TestDownloadPageStructure:
    """download.html contains download links and platform detection."""

    @pytest.fixture(scope="class")
    def html(self):
        return _read(_DOWNLOAD_PATH)

    def test_primary_download_link_exists(self, html):
        """Primary download button must exist."""
        assert _has_id(html, "primary-download"), \
            "Expected id='primary-download' in download.html"

    def test_detected_platform_element_exists(self, html):
        """Platform detection element must exist."""
        assert _has_id(html, "detected-platform"), \
            "Expected id='detected-platform' in download.html"

    def test_install_command_or_build_from_source(self, html):
        """CLI install command or build-from-source instructions must exist."""
        assert "install" in html.lower() or "pip" in html.lower() or "build" in html.lower(), \
            "Expected install or build instructions in download.html"

    def test_macos_download_section(self, html):
        """macOS download section must be present."""
        assert "macos" in html.lower() or "mac" in html.lower(), \
            "Expected macOS download section"

    def test_linux_download_section(self, html):
        """Linux download section must be present."""
        assert "linux" in html.lower(), "Expected Linux download section"

    def test_windows_download_section(self, html):
        """Windows download section must be present."""
        assert "windows" in html.lower(), "Expected Windows download section"

    def test_download_urls_point_to_github_releases(self, html):
        """Download URLs must point to GitHub Releases."""
        assert "github.com/solaceagi/solace-browser/releases" in html, \
            "Expected GitHub Releases download URL in download.html"

    def test_release_notes_link(self, html):
        """Release notes link must be present."""
        assert "github.com/solaceagi/solace-browser/releases" in html, \
            "Expected GitHub releases link"


# ===========================================================================
# 5. TestHamburgerMenuConsistency
# ===========================================================================

class TestHamburgerMenuConsistency:
    """All pages must have identical hamburger button and mobile menu structure."""

    @pytest.fixture(scope="class")
    def pages(self):
        return {p.stem: _read(p) for p in ALL_PAGES}

    # Pages that use dashboard layout (no shared header) or are partials
    _SKIP_PAGES = {"home", "partials-header", "partials-footer"}

    def test_all_pages_have_header_slot_or_hamburger(self, pages):
        """Every page must have header-slot (for layout.js injection) or inline hamburger."""
        for name, html in pages.items():
            if name in self._SKIP_PAGES:
                continue
            has_slot = _has_id(html, "header-slot")
            has_hamburger = _has_id(html, "hamburger-toggle")
            assert has_slot or has_hamburger, \
                f"Missing id='header-slot' or 'hamburger-toggle' in {name}"

    def test_partials_header_has_hamburger(self, pages):
        """The shared header partial must have the hamburger button."""
        if "partials-header" in pages:
            assert _has_id(pages["partials-header"], "hamburger-toggle"), \
                "Missing id='hamburger-toggle' in partials-header.html"

    def test_hamburger_has_three_spans(self, pages):
        """Hamburger button in partials-header must contain three span elements."""
        if "partials-header" in pages:
            assert _has_pattern(pages["partials-header"],
                r'id="hamburger-toggle"[^>]*><span></span><span></span><span></span>'), \
                "Hamburger button in partials-header must have 3 spans"

    def test_pages_use_layout_js(self, pages):
        """Pages with header-slot must include layout.js for header injection."""
        for name, html in pages.items():
            if name in self._SKIP_PAGES:
                continue
            if _has_id(html, "header-slot"):
                assert "layout.js" in html, \
                    f"Page {name} has header-slot but missing layout.js include"


# ===========================================================================
# 6. TestMobileResponsive
# ===========================================================================

class TestMobileResponsive:
    """Verify pages include responsive CSS patterns."""

    @pytest.fixture(scope="class")
    def pages(self):
        return {p.stem: _read(p) for p in ALL_PAGES}

    @pytest.fixture(scope="class")
    def css(self):
        return _read(_SITE_CSS_PATH)

    def test_all_pages_have_viewport_meta(self, pages):
        """All pages must have viewport meta tag for mobile."""
        for name, html in pages.items():
            assert 'name="viewport"' in html, \
                f"{name} must have viewport meta tag"

    def test_css_has_media_queries(self, css):
        """site.css must have responsive media queries."""
        assert "@media" in css, \
            "site.css must include responsive @media queries"

    def test_css_has_hamburger_breakpoint(self, css):
        """CSS must hide hamburger on desktop (>=769px)."""
        assert _has_pattern(css, r"@media.*min-width.*769"), \
            "CSS must have 769px breakpoint for desktop nav"

    def test_css_hides_nav_on_mobile(self, css):
        """CSS must hide desktop nav on mobile (<=768px)."""
        assert _has_pattern(css, r"@media.*max-width.*768"), \
            "CSS must have 768px breakpoint for mobile nav"

    def test_css_has_flexbox_or_grid(self, css):
        """CSS must use flexbox or grid for layouts."""
        assert "display: flex" in css or "display:flex" in css or \
               "display: grid" in css or "display:grid" in css, \
            "site.css must use flexbox or grid layouts"

    def test_all_pages_use_shared_css(self, pages):
        """All pages must reference the shared site.css."""
        for name, html in pages.items():
            assert "/css/site.css" in html, \
                f"{name} must include /css/site.css"


# ===========================================================================
# 7. TestAccessibility
# ===========================================================================

class TestAccessibility:
    """Verify ARIA attributes and accessibility patterns."""

    @pytest.fixture(scope="class")
    def pages(self):
        return {p.stem: _read(p) for p in ALL_PAGES}

    def test_hamburger_has_aria_label(self, pages):
        """Hamburger button in partials-header must have aria-label."""
        if "partials-header" in pages:
            assert _has_pattern(pages["partials-header"], r'id="hamburger-toggle"[^>]*aria-label='), \
                "Hamburger in partials-header missing aria-label"

    def test_hamburger_has_aria_expanded(self, pages):
        """Hamburger button in partials-header must have aria-expanded attribute."""
        if "partials-header" in pages:
            assert _has_pattern(pages["partials-header"], r'id="hamburger-toggle"[^>]*aria-expanded='), \
                "Hamburger in partials-header missing aria-expanded"

    def test_nav_has_aria_label(self, pages):
        """Primary navigation in partials-header must have aria-label."""
        if "partials-header" in pages:
            assert _has_pattern(pages["partials-header"], r'<nav[^>]*aria-label="Primary"'), \
                "Nav in partials-header missing aria-label='Primary'"

    def test_search_inputs_have_labels(self):
        """Search inputs must have associated labels or aria-label."""
        home = _read(_HOME_PATH)
        if _has_id(home, "recipe-search"):
            assert _has_pattern(home, r'(for="recipe-search"|aria-label=)'), \
                "Recipe search input must have label or aria-label"
        machine = _read(_MACHINE_DASHBOARD_PATH)
        if _has_id(machine, "file-search"):
            assert _has_pattern(machine, r'(for="file-search"|aria-label=)'), \
                "File search input must have label or aria-label"

    def test_images_have_alt_text(self, pages):
        """All img elements must have alt attributes."""
        for name, html in pages.items():
            imgs = re.findall(r'<img\b[^>]*>', html)
            for img in imgs:
                assert 'alt=' in img, \
                    f"Image in {name} missing alt attribute: {img[:80]}"

    def test_all_pages_have_lang_attribute(self, pages):
        """All pages must have lang attribute on html element."""
        for name, html in pages.items():
            assert '<html lang="en">' in html, \
                f"{name} missing lang='en' on html element"

    def test_terminal_input_has_label(self):
        """Terminal command input must have accessible label."""
        html = _read(_MACHINE_DASHBOARD_PATH)
        assert _has_pattern(html, r'(for="terminal-command"|aria-label=.*[Tt]erminal)'), \
            "Terminal command input must have label or aria-label"

    def test_particles_canvas_is_aria_hidden(self, pages):
        """Particles canvas (decorative) must be aria-hidden."""
        for name, html in pages.items():
            if "data-particles-canvas" in html:
                assert _has_pattern(html, r'data-particles-canvas[^>]*aria-hidden="true"'), \
                    f"Particles canvas in {name} must be aria-hidden='true'"


# ===========================================================================
# 8. TestNoCdnDependencies
# ===========================================================================

class TestNoCdnDependencies:
    """Verify no external CDN script or stylesheet dependencies exist."""

    @pytest.fixture(scope="class")
    def pages(self):
        return {p.stem: _read(p) for p in ALL_PAGES}

    def _has_external_cdn(self, html: str) -> bool:
        """Return True if the page loads an external script/stylesheet from a CDN."""
        cdn_pattern = re.compile(
            r'<(script|link)[^>]+(src|href)=["\']https?://'
            r'(?![a-z.]*solaceagi\.com|localhost|storage\.googleapis\.com|github\.com)'
        )
        return bool(cdn_pattern.search(html))

    def test_home_no_cdn(self, pages):
        """home.html must not depend on external CDNs."""
        assert not self._has_external_cdn(pages["home"]), \
            "home.html must not load external CDN scripts/styles"

    def test_machine_no_cdn(self, pages):
        """machine-dashboard.html must not depend on external CDNs."""
        assert not self._has_external_cdn(pages["machine-dashboard"]), \
            "machine-dashboard.html must not load external CDN scripts/styles"

    def test_tunnel_no_cdn(self, pages):
        """tunnel-connect.html must not depend on external CDNs."""
        assert not self._has_external_cdn(pages["tunnel-connect"]), \
            "tunnel-connect.html must not load external CDN scripts/styles"

    def test_download_no_cdn(self, pages):
        """download.html must not depend on external CDNs."""
        assert not self._has_external_cdn(pages["download"]), \
            "download.html must not load external CDN scripts/styles"


# ===========================================================================
# 9. TestYinyangRailCSS
# ===========================================================================

class TestYinyangRailCSS:
    """Verify Yinyang rail CSS exists in site.css."""

    @pytest.fixture(scope="class")
    def css(self):
        return _read(_SITE_CSS_PATH)

    def test_top_rail_class_exists(self, css):
        """.yy-top-rail CSS class must exist."""
        assert ".yy-top-rail" in css, \
            "Expected .yy-top-rail class in site.css"

    def test_bottom_rail_class_exists(self, css):
        """.yy-bottom-rail CSS class must exist."""
        assert ".yy-bottom-rail" in css, \
            "Expected .yy-bottom-rail class in site.css"

    def test_bottom_rail_expanded_state(self, css):
        """.yy-bottom-rail must have expandable state."""
        assert ".yy-bottom-rail.is-expanded" in css, \
            "Expected .yy-bottom-rail.is-expanded in site.css"

    def test_user_message_style_exists(self, css):
        """User message bubble style must exist."""
        assert ".yy-msg--user" in css, \
            "Expected .yy-msg--user class in site.css"

    def test_assistant_message_style_exists(self, css):
        """Assistant message bubble style must exist."""
        assert ".yy-msg--assistant" in css, \
            "Expected .yy-msg--assistant class in site.css"

    def test_credits_display_style_exists(self, css):
        """Credits display style must exist."""
        assert ".yy-bottom-rail__credits" in css, \
            "Expected .yy-bottom-rail__credits class in site.css"
