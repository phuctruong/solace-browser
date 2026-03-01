"""
App Store & Settings Page Tests — Solace Browser

Verifies that the new web UI pages (app-store.html, app-detail.html,
settings.html) contain the expected structure, navigation, content,
and accessibility patterns.

Tests organized into:
  1. TestAppStorePageStructure    — 12 tests
  2. TestAppDetailPageStructure   — 12 tests
  3. TestSettingsPageStructure    — 14 tests
  4. TestNavigationConsistency    — 8 tests
  5. TestServerRoutes             — 6 tests
  6. TestOpenAPISpec              — 8 tests

Total: 60 tests
Rung: 641
"""

from __future__ import annotations

import re
import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent
_WEB_DIR = _REPO_ROOT / "web"
_CSS_DIR = _WEB_DIR / "css"
_SRC_DIR = _REPO_ROOT / "src"

_APP_STORE_PATH = _WEB_DIR / "app-store.html"
_APP_DETAIL_PATH = _WEB_DIR / "app-detail.html"
_SETTINGS_PATH = _WEB_DIR / "settings.html"
_SERVER_PATH = _WEB_DIR / "server.py"
_OPENAPI_PATH = _SRC_DIR / "api" / "openapi.yaml"

ALL_NEW_PAGES = [_APP_STORE_PATH, _APP_DETAIL_PATH, _SETTINGS_PATH]
ALL_PAGES = list((_WEB_DIR).glob("*.html"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _has_class(html: str, cls: str) -> bool:
    return f'class="{cls}"' in html or f"class=\"{cls}" in html or f' {cls}"' in html or f' {cls} ' in html


# ===========================================================================
# 1. App Store Page Structure (12 tests)
# ===========================================================================

class TestAppStorePageStructure:

    @pytest.fixture(autouse=True)
    def load_html(self):
        self.html = _read(_APP_STORE_PATH)

    def test_page_exists(self):
        assert _APP_STORE_PATH.exists(), "app-store.html must exist"

    def test_data_page_attribute(self):
        assert 'data-page="app-store"' in self.html

    def test_title_contains_app_store(self):
        assert "<title>App Store" in self.html

    def test_has_site_css(self):
        assert 'href="/css/site.css"' in self.html

    def test_has_solace_js(self):
        assert 'src="/js/solace.js"' in self.html

    def test_has_search_input(self):
        assert 'id="app-search"' in self.html

    def test_has_communications_category(self):
        assert "Communications" in self.html

    def test_has_productivity_category(self):
        assert "Productivity" in self.html

    def test_has_engineering_category(self):
        assert "Engineering" in self.html

    def test_has_no_api_exclusives(self):
        assert "No-API Exclusives" in self.html

    def test_has_whatsapp_exclusive(self):
        assert "WhatsApp" in self.html

    def test_has_how_it_works(self):
        assert "How every app works" in self.html


# ===========================================================================
# 2. App Detail Page Structure (12 tests)
# ===========================================================================

class TestAppDetailPageStructure:

    @pytest.fixture(autouse=True)
    def load_html(self):
        self.html = _read(_APP_DETAIL_PATH)

    def test_page_exists(self):
        assert _APP_DETAIL_PATH.exists(), "app-detail.html must exist"

    def test_data_page_attribute(self):
        assert 'data-page="app-detail"' in self.html

    def test_has_inbox_section(self):
        assert "Inbox" in self.html

    def test_has_outbox_section(self):
        assert "Outbox" in self.html

    def test_has_budget_section(self):
        assert "Budget" in self.html

    def test_has_scopes_section(self):
        assert "OAuth3 Scopes" in self.html

    def test_has_execution_model(self):
        assert "Execution Model" in self.html

    def test_has_recent_runs(self):
        assert "Recent Runs" in self.html

    def test_inbox_has_prompts(self):
        assert "prompts/" in self.html

    def test_inbox_has_templates(self):
        assert "templates/" in self.html

    def test_inbox_has_policies(self):
        assert "policies/" in self.html

    def test_outbox_has_previews(self):
        assert "previews/" in self.html


# ===========================================================================
# 3. Settings Page Structure (14 tests)
# ===========================================================================

class TestSettingsPageStructure:

    @pytest.fixture(autouse=True)
    def load_html(self):
        self.html = _read(_SETTINGS_PATH)

    def test_page_exists(self):
        assert _SETTINGS_PATH.exists(), "settings.html must exist"

    def test_data_page_attribute(self):
        assert 'data-page="settings"' in self.html

    def test_has_account_section(self):
        assert 'id="account"' in self.html

    def test_has_history_section(self):
        assert 'id="history"' in self.html

    def test_has_llm_section(self):
        assert 'id="llm"' in self.html

    def test_has_tunnel_section(self):
        assert 'id="tunnel"' in self.html

    def test_has_part11_section(self):
        assert 'id="part11"' in self.html

    def test_has_privacy_section(self):
        assert 'id="privacy"' in self.html

    def test_has_yinyang_section(self):
        assert 'id="yinyang"' in self.html

    def test_has_about_section(self):
        assert 'id="about"' in self.html

    def test_settings_mentions_vault(self):
        assert "vault.enc" in self.html

    def test_settings_mentions_aes(self):
        assert "AES-256-GCM" in self.html

    def test_settings_mentions_pzip(self):
        assert "PZip" in self.html

    def test_settings_mentions_alcoa(self):
        assert "ALCOA+" in self.html


# ===========================================================================
# 4. Navigation Consistency (8 tests)
# ===========================================================================

class TestNavigationConsistency:

    def test_all_new_pages_have_app_store_nav(self):
        for page in ALL_NEW_PAGES:
            html = _read(page)
            assert 'href="/app-store"' in html, f"{page.name} missing app-store nav link"

    def test_all_new_pages_have_settings_nav(self):
        for page in ALL_NEW_PAGES:
            html = _read(page)
            assert 'href="/settings"' in html, f"{page.name} missing settings nav link"

    def test_all_new_pages_have_home_nav(self):
        for page in ALL_NEW_PAGES:
            html = _read(page)
            assert 'href="/"' in html, f"{page.name} missing home nav link"

    def test_all_new_pages_have_hamburger(self):
        for page in ALL_NEW_PAGES:
            html = _read(page)
            assert 'id="hamburger-toggle"' in html, f"{page.name} missing hamburger button"

    def test_all_new_pages_have_mobile_menu(self):
        for page in ALL_NEW_PAGES:
            html = _read(page)
            assert 'id="mobile-menu"' in html, f"{page.name} missing mobile menu"

    def test_all_new_pages_have_footer(self):
        for page in ALL_NEW_PAGES:
            html = _read(page)
            assert "site-footer" in html, f"{page.name} missing footer"

    def test_existing_pages_updated_nav(self):
        """Existing pages should link to app-store and settings."""
        for page_name in ["home.html", "download.html", "machine-dashboard.html", "tunnel-connect.html"]:
            path = _WEB_DIR / page_name
            if path.exists():
                html = _read(path)
                assert 'href="/app-store"' in html or 'href="/settings"' in html, \
                    f"{page_name} not updated with new nav links"

    def test_no_page_links_to_nonexistent_style_guide_nav(self):
        """Old style-guide nav link should be replaced in main nav."""
        for page in ALL_NEW_PAGES:
            html = _read(page)
            nav_section = re.search(r'<nav class="site-nav".*?</nav>', html, re.DOTALL)
            if nav_section:
                assert '/style-guide' not in nav_section.group(), \
                    f"{page.name} still has style-guide in main nav"


# ===========================================================================
# 5. Server Routes (6 tests)
# ===========================================================================

class TestServerRoutes:

    @pytest.fixture(autouse=True)
    def load_server(self):
        self.server_code = _read(_SERVER_PATH)

    def test_server_has_app_store_route(self):
        assert '"app-store"' in self.server_code

    def test_server_has_app_detail_route(self):
        assert '"app-detail"' in self.server_code

    def test_server_has_settings_route(self):
        assert '"settings"' in self.server_code

    def test_server_has_apps_api(self):
        assert '"/api/apps"' in self.server_code

    def test_server_has_app_detail_api(self):
        assert '"/api/apps/gmail-inbox-triage"' in self.server_code

    def test_server_has_settings_api(self):
        assert '"/api/settings"' in self.server_code


# ===========================================================================
# 6. OpenAPI Spec (8 tests)
# ===========================================================================

class TestOpenAPISpec:

    @pytest.fixture(autouse=True)
    def load_spec(self):
        self.spec_text = _read(_OPENAPI_PATH)

    def test_openapi_file_exists(self):
        assert _OPENAPI_PATH.exists(), "openapi.yaml must exist"

    def test_has_apps_endpoint(self):
        assert "/api/apps:" in self.spec_text

    def test_has_apps_detail_endpoint(self):
        assert "/api/apps/{appId}:" in self.spec_text

    def test_has_inbox_endpoint(self):
        assert "/api/apps/{appId}/inbox:" in self.spec_text

    def test_has_outbox_endpoint(self):
        assert "/api/apps/{appId}/outbox:" in self.spec_text

    def test_has_execute_endpoint(self):
        assert "/api/apps/{appId}/execute:" in self.spec_text

    def test_has_evidence_chain_endpoint(self):
        assert "/api/evidence/chain:" in self.spec_text

    def test_has_settings_endpoint(self):
        assert "/api/settings:" in self.spec_text
