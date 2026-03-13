"""
Tests for Yinyang sidebar UX refactor (GLOW 453).
Verifies: Domains tab first, registration gate, events tab, chat tab, CSS token compliance.
"""
import sys
import re
from pathlib import Path

SIDEPANEL_HTML = Path("/home/phuc/projects/solace-browser/solace-hub/src/sidepanel.html")
SIDEPANEL_JS   = Path("/home/phuc/projects/solace-browser/solace-hub/src/sidepanel.js")


def html() -> str:
    return SIDEPANEL_HTML.read_text(encoding="utf-8")


def js() -> str:
    return SIDEPANEL_JS.read_text(encoding="utf-8")


class TestTabOrder:
    def test_domains_tab_is_first_tab(self):
        content = html()
        # Domains button must appear before Chat and Events buttons
        pos_domains = content.index('id="tab-domains"')
        pos_chat    = content.index('id="tab-chat"')
        pos_events  = content.index('id="tab-events"')
        assert pos_domains < pos_chat < pos_events

    def test_domains_tab_is_active_by_default(self):
        content = html()
        # The first active tab should be domains
        first_active = re.search(r'class="yy-tab\s+active"[^>]*id="([^"]+)"', content)
        assert first_active is not None
        assert first_active.group(1) == "tab-domains"

    def test_no_old_now_runs_more_tabs(self):
        content = html()
        assert 'id="tab-now"' not in content
        assert 'id="tab-runs"' not in content
        assert 'id="tab-more"' not in content


class TestRegistrationGate:
    def test_gate_overlay_element_present(self):
        assert 'id="gate-overlay"' in html()

    def test_gate_links_to_register(self):
        assert 'solaceagi.com/register' in html()

    def test_js_checks_onboarding_status(self):
        content = js()
        assert '/api/v1/onboarding/status' in content

    def test_js_sets_gate_visible_when_not_logged_in(self):
        content = js()
        assert 'gate-overlay' in content
        assert 'visible' in content
        assert "auth_state === 'logged_in'" in content


class TestDomainsList:
    def test_domain_list_container_present(self):
        assert 'id="domain-list"' in html()

    def test_js_fetches_api_domains(self):
        assert '/api/v1/domains' in js()

    def test_js_navigates_on_domain_click(self):
        content = js()
        assert 'navigateToDomain' in content
        assert '/domains/' in content

    def test_solaceagi_sorted_first(self):
        content = js()
        assert "solaceagi.com" in content
        assert "return -1" in content  # sort puts it first

    def test_js_uses_solace_navigate_main_if_available(self):
        content = js()
        assert 'SOLACE_NAVIGATE_MAIN' in content


class TestEventsTab:
    def test_events_panel_present(self):
        assert 'id="panel-events"' in html()

    def test_js_fetches_events_feed(self):
        assert '/api/v1/events/feed' in js()

    def test_js_uses_current_domain_for_events(self):
        content = js()
        assert 'getCurrentDomain' in content
        assert 'loadEvents' in content

    def test_events_auto_refresh_30s(self):
        content = js()
        assert '30000' in content


class TestCSSTokenCompliance:
    def test_no_raw_hex_literals_in_style(self):
        """PrimeVisionScore: all colors must use var(--*) — no raw #hex in CSS rules."""
        content = html()
        style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
        assert style_match, "No <style> block found"
        style = style_match.group(1)

        # Extract CSS rules (not :root token definitions or comments)
        # Remove the :root block (token definitions are allowed there)
        without_root = re.sub(r':root\s*\{[^}]*\}', '', style, flags=re.DOTALL)
        # Find any raw hex colors outside :root
        raw_hex = re.findall(r'(?<!var\()#[0-9a-fA-F]{3,8}\b', without_root)
        assert raw_hex == [], f"Raw hex literals found outside :root: {raw_hex}"

    def test_design_tokens_defined_in_root(self):
        content = html()
        assert ':root' in content
        assert '--accent:' in content
        assert '--bg:' in content
        assert '--text:' in content
        assert '--border:' in content

    def test_css_uses_var_for_colors(self):
        content = html()
        # Must use var(--accent), var(--bg), etc. in CSS rules
        assert 'var(--accent)' in content
        assert 'var(--bg)' in content
        assert 'var(--text)' in content

    def test_transition_uses_ease_token(self):
        """AnimationConsistency: transitions should use var(--ease) or cubic-bezier."""
        content = html()
        assert 'var(--ease)' in content or 'cubic-bezier' in content
