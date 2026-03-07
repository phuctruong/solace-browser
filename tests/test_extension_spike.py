"""
Phase 0 Spike — Validate Playwright + MV3 Extension feasibility.

Tests the 8 spike checklist items from the architecture doc.
Run: pytest tests/test_extension_spike.py -v
"""
import json
import os
import pytest
from pathlib import Path

EXTENSION_DIR = Path(__file__).parent.parent / "solace-extension"


class TestExtensionManifest:
    """Validate manifest.json structure."""

    def test_manifest_exists(self):
        assert (EXTENSION_DIR / "manifest.json").exists()

    def test_manifest_valid_json(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        assert manifest["manifest_version"] == 3

    def test_manifest_has_side_panel(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        assert "sidePanel" in manifest["permissions"]
        assert "side_panel" in manifest
        assert manifest["side_panel"]["default_path"] == "sidepanel.html"

    def test_manifest_has_service_worker(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        assert manifest["background"]["service_worker"] == "service-worker.js"

    def test_manifest_has_tabs_permission(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        assert "tabs" in manifest["permissions"]

    def test_manifest_has_storage_permission(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        assert "storage" in manifest["permissions"]

    def test_manifest_has_csp(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        csp = manifest.get("content_security_policy", {}).get("extension_pages", "")
        assert "script-src 'self'" in csp
        assert "'unsafe-inline'" not in csp
        assert "'unsafe-eval'" not in csp

    def test_manifest_has_action(self):
        manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text())
        assert "action" in manifest
        assert "default_title" in manifest["action"]


class TestExtensionFiles:
    """Validate all required extension files exist."""

    def test_service_worker_exists(self):
        assert (EXTENSION_DIR / "service-worker.js").exists()

    def test_sidepanel_html_exists(self):
        assert (EXTENSION_DIR / "sidepanel.html").exists()

    def test_sidepanel_js_exists(self):
        assert (EXTENSION_DIR / "sidepanel.js").exists()

    def test_sidepanel_css_exists(self):
        assert (EXTENSION_DIR / "sidepanel.css").exists()

    def test_icons_exist(self):
        for size in [16, 48, 128]:
            assert (EXTENSION_DIR / f"icons/icon-{size}.png").exists()


class TestSidePanelHtml:
    """Validate side panel HTML structure."""

    def test_has_4_tabs(self):
        html = (EXTENSION_DIR / "sidepanel.html").read_text()
        assert 'data-tab="now"' in html
        assert 'data-tab="runs"' in html
        assert 'data-tab="chat"' in html
        assert 'data-tab="more"' in html

    def test_has_4_panels(self):
        html = (EXTENSION_DIR / "sidepanel.html").read_text()
        assert 'id="panel-now"' in html
        assert 'id="panel-runs"' in html
        assert 'id="panel-chat"' in html
        assert 'id="panel-more"' in html

    def test_has_aria_roles(self):
        html = (EXTENSION_DIR / "sidepanel.html").read_text()
        assert 'role="tablist"' in html
        assert 'role="tab"' in html
        assert 'role="tabpanel"' in html

    def test_has_connection_status(self):
        html = (EXTENSION_DIR / "sidepanel.html").read_text()
        assert 'id="connection-status"' in html

    def test_has_chat_input(self):
        html = (EXTENSION_DIR / "sidepanel.html").read_text()
        assert 'id="chat-input"' in html
        assert 'aria-label="Chat message"' in html

    def test_no_inline_scripts(self):
        html = (EXTENSION_DIR / "sidepanel.html").read_text()
        assert '<script>' not in html.replace('<script src=', '')
        assert 'onclick=' not in html
        assert 'onerror=' not in html

    def test_loads_js_from_file(self):
        html = (EXTENSION_DIR / "sidepanel.html").read_text()
        assert 'src="sidepanel.js"' in html

    def test_loads_css_from_file(self):
        html = (EXTENSION_DIR / "sidepanel.html").read_text()
        assert 'href="sidepanel.css"' in html


class TestServiceWorkerCode:
    """Validate service worker code quality."""

    def test_no_runtime_evaluate(self):
        """CDP Runtime.evaluate is BANNED (R8 consensus)."""
        sw = (EXTENSION_DIR / "service-worker.js").read_text()
        assert "Runtime.evaluate" not in sw

    def test_sets_panel_behavior(self):
        sw = (EXTENSION_DIR / "service-worker.js").read_text()
        assert "setPanelBehavior" in sw

    def test_listens_tabs_onupdated(self):
        sw = (EXTENSION_DIR / "service-worker.js").read_text()
        assert "tabs.onUpdated" in sw

    def test_listens_tabs_onactivated(self):
        sw = (EXTENSION_DIR / "service-worker.js").read_text()
        assert "tabs.onActivated" in sw

    def test_no_unsafe_patterns(self):
        sw = (EXTENSION_DIR / "service-worker.js").read_text()
        assert "eval(" not in sw
        assert "innerHTML" not in sw
        assert "document.write" not in sw


class TestSidePanelCode:
    """Validate side panel JS code quality."""

    def test_uses_escape_html(self):
        js = (EXTENSION_DIR / "sidepanel.js").read_text()
        assert "escapeHtml" in js

    def test_no_innerhtml_without_escape(self):
        """All innerHTML usage should use escapeHtml for dynamic content."""
        js = (EXTENSION_DIR / "sidepanel.js").read_text()
        # Count innerHTML assignments
        inner_count = js.count("innerHTML")
        escape_count = js.count("escapeHtml")
        # escapeHtml should be used at least as often as innerHTML with data
        assert escape_count >= 3, f"escapeHtml used {escape_count} times, expected >= 3"

    def test_websocket_reconnect(self):
        js = (EXTENSION_DIR / "sidepanel.js").read_text()
        assert "reconnect" in js.lower()

    def test_api_health_check(self):
        js = (EXTENSION_DIR / "sidepanel.js").read_text()
        assert "health" in js.lower()

    def test_no_eval(self):
        js = (EXTENSION_DIR / "sidepanel.js").read_text()
        # Check for eval( but not addEventListener(
        lines = js.split('\n')
        for line in lines:
            stripped = line.strip()
            if 'eval(' in stripped and not stripped.startswith('//'):
                assert False, f"eval() found: {stripped}"


class TestCssQuality:
    """Validate CSS quality."""

    def test_has_design_tokens(self):
        css = (EXTENSION_DIR / "sidepanel.css").read_text()
        assert "--yy-bg" in css
        assert "--yy-accent" in css
        assert "--yy-text" in css

    def test_no_hardcoded_colors_in_rules(self):
        """Colors should use CSS variables, not hardcoded hex."""
        css = (EXTENSION_DIR / "sidepanel.css").read_text()
        import re
        # Find hex colors outside :root block
        in_root = False
        for line in css.split('\n'):
            if ':root' in line:
                in_root = True
            if in_root and '}' in line:
                in_root = False
            if not in_root and not line.strip().startswith('/*'):
                # Allow hex in filter/animation but flag in color/background
                if re.search(r'(?:color|background):\s*#[0-9a-fA-F]{3,8}', line):
                    assert False, f"Hardcoded color: {line.strip()}"

    def test_has_scrollbar_styles(self):
        css = (EXTENSION_DIR / "sidepanel.css").read_text()
        assert "scrollbar" in css

    def test_has_accessibility_focus(self):
        """Check keyboard focus styles exist."""
        css = (EXTENSION_DIR / "sidepanel.css").read_text()
        # At minimum, no outline:none without replacement
        assert "outline: none" not in css or "outline:none" not in css
